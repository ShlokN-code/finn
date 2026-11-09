from decimal import Decimal

import pytest

from finn.numbers import approx_equal, pct_change, round_display, to_crore


def test_to_crore_units():
    assert to_crore(123456.78, "lakh") == pytest.approx(1234.5678)
    assert to_crore(4924.4, "million") == pytest.approx(492.44)
    assert to_crore(407190000000, "rupees") == pytest.approx(40719.0)
    assert to_crore(49244, "crore") == 49244
    with pytest.raises(ValueError):
        to_crore(1, "thousand")


def test_approx_equal_handles_float_noise_and_source_rounding():
    assert approx_equal(0.1 + 0.2, 0.3)
    assert approx_equal(49244.0, 49243.6)  # screener rounds to whole crore
    assert not approx_equal(49244.0, 49100.0)


def test_pct_change_tiny_or_negative_base():
    assert pct_change(110, 100) == pytest.approx(10.0)
    assert pct_change(10, -5) is None  # loss → profit: not meaningful
    assert pct_change(10, 0) is None


def test_round_display_half_up():
    assert round_display(2.675, 2) == Decimal("2.68")  # plain round() gives 2.67
    assert round_display(12.25, 1) == Decimal("12.3")
    assert round_display(-1.25, 1) == Decimal("-1.3")
