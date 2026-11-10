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


def qfacts(qe: date, values: dict[str, float], basis: str = "consolidated") -> QuarterFacts:
    row = {
        "facts": parse_instance(instance(qe, values)),
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
    assert e.value == pytest.approx(11063 + 115 + 1359 - 848)  # 11,689
    assert "other income" in e.formula and len(e.inputs) == 4


def test_ebitda_excludes_exceptional_items_when_only_pbt_is_given():
    vals = {k: v for k, v in INFY.items() if k != "ProfitBeforeExceptionalItemsAndTax"}
    vals |= {"ProfitBeforeTax": 11063 - 300, "ExceptionalItemsBeforeTax": -300}
    e = metric("EBITDA", qfacts(Q2, vals))
    assert e.value == pytest.approx(11689)  # a ₹300 Cr one-off loss doesn't depress operating EBITDA


def test_margin_and_bps_change():
    cur = qfacts(Q2, INFY)
    prev = qfacts(Q1, INFY | {"RevenueFromOperations": 47000})
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
