"""Promise Ledger rules (decided in code): comparisons per type, units, bases, periods, revisions, timing,
quietly dropped, credibility."""

from datetime import UTC, date, datetime

import pytest

from finn.research.ledger import Call, build_ledger, compare, normalise_unit
from finn.research.periods import resolve

NOW = datetime(2026, 11, 11, tzinfo=UTC)


def g(metric_key="ebitda_margin", lo=20.0, hi=22.0, unit="%", kind="range", fy=2026, period_type="fy",
      currency="INR", scope="consolidated", quote=None, measure="level", terms=("margin",), **kw):  # fmt: skip
    return {
        "metric": kw.pop("metric", metric_key.replace("_", " ")), "metric_key": metric_key, "measure": measure,
        "kind": kind, "target_low": lo, "target_high": hi, "unit_text": unit, "currency": currency, "scope": scope,
        "segment": kw.pop("segment", None), "period_text": kw.pop("period_text", "FY26"), "period_type": period_type,
        "fy": fy, "quarter": kw.pop("quarter", None), "half": None, "years": None, "statement": "s",
        "search_terms": list(terms), "speaker": "CFO", "speaker_role": "management",
        "quote": quote or f"we expect {metric_key} of {lo} to {hi} {unit}", "page": 3, **kw,
    }  # fmt: skip


def a(metric_key="ebitda_margin", value=21.0, unit="%", fy=2026, period_type="fy", currency="INR",
      scope="consolidated", measure="level"):  # fmt: skip
    return {"metric": metric_key, "metric_key": metric_key, "measure": measure, "value": value, "unit_text": unit,
            "currency": currency, "scope": scope, "segment": None, "period_text": "FY26", "period_type": period_type,
            "fy": fy, "quarter": None, "half": None, "years": None, "quote": f"{metric_key} was {value}",
            "page": 2}  # fmt: skip


def call(i, made, guidance=(), actuals=(), text="nothing relevant here"):
    return Call(f"doc{i}", f"https://x/{i}.pdf", f"Q{i} call", made, [text], {"guidance": list(guidance),
                "actuals": list(actuals)}, NOW)  # fmt: skip


def ledger(calls, today=date(2026, 11, 11)):
    return build_ledger("TEST", calls, None, today)


def only(led):
    assert len(led.promises) == 1, [p.statement for p in led.promises]
    return led.promises[0]


# --- comparison rules ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("kind,lo,hi,val,direction,expect", [
    ("range", 20, 22, 21, "higher", "kept"),
    ("range", 20, 22, 19.95, "higher", "kept"),  # rounding of the bound (0.1 pp)
    ("range", 20, 22, 19.5, "higher", "missed"),
    ("range", 20, 22, 23, "higher", "kept"),  # beat
    ("range", 1.7, 1.8, 2.0, "lower", "missed"),  # credit cost above the range is bad
    ("range", 1.7, 1.8, 1.5, "lower", "kept"),  # below is a beat for a lower-is-better metric
    ("range", 500, 600, 700, "neutral", "missed"),  # capex: off-plan either way
    ("point", 20, 20, 19.6, "higher", "kept"),  # point target ±0.5 pp
    ("point", 20, 20, 19.4, "higher", "missed"),
    ("at_least", 15, None, 14.95, "higher", "kept"),
    ("at_least", 15, None, 14.5, "higher", "missed"),
    ("at_most", None, 2.0, 2.05, "lower", "kept"),
    ("at_most", None, 2.0, 2.3, "lower", "missed"),
])  # fmt: skip
def test_compare_per_type(kind, lo, hi, val, direction, expect):
    assert compare(kind, lo, hi, val, "PCT", direction)[0] == expect


def test_money_tolerance_is_relative():
    assert compare("point", 1000, 1000, 980, "INR_CR", "higher")[0] == "kept"  # within 2.5 %
    assert compare("point", 1000, 1000, 960, "INR_CR", "higher")[0] == "missed"


@pytest.mark.parametrize("unit,currency,fam,f", [
    ("bps", "not_money", "PCT", 0.01), ("%", "INR", "PCT", 1.0), ("crore", "INR", "INR_CR", 1.0),
    ("lakh", "INR", "INR_CR", 0.01), ("million", "INR", "INR_CR", 0.1), ("billion", "INR", "INR_CR", 100.0),
    ("USD million", "USD", "USD_MN", 1.0), ("billion", "USD", "USD_MN", 1000.0), ("x", "not_money", "X", 1.0),
])  # fmt: skip
def test_unit_normalisation(unit, currency, fam, f):
    assert normalise_unit(unit, currency) == (fam, f)


