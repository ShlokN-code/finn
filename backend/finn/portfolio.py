"""The demo portfolio the scheduled jobs track (holdings themselves live in the browser — PRODUCT.md §7).

Later phases add the union of opted-in server copies (push_subscriptions) to this list.
"""

from __future__ import annotations

DEMO_PORTFOLIO: list[str] = [
    "HAL", "EICHERMOT", "GRASIM", "TATAPOWER", "ALKEM", "KALYANKJIL", "COCHINSHIP", "TITAGARH", "IDEA",
    "RELIANCE", "HDFCBANK", "BAJFINANCE", "INFY", "ITC", "DIVISLAB", "TATASTEEL", "JUBLFOOD", "DIXON",
]  # fmt: skip


def tracked_symbols(override: str | None = None) -> list[str]:
    """Symbols for a job run: a comma-separated override (CLI/workflow input) or the demo portfolio."""
    if override:
        return [s.strip().upper() for s in override.split(",") if s.strip()]
    return list(DEMO_PORTFOLIO)
