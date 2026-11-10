from datetime import UTC, date, datetime

import pytest

from finn.calendar import (
    fy_of,
    is_market_hours,
    is_trading_day,
    parse_ist,
    previous_trading_day,
    quarter_period,
    results_quarter_for,
)


@pytest.mark.parametrize(
    "qe,label",
    [
        (date(2026, 9, 30), "Q2 FY27"),
        (date(2026, 12, 31), "Q3 FY27"),
        (date(2027, 3, 31), "Q4 FY27"),
        (date(2026, 6, 30), "Q1 FY27"),
        (date(2026, 3, 31), "Q4 FY26"),
    ],
)
def test_quarter_labels(qe, label):
    p = quarter_period(qe)
    assert p.label == label and p.end == qe and (p.end - p.start).days in (89, 90, 91)


def test_quarter_period_rejects_non_quarter_end():
    with pytest.raises(ValueError):
        quarter_period(date(2026, 9, 29))


def test_fy_of():
    assert fy_of(date(2026, 4, 1)) == 2027 and fy_of(date(2026, 3, 31)) == 2026


@pytest.mark.parametrize(
    "filed,qe",
    [
        (date(2026, 10, 3), date(2026, 9, 30)),  # intimation after quarter end
        (date(2026, 9, 20), date(2026, 9, 30)),  # intimation in the last 2 weeks of the quarter
        (date(2026, 11, 1), date(2026, 9, 30)),  # transcript
        (date(2026, 5, 28), date(2026, 3, 31)),  # Q4 audited results, late May
        (date(2026, 12, 20), date(2026, 12, 31)),
    ],
)
def test_results_quarter_inference(filed, qe):
    assert results_quarter_for(filed) == qe


def test_holidays_and_trading_days():
    assert not is_trading_day(date(2026, 11, 10))  # Diwali-Balipratipada
    assert not is_trading_day(date(2026, 11, 7))  # Saturday
    assert is_trading_day(date(2026, 11, 9))
    assert previous_trading_day(date(2026, 11, 11)) == date(2026, 11, 9)


def test_market_hours_ist():
    assert is_market_hours(datetime(2026, 11, 11, 5, 0, tzinfo=UTC))  # 10:30 IST
    assert not is_market_hours(datetime(2026, 11, 11, 11, 0, tzinfo=UTC))  # 16:30 IST
    assert not is_market_hours(datetime(2026, 11, 10, 5, 0, tzinfo=UTC))  # holiday


def test_parse_ist_to_utc():
    assert parse_ist("04-Nov-2026 21:01:36", "%d-%b-%Y %H:%M:%S") == datetime(2026, 11, 4, 15, 31, 36, tzinfo=UTC)
