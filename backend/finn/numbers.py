"""Numeric helpers that enforce the float-money rules (see docs/DECISIONS.md, 'Money as float').

- Never compare floats with ==; use approx_equal with source-aware tolerances.
- Compute on unrounded values; round only for display, half-up, via round_display.
- Percentage change on a tiny or negative base is not meaningful; pct_change returns None.
"""

from __future__ import annotations

import math
import re
from decimal import ROUND_HALF_UP, Decimal

LAKH_PER_CRORE = 100.0
MILLION_PER_CRORE = 10.0


def to_crore(value: float, unit: str) -> float:
    """Normalise a money value to ₹ crore. `unit` as printed: crore/lakh/million/rupees."""
    u = unit.strip().lower()
    if u in ("cr", "crore", "crores", "inr crore", "rs. crores"):
        return value
    if u in ("lakh", "lakhs", "lac", "lacs"):
        return value / LAKH_PER_CRORE
    if u in ("million", "millions", "mn"):
        return value / MILLION_PER_CRORE
    if u in ("rupees", "inr", "rs"):
        return value / 1e7
    raise ValueError(f"Unknown money unit: {unit!r}")


def approx_equal(a: float, b: float, *, abs_tol: float = 0.5, rel_tol: float = 0.001) -> bool:
    """True if a and b agree within the coarser of the two tolerances.

    Defaults suit ₹ crore figures cross-checked against screener (rounds to whole crore):
    0.5 Cr absolute or 0.1 % relative.
    """
    return math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol)


def pct_change(current: float, base: float, *, min_base: float = 1e-9) -> float | None:
    """Percentage change, or None when the base is ≤ 0 or ~0 (show 'n/m' or 'turned profitable')."""
    if base <= min_base:
        return None
    return (current - base) / base * 100.0


def round_display(x: float, places: int = 1) -> Decimal:
    """Half-up rounding for display, matching what a reader computes by hand (2.675 → 2.68)."""
    q = Decimal(1).scaleb(-places)
    return Decimal(repr(x)).quantize(q, rounding=ROUND_HALF_UP)


# --- parsing printed numbers (trust layer: unit normalisation) -------------------------------------

_NUM_RE = re.compile(r"[-−]?\(?\d[\d,]*(?:\.\d+)?\)?")
_UNIT_WORDS = {
    "crore": "crore",
    "crores": "crore",
    "cr": "crore",
    "cr.": "crore",
    "lakh": "lakh",
    "lakhs": "lakh",
    "lac": "lakh",
    "lacs": "lakh",
    "million": "million",
    "millions": "million",
    "mn": "million",
    "mln": "million",
    "billion": "billion",
    "billions": "billion",
    "bn": "billion",
}
_UNIT_RE = re.compile(r"\b(crores?|cr\.?|lakhs?|lacs?|millions?|mn|mln|billions?|bn)(?![a-z])", re.I)


def parse_indian_number(text: str) -> float:
    """'1,23,456.78' → 123456.78; '(1,234)' and '−5' → negative. Raises ValueError if no number."""
    m = _NUM_RE.search(text.replace(" ", " "))
    if not m:
        raise ValueError(f"no number in {text!r}")
    s = m.group(0)
    neg = s.startswith(("-", "−")) or (s.startswith("(") and s.endswith(")"))
    v = float(s.strip("-−()").replace(",", ""))
    return -v if neg else v


def to_crore_any(value: float, unit: str) -> float:
    """to_crore plus 'billion' (1 bn = 100 Cr)."""
    if unit.strip().lower() in ("billion", "billions", "bn"):
        return value * 100.0
    return to_crore(value, unit)


def parse_money(text: str, default_unit: str | None = None) -> tuple[float, str, str]:
    """Parse a printed money amount into ₹ crore.

    Returns (value_cr, raw_number_text, raw_unit). The unit is read from the text ('Rs 450 million',
    '₹12.5 lakh', '1,234 Cr') or, failing that, from `default_unit` (e.g. a table header 'Rs. in lakhs').
    Raises ValueError when no unit can be determined — never guess a unit.
    """
    raw = text.strip()
    m = _NUM_RE.search(raw.replace(" ", " "))
    if not m:
        raise ValueError(f"no number in {text!r}")
    value = parse_indian_number(m.group(0))
    um = _UNIT_RE.search(raw[m.end() :]) or _UNIT_RE.search(raw)
    if um:
        unit = _UNIT_WORDS[um.group(1).lower()]
    elif default_unit:
        unit = default_unit
    elif re.search(r"(₹|\bRs\.?|\bINR)", raw, re.I):
        unit = "rupees"
    else:
        raise ValueError(f"no unit in {text!r} and no default_unit")
    return to_crore_any(value, unit), m.group(0), unit


def deal_value_cr(quantity: float, price_inr: float) -> float:
    """Bulk/block deal value: shares × ₹ price, in ₹ crore."""
    return quantity * price_inr / 1e7
