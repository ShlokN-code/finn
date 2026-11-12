"""SEBI `in-capmkt` XBRL results instances → plain facts.

An instance carries one quarter (context like `OneD`) and the year-to-date (`FourD`), values in rupees.
We keep every top-level fact (no dimension members), so new metrics need no re-download.
"""

from __future__ import annotations

import gzip
from dataclasses import dataclass
from datetime import date, datetime

from lxml import etree

XBRLI = "http://www.xbrl.org/2003/instance"
XBRLDI = "http://xbrl.org/2006/xbrldi"
META_KEYS = (
    "NatureOfReportStandaloneConsolidated", "LevelOfRounding", "Symbol", "DescriptionOfPresentationCurrency",
    "TypeOfReportingPeriod", "WhetherResultsAreAuditedOrUnaudited", "NameOfTheCompany", "DateOfStartOfReportingPeriod",
    "DateOfEndOfReportingPeriod", "ReportingQuarter",
)  # fmt: skip


def parse_instance(xml: bytes) -> dict:
    """→ {"meta": {...}, "facts": {name: [{"ctx", "start", "end", "value", "decimals"}]}} (values in ₹)."""
    parser = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False)
    root = etree.fromstring(xml, parser)
    ctx: dict[str, dict] = {}
    for c in root.iter(f"{{{XBRLI}}}context"):
        p = c.find(f"{{{XBRLI}}}period")
        if p is None:
            continue
        start = p.findtext(f"{{{XBRLI}}}startDate")
        end = p.findtext(f"{{{XBRLI}}}endDate") or p.findtext(f"{{{XBRLI}}}instant")
        dims = [m.text for m in c.iter(f"{{{XBRLDI}}}explicitMember")]
        ctx[c.get("id")] = {"start": start, "end": end, "dims": bool(dims)}
    facts: dict[str, list[dict]] = {}
    meta: dict[str, str] = {}
    for el in root:
        if not isinstance(el.tag, str):
            continue
        name = etree.QName(el).localname
        text = (el.text or "").strip()
        if name in META_KEYS and text:
            meta.setdefault(name, text)
        if name == "DescriptionOfOtherExpenses" and text:
            # itemised other expenses: the description sits in its own context next to an OtherExpenses value
            # (how ITC and RELIANCE tag excise duty)
            meta.setdefault("other_expense_items", {})[el.get("contextRef") or ""] = text
        c = ctx.get(el.get("contextRef") or "")
        if not c or el.get("unitRef") is None:
            continue
        if c["dims"]:
            if name != "OtherExpenses":
                continue
            name = "OtherExpensesItem"  # an itemised other expense (its description is in meta), not the total
        try:
            value = float(text)
        except ValueError:
            continue
        facts.setdefault(name, []).append(
            {"ctx": el.get("contextRef"), "start": c["start"], "end": c["end"], "value": value,
             "decimals": el.get("decimals"), "unit": el.get("unitRef")}
        )  # fmt: skip
    return {"meta": meta, "facts": facts}


def gz(xml: bytes) -> bytes:
    return gzip.compress(xml, 9)


def gunzip(b: bytes) -> bytes:
    return gzip.decompress(b)


def _d(s: str | None) -> date | None:
    return datetime.strptime(s[:10], "%Y-%m-%d").date() if s else None


def quarter_value(facts: dict, name: str, quarter_end: date) -> tuple[float, dict] | None:
    """The fact for the three months ending `quarter_end` (≈ 89–92 days), in ₹. None if absent."""
    for f in facts.get(name, []):
        s, e = _d(f.get("start")), _d(f.get("end"))
        if s and e == quarter_end and 80 <= (e - s).days <= 95:
            return f["value"], f
    return None


@dataclass
class ResultsFilingRef:
    """One row of NSE's integrated-filing list: which XBRL holds which quarter on which basis."""

    symbol: str
    period_end: date
    basis: str  # consolidated | standalone
    type_sub: str | None
    audited: str | None
    xbrl_url: str
    broadcast_at: datetime | None
    raw: dict
    ixbrl_url: str | None = None  # NSE's human-readable (HTML) view of the same instance