# --- periods -------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("ptype,fy,q,made,label", [
    ("fy", 2027, None, date(2026, 10, 20), "FY27"),
    ("quarter", 2027, 3, date(2026, 10, 20), "Q3 FY27"),
    ("quarter", None, 3, date(2026, 10, 20), "Q3 FY27"),
    ("by_fy", 2028, None, date(2026, 10, 20), "FY28"),
    ("this_fy", None, None, date(2026, 10, 20), "FY27"),
    ("next_fy", None, None, date(2026, 10, 20), "FY28"),
    ("next_fy", None, None, date(2026, 5, 5), None),  # 'next year' in a Q4 call is ambiguous → no period
    ("medium_term", None, None, date(2026, 10, 20), None),
])  # fmt: skip
def test_period_resolution(ptype, fy, q, made, label):
    p = resolve(ptype, fy, q, None, None, made)
    assert (p.label if p else None) == label


def test_september_year_end():
    p = resolve("fy", 2027, None, None, None, date(2026, 11, 1), ye_month=9)
    assert p.end == date(2027, 9, 30)


# --- threads, delivery, timing -----------------------------------------------------------------------------------


def test_kept_from_management_reported_actual_in_later_call():
    p = only(ledger([call(1, date(2025, 7, 20), [g()]), call(2, date(2026, 5, 5), actuals=[a(value=21.4)])]))
    assert p.verdict == "kept" and p.delivered_source == "management_reported"
    assert p.delivered.citation.url == "https://x/2.pdf" and len(p.verdict_reason.citations) == 2  # both calls


def test_restatements_group_into_one_thread_and_unspecified_basis_merges():
    c1 = call(1, date(2025, 7, 20), [g()])
    c2 = call(2, date(2025, 10, 20), [g(scope="unspecified", currency="unspecified")])
    p = only(ledger([c1, c2, call(3, date(2026, 5, 5), actuals=[a()])]))
    assert len(p.statements) == 2 and p.verdict == "kept"


def test_never_compares_across_currency_basis():
    cc = g("revenue_growth", 4, 6, measure="growth", currency="constant_currency")
    p = only(
        ledger(
            [
                call(1, date(2025, 7, 20), [cc]),
                call(2, date(2026, 5, 5), actuals=[a("revenue_growth", 5, measure="growth", currency="INR")]),
            ]
        )
    )
    assert p.verdict in ("cant_score", "quietly_dropped") and p.delivered is None


def test_never_compares_standalone_with_consolidated():
    p = only(
        ledger(
            [
                call(1, date(2025, 7, 20), [g(scope="standalone")]),
                call(2, date(2026, 5, 5), actuals=[a(scope="consolidated")]),
            ]
        )
    )
    assert p.delivered is None


def test_not_yet_due_and_awaiting_results():
    assert only(ledger([call(1, date(2026, 7, 20), [g(fy=2027)])])).verdict == "not_yet_due"
    # FY26 ended 31 Mar 2026; on 10 May the results may not be out yet
    p = only(ledger([call(1, date(2025, 7, 20), [g()])], today=date(2026, 5, 10)))
    assert p.verdict == "not_yet_due" and "Awaiting" in p.verdict_reason.text


def test_cant_score_without_delivered_figure_after_lag():
    p = only(ledger([call(1, date(2025, 7, 20), [g()])], today=date(2026, 11, 11)))
    assert p.verdict == "cant_score"


def test_benchmark_relative_target_is_not_scored():
    p = only(ledger([call(1, date(2025, 7, 20), [g("revenue_growth", 1.5, 2, unit="x", measure="growth")])]))
    assert p.verdict == "cant_score" and "benchmark" in p.verdict_reason.text


# --- revisions -------------------------------------------------------------------------------------------------------


def test_raised_target_is_not_a_miss():
    calls = [call(1, date(2025, 7, 20), [g(lo=20, hi=22)]), call(2, date(2025, 10, 20), [g(lo=22, hi=24)]),
             call(3, date(2026, 5, 5), actuals=[a(value=23)])]  # fmt: skip
    p = only(ledger(calls))
    assert p.revision == "raised" and p.verdict == "kept"  # scored against the last target before period end


def test_lowered_target_is_goalposts_moved_even_if_met():
    calls = [call(1, date(2025, 7, 20), [g(lo=20, hi=22)]), call(2, date(2025, 10, 20), [g(lo=17, hi=18)]),
             call(3, date(2026, 5, 5), actuals=[a(value=17.5)])]  # fmt: skip
    p = only(ledger(calls))
    assert p.revision == "lowered" and p.verdict == "goalposts_moved" and len(p.verdict_reason.citations) == 2


