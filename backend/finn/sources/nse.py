"""NSE adapters: announcements, corporate actions, bulk/block deals, holidays, equity list.

Only GitHub Actions runners and dev machines may call these — NSE blocks Render (DATA_SOURCES.md).
Every function returns parsed rows plus the raw dicts (kept in the DB for audit/re-parsing).
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from finn.calendar import parse_ist
from finn.models import Filing
from finn.numbers import deal_value_cr
from finn.sources.http import NSESession, get_json, polite_get

API = "https://www.nseindia.com/api"
DMY = "%d-%m-%Y"


def session() -> NSESession:
    s = NSESession()
    s.warm()
    return s


def _get(s: NSESession, path: str, params: dict, ttl: float | None = 0):
    s.ensure_warm()
    return get_json(s, f"{API}/{path}", params=params, ttl=ttl, on_auth_error=s.warm)


# --- announcements ----------------------------------------------------------------------------


def fetch_announcements(s: NSESession, symbol: str, frm: date, to: date) -> list[dict]:
    """Corporate announcements for one symbol in [frm, to] (IST dates). Always windowed: without dates the
    API returns the full history (RELIANCE: 3,382 rows)."""
    data = _get(
        s,
        "corporate-announcements",
        {"index": "equities", "symbol": symbol, "from_date": frm.strftime(DMY), "to_date": to.strftime(DMY)},
    )
    rows = data if isinstance(data, list) else data.get("data", [])
    return [r for r in rows if isinstance(r, dict)]


def announcement_to_filing(row: dict, fetched_at: datetime | None = None) -> Filing:
    stamp = row.get("exchdisstime") or row.get("an_dt")
    filed_at = parse_ist(stamp, "%d-%b-%Y %H:%M:%S") if stamp else parse_ist(row["sort_date"], "%Y-%m-%d %H:%M:%S")
    return Filing(
        id=f"NSE:{row['seq_id']}",
        exchange="NSE",
        exchange_id=str(row["seq_id"]),
        symbol=row["symbol"].strip().upper(),
        isin=row.get("sm_isin") or None,
        filed_at=filed_at,
        exchange_category=(row.get("desc") or "").strip(),
        subject=clean_subject(row.get("attchmntText") or ""),
        attachment_url=row.get("attchmntFile") or None,
        fetched_at=fetched_at or datetime.now(UTC),
    )


_BOILER = re.compile(
    r"^.{0,120}?has (?:informed|submitted to|submitted) the Exchange (?:a copy of |about |regarding )?", re.I
)


def clean_subject(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def subject_core(subject: str) -> str:
    """Strip NSE boilerplate ('X Limited has informed the Exchange regarding ...') → the informative part."""
    core = _BOILER.sub("", subject).strip().rstrip(".").strip().strip("'\"‘’“”").strip()
    return core or subject


# --- corporate actions ------------------------------------------------------------------------


def fetch_corporate_actions(s: NSESession, symbol: str) -> list[dict]:
    data = _get(s, "corporates-corporateActions", {"index": "equities", "symbol": symbol})
    rows = data if isinstance(data, list) else data.get("data", [])
    return [r for r in rows if isinstance(r, dict)]


@dataclass
class CorporateAction:
    symbol: str
    ex_date: date
    record_date: date | None
    subject: str
    kind: str  # dividend | bonus | split | rights | buyback | demerger | other
    ratio_new: float | None = None
    ratio_held: float | None = None
    amount_per_share: float | None = None
    face_value: str | None = None


def _d(text: str | None) -> date | None:
    if not text or text.strip() in ("-", ""):
        return None
    for fmt in ("%d-%b-%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    return None


_RS = r"(?:Rs\.?|Re\.?|₹)\s*"


def parse_action_subject(subject: str) -> dict:
    """'Bonus 4:1' → bonus 4 new per 1 held; 'Face Value Split (Sub-Division) - From Rs 2/- Per Share To Re 1/-
    Per Share' → split 2:1; 'Dividend - Rs 19.50 Per Share' → dividend ₹19.50. Unknown → kind 'other'."""
    s = re.sub(r"\s+", " ", subject).strip()
    low = s.lower()
    if "bonus" in low and (m := re.search(r"(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)", s)):
        return {"kind": "bonus", "ratio_new": float(m.group(1)), "ratio_held": float(m.group(2))}
    if "split" in low or "sub-division" in low:
        m = re.search(rf"From {_RS}(\d+(?:\.\d+)?).*?To {_RS}(\d+(?:\.\d+)?)", s, re.I)
        if m:
            old, new = float(m.group(1)), float(m.group(2))
            return {"kind": "split", "ratio_new": old / new, "ratio_held": 1.0}
        return {"kind": "split"}
    if "dividend" in low:
        m = re.search(rf"{_RS}(\d+(?:\.\d+)?)", s, re.I)
        return {"kind": "dividend", "amount_per_share": float(m.group(1)) if m else None}
    if "rights" in low:
        m = re.search(r"(\d+)\s*:\s*(\d+)", s)
        return {"kind": "rights", **({"ratio_new": float(m.group(1)), "ratio_held": float(m.group(2))} if m else {})}
    if "buy back" in low or "buyback" in low:
        return {"kind": "buyback"}
    if "demerger" in low or "scheme of arrangement" in low:
        return {"kind": "demerger"}
    return {"kind": "other"}


