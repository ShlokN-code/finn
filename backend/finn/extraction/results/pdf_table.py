"""Results PDF fallback (before the XBRL is filed, ~4 h after the PDF): read the statement's three quarter
columns — current, previous, year-ago — from the PDF text layer.

SEBI's format puts "Quarter ended" columns first (current, preceding, corresponding quarter last year), then
half-year / nine-month and year columns, so the first three numbers on a line item are the three quarters.
The unit comes from the header ("₹ in crore", "Rs. in lakhs", "in million"); no unit → no extraction.
Scanned PDFs (no text layer) go to the multimodal model (pdf_model.py).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime

from finn.calendar import previous_quarter_end, year_ago_quarter_end
from finn.extraction.results.compute import Fact, QuarterFacts
from finn.models import Citation
from finn.numbers import parse_indian_number, to_crore_any

_PL = r"profit(?:\s*/\s*\(?loss\)?|\s*\(loss\))?"  # "profit", "profit/(loss)", "profit (loss)"
# input key → label patterns (start of the printed row, after any serial like "1", "(a)", "IV").
ROWS: dict[str, str] = {
    "revenue": r"revenue from operations",
    "other_income": r"other income",
    "finance_costs": r"finance costs?",
    "dna": r"depreciation(?:,| and) (?:depletion and )?amorti[sz]ation(?: expenses?)?",
    "expenses": r"total expenses",
    "pbt_pre_exceptional": _PL + r" before exceptional items(?: and tax)?",
    "exceptional": r"exceptional items?(?! and)",
    "pbt": _PL + r" before tax",
    "pat": r"(?:net )?" + _PL + r" (?:for|after tax for) the (?:period|quarter)|net " + _PL + r" after tax",
    "interest_earned": r"interest earned",
    "interest_expended": r"interest expended",
    "ppop": r"operating profit before provisions and contingencies",
    "interest_income": r"interest income",
    "impairment": r"impairment (?:on|of) financial instruments",
}  # fmt: skip
_SERIAL = r"^\s*(?:\(?[a-z0-9]{1,4}[\).]|[ivx]{1,5}[\).]?|\d{1,2})?\s*"
_UNIT = re.compile(
    r"(?:₹|rs\.?|inr|rupees)\s*(?:in\s+)?(crores?|lakhs?|lacs?|millions?|mn)\b|in\s+(crores?|lakhs?|lacs?|millions?)\b",
    re.I,
)


@dataclass
class Statement:
    basis: str
    page: int  # 1-based
    unit: str  # crore | lakh | million
    text: str


def find_statement(pages: list[str], want: str = "consolidated") -> Statement | None:
    """The page holding the quarterly statement of results for `want` basis (a unit header and a revenue row)."""
    for i, t in enumerate(pages, start=1):
        low = t.lower()
        has_basis = want in low and ("result" in low or "statement" in low)
        if want == "standalone" and "consolidated" in low and "standalone" not in low:
            has_basis = False
        if not has_basis or not re.search(ROWS["revenue"] + "|" + ROWS["interest_earned"], low):
            continue
        m = _UNIT.search(t)
        if not m:
            continue
        unit = (m.group(1) or m.group(2)).lower().rstrip("s")
        unit = {"lac": "lakh", "mn": "million", "crore": "crore"}.get(unit, unit)
        return Statement(want, i, unit, t)
    return None


_NOTE = re.compile(r"\(?\s*(?:refer\s+)?notes?\s*(?:no\.?\s*)?[\d\s,&and]+\)?", re.I)
_TOKEN = re.compile(r"^\(?-?[\d,]*\d\.?\d*\)?$")


def _numbers(s: str) -> list[str]:
    """Printed numbers left to right; a lone dash means nil ('0'); note references are ignored."""
    out = []
    for tok in _NOTE.sub(" ", s).split():
        if tok in ("-", "–", "—"):
            out.append("0")
        elif _TOKEN.match(tok):
            out.append(tok)
    return out


def parse_rows(st: Statement) -> dict[str, tuple[list[str], str]]:
    """key → (first three printed numbers, the printed line). A row whose label wraps takes the next line's
    numbers."""
    lines = [ln.strip() for ln in st.text.splitlines() if ln.strip()]
    out: dict[str, tuple[list[str], str]] = {}
    for i, ln in enumerate(lines):
        low = ln.lower()
        for key, pat in ROWS.items():
            if key in out or not re.match(_SERIAL + "(?:" + pat + ")", low):
                continue
            if key == "pbt" and "exceptional" in low:
                continue
            label_end = re.match(_SERIAL + "(?:" + pat + ")", low).end()
            nums = _numbers(ln[label_end:])
            j = i
            while len(nums) < 3 and j + 1 < len(lines) and j - i < 2:
                j += 1
                nums += _numbers(lines[j])
            if len(nums) >= 3:
                out[key] = (nums[:3], ln[:200])
            break
    return out


def _half_unit(raw: str, unit: str) -> float:
    dec = len(raw.split(".")[1].rstrip(")")) if "." in raw else 0
    return to_crore_any(0.5 * 10 ** (-dec), unit)


def quarters_from_pdf(pages: list[str], quarter_end: date, url: str, filed_at: datetime | None,
                      prefer: str = "consolidated") -> tuple[str, dict[str, QuarterFacts | None]] | None:  # fmt: skip
    for basis in (prefer, "standalone" if prefer == "consolidated" else "consolidated"):
        st = find_statement(pages, basis)
        if not st:
            continue
        rows = parse_rows(st)
        if "revenue" not in rows and "interest_earned" not in rows:
            continue
        ends = [quarter_end, previous_quarter_end(quarter_end), year_ago_quarter_end(quarter_end)]
        qs = [QuarterFacts(e, basis) for e in ends]
        now = datetime.now(UTC)
        for key, (nums, line) in rows.items():
            for col, raw in enumerate(nums):
                v = parse_indian_number(raw)
                cite = Citation(source_type="exchange_filing", url=url, title=f"Results PDF ({basis})", exchange="NSE",
                                page=st.page, quote=line, locator=f"pdf:p{st.page}/{key}/col{col + 1}",
                                published_at=filed_at, retrieved_at=now)  # fmt: skip
                qs[col].facts[key] = Fact(to_crore_any(v, st.unit), cite, raw, st.unit, _half_unit(raw, st.unit))
        return basis, {"current": qs[0], "previous": qs[1], "year_ago": qs[2]}
    return None
