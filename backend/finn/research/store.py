"""Supabase persistence for research: build jobs (the queue), dossiers, documents, extracted text, extractions.

Every function takes a psycopg connection (dict rows, autocommit). The queue is safe with several workers (Render's
thread and a GitHub Actions run): jobs are claimed with FOR UPDATE SKIP LOCKED, and a partial unique index allows
one active job per ticker.
"""

from __future__ import annotations

import gzip
import json
from datetime import datetime

from psycopg.types.json import Jsonb

from finn.calendar import ist_today
from finn.models.research import SCHEMA_VERSION, Dossier, DossierJob

ACTIVE = ("queued", "running", "waiting_quota")
STALE_AFTER_S = 180  # a running job whose heartbeat is older than this is assumed dead (worker restarted)
MAX_ATTEMPTS = 3

# --- securities ------------------------------------------------------------------------------


def security(conn, symbol: str) -> dict | None:
    return conn.execute("select symbol, name, isin from public.securities where symbol = %s", (symbol,)).fetchone()


def all_securities(conn) -> list[dict]:
    return conn.execute("select symbol, name from public.securities order by symbol").fetchall()


# --- jobs ------------------------------------------------------------------------------------


def enqueue(conn, symbol: str, reason: str = "requested", priority: int = 10) -> tuple[dict, bool]:
    """(job row, created). An active job for the ticker is reused rather than duplicated."""
    row = conn.execute(
        "insert into public.research_jobs (symbol, reason, priority, progress) values (%s, %s, %s, %s) "
        "on conflict (symbol) where status in ('queued','running','waiting_quota') do nothing returning *",
        (symbol, reason, priority, Jsonb({"message": "Queued"})),
    ).fetchone()
    if row:
        return row, True
    return active_job(conn, symbol), False


def active_job(conn, symbol: str) -> dict | None:
    return conn.execute(
        "select * from public.research_jobs where symbol = %s and status = any(%s) order by id desc limit 1",
        (symbol, list(ACTIVE)),
    ).fetchone()


def latest_job(conn, symbol: str) -> dict | None:
    return conn.execute(
        "select * from public.research_jobs where symbol = %s order by id desc limit 1", (symbol,)
    ).fetchone()


def get_job(conn, job_id: int) -> dict | None:
    return conn.execute("select * from public.research_jobs where id = %s", (job_id,)).fetchone()


def claim(conn, worker: str) -> dict | None:
    """Take the next runnable job (queued, or waiting for quota whose resume time has passed)."""
    return conn.execute(
        "update public.research_jobs set status = 'running', worker = %s, attempts = attempts + 1, "
        "started_at = coalesce(started_at, now()), heartbeat_at = now(), updated_at = now(), resume_after = null "
        "where id = (select id from public.research_jobs where status = 'queued' "
        "   or (status = 'waiting_quota' and resume_after <= now()) "
        "   order by priority, queued_at for update skip locked limit 1) returning *",
        (worker,),
    ).fetchone()


def requeue_stale(conn) -> int:
    """Running jobs whose worker died (restart/deploy) go back to the queue; after MAX_ATTEMPTS they fail."""
    failed = conn.execute(
        "update public.research_jobs set status = 'failed', finished_at = now(), updated_at = now(), "
        "error = 'Stopped after repeated worker restarts' where status = 'running' "
        "and heartbeat_at < now() - make_interval(secs => %s) and attempts >= %s returning id",
        (STALE_AFTER_S, MAX_ATTEMPTS),
    ).fetchall()
    back = conn.execute(
        "update public.research_jobs set status = 'queued', updated_at = now() where status = 'running' "
        "and heartbeat_at < now() - make_interval(secs => %s) returning id",
        (STALE_AFTER_S,),
    ).fetchall()
    return len(failed) + len(back)


def heartbeat(conn, job_id: int) -> None:
    conn.execute("update public.research_jobs set heartbeat_at = now() where id = %s and status = 'running'",
                 (job_id,))  # fmt: skip


def set_progress(conn, job_id: int, stage: str | None, progress: dict) -> None:
    conn.execute(
        "update public.research_jobs set stage = %s, progress = %s, heartbeat_at = now(), updated_at = now() "
        "where id = %s",
        (stage, Jsonb(progress), job_id),
    )


def finish(conn, job_id: int, status: str, stats: dict, error: str | None = None,
           resume_after: datetime | None = None) -> None:  # fmt: skip
    conn.execute(
        "update public.research_jobs set status = %s, stats = %s, error = %s, resume_after = %s, "
        "attempts = case when %s = 'waiting_quota' then 0 else attempts end, "
        "finished_at = case when %s in ('done','partial','failed') then now() else null end, "
        "updated_at = now() where id = %s",
        (status, Jsonb(stats), error, resume_after, status, status, job_id),
    )


def queue_position(conn, job: dict) -> int | None:
    if job["status"] != "queued":
        return None
    r = conn.execute(
        "select count(*) as n from public.research_jobs where status = 'queued' and (priority, queued_at) < (%s, %s)",
        (job["priority"], job["queued_at"]),
    ).fetchone()
    running = conn.execute("select count(*) as n from public.research_jobs where status = 'running'").fetchone()
    return int(r["n"]) + int(running["n"] > 0) + 1


