"""Scheduler slots: the external trigger and GitHub's backup cron must not both do the work."""

from datetime import UTC, datetime

from finn.ingest.schedule import already_ran, slot_start


def utc(h, m, day=10):
    return datetime(2026, 11, day, h, m, tzinfo=UTC)


class Conn:
    def __init__(self, rows):
        self.rows, self.args = rows, None

    def execute(self, sql, args):
        self.args = args
        job, since = args
        hit = [r for r in self.rows if r[0] == job and r[2] in ("ok", "partial") and r[1] >= since]
        hit.sort(key=lambda r: r[1], reverse=True)
        return type("R", (), {"fetchone": lambda s: {"started_at": hit[0][1]} if hit else None})()


def test_filings_slot_is_twenty_minutes():
    assert slot_start("check_filings", utc(5, 30)) == utc(5, 10)
    conn = Conn([("check_filings", utc(5, 0), "ok")])  # external scheduler ran the 10:30 IST slot
    assert already_ran(conn, "check_filings", utc(5, 17)) == utc(5, 0)  # GitHub's late backup at 10:47 → skip
    assert already_ran(conn, "check_filings", utc(5, 30)) is None  # the 11:00 IST slot runs


def test_failed_run_does_not_block_the_slot():
    conn = Conn([("check_filings", utc(5, 0), "failed")])
    assert already_ran(conn, "check_filings", utc(5, 5)) is None


def test_daily_counts_from_four_pm_ist():
    assert slot_start("ingest_daily", utc(9, 0)) is None  # 14:30 IST: before the post-close slot
    assert slot_start("ingest_daily", utc(11, 0)) == utc(10, 30)  # 16:30 IST → since 16:00 IST
    morning_backfill = ("ingest_daily", utc(4, 30), "ok")  # 10:00 IST manual run doesn't count
    assert already_ran(Conn([morning_backfill]), "ingest_daily", utc(11, 0)) is None
    post_close = ("ingest_daily", utc(11, 1), "partial")
    assert already_ran(Conn([morning_backfill, post_close]), "ingest_daily", utc(11, 40)) == utc(11, 1)


def test_other_jobs_have_no_slot():
    assert slot_start("alerts", utc(1, 30)) is None  # alert dispatch is idempotent by itself
