"""Event threading: group a symbol's classified filings into events (one card each in the Brief).

Rules (deterministic, idempotent — the event id is its key, so re-running over the same filings gives the
same events):

- Results thread, key 'SYM:results:Q2 FY27': results + earnings_call filings of one quarter (board-meeting
  intimation → outcome → press release/deck → call → recording → transcript). The quarter is read from the
  text ('quarter ended 30th June 2026', 'Q1 FY2027', 'period ended Jun 30, 2026'); otherwise inferred from
  the filing date (finn.calendar.results_quarter_for).
- Satellites: an investor presentation filed within 2 days of a results outcome joins that results thread;
  a newspaper ad joins the symbol's most recent event active within the previous 3 days (results ads,
  AGM notices). Otherwise both stay hidden filings (no event).
- Everything else that is material: same symbol + category within 7 days of the cluster's last filing
  → one event, key 'SYM:<category>:<IST date of first filing>'.
- routine / investor_meetings / unclassified filings are not threaded (Brief's hidden drawer).
- Duplicates (duplicate_of set) are skipped; the canonical copy carries the thread.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime, timedelta

from finn.calendar import quarter_period, results_quarter_for, to_ist
from finn.models import Category, Event, EventStage, Filing, TimelineItem
from finn.sources.nse import subject_core

C, S = Category, EventStage

CLUSTER_GAP = timedelta(days=7)
PRESENTATION_WINDOW = timedelta(days=2)
AD_WINDOW = timedelta(days=3)

UNTHREADED = {C.routine, C.investor_meetings, C.unclassified}
RESULTS_THREAD = {C.results, C.earnings_call}

TITLES = {
    C.mna: "M&A / restructuring", C.management_change: "Management change", C.litigation: "Legal / regulatory",
    C.credit_rating: "Credit rating", C.pledging: "Promoter pledge", C.capex: "Capex / capacity",
    C.press_release: "Business update", C.insider_trading: "Insider trading disclosure", C.fund_raise: "Fund raise",
    C.dividend: "Dividend", C.bonus_split: "Bonus / split", C.agm_egm: "Shareholder meeting",
    C.postal_ballot: "Postal ballot", C.earnings_call: "Earnings call",
}  # fmt: skip

STAGE_LABELS = {
    S.intimation: "Board meeting intimated", S.outcome: "Results filed", S.presentation: "Presentation / press release",
    S.call: "Earnings call", S.transcript: "Call transcript", S.newspaper_ad: "Newspaper ad",
    S.clarification: "Clarification",
}  # fmt: skip

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}  # fmt: skip
_MON = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?"
_ENDED = r"(?:ended|ending|end)\s+(?:on\s+)?"
_PATTERNS = [
    re.compile(_ENDED + r"(\d{1,2})(?:st|nd|rd|th)?[\s-]+" + _MON + r",?[\s-]+(\d{4})", re.I),  # 30th June 2026
    re.compile(_ENDED + _MON + r"\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})", re.I),  # September 30, 2026
    re.compile(_ENDED + _MON + r",?\s+(\d{4})", re.I),  # September 2026
]
_PAST_CALL = re.compile(r"audio|recording|webcast|transcript|held on", re.I)
_QFY = re.compile(r"\bQ([1-4])\s*[- ]?\s*FY\s*'?(\d{2,4})\b", re.I)


def _month_end_quarter(year: int, month: int) -> date | None:
    ends = {3: 31, 6: 30, 9: 30, 12: 31}
    return date(year, month, ends[month]) if month in ends else None


def quarter_from_text(text: str) -> date | None:
    """Quarter-end date stated in a filing's text, or None."""
    if m := _QFY.search(text):
        q, fy = int(m.group(1)), int(m.group(2))
        fy = fy + 2000 if fy < 100 else fy
        month = {1: 6, 2: 9, 3: 12, 4: 3}[q]
        year = fy if q == 4 else fy - 1
        return _month_end_quarter(year, month)
    for i, pat in enumerate(_PATTERNS):
        if m := pat.search(text):
            g = m.groups()
            if i == 0:
                month, year = _MONTHS[g[1][:3].lower()], int(g[2])
            elif i == 1:
                month, year = _MONTHS[g[0][:3].lower()], int(g[2])
            else:
                month, year = _MONTHS[g[0][:3].lower()], int(g[1])
            if qe := _month_end_quarter(year, month):
                return qe
    return None


def _cat(f: Filing) -> Category:
    return Category(f.category) if f.category else C.unclassified


