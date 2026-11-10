"""BSE announcements — parser only. BSE's APIs return 403 to GitHub runners and Render, so BSE is not wired
into scheduled jobs (DECISIONS.md); this exists so NSE↔BSE dedup is built and tested for local/backup use.
"""

from __future__ import annotations

from datetime import UTC, datetime

from finn.calendar import IST
from finn.models import Filing

ATTACH_BASE = "https://www.bseindia.com/xml-data/corpfiling/AttachLive/"


def _bse_time(text: str) -> datetime:
    # '2026-10-30T19:42:49.917' (IST, variable fractional digits)
    base = text.split(".")[0]
    return datetime.strptime(base, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=IST).astimezone(UTC)


def announcement_to_filing(row: dict, symbol: str, isin: str | None = None) -> Filing:
    """BSE row → Filing. `symbol` is the NSE symbol (canonical key) the caller queried by BSE code."""
    subject = (row.get("NEWSSUB") or row.get("HEADLINE") or "").strip()
    category = " / ".join(x for x in (row.get("CATEGORYNAME"), row.get("SUBCATNAME")) if x)
    attachment = row.get("ATTACHMENTNAME")
    return Filing(
        id=f"BSE:{row['NEWSID']}",
        exchange="BSE",
        exchange_id=str(row["NEWSID"]),
        symbol=symbol,
        isin=isin,
        bse_code=str(row.get("SCRIP_CD") or "") or None,
        filed_at=_bse_time(row.get("DissemDT") or row["NEWS_DT"]),
        exchange_category=category,
        subject=subject,
        attachment_url=ATTACH_BASE + attachment if attachment else None,
    )


def attachment_bytes(row: dict) -> int | None:
    v = row.get("Fld_Attachsize")
    return int(v) if isinstance(v, int | float) and v > 0 else None
