"""Alert dispatch: new events → Telegram subscribers (budget, batching, quiet hours, snooze).

Also runs at the end of check_filings and ingest_daily; the 07:00 IST cron releases quiet-hours holds.

python -m jobs.alerts
"""

from __future__ import annotations

import logging

from finn.calendar import now_utc
from finn.db import connect
from finn.ingest import pipeline as p
from finn.push.dispatch import run_dispatch
from finn.push.telegram import Telegram


def step_alerts(run: p.Run) -> None:
    run.stats["alerts"] = run_dispatch(run.conn, Telegram(), now_utc())


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    with connect() as conn, p.Run("alerts", conn) as run:
        run.step("alerts", step_alerts)


if __name__ == "__main__":
    main()
