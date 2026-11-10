from datetime import UTC, date, datetime, timedelta

import pytest

from finn.ranking.feedback import apply_feedback, effective_multiplier, reset
from finn.ranking.score import position_weight, repeat_counts, score

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)


def ev(category="results", symbol="INFY", started=NOW, eid=None, impact=None, detail=None, timeline=None):
    return {"id": eid or f"{symbol}:{category}:{started:%Y-%m-%d}", "symbol": symbol, "category": category,
            "started_at": started, "impact": impact, "detail": detail, "driver_ids": [],
            "timeline": timeline or [{"stage": "outcome", "at": started.isoformat()}]}  # fmt: skip


@pytest.mark.parametrize("w,expected", [(2, 0.80), (15, 1.50), (100, 1.8), (None, 0.4), (0, 0.4)])
def test_position_curve(w, expected):
    assert position_weight(w) == pytest.approx(expected, abs=0.01)


def test_formula_is_the_product_of_factors():
    s = score(ev(impact="negative"), 10, [])
    assert s.total == pytest.approx(s.category_weight * s.position_weight * s.relevance * s.novelty * s.surprise,
                                    rel=1e-3)  # fmt: skip
    assert s.relevance == 1.2 and s.category_weight == 1.0 and any("Impact" in n for n in s.notes)


def test_big_event_in_small_holding_can_beat_small_event_in_big_holding():
    big_small = score(ev("results", "A", impact="negative"), 2, [])
    small_big = score(ev("fund_raise", "B", impact="neutral"), 20, [])
    assert big_small.total > small_big.total


def test_not_useful_scopes_and_bounds():
    rules = apply_feedback([], useful=False, scope="stock", symbol="IDEA")
    rules = apply_feedback(rules, useful=False, scope="stock", symbol="IDEA")
    m, notes = effective_multiplier(rules, "IDEA", "press_release", "e1")
    assert m == pytest.approx(0.64) and notes
    assert effective_multiplier(rules, "INFY", "press_release", "e1")[0] == 1.0
    for _ in range(30):
        rules = apply_feedback(rules, useful=False, scope="stock", symbol="IDEA")
    assert effective_multiplier(rules, "IDEA", "x", "e")[0] == pytest.approx(0.1)  # bounded
    rules = apply_feedback(rules, useful=True, scope="category", category="press_release")
    assert effective_multiplier(rules, "IDEA", "press_release", "e")[0] == pytest.approx(0.1 * 1.25)


def test_rules_compose_and_reset():
    rules = apply_feedback([], useful=False, scope="category", category="fund_raise")
    rules = apply_feedback(rules, useful=False, scope="stock_category", symbol="BAJFINANCE", category="fund_raise")
    assert effective_multiplier(rules, "BAJFINANCE", "fund_raise", "e")[0] == pytest.approx(0.64)
    assert effective_multiplier(rules, "INFY", "fund_raise", "e")[0] == pytest.approx(0.8)
    assert len(reset(rules, "category:fund_raise")) == 1 and reset(rules) == []


def test_critical_floor():
    rules = []
    for _ in range(20):
        rules = apply_feedback(rules, useful=False, scope="category", category="results")
        rules = apply_feedback(rules, useful=False, scope="category", category="press_release")
    assert score(ev("results"), 5, rules).category_weight == pytest.approx(0.5)  # floor: half of 1.0
    assert score(ev("press_release"), 5, rules).category_weight == pytest.approx(0.05)  # no floor
    down = {"kind": "one_liner", "line": {}, "direction": "down"}
    assert score(ev("credit_rating", detail=down), 5, rules + [r for r in apply_feedback(
        [], useful=False, scope="category", category="credit_rating")]).category_weight >= 0.45  # fmt: skip


def test_novelty_and_repeats():
    since = NOW - timedelta(hours=12)
    old = ev(started=NOW - timedelta(days=3), timeline=[
        {"stage": "outcome", "at": (NOW - timedelta(days=3)).isoformat()},
        {"stage": "newspaper_ad", "at": (NOW - timedelta(hours=2)).isoformat()}])  # fmt: skip
    assert score(old, 5, [], since=since).novelty == 0.3  # only an ad is new
    fresh_outcome = ev(started=NOW - timedelta(days=20), timeline=[
        {"stage": "intimation", "at": (NOW - timedelta(days=20)).isoformat()},
        {"stage": "outcome", "at": (NOW - timedelta(hours=10)).isoformat()},
        {"stage": "newspaper_ad", "at": (NOW - timedelta(hours=2)).isoformat()}])  # fmt: skip
    assert score(fresh_outcome, 5, [], since=since).novelty == 1.0
    assert score(ev(), 5, [], since=since).novelty == 1.0
    ncds = [ev("fund_raise", "BAJFINANCE", NOW - timedelta(days=d), eid=f"n{d}") for d in (21, 14, 7, 0)]
    reps = repeat_counts(ncds)
    assert reps["n0"] == 3 and reps["n21"] == 0
    assert score(ncds[-1], 5, [], repeats=reps["n0"]).novelty == pytest.approx(0.125)


def test_surprise_results_and_price():
    d = {"kind": "results", "verification": "cross_checked", "trend_pat_yoy_pct": 10.0,
         "lines": [{"metric": "PAT", "yoy": {"value": -20.0}}]}  # fmt: skip
    assert score(ev(detail=d), 5, []).surprise == 2.0
    d["lines"][0]["yoy"]["value"] = 15.0
    assert score(ev(detail=d), 5, []).surprise == pytest.approx(1.25)
    pv = {"kind": "price_volume", "z_score": -3.0}
    assert score(ev("price_volume", detail=pv), 5, []).surprise == pytest.approx(1.5)


def test_surprise_ignores_low_base_effects():
    from finn.extraction.results.build import trend_pat_yoy
    from finn.sources.screener import QuarterTable

    # TATASTEEL's screener Net Profit, Sep 2024 … Sep 2026
    ends = [date(2024, 9, 30), date(2024, 12, 31), date(2025, 3, 31), date(2025, 6, 30), date(2025, 9, 30),
            date(2025, 12, 31), date(2026, 3, 31), date(2026, 6, 30), date(2026, 9, 30)]  # fmt: skip
    np_ = [759, 295, 1201, 2007, 3183, 2730, 2965, 2385, 3700]
    t = QuarterTable("TATASTEEL", "consolidated", "u", "Rs. Crores", ends, {"Net Profit": np_})
    assert trend_pat_yoy(t, ends[-1]) is None  # only one comparable YoY (+18.8%) left → no surprise factor
    d = {"kind": "results", "verification": "cross_checked", "trend_pat_yoy_pct": None,
         "lines": [{"metric": "PAT", "yoy": {"value": 16.2}}]}  # fmt: skip
    assert score(ev(detail=d), 5, []).surprise == 1.0
    # median, not mean: one outlier doesn't swing the trend
    t2 = QuarterTable("X", "consolidated", "u", "Rs. Crores", ends, {"Net Profit": [100, 100, 100, 100, 110, 112,
                                                                                    195, 115, 120]})  # fmt: skip
    assert trend_pat_yoy(t2, ends[-1]) == pytest.approx(13.5)  # median of 10, 12, 95, 15
    d["trend_pat_yoy_pct"], d["lines"][0]["yoy"]["value"] = 10.0, 150.0
    assert score(ev(detail=d), 5, []).surprise == 1.0  # current YoY off a low base
