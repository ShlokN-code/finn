"""Visible feedback rules (PRODUCT §5) — transparent multipliers, not learned ranking.

Not useful → ×0.8 per swipe at the chosen scope; Useful → ×1.25. Bounded to [0.1, 2.0]. Rules multiply
(a stock rule and a category rule both apply). Critical-category floors are applied in score.py.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from finn.models import WeightRule

NOT_USEFUL, USEFUL = 0.8, 1.25
MIN_MULT, MAX_MULT = 0.1, 2.0
Scope = Literal["stock", "category", "stock_category", "event"]


def rule_id(scope: Scope, symbol: str | None = None, category: str | None = None, event_id: str | None = None) -> str:
    return {
        "stock": f"stock:{symbol}",
        "category": f"category:{category}",
        "stock_category": f"stock_category:{symbol}:{category}",
        "event": f"event:{event_id}",
    }[scope]


def apply_feedback(
    rules: list[WeightRule],
    useful: bool,
    scope: Scope,
    symbol: str | None = None,
    category: str | None = None,
    event_id: str | None = None,
    now: datetime | None = None,
) -> list[WeightRule]:
    """Return the rules with one swipe applied (a new list; the input is not modified)."""
    rid = rule_id(scope, symbol, category, event_id)
    now = now or datetime.now(UTC)
    out = [r for r in rules if r.id != rid]
    cur = next((r for r in rules if r.id == rid), None)
    mult = (cur.multiplier if cur else 1.0) * (USEFUL if useful else NOT_USEFUL)
    mult = min(MAX_MULT, max(MIN_MULT, mult))
    out.append(
        WeightRule(
            id=rid, scope=scope,
            symbol=symbol if scope in ("stock", "stock_category") else None,
            category=category if scope in ("category", "stock_category") else None,
            event_id=event_id if scope == "event" else None,
            multiplier=round(mult, 6),
            not_useful_count=(cur.not_useful_count if cur else 0) + (0 if useful else 1),
            useful_count=(cur.useful_count if cur else 0) + (1 if useful else 0),
            updated_at=now,
        )
    )  # fmt: skip
    return out


def reset(rules: list[WeightRule], rid: str | None = None) -> list[WeightRule]:
    """Reset one rule (by id) or all of them."""
    return [] if rid is None else [r for r in rules if r.id != rid]


def matches(r: WeightRule, symbol: str, category: str, event_id: str) -> bool:
    return (
        (r.scope == "stock" and r.symbol == symbol)
        or (r.scope == "category" and r.category == category)
        or (r.scope == "stock_category" and r.symbol == symbol and r.category == category)
        or (r.scope == "event" and r.event_id == event_id)
    )


def effective_multiplier(rules: list[WeightRule], symbol: str, category: str, event_id: str) -> tuple[float, list[str]]:
    m, notes = 1.0, []
    for r in rules:
        if matches(r, symbol, category, event_id):
            m *= r.multiplier
            notes.append(f"Your rule {r.id} (×{r.multiplier:g})")
    return m, notes
