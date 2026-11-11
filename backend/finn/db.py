"""Postgres (Supabase) access for jobs and the API: one psycopg 3 connection from DATABASE_URL.

Jobs load a local `.env` (repo root or backend/) when present so `python -m jobs.x` works on a dev machine;
in GitHub Actions the variables come from secrets.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import set_json_dumps

# Postgres jsonb rejects the NUL character ("\u0000 cannot be converted to text"), and a single filing whose PDF
# text carried one made every run's tagging step fail. Strip escaped NULs (not an escaped backslash before 'u0000').
_NUL = re.compile(r"(?<!\\)((?:\\\\)*)\\u0000")


def _dumps(obj) -> str:
    return _NUL.sub(r"\1", json.dumps(obj))


set_json_dumps(_dumps)

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


def _raw_connect(dsn: str, autocommit: bool) -> psycopg.Connection:
    # prepare_threshold=None: the Supabase pooler may not keep prepared statements across transactions.
    # TCP keepalives stop the pooler/NAT from silently dropping a connection that idles during slow model calls.
    return psycopg.connect(
        dsn, autocommit=autocommit, row_factory=dict_row, connect_timeout=15, prepare_threshold=None,
        keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=5,
    )  # fmt: skip


class ResilientConnection:
    """psycopg connection that reconnects once when the server has closed it (jobs run for many minutes
    against a pooled Supabase connection). Only autocommit statements are retried — never a half-done
    transaction."""

    def __init__(self, dsn: str, autocommit: bool = True):
        self._dsn, self._autocommit = dsn, autocommit
        self._conn = _raw_connect(dsn, autocommit)

    def _ensure(self) -> psycopg.Connection:
        if self._conn.closed or self._conn.broken:
            self._conn = _raw_connect(self._dsn, self._autocommit)
        return self._conn

    def execute(self, *args, **kw):
        try:
            return self._ensure().execute(*args, **kw)
        except psycopg.OperationalError:
            # Retry only a lost autocommit connection; anything else (or a lost transaction) is re-raised.
            if not self._autocommit or not (self._conn.closed or self._conn.broken):
                raise
            self._conn = _raw_connect(self._dsn, self._autocommit)
            return self._conn.execute(*args, **kw)

    def cursor(self, *args, **kw):
        return self._ensure().cursor(*args, **kw)

    def transaction(self, *args, **kw):
        return self._ensure().transaction(*args, **kw)

    def close(self) -> None:
        self._conn.close()

    def __getattr__(self, name):
        return getattr(self._ensure(), name)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def connect(*, autocommit: bool = True) -> ResilientConnection:
    load_dotenv()
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set (see .env.example)")
    return ResilientConnection(dsn, autocommit)
