"""Deck lookup validation: a deck figure needs its number and its metric's name on the cited page."""

from datetime import date

from finn.models.research import Promise
from finn.research import deck
from finn.research.ledger import build_ledger
from tests.test_ledger import call, g


def _promise(metric="credit cost", key="credit_cost") -> Promise:
    led = build_ledger("T", [call(1, date(2025, 7, 20), [g(key, 1.85, 1.95, metric=metric, fy=2026)])], None,
                       date(2026, 11, 11))  # fmt: skip
    return led.promises[0]


PAGES = ["Cover", "Guidance scorecard\nCredit cost\n1.85% - 1.95%\n1.93%\nROE\n19% - 20%\n19.2%"]


def test_table_cell_fallback_when_the_row_isnt_contiguous():
    p = _promise()
    figs = deck._validate([{"request_id": "R1", "value": 1.93, "quote": "Credit cost for FY26 was 1.93%", "page": 2,
                            "currency": "unspecified", "scope": "consolidated", "period_text": "FY26",
                            "period_type": "fy", "fy": 2026}], {"R1": p}, PAGES)  # fmt: skip
    assert len(figs) == 1 and figs[0]["page"] == 2 and "1.93%" in figs[0]["quote"] and "Credit cost" in figs[0]["quote"]


def test_number_not_on_page_or_metric_not_named_is_dropped():
    p = _promise()
    wrong_num = {"request_id": "R1", "value": 2.05, "quote": "Credit cost 2.05%", "page": 2}
    assert deck._validate([wrong_num], {"R1": p}, PAGES) == []
    other = _promise("net interest margin", "nim")
    assert deck._validate([{"request_id": "R1", "value": 1.93, "quote": "x", "page": 2}], {"R1": other}, PAGES) == []
