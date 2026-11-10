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


def test_web_enrichment_keeps_only_new_facts_ranked_and_labelled(monkeypatch):
    # IDEA, Oct 2026: a news article restated the filing's degrees; that must not come back as a web fact
    det = mg.build_detail({"people": [{"name": "Manoj Murali", "role": "Chief Operating Officer",
        "change": "appointed",
        "prior_roles": [{"company": "Bharti Airtel", "quote": "has earlier worked with Bharti Airtel"}],
        "qualifications": [{"text": "Master of Business Administration from SIBM Pune",
                            "quote": "Mr. Murali holds a Master of Business Administration from SIBM Pune"}]}]},
        {"symbol": "IDEA"}, FILING,
        "Mr. Murali has earlier worked with Bharti Airtel. Mr. Murali holds a Master of Business Administration "
        "from SIBM Pune", [], "Vodafone Idea Limited")  # fmt: skip
    news = ("Vodafone Idea appoints Manoj Murali as COO. He holds an MBA from Symbiosis Institute of Business "
            "Management (SIBM), Pune.")  # fmt: skip
    linkedin = ("Manoj Murali · Bharti Airtel 2009 - 2016 · Zonal Business Head · Vodafone Essar 2004 - 2009 · "
                "Led the turnaround of the Kenya circle to profitability in 2018.")  # fmt: skip
    calls = []

    def search(q, max_results=5, include_domains=None):
        calls.append(include_domains)
        if include_domains == ["linkedin.com"]:
            return [
                {"title": "Manoj Murali - COO", "url": "https://in.linkedin.com/in/manoj-murali", "content": linkedin}
            ]
        return [{"title": "Vodafone Idea appoints COO", "url": "https://www.thehindubusinessline.com/a.ece",
                 "content": news}]  # fmt: skip

    monkeypatch.setattr(mg.tavily, "available", lambda: True)
    monkeypatch.setattr(mg.tavily, "search", search)
    prompts = []
    items = [  # snippet 0 = LinkedIn (ranked first), 1 = news
        {"kind": "qualification", "text": "MBA from Symbiosis Institute of Business Management (SIBM), Pune",
         "snippet": 1, "quote": "He holds an MBA from Symbiosis Institute of Business Management (SIBM), Pune"},
        {"kind": "role", "company": "Bharti Airtel", "role": "Zonal Business Head", "period": "2009 - 2016",
         "snippet": 0, "quote": "Bharti Airtel 2009 - 2016 · Zonal Business Head"},
        {"kind": "role", "company": "Vodafone Essar", "period": "2004 - 2009", "snippet": 0,
         "quote": "Vodafone Essar 2004 - 2009"},
        {"kind": "achievement", "text": "Turned the Kenya circle profitable (2018)", "snippet": 0,
         "quote": "Led the turnaround of the Kenya circle to profitability in 2018."},
        {"kind": "role", "company": "Nokia", "snippet": 0, "quote": "He led Nokia India"},  # not in the snippet
    ]  # fmt: skip

    class Router:
        def run(self, tier, req):
            prompts.append(req.prompt)
            return type("R", (), {"data": {"items": items}})()

    out = mg.enrich(Router(), det, "Vodafone Idea Limited")
    p = out.people[0]
    assert ["linkedin.com"] in calls  # LinkedIn snippets via search only
    assert prompts[0].index("(Professional profile)") < prompts[0].index("(News)")  # best source first
    assert "Already known" in prompts[0] and "SIBM Pune" in prompts[0] and "(no dates)" in prompts[0]
    assert len(p.qualifications) == 1  # the restated degree is not added again
    airtel, essar = p.prior_roles
    assert airtel.source == "filing" and (airtel.start_year, airtel.end_year) == (2009, 2016)
    assert airtel.period_citation.url.startswith("https://in.linkedin.com") and airtel.citation.url == FILING[
        "attachment_url"]  # fmt: skip
    assert (essar.source, essar.start_year, essar.end_year) == ("web", 2004, 2009)
    assert essar.citation.title.startswith("Professional profile")
    assert [a.text for a in p.achievements] == ["Turned the Kenya circle profitable (2018)"]
    assert p.achievements[0].status == "unverified" and p.achievements[0].citations[0].quote
    assert out.web_enrichment == "done" and "3 web item(s)" in out.web_note