def to_corporate_action(row: dict) -> CorporateAction | None:
    ex = _d(row.get("exDate"))
    if ex is None:
        return None
    subject = re.sub(r"\s+", " ", row.get("subject") or "").strip()
    return CorporateAction(
        symbol=row["symbol"].strip().upper(),
        ex_date=ex,
        record_date=_d(row.get("recDate")),
        subject=subject,
        face_value=row.get("faceVal"),
        **parse_action_subject(subject),
    )


# --- bulk / block deals -----------------------------------------------------------------------


@dataclass
class Deal:
    id: str
    date: date
    symbol: str
    kind: str  # bulk | block
    client: str
    side: str
    quantity: int
    price: float
    value_cr: float
    remarks: str | None
    raw: dict


def _deal_id(kind: str, d: date, symbol: str, client: str, side: str, qty: int, price: float) -> str:
    return hashlib.sha256(json.dumps([kind, d.isoformat(), symbol, client, side, qty, price]).encode()).hexdigest()[:24]


def _mk_deal(kind: str, d: date, symbol: str, client: str, side: str, qty, price, remarks, raw) -> Deal:
    qty_i, px = int(float(str(qty).replace(",", ""))), float(str(price).replace(",", ""))
    side = side.strip().upper()
    return Deal(
        _deal_id(kind, d, symbol, client, side, qty_i, px),
        d,
        symbol.strip().upper(),
        kind,
        client.strip(),
        side,
        qty_i,
        px,
        deal_value_cr(qty_i, px),
        (remarks or "").strip() or None,
        raw,
    )


def fetch_deals(s: NSESession, kind: str, frm: date, to: date) -> list[Deal]:
    """Market-wide bulk or block deals in [frm, to]. kind: 'bulk' | 'block'."""
    data = _get(
        s,
        "historicalOR/bulk-block-short-deals",
        {"optionType": f"{kind}_deals", "from": frm.strftime(DMY), "to": to.strftime(DMY)},
    )
    rows = data if isinstance(data, list) else data.get("data", [])
    out = []
    for r in rows:
        d = _d(r.get("BD_DT_DATE"))
        if d is None or not r.get("BD_SYMBOL"):
            continue
        out.append(
            _mk_deal(
                kind,
                d,
                r["BD_SYMBOL"],
                r.get("BD_CLIENT_NAME") or "",
                r.get("BD_BUY_SELL") or "",
                r.get("BD_QTY_TRD") or 0,
                r.get("BD_TP_WATP") or 0,
                r.get("BD_REMARKS"),
                r,
            )
        )
    return out


def fetch_deals_archive(s: NSESession, kind: str) -> list[Deal]:
    """Fallback: latest session's deals from nsearchives (bulk.csv / block.csv)."""
    r = polite_get(s, f"https://nsearchives.nseindia.com/content/equities/{kind}.csv", ttl=0)
    if not r.ok:
        return []
    out = []
    for row in csv.DictReader(io.StringIO(r.text)):
        row = {k.strip(): (v or "").strip() for k, v in row.items() if k}
        d = _d(row.get("Date"))
        if d is None or not row.get("Symbol"):
            continue
        out.append(
            _mk_deal(
                kind,
                d,
                row["Symbol"],
                row.get("Client Name", ""),
                row.get("Buy/Sell", ""),
                row.get("Quantity Traded", "0"),
                row.get("Trade Price / Wght. Avg. Price", "0"),
                row.get("Remarks"),
                row,
            )
        )
    return out


# --- holidays & equity list -------------------------------------------------------------------


def fetch_holidays(s: NSESession) -> list[tuple[date, str]]:
    data = _get(s, "holiday-master", {"type": "trading"}, ttl=86400)
    out = []
    for r in data.get("CM", []):
        d = _d(r.get("tradingDate"))
        if d:
            out.append((d, (r.get("description") or "").strip()))
    return out


def fetch_equity_list(s: NSESession) -> list[dict]:
    """EQUITY_L.csv → [{symbol, name, series, isin}]. Needs the warmed session (plain UA hangs)."""
    s.ensure_warm()
    r = polite_get(s, "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv", ttl=86400)
    if not r.ok:
        return []
    out = []
    for row in csv.DictReader(io.StringIO(r.text)):
        row = {k.strip(): (v or "").strip() for k, v in row.items() if k}
        out.append(
            {
                "symbol": row.get("SYMBOL"),
                "name": row.get("NAME OF COMPANY"),
                "series": row.get("SERIES"),
                "isin": row.get("ISIN NUMBER"),
            }
        )
    return out


def default_window(today: date, days: int) -> tuple[date, date]:
    return today - timedelta(days=days), today
