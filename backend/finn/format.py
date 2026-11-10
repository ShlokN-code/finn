"""Display formatting (Indian conventions): lakh separators, ₹ Cr, IST, signed percentages. Display only —
never feed these strings back into arithmetic."""

from __future__ import annotations

from datetime import datetime

from finn.calendar import to_ist
from finn.numbers import round_display


def indian(x: float, places: int = 0) -> str:
    """1234567.8 → '12,34,568' (places=0) / '12,34,567.8' (places=1)."""
    d = round_display(x, places)
    neg = d < 0
    s = f"{abs(d):.{places}f}"
    whole, _, frac = s.partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    return ("−" if neg else "") + whole + (f".{frac}" if frac else "")


def money_cr(x: float) -> str:
    return f"₹{indian(x, 0 if abs(x) >= 100 else 1)} Cr"


def signed_pct(x: float | None, places: int = 1) -> str:
    if x is None:
        return "n/m"
    v = round_display(x, places)
    return f"{'+' if v > 0 else '−' if v < 0 else '±'}{abs(v)}%"


def ist(dt: datetime, fmt: str = "%d %b, %H:%M IST") -> str:
    return to_ist(dt).strftime(fmt)


def figure_text(fig: dict) -> str:
    """A Figure (as JSON) → short display text."""
    v, unit = fig.get("value"), fig.get("unit")
    if v is None:
        return "n/m"
    if unit == "INR_CR":
        return money_cr(v)
    if unit == "PCT":
        return f"{round_display(v, 1)}%"
    if unit == "BPS":
        return f"{'+' if v > 0 else '−' if v < 0 else '±'}{abs(round_display(v, 0))} bps"
    if unit == "X":
        return f"{round_display(v, 1)}×"
    if unit in ("INR", "INR_PER_SHARE"):
        return f"₹{indian(v, 2)}"
    return indian(v, 1)
