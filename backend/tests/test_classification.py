from datetime import UTC, datetime

import pytest

from finn.classification.ladder import Classifier, is_uninformative
from finn.llm import LLMResult, MemoryLLMLog, QuotaExceeded, Router
from finn.models import Filing


def filing(desc, subject, sym="RELIANCE", url="https://nsearchives.nseindia.com/corporate/x.pdf"):
    return Filing(id=f"NSE:{abs(hash((desc, subject)))}", exchange="NSE", exchange_id="1", symbol=sym,
                  filed_at=datetime(2026, 10, 30, 14, 0, tzinfo=UTC), exchange_category=desc, subject=subject,
                  attachment_url=url)  # fmt: skip


# Real NSE (desc, subject) pairs from the demo portfolio, Aug–Nov 2026.
CASES = [
    # tier a — exchange label alone
    ("Change in Management", "HDFC Bank Limited has informed the Exchange about change in Management",
     "management_change", None, "exchange"),
    ("Copy of Newspaper Publication", "Infosys Limited has informed the Exchange about Copy of Newspaper Publication",
     "routine", "newspaper_ad", "exchange"),
    ("ESOP/ESOS/ESPS", "HDFC Bank Limited has informed the Exchange regarding Allotment of 4675598  Shares.",
     "routine", None, "exchange"),
    ("Credit Rating", "Reliance Industries Limited has informed the Exchange about Credit Rating",
     "credit_rating", None, "exchange"),
    ("Board Meeting: Financial Results", "Board meeting on 17-Oct-2026: To consider and approve the results",
     "results", "intimation", "exchange"),
    # tier b — subject rules
    ("Analysts/Institutional Investor Meet/Con. Call Updates",
     "Transcript of the discussion on the Unaudited Financial Results", "earnings_call", "transcript", "rule"),
    ("Analysts/Institutional Investor Meet/Con. Call Updates",
     "Audio recording of the discussion on the Unaudited Financial Results", "earnings_call", "call", "rule"),
    ("Analysts/Institutional Investor Meet/Con. Call Updates",
     "Please note that the Company executives will be participating in the Institutional Investors' Meeting - CLSA",
     "investor_meetings", None, "rule"),
    ("Analysts/Institutional Investor Meet/Con. Call Updates",
     "The meeting of the Board of Directors of the Company is scheduled on October 30, 2026, inter alia, to consider "
     "and approve a. the standalone and consolidated unaudited financial results", "results", "intimation", "rule"),
    ("Outcome of Board Meeting",
     "Cochin Shipyard Limited has submitted to the Exchange, the financial results for the period ended Jun 30, 2026",
     "results", "outcome", "rule"),
    ("Press Release", "a press release dated October 29, 2026, titled \"Press Release on Unaudited Financial Results",
     "results", "presentation", "rule"),
    ("Press Release", "a press release dated November 03, 2026, titled \"Royal Enfield at EICMA 2026",
     "press_release", None, "rule"),
    ("Updates", "Hooghly-CSL, a wholly owned subsidiary of CSL, secured a Notable* order from a Domestic Client",
     "press_release", None, "rule"),
    ("General Updates", "Disclosure under Regulation 30 of SEBI LODR Regulations ESG Rating",
     "routine", None, "rule"),
    ("Shareholders meeting", "Vodafone Idea Limited has enclosed Notice of Postal Ballot seeking approval of "
     "shareholders for appointment of", "postal_ballot", None, "rule"),
    ("Allotment of Securities", "allotment of 2,06,950 securities pursuant to Non Convertible Securities",
     "fund_raise", None, "rule"),
    ("Allotment of Securities", "allotment of 7683981 securities pursuant to Qualified Institution Placement",
     "fund_raise", None, "rule"),
    ("Record Date", "Infosys Limited has informed the Exchange that Record date for the purpose of Dividend is 03-Nov",
     "dividend", None, "rule"),
]  # fmt: skip


@pytest.mark.parametrize("desc,subject,cat,stage,tier", CASES)
def test_ladder_without_model(desc, subject, cat, stage, tier):
    c = Classifier(None).classify(filing(desc, subject))
    assert (c.category, c.stage, c.tier) == (cat, stage, tier)


def test_leftover_without_model_is_honestly_unclassified():
    c = Classifier(None).classify(
        filing("General Updates", "X Limited has informed the Exchange about General Updates")
    )
    assert c.category == "unclassified" and c.tier == "failed"


