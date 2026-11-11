"""Results-season strip and scoreboard (PRODUCT §4, §7): which holdings have reported this quarter, and how.

Shown from a quarter's end until 60 days after it (75 for Q4, whose results are due later). Counts are taken
in code from the stored results cards; a card that failed its cross-check ("Couldn't verify") counts as reported
but contributes no numbers. Event keys are '<SYM>:results:<Q label>' (DECISIONS: event threading).
"""

from __future__ import annotations

from datetime import date, datetime

from finn.calendar import quarter_end_on_or_before, quarter_period, to_ist
from finn.models import Figure, SeasonRow, SeasonStrip


def season_quarter(today: date) -> date | None:
    qe = quarter_end_on_or_before(today)
    lag = 75 if qe.month == 3 else 60
    return qe if 0 < (today - qe).days <= lag else None


def _ts(x) -> datetime:
    return x if isinstance(x, datetime) else datetime.fromisoformat(str(x).replace("Z", "+00:00"))


def _line(detail: dict, *metrics: str) -> Figure | None:
    for m in metrics:
        ln = next((ln for ln in detail.get("lines", []) if ln.get("metric") == m), None)
        if ln and ln.get("yoy") and ln["yoy"].get("value") is not None:
            return Figure.model_validate(ln["yoy"])
    return None


def season_row(symbol: str, event: dict | None, as_of: datetime) -> SeasonRow:
    if event is None:
        return SeasonRow(symbol=symbol, status="awaited")
    timeline = [t for t in (event.get("timeline") or []) if _ts(t["at"]) <= as_of]
    outcome = min((_ts(t["at"]) for t in timeline if t["stage"] == "outcome"), default=None)
    if outcome is None:
        return SeasonRow(symbol=symbol, status="scheduled" if timeline else "awaited", event_id=event["id"])
    d = event.get("detail") or {}
    if d.get("kind") != "results":
        return SeasonRow(symbol=symbol, status="reported", event_id=event["id"], reported_at=outcome)
    shown = d.get("verification") != "mismatch"
    return SeasonRow(
        symbol=symbol, status="reported", event_id=event["id"], reported_at=outcome,
        verification=d.get("verification"),
        revenue_yoy=_line(d, "Revenue", "NII") if shown else None,
        pat_yoy=_line(d, "PAT") if shown else None,
        margin_yoy=_line(d, "EBITDA margin") if shown else None,
    )  # fmt: skip


def build_strip(symbols: list[str], events: list[dict], as_of: datetime) -> SeasonStrip | None:
    qe = season_quarter(to_ist(as_of).date())
    if qe is None:
        return None
    period = quarter_period(qe)
    by_key = {e["key"]: e for e in events}
    rows = [season_row(s, by_key.get(f"{s}:results:{period.label}"), as_of) for s in symbols]
    reported = [r for r in rows if r.status == "reported"]

    def n(pred) -> int:
        return sum(1 for r in reported if pred(r))

    order = {"reported": 0, "scheduled": 1, "awaited": 2}
    rows.sort(key=lambda r: (order[r.status], -(r.reported_at.timestamp() if r.reported_at else 0), r.symbol))
    return SeasonStrip(
        quarter=period, total=len(symbols), reported=len(reported),
        cross_checked=n(lambda r: r.verification in ("cross_checked", "partial")),
        pat_up=n(lambda r: r.pat_yoy is not None and r.pat_yoy.value > 0),
        pat_down=n(lambda r: r.pat_yoy is not None and r.pat_yoy.value < 0),
        margin_up=n(lambda r: r.margin_yoy is not None and r.margin_yoy.value > 0),
        margin_down=n(lambda r: r.margin_yoy is not None and r.margin_yoy.value < 0),
        rows=rows,
    )  # fmt: skip


def season_strip(conn, symbols: list[str], as_of: datetime) -> SeasonStrip | None:
    qe = season_quarter(to_ist(as_of).date())
    if qe is None:
        return None
    label = quarter_period(qe).label
    events = conn.execute(
        "select id, key, symbol, timeline, detail from public.events where key = any(%s)",
        ([f"{s}:results:{label}" for s in symbols],),
    ).fetchall()
    return build_strip(symbols, events, as_of)
