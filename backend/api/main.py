"""FINN API (skeleton).

GET /health     — liveness (no DB), used by keep-alive pings.
GET /health/db  — reads one row from Supabase Postgres to prove web → API → DB.
"""

from __future__ import annotations

import logging
import os
import time

import psycopg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from finn import __version__

log = logging.getLogger("finn.api")
app = FastAPI(title="FINN API", version=__version__)

_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
if _origins:
    app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_methods=["GET"], allow_headers=["*"])


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


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
