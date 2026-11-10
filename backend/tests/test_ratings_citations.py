import pytest

from finn.citations import quote_in_text
from finn.ranking.ratings import direction, parse


@pytest.mark.parametrize("old,new,d", [
    ("CRISIL AA+/Stable", "CRISIL AA/Negative", "down"),
    ("[ICRA]AA-(Stable)", "[ICRA]AA (Stable)", "up"),
    ("IND A1+", "IND A1+", "unchanged"),
    (None, "CARE AAA; Stable", "new"),
    ("CRISIL AA", "CRISIL A1+", None),  # long vs short term: not comparable
])  # fmt: skip
def test_rating_direction(old, new, d):
    assert direction(old, new) == d


def test_parse():
    assert parse("CARE BBB-") == ("long", 9) and parse("nothing") is None


def test_quote_fuzzy():
    text = "The Board approved the appointment of Mr. A. Kumar as\nChief  Financial Officer w.e.f. 1st December, 2026."
    assert quote_in_text("appointment of Mr. A. Kumar as Chief Financial Officer", text)
    assert quote_in_text("appointment of Mr A Kumar as Chief Financial Oficer", text)  # OCR-ish noise
    assert not quote_in_text("resignation of the Managing Director", text)