def job_model(conn, row: dict) -> DossierJob:
    p = row.get("progress") or {}
    return DossierJob(
        id=row["id"],
        symbol=row["symbol"],
        status=row["status"],
        reason=row["reason"],
        queue_position=queue_position(conn, row),
        stage=row.get("stage"),
        steps=p.get("steps", []),
        counters=p.get("counters", {}),
        message=p.get("message") or row["status"].replace("_", " ").capitalize(),
        queued_at=row["queued_at"],
        started_at=row.get("started_at"),
        updated_at=row["updated_at"],
        finished_at=row.get("finished_at"),
        resume_after=row.get("resume_after"),
        error=row.get("error"),
    )


def count_requests_today(conn, kind: str = "build") -> int:
    r = conn.execute(
        "select count(*) as n from public.research_requests where ist_date = %s and kind = %s", (ist_today(), kind)
    ).fetchone()
    return int(r["n"])


def record_request(conn, symbol: str, kind: str = "build") -> None:
    conn.execute(
        "insert into public.research_requests (symbol, ist_date, kind) values (%s, %s, %s)",
        (symbol, ist_today(), kind),
    )


# --- dossiers --------------------------------------------------------------------------------


def get_dossier_row(conn, symbol: str) -> dict | None:
    return conn.execute("select * from public.dossiers where symbol = %s", (symbol,)).fetchone()


def load_dossier(row: dict | None) -> Dossier | None:
    """The stored dossier, or None when it was written by an older contract (it gets rebuilt)."""
    if not row or row["schema_version"] != SCHEMA_VERSION:
        return None
    try:
        return Dossier.model_validate(row["payload"])
    except ValueError:
        return None


def publish(conn, d: Dossier, complete: bool, doc_set_hash: str | None = None,
            synthesis_hash: str | None = None) -> int:  # fmt: skip
    """Write the dossier; returns its new version (clients refetch when it changes)."""
    r = conn.execute(
        "insert into public.dossiers (symbol, schema_version, payload, doc_set_hash, synthesis_hash, status, "
        "built_at) values (%s,%s,%s,%s,%s,%s,%s) on conflict (symbol) do update set "
        "schema_version = excluded.schema_version, payload = excluded.payload, "
        "doc_set_hash = coalesce(excluded.doc_set_hash, dossiers.doc_set_hash), "
        "synthesis_hash = coalesce(excluded.synthesis_hash, dossiers.synthesis_hash), status = excluded.status, "
        "built_at = excluded.built_at, version = dossiers.version + 1, updated_at = now() returning version",
        (d.symbol, d.schema_version, Jsonb(d.model_dump(mode="json")), doc_set_hash, synthesis_hash,
         "complete" if complete else "partial", d.built_at),
    ).fetchone()  # fmt: skip
    return int(r["version"])


def touch_opened(conn, symbol: str) -> None:
    conn.execute("update public.dossiers set last_opened_at = now() where symbol = %s", (symbol,))


# --- documents and text ----------------------------------------------------------------------


def get_document(conn, url: str) -> dict | None:
    return conn.execute("select * from public.research_documents where url = %s", (url,)).fetchone()


def upsert_document(conn, url: str, symbol: str, kind: str, **fields) -> None:
    cols = ["url", "symbol", "kind", *fields]
    vals = [url, symbol, kind, *fields.values()]
    sets = ", ".join(f"{c} = excluded.{c}" for c in ["symbol", "kind", *fields])
    conn.execute(
        f"insert into public.research_documents ({', '.join(cols)}) values ({', '.join(['%s'] * len(cols))}) "
        f"on conflict (url) do update set {sets}",
        vals,
    )


def has_text(conn, sha256: str) -> bool:
    return conn.execute("select 1 from public.research_doc_text where sha256 = %s", (sha256,)).fetchone() is not None


def save_text(conn, sha256: str, pages: list[str], extractor: str) -> None:
    blob = gzip.compress(json.dumps(pages, ensure_ascii=False).encode(), compresslevel=6)
    conn.execute(
        "insert into public.research_doc_text (sha256, pages_gz, page_count, chars, extractor) "
        "values (%s,%s,%s,%s,%s) on conflict (sha256) do nothing",
        (sha256, blob, len(pages), sum(len(p) for p in pages), extractor),
    )


def load_text(conn, sha256: str) -> list[str] | None:
    r = conn.execute(
        "update public.research_doc_text set last_used_at = now() where sha256 = %s returning pages_gz", (sha256,)
    ).fetchone()
    return json.loads(gzip.decompress(bytes(r["pages_gz"]))) if r else None


def get_extraction(conn, sha256: str, extractor: str, version: str) -> dict | None:
    return conn.execute(
        "select * from public.research_extractions where sha256 = %s and extractor = %s and prompt_version = %s",
        (sha256, extractor, version),
    ).fetchone()


def save_extraction(conn, sha256: str, extractor: str, version: str, model: str, payload: dict,
                    stats: dict) -> None:  # fmt: skip
    conn.execute(
        "insert into public.research_extractions (sha256, extractor, prompt_version, model, payload, stats) "
        "values (%s,%s,%s,%s,%s,%s) on conflict (sha256, extractor, prompt_version) do update set "
        "model = excluded.model, payload = excluded.payload, stats = excluded.stats, created_at = now()",
        (sha256, extractor, version, model, Jsonb(payload), Jsonb(stats)),
    )
