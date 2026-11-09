"""Spike (e): full NSE equity list (for ticker autocomplete), plus demo-ticker checks."""

from __future__ import annotations

import csv
import io

from _common import Result, finn_session, log, nse_session, polite_get, save_sample

URLS = [
    "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv",
    "https://archives.nseindia.com/content/equities/EQUITY_L.csv",
]
DEMO = ["HAL", "EICHERMOT", "GRASIM", "TATAPOWER", "ALKEM", "KALYANKJIL", "COCHINSHIP", "TITAGARH",
        "IDEA", "RELIANCE", "HDFCBANK", "BAJFINANCE", "INFY", "ITC", "DIVISLAB", "TATASTEEL",
        "JUBLFOOD", "DIXON", "PERSISTENT", "POLYCAB"]

res = Result("e_equity_list")
rows: list[dict] = []
for url in URLS:
    for label, sess in (("plain FINN UA", finn_session()), ("NSE session", None)):
        if sess is None:
            sess = nse_session()
        r = polite_get(sess, url, use_cache=False, retries=1)
        ok = r.ok and r.text.startswith("SYMBOL")
        log(f"  {url} [{label}]: HTTP {r.status_code}, {len(r.content)} bytes, csv={ok}")
        if ok:
            rows = list(csv.DictReader(io.StringIO(r.text)))
            break
    if rows:
        break

rows = [{k.strip(): (v or "").strip() for k, v in x.items()} for x in rows]
res.check("EQUITY_L.csv downloaded", len(rows) > 1500, f"{len(rows)} securities")
if rows:
    log(f"  columns: {list(rows[0].keys())}")
    series = {}
    for x in rows:
        series[x["SERIES"]] = series.get(x["SERIES"], 0) + 1
    log(f"  series counts: {series}")
    by_sym = {x["SYMBOL"]: x for x in rows}
    for sym in DEMO:
        hit = by_sym.get(sym)
        res.check(f"{sym} in NSE list", bool(hit),
                  f"{hit['NAME OF COMPANY']} | {hit['SERIES']} | {hit['ISIN NUMBER']} | listed {hit['DATE OF LISTING']}"
                  if hit else "NOT FOUND")
    save_sample("e_equity_list_head.json", rows[:5])

res.finish()
