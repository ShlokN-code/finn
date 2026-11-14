"""FINN API (skeleton).

GET /health     — liveness (no DB), used by keep-alive pings.
GET /health/db  — reads one row from Supabase Postgres to prove web → API → DB.
GET|HEAD /ping  — keepalive: answers at once ('ok', never compressed); SELECT 1 on Supabase in the background.
GET /health/sources — can this server reach NSE/BSE/screener? (cached 15 min)
/research/*     — dossiers, build jobs, Ask (api/research.py)
"""

from __future__ import annotations

import logging
import os
import threading
import time
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from api.diagnostics import get_probes
from api.push import router as push_router
from api.research import router as research_router
from finn import __version__

log = logging.getLogger("finn.api")
_STARTED = time.time()  # process start: /version reports uptime, so a restart or wake-from-sleep is visible


def _rss_mb() -> float | None:
    """Resident memory of this process (Linux /proc; None elsewhere) — Render's free instance has 512 MB."""
    try:
        for line in open("/proc/self/status"):
            if line.startswith("VmRSS:"):
                return round(int(line.split()[1]) / 1024, 1)
    except OSError:
        return None
    return None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Research builds run in a background thread of this process — only where RESEARCH_WORKER=1 (Render, started
    # with --workers 1), never in tests or a second uvicorn worker.
    if os.environ.get("RESEARCH_WORKER") == "1":
        from finn.research.jobs import Worker

        Worker.start_once()
    yield


app = FastAPI(title="FINN API", version=__version__, lifespan=lifespan)


@app.middleware("http")
async def server_timing(request, call_next):
    """Server-Timing: app;dur=<ms> on every response — separates time spent in FINN from network, Render's proxy
    and cold starts when a caller (cron-job.org, the smoke test) sees a slow request."""
    t0 = time.perf_counter()
    resp = await call_next(request)
    resp.headers["Server-Timing"] = f"app;dur={(time.perf_counter() - t0) * 1000:.1f}"
    return resp


app.include_router(push_router)
app.include_router(research_router)

_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
if _origins:
    app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_methods=["GET", "POST", "PUT", "DELETE"],
                       allow_headers=["*"])  # fmt: skip


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.get("/version")
def version() -> dict:
    """The deployed commit (Render sets RENDER_GIT_COMMIT), so a push can be confirmed live."""
    commit = os.environ.get("RENDER_GIT_COMMIT") or os.environ.get("GIT_COMMIT") or None
    return {"commit": commit, "short": commit[:7] if commit else None, "version": __version__,
            "uptime_s": round(time.time() - _STARTED), "rss_mb": _rss_mb()}  # fmt: skip


@app.get("/health/db")
def health_db():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return JSONResponse({"status": "error", "error": "DATABASE_URL not set"}, status_code=503)
    t0 = time.perf_counter()
    try:
        with psycopg.connect(dsn, connect_timeout=10) as conn:
            row = conn.execute("select id, message, created_at from public.hello order by id limit 1").fetchone()
    except psycopg.Error as e:
        # Log details server-side; return only the error class (never the DSN).
        log.exception("DB check failed")
        return JSONResponse({"status": "error", "error": type(e).__name__}, status_code=503)
    ms = round((time.perf_counter() - t0) * 1000)
    if row is None:
        return JSONResponse({"status": "error", "error": "hello table is empty"}, status_code=503)
    return {
        "status": "ok",
        "row": {"id": row[0], "message": row[1], "created_at": row[2].isoformat()},
        "db_ms": ms,
    }


# Keepalive for uptime pingers (cron-job.org): the smallest possible reply. Render's Cloudflare edge Brotli-
# compresses and chunk-streams normal responses for clients that accept it, which strict pingers reject
# ("output too large"); `no-transform` stops edge compression and Content-Length is explicit. HEAD works too.
_PING_HEADERS = {"Cache-Control": "no-store, no-transform", "Content-Encoding": "identity"}


_DB_TOUCH_EVERY_S = 300
_db_state = {"at": 0.0, "ok": True, "running": False}
_db_lock = threading.Lock()


def _touch_db() -> None:
    """SELECT 1 on Supabase (keeps the free project from pausing) — on a background thread, never on /ping's path."""
    dsn = os.environ.get("DATABASE_URL")
    ok = False
    try:
        if dsn:
            with psycopg.connect(dsn, connect_timeout=10) as conn:
                conn.execute("select 1").fetchone()
            ok = True
    except psycopg.Error:
        log.exception("ping: background DB check failed")
    finally:
        with _db_lock:
            _db_state.update(at=time.time(), ok=ok, running=False)


@app.api_route("/ping", methods=["GET", "HEAD"], include_in_schema=False)
def ping() -> PlainTextResponse:
    """Keepalive: answers at once. The DB check runs in the background at most every 5 minutes; /ping reports the
    last result (503 'db down' if it failed), so the pinger still alerts on a dead database without waiting on it."""
    with _db_lock:
        due = not _db_state["running"] and time.time() - _db_state["at"] > _DB_TOUCH_EVERY_S
        if due:
            _db_state["running"] = True
        ok = _db_state["ok"]
    if due:
        threading.Thread(target=_touch_db, name="ping-db", daemon=True).start()
    if not os.environ.get("DATABASE_URL"):
        return PlainTextResponse("no db", status_code=503, headers=_PING_HEADERS)
    if not ok:
        return PlainTextResponse("db down", status_code=503, headers=_PING_HEADERS)
    return PlainTextResponse("ok", headers=_PING_HEADERS)


@app.get("/health/sources")
def health_sources() -> dict:
    return get_probes()
