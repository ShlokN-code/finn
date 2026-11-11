"""Resolve a promise's period in code from what the model read (period_type, fy, quarter, …) and the call date.

The model never computes dates: it reports "FY27" as fy=2027, "next year" as period_type=next_fy. Code turns that
into a Period using the company's fiscal year-end month (March for most Indian companies). Ambiguous phrases
resolve to None, which the ledger reports as "Can't score (no clear period)" — never a guess.
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta

from finn.models import Period

RESULTS_LAG_DAYS = {"quarter": 60, "half_year": 75, "year": 90}  # results + call usually land within this


def _month_end(y: int, m: int) -> date:
    return date(y, m, calendar.monthrange(y, m)[1])


def fy_end(fy: int, ye_month: int = 3) -> date:
    """FY27 (fy=2027) ends 31 Mar 2027; a December-year-end company's 2027 ends 31 Dec 2027."""
    return _month_end(fy, ye_month)


def fiscal_year_of(d: date, ye_month: int = 3) -> int:
    """The fiscal year (named by the calendar year it ends in) that contains `d`."""
    return d.year if d.month <= ye_month else d.year + 1


def fy_label(fy: int, ye_month: int = 3) -> str:
    return f"FY{fy % 100:02d}" if ye_month == 3 else f"{calendar.month_abbr[ye_month]} {fy}"


def year_period(fy: int, ye_month: int = 3) -> Period:
    end = fy_end(fy, ye_month)
    start = _month_end(fy - 1, ye_month) + timedelta(days=1)
    return Period(kind="year", start=start, end=end, label=fy_label(fy, ye_month))


def quarter_of_fy(fy: int, q: int, ye_month: int = 3) -> Period:
    """Q1..Q4 of fiscal year `fy`."""
    end_month = (ye_month + 3 * q - 1) % 12 + 1
    end_year = fy - 1 if end_month > ye_month else fy
    end = _month_end(end_year, end_month)
    start_month = (end_month - 3) % 12 + 1
    start = date(end_year if start_month <= end_month else end_year - 1, start_month, 1)
    label = f"Q{q} FY{fy % 100:02d}" if ye_month == 3 else f"Q{q} {fy}"
    return Period(kind="quarter", start=start, end=end, label=label)


def half_of_fy(fy: int, h: int, ye_month: int = 3) -> Period:
    q_first, q_last = quarter_of_fy(fy, 1 if h == 1 else 3, ye_month), quarter_of_fy(fy, 2 if h == 1 else 4, ye_month)
    label = f"H{h} FY{fy % 100:02d}" if ye_month == 3 else f"H{h} {fy}"
    return Period(kind="half_year", start=q_first.start, end=q_last.end, label=label)


def resolve(period_type: str, fy: int | None, quarter: int | None, half: int | None, years: int | None,
            call_date: date, ye_month: int = 3) -> Period | None:  # fmt: skip
    """Period for a guidance item, or None when it has no clear date."""
    cur = fiscal_year_of(call_date, ye_month)
    # A call within ~2 months after the year-end discusses the year just closed; "next year" is ambiguous there.
    just_closed = 0 < (call_date - fy_end(cur - 1, ye_month)).days <= 62
    if fy is not None and not (2000 <= fy <= 2100):
        fy = None
    if period_type == "quarter" and quarter in (1, 2, 3, 4):
        if fy is None:  # 'Q3' alone: the next Q3 on or after the call
            for f in (cur, cur + 1):
                p = quarter_of_fy(f, quarter, ye_month)
                if p.end >= call_date:
                    return p
            return None
        return quarter_of_fy(fy, quarter, ye_month)
    if period_type == "half" and half in (1, 2):
        return half_of_fy(fy or cur, half, ye_month)
    if period_type in ("fy", "by_fy"):
        return year_period(fy, ye_month) if fy else None
    if period_type == "this_fy":
        return year_period(cur, ye_month)
    if period_type == "next_fy":
        return None if just_closed else year_period(cur + 1, ye_month)
    if period_type == "next_n_years" and years and 1 <= years <= 10:
        return None if just_closed else year_period(cur + years, ye_month)
    return None  # medium_term, unspecified


def results_due(p: Period) -> date:
    """When the delivered figure for `p` should be public (results + call)."""
    return p.end + timedelta(days=RESULTS_LAG_DAYS.get(p.kind, 90))