def test_web_search_that_only_restates_the_filing_finds_nothing(monkeypatch):
    det = mg.build_detail({"people": [{"name": "A", "role": "CFO", "change": "appointed", "qualifications": [
        {"text": "Chartered Accountant", "quote": "is a Chartered Accountant"}]}]}, {"symbol": "X"}, FILING,
        "Ms A is a Chartered Accountant", [], "X Ltd")  # fmt: skip
    monkeypatch.setattr(mg.tavily, "available", lambda: True)
    monkeypatch.setattr(
        mg.tavily,
        "search",
        lambda q, max_results=5, include_domains=None: [
            {"title": "X appoints CFO", "url": "https://economictimes.com/x", "content": "A, a Chartered Accountant."}
        ],
    )

    class Router:
        def run(self, tier, req):
            return type(
                "R",
                (),
                {
                    "data": {
                        "items": [
                            {
                                "kind": "qualification",
                                "text": "Chartered Accountant",
                                "snippet": 0,
                                "quote": "A, a Chartered Accountant.",
                            }
                        ]
                    }
                },
            )()

    out = mg.enrich(Router(), det, "X Ltd")
    assert out.web_enrichment == "nothing_found" and out.people == det.people


def test_web_facts_must_name_the_person_and_print_their_dates(monkeypatch):
    # IDEA, Sep 2026: a board page's generic "Non-Executive & Independent Director" line, and LinkedIn roles
    # whose years came from the model's 'period' field rather than the snippet
    det = mg.ManagementDetail(people=[mg.PersonProfile(name="Ms. Gopika Pant", role="Independent Woman Director",
                                                       change="appointed")], web_enrichment="not_run")  # fmt: skip
    board = ("Board of Directors. Mr. Ram Raghavan, Managing Director. Ms. Alice Rao, Non-Executive & Independent "
             "Director. Mr. B. Sen, Chairman.")  # fmt: skip
    linkedin = "Senior Partner at Indian Law Partners · Partner at Amarchand Mangaldas 1993 - 2007"
    snippets = [
        {"title": "Board of Directors | Colgate-Palmolive", "url": "https://www.colgatepalmolive.co.in/who-we-are/"
         "board-of-directors", "content": board, "kind": "bio"},
        {"title": "Gopika Pant - Senior Partner", "url": "https://in.linkedin.com/in/gopika-pant", "content": linkedin,
         "kind": "profile"},
    ]  # fmt: skip
    items = [
        {"kind": "role", "company": "Colgate-Palmolive", "role": "Non-Executive & Independent Director", "snippet": 0,
         "quote": "Non-Executive & Independent Director"},
        {"kind": "role", "company": "Indian Law Partners", "role": "Senior Partner", "period": "2008 - 2020",
         "snippet": 1, "quote": "Senior Partner at Indian Law Partners"},
        {"kind": "role", "company": "Amarchand Mangaldas", "role": "Partner", "period": "1993 - 2007", "snippet": 1,
         "quote": "Partner at Amarchand Mangaldas 1993 - 2007"},
    ]  # fmt: skip
    p, added = mg._apply_web(det.people[0], items, snippets)
    assert [(r.company, r.start_year, r.end_year) for r in p.prior_roles] == [
        ("Indian Law Partners", None, None),  # '2008 - 2020' isn't in the snippet → no dates
        ("Amarchand Mangaldas", 1993, 2007),
    ]  # board-page line doesn't name her → dropped
    assert added == ["profile", "profile"]


def test_exchange_filing_url_and_passing_mentions():
    assert mg.source_kind("https://nsearchives.nseindia.com/corporate/IDEA_21092026_PostalBallot.pdf",
                          "Vodafone Idea Limited", []) == "exchange_filing"  # fmt: skip
    assert list(mg.KIND_LABEL)[0] == "exchange_filing"
    det = mg.build_detail({"people": [
        {"name": "Ms. Gopika Pant", "role": "Independent Woman Director", "change": "appointed"},
        {"name": "Pankaj Kapdeo", "role": "Company Secretary", "change": "other"}]},  # signed the letter
        {"symbol": "IDEA"}, FILING, "text", [], "Vodafone Idea Limited")  # fmt: skip
    assert [x.name for x in det.people] == ["Ms. Gopika Pant"]
    assert mg.surname("Ms. Gopika Pant") == "pant" and mg.surname("Mr. Anil Berera") == "berera"
