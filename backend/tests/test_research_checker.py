"""Citation checker + MAP validation: quotes must be in the source text; numbers must be in their own quote."""

from finn.research.checker import Checker, number_in_quote, strip_boilerplate
from finn.research.extract import validate

PAGES = [
    "Polycab India Limited\nWelcome to the call.\nModerator: please go ahead.",
    "Polycab India Limited\nWe expect EBITDA margins of 11% to 13% in the medium term, and our manu-\nfacturing "
    "capacity will expand.\nPage 2",
    "Polycab India Limited\nRevenue grew 53% year-on-year.\nAnalyst: what is the outlook on “FMEG” margins?\nPage 3",
]


def test_exact_and_hyphen_break_and_curly_quotes():
    c = Checker(PAGES)
    assert c.locate("We expect EBITDA margins of 11% to 13% in the medium term", 2).method == "exact"
    assert c.locate("our manufacturing capacity will expand", 2) is not None  # 'manu-\nfacturing' joined
    assert c.locate('what is the outlook on "FMEG" margins?', 3) is not None  # curly vs straight quotes


def test_wrong_page_is_fixed_and_missing_quote_dropped():
    c = Checker(PAGES)
    loc = c.locate("Revenue grew 53% year-on-year", 1)
    assert loc.page == 3 and loc.method == "page_fixed"
    assert c.locate("Revenue grew 80% year-on-year in every segment of the business", 3) is None
    assert c.stats.dropped == 1 and c.stats.page_fixed == 1


def test_reanchor_to_sentence_with_the_same_number():
    c = Checker(PAGES)
    loc = c.locate("We are expecting EBITDA margin between 11 and 13 percent over medium term", 2, anchor_number=11)
    assert loc.method == "reanchored" and "11% to 13%" in loc.quote  # stored quote is verbatim source text


def test_boilerplate_lines_removed():
    out = strip_boilerplate(PAGES + ["Polycab India Limited\nClosing remarks.\nPage 4"])
    assert all("Polycab India Limited" not in p for p in out)


def test_number_must_be_in_quote():
    assert number_in_quote(11.0, "margins of 11% to 13%") and number_in_quote(1500, "capex of ₹1,500 crore")
    assert not number_in_quote(15.0, "margins of 11% to 13%")


def test_validate_drops_analyst_guidance_invented_numbers_and_missing_quotes():
    raw = {
        "guidance": [
            {"metric": "EBITDA margin", "metric_key": "ebitda_margin", "measure": "level", "kind": "range",
             "target_low": 11, "target_high": 13, "unit_text": "%", "currency": "unspecified", "scope": "unspecified",
             "period_text": "medium term", "period_type": "medium_term", "statement": "s", "speaker": "CEO",
             "speaker_role": "management", "quote": "We expect EBITDA margins of 11% to 13% in the medium term",
             "page": 2},
            {"metric": "EBITDA margin", "metric_key": "ebitda_margin", "measure": "level", "kind": "point",
             "target_low": 15, "target_high": 15, "unit_text": "%", "currency": "unspecified", "scope": "unspecified",
             "period_text": "medium term", "period_type": "medium_term", "statement": "s", "speaker": "CEO",
             "speaker_role": "management", "quote": "We expect EBITDA margins of 11% to 13% in the medium term",
             "page": 2},  # 15 isn't in the quote
            {"metric": "FMEG margin", "metric_key": "ebitda_margin", "measure": "level", "kind": "qualitative",
             "currency": "unspecified", "scope": "unspecified", "period_text": "", "period_type": "unspecified",
             "statement": "s", "speaker": "Analyst", "speaker_role": "analyst",
             "quote": "what is the outlook on FMEG margins?", "page": 3},
            {"metric": "x", "metric_key": "made_up_key", "measure": "level", "kind": "qualitative",
             "currency": "unspecified", "scope": "unspecified", "period_text": "", "period_type": "unspecified",
             "statement": "s", "speaker": "CEO", "speaker_role": "management",
             "quote": "We will enter the US market next year with three products", "page": 2},  # not in text
        ],
        "actuals": [], "analyst_questions": [], "segments": [], "capex": [], "risks": [],
    }  # fmt: skip
    facts, stats = validate(raw, PAGES)
    assert len(facts["guidance"]) == 1 and facts["guidance"][0]["target_low"] == 11
    assert stats["dropped"]["number_not_in_quote"] == 1 and stats["dropped"]["not_management"] == 1
    assert stats["dropped_total"] if "dropped_total" in stats else stats["reasons"]["not_in_source"] == 1
