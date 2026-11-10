"""Alert dispatch (PRODUCT §6): which new events reach which Telegram subscriber, and how.

For each subscriber and each event on their holdings updated since the last runs (and after they connected):
  push category? → snoozed? → feedback (score too low after "not useful") → quiet hours (only M&A, a CEO/MD
  exit and a rating downgrade break through; everything else, results included, waits for the 07:00 IST run)
  → budget (5 messages / IST day; critical categories not counted against it) → batching (≥ 2 normal alerts
  in one run → one "N updates on your holdings" message) → send → one `alerts` row per (subscriber, event).
"Critical" (results, M&A, management change, rating downgrade: feedback floor, budget-exempt) is broader than
"breaks quiet hours" — a results card at 00:40 is important, but not wake-you-up urgent.
The unique row makes reruns idempotent; quiet-hours holds are re-evaluated by the 07:00 IST run.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta

from finn.calendar import IST, to_ist
from finn.cards.brief import load_events, load_filings, rank
from finn.models import AlertSettings, Card, Category
from finn.push import subscriptions as subs
from finn.push.format import batch_buttons, batch_text, buttons, card_text
from finn.push.telegram import Telegram, TelegramError
from finn.ranking.score import is_critical

log = logging.getLogger("finn.dispatch")

LOOKBACK = timedelta(hours=36)
MIN_PUSH_SCORE = 0.2  # below this (after "not useful" feedback) a non-critical event stays in the Brief only
RESULTS_WAIT = timedelta(hours=6)  # push results once numbers are built, or 6 h after the outcome regardless
FINAL = ("sent", "batched", "suppressed", "over_budget")  # never reconsidered; held/failed are retried


@dataclass
class Decision:
    card: Card
    severity: str
    status: str
    reason: str | None = None
    trigger: str = "filing"


@dataclass
class SubResult:
    chat_id: int
    decisions: list[Decision] = field(default_factory=list)
    messages: int = 0


_CEO = re.compile(r"\b(chief executive|ceo|managing director|md)\b", re.I)
_EXIT = re.compile(r"\b(resign\w*|cessation|ceas(?:e|ed|es|ing)|retire\w*|superannuat\w*|step(?:s|ped|ping)? down|"
                   r"demise|passed away|remov(?:al|ed)|terminat\w*|vacat\w*)\b", re.I)  # fmt: skip


def ceo_exit(event: dict) -> bool:
    """The CEO / MD is leaving. From the built management card (role + change) when there is one; before it is
    built, from the event title (e.g. 'Resignation of Mr X as Managing Director & CEO')."""
    d = event.get("detail") or {}
    if d.get("kind") == "management_change" and d.get("people"):
        return any(_CEO.search(p.get("role") or "") and p.get("change") in ("resigned", "retired") for p in d["people"])
    title = event.get("title") or ""
    return bool(_CEO.search(title) and _EXIT.search(title))


def breaks_quiet_hours(category: str, event: dict) -> bool:
    """Wake-you-up urgent (product owner, 11 Nov 2026): M&A, a CEO/MD exit, a credit-rating downgrade."""
    if category == Category.mna:
        return True
    if category == Category.credit_rating:
        return is_critical(category, event)  # downgrades only
    if category == Category.management_change:
        return ceo_exit(event)
    return False


def in_quiet_hours(now: datetime, s: AlertSettings) -> bool:
    t = to_ist(now).time()
    start, end = (time.fromisoformat(s.quiet_start), time.fromisoformat(s.quiet_end))
    return (start <= t or t < end) if start > end else (start <= t < end)


def ist_day_start(now: datetime) -> datetime:
    d = to_ist(now).date()
    return datetime.combine(d, time(0), IST)


def price_triggers(detail: dict, symbol: str, s: AlertSettings) -> list[str]:
    """Re-evaluate a stored price/volume event against this subscriber's own thresholds."""
    from finn.signals.price_volume import Z_MIN

    out = []
    move = (detail.get("move_pct") or {}).get("value")
    rel = (detail.get("relative_move_pct") or {}).get("value")
    z = detail.get("z_score")
    vr = (detail.get("volume_ratio") or {}).get("value")
    thr = s.per_stock_pct.get(symbol, s.price_move_pct)
    test = rel if s.sector_relative and rel is not None else move
    if test is not None and abs(test) >= thr and (not s.volatility_aware or z is None or abs(z) >= Z_MIN):
        out.append("price")
    if vr is not None and vr >= s.volume_multiple:
        out.append("volume")
    return out


def ready(event: dict, now: datetime) -> bool:
    """A results event is pushed once its numbers are built, or 6 h after the outcome regardless (the card then
    says the numbers are still being verified). Intimations alone ('what to watch') are never pushed."""
    if event["category"] != "results":
        return True
    outcomes = [t for t in event.get("timeline", []) if t["stage"] == "outcome"]
    if not outcomes:
        return False
    if event.get("detail"):
        return True
    first = min(datetime.fromisoformat(t["at"].replace("Z", "+00:00")) for t in outcomes)
    return now - first >= RESULTS_WAIT


