"""The ranked Brief: holdings + window + feedback rules → Cards, hidden-drawer counts, freshness.

Holdings arrive with the request and are used only to rank it — never stored or logged (DECISIONS: holdings).
Runs on Render (Supabase reads only) and in jobs (alert dispatch, Telegram test alert).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from finn.calendar import now_utc
from finn.cards.build import NEUTRAL_SCORE, build_card
from finn.cards.counts import brief_counts
from finn.cards.season import season_strip
from finn.models import BriefResponse, Card, FeedbackAction, HiddenItem, WeightRule
from finn.ranking.feedback import apply_feedback
from finn.ranking.score import HIDDEN, REPEAT_WINDOW_DAYS, repeat_counts, score

EVENT_COLS = (
    "id, key, symbol, category, title, period, started_at, updated_at, timeline, figures, impact, impact_reason, "
    "driver_ids, so_what, detail, detail_at, refreshed_at"
)
FILING_COLS = "id, exchange, symbol, filed_at, subject, attachment_url, xbrl_url, fetched_at"


def load_events(conn, symbols: list[str], since: datetime | None, limit: int = 400) -> list[dict]:
    q = f"select {EVENT_COLS} from public.events where symbol = any(%s)"
    params: list = [symbols]
    if since is not None:
        q += " and updated_at >= %s"
        params.append(since)
    return conn.execute(q + " order by updated_at desc limit %s", [*params, limit]).fetchall()


def load_event(conn, event_id: str) -> dict | None:
    return conn.execute(f"select {EVENT_COLS} from public.events where id = %s", (event_id,)).fetchone()


def load_filings(conn, events: list[dict]) -> dict[str, dict]:
    ids = sorted({t["filing_id"] for e in events for t in (e.get("timeline") or [])})
    if not ids:
        return {}
    rows = conn.execute(f"select {FILING_COLS} from public.filings where id = any(%s)", (ids,)).fetchall()
    return {r["id"]: r for r in rows}


def _repeat_context(conn, symbols: list[str], since: datetime | None) -> list[dict]:
    lo = (since or datetime.now().astimezone()) - timedelta(days=REPEAT_WINDOW_DAYS + 1)
    return conn.execute(
        "select id, symbol, category, started_at from public.events where symbol = any(%s) and started_at >= %s",
        (symbols, lo),
    ).fetchall()


HIDDEN_GROUP = (
    "coalesce(case when category = 'routine' then hidden_reason end, case category "
    "when 'investor_meetings' then 'Investor-meeting notice' when 'unclassified' then 'Unclassified' end, "
    "'Other routine filing')"
)
MAX_HIDDEN_ITEMS = 300


def hidden_filings(conn, symbols: list[str], since: datetime | None, until: datetime | None = None) -> list[dict]:
    """Hidden drawer: routine filings (grouped by hidden_reason), investor meetings and unclassified, newest first."""
    q = (
        f"select id, symbol, subject, filed_at, coalesce(attachment_url, xbrl_url) as url, {HIDDEN_GROUP} as grp "
        "from public.filings where symbol = any(%s) and duplicate_of is null "
        "and category in ('routine', 'investor_meetings', 'unclassified')"
    )
    params: list = [symbols]
    if since is not None:
        q += " and filed_at >= %s"
        params.append(since)
    if until is not None:
        q += " and filed_at < %s"
        params.append(until)
    return conn.execute(q + " order by filed_at desc", params).fetchall()


def hidden_counts(rows: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in rows:
        out[r["grp"]] = out.get(r["grp"], 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


def hidden_items(rows: list[dict]) -> list[HiddenItem]:
    return [
        HiddenItem(id=r["id"], symbol=r["symbol"], subject=(r["subject"] or "")[:240], filed_at=r["filed_at"],
                   url=r["url"], group=r["grp"])
        for r in rows[:MAX_HIDDEN_ITEMS]
    ]  # fmt: skip


def data_as_of(conn) -> datetime | None:
    r = conn.execute(
        "select min(last_success_at) as t from public.source_status where source = 'nse_announcements'"
    ).fetchone()
    return r["t"] if r else None


def rank(
    events: list[dict],
    filings: dict[str, dict],
    weights: dict[str, float | None],
    rules: list[WeightRule],
    since: datetime | None,
    context: list[dict] | None = None,
) -> list[Card]:
    reps = repeat_counts(list(context or events))
    cards: list[Card] = []
    for e in events:
        if e["category"] in HIDDEN:
            continue
        s = score(e, weights.get(e["symbol"]), rules, since=since, repeats=reps.get(e["id"], 0))
        if s.total <= 0:
            continue
        cards.append(build_card(e, filings, s))
    cards.sort(key=lambda c: c.score.total, reverse=True)
    return cards


def brief(
    conn,
    weights: dict[str, float | None],
    since: datetime | None,
    rules: list[WeightRule],
    feedback: list[FeedbackAction] | None = None,
    window: str = "since",
) -> BriefResponse:
    symbols = sorted(weights)
    rules = apply_actions(rules, feedback or [])
    events = load_events(conn, symbols, since)
    filings = load_filings(conn, events)
    cards = rank(events, filings, weights, rules, since, _repeat_context(conn, symbols, since))
    hidden_rows = hidden_filings(conn, symbols, since)
    hidden = hidden_counts(hidden_rows)
    return BriefResponse(
        cards=cards, hidden=hidden, hidden_total=len(hidden_rows), hidden_items=hidden_items(hidden_rows),
        counts=brief_counts(cards, len(hidden_rows), since),
        season=season_strip(conn, symbols, now_utc()),
        rules=rules, data_as_of=data_as_of(conn), since=since, window=window,
    )  # fmt: skip


def apply_actions(rules: list[WeightRule], actions: list[FeedbackAction]) -> list[WeightRule]:
    """Swipes queued on the phone (after their undo window) applied in order — the ×0.8/×1.25 maths stays here."""
    for a in sorted(actions, key=lambda a: a.at):
        rules = apply_feedback(rules, a.useful, a.scope, a.symbol, a.category, a.event_id, now=a.at)
    return rules


def single_card(conn, event_id: str) -> Card | None:
    e = load_event(conn, event_id)
    if e is None:
        return None
    return build_card(e, load_filings(conn, [e]), NEUTRAL_SCORE)
