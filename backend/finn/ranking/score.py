"""score = category_weight × position_weight × relevance × novelty × surprise (PRODUCT §5).

Pure functions; every factor is explained in ScoreBreakdown.notes for "Why is this #1?". Constants are
documented in DECISIONS.md ("Ranking constants") — change them there and here together.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from finn.constants import BASE_EFFECT_PCT
from finn.models import Category, ScoreBreakdown, WeightRule
from finn.ranking.feedback import effective_multiplier

BASE_WEIGHT: dict[str, float] = {
    Category.results: 1.0, Category.mna: 0.95, Category.management_change: 0.9, Category.credit_rating: 0.8,
    Category.litigation: 0.8, Category.pledging: 0.8, Category.price_volume: 0.7, Category.capex: 0.6,
    Category.press_release: 0.5, Category.insider_trading: 0.5, Category.fund_raise: 0.4,
    Category.dividend: 0.3, Category.bonus_split: 0.3, Category.earnings_call: 0.25, Category.agm_egm: 0.25,
    Category.postal_ballot: 0.25, Category.investor_meetings: 0.0, Category.routine: 0.0,
    Category.unclassified: 0.0,
}  # fmt: skip
# Direction-specific bases (decided in code from extracted facts, never by the model).
RATING_DOWN, RATING_OTHER = 0.9, 0.5
PLEDGE_UP, PLEDGE_DOWN = 0.8, 0.4

HIDDEN = {Category.investor_meetings, Category.routine, Category.unclassified}
CRITICAL = {Category.results, Category.mna, Category.management_change}  # + rating downgrades (is_critical)
FLOOR_SHARE = 0.5  # critical categories never fall below half their base weight

POS_A, POS_B, POS_CAP, NOT_HELD = 0.40, 0.285, 1.8, 0.4
RELEVANCE = {"positive": 1.2, "negative": 1.2, "mixed": 1.1, "neutral": 0.8}
DRIVER_BOOST = 1.5
NOVELTY_STAGE = {"outcome": 1.0, "intimation": 0.5, "presentation": 0.6, "call": 0.6, "transcript": 0.6,
                 "newspaper_ad": 0.3, "clarification": 0.3, "other": 0.5}  # fmt: skip
REPEAT_DECAY, REPEAT_WINDOW_DAYS, REPEAT_MIN = 0.5, 30, 0.125


def direction(event: dict) -> str | None:
    d = event.get("detail") or {}
    return d.get("direction") if d.get("kind") == "one_liner" else None


def is_critical(category: str, event: dict | None = None) -> bool:
    if category in CRITICAL:
        return True
    return category == Category.credit_rating and event is not None and direction(event) == "down"


def base_weight(category: str, event: dict | None = None) -> float:
    if category == Category.credit_rating and event is not None:
        return (
            RATING_DOWN if direction(event) == "down" else RATING_OTHER if direction(event) else BASE_WEIGHT[category]
        )
    if category == Category.pledging and event is not None and direction(event) == "down":
        return PLEDGE_DOWN
    return BASE_WEIGHT.get(category, 0.3)


def position_weight(weight_pct: float | None) -> float:
    """≈0.80 at 2 %, ≈1.50 at 15 %, capped at 1.8 so a big event in a small holding can still top the list."""
    if not weight_pct or weight_pct <= 0:
        return NOT_HELD
    return min(POS_CAP, POS_A + POS_B * math.sqrt(weight_pct))


def relevance(impact: str | None, event_driver_ids: list[str], confirmed: dict[str, str]) -> tuple[float, list[str]]:
    """Level 0 impact tag; Level 1 boost when the event touches a confirmed driver (id → label)."""
    r = RELEVANCE.get(impact or "", 1.0)
    notes = [f"Impact: {impact} (×{r})"] if impact else ["Impact not tagged (×1.0)"]
    hit = [confirmed[d] for d in event_driver_ids if d in confirmed]
    if hit:
        r *= DRIVER_BOOST
        notes.append(f"affects: {', '.join(hit)} — a driver you're watching (×{DRIVER_BOOST})")
    return r, notes


def novelty(event: dict, since: datetime | None, repeats: int) -> tuple[float, list[str]]:
    started = event["started_at"]
    if since is None or started >= since:
        n, why = 1.0, "New event"
    else:
        # The most substantive filing inside the window counts: results landing this week is news even if a
        # newspaper ad followed it.
        items = [t for t in event.get("timeline", []) if _ts(t["at"]) >= since]
        best = max(items, key=lambda t: NOVELTY_STAGE.get(t["stage"], 0.5), default=None)
        n = NOVELTY_STAGE.get(best["stage"], 0.5) if best else 0.3
        why = f"Update to an earlier event ({best['stage'] if best else 'no new filing'})"
    notes = [f"{why} (×{n})"]
    if repeats:
        d = max(REPEAT_MIN, REPEAT_DECAY**repeats)
        n *= d
        notes.append(f"{repeats} similar filing(s) in the previous {REPEAT_WINDOW_DAYS} days (×{d:g})")
    return n, notes


def surprise(event: dict) -> tuple[float, list[str]]:
    d = event.get("detail") or {}
    if d.get("kind") == "results" and d.get("verification") != "mismatch":
        trend = d.get("trend_pat_yoy_pct")
        pat = next((ln for ln in d.get("lines", []) if ln["metric"] == "PAT"), None)
        yoy = (pat or {}).get("yoy") or {}
        if trend is not None and yoy.get("value") is not None:
            if yoy["value"] > BASE_EFFECT_PCT:  # low base: growth % says little about surprise
                return 1.0, [f"PAT YoY {yoy['value']:+.0f}% is off a low base — no surprise factor"]
            gap = abs(yoy["value"] - trend)
            s = 1 + min(1.0, gap / 20.0)
            return s, [f"PAT YoY {yoy['value']:+.1f}% vs {trend:+.1f}% trailing median (×{s:.2f})"]
    if d.get("kind") == "price_volume" and d.get("z_score") is not None:
        s = min(2.0, max(1.0, abs(d["z_score"]) / 2))
        return s, [f"Move is {abs(d['z_score']):.1f}σ for this stock (×{s:.2f})"]
    return 1.0, []


def score(
    event: dict,
    weight_pct: float | None,
    rules: list[WeightRule],
    since: datetime | None = None,
    repeats: int = 0,
    confirmed_drivers: dict[str, str] | None = None,
) -> ScoreBreakdown:
    cat = event["category"]
    base = base_weight(cat, event)
    mult, mult_notes = effective_multiplier(rules, event["symbol"], cat, event["id"])
    cw = base * mult
    notes = [f"{cat.replace('_', ' ')}: base weight {base}"] + mult_notes
    if is_critical(cat, event) and cw < base * FLOOR_SHARE:
        cw = base * FLOOR_SHARE
        notes.append(f"Critical category floor: never below {FLOOR_SHARE:g}× base")
    pw = position_weight(weight_pct)
    notes.append(f"Position {weight_pct:g}% of portfolio (×{pw:.2f})" if weight_pct else f"Not held (×{pw})")
    rel, n1 = relevance(event.get("impact"), event.get("driver_ids") or [], confirmed_drivers or {})
    nov, n2 = novelty(event, since, repeats)
    sur, n3 = surprise(event)
    total = cw * pw * rel * nov * sur
    return ScoreBreakdown(category_weight=round(cw, 4), position_weight=round(pw, 4), relevance=round(rel, 4),
                          novelty=round(nov, 4), surprise=round(sur, 4), total=round(total, 4),
                          notes=notes + n1 + n2 + n3)  # fmt: skip


def repeat_counts(events: list[dict]) -> dict[str, int]:
    """For each event: earlier events of the same symbol+category started within REPEAT_WINDOW_DAYS before it
    (BAJFINANCE's weekly NCD allotments decay instead of each scoring like news)."""
    out: dict[str, int] = {}
    by_key: dict[tuple[str, str], list[dict]] = {}
    for e in events:
        by_key.setdefault((e["symbol"], e["category"]), []).append(e)
    for group in by_key.values():
        group.sort(key=lambda e: e["started_at"])
        for i, e in enumerate(group):
            lo = e["started_at"] - timedelta(days=REPEAT_WINDOW_DAYS)
            out[e["id"]] = sum(1 for p in group[:i] if p["started_at"] >= lo)
    return out


def _ts(x) -> datetime:
    return x if isinstance(x, datetime) else datetime.fromisoformat(str(x).replace("Z", "+00:00"))
