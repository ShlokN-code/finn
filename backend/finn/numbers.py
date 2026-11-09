"""Numeric helpers that enforce the float-money rules (see docs/DECISIONS.md, 'Money as float').

- Never compare floats with ==; use approx_equal with source-aware tolerances.
- Compute on unrounded values; round only for display, half-up, via round_display.
- Percentage change on a tiny or negative base is not meaningful; pct_change returns None.
"""

from __future__ import annotations

import math
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
