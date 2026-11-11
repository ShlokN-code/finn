"""JUDGE and REDUCE guards: model verdicts need verbatim later-call evidence; model text never carries a number."""

from datetime import UTC, date, datetime

from finn.models import Citation, Figure
from finn.research import judge, reduce
from finn.research.bm25 import BM25, passages
from finn.research.ledger import Call, build_ledger

NOW = datetime(2026, 11, 11, tzinfo=UTC)


def qual(**kw):
    return {"metric": "US launch", "metric_key": "other", "measure": "qualitative", "kind": "qualitative",
            "target_low": None, "target_high": None, "unit_text": None, "currency": "not_money", "scope": "unspecified",
            "segment": None, "period_text": "this year", "period_type": "this_fy", "fy": None, "quarter": None,
            "half": None, "years": None, "statement": "Launch the product in the US this year",
            "search_terms": ["US", "launch"], "speaker": "CEO", "speaker_role": "management",
            "quote": "we plan to launch our first product in the US market this year", "page": 1, **kw}  # fmt: skip


def calls():
    c1 = Call("d1", "https://x/1.pdf", "Q1 FY26 call", date(2025, 7, 20),
              ["Opening. We plan to launch our first product in the US market this year, subject to approvals."],
              {"guidance": [qual()], "actuals": []}, NOW)  # fmt: skip
    c2 = Call("d2", "https://x/2.pdf", "Q3 FY26 call", date(2026, 1, 20),
              ["Update on the US: we launched our first product in the US market in December and early demand is "
               "encouraging across our channel partners."], {"guidance": [], "actuals": []}, NOW)  # fmt: skip
    return [c1, c2]


def test_judge_accepts_verbatim_later_evidence_and_cites_both_calls():
    cs = calls()
    led = build_ledger("T", cs, None, date(2026, 11, 11))
    req, pid_map = judge.build_request(led.promises, cs, {})
    assert req is not None and "PROMISE" in req.prompt and "today" not in req.prompt.lower()
    p = led.promises[0]
    pid = next(k for k, (_, prom) in pid_map.items() if prom == p.id)
    data = {"verdicts": [{"id": p.id, "verdict": "kept", "passage_id": pid,
                          "quote": "we launched our first product in the US market in December",
                          "reason": "Launched in December"}]}  # fmt: skip
    res = judge.apply(led.promises, data, pid_map, cs, "gemini-3.8-flash", led.settled)
    assert (
        res.changed == 1 and p.verdict == "kept" and p.verdict_by == "model" and p.verdict_model == "gemini-3.8-flash"
    )
    assert {c.url for c in p.verdict_reason.citations} == {"https://x/1.pdf", "https://x/2.pdf"}


def test_judge_rejects_invented_quote_and_never_sets_dropped():
    cs = calls()
    led = build_ledger("T", cs, None, date(2026, 11, 11))
    req, pid_map = judge.build_request(led.promises, cs, {})
    p = led.promises[0]
    pid = next(iter(pid_map))
    before = p.verdict
    bad = {"verdicts": [
        {"id": p.id, "verdict": "missed", "passage_id": pid, "quote": "the US launch was cancelled", "reason": "x"},
        {"id": p.id, "verdict": "quietly_dropped", "passage_id": None, "quote": None, "reason": "x"},
    ]}  # fmt: skip
    res = judge.apply(led.promises, bad, pid_map, cs, "m", led.settled)
    assert res.rejected == 1 and p.verdict == before and p.verdict_by == "code"


def test_bm25_finds_the_relevant_passage():
    ps = passages("d", ["Margins improved due to mix.", "We launched our first product in the US market in December."])
    top = BM25(ps).search("US product launch", 1)
    assert top and top[0][1].page == 2


def _fig(label, v, unit="PCT"):
    cite = Citation(source_type="screener_table", url="https://s/x", locator=f"screener:x/{label}", retrieved_at=NOW)
    return Figure(label=label, value=v, unit=unit, status="verified", citation=cite)


