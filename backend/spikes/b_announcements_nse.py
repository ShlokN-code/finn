"""Spike (b1): NSE corporate announcements.

Questions:
- Does the homepage cookie warm-up still work? Which cookies?
- Which announcement endpoint works now; what fields; are attachment PDFs fetchable?
- Any blocking / rate limiting?
"""

from __future__ import annotations

from datetime import date, timedelta

from _common import Result, log, nse_session, polite_get, save_sample

SYMBOLS = ["RELIANCE", "HDFCBANK", "INFY"]
API = "https://www.nseindia.com/api"

res = Result("b_announcements_nse")
s = nse_session()
res.check("NSE homepage warm-up sets cookies", len(s.cookies) > 0, ",".join(sorted(s.cookies.keys())))

to_d = date.today()
from_d = to_d - timedelta(days=30)
fmt = "%d-%m-%Y"

first_pdf = None
for sym in SYMBOLS:
    log(f"\n--- {sym} ---")
    candidates = [
        ("corporate-announcements (30d window)", f"{API}/corporate-announcements",
         {"index": "equities", "symbol": sym, "from_date": from_d.strftime(fmt), "to_date": to_d.strftime(fmt)}),
        ("corporate-announcements (no dates)", f"{API}/corporate-announcements",
         {"index": "equities", "symbol": sym}),
    ]
    for label, url, params in candidates:
        r = polite_get(s, url, params=params, use_cache=False)
        ctype = r.headers.get("content-type", "")
        ok = r.ok and "json" in ctype
        detail = f"HTTP {r.status_code}, {ctype.split(';')[0]}, {len(r.content)} bytes"
        if ok:
            data = r.json()
            rows = data if isinstance(data, list) else data.get("data", [])
            detail += f", {len(rows)} rows"
            if rows:
                log(f"  fields: {sorted(rows[0].keys())}")
                for row in rows[:5]:
                    log(f"    {row.get('an_dt') or row.get('sort_date')} | {row.get('desc')} | "
                        f"{(row.get('attchmntText') or '')[:90]!r} | {row.get('attchmntFile')}")
                save_sample(f"b_nse_ann_{sym}.json", rows[:10])
                first_pdf = first_pdf or next((x.get("attchmntFile") for x in rows if x.get("attchmntFile")), None)
        res.check(f"{sym}: {label}", ok and bool(rows) if ok else False, detail)

# Attachment fetch
if first_pdf:
    log(f"\n--- attachment: {first_pdf}")
    r = polite_get(s, first_pdf, headers={"Accept": "application/pdf,*/*"})
    is_pdf = r.content[:4] == b"%PDF"
    res.check("attachment PDF downloadable", r.ok and is_pdf,
              f"HTTP {r.status_code}, {len(r.content)} bytes, magic={r.content[:4]!r}")
    # without cookies?
    import requests
    r2 = requests.get(first_pdf, headers={"User-Agent": "FINN-research/0.1"}, timeout=20)
    log(f"  same PDF with plain session, FINN UA, no cookies: HTTP {r2.status_code}, magic={r2.content[:4]!r}")
else:
    res.check("attachment PDF downloadable", False, "no attachment URL found")

# Rate-limit probe: 5 quick calls (still >= 2.5s apart via throttle) — observe any 403/429.
log("\n--- repeat calls ---")
codes = []
for _ in range(5):
    r = polite_get(s, f"{API}/corporate-announcements",
                   params={"index": "equities", "symbol": "INFY",
                           "from_date": from_d.strftime(fmt), "to_date": to_d.strftime(fmt)},
                   use_cache=False, retries=1)
    codes.append(r.status_code)
res.check("5 repeat calls at 2.5s spacing not blocked", all(c == 200 for c in codes), str(codes))

res.finish()
