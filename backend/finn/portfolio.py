"""The demo portfolio the scheduled jobs track (holdings themselves live in the browser — PRODUCT.md §7).

Jobs also track every Telegram subscriber's symbols (push_subscriptions).
"""

from __future__ import annotations

DEMO_PORTFOLIO: list[str] = [
    "HAL", "EICHERMOT", "GRASIM", "TATAPOWER", "ALKEM", "KALYANKJIL", "COCHINSHIP", "TITAGARH", "IDEA",
    "RELIANCE", "HDFCBANK", "BAJFINANCE", "INFY", "ITC", "DIVISLAB", "TATASTEEL", "JUBLFOOD", "DIXON",
]  # fmt: skip


# Demo weights (% of portfolio; sum 100). Mirrored in web/lib/demo.ts — the phone sends these with /brief.
DEMO_WEIGHTS: dict[str, float] = {
    "HAL": 6, "EICHERMOT": 6, "GRASIM": 5, "TATAPOWER": 5, "ALKEM": 5, "KALYANKJIL": 5, "COCHINSHIP": 5,
    "TITAGARH": 4, "IDEA": 3, "RELIANCE": 8, "HDFCBANK": 8, "BAJFINANCE": 6, "INFY": 7, "ITC": 6, "DIVISLAB": 5,
    "TATASTEEL": 5, "JUBLFOOD": 5, "DIXON": 6,
}  # fmt: skip
assert set(DEMO_WEIGHTS) == set(DEMO_PORTFOLIO) and sum(DEMO_WEIGHTS.values()) == 100


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