def decide(sub: dict, cards: list[Card], events: dict[str, dict], sent_today: int, snoozed: dict, now: datetime,
           done: set[str]) -> list[Decision]:  # fmt: skip
    """Pure decision logic (tested without a DB or Telegram)."""
    s = subs.settings_of(sub)
    quiet = in_quiet_hours(now, s)
    budget_left = max(0, s.daily_budget - sent_today)
    out: list[Decision] = []
    normal: list[Decision] = []
    for c in cards:  # already ranked best-first
        ev = events[c.event_id]
        if c.event_id in done or not ready(ev, now) or c.category not in s.push_categories:
            continue
        crit = is_critical(c.category, ev)
        urgent = breaks_quiet_hours(c.category, ev)
        d = Decision(c, "critical" if crit else "normal", "queued")
        if c.category == "price_volume":
            fired = price_triggers(ev.get("detail") or {}, c.symbol, s)
            if not fired:
                continue  # below this subscriber's thresholds: not an alert for them at all
            d.trigger = "price_move" if "price" in fired else "volume_spike"
        if c.symbol in snoozed:
            d.status, d.reason = "suppressed", f"snoozed until {snoozed[c.symbol]:%Y-%m-%d %H:%M} UTC"
        elif not crit and c.score.total < MIN_PUSH_SCORE:
            d.status, d.reason = "suppressed", f"score {c.score.total:.2f} < {MIN_PUSH_SCORE} after your feedback"
        elif quiet and not urgent:
            d.status, d.reason = "held_quiet_hours", (f"quiet hours {s.quiet_start}–{s.quiet_end} IST (only M&A, "
                                                      "CEO exits and rating downgrades break through)")  # fmt: skip
        elif crit:
            d.status = "sent"
        else:
            normal.append(d)
        out.append(d)
    if normal:
        if s.batching and len(normal) >= 2 and budget_left >= 1:
            for d in normal:
                d.status = "batched"
        else:
            for i, d in enumerate(normal):
                d.status, d.reason = ("sent", None) if i < budget_left else ("over_budget", "daily budget reached")
    return out


def _messages_today(conn, sub_id: int, now: datetime) -> int:
    """Messages counted against the budget today: single non-critical sends + one per batch."""
    r = conn.execute(
        "select count(*) filter (where status = 'sent' and severity = 'normal' and trigger <> 'test') "
        "+ count(distinct batch_id) filter (where status = 'batched') as n from public.alerts "
        "where subscription_id = %s and sent_at >= %s",
        (sub_id, ist_day_start(now)),
    ).fetchone()
    return int(r["n"] or 0)


def _done(conn, sub_id: int) -> set[str]:
    rows = conn.execute(
        "select event_id from public.alerts where subscription_id = %s and status = any(%s)", (sub_id, list(FINAL))
    ).fetchall()
    return {r["event_id"] for r in rows}


def run_dispatch(conn, tg: Telegram, now: datetime) -> dict:
    from finn.push.bot import record_alert

    stats: dict = {"subscriptions": 0, "sent": 0, "batched": 0, "held_quiet_hours": 0, "over_budget": 0,
                   "suppressed": 0, "failed": 0}  # fmt: skip
    if not tg.available():
        stats["skipped"] = "TELEGRAM_BOT_TOKEN not set"
        return stats
    for sub in subs.all_subscriptions(conn):
        stats["subscriptions"] += 1
        weights = subs.weights_of(sub)
        since = max(now - LOOKBACK, sub["created_at"])
        evs = load_events(conn, sorted(weights), since)
        if not evs:
            continue
        cards = rank(evs, load_filings(conn, evs), weights, subs.rules(conn, sub["id"]), since)
        decisions = decide(sub, cards, {e["id"]: e for e in evs}, _messages_today(conn, sub["id"], now),
                           subs.snoozed(conn, sub["id"]), now, _done(conn, sub["id"]))  # fmt: skip
        batch = [d for d in decisions if d.status == "batched"]
        batch_id = uuid.uuid4().hex[:12] if batch else None
        for d in decisions:
            text = card_text(d.card)
            msg_id = None
            if d.status == "sent":
                try:
                    msg_id = tg.send(sub["chat_id"], text, buttons(d.card)).get("message_id")
                except TelegramError as e:
                    d.status, d.reason = "failed", str(e)[:200]
            record_alert(conn, sub["id"], d.card, d.trigger, d.status, d.card.headline, text, msg_id, d.reason,
                         batch_id if d.status == "batched" else None, d.severity)  # fmt: skip
            stats[d.status] = stats.get(d.status, 0) + 1
        if batch:
            try:
                tg.send(sub["chat_id"], batch_text([d.card for d in batch]), batch_buttons())
            except TelegramError as e:
                for d in batch:
                    record_alert(conn, sub["id"], d.card, d.trigger, "failed", d.card.headline, "", None, str(e))
                stats["failed"] += len(batch)
                stats["batched"] -= len(batch)
    return stats