def test_lower_is_better_metric_revision_direction():
    cc = "credit_cost"
    calls = [call(1, date(2025, 7, 20), [g(cc, 1.7, 1.8)]), call(2, date(2025, 10, 20), [g(cc, 1.9, 2.0)])]
    assert only(ledger(calls)).verdict == "goalposts_moved"  # higher credit-cost guidance is worse
    calls = [call(1, date(2025, 7, 20), [g(cc, 1.9, 2.0)]), call(2, date(2025, 10, 20), [g(cc, 1.7, 1.8)])]
    assert only(ledger(calls)).revision == "raised"


def test_narrowed_range():
    calls = [call(1, date(2025, 7, 20), [g(lo=1, hi=3)]), call(2, date(2025, 10, 20), [g(lo=1.5, hi=2.5)])]
    assert only(ledger(calls)).revision == "narrowed"


def test_delayed_target_is_goalposts_moved():
    calls = [call(1, date(2025, 7, 20), [g(lo=20, hi=20, kind="point", fy=2026)]),
             call(2, date(2025, 10, 20), [g(lo=20, hi=20, kind="point", fy=2027, period_text="FY27")])]  # fmt: skip
    led = ledger(calls)
    fy26 = next(p for p in led.promises if p.period.label == "FY26")
    assert fy26.revision == "delayed" and fy26.verdict == "goalposts_moved"


# --- quietly dropped ------------------------------------------------------------------------------------------------


def test_quietly_dropped_needs_two_later_calls_with_no_mention():
    first = call(1, date(2025, 7, 20), [g("other", 500, 500, unit="crore", kind="point", metric="defence exports",
                                          terms=("defence", "exports"), fy=2028)])  # fmt: skip
    one_later = ledger([first, call(2, date(2025, 10, 20))])
    assert one_later.promises[0].verdict == "not_yet_due"
    two_later = ledger([first, call(2, date(2025, 10, 20)), call(3, date(2026, 1, 20))])
    p = two_later.promises[0]
    assert p.verdict == "quietly_dropped" and p.dropped_note == "Not mentioned in the 2 calls since the Q1 call"


def test_any_mention_keeps_it_alive():
    first = call(1, date(2025, 7, 20), [g("other", 500, 500, unit="crore", kind="point", metric="defence exports",
                                          terms=("defence", "exports"), fy=2028)])  # fmt: skip
    led = ledger([first, call(2, date(2025, 10, 20)), call(3, date(2026, 1, 20), text="Our Defence business grew")])
    assert led.promises[0].verdict == "not_yet_due"


# --- credibility ---------------------------------------------------------------------------------------------------


def test_credibility_formula_and_min_n():
    keys = ["ebitda_margin", "revenue_growth", "pat_growth", "gross_margin", "nim", "roe"]
    guid = [g(k, 10, 12, measure="growth" if "growth" in k else "level") for k in keys]
    acts = [a(k, 11 if i < 4 else 5, measure="growth" if "growth" in k else "level") for i, k in enumerate(keys)]
    led = ledger([call(1, date(2025, 7, 20), guid), call(2, date(2026, 5, 5), actuals=acts)])
    cr = led.credibility
    assert (cr.kept, cr.n, cr.shown, cr.score_pct, cr.numeric_n) == (4, 6, True, pytest.approx(66.7), 6)
    small = ledger([call(1, date(2025, 7, 20), guid[:3]), call(2, date(2026, 5, 5), actuals=acts[:3])])
    assert small.credibility.shown is False and small.credibility.n == 3


def test_loose_metric_keys_need_matching_names():
    hire = g("headcount", 15000, None, unit="employees", kind="at_least", metric="fresher hiring", measure="level")
    total = {**a("headcount", 323578, unit="employees"), "metric": "total headcount"}
    p = only(
        ledger([call(1, date(2024, 7, 20), [hire]), call(2, date(2025, 5, 5), actuals=[total])], date(2025, 11, 1))
    )
    assert p.delivered is None


def test_partly_specified_basis_merges_into_the_fully_specified_thread():
    cc = {"measure": "growth", "currency": "constant_currency"}
    calls = [call(1, date(2025, 4, 20), [g("revenue_growth", 0, 3, **cc)]),
             call(2, date(2025, 7, 20), [g("revenue_growth", 1, 3, scope="unspecified", **cc)]),
             call(3, date(2025, 10, 20), [g("revenue_growth", 2, 3, **cc)])]  # fmt: skip
    p = only(ledger(calls))
    assert len(p.statements) == 3 and p.revision == "raised"


def test_lowered_reason_names_latest_cut_and_original():
    calls = [call(1, date(2025, 4, 20), [g(lo=20, hi=22)]), call(2, date(2025, 7, 20), [g(lo=19, hi=21)]),
             call(3, date(2025, 10, 20), [g(lo=17, hi=18)])]  # fmt: skip
    p = only(ledger(calls))
    assert (
        "17–18%" in p.verdict_reason.text and "Q3 call" in p.verdict_reason.text and "20–22%" in p.verdict_reason.text
    )
