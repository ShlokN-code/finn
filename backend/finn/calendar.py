"""Time, trading-day and Indian-FY helpers (trust layer: IST display, UTC storage, FY quarter labels, holidays).

- Store UTC; display IST (UTC+5:30, no DST).
- Indian FY runs Apr–Mar and is named for the year it ends in: Q2 FY27 = Jul–Sep 2026.
- NSE holidays: the DB copy (refreshed by the daily job) wins; the committed finn/data/nse_holidays.json is
  the fallback. Note: NSE sometimes holds a special session on a listed holiday (Muhurat trading on Diwali),
  so "did the market trade on D" is answered by price data when we have it; this calendar is for scheduling.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, time, timedelta, timezone
from functools import lru_cache
from pathlib import Path

from finn.models import Period

IST = timezone(timedelta(hours=5, minutes=30), name="IST")
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)
_HOLIDAYS_FILE = Path(__file__).resolve().parent / "data" / "nse_holidays.json"


def now_utc() -> datetime:
    return datetime.now(UTC)


def to_ist(dt: datetime) -> datetime:
    return dt.astimezone(IST)


def ist_today(now: datetime | None = None) -> date:
    return to_ist(now or now_utc()).date()


def parse_ist(text: str, fmt: str) -> datetime:
    """Parse an exchange timestamp printed in IST (e.g. '04-Nov-2026 21:01:36') → aware UTC datetime."""
    return datetime.strptime(text.strip(), fmt).replace(tzinfo=IST).astimezone(UTC)


# --- holidays / trading days ------------------------------------------------------------------


@lru_cache(maxsize=1)
def _file_holidays() -> frozenset[date]:
    data = json.loads(_HOLIDAYS_FILE.read_text())
    return frozenset(date.fromisoformat(h["date"]) for h in data["holidays"])


_extra_holidays: set[date] = set()


def set_holidays(days: set[date]) -> None:
    """Override with the DB copy (called by jobs after loading market_holidays)."""
    _extra_holidays.clear()
    _extra_holidays.update(days)


def holidays() -> frozenset[date]:
    return frozenset(_extra_holidays) | _file_holidays()


def is_trading_day(d: date) -> bool:
    return d.weekday() < 5 and d not in holidays()


def previous_trading_day(d: date) -> date:
    d -= timedelta(days=1)
    while not is_trading_day(d):
        d -= timedelta(days=1)
    return d


def is_market_hours(now: datetime | None = None) -> bool:
    t = to_ist(now or now_utc())
    return is_trading_day(t.date()) and MARKET_OPEN <= t.time() <= MARKET_CLOSE


# --- Indian FY periods ------------------------------------------------------------------------


def fy_of(d: date) -> int:
    """FY number (ends-in year): 15 Aug 2026 → 2027."""
    return d.year + 1 if d.month >= 4 else d.year


def quarter_end_on_or_before(d: date) -> date:
    for m, day in ((12, 31), (9, 30), (6, 30), (3, 31)):
        qe = date(d.year, m, day)
        if qe <= d:
            return qe
    return date(d.year - 1, 12, 31)


def next_quarter_end(d: date) -> date:
    """First quarter end strictly after d."""
    for m, day in ((3, 31), (6, 30), (9, 30), (12, 31)):
        qe = date(d.year, m, day)
        if qe > d:
            return qe
    return date(d.year + 1, 3, 31)


def previous_quarter_end(quarter_end: date) -> date:
    return quarter_end_on_or_before(quarter_end - timedelta(days=1))


def year_ago_quarter_end(quarter_end: date) -> date:
    return date(quarter_end.year - 1, quarter_end.month, quarter_end.day)


def quarter_period(quarter_end: date) -> Period:
    """Period for the quarter ending on `quarter_end` (must be a quarter end). Label like 'Q2 FY27'."""
    if (quarter_end.month, quarter_end.day) not in ((3, 31), (6, 30), (9, 30), (12, 31)):
        raise ValueError(f"not a quarter end: {quarter_end}")
    start_month = quarter_end.month - 2
    start = date(quarter_end.year, start_month, 1)
    q = {6: 1, 9: 2, 12: 3, 3: 4}[quarter_end.month]
    return Period(kind="quarter", start=start, end=quarter_end, label=f"Q{q} FY{fy_of(quarter_end) % 100:02d}")


def results_quarter_for(filed: date, *, forward_looking: bool = True) -> date:
    """Quarter whose results a filing on `filed` most likely concerns (when the text doesn't say).

    Only a forward-looking filing (a board-meeting intimation or call schedule) can concern a quarter that has
    not ended yet — when it is filed within 15 days of that quarter's end. Outcomes, decks, recordings and
    transcripts always concern a quarter that has already ended.
    """
    upcoming = next_quarter_end(filed)
    if forward_looking and (upcoming - filed).days <= 15:
        return upcoming
    return quarter_end_on_or_before(filed)
