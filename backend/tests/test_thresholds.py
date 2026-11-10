"""Price/volume triggers: ±%, per-stock override, volatility-aware z, sector-relative, volume multiple, explanations."""

import math
from datetime import UTC, date, datetime, timedelta

import pytest

from finn.models import AlertSettings
from finn.signals.price_volume import Bar, compute, explain, sector_index, triggers

DAY = date(2026, 11, 9)


def series(n=70, daily=0.01, last_ret=0.0, vol=1_000_000, last_vol=None, start=100.0):
    """Alternating ±daily returns (σ ≈ daily), then a final day with `last_ret`."""
    bars, p = [], start
    d0 = DAY - timedelta(days=n)
    for i in range(n):
        p *= 1 + (daily if i % 2 else -daily)
        bars.append(Bar(d0 + timedelta(days=i), p, p, vol))
    p *= 1 + last_ret
    bars.append(Bar(DAY, p, p, last_vol or vol))
    return bars


def idx(move_pct):
    return [Bar(DAY - timedelta(days=1), 100, 100, None), Bar(DAY, 100 + move_pct, 100 + move_pct, None)]


def sig(last_ret, daily=0.01, sector_move=None, last_vol=None):
    return compute("X", series(daily=daily, last_ret=last_ret, last_vol=last_vol), DAY, [], "^CNXIT",
                   idx(sector_move) if sector_move is not None else None, idx(0.2))  # fmt: skip


def test_default_threshold_and_z():
    s = sig(-0.05)
    assert s.move_pct == pytest.approx(-5.0) and s.z == pytest.approx(-5.0, rel=0.05)
    assert triggers(s, AlertSettings(sector_relative=False)) == ["price"]
    assert triggers(sig(-0.03), AlertSettings(sector_relative=False)) == []


def test_per_stock_override():
    st = AlertSettings(sector_relative=False, per_stock_pct={"X": 2.5})
    assert triggers(sig(-0.03), st) == ["price"]


def test_volatility_aware_suppresses_normal_moves_for_volatile_stocks():
    s = sig(0.05, daily=0.04)  # a 5 % day is ~1.2σ for a stock that moves 4 % a day
    assert abs(s.z) < 2
    assert triggers(s, AlertSettings(sector_relative=False)) == []
    assert triggers(s, AlertSettings(sector_relative=False, volatility_aware=False)) == ["price"]


def test_sector_relative_uses_stock_minus_sector():
    s = sig(-0.05, sector_move=-4.5)
    assert s.relative_move_pct == pytest.approx(-0.5)
    assert triggers(s, AlertSettings()) == []  # the sector explains it
    assert triggers(s, AlertSettings(sector_relative=False)) == ["price"]


def test_volume_multiple():
    s = sig(0.0, last_vol=2_500_000)
    assert s.volume_ratio == pytest.approx(2.5)
    assert triggers(s, AlertSettings()) == ["volume"]
    assert triggers(s, AlertSettings(volume_multiple=3)) == []


def test_explanation_order():
    s = sig(-0.06, sector_move=-4.0)
    filed = datetime(2026, 11, 8, 18, 0, tzinfo=UTC)  # after the previous close (IST 23:30 on 8 Nov)
    f = {"filed_at": filed, "category": "credit_rating", "subject": "Rating downgraded", "attachment_url": "u"}
    d = {"kind": "block", "client": "ABC FUND", "side": "SELL", "value_cr": 210.5}
    ex = explain(s, [f], [d], DAY - timedelta(days=1))
    assert [e.kind for e in ex] == ["filing", "bulk_block_deal", "sector_move"]
    assert "sold ₹210.5 Cr" in ex[1].text
    assert explain(sig(-0.06, sector_move=-1.0), [], [], DAY - timedelta(days=1))[0].kind == "none"


def test_filing_outside_window_does_not_explain():
    s = sig(-0.06)
    old = {"filed_at": datetime(2026, 11, 1, tzinfo=UTC), "category": "results", "subject": "x"}
    assert explain(s, [old], [], DAY - timedelta(days=1))[0].kind == "none"


def test_sector_mapping():
    assert sector_index("HDFCBANK", "Banks") == "^NSEBANK"
    assert sector_index("BAJFINANCE", "Finance") == "NIFTY_FIN_SERVICE.NS"
    assert sector_index("HAL", None) == "^CNXPSE"
    assert sector_index("ZZZ", None) == "^NSEI"


def test_nan_free():
    s = sig(0.0)
    assert not math.isnan(s.move_pct)


def test_outcome_beats_newspaper_ad():
    s = sig(0.12)
    prev = DAY - timedelta(days=3)  # Friday; results filed Saturday, ad filed Monday
    outcome = {
        "filed_at": datetime(2026, 11, 7, 6, 26, tzinfo=UTC),
        "category": "results",
        "stage": "outcome",
        "subject": "Divi's Laboratories Limited has submitted to the Exchange, the financial results",
    }
    ad = {
        "filed_at": datetime(2026, 11, 9, 6, 42, tzinfo=UTC),
        "category": "results",
        "stage": "newspaper_ad",
        "subject": "Divi's Laboratories Limited has informed the Exchange about Copy of Newspaper Publication",
    }
    e = explain(s, [ad, outcome], [], prev)[0]
    assert e.kind == "filing" and "07 Nov" in e.text and e.text.endswith("the financial results")
