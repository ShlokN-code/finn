"""Background build worker and progress reporting.

Render runs one worker thread inside the API process (only when RESEARCH_WORKER=1, and with uvicorn --workers 1);
the nightly GitHub Actions job runs the same loop in the foreground. Both claim from `research_jobs` in Supabase,
so a deploy or restart mid-build only delays a job: its heartbeat stops, `requeue_stale` puts it back, and every
stage is cached (documents, text, extractions, model calls), so the rerun is cheap.

Each thread owns its own DB connection (psycopg connections are not shared across threads).
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime

from finn.research import store

log = logging.getLogger("finn.research.jobs")

STEPS = [
    ("discover", "Finding the company's financials and documents"),
    ("compute", "Computing trajectory, cash and balance sheet"),
    ("documents", "Reading transcripts and the annual report"),
    ("extract", "Extracting guidance, actuals and analyst questions"),
    ("ledger", "Scoring promises against what was delivered"),
    ("decks", "Checking investor decks for figures the calls didn't state"),
    ("judge", "Judging qualitative promises"),
    ("reduce", "Writing the summary, bull and bear"),
    ("publish", "Publishing the dossier"),
]
HEARTBEAT_S = 30
IDLE_POLL_S = 20


class Progress:
    """Steps + counters + one human message, written to the job row (the client polls it)."""

    def __init__(self, conn, job_id: int | None):
        self.conn, self.job_id = conn, job_id
        self.steps = [{"key": k, "label": label, "status": "pending", "detail": None} for k, label in STEPS]
        self.counters = {"transcripts_total": 0, "transcripts_read": 0, "guidance_found": 0, "quotes_dropped": 0}
        self.message = "Starting"
        self.stage: str | None = None

    def step(self, key: str, status: str, detail: str | None = None, message: str | None = None) -> None:
        for s in self.steps:
            if s["key"] == key:
                s["status"], s["detail"] = status, detail
        if status == "running":
            self.stage = key
        if message:
            self.message = message
        self.flush()

    def count(self, **kw: int) -> None:
        self.counters.update(kw)
        c = self.counters
        if c["transcripts_total"]:
            self.message = f"Reading {c['transcripts_read']} of {c['transcripts_total']} transcripts"
            if c["guidance_found"]:
                self.message += f" · {c['guidance_found']} guidance statements found"
        self.flush()

    def flush(self) -> None:
        if self.job_id is None:
            return
        store.set_progress(self.conn, self.job_id, self.stage,
                           {"steps": self.steps, "counters": self.counters, "message": self.message})  # fmt: skip


@dataclass
class Outcome:
    status: str  # done | partial | waiting_quota | failed
    stats: dict = field(default_factory=dict)
    error: str | None = None
    resume_after: datetime | None = None


def run_job(conn, job: dict) -> Outcome:
    from finn.research.build import build

    progress = Progress(conn, job["id"])
    try:
        out = build(conn, job["symbol"], progress, job_id=job["id"])
    except Exception as e:  # never leave a job running; the last good dossier stays published
        import psycopg

        log.exception("research build %s failed", job["symbol"])
        transient = isinstance(e, psycopg.OperationalError) and job.get("attempts", 1) < store.MAX_ATTEMPTS
        # a lost database connection is retried (every stage is cached, so the rerun is cheap); a bug is not
        out = Outcome("queued" if transient else "failed", error=f"{type(e).__name__}: {str(e)[:300]}")
    store.finish(conn, job["id"], out.status, out.stats, out.error, out.resume_after)
    return out


class _Heartbeat(threading.Thread):
    def __init__(self, job_id: int):
        super().__init__(daemon=True, name=f"research-heartbeat-{job_id}")
        self.job_id = job_id
        self.stop = threading.Event()

    def run(self) -> None:
        from finn.db import connect

        try:
            with connect() as conn:
                while not self.stop.wait(HEARTBEAT_S):
                    store.heartbeat(conn, self.job_id)
        except Exception:
            log.exception("heartbeat thread stopped")


def work_once(conn, worker: str) -> dict | None:
    """Claim and run one job. Returns the job row, or None when the queue is empty."""
    store.requeue_stale(conn)
    job = store.claim(conn, worker)
    if not job:
        return None
    log.info("research job %s %s claimed by %s", job["id"], job["symbol"], worker)
    hb = _Heartbeat(job["id"])
    hb.start()
    try:
        run_job(conn, job)
    finally:
        hb.stop.set()
    return job


class Worker(threading.Thread):
    """In-process worker for the API (Render). `wake()` after enqueueing to start without waiting for the poll."""

    _instance: Worker | None = None

    def __init__(self) -> None:
        super().__init__(daemon=True, name="research-worker")
        self._wake = threading.Event()
        self.name_tag = f"render:{os.getpid()}"

    @classmethod
    def start_once(cls) -> Worker:
        if cls._instance is None:
            cls._instance = cls()
            cls._instance.start()
        return cls._instance

    @classmethod
    def poke(cls) -> None:
        if cls._instance is not None:
            cls._instance._wake.set()

    def run(self) -> None:
        from finn.db import connect

        while True:
            try:
                with connect() as conn:
                    while True:
                        if work_once(conn, self.name_tag) is None:
                            self._wake.wait(IDLE_POLL_S)
                            self._wake.clear()
            except Exception:
                log.exception("research worker loop crashed; restarting in 30 s")
                time.sleep(30)


def drain(conn, worker: str, max_jobs: int = 50, deadline_s: float | None = None) -> int:
    """Foreground loop for GitHub Actions: run queued jobs until the queue is empty or the deadline passes."""
    t0, n = time.monotonic(), 0
    while n < max_jobs and (deadline_s is None or time.monotonic() - t0 < deadline_s):
        if work_once(conn, worker) is None:
            break
        n += 1
    return n
