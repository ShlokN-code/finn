"""Stored Event (+ its filings) → Card. Cards are computed on read, never stored (DECISIONS: contracts).

The builder is pure: callers pass the event row, the filings it references and a ScoreBreakdown.
Imports nothing that needs job-only dependencies, so it runs on Render.
"""

from __future__ import annotations

from datetime import UTC, datetime

from finn.models import Card, Citation, Figure, ScoreBreakdown

CARD_TYPE = {
    "results": "results",
    "management_change": "management_change",
    "price_volume": "price_volume",
    "dividend": "inline_chip",
    "bonus_split": "inline_chip",
}

CATEGORY_LABEL = {
    "results": "Results", "mna": "M&A", "management_change": "Management change", "litigation": "Litigation",
    "credit_rating": "Credit rating", "pledging": "Pledging", "capex": "Capex", "press_release": "Press release",
    "insider_trading": "Insider trade", "fund_raise": "Fund raise", "dividend": "Dividend",
    "bonus_split": "Bonus / split", "earnings_call": "Earnings call", "agm_egm": "AGM / EGM",
    "postal_ballot": "Postal ballot", "price_volume": "Price / volume",
}  # fmt: skip

ASK_CHIPS = {
    "results": ["What drove the margin change?", "How does this compare with guidance?", "Show the segment split"],
    "management_change": ["What did they do before?", "Why did the predecessor leave?", "Any other exits this year?"],
    "price_volume": ["What else was filed recently?", "Who traded in bulk today?", "How did the sector move?"],
    "mna": ["What is the deal value?", "How is it funded?", "What does management say it adds?"],
    "credit_rating": ["What did the agency cite?", "What's the debt profile?", "Any rating history?"],
    "fund_raise": ["What will the money fund?", "What does it do to leverage?", "How often do they raise?"],
}  # fmt: skip
DEFAULT_CHIPS = ["What does this mean for the business?", "Has this happened before?", "Show the filing"]

NEXT_ACTION = {
    "results": "Check margins against guidance",
    "management_change": "Read the appointee's profile in the filing",
    "price_volume": "Look for a filing or deal behind the move",
    "credit_rating": "Read the agency's rationale",
    "mna": "Read the deal terms",
}


def card_type(event: dict) -> str:
    cat = event["category"]
    if cat == "results" and not any(t["stage"] == "outcome" for t in event.get("timeline", [])):
        return "what_to_watch"  # board meeting announced, results not out yet
    return CARD_TYPE.get(cat, "one_liner")


def _citation(f: dict) -> Citation | None:
    url = f.get("attachment_url") or f.get("xbrl_url")
    if not url:
        return None
    return Citation(
        source_type="exchange_filing", url=url, title=(f.get("subject") or "")[:120] or None,
        exchange=f.get("exchange") or "NSE", published_at=f.get("filed_at"),
        retrieved_at=f.get("fetched_at") or f.get("filed_at") or datetime.now(UTC),
    )  # fmt: skip


def _key_figures(event: dict) -> list[Figure]:
    d = event.get("detail") or {}
    kind = d.get("kind")
    if kind == "results":
        if d.get("verification") == "mismatch":
            return []  # "Couldn't verify — open filing": no numbers
        return [Figure.model_validate(ln["current"]) for ln in d.get("lines", [])]
    if kind == "price_volume":
        out = [Figure.model_validate(d["move_pct"])]
        if d.get("volume_ratio"):
            out.append(Figure.model_validate(d["volume_ratio"]))
        return out
    if kind in ("one_liner", "chip") and d.get("key_figure" if kind == "one_liner" else "amount"):
        return [Figure.model_validate(d["key_figure" if kind == "one_liner" else "amount"])]
    return []


def default_so_what(event: dict) -> str:
    ct = card_type(event)
    if ct == "what_to_watch":
        return "Results due — see what they will test"
    return {
        "management_change": "Leadership change — check who and why",
        "mna": "Deal announced — check size and fit",
        "litigation": "Legal matter disclosed — check the exposure",
        "credit_rating": "Rating action — check direction and reasons",
        "fund_raise": "Raising money — check size and use",
        "dividend": "Dividend declared",
        "bonus_split": "Share count changes; value doesn't",
    }.get(event["category"], f"{CATEGORY_LABEL.get(event['category'], 'Update')} filed")


def build_card(event: dict, filings: dict[str, dict], score: ScoreBreakdown, now: datetime | None = None) -> Card:
    """event: an `events` row (dict, JSON columns decoded); filings: id → filings row for its timeline."""
    timeline = event.get("timeline") or []
    ordered = sorted(timeline, key=lambda t: (t["stage"] != "outcome", t["at"]))  # outcome first = primary chip
    sources = [c for t in ordered if (f := filings.get(t["filing_id"])) and (c := _citation(f))]
    detail = event.get("detail")
    if detail and detail.get("kind") == "results" and detail.get("filing_url"):
        primary = next((s for s in sources if s.url == detail["filing_url"]), None)
        if primary:
            sources = [primary] + [s for s in sources if s is not primary]
    as_of = event.get("detail_at") or event.get("refreshed_at") or event.get("updated_at") or now or datetime.now(UTC)
    return Card(
        id=event["id"], event_id=event["id"], symbol=event["symbol"], card_type=card_type(event),
        category=event["category"], impact=event.get("impact"), impact_reason=event.get("impact_reason"),
        headline=event["title"], so_what=event.get("so_what") or default_so_what(event),
        key_figures=_key_figures(event), sources=sources[:4], timeline=timeline,
        next_action=NEXT_ACTION.get(event["category"]),
        ask_chips=ASK_CHIPS.get(event["category"], DEFAULT_CHIPS)[:3],
        affects_drivers=[], detail=detail, score=score, as_of=as_of,
    )  # fmt: skip


NEUTRAL_SCORE = ScoreBreakdown(category_weight=1, position_weight=1, relevance=1, novelty=1, surprise=1, total=1,
                               notes=["Unranked (opened directly)"])  # fmt: skip