def _stage(f: Filing) -> EventStage | None:
    return EventStage(f.stage) if f.stage else None


def _item(f: Filing) -> TimelineItem:
    st = _stage(f) or S.other
    label = STAGE_LABELS.get(st) or subject_core(f.subject)[:90]
    if st == S.call and re.search(r"audio|recording|webcast", f.subject, re.I):
        label = "Call recording"
    if st == S.presentation and re.search(r"press release", f.subject, re.I):
        label = "Press release"
    elif st == S.presentation:
        label = "Investor presentation"
    return TimelineItem(stage=st, filing_id=f.id, at=f.filed_at, label=label)


def _title(cat: Category, filings: list[Filing]) -> str:
    for f in filings:
        if _stage(f) == S.newspaper_ad:
            continue
        core = subject_core(f.subject)
        if len(core) >= 15 and not re.match(r"(general )?updates?$|disclosure under regulation", core, re.I):
            return f"{TITLES.get(cat, cat.value)}: {core[:100]}"
    return TITLES.get(cat, cat.value)


def thread(filings: list[Filing]) -> tuple[list[Event], dict[str, str | None]]:
    """Thread all filings (any symbols). Returns events and a filing_id → event_id map (None = unthreaded)."""
    assignment: dict[str, str | None] = {f.id: None for f in filings}
    groups: dict[str, list[Filing]] = defaultdict(list)
    meta: dict[str, dict] = {}
    by_symbol: dict[str, list[Filing]] = defaultdict(list)
    for f in filings:
        if not f.duplicate_of:
            by_symbol[f.symbol].append(f)

    for symbol, fs in by_symbol.items():
        fs.sort(key=lambda x: (x.filed_at, x.id))
        satellites: list[Filing] = []
        open_clusters: dict[Category, tuple[str, datetime]] = {}
        for f in fs:
            cat, st = _cat(f), _stage(f)
            if st == S.newspaper_ad or (cat == C.investor_meetings and st == S.presentation):
                satellites.append(f)
                continue
            if cat in UNTHREADED:
                continue
            if cat in RESULTS_THREAD:
                forward = st in (S.intimation, None) or (st == S.call and not _PAST_CALL.search(f.subject))
                qe = quarter_from_text(f.subject) or results_quarter_for(
                    to_ist(f.filed_at).date(), forward_looking=forward
                )
                period = quarter_period(qe)
                key = f"{symbol}:results:{period.label}"
                meta.setdefault(key, {"symbol": symbol, "category": C.results, "period": period})
            else:
                cur = open_clusters.get(cat)
                if cur and f.filed_at - cur[1] <= CLUSTER_GAP:
                    key = cur[0]
                else:
                    key = f"{symbol}:{cat.value}:{to_ist(f.filed_at).date().isoformat()}"
                    meta[key] = {"symbol": symbol, "category": cat, "period": None}
                open_clusters[cat] = (key, f.filed_at)
            groups[key].append(f)

        # satellites: presentations → nearby results outcome; newspaper ads → most recent active event
        for f in satellites:
            target = None
            if _stage(f) == S.presentation:
                for key, members in groups.items():
                    if (
                        meta[key]["symbol"] == symbol
                        and meta[key]["category"] == C.results
                        and any(
                            _stage(m) == S.outcome and abs(m.filed_at - f.filed_at) <= PRESENTATION_WINDOW
                            for m in members
                        )
                    ):
                        target = key
                        break
            else:
                best = None
                for key, members in groups.items():
                    if meta[key]["symbol"] != symbol:
                        continue
                    last = max((m.filed_at for m in members if m.filed_at <= f.filed_at), default=None)
                    if last and f.filed_at - last <= AD_WINDOW and (best is None or last > best[1]):
                        best = (key, last)
                target = best[0] if best else None
            if target:
                groups[target].append(f)

    events = []
    for key, members in groups.items():
        members.sort(key=lambda x: (x.filed_at, x.id))
        m = meta[key]
        cat: Category = m["category"]
        title = f"{m['period'].label} results" if cat == C.results else _title(cat, members)
        events.append(
            Event(
                id=key,
                key=key,
                symbol=m["symbol"],
                category=cat,
                title=title,
                period=m["period"],
                started_at=members[0].filed_at,
                updated_at=members[-1].filed_at,
                timeline=[_item(f) for f in members],
            )
        )
        for f in members:
            assignment[f.id] = key
    events.sort(key=lambda e: e.updated_at, reverse=True)
    return events, assignment
