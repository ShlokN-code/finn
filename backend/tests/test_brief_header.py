"""Brief header numbers, season strip and feedback passthrough (Phase 4 contract)."""

from datetime import UTC, date, datetime, timedelta

import pytest

from finn.cards.brief import apply_actions
from finn.cards.build import NEUTRAL_SCORE, build_card
from finn.cards.counts import brief_counts, material_filings, round_minutes
from finn.cards.season import build_strip, season_quarter
from finn.models import FeedbackAction

NOW = datetime(2026, 11, 11, 10, 0, tzinfo=UTC)
CIT = {
    "source_type": "xbrl",
    "url": "https://x",
    "title": None,
    "exchange": "NSE",
    "page": None,
    "quote": None,
    "locator": None,
    "published_at": None,
    "retrieved_at": "2026-11-11T00:00:00Z",
}


def card(category, at, n_filings=1, eid=None, detail=None, stage="outcome"):
    timeline = [
        {"filing_id": f"{eid or category}-{i}", "stage": stage, "at": (at - timedelta(hours=i)).isoformat(),
         "label": "x"}
        for i in range(n_filings)
    ]  # fmt: skip
    e = {"id": eid or f"S:{category}", "symbol": "S", "category": category, "title": "t", "timeline": timeline,
         "detail": detail, "updated_at": at}  # fmt: skip
    return build_card(e, {}, NEUTRAL_SCORE)


@pytest.mark.parametrize("secs,mins", [(0, 0), (-50, 0), (89, 1), (90, 2), (539, 9), (600, 10), (2220, 35),
                                       (2280, 40), (3300, 55)])  # fmt: skip
def test_round_minutes(secs, mins):
    assert round_minutes(secs) == mins


def test_counts_match_the_spec_example():
    # Spec: "3 things matter · ~90 sec · 41 routine filings hidden · ~35 min saved"
    since = NOW - timedelta(days=1)
    cards = [card("results", NOW, 2, "a"), card("management_change", NOW, 1, "b"), card("mna", NOW, 1, "c"),
             card("results", NOW, 2, "d")]  # fmt: skip
    cards = cards[:3]  # 2 full cards + 1 one-liner, 4 filings in the window
    c = brief_counts(cards, hidden_n=41, since=since)
    assert (c.cards, c.one_liners, c.chips, c.material_filings) == (2, 1, 0, 4)
    assert c.read_seconds == 70
    # 41×30 + 4×180 − 70 = 1880 s ≈ 31.3 min → nearest 5
    assert c.est_minutes_saved == 30
    assert "est." in c.formula


def test_material_filings_only_inside_the_window():
    since = NOW - timedelta(hours=1, minutes=30)
    cards = [card("results", NOW, 3, "a")]  # filed now, −1 h, −2 h
    assert material_filings(cards, since) == 2
    assert material_filings(cards, None) == 3


def test_feedback_actions_applied_in_order_by_python():
    acts = [
        FeedbackAction(useful=False, scope="category", category="fund_raise", at=NOW),
        FeedbackAction(useful=False, scope="category", category="fund_raise", at=NOW + timedelta(seconds=5)),
    ]
    rules = apply_actions([], acts)
    assert len(rules) == 1 and rules[0].multiplier == pytest.approx(0.64) and rules[0].not_useful_count == 2


def test_season_quarter_window():
    assert season_quarter(date(2026, 11, 11)) == date(2026, 9, 30)
    assert season_quarter(date(2026, 9, 30)) is None  # quarter not over
    assert season_quarter(date(2026, 12, 15)) is None  # > 60 days after Q2
    assert season_quarter(date(2026, 6, 10)) == date(2026, 3, 31)  # Q4 allows 75 days


def _results_event(sym, at, pat_yoy, margin_bps, verification="cross_checked"):
    def fig(v, unit):
        return {"label": "x", "value": v, "unit": unit, "status": "verified", "basis": "consolidated",
                "period": None, "citation": CIT, "raw": None, "raw_unit": None, "check_note": None,
                "formula": None, "inputs": []}  # fmt: skip

    lines = [{"metric": "PAT", "yoy": fig(pat_yoy, "PCT")}, {"metric": "EBITDA margin", "yoy": fig(margin_bps, "BPS")}]
    return {"id": f"{sym}:results:Q2 FY27", "key": f"{sym}:results:Q2 FY27", "symbol": sym,
            "timeline": [{"stage": "intimation", "at": (at - timedelta(days=10)).isoformat()},
                         {"stage": "outcome", "at": at.isoformat()}],
            "detail": {"kind": "results", "verification": verification, "lines": lines}}  # fmt: skip


def test_season_strip_counts():
    at = NOW - timedelta(days=2)
    events = [
        _results_event("A", at, 12.0, 40),
        _results_event("B", at, -5.0, -120),
        _results_event("C", at, 30.0, 10, verification="mismatch"),  # reported, no numbers
        {
            "id": "D:results:Q2 FY27",
            "key": "D:results:Q2 FY27",
            "symbol": "D",
            "detail": None,
            "timeline": [{"stage": "intimation", "at": at.isoformat()}],
        },  # fmt: skip
        _results_event("F", NOW + timedelta(days=1), 1.0, 1),  # outcome after as_of → not yet reported
    ]
    s = build_strip(["A", "B", "C", "D", "E", "F"], events, NOW)
    assert s.quarter.label == "Q2 FY27"
    assert (s.total, s.reported, s.cross_checked) == (6, 3, 2)
    assert (s.pat_up, s.pat_down, s.margin_up, s.margin_down) == (1, 1, 1, 1)
    status = {r.symbol: r.status for r in s.rows}
    assert status == {"A": "reported", "B": "reported", "C": "reported", "D": "scheduled", "E": "awaited",
                      "F": "scheduled"}  # fmt: skip
    assert next(r for r in s.rows if r.symbol == "C").pat_yoy is None


def test_no_strip_outside_season():
    assert build_strip(["A"], [], datetime(2026, 12, 20, tzinfo=UTC)) is None
