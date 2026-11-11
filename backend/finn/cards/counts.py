"""Brief header numbers (PRODUCT §4): how much there is to read and an estimate of the time FINN saved.

The estimate is deliberately simple and is shown with its formula (DECISIONS: "est. time saved"):
    est. = 30 s × routine filings hidden + 3 min × material filings in the window − the Brief's own read time
    (30 s per full card, 10 s per one-liner or chip); nearest minute under 10, else nearest 5; never below 0.
"""

from __future__ import annotations

from datetime import datetime

from finn.models import BriefCounts, Card

ROUTINE_S, MATERIAL_S = 30, 180
CARD_READ_S, LINE_READ_S = 30, 10
FULL_CARDS = {"results", "management_change", "price_volume", "what_to_watch"}
FORMULA = (
    "est. = 30 s × routine filings hidden + 3 min × material filings in the window − this Brief's read time "
    "(30 s per card, 10 s per one-liner or chip); nearest minute under 10, else nearest 5"
)


def material_filings(cards: list[Card], since: datetime | None) -> int:
    """Distinct filings behind the shown cards that were filed inside the window (all of them for 'all')."""
    ids = {t.filing_id for c in cards for t in c.timeline if since is None or t.at >= since}
    return len(ids)


def round_minutes(seconds: float) -> int:
    if seconds <= 0:
        return 0
    m = seconds / 60
    return int(m + 0.5) if m < 10 else 5 * int(m / 5 + 0.5)


def brief_counts(cards: list[Card], hidden_n: int, since: datetime | None) -> BriefCounts:
    full = sum(1 for c in cards if c.card_type in FULL_CARDS)
    chips = sum(1 for c in cards if c.card_type == "inline_chip")
    lines = len(cards) - full - chips
    material = material_filings(cards, since)
    read_s = CARD_READ_S * full + LINE_READ_S * (lines + chips)
    saved_s = ROUTINE_S * hidden_n + MATERIAL_S * material - read_s
    return BriefCounts(
        cards=full, one_liners=lines, chips=chips, material_filings=material, hidden_filings=hidden_n,
        read_seconds=read_s, est_minutes_saved=round_minutes(saved_s), formula=FORMULA,
    )  # fmt: skip
