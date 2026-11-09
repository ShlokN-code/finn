"""Spike (c): NSE event calendar, board meetings, corporate actions, bulk/block deals,
plus NSE raw (unadjusted) historical prices to cross-check Yahoo's adjustment.
"""

from __future__ import annotations

import csv
import io
from datetime import date, timedelta

from _common import Result, log, nse_session, polite_get, save_sample

API = "https://www.nseindia.com/api"
SYM = "HDFCBANK"
fmt = "%d-%m-%Y"
today = date.today()

res = Result("c_calendar_deals")
s = nse_session()


def probe(label: str, url: str, params: dict | None = None, list_key: str | None = None, show=None):
    r = polite_get(s, url, params=params, use_cache=False)
    ctype = r.headers.get("content-type", "").split(";")[0]
    rows: list = []
    if r.ok and "json" in ctype:
        body = r.json()
        rows = body if isinstance(body, list) else body.get(list_key or "data", []) or []
    ok = bool(rows)
    res.check(label, ok, f"HTTP {r.status_code}, {ctype}, {len(rows)} rows")
    if rows:
        log(f"    fields: {sorted(rows[0].keys())}")
        for x in rows[:4]:
            log(f"    {show(x) if show else x}")
    return rows


# Event calendar (forthcoming board meetings, all companies / one company)
ev = probe("event-calendar (all, next 30d)", f"{API}/event-calendar",
           {"index": "equities", "from_date": today.strftime(fmt),
            "to_date": (today + timedelta(days=30)).strftime(fmt)},
           show=lambda x: f"{x.get('date')} | {x.get('symbol')} | {x.get('purpose')} | {(x.get('bm_desc') or '')[:70]}")
save_sample("c_event_calendar.json", ev[:10])

bm = probe(f"corporate-board-meetings ({SYM})", f"{API}/corporate-board-meetings",
           {"index": "equities", "symbol": SYM},
           show=lambda x: f"{x.get('bm_date')} | {x.get('bm_purpose')} | {x.get('attachment')}")
save_sample("c_board_meetings.json", bm[:5])

ca = probe(f"corporates-corporateActions ({SYM})", f"{API}/corporates-corporateActions",
           {"index": "equities", "symbol": SYM},
           show=lambda x: f"ex {x.get('exDate')} | rec {x.get('recDate')} | {x.get('subject')}")
save_sample("c_corporate_actions_HDFCBANK.json", ca[:10])

ca2 = probe("corporates-corporateActions (BAJFINANCE)", f"{API}/corporates-corporateActions",
            {"index": "equities", "symbol": "BAJFINANCE"},
            show=lambda x: f"ex {x.get('exDate')} | rec {x.get('recDate')} | {x.get('subject')}")
save_sample("c_corporate_actions_BAJFINANCE.json", ca2[:10])

# Bulk / block deals — historical API
frm, to = (today - timedelta(days=30)).strftime(fmt), today.strftime(fmt)
for kind in ("bulk_deals", "block_deals"):
    rows = probe(f"historicalOR/bulk-block-short-deals ({kind}, 30d)",
                 f"{API}/historicalOR/bulk-block-short-deals",
                 {"optionType": kind, "from": frm, "to": to},
                 show=lambda x: f"{x.get('BD_DT_DATE')} | {x.get('BD_SYMBOL')} | {x.get('BD_CLIENT_NAME')} | "
                                f"{x.get('BD_BUY_SELL')} {x.get('BD_QTY_TRD')} @ {x.get('BD_TP_WATP')}")
    save_sample(f"c_{kind}.json", rows[:10])

# Bulk / block deals — daily archive CSVs (fallback)
for name in ("bulk", "block"):
    url = f"https://nsearchives.nseindia.com/content/equities/{name}.csv"
    r = polite_get(s, url, use_cache=False)
    rows = list(csv.DictReader(io.StringIO(r.text))) if r.ok else []
    res.check(f"archive {name}.csv (latest session)", r.ok, f"HTTP {r.status_code}, {len(rows)} rows")
    if rows:
        log(f"    columns: {list(rows[0].keys())}")
        log(f"    {rows[0]}")

# Raw historical prices from NSE — is Yahoo's Close adjusted? HDFCBANK 1:1 bonus, ex 26-Aug-2025.
r = polite_get(s, f"{API}/historicalOR/generateSecurityWiseHistoricalData", use_cache=False, params={
    "from": "20-08-2025", "to": "29-08-2025", "symbol": SYM, "type": "priceVolumeDeliverable", "series": "EQ"})
rows = r.json().get("data", []) if r.ok and "json" in r.headers.get("content-type", "") else []
res.check("NSE raw historical prices (priceVolumeDeliverable)", bool(rows),
          f"HTTP {r.status_code}, {len(rows)} rows")
for x in rows:
    log(f"    {x.get('mTIMESTAMP') or x.get('CH_TIMESTAMP')} close={x.get('CH_CLOSING_PRICE')} "
        f"vol={x.get('CH_TOT_TRADED_QTY')} deliv%={x.get('COP_DELIV_PERC')}")
if rows:
    log(f"    fields: {sorted(rows[0].keys())}")
    save_sample("c_nse_raw_prices_HDFCBANK_bonus.json", rows)

res.finish()
