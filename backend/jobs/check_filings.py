"""Intraday filing check (every 30 min, 08:30–21:30 IST on weekdays): today's announcements → classify → thread.

Runs on exchange holidays too: companies still file (board meetings, results) when the market is shut.
Outside the window it exits at once, so a delayed GitHub cron run costs nothing.

python -m jobs.check_filings [--symbols X,Y] [--force]
"""

from __future__ import annotations

import argparse
import logging
from datetime import time, timedelta

from finn.calendar import ist_today, now_utc, to_ist
from finn.db import connect
from finn.ingest import pipeline as p
from finn.portfolio import tracked_symbols
from finn.sources import nse
from jobs.alerts import step_alerts

WINDOW = (time(8, 30), time(22, 0))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="")
    ap.add_argument("--force", action="store_true", help="run outside the IST window / on weekends")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    now = to_ist(now_utc())
    if not args.force and (now.weekday() >= 5 or not (WINDOW[0] <= now.time() <= WINDOW[1])):
        print(f"outside filing-check window ({now:%a %H:%M} IST); nothing to do")
        return

    today = ist_today()
    with connect() as conn, p.Run("check_filings", conn) as run:
        symbols = tracked_symbols(args.symbols or None, conn)
        run.stats["symbols"] = symbols
        s = nse.session()
        run.step("announcements", p.step_announcements, s, symbols, today - timedelta(days=1), today)
        run.step("classify", p.step_classify, s, symbols)
        run.step("thread", p.step_thread, symbols)
        run.step("results_fetch", p.step_results_fetch, s, symbols)
        run.step("results_build", p.step_results_build, symbols, s=s)
        run.step("tag", p.step_tag, s, symbols)
        run.step("alerts", step_alerts)


if __name__ == "__main__":
    main()
