"""Credit-rating scale, so code (not the model) decides upgrade vs downgrade."""

from __future__ import annotations

import re

LONG = ["AAA", "AA+", "AA", "AA-", "A+", "A", "A-", "BBB+", "BBB", "BBB-", "BB+", "BB", "BB-", "B+", "B", "B-",
        "C+", "C", "C-", "D"]  # fmt: skip
SHORT = ["A1+", "A1", "A2+", "A2", "A3+", "A3", "A4+", "A4", "D"]
_SHORT_RE = re.compile(r"\bA([1-4])(\+?)(?![\w])")
_LONG_RE = re.compile(r"(?<![A-Z])(AAA|AA|BBB|BB|A|B|C|D)([+-]?)(?![A-Z0-9])")


def parse(rating: str | None) -> tuple[str, int] | None:
    """'CRISIL AA+/Stable' → ('long', 1); '[ICRA]A1+' → ('short', 0). None if no grade is found."""
    if not rating:
        return None
    s = re.sub(r"\b(CRISIL|ICRA|CARE|IND|BWR|ACUITE|INFOMERICS|FITCH|MOODY'?S|S&P)\b", " ", rating.upper())
    s = s.replace("[", " ").replace("]", " ")
    if m := _SHORT_RE.search(s):
        return "short", SHORT.index(f"A{m.group(1)}{m.group(2)}")
    if m := _LONG_RE.search(s):
        g = m.group(1) + m.group(2)
        if g in LONG:
            return "long", LONG.index(g)
    return None


def direction(old: str | None, new: str | None) -> str | None:
    """'up' | 'down' | 'unchanged' | 'new' (no previous rating) | None (unparseable)."""
    n = parse(new)
    if n is None:
        return None
    o = parse(old)
    if o is None:
        return "new" if not old else None
    if o[0] != n[0]:
        return None
    return "unchanged" if o[1] == n[1] else ("up" if n[1] < o[1] else "down")
