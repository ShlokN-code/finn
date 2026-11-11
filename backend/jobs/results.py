"""Results cards: fetch XBRL (current, previous, year-ago quarter) for recent results events, then build and
cross-check each card. Also run at the end of check_filings / ingest_daily.

python -m jobs.results [--symbols X,Y] [--days 45] [--no-fetch] [--rebuild] [--relink]
  --no-fetch: build from stored XBRL only · --rebuild: also rebuild final (cross-checked) cards
  --relink: only rewrite stored cards' links (results PDF page → iXBRL → raw XBRL); no number changes
"""

from __future__ import annotations

import argparse
import logging

from finn.db import connect
from finn.ingest import pipeline as p
from finn.portfolio import tracked_symbols
from finn.sources import nse


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="")
    ap.add_argument("--days", type=int, default=45, help="results events updated in the last N days")
    ap.add_argument("--no-fetch", action="store_true", help="skip NSE (local dev / Render): stored XBRL only")
    ap.add_argument("--rebuild", action="store_true", help="rebuild final cards too (after a method change)")
    ap.add_argument("--relink", action="store_true", help="rewrite stored cards' links only")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    with connect() as conn, p.Run("results", conn) as run:
        symbols = tracked_symbols(args.symbols or None, conn)
        run.stats["symbols"] = symbols
        s = None if args.no_fetch else nse.session()
        if args.relink:
            if not args.symbols:  # every symbol with a results card, not only the tracked portfolio
                rows = conn.execute("select distinct symbol from public.events where category = 'results'").fetchall()
                symbols = sorted({r["symbol"] for r in rows} | set(symbols))
                run.stats["symbols"] = symbols
            run.step("results_relink", p.step_results_relink, symbols, args.days, s)
            return
        if s is not None:
            run.step("results_fetch", p.step_results_fetch, s, symbols, args.days)
        run.step("results_build", p.step_results_build, symbols, args.days, s=s, rebuild=args.rebuild)


if __name__ == "__main__":
    main()
