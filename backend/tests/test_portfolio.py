from datetime import UTC, datetime, timedelta

from finn.cards.portfolio import status_for

NOW = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)


def ev(cat, impact, days_ago, so_what=None, sym="INFY"):
    return {"id": f"{sym}:{cat}:{days_ago}", "symbol": sym, "category": cat, "impact": impact, "so_what": so_what,
            "updated_at": NOW - timedelta(days=days_ago)}  # fmt: skip


def test_negative_material_event_is_pressure_and_names_it():
    s = status_for("INFY", [ev("results", "negative", 3)], 4.0, NOW)
    assert s.level == "pressure" and s.reason.startswith("Results tagged negative") and s.event_id


def test_sharp_fall_is_pressure_moderate_fall_is_watch():
    assert status_for("INFY", [], -16.0, NOW).level == "pressure"
    assert status_for("INFY", [], -9.0, NOW).level == "watch"
    assert status_for("INFY", [], -3.0, NOW).level == "intact"


def test_mixed_or_unexplained_move_is_watch_old_news_is_not():
    assert status_for("INFY", [ev("results", "mixed", 5)], 2.0, NOW).level == "watch"
    unexplained = ev("price_volume", None, 2, "No disclosure explains this move")
    assert status_for("INFY", [unexplained], 2.0, NOW).level == "watch"
    assert status_for("INFY", [ev("results", "negative", 40)], 2.0, NOW).level == "intact"


def test_unknown_without_prices_or_events():
    assert status_for("ZZZ", [], None, NOW).level == "unknown"
