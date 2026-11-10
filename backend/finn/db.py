"""Postgres (Supabase) access for jobs and the API: one psycopg 3 connection from DATABASE_URL.

Jobs load a local `.env` (repo root or backend/) when present so `python -m jobs.x` works on a dev machine;
in GitHub Actions the variables come from secrets.
"""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

_ROOTS = [Path(__file__).resolve().parents[2], Path(__file__).resolve().parents[1]]


def load_dotenv() -> None:
    """Minimal .env loader (KEY=VALUE lines); never overrides variables already set."""
    for root in _ROOTS:
        f = root / ".env"
        if not f.exists():
            continue
        for line in f.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def connect(*, autocommit: bool = True) -> psycopg.Connection:
    load_dotenv()
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set (see .env.example)")
    # prepare_threshold=None: the Supabase pooler may not keep prepared statements across transactions.
    return psycopg.connect(dsn, autocommit=autocommit, row_factory=dict_row, connect_timeout=15, prepare_threshold=None)
