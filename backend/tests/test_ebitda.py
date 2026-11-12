"""Results maths: XBRL parsing, EBITDA definition, bank/NBFC templates, QoQ/YoY, cross-check states."""

from datetime import UTC, date, datetime

import pytest

from finn.extraction.results.build import build_from_quarters, impact_from_lines, so_what_for
from finn.extraction.results.compute import (
    QuarterFacts,
    build_lines,
    facts_from_xbrl,
    metric,
    template_for,
)
from finn.extraction.results.xbrl import parse_instance, quarter_value
from finn.sources.screener import QuarterTable

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
Q2, Q1, Q2_LY = date(2026, 9, 30), date(2026, 6, 30), date(2025, 9, 30)


def instance(qe: date, values_cr: dict[str, float], decimals: str = "-7") -> bytes:
    """A minimal SEBI-style instance: OneD = the quarter, FourD = YTD (ignored), one dimensional fact (ignored)."""
    qs = date(qe.year, qe.month - 2, 1)
    facts = "".join(
        f'<in-capmkt:{k} contextRef="OneD" unitRef="INR" decimals="{decimals}">{v * 1e7:.0f}</in-capmkt:{k}>'
        f'<in-capmkt:{k} contextRef="FourD" unitRef="INR" decimals="{decimals}">{v * 2e7:.0f}</in-capmkt:{k}>'
        for k, v in values_cr.items()
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:xbrldi="http://xbrl.org/2006/xbrldi"
  xmlns:in-capmkt="http://www.sebi.gov.in/xbrl/2026-01-31/in-capmkt">
 <xbrli:context id="OneD"><xbrli:entity><xbrli:identifier scheme="x">X</xbrli:identifier></xbrli:entity>
  <xbrli:period><xbrli:startDate>{qs}</xbrli:startDate><xbrli:endDate>{qe}</xbrli:endDate></xbrli:period>
 </xbrli:context>
 <xbrli:context id="FourD"><xbrli:entity><xbrli:identifier scheme="x">X</xbrli:identifier></xbrli:entity>
  <xbrli:period><xbrli:startDate>{qe.year}-04-01</xbrli:startDate><xbrli:endDate>{qe}</xbrli:endDate></xbrli:period>
 </xbrli:context>
 <xbrli:context id="Seg"><xbrli:entity><xbrli:identifier scheme="x">X</xbrli:identifier>
  <xbrli:segment><xbrldi:explicitMember dimension="a">b</xbrldi:explicitMember></xbrli:segment></xbrli:entity>
  <xbrli:period><xbrli:startDate>{qs}</xbrli:startDate><xbrli:endDate>{qe}</xbrli:endDate></xbrli:period>
 </xbrli:context>
 <in-capmkt:NatureOfReportStandaloneConsolidated contextRef="OneD">Consolidated
 </in-capmkt:NatureOfReportStandaloneConsolidated>
 <in-capmkt:RevenueFromOperations contextRef="Seg" unitRef="INR" decimals="-7">10000000
 </in-capmkt:RevenueFromOperations>
 {facts}
</xbrli:xbrl>""".encode()


def qfacts(qe: date, values: dict[str, float], basis: str = "consolidated", decimals: str = "-7") -> QuarterFacts:
    row = {
        "facts": parse_instance(instance(qe, values, decimals)),
        "basis": basis,
        "xbrl_url": f"https://nsearchives.nseindia.com/corporate/xbrl/{qe}.xml",
        "broadcast_at": NOW,
        "fetched_at": NOW,
    }
    return facts_from_xbrl(row, qe)


# INFY Q2 FY27 consolidated (from the spike sample) plus made-up expenses / prior quarters.
INFY = {"RevenueFromOperations": 49244, "OtherIncome": 848, "FinanceCosts": 115,
        "DepreciationDepletionAndAmortisationExpense": 1359, "ProfitBeforeTax": 11063,
        "ProfitBeforeExceptionalItemsAndTax": 11063, "ProfitLossForPeriod": 8211,
        "Expenses": 39029}  # fmt: skip


def test_parser_keeps_quarter_and_skips_dimensional_facts():
    parsed = parse_instance(instance(Q2, {"RevenueFromOperations": 49244}))
    assert parsed["meta"]["NatureOfReportStandaloneConsolidated"] == "Consolidated"
    rev = parsed["facts"]["RevenueFromOperations"]
    assert len(rev) == 2  # OneD + FourD; the segment fact is dropped
    v, f = quarter_value(parsed["facts"], "RevenueFromOperations", Q2)
    assert v == 49244e7 and f["ctx"] == "OneD"


def test_ebitda_excludes_other_income():
    e = metric("EBITDA", qfacts(Q2, INFY))
    assert e.value == pytest.approx(11063 + 115 + 1359 - 848)  # 11,689 = revenue − (expenses − FC − D&A)
    assert "total expenses" in e.formula and len(e.inputs) == 4


def test_ebitda_ignores_regulatory_deferral_and_jv_share_below_expenses():
    # A Tata Power-style statement: "PBT before exceptional items" (1,823.34) already includes a regulatory-deferral
    # movement and the JV share; operating EBITDA reads revenue and expenses, so neither leaks in.
    vals = {"RevenueFromOperations": 19051.26, "OtherIncome": 388.39, "Expenses": 17704.61, "FinanceCosts": 1406.78,
            "DepreciationDepletionAndAmortisationExpense": 1259.86, "ProfitBeforeExceptionalItemsAndTax": 1823.34,
            "ProfitLossForPeriod": 1300.0, "TaxExpense": 523.34}  # fmt: skip
    e = metric("EBITDA", qfacts(Q1, vals))
    assert e.value == pytest.approx(19051.26 - (17704.61 - 1406.78 - 1259.86))
    assert e.value == pytest.approx(
        metric("EBITDA", qfacts(Q1, vals | {"ProfitBeforeExceptionalItemsAndTax": 1.0})).value
    )


def test_pbt_is_pat_plus_tax_without_discontinued_operations():
    # Tata Power Q2 FY27: SEBI's ProfitBeforeTax element (1,442.91) + JV share (486.80) = 1,929.71, but the statement
    # prints Profit before tax (7+8) = 2,179.85 = PAT 1,652.04 + tax 527.81.
    vals = {"RevenueFromOperations": 19635.94, "ProfitBeforeTax": 1442.91, "TaxExpense": 527.81,
            "ShareOfProfitLossOfAssociatesAndJointVenturesAccountedForUsingEquityMethod": 486.80,
            "ProfitLossForPeriod": 1652.04}  # fmt: skip
    pbt = metric("PBT", qfacts(Q2, vals))
    assert pbt.value == pytest.approx(2179.85) and pbt.formula == "Profit for the period + tax expense"
    with_disc = metric("PBT", qfacts(Q2, vals | {"ProfitLossFromDiscontinuedOperationsBeforeTax": -12.0}))
    assert with_disc.value == pytest.approx(1442.91 + 486.80 - 12.0)  # discontinued ops: the element route


def test_ebitda_old_route_when_total_expenses_is_not_tagged():
    vals = {k: v for k, v in INFY.items() if k != "Expenses"}
    e = metric("EBITDA", qfacts(Q2, vals))
    assert e.value == pytest.approx(11689) and "other income" in e.formula


def test_ebitda_excludes_exceptional_items_when_only_pbt_is_given():
    vals = {k: v for k, v in INFY.items() if k not in ("ProfitBeforeExceptionalItemsAndTax", "Expenses")}
    vals |= {"ProfitBeforeTax": 11063 - 300, "ExceptionalItemsBeforeTax": -300}
    e = metric("EBITDA", qfacts(Q2, vals))
    assert e.value == pytest.approx(11689)  # a ₹300 Cr one-off loss doesn't depress operating EBITDA


def test_margin_and_bps_change():
    cur = qfacts(Q2, INFY)
    prev = qfacts(Q1, INFY | {"RevenueFromOperations": 47000, "Expenses": 39029 - 2244})  # same EBITDA
    lines = build_lines("standard", cur, prev, None)
    m = next(x for x in lines if x.metric == "EBITDA margin")
    assert m.current.value == pytest.approx(11689 / 49244 * 100)
    assert m.qoq.unit == "BPS"
    assert m.qoq.value == pytest.approx((11689 / 49244 - 11689 / 47000) * 1e4)
    rev = next(x for x in lines if x.metric == "Revenue")
    assert rev.qoq.value == pytest.approx((49244 - 47000) / 47000 * 100)
    assert rev.yoy is None  # no year-ago filing → no YoY, never guessed


def test_negative_base_is_not_meaningful():
    cur = qfacts(Q2, INFY)
    ya = qfacts(Q2_LY, INFY | {"ProfitLossForPeriod": -50})
    pat = next(x for x in build_lines("standard", cur, None, ya) if x.metric == "PAT")
    assert pat.yoy.value is None and pat.yoy.status == "not_found" and "n/m" in pat.yoy.check_note


def test_bank_template_nii_and_ppop():
    vals = {"InterestEarned": 95132, "InterestExpended": 50667, "OperatingProfitBeforeProvisionAndContingencies":
            32000, "ProvisionsOtherThanTaxAndContingencies": 3337, "ProfitLossForPeriod": 21537}  # fmt: skip
    q = qfacts(Q2, vals)
    assert template_for(q) == "bank"
    lines = build_lines("bank", q, None, None)
    assert [x.metric for x in lines] == ["NII", "PPOP", "PAT"]
    assert lines[0].current.value == pytest.approx(95132 - 50667)
    assert metric("EBITDA", q) is None  # banks: no EBITDA


def test_nbfc_template():
    vals = {"InterestIncome": 18000, "FinanceCosts": 7000, "ImpairmentOnFinancialInstruments": 2100,
            "ProfitBeforeTax": 6000, "ProfitLossForPeriod": 4500, "RevenueFromOperations": 19500}  # fmt: skip
    q = qfacts(Q2, vals)
    assert template_for(q, "Finance") == "nbfc"
    nii, ppop, _ = build_lines("nbfc", q, None, None)
    assert nii.current.value == pytest.approx(11000) and ppop.current.value == pytest.approx(8100)


def table(periods: list[date], rows: dict[str, list[float | None]], basis: str = "consolidated") -> QuarterTable:
    return QuarterTable("INFY", basis, "https://www.screener.in/company/INFY/consolidated/",
                        "Consolidated Figures in Rs. Crores", periods, rows, NOW)  # fmt: skip


def three():
    return {
        "current": qfacts(Q2, INFY),
        "previous": qfacts(Q1, INFY | {"RevenueFromOperations": 47000, "Expenses": 36785}),
        "year_ago": qfacts(
            Q2_LY, INFY | {"RevenueFromOperations": 44000, "ProfitLossForPeriod": 7300, "Expenses": 33785}
        ),  # fmt: skip
    }


def screener_rows(pat_now: float = 8211, sales_now: float = 49244):
    return table(
        [Q2_LY, Q1, Q2],
        {"Sales": [44000, 47000, sales_now], "Operating Profit": [11689, 11689, 11689],
         "Profit before tax": [11063, 11063, 11063], "Net Profit": [7300, 8211, pat_now]},
    )  # fmt: skip


def test_cross_checked_card():
    b = build_from_quarters("standard", "consolidated", Q2, three(), screener_rows(), "xbrl", "https://x/pdf")
    d = b.detail
    assert d.verification == "cross_checked", d.verification_note
    assert all(x.check == "match" for x in d.lines)
    margin = next(x for x in d.lines if x.metric == "EBITDA margin")
    assert margin.current.status == "verified"  # inherits from EBITDA and revenue
    assert b.impact == "positive" and b.impact_reason.status == "verified"
    assert len(b.so_what.split()) <= 10


def test_mismatch_card_hides_impact():
    b = build_from_quarters("standard", "consolidated", Q2, three(), screener_rows(pat_now=9000), "xbrl", None)
    assert b.detail.verification == "mismatch" and "PAT" in b.detail.verification_note
    assert b.impact is None and b.so_what.startswith("Couldn't verify")


def test_pending_when_screener_lacks_the_quarter():
    t = table([Q2_LY, Q1], {"Sales": [44000, 47000], "Net Profit": [7300, 8211]})
    b = build_from_quarters("standard", "consolidated", Q2, three(), t, "xbrl", None)
    assert b.detail.verification == "pending"
    rev = next(x for x in b.detail.lines if x.metric == "Revenue")
    assert rev.check == "not_in_screener"
    assert rev.previous.status == "verified"  # older quarters still checked


def test_basis_mismatch_with_screener_is_pending_not_verified():
    t = screener_rows()
    t.basis = "standalone"
    b = build_from_quarters("standard", "consolidated", Q2, three(), t, "xbrl", None)
    assert b.detail.verification == "pending" and "standalone" in b.detail.verification_note


def test_sanity_failure_is_mismatch():
    q = three()
    q["current"] = qfacts(Q2, INFY | {"Expenses": 30000})  # rows don't reconcile
    b = build_from_quarters("standard", "consolidated", Q2, q, screener_rows(), "xbrl", None)
    assert b.detail.verification == "mismatch" and "PBT before exceptional" in b.detail.verification_note


def test_impact_rules():
    ya = qfacts(Q2_LY, INFY | {"RevenueFromOperations": 44000, "ProfitLossForPeriod": 9000})
    lines = build_lines("standard", qfacts(Q2, INFY), None, ya)
    impact, _ = impact_from_lines("standard", lines)
    assert impact == "mixed"  # revenue up, PAT down
    assert so_what_for("standard", lines, "pending")


# --- found on the first real run (Q2 FY27): XBRL layout vs screener's derived rows ----------------------------

ONLY = {"previous": None, "year_ago": None}


def one_quarter_table(rows: dict[str, float]) -> QuarterTable:
    return table([Q2], {k: [v] for k, v in rows.items()})


def test_pbt_adds_back_associates_and_discontinued_ops():
    # TRENT-like: SEBI's ProfitBeforeTax element sits before the share of JV loss
    q = qfacts(Q2, {"ProfitBeforeTax": 640.12, "ShareOfProfitLossOfAssociatesAndJointVenturesAccountedForUsingEquity"
                    "Method": -21.06, "ProfitLossFromDiscontinuedOperationsBeforeTax": 0})  # fmt: skip
    pbt = metric("PBT", q)
    assert pbt.value == pytest.approx(619.06) and len(pbt.inputs) == 2  # zero discontinued ops left out
    plain = metric("PBT", qfacts(Q2, {"ProfitBeforeTax": 500}))
    assert plain.value == 500 and plain.formula is None and plain.label == "PBT"


def test_screener_reconciliations_are_named_in_the_note():
    vals = {"RevenueFromOperations": 5873.14, "OtherIncome": 26.11, "FinanceCosts": 100, "DepreciationDepletionAnd"
            "AmortisationExpense": 364, "ProfitBeforeExceptionalItemsAndTax": 640.12, "ProfitBeforeTax": 640.12,
            "ShareOfProfitLossOfAssociatesAndJointVenturesAccountedForUsingEquityMethod": -21.06,
            "ProfitLossFromDiscontinuedOperationsBeforeTax": -3.10, "ProfitLossForPeriod": 466.59,
            "TaxExpense": 150.97}  # fmt: skip
    q = qfacts(Q2, vals, decimals="2")
    # screener: JV loss inside operating profit; PBT = PAT + tax
    t = one_quarter_table({"Sales": 5873, "Operating Profit": 1057, "Profit before tax": 618, "Net Profit": 467})
    d = build_from_quarters("standard", "consolidated", Q2, {"current": q} | ONLY, t, "xbrl", None).detail
    assert d.verification == "cross_checked", d.verification_note
    by = {x.metric: x.current for x in d.lines}
    assert "matches as EBITDA + share of associates/JVs" in by["EBITDA"].check_note
    assert by["EBITDA"].value == pytest.approx(1078.01)  # the card keeps operating EBITDA
    assert by["PBT"].value == pytest.approx(615.96)
    assert "matches as profit for the period + tax" in by["PBT"].check_note
    # a genuinely different number still fails
    bad = one_quarter_table({"Sales": 5873, "Operating Profit": 1000, "Profit before tax": 618, "Net Profit": 467})
    assert build_from_quarters("standard", "consolidated", Q2, {"current": q} | ONLY, bad, "xbrl",
                               None).detail.verification == "mismatch"  # fmt: skip


BANK = {"InterestEarned": 95131.63, "InterestExpended": 50667.43, "OperatingProfitBeforeProvisionAndContingencies":
        32871.54, "ProvisionsOtherThanTaxAndContingencies": 4209, "TaxExpense": 7125.45}  # fmt: skip


def test_consolidated_bank_pat_is_before_minority_whatever_the_tagging():
    # HDFCBANK Q2 FY27 put minority interest under ExceptionalItems; Q1 used the minority element
    sep = qfacts(Q2, BANK | {"ExceptionalItems": -837.06, "ProfitLossForThePeriod": 20700.03})
    jun = qfacts(Q1, BANK | {"ProfitLossOfMinorityInterest": 1137.98, "ProfitLossForThePeriod": 20382.69,
                             "ProvisionsOtherThanTaxAndContingencies": 3802.84 + 2471.54})  # fmt: skip
    a, b = metric("PAT", sep), metric("PAT", jun)
    assert a.value == pytest.approx(21537.09) and "before minority interest" in a.formula
    assert b.value == pytest.approx(32871.54 - 3802.84 - 2471.54 - 7125.45)
    standalone = qfacts(Q2, BANK | {"ProfitLossForThePeriod": 19509.96}, basis="standalone")
    assert metric("PAT", standalone).value == pytest.approx(19509.96) and metric("PAT", standalone).formula is None
    d = build_from_quarters("bank", "consolidated", Q2, {"current": sep} | ONLY, None, "xbrl", None).detail
    assert "minority" in (d.ebitda_note or "")


def test_nbfc_that_tags_interest_earned_is_not_a_bank_and_is_partly_checked():
    vals = {"InterestEarned": 21936.39, "FinanceCosts": 8601.73, "ImpairmentOnFinancialInstruments": 2166.09,
            "ProfitBeforeTax": 8533.47, "ProfitLossForPeriod": 6366.57, "RevenueFromOperations": 24546.37}  # fmt: skip
    q = qfacts(Q2, vals, decimals="2")
    assert template_for(q, "Non Banking Financial Company (NBFC)") == "nbfc"
    t = one_quarter_table({"Revenue": 24546, "Interest": 8602, "Profit before tax": 8533, "Net Profit": 6367})
    d = build_from_quarters("nbfc", "consolidated", Q2, {"current": q} | ONLY, t, "xbrl", None).detail
    by = {x.metric: x.current for x in d.lines}
    assert by["NII"].value == pytest.approx(21936.39 - 8601.73)
    # finance costs verified via screener 'Interest'; interest income has no screener row → line unverified
    assert by["NII"].status == "unverified"
    assert [i.status for i in by["NII"].inputs] == ["unverified", "verified"]
    assert by["PAT"].status == "verified"
    assert d.verification == "partial" and "NII" in d.verification_note and "PPOP" in d.verification_note


def test_revenue_reconciles_with_screener_net_of_itemised_excise():
    # RELIANCE Q2 FY27: Revenue from operations 3,32,861; excise duty 2,260 itemised under other expenses
    # (DescriptionOfOtherExpenses "Excise Duty", context OneExpenses1D); screener's Sales 3,30,601 = the difference.
    from finn.extraction.results.crosscheck import crosscheck

    xml = instance(Q2, {"RevenueFromOperations": 332861}).replace(
        b"</xbrli:xbrl>",
        b'<xbrli:context id="OneExpenses1D"><xbrli:entity><xbrli:identifier scheme="x">X</xbrli:identifier>'
        b'<xbrli:segment><xbrldi:explicitMember dimension="in-capmkt:OtherExpensesAxis">m1</xbrldi:explicitMember>'
        b"</xbrli:segment></xbrli:entity><xbrli:period><xbrli:startDate>2026-07-01</xbrli:startDate><xbrli:endDate>2026-09-30"
        b"</xbrli:endDate></xbrli:period></xbrli:context>"
        b'<in-capmkt:DescriptionOfOtherExpenses contextRef="OneExpenses1D">Excise Duty'
        b"</in-capmkt:DescriptionOfOtherExpenses>"
        b'<in-capmkt:OtherExpenses contextRef="OneExpenses1D" unitRef="INR" decimals="-7">22600000000'
        b"</in-capmkt:OtherExpenses>"
        b"</xbrli:xbrl>",
    )
    row = {"facts": parse_instance(xml), "basis": "consolidated", "xbrl_url": "https://x/q2.xml",
           "broadcast_at": NOW, "fetched_at": NOW}  # fmt: skip
    q = facts_from_xbrl(row, Q2)
    assert q.get("excise").value_cr == pytest.approx(2260)
    table = QuarterTable("RELIANCE", "consolidated", "https://screener", "Rs. Crores", [Q2], {"Sales": [330601.0]})
    lines = [x for x in build_lines("standard", q, None, None) if x.metric == "Revenue"]
    res = crosscheck("standard", lines, {"current": q, "previous": None, "year_ago": None}, table)
    rev = res.lines[0].current
    assert rev.value == pytest.approx(332861) and rev.status == "verified"
    assert "excise" in rev.check_note


def test_pbt_layout_follows_the_statement_screener_confirms():
    # RELIANCE Q2 FY27 prints PBT 38,613 before the JV share (300), which it adds after tax: PAT 29,550 + tax 9,363
    # = 38,913 is not its printed PBT. Screener's Profit before tax picks the layout.
    from finn.extraction.results.build import choose_pbt

    vals = {"RevenueFromOperations": 332861, "ProfitBeforeTax": 38613, "TaxExpense": 9363,
            "ShareOfProfitLossOfAssociatesAndJointVenturesAccountedForUsingEquityMethod": 300,
            "ProfitLossForPeriod": 29550}  # fmt: skip
    q = qfacts(Q2, vals)
    assert metric("PBT", q).value == pytest.approx(38913)  # default (unconfirmed): PAT + tax
    table = QuarterTable("RELIANCE", "consolidated", "https://screener", "Rs. Crores", [Q2],
                         {"Profit before tax": [38613.0]})  # fmt: skip
    choose_pbt("standard", {"current": q, "previous": None, "year_ago": None}, table)
    assert q.pbt_variant == "element" and metric("PBT", q).value == pytest.approx(38613)


def test_prior_quarter_disagreement_keeps_the_card_partial():
    from finn.extraction.results.crosscheck import crosscheck

    cur, prev = qfacts(Q2, INFY), qfacts(Q1, INFY)
    lines = [x for x in build_lines("standard", cur, prev, None) if x.metric == "Revenue"]
    table = QuarterTable("INFY", "consolidated", "https://screener", "Rs. Crores", [Q1, Q2],
                         {"Sales": [40000.0, 49244.0]})  # fmt: skip  # Q1 disagrees (restated), Q2 agrees
    res = crosscheck("standard", lines, {"current": cur, "previous": prev, "year_ago": None}, table)
    assert res.verification == "partial" and "earlier quarter" in res.note
    rev = res.lines[0]
    assert rev.current.status == "verified" and rev.previous.status == "unverified" and rev.qoq.status == "unverified"
