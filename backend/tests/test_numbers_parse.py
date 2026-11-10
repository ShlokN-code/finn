import pytest

from finn.numbers import approx_equal, deal_value_cr, parse_indian_number, parse_money, to_crore


@pytest.mark.parametrize(
    "text,expected",
    [("1,23,456.78", 123456.78), ("(1,234)", -1234.0), ("−5.5", -5.5), ("Rs. 12", 12.0), ("1234", 1234.0)],
)
def test_parse_indian_number(text, expected):
    assert parse_indian_number(text) == expected


@pytest.mark.parametrize(
    "text,default,cr,unit",
    [
        ("Rs 450 million", None, 45.0, "million"),
        ("₹12.5 lakh", None, 0.125, "lakh"),
        ("1,234 Cr", None, 1234.0, "crore"),
        ("Rs. 5 crores", None, 5.0, "crore"),
        ("USD-free 2.5 bn", None, 250.0, "billion"),
        ("1,00,000", "lakh", 1000.0, "lakh"),
        ("Rs 1,00,00,000", None, 1.0, "rupees"),
    ],
)
def test_parse_money_to_crore(text, default, cr, unit):
    v, raw, raw_unit = parse_money(text, default)
    assert approx_equal(v, cr, abs_tol=1e-9)
    assert raw_unit == unit
    assert raw.replace(",", "").strip("()")


def test_parse_money_never_guesses_unit():
    with pytest.raises(ValueError):
        parse_money("1,234.5")


def test_unit_words_dont_false_match():
    # 'Credit' must not be read as 'Cr'
    with pytest.raises(ValueError):
        parse_money("Credit facility of 500")


def test_to_crore_lakh_million():
    assert to_crore(250, "lakh") == 2.5
    assert to_crore(100, "million") == 10.0


def test_deal_value_cr():
    # 10,00,000 shares × ₹196.24 = ₹19.624 Cr
    assert approx_equal(deal_value_cr(1_000_000, 196.24), 19.624, abs_tol=1e-9)
