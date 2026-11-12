"""Scheduled slots. The external scheduler (cron-job.org → workflow_dispatch) and GitHub's own cron (kept as a
backup) can both fire for the same slot; whichever starts second sees the first run in `ingest_runs` and skips.
Manual runs never skip.

  filings: one run per 20 minutes (slots are every 30 min; GitHub's cron is often late by minutes to hours)
  daily:   one post-close run per IST day (counted from 16:00 IST, so a manual daytime backfill doesn't block it)
  research_refresh: one per IST day, from the first filing slot at or after 22:00 IST
"""

from __future__ import annotations

from datetime import datetime, time, timedelta

from finn.calendar import IST, to_ist

FILINGS_SLOT = timedelta(minutes=20)
DAILY_SLOT_START = time(16, 0)  # IST
REFRESH_SLOT_START = time(22, 0)  # IST: the nightly research refresh rides on the first filing slot from 22:00


def slot_start(job: str, now: datetime) -> datetime | None:
    """Earliest start time that counts as 'this slot already ran' for `job`; None = no slot logic."""
    if job == "check_filings":
        return now - FILINGS_SLOT
    if job in ("ingest_daily", "research_refresh"):
        local = to_ist(now)
        start = datetime.combine(local.date(), DAILY_SLOT_START if job == "ingest_daily" else REFRESH_SLOT_START,
                                 tzinfo=IST)  # fmt: skip
        return start if local >= start else None
    return None


def refresh_due(conn, now: datetime) -> tuple[bool, str]:
    """The nightly research refresh: due from 22:00 IST, once per IST day."""
    if slot_start("research_refresh", now) is None:
        return False, f"before 22:00 IST ({to_ist(now):%H:%M})"
    ran = already_ran(conn, "research_refresh", now)
    return (False, f"already ran at {to_ist(ran):%H:%M} IST") if ran else (True, "due")


def already_ran(conn, job: str, now: datetime) -> datetime | None:
    """When this slot's successful (ok/partial) run started, or None if it hasn't run yet."""
    start = slot_start(job, now)
    if start is None:
        return None
    row = conn.execute(
        "select started_at from public.ingest_runs where job = %s and status in ('ok', 'partial') "
        "and started_at >= %s order by started_at desc limit 1",
        (job, start),
    ).fetchone()
    return row["started_at"] if row else None