def test_reduce_fills_placeholders_and_drops_typed_numbers():
    fs = [reduce.Fact("F1", "F1: Revenue CAGR 5y = 26.9%", reduce.show(_fig("Revenue CAGR 5y", 26.94)),
                      [_fig("x", 1).citation])]  # fmt: skip
    ok, dropped = reduce.render({"text": "Revenue compounded at {F1} over five years to FY26.", "fact_ids": ["F1"]}, fs)
    assert ok.text == "Revenue compounded at 26.9% over five years to FY26." and ok.citations and not dropped
    bad, dropped = reduce.render({"text": "Revenue grew 27% a year.", "fact_ids": ["F1"]}, fs)
    assert bad is None and dropped  # the model typed a number
    none, dropped = reduce.render({"text": "Strong franchise.", "fact_ids": ["F9"]}, fs)
    assert none is None and dropped  # no valid fact behind it


def test_reduce_keeps_a_typed_number_only_when_a_cited_fact_prints_it():
    f = _fig("Revenue CAGR 5y", 26.94)
    fs = [reduce.Fact("F1", "F1: Revenue CAGR 5y = 26.9%", reduce.show(f), [f.citation])]
    ok, dropped = reduce.render({"text": "Revenue compounded at 26.9% a year.", "fact_ids": ["F1"]}, fs)
    assert ok is not None and not dropped
    bad, dropped = reduce.render({"text": "Revenue compounded at 27.5% a year.", "fact_ids": ["F1"]}, fs)
    assert bad is None and dropped


def test_judge_never_scores_a_numeric_target():
    cs = calls()
    led = build_ledger("T", cs, None, date(2026, 11, 11))
    p = led.promises[0]
    req, pid_map = judge.build_request(led.promises, cs, {})
    pid = next(iter(pid_map))
    p.measure = "level"  # the same verdict on a numeric target must be refused
    data = {
        "verdicts": [
            {
                "id": p.id,
                "verdict": "kept",
                "passage_id": pid,
                "quote": "we launched our first product in the US market in December",
                "reason": "x",
            }
        ]
    }
    res = judge.apply(led.promises, data, pid_map, cs, "m", led.settled)
    assert res.rejected == 1 and p.verdict_by == "code"


def test_reduce_blocks_spelled_out_numbers_and_allows_numbers_printed_by_a_cited_promise():
    f = _fig("x", 1.0)
    promise = reduce.Fact("F2", "F2: promise 'revenue growth 1–2% (FY27)' → goalposts moved: cut from 1.5–3.5%",
                          "1–2%", [f.citation])  # fmt: skip
    ok, _ = reduce.render({"text": "Guidance was cut to 1–2% from 1.5–3.5% for FY27.", "fact_ids": ["F2"]}, [promise])
    assert ok is not None
    assert reduce.render({"text": "Growth of {F2} is guided.", "fact_ids": ["F2"]}, [promise])[0].text == \
        "Growth of 1–2% is guided."  # fmt: skip
    bad, dropped = reduce.render({"text": "Growth of ten to twelve percent was missed.", "fact_ids": ["F2"]}, [promise])
    assert bad is None and dropped
    fine, _ = reduce.render({"text": "A five-year record of cash conversion.", "fact_ids": ["F2"]}, [promise])
    assert fine is not None


def test_reduce_tidies_units_around_placeholders_and_id_lists():
    f = _fig("Free cash flow", 1571.0, "INR_CR")
    fs = [reduce.Fact("F1", "F1: Free cash flow (FY26) = ₹1,571 Cr", reduce.show(f), [f.citation]),
          reduce.Fact("F2", "F2: ROCE = 34.0%", "34.0%", [f.citation])]  # fmt: skip
    c, _ = reduce.render(
        {"text": "Free cash flow was ₹{F1} Cr in FY26 with ROCE of {F2}% {F1, F2}.", "fact_ids": []}, fs
    )
    assert c.text == "Free cash flow was ₹1,571 Cr in FY26 with ROCE of 34.0%." and len(c.citations) == 1


def test_segment_shares_over_100_percent_are_not_shares():
    from finn.research.insights import segments

    c = calls()[1]
    c.facts["segments"] = [
        {"name": "Rural", "share_pct": 63.0, "quote": "rural contributed 63% growth", "page": 1},
        {"name": "CV", "share_pct": 89.0, "quote": "CV and tractor share up 89%", "page": 1},
    ]
    assert segments(c) == []
