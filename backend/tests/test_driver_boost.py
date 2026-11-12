from datetime import UTC, datetime

from finn.cards.brief import rank
from finn.ranking.drivers import match, touched

NOW = datetime(2026, 11, 12, 8, 0, tzinfo=UTC)


def ev(cat, title, sym="INFY", **kw):
    return {"id": f"{sym}:{cat}:{title[:8]}", "symbol": sym, "category": cat, "title": title, "so_what": None,
            "started_at": NOW, "updated_at": NOW, "impact": "positive", "timeline": [], **kw}  # fmt: skip


LINES = [{"metric": m, "current": {"value": 1}} for m in ("Revenue", "EBITDA margin", "PAT")]
RESULTS = {"kind": "results", "verification": "cross_checked", "lines": LINES}


def test_results_touch_growth_margins_profit_from_their_lines():
    assert touched(ev("results", "Q2 FY27 results", detail=RESULTS)) == {"Growth", "Margins", "Profit"}
    hidden = RESULTS | {"verification": "mismatch"}  # numbers hidden → no driver claim
    assert touched(ev("results", "Q2 FY27 results", detail=hidden)) == set()


def test_specific_words_match_generic_words_do_not():
    assert "Order book" in touched(ev("press_release", "Secures orders worth ₹1,200 crore from Indian Railways"))
    assert "Capacity" in touched(ev("press_release", "Commissioning of 300 MW solar capacity in Karnataka"))
    weak = touched(ev("press_release", "Company strengthens market presence and growth investment"))
    assert weak == set()  # 'growth', 'share', 'investment' are too weak to boost


def test_only_confirmed_drivers_of_that_company():
    e = ev("results", "Q2 FY27 results", detail=RESULTS)
    assert match(e, ["INFY:margins", "TCS:growth"]) == [("INFY:margins", "Margins")]
    assert match(e, []) == []


def test_boost_and_why_note_name_the_driver():
    e = ev("capex", "Board approves ₹2,000 crore expansion of capacity at Jamnagar")
    plain = rank([e], {}, {"INFY": 5.0}, [], None)[0]
    boosted = rank([e], {}, {"INFY": 5.0}, [], None, drivers=["INFY:capacity"])[0]
    assert (
        boosted.score.total == round(plain.score.total * 1.5, 4)
        or abs(boosted.score.total / plain.score.total - 1.5) < 1e-3
    )
    assert boosted.affects_drivers == ["Capacity"] and plain.affects_drivers == []
    assert any(n.startswith("affects: Capacity") for n in boosted.score.notes)