def test_clarification_never_classified_by_headline_keywords():
    f = filing("News Verification", "The Exchange has sought clarification with respect to news item captioned "
               "Company plans QIP")  # fmt: skip
    c = Classifier(None).classify(f)
    assert c.tier == "failed" and c.stage == "clarification"


class FakeGemini:
    name = "gemini"

    def __init__(self, data=None, fail=None):
        self.data, self.fail, self.reqs = data, fail, []

    def model_for(self, tier):
        return "gemini-test"

    def supports_pdf(self):
        return True

    def price(self, model):
        return (0.0, 0.0)

    def generate(self, req, model):
        self.reqs.append(req)
        if self.fail:
            raise self.fail
        return LLMResult(self.data, "gemini", model, 100, 10)


def test_model_tier_with_pdf_for_uninformative_subject():
    g = FakeGemini({"category": "mna", "stage": "other", "confidence": 0.9, "reason": "acquires stake"})
    pdf_calls = []
    clf = Classifier(Router([g], MemoryLLMLog()), pdf_fetcher=lambda url: pdf_calls.append(url) or b"not a pdf")
    c = clf.classify(filing("General Updates", "X Limited has informed the Exchange about General Updates"))
    assert (c.category, c.tier, c.model, c.stage) == ("mna", "model", "gemini-test", None)
    assert pdf_calls  # tried to fetch the PDF because the subject says nothing
    assert clf.stats.as_dict()["tiers"] == {"model": 1}


def test_model_quota_degrades_to_unclassified():
    clf = Classifier(Router([FakeGemini(fail=QuotaExceeded("429"))], MemoryLLMLog()))
    c = clf.classify(filing("Agreements", "Agreements"))
    assert c.category == "unclassified" and c.tier == "failed" and "unavailable" in c.note


def test_model_unknown_category_rejected():
    clf = Classifier(Router([FakeGemini({"category": "weather", "stage": "other", "confidence": 1, "reason": ""})],
                            MemoryLLMLog()))  # fmt: skip
    assert clf.classify(filing("Agreements", "Agreements")).tier == "failed"


def test_uninformative_subjects():
    assert is_uninformative("HAL has informed the Exchange regarding 'General Updates'.")
    assert is_uninformative("Disclosure Under Regulation 30 Of The SEBI (LODR) Regulations, 2015")
    assert not is_uninformative("Appointment of Mr. Manoj Murali as Chief Operating Officer")


def test_model_hidden_reason_restricted_to_drawer_groups():
    g = FakeGemini({"category": "routine", "stage": "other", "confidence": 0.9, "reason": "x",
                    "hidden_reason": "A long free-text explanation the model made up"})  # fmt: skip
    c = Classifier(Router([g], MemoryLLMLog())).classify(filing("Agreements", "Agreements"))
    assert c.hidden_reason == "Other routine filing"


# --- material over routine (reviewer rule, 10 Nov 2026) ---
@pytest.mark.parametrize(
    "desc,subject,cat,stage",
    [
        # results newspaper publication (Reg 47) → results thread, not the hidden drawer
        ("Copy of Newspaper Publication", "Intimation under Regulations 33 and 47 of SEBI (LODR) Regulations, 2015",
         "results", "newspaper_ad"),
        ("Updates", "Newspaper publication of the Financial Results for the quarter ended September 30, 2026",
         "results", "newspaper_ad"),
        # a subsidiary's IPO advertised in the paper → M&A (stake sale), still marked as an ad
        ("Copy of Newspaper Publication", "Newspaper Clippings Proposed Initial Public Offer of Jio Platforms Limited",
         "mna", "newspaper_ad"),
        # NCD allotment = debt raise
        ("Allotment of Securities", "We wish to inform that the Company has today allotted 13,00,000 Unsecured, "
         "Redeemable, Non-Convertible Debentures", "fund_raise", None),
    ],
)  # fmt: skip
def test_material_beats_weak_routine(desc, subject, cat, stage):
    c = Classifier(None).classify(filing(desc, subject))
    assert (c.category, c.stage, c.hidden_reason) == (cat, stage, None)


