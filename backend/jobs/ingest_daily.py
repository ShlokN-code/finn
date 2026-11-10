"""Daily post-close ingest (~16:30 IST): holidays, securities, prices, announcements, board meetings,
corporate actions, deals → classify → thread. Also the backfill entry point.

python -m jobs.ingest_daily                       # normal daily run for the demo portfolio
python -m jobs.ingest_daily --backfill-days 365   # first run: 1y prices + 365 days of filings
python -m jobs.ingest_daily --symbols TRENT,POLYCAB
"""

from __future__ import annotations

import argparse
import logging
from datetime import timedelta

from finn.calendar import is_trading_day, ist_today
from finn.db import connect
from finn.ingest import pipeline as p
from finn.portfolio import tracked_symbols
from finn.push import subscriptions as subs
from finn.signals.price_volume import INDEX_TICKERS
from finn.signals.run import step_signals
from finn.sources import nse
from jobs.alerts import step_alerts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="")
    ap.add_argument("--backfill-days", type=int, default=0, help="also re-fetch this many days of filings")
    ap.add_argument("--skip-prices", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    today = ist_today()
    days = max(args.backfill_days, 3)
    with connect() as conn, p.Run("ingest_daily", conn) as run:
        symbols = tracked_symbols(args.symbols or None, conn)
        run.stats["symbols"] = symbols
        s = nse.session()
        run.step("holidays", p.step_holidays, s)
        run.step("securities", p.step_securities, s)
        if args.skip_prices:
            pass
        elif is_trading_day(today) or args.backfill_days:
            run.step("prices", p.step_prices, symbols + INDEX_TICKERS, backfill=args.backfill_days >= 365)
        else:
            run.stats["prices"] = f"skipped: {today} is not a trading day"
        # Filings are disseminated on exchange holidays too (board meetings happen), so always fetch them.
        run.step("announcements", p.step_announcements, s, symbols, today - timedelta(days=days), today)
        run.step("board_meetings", p.step_board_meetings, s, symbols, today - timedelta(days=max(days, 120)))
        run.step("corporate_actions", p.step_corporate_actions, s, symbols)
        run.step("deals", p.step_deals, s, symbols, today - timedelta(days=min(days, 30)), today)
        run.step("classify", p.step_classify, s, symbols)
        run.step("thread", p.step_thread, symbols)
        run.step("results_fetch", p.step_results_fetch, s, symbols)
        run.step("results_build", p.step_results_build, symbols)
        if is_trading_day(today) and not args.skip_prices:
            settings = [subs.settings_of(x) for x in subs.all_subscriptions(conn)]
            run.step("signals", step_signals, symbols, today, settings)
        run.step("alerts", step_alerts)


if __name__ == "__main__":
    main()
