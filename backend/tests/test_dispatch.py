"""Alert dispatch decisions: push categories, snooze, feedback floor, quiet hours + critical, budget, batching."""

from datetime import UTC, datetime, timedelta

from finn.cards.build import build_card
from finn.models import AlertSettings, ScoreBreakdown
from finn.push.dispatch import decide, in_quiet_hours, price_triggers, ready

DAY = datetime(2026, 11, 10, 6, 0, tzinfo=UTC)  # 11:30 IST
NIGHT = datetime(2026, 11, 10, 17, 30, tzinfo=UTC)  # 23:00 IST


def ev(sym, cat, detail=None, stage="outcome", at=DAY - timedelta(hours=1)):
    return {"id": f"{sym}:{cat}", "symbol": sym, "category": cat, "title": f"{sym} {cat}", "started_at": at,
            "timeline": [{"stage": stage, "filing_id": "f", "at": at.isoformat(), "label": "x"}],
            "detail": detail, "impact": None, "so_what": "x"}  # fmt: skip


def card(e, total=1.0):
    s = ScoreBreakdown(category_weight=1, position_weight=1, relevance=1, novelty=1, surprise=1, total=total)
    return build_card(e, {}, s)


def sub(**settings):
    return {"id": 1, "chat_id": 9, "holdings": [], "settings": AlertSettings(**settings).model_dump(mode="json")}


def run(events, now=DAY, sent_today=0, snoozed=None, done=None, totals=None, **settings):
    cards = [card(e, (totals or {}).get(e["id"], 1.0)) for e in events]
    return {d.card.event_id: (d.status, d.severity) for d in
            decide(sub(**settings), cards, {e["id"]: e for e in events}, sent_today, snoozed or {}, now,
                   done or set())}  # fmt: skip


LIT = ev("TATAPOWER", "litigation")
MGMT = ev("TATASTEEL", "management_change")
PLEDGE = ev("IDEA", "pledging")
CAPEX = ev("HAL", "capex")


def test_push_categories_only():
    assert "HAL:capex" not in run([CAPEX, LIT])  # capex is not a default push category


def test_batching_and_critical_sent_alone():
    out = run([LIT, PLEDGE, MGMT])
    assert out["TATASTEEL:management_change"] == ("sent", "critical")
    assert out["TATAPOWER:litigation"][0] == out["IDEA:pledging"][0] == "batched"


def test_single_normal_is_sent_and_budget():
    assert run([LIT])["TATAPOWER:litigation"][0] == "sent"
    assert run([LIT], sent_today=5)["TATAPOWER:litigation"][0] == "over_budget"
    assert run([LIT, PLEDGE], sent_today=5)["TATAPOWER:litigation"][0] == "over_budget"
    assert run([MGMT], sent_today=5)["TATASTEEL:management_change"][0] == "sent"  # critical not budgeted
    out = run([LIT, PLEDGE], sent_today=4, batching=False)
    assert sorted(s for s, _ in out.values()) == ["over_budget", "sent"]


def test_quiet_hours_hold_normal_but_not_critical():
    assert in_quiet_hours(NIGHT, AlertSettings()) and not in_quiet_hours(DAY, AlertSettings())
    out = run([LIT, MGMT], now=NIGHT)
    assert out["TATAPOWER:litigation"][0] == "held_quiet_hours" and out["TATASTEEL:management_change"][0] == "sent"


def test_snooze_and_feedback_floor_and_idempotency():
    assert run([LIT], snoozed={"TATAPOWER": DAY + timedelta(days=1)})["TATAPOWER:litigation"][0] == "suppressed"
    assert run([LIT], totals={"TATAPOWER:litigation": 0.1})["TATAPOWER:litigation"][0] == "suppressed"
    assert run([MGMT], totals={"TATASTEEL:management_change": 0.1})["TATASTEEL:management_change"][0] == "sent"
    assert run([LIT], done={"TATAPOWER:litigation"}) == {}


def test_results_wait_for_numbers_or_six_hours():
    fresh = ev("INFY", "results", at=DAY - timedelta(hours=1))
    assert not ready(fresh, DAY) and ready({**fresh, "detail": {"kind": "results"}}, DAY)
    assert ready(ev("INFY", "results", at=DAY - timedelta(hours=7)), DAY)
    assert not ready(ev("INFY", "results", stage="intimation"), DAY)


def pv_detail(move, rel, z, vr):
    from finn.models import Citation, Figure, PriceVolumeDetail

    c = Citation(source_type="price_feed", url="https://finance.yahoo.com/quote/X.NS/history", retrieved_at=DAY)

    def f(label, v, unit):
        return Figure(label=label, value=v, unit=unit, status="unverified", citation=c)

    return PriceVolumeDetail(trading_date=DAY.date(), move_pct=f("Move", move, "PCT"), z_score=z,
                             relative_move_pct=f("Move vs sector", rel, "PCT"),
                             volume_ratio=f("Volume", vr, "X")).model_dump(mode="json")  # fmt: skip


def test_price_volume_uses_subscriber_thresholds():
    d = pv_detail(-4.5, -1.0, -3.0, 1.2)
    assert price_triggers(d, "X", AlertSettings()) == []  # sector explains most of it
    assert price_triggers(d, "X", AlertSettings(sector_relative=False)) == ["price"]
    assert price_triggers(pv_detail(-1, -1, -1, 2.4), "X", AlertSettings()) == ["volume"]
    e = ev("X", "price_volume", detail=d)
    assert run([e]) == {}
    assert run([e], sector_relative=False)["X:price_volume"] == ("sent", "normal")
