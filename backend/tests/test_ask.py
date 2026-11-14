from datetime import UTC, date, datetime

from finn.models import Citation
from finn.research.ask import Source, check, normalise_question, visitor_id
from finn.research.bm25 import Passage
from finn.research.reduce import Fact

NOW = datetime(2026, 11, 12, tzinfo=UTC)
CITE = Citation(source_type="screener_table", url="https://www.screener.in/company/INFY/", retrieved_at=NOW,
                locator="screener:profit-loss/Sales/Mar 2026")  # fmt: skip
FACTS = [Fact("F1", "F1: Revenue (FY26) = ₹1,62,990 Cr", "₹1,62,990 Cr", [CITE])]
PASSAGE = Passage("u", 4, "Based on our Q2 performance, our revenue growth guidance for FY27 is now 1% to 2% in "
                          "constant currency terms, with operating margin of 20% to 22%.")  # fmt: skip
SRCS = [Source("P1", PASSAGE, {"source_type": "concall_transcript", "url": "https://bse/x.pdf",
                               "title": "Q2 FY27 earnings call transcript", "retrieved_at": NOW})]  # fmt: skip
QUOTE = "our revenue growth guidance for FY27 is now 1% to 2% in constant currency terms"


def test_answer_with_verified_quote():
    data = {"found": True, "answer": "Management now guides FY27 growth of 1% to 2% in CC.",
            "passages": [{"id": "P1", "quote": QUOTE}]}  # fmt: skip
    claim, _, reason = check(data, "growth guidance?", FACTS, SRCS)
    assert reason is None and claim and claim.citations[0].page == 4 and claim.citations[0].quote == QUOTE


def test_number_not_in_sources_is_refused():
    # 1.5 appears nowhere in the cited quote: the model computed or recalled it
    claim, _, reason = check({"found": True, "answer": "Guidance is 1.5% at the midpoint.",
                              "passages": [{"id": "P1", "quote": QUOTE}]}, "growth?", FACTS, SRCS)  # fmt: skip
    assert claim is None and reason == "unsupported_number"


def test_invented_quote_or_unknown_ids_mean_not_found():
    claim, _, _ = check({"found": True, "answer": "Growth will be strong.", "fact_ids": ["F9"],
                         "passages": [{"id": "P1", "quote": "we expect growth to be very strong next year"}]},
                        "growth?", FACTS, SRCS)  # fmt: skip
    assert claim is None


def test_fact_citation_and_figure_numbers_with_indian_separators():
    claim, _, reason = check({"found": True, "answer": "FY26 revenue was ₹1,62,990 Cr.", "fact_ids": ["F1"]},
                             "revenue?", FACTS, SRCS)  # fmt: skip
    assert reason is None and claim and claim.citations == [CITE]


def test_model_says_not_found():
    assert check({"found": False, "answer": ""}, "q", FACTS, SRCS) == (None, [], None)


def test_normalise_and_visitor():
    assert normalise_question("  What's the FY27 guidance?? ") == "what s the fy27 guidance"
    a = visitor_id("1.2.3.4", date(2026, 11, 12))
    assert a == visitor_id("1.2.3.4", date(2026, 11, 12)) and a != visitor_id("1.2.3.4", date(2026, 11, 13))
    assert "1.2.3.4" not in a and len(a) == 20


class _Conn:
    def commit(self):
        pass


class _Res:
    cached, model = False, "gemini-flash-lite"
    quote = "Management said order inflows were strong this quarter across defence"
    data = {"found": True, "answer": "Management said order inflows were strong this quarter.",
            "passages": [{"id": "P1", "quote": quote}]}  # fmt: skip


class _Router:
    def __init__(self):
        self.reqs = []

    def run(self, tier, req):
        self.reqs.append((tier, req))
        return _Res()


def _no_dossier(monkeypatch, n_docs: int, keys: list):
    from finn.research import ask

    monkeypatch.setattr(ask.rstore, "get_dossier_row", lambda conn, s: None)
    monkeypatch.setattr(ask, "doc_count", lambda conn, s: n_docs)
    monkeypatch.setattr(ask, "_cached", lambda conn, s, qn, v: keys.append(v))  # append → None: a cache miss
    monkeypatch.setattr(ask, "used_today", lambda conn, v: 0)
    monkeypatch.setattr(ask, "_count", lambda conn, v: 1)
    monkeypatch.setattr(ask, "_store", lambda conn, s, qn, v, a: keys.append(("stored", v)))
    monkeypatch.setattr(ask, "_name", lambda conn, s: "Hindustan Aeronautics Limited")
    text = "Management said order inflows were strong this quarter across defence platforms and exports, they added."
    meta = {"source_type": "concall_transcript", "url": "https://bse/hal-q2.pdf",
            "title": "Q2 FY27 earnings call transcript", "retrieved_at": NOW}  # fmt: skip
    monkeypatch.setattr(ask, "load_sources", lambda conn, s: [(Passage("u", 3, text), meta)])
    return ask


def test_no_dossier_answers_from_transcripts_already_read(monkeypatch):
    keys: list = []
    ask = _no_dossier(monkeypatch, 3, keys)
    router = _Router()
    a = ask.answer(_Conn(), "HAL", "What did management say about order inflows?", router=router)
    assert a.status == "answered" and a.basis == "transcripts"
    assert a.answer.citations[0].url == "https://bse/hal-q2.pdf" and a.answer.citations[0].page == 3
    tier, req = router.reqs[0]
    assert tier == "cheap" and len(router.reqs) == 1  # the Ask call is the only model call
    assert "Company: Hindustan Aeronautics Limited (HAL)" in req.prompt and "Facts:\n(none)" in req.prompt
    assert keys == [-3, ("stored", -3)]  # cached apart from dossier answers, keyed by documents read


def test_no_dossier_and_no_transcripts_is_no_dossier(monkeypatch):
    keys: list = []
    ask = _no_dossier(monkeypatch, 0, keys)
    router = _Router()
    a = ask.answer(_Conn(), "ITC", "What did management say about cigarettes?", router=router)
    assert a.status == "unavailable" and a.reason == "no_dossier" and not router.reqs and not keys
