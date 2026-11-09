"""Source reachability probe, run from wherever the API is deployed (e.g. Render).

Answers: can this server reach NSE, BSE and screener? Results are cached for CACHE_TTL_S and
computed at most once at a time, so a public endpoint can't be used to hammer the sources.
"""

from __future__ import annotations

import threading
import time
from datetime import UTC, date, datetime, timedelta

import requests

CACHE_TTL_S = 15 * 60
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
FINN_UA = "FINN-research/0.1 (+https://github.com/ShlokN-code/finn)"
NSE_GAP_S = 2.5
# A known BSE attachment (RELIANCE, 06-Nov-2026) — screener's document links point to files like this.
BSE_PDF = "https://www.bseindia.com/xml-data/corpfiling/AttachLive/bab324f6-6fab-42fc-8b79-a3881f4fb7c7.pdf"

_lock = threading.Lock()
_cache: dict | None = None


def _probe(name: str, fn) -> dict:
    t0 = time.perf_counter()
    try:
        ok, status, detail = fn()
    except requests.RequestException as e:
        ok, status, detail = False, None, type(e).__name__
    return {"name": name, "ok": ok, "status": status, "ms": round((time.perf_counter() - t0) * 1000), "detail": detail}


def run_probes() -> dict:
    results: list[dict] = []
    fmt = "%d-%m-%Y"
    to_d, from_d = date.today(), date.today() - timedelta(days=7)

    def egress():
        r = requests.get("https://ipinfo.io/json", timeout=10)
        d = r.json()
        return r.ok, r.status_code, f"{d.get('country')} {d.get('region')} {d.get('org')}"

    results.append(_probe("egress", egress))

    nse = requests.Session()
    nse.headers.update(
        {
            "User-Agent": BROWSER_UA,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/",
        }
    )
    pdf_url: list[str] = []

    def nse_home():
        r = nse.get("https://www.nseindia.com/", headers={"Accept": "text/html"}, timeout=15)
        return r.ok and len(nse.cookies) > 0, r.status_code, f"cookies={sorted(nse.cookies.keys())}"

    def nse_announcements():
        time.sleep(NSE_GAP_S)
        r = nse.get(
            "https://www.nseindia.com/api/corporate-announcements",
            timeout=15,
            params={
                "index": "equities",
                "symbol": "RELIANCE",
                "from_date": from_d.strftime(fmt),
                "to_date": to_d.strftime(fmt),
            },
        )
        rows = r.json() if r.ok and "json" in r.headers.get("content-type", "") else []
        pdf_url.extend(x["attchmntFile"] for x in rows[:5] if x.get("attchmntFile"))
        return bool(r.ok and isinstance(rows, list)), r.status_code, f"{len(rows)} rows (7d)"

    def nse_corporate_actions():
        time.sleep(NSE_GAP_S)
        r = nse.get(
            "https://www.nseindia.com/api/corporates-corporateActions",
            timeout=15,
            params={"index": "equities", "symbol": "HDFCBANK"},
        )
        rows = r.json() if r.ok and "json" in r.headers.get("content-type", "") else []
        return bool(rows), r.status_code, f"{len(rows)} rows"

    def nse_pdf():
        if not pdf_url:
            return False, None, "no attachment URL (announcements failed or empty)"
        time.sleep(1.5)
        r = nse.get(pdf_url[0], timeout=20)
        return r.ok and r.content[:4] == b"%PDF", r.status_code, f"{len(r.content)} bytes"

    def nse_equity_list():
        time.sleep(1.5)
        r = nse.get("https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv", timeout=20)
        return r.ok and r.text.startswith("SYMBOL"), r.status_code, f"{r.text.count(chr(10))} lines"

    def bse_announcements():
        r = requests.get(
            "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w",
            timeout=15,
            headers={
                "User-Agent": BROWSER_UA,
                "Referer": "https://www.bseindia.com/",
                "Origin": "https://www.bseindia.com",
            },
            params={
                "pageno": 1,
                "strCat": -1,
                "strPrevDate": from_d.strftime("%Y%m%d"),
                "strScrip": "500325",
                "strSearch": "P",
                "strToDate": to_d.strftime("%Y%m%d"),
                "strType": "C",
                "subcategory": -1,
            },
        )
        rows = r.json().get("Table", []) if r.ok and "json" in r.headers.get("content-type", "") else []
        return bool(r.ok and "json" in r.headers.get("content-type", "")), r.status_code, f"{len(rows)} rows (7d)"

    def bse_pdf():
        r = requests.get(
            BSE_PDF, timeout=20, headers={"User-Agent": BROWSER_UA, "Referer": "https://www.bseindia.com/"}
        )
        return r.ok and r.content[:4] == b"%PDF", r.status_code, f"{len(r.content)} bytes"

    def screener():
        r = requests.get(
            "https://www.screener.in/company/INFY/consolidated/", timeout=20, headers={"User-Agent": FINN_UA}
        )
        return r.ok and 'id="quarters"' in r.text, r.status_code, f"{len(r.content)} bytes"

    for name, fn in [
        ("nse_homepage_warmup", nse_home),
        ("nse_announcements", nse_announcements),
        ("nse_corporate_actions", nse_corporate_actions),
        ("nse_attachment_pdf", nse_pdf),
        ("nse_equity_list", nse_equity_list),
        ("bse_announcements", bse_announcements),
        ("bse_attachment_pdf", bse_pdf),
        ("screener_company_page", screener),
    ]:
        results.append(_probe(name, fn))

    return {"checked_at": datetime.now(UTC).isoformat(), "probes": results}


def get_probes(now: float | None = None) -> dict:
    """Cached results; recomputes at most once per CACHE_TTL_S, one caller at a time."""
    global _cache
    now = time.time() if now is None else now
    with _lock:
        if _cache is None or now - _cache["_ts"] > CACHE_TTL_S:
            _cache = {"_ts": now, **run_probes()}
        out = {k: v for k, v in _cache.items() if k != "_ts"}
        out["cache_age_s"] = round(now - _cache["_ts"])
        return out
