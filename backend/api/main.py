"""FINN API (skeleton).

GET /health     — liveness (no DB), used by keep-alive pings.
GET /health/db  — reads one row from Supabase Postgres to prove web → API → DB.
GET|HEAD /ping  — keepalive: SELECT 1 on Supabase, plain-text 'ok', never compressed (cron-job.org).
GET /health/sources — can this server reach NSE/BSE/screener? (cached 15 min)
/research/*     — dossiers, build jobs, Ask (api/research.py)
"""

from __future__ import annotations

import logging
import os
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


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Research builds run in a background thread of this process — only where RESEARCH_WORKER=1 (Render, started
    # with --workers 1), never in tests or a second uvicorn worker.
    if os.environ.get("RESEARCH_WORKER") == "1":
        from finn.research.jobs import Worker

        Worker.start_once()
    yield


app = FastAPI(title="FINN API", version=__version__, lifespan=lifespan)
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
    return {"commit": commit, "short": commit[:7] if commit else None, "version": __version__}


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


@app.api_route("/ping", methods=["GET", "HEAD"], include_in_schema=False)
def ping() -> PlainTextResponse:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return PlainTextResponse("no db", status_code=503, headers=_PING_HEADERS)
    try:
        with psycopg.connect(dsn, connect_timeout=10) as conn:
            conn.execute("select 1").fetchone()
    except psycopg.Error:
        log.exception("ping: DB check failed")
        return PlainTextResponse("db down", status_code=503, headers=_PING_HEADERS)
    return PlainTextResponse("ok", headers=_PING_HEADERS)


@app.get("/health/sources")
def health_sources() -> dict:
    return get_probes()
