"""Ex-date handling: the mechanical move of a dividend/bonus/split never alerts; a genuine move beyond it does."""

from datetime import date, timedelta

import pytest

from finn.models import AlertSettings
from finn.signals.price_volume import Action, Bar, compute, mechanical_factor, triggers

DAY = date(2026, 11, 9)
ST = AlertSettings(sector_relative=False)


def flat(n=40, price=500.0, vol=1_000_000):
    d0 = DAY - timedelta(days=n)
    return [Bar(d0 + timedelta(days=i), price * (1.005 if i % 2 else 0.995), price * (1.005 if i % 2 else 0.995),
                vol) for i in range(n)]  # fmt: skip


def run(bars, actions):
    return compute("X", bars, DAY, actions, "^NSEI", None, None)


def test_bonus_restated_by_yahoo_is_a_normal_day():
    bars = flat() + [Bar(DAY, 500.0, 500.0, 1_000_000)]  # Yahoo already halved history → no visible drop
    s = run(bars, [Action(DAY, "bonus", "Bonus 1:1", 1, 1)])
    assert s.mechanical_pct is None and abs(s.move_pct) < 1 and s.day_label == "Bonus 1:1 ex-date today"
    assert triggers(s, ST) == []


def test_bonus_not_yet_restated_removes_mechanical_half():
    bars = flat() + [Bar(DAY, 250.0, 250.0, 2_000_000)]  # raw −50 %, volume ×2 on the new share count
    s = run(bars, [Action(DAY, "bonus", "Bonus 1:1", 1, 1)])
    assert s.mechanical_pct == pytest.approx(-50) and s.raw_move_pct == pytest.approx(-50, abs=1)
    assert abs(s.move_pct) < 1 and s.volume_ratio == pytest.approx(1.0, abs=0.05)
    assert triggers(s, ST) == []


def test_genuine_move_beyond_the_bonus_still_alerts():
    bars = flat() + [Bar(DAY, 225.0, 225.0, 1_000_000)]  # −55 % raw = −50 % bonus × −10 % genuine
    s = run(bars, [Action(DAY, "bonus", "Bonus 1:1", 1, 1)])
    assert s.move_pct == pytest.approx(-10, abs=1)
    assert "price" in triggers(s, ST)


def test_split_and_combined_split_plus_bonus():
    assert mechanical_factor(Action(DAY, "split", "FV 2→1", 2, 1), 500) == pytest.approx(0.5)
    bars = flat(price=1000) + [Bar(DAY, 100.0, 100.0, 1_000_000)]  # BAJFINANCE-style 1:2 split + 4:1 bonus
    acts = [Action(DAY, "split", "Split", 2, 1), Action(DAY, "bonus", "Bonus 4:1", 4, 1)]
    s = run(bars, acts)
    assert s.mechanical_pct is not None and abs(s.move_pct) < 1 and triggers(s, ST) == []


def test_dividend_via_adj_close_and_large_special_dividend():
    small = flat() + [Bar(DAY, 492.0, 500.0, 1_000_000)]  # ₹8 dividend: close drops, adj_close doesn't
    s = run(small, [Action(DAY, "dividend", "Dividend - Rs 8", amount_per_share=8)])
    assert abs(s.move_pct) < 1 and s.day_label == "Ex-dividend today (₹8/share)"
    special = flat() + [Bar(DAY, 400.0, 400.0, 1_000_000)]  # ₹100 special dividend, adj_close not yet restated
    s = run(special, [Action(DAY, "dividend", "Special dividend Rs 100", amount_per_share=100)])
    assert s.mechanical_pct == pytest.approx(-20, abs=0.5) and abs(s.move_pct) < 1
