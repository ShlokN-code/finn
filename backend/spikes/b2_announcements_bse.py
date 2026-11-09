"""Spike (b2): BSE corporate announcements.

Questions:
- Can we map NSE symbol -> BSE scrip code (via ISIN) from BSE's scrip list?
- Does the announcements API work; what fields; are attachment PDFs fetchable?
"""

from __future__ import annotations

from datetime import date, timedelta

from _common import Result, bse_session, log, polite_get, save_sample

SYMBOLS = {"RELIANCE": "INE002A01018", "HDFCBANK": "INE040A01034", "INFY": "INE009A01021"}  # ISINs
API = "https://api.bseindia.com/BseIndiaAPI/api"

res = Result("b2_announcements_bse")
s = bse_session()

# 1) Scrip master: map ISIN -> scrip code
r = polite_get(s, f"{API}/ListofScripData/w",
               params={"Group": "", "Scripcode": "", "industry": "", "segment": "Equity", "status": "Active"})
scrips = []
if r.ok and "json" in r.headers.get("content-type", ""):
    scrips = r.json()
res.check("BSE scrip master (ListofScripData)", len(scrips) > 1000,
          f"HTTP {r.status_code}, {len(scrips)} active equity scrips")
codes: dict[str, str] = {}
if scrips:
    log(f"  scrip fields: {sorted(scrips[0].keys())}")
    by_isin = {x.get("ISIN_NUMBER"): x for x in scrips}
    for sym, isin in SYMBOLS.items():
        hit = by_isin.get(isin)
        if hit:
            codes[sym] = str(hit["SCRIP_CD"])
            log(f"  {sym} ({isin}) -> {hit['SCRIP_CD']} / {hit.get('scrip_id')} / {hit.get('Scrip_Name')}")
        res.check(f"{sym} resolves to BSE scrip code via ISIN", bool(hit))
    save_sample("b2_bse_scrips_head.json", scrips[:5])
else:
    # Scrip master is 403 from GitHub runners — still test the announcements API with known codes.
    codes = {"RELIANCE": "500325", "HDFCBANK": "500180", "INFY": "500209"}
    log("  scrip master unavailable; using known scrip codes to test announcements")

# 2) Announcements
to_d, from_d = date.today(), date.today() - timedelta(days=30)
first_att = None
for sym, code in codes.items():
    r = polite_get(s, f"{API}/AnnSubCategoryGetData/w", use_cache=False, params={
        "pageno": 1, "strCat": -1, "strPrevDate": from_d.strftime("%Y%m%d"), "strScrip": code,
        "strSearch": "P", "strToDate": to_d.strftime("%Y%m%d"), "strType": "C", "subcategory": -1,
    })
    rows = []
    if r.ok and "json" in r.headers.get("content-type", ""):
        body = r.json()
        rows = body.get("Table", [])
        if rows:
            log(f"\n--- {sym} ({code}) fields: {sorted(rows[0].keys())}")
            for x in rows[:5]:
                log(f"    {x.get('NEWS_DT')} | {x.get('CATEGORYNAME')} / {x.get('SUBCATNAME')} | "
                    f"{(x.get('NEWSSUB') or '')[:80]!r} | {x.get('ATTACHMENTNAME')}")
            save_sample(f"b2_bse_ann_{sym}.json", rows[:10])
            first_att = first_att or next((x["ATTACHMENTNAME"] for x in rows if x.get("ATTACHMENTNAME")), None)
            log(f"  Table1 (paging): {body.get('Table1')}")
    res.check(f"{sym}: AnnSubCategoryGetData 30d", bool(rows),
              f"HTTP {r.status_code}, {r.headers.get('content-type', '').split(';')[0]}, {len(rows)} rows")

# 3) Attachment
if first_att:
    for base in ("https://www.bseindia.com/xml-data/corpfiling/AttachLive/",
                 "https://www.bseindia.com/xml-data/corpfiling/AttachHis/"):
        r = polite_get(s, base + first_att, headers={"Accept": "application/pdf,*/*"})
        ok = r.ok and r.content[:4] == b"%PDF"
        log(f"  {base}{first_att}: HTTP {r.status_code}, {len(r.content)} bytes, pdf={ok}")
        if ok:
            break
    res.check("BSE attachment PDF downloadable", ok)
else:
    res.check("BSE attachment PDF downloadable", False, "no attachment found")

res.finish()
