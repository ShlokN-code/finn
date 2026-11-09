"""Spike (a2): verify demo tickers resolve on Yahoo (.NS) and flag renames/demergers/splits.

Sources: yfinance (resolves? fresh?), NSE equity list (name/ISIN/series), NSE corporate actions
(demerger / bonus / split / scheme of arrangement in the last ~3 years).
"""

from __future__ import annotations

import csv
import io
import re
import time
from datetime import date, datetime, timedelta

import yfinance as yf

from _common import Result, log, nse_session, polite_get, save_sample

PORTFOLIO = ["HAL", "EICHERMOT", "GRASIM", "TATAPOWER", "ALKEM", "KALYANKJIL", "COCHINSHIP", "TITAGARH",
             "IDEA", "RELIANCE", "HDFCBANK", "BAJFINANCE", "INFY", "ITC", "DIVISLAB", "TATASTEEL",
             "JUBLFOOD", "DIXON"]
RESEARCH = ["BAJFINANCE", "INFY", "PERSISTENT", "POLYCAB"]
ALL = list(dict.fromkeys(PORTFOLIO + RESEARCH))
FLAG_RE = re.compile(r"demerg|amalgam|scheme of arrangement|bonus|split|sub-division|consolidation|"
                     r"rights|buy ?back|capital reduction", re.I)

res = Result("a2_verify_portfolio")

log("--- Yahoo (1mo, chunks of 5, one retry pass for failures) ---")
# Yahoo rate-limits bursts (YFRateLimitError seen on repeated runs) — keep requests small and spaced.
yahoo: dict[str, dict] = {}


def fetch(tickers: list[str]) -> None:
    for i in range(0, len(tickers), 5):
        chunk = tickers[i:i + 5]
        df = yf.download([f"{t}.NS" for t in chunk], period="1mo", auto_adjust=False, group_by="ticker",
                         progress=False, threads=False)
        for t in chunk:
            try:
                sub = df[f"{t}.NS"].dropna(how="all")
            except KeyError:
                sub = []
            if len(sub):
                yahoo[t] = {"rows": len(sub), "last_date": str(sub.index.max().date()),
                            "last_close": round(float(sub["Close"].iloc[-1]), 2)}
        time.sleep(3)


fetch(ALL)
missing = [t for t in ALL if t not in yahoo]
if missing:
    log(f"  retrying after 30s: {missing}")
    time.sleep(30)
    fetch(missing)
for t in ALL:
    yahoo.setdefault(t, {"rows": 0, "last_date": None, "last_close": None})

s = nse_session()
# Names/ISINs from the NSE equity list. (quote-equity API returns 403 to scripts — see DATA_SOURCES.md.)
_r = polite_get(s, "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv")
equity_list = {row["SYMBOL"]: {k.strip(): v.strip() for k, v in row.items()}
               for row in csv.DictReader(io.StringIO(_r.text))} if _r.ok else {}
cutoff = date.today() - timedelta(days=3 * 365)
report = {}
for t in ALL:
    y = yahoo[t]
    fresh = bool(y["last_date"]) and (date.today() - date.fromisoformat(y["last_date"])).days <= 5
    res.check(f"{t}.NS resolves on Yahoo with fresh data", fresh,
              f"{y['rows']} rows, last {y['last_date']} close {y['last_close']}")

    eq = equity_list.get(t, {})
    ca = polite_get(s, "https://www.nseindia.com/api/corporates-corporateActions",
                    params={"index": "equities", "symbol": t}, use_cache=False)
    actions = ca.json() if ca.ok and "json" in ca.headers.get("content-type", "") else []
    flags = []
    for a in actions if isinstance(actions, list) else []:
        try:
            ex = datetime.strptime(a.get("exDate", ""), "%d-%b-%Y").date()
        except ValueError:
            continue
        if ex >= cutoff and FLAG_RE.search(a.get("subject", "")):
            flags.append(f"{a['exDate']}: {a['subject'].strip()}")
    report[t] = {"yahoo": y, "nse_name": eq.get("NAME OF COMPANY"), "isin": eq.get("ISIN NUMBER"),
                 "series": eq.get("SERIES"), "flags": flags}
    log(f"    NSE: {eq.get('NAME OF COMPANY')} | {eq.get('SERIES')} | {eq.get('ISIN NUMBER')} | flags: {flags or '-'}")

save_sample("a2_portfolio_report.json", report)
res.finish()
