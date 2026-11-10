from datetime import UTC, date, datetime

from finn.cards.chips import chip_for
from finn.extraction import management as mg
from finn.ranking.impact import build_tagged

NOW = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)
FILING = {"id": "NSE:1", "subject": "Credit rating", "filed_at": NOW, "exchange_category": "Credit Rating",
          "attachment_url": "https://nsearchives.nseindia.com/corporate/r.pdf"}  # fmt: skip
TEXT = (
    "CRISIL has revised its rating on the long-term bank facilities of the Company to CRISIL AA/Negative "
    "from CRISIL AA+/Stable. The rated amount is Rs. 1,250 crore."
)


def test_rating_downgrade_decided_in_code_and_quote_checked():
    d = {"impact": "negative", "reason": "Long-term rating cut one notch", "so_what": "Rating cut to AA; "
         "borrowing may cost more over the next few quarters", "quote": "revised its rating on the long-term bank "
         "facilities of the Company to CRISIL AA/Negative", "rating_previous": "CRISIL AA+/Stable",
         "rating_new": "CRISIL AA/Negative", "amount": "Rs. 1,250 crore", "amount_label": "Rated amount"}  # fmt: skip
    t = build_tagged(d, {"category": "credit_rating", "symbol": "X"}, FILING, TEXT, [TEXT])
    assert t.detail.direction == "down"
    assert t.reason.status == "verified" and t.reason.citations[0].page == 1
    assert t.detail.key_figure.value == 1250 and t.detail.key_figure.status == "verified"
    assert len(t.so_what.split()) <= 10


def test_invented_quote_is_unverified_and_no_unit_no_figure():
    d = {"impact": "positive", "reason": "Big order", "so_what": "Order win", "quote": "record order book of the "
         "decade", "amount": "1,250"}  # fmt: skip
    t = build_tagged(d, {"category": "press_release", "symbol": "X"}, FILING, TEXT, [TEXT])
    assert t.reason.status == "unverified" and t.detail.key_figure is None
    assert t.reason.citations[0].quote is None  # never show a quote we couldn't find


PROFILE = ("The Board appointed Ms. Asha Rao as Chief Financial Officer with effect from 1st December 2026. "
           "Ms. Rao is a Chartered Accountant. She was CFO of Tata Motors Limited from 2018 to 2024 and earlier "
           "served at Hindustan Unilever Limited between 2009 and 2018. Mr. B. Shah, who joined the Company on "
           "1st April 2015, has resigned as CFO.")  # fmt: skip


def test_management_profile_outside_hire_and_tenure():
    d = {"people": [
        {"name": "Asha Rao", "role": "Chief Financial Officer", "change": "appointed",
         "profile_quote": "She was CFO of Tata Motors Limited from 2018 to 2024",
         "prior_roles": [{"company": "Tata Motors Limited", "role": "CFO", "period": "2018 to 2024",
                          "quote": "She was CFO of Tata Motors Limited from 2018 to 2024"},
                         {"company": "Hindustan Unilever Limited", "period": "2009 and 2018",
                          "quote": "served at Hindustan Unilever Limited between 2009 and 2018"},
                         {"company": "Made Up Ltd", "quote": "worked at Made Up Ltd"}],
         "qualifications": [{"text": "Chartered Accountant", "quote": "Ms. Rao is a Chartered Accountant"}]},
        {"name": "B. Shah", "role": "CFO", "change": "resigned", "joined_company": "1st April 2015",
         "joined_quote": "who joined the Company on 1st April 2015"}]}  # fmt: skip
    det = mg.build_detail(d, {"symbol": "X"}, {**FILING, "subject": "Change in CFO"}, PROFILE, [PROFILE], "X Ltd")
    rao, shah = det.people
    assert [r.company for r in rao.prior_roles] == ["Tata Motors Limited", "Hindustan Unilever Limited"]
    assert (rao.prior_roles[0].start_year, rao.prior_roles[0].end_year) == (2018, 2024)
    assert rao.insider is False and rao.qualifications[0].status == "verified"
    assert shah.tenure_years.value == 11.6 and shah.tenure_years.unit == "YEARS"
    assert det.web_enrichment == "not_run"
    assert mg.so_what(det) == "New Chief Financial Officer: outside hire"


def test_insider_and_web_fallback(monkeypatch):
    roles = mg.build_detail({"people": [{"name": "A", "role": "CEO", "change": "appointed", "prior_roles": [
        {"company": "X Limited", "role": "COO", "quote": "COO of X Limited"}]}]}, {"symbol": "X"}, FILING,
        "He is COO of X Limited.", [], "X Ltd")  # fmt: skip
    assert roles.people[0].insider is True
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    out = mg.enrich(None, roles, "X Ltd")
    assert out.web_enrichment == "unavailable" and out.people == roles.people  # card still complete


def test_dividend_chip_from_corporate_actions():
    ev = {"symbol": "ITC", "category": "dividend", "started_at": NOW}
    acts = [{"kind": "dividend", "ex_date": date(2026, 11, 20), "record_date": date(2026, 11, 21),
             "subject": "Interim Dividend - Rs 8 Per Share", "amount_per_share": 8.0, "ratio_new": None,
             "ratio_held": None}]  # fmt: skip
    chip = chip_for(ev, acts, FILING)
    assert chip.text == "₹8 dividend · record 21 Nov" and chip.amount.value == 8
