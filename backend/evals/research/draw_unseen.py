"""Reproducible draw of 'unseen' tickers for the research acceptance test (Phase 3).

python -m evals.research.draw_unseen [--seed 20261111] [--extra 0]

- Pool: NSE equity list, EQ series (public.securities, refreshed from EQUITY_L.csv).
- Excluded: the 18 demo-portfolio tickers, the 4 research demo tickers, and every symbol FINN has already built or
  tested (anything in dossiers, research_documents, filings, results_filings or prices_daily, plus TRENT).
- Draw 1 — banks/NBFCs: company name matches FIN_RE (the equity list carries no industry, so the name decides).
- Draw 2 — outside the Nifty 100 (evals/research/nifty100_2026-11-11.csv, NSE archive) and not matching FIN_RE.
- `--extra N` draws N more from pool 2 (used when a drawn ticker has no screener page — it is kept, not replaced).
The seed is fixed and logged so the pick is reproducible and not hand-chosen.
"""

from __future__ import annotations

import argparse
import csv
import random
import re
from pathlib import Path

from finn.db import connect
from finn.portfolio import DEMO_PORTFOLIO

DEMO = ["BAJFINANCE", "INFY", "PERSISTENT", "POLYCAB"]
FIN_RE = re.compile(r"\b(bank|finance|financial|financials|fincorp|finserv|fincap|credit|leasing|housing finance)\b",
                    re.I)  # fmt: skip
NIFTY100 = Path(__file__).with_name("nifty100_2026-11-11.csv")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20261111)
    ap.add_argument("--extra", type=int, default=0)
    a = ap.parse_args()
    nifty = {r["Symbol"] for r in csv.DictReader(NIFTY100.open())}
    with connect() as c:
        rows = c.execute("select symbol, name from public.securities where series = 'EQ' order by symbol").fetchall()
        seen = {"TRENT"} | set(DEMO_PORTFOLIO) | set(DEMO)
        for t in ("dossiers", "research_documents", "filings", "results_filings", "prices_daily"):
            seen |= {r["symbol"] for r in c.execute(f"select distinct symbol from public.{t}").fetchall()}  # noqa: S608
    pool = [r for r in rows if r["symbol"] not in seen]
    fin = [r for r in pool if FIN_RE.search(r["name"] or "")]
    other = [r for r in pool if not FIN_RE.search(r["name"] or "") and r["symbol"] not in nifty]
    rng = random.Random(a.seed)
    pick_fin = rng.choice(fin)
    pick_other = rng.sample(other, 1 + a.extra)
    print(f"seed={a.seed} pool={len(pool)} excluded={len(seen)} banks/NBFCs={len(fin)} outside-Nifty100={len(other)}")
    print(f"bank/NBFC: {pick_fin['symbol']} ({pick_fin['name']})")
    for p in pick_other:
        print(f"outside Nifty 100: {p['symbol']} ({p['name']})")


if __name__ == "__main__":
    main()
