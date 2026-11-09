"""Spike (d): screener.in company page.

robots.txt (checked 2026-11-10) allows /company/<SYM>/consolidated/; disallows
/company/source/quarter/* — we do not follow those links.

Questions:
- Can we fetch and parse the page with a plain, identifying User-Agent?
- Documents: annual report links, concall transcripts / PPT / recordings.
- Tables: quarterly results, P&L, balance sheet, cash flow, ratios — shape and units.
"""

from __future__ import annotations

import sys

from bs4 import BeautifulSoup

from _common import Result, finn_session, log, polite_get, save_sample

SYM = sys.argv[1] if len(sys.argv) > 1 else "BAJFINANCE"
URL = f"https://www.screener.in/company/{SYM}/consolidated/"

res = Result("d_screener")
s = finn_session()
r = polite_get(s, URL)
res.check("company page fetch", r.ok, f"HTTP {r.status_code}, {len(r.content)} bytes, cached={r.from_cache}")
soup = BeautifulSoup(r.text, "lxml")

name = soup.select_one("h1")
log(f"  company: {name.get_text(strip=True) if name else '?'}")
info = soup.select_one("[data-company-id]")
log(f"  data-company-id={info.get('data-company-id') if info else None} "
    f"data-warehouse-id={info.get('data-warehouse-id') if info else None}")


def parse_table(section_id: str) -> dict | None:
    sec = soup.select_one(f"section#{section_id}")
    if not sec:
        return None
    unit_note = sec.select_one("p.sub")
    table = sec.select_one("table.data-table")
    if not table:
        return None
    headers = [th.get_text(strip=True) for th in table.select("thead th")]
    rows = []
    for tr in table.select("tbody tr"):
        cells = [td.get_text(" ", strip=True) for td in tr.select("td")]
        if cells:
            rows.append({"label": cells[0].replace("\xa0", " ").rstrip(" +"), "values": cells[1:]})
    return {"unit_note": unit_note.get_text(" ", strip=True) if unit_note else None,
            "periods": headers[1:], "rows": rows}


tables = {}
for sec in ("quarters", "profit-loss", "balance-sheet", "cash-flow", "ratios", "shareholding"):
    t = parse_table(sec)
    ok = bool(t and t["rows"])
    res.check(f"table #{sec}", ok,
              f"{len(t['periods'])} periods ({t['periods'][0]} … {t['periods'][-1]}), {len(t['rows'])} rows"
              if ok else "missing")
    if ok:
        tables[sec] = t
        log(f"    unit: {t['unit_note']!r}")
        log(f"    rows: {[x['label'] for x in t['rows']]}")
save_sample(f"d_screener_{SYM}_tables.json", tables)

# Documents
docs = soup.select_one("section#documents")
ann_reports, concalls = [], []
if docs:
    ar = docs.select_one(".annual-reports")
    if ar:
        for a in ar.select("a[href]"):
            ann_reports.append({"text": a.get_text(" ", strip=True), "href": a["href"]})
    cc = docs.select_one(".concalls")
    if cc:
        for li in cc.select("li"):
            period = li.select_one(".ink-600, div")
            links = [{"kind": a.get_text(strip=True), "href": a.get("href")} for a in li.select("a")]
            btns = [b.get_text(strip=True) for b in li.select("button")]  # e.g. AI summary (login-gated)
            concalls.append({"period": period.get_text(" ", strip=True) if period else None,
                             "links": links, "buttons": btns})
res.check("annual report links", bool(ann_reports), f"{len(ann_reports)} links")
for x in ann_reports[:4]:
    log(f"    {x['text']!r} -> {x['href']}")
res.check("concall entries", bool(concalls), f"{len(concalls)} quarters")
for x in concalls[:4]:
    log(f"    {x['period']!r}: {[(l['kind'], l['href']) for l in x['links']]}")
n_transcripts = sum(1 for c in concalls for l in c["links"] if l["kind"].lower().startswith("transcript"))
res.check("concall transcript links present", n_transcripts > 0, f"{n_transcripts} transcripts")
save_sample(f"d_screener_{SYM}_documents.json", {"annual_reports": ann_reports, "concalls": concalls})

# Where do document links point? (exchange vs company site vs screener)
hosts: dict[str, int] = {}
from urllib.parse import urlparse
for x in ann_reports + [l for c in concalls for l in c["links"]]:
    h = urlparse(x["href"] or "").netloc or "(relative)"
    hosts[h] = hosts.get(h, 0) + 1
log(f"  document link hosts: {hosts}")

# Can we fetch a transcript that screener links to? (Most point to BSE; BSE may block datacenter IPs.)
from _common import bse_session  # noqa: E402

t_link = next((lk["href"] for c in concalls for lk in c["links"] if lk["kind"].lower().startswith("transcript")
               and "bseindia.com" in (lk["href"] or "")), None)
if t_link:
    pr = polite_get(bse_session(), t_link, headers={"Accept": "application/pdf,*/*"})
    res.check("screener-linked BSE transcript PDF downloads", pr.ok and pr.content[:4] == b"%PDF",
              f"HTTP {pr.status_code}, {len(pr.content)} bytes ({t_link[:70]}...)")

res.finish()