@pytest.mark.parametrize(
    "desc,subject,hidden",
    [
        # strong routine labels stay routine even when material words appear
        ("General Updates", "the Trading Window closure pursuant to SEBI (Prohibition of Insider Trading) Regulations",
         "Trading-window notice"),
        ("General Updates", "Communication to Shareholders w.r.t. Tax Deduction at Source on Dividend Payout",
         "Shareholder administration"),
        # content-free ads stay hidden
        ("Copy of Newspaper Publication", "Copy of Newspaper Publication", "Newspaper ad"),
        ("General Updates", "Newspaper Advertisement - Public Notice regarding loss of Share Certificates",
         "Newspaper ad"),
    ],
)  # fmt: skip
def test_strong_routine_and_empty_ads_stay_hidden(desc, subject, hidden):
    c = Classifier(None).classify(filing(desc, subject))
    assert c.category == "routine" and c.hidden_reason == hidden


def test_audio_visual_means_is_not_a_call_recording():
    c = Classifier(None).classify(filing("General Updates", "copies of newspaper publication titled Notice to the "
                                         "Shareholders regarding the 33rd Annual General Meeting to be held through "
                                         "Video Conference/ Other Audio Visual Means"))  # fmt: skip
    assert (c.category, c.stage) == ("agm_egm", "newspaper_ad")


# --- content-free newspaper ads are read from their PDF ---
def _pdf() -> bytes:
    import io

    from pypdf import PdfWriter

    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


AD = ("Copy of Newspaper Publication", "Persistent Systems Limited has informed the Exchange about Copy of Newspaper "
      "Publication")  # fmt: skip


def test_blind_ad_read_from_pdf_becomes_material():
    g = FakeGemini({"category": "results", "stage": "outcome", "confidence": 0.9, "reason": "results ad"})
    clf = Classifier(Router([g], MemoryLLMLog()), pdf_fetcher=lambda url: _pdf())
    c = clf.classify(filing(*AD))
    assert (c.category, c.stage, c.tier, c.hidden_reason) == ("results", "newspaper_ad", "model", None)
    assert g.reqs[0].pdf and g.reqs[0].pdf_required


def test_blind_ad_that_is_really_routine_stays_hidden():
    g = FakeGemini({"category": "routine", "stage": "other", "confidence": 0.9, "reason": "share certificate notice",
                    "hidden_reason": "Shareholder administration"})  # fmt: skip
    c = Classifier(Router([g], MemoryLLMLog()), pdf_fetcher=lambda url: _pdf()).classify(filing(*AD))
    assert (c.category, c.stage, c.tier, c.hidden_reason) == ("routine", "newspaper_ad", "model", "Newspaper ad")


def test_blind_ad_model_down_is_marked_for_retry():
    g = FakeGemini(fail=QuotaExceeded("429"))
    c = Classifier(Router([g], MemoryLLMLog()), pdf_fetcher=lambda url: _pdf()).classify(filing(*AD))
    assert (c.category, c.tier, c.hidden_reason) == ("routine", "failed", "Newspaper ad")
    assert c.note.startswith("llm unavailable")  # store.filings_to_classify retries these


def test_blind_ad_without_pdf_or_model_keeps_routine():
    assert Classifier(None).classify(filing(*AD)).tier == "exchange"
    g = FakeGemini({"category": "results", "stage": "outcome", "confidence": 1, "reason": ""})
    c = Classifier(Router([g], MemoryLLMLog()), pdf_fetcher=lambda url: None).classify(filing(*AD))
    assert c.category == "routine" and not g.reqs


def test_ads_that_name_their_content_never_call_the_model():
    g = FakeGemini({"category": "results", "stage": "outcome", "confidence": 1, "reason": ""})
    clf = Classifier(Router([g], MemoryLLMLog()), pdf_fetcher=lambda url: _pdf())
    c = clf.classify(filing("General Updates", "Newspaper Advertisement - Public Notice regarding loss of Share "
                            "Certificates"))  # fmt: skip
    assert c.category == "routine" and not g.reqs


@pytest.mark.parametrize(
    "subject,blind",
    [
        ("X Limited has informed the Exchange about Copy of Newspaper Publication", True),
        ("The newspaper clippings of the advertisement on the captioned subject published today are enclosed", True),
        ("Newspaper Publication", True),
        ("Newspaper publication regarding special window for transfer of physical shares", False),
    ],
)
def test_content_free_ad_pattern(subject, blind):
    from finn.classification.ladder import CONTENT_FREE_AD
    from finn.sources.nse import subject_core

    assert bool(CONTENT_FREE_AD.search(subject_core(subject))) is blind
