"""The demo portfolio the scheduled jobs track (holdings themselves live in the browser — PRODUCT.md §7).

Jobs also track every Telegram subscriber's symbols (push_subscriptions).
"""

from __future__ import annotations

DEMO_PORTFOLIO: list[str] = [
    "HAL", "EICHERMOT", "GRASIM", "TATAPOWER", "ALKEM", "KALYANKJIL", "COCHINSHIP", "TITAGARH", "IDEA",
    "RELIANCE", "HDFCBANK", "BAJFINANCE", "INFY", "ITC", "DIVISLAB", "TATASTEEL", "JUBLFOOD", "DIXON",
]  # fmt: skip


def tracked_symbols(override: str | None = None, conn=None) -> list[str]:
    """Symbols for a job run: a comma-separated override (CLI/workflow input), else the demo portfolio plus
    every Telegram subscriber's symbols (their opt-in server copy) when a DB connection is given."""
    if override:
        return [s.strip().upper() for s in override.split(",") if s.strip()]
    out = list(DEMO_PORTFOLIO)
    if conn is not None:
        rows = conn.execute(
            "select distinct h->>'symbol' as s from public.push_subscriptions, jsonb_array_elements(holdings) h"
        ).fetchall()
        out += sorted({r["s"] for r in rows if r["s"]} - set(out))
    return out
