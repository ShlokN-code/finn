"""Screener tables → computed trajectory, cash quality and balance sheet (code calculates; every value cited)."""

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from finn.research.compute import cagr, compute, year_label
from finn.research.discover import _from_html, template_for, transcript_quarter
from finn.sources.screener import parse_table

FIX = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 11, 11, tzinfo=UTC)


def disc(sym: str, schedule: bool = False):
    d = _from_html(sym, (FIX / f"screener_{sym}.html").read_text(), f"https://www.screener.in/company/{sym}/consolidated/",
                   NOW)  # fmt: skip
    if schedule:
        sch = json.loads((FIX / f"screener_{sym}_cfi_schedule.json").read_text())
        d.capex = {k: v for k, v in sch["Fixed assets purchased"].items() if k != "setAttributes"}
        d.fixed_assets_sold = {k: v for k, v in sch["Fixed assets sold"].items() if k != "setAttributes"}
    return d


def test_table_columns_ttm_and_half_year():
    html = (FIX / "screener_POLYCAB.html").read_text()
    pl = parse_table(html, "profit-loss", "u")
    bs = parse_table(html, "balance-sheet", "u")
    assert pl.columns[-1].kind == "ttm" and pl.columns[-2].kind == "year"
    assert bs.columns[-1].kind == "interim" and bs.columns[-1].label == "Sep 2026"
    assert pl.raw["Sales"][-2] and pl.rows["Sales"][-2] == 28884.0
    assert parse_table(html, "ratios", "u").rows["ROCE %"]  # ratios carry no crore note and still parse


@pytest.mark.parametrize("sym,template", [("POLYCAB", "standard"), ("INFY", "standard"), ("BAJFINANCE", "nbfc"),
                                           ("HDFCBANK", "bank")])  # fmt: skip
def test_template_detection(sym, template):
    d = disc(sym)
    assert template_for(d.tables) == template == d.template


def test_transcripts_last_8_one_per_quarter_labelled_by_quarter_discussed():
    d = disc("INFY")
    assert len(d.transcripts) == 8
    assert d.transcripts[0].period_label == "Q2 FY27" and d.transcripts[0].call_month == date(2026, 10, 1)
    assert len({t.period_label for t in d.transcripts}) == 8
    assert transcript_quarter(date(2026, 5, 1)) == date(2026, 3, 31)  # a May call discusses Q4
    assert d.annual_report and d.annual_report.period_label == "FY26"


def test_standard_figures_cited_and_fcf_matches_screener():
    c = compute(disc("POLYCAB", schedule=True))
    rev = next(s for s in c.trajectory if s.metric == "Revenue")
    last = rev.points[-1]
    assert last.value == 28884.0 and last.period.label == "FY26" and last.citation.locator == \
        "screener:profit-loss/Sales/Mar 2026"  # fmt: skip
    fcf = next(s for s in c.cash if s.metric == "Free cash flow")
    assert all(p.status == "verified" and "✓" in p.check_note for p in fcf.points)  # every year equals screener's row
    assert fcf.points[-1].value == 2340.0
    capex = next(s for s in c.cash if s.metric == "Capex")
    assert capex.points[-1].value > 0  # spend shown as a positive number
    de = next(s for s in c.balance if s.metric == "Debt/Equity").points[-1]
    assert (
        de.formula
        and len(de.inputs) == 3
        and de.value == pytest.approx(236 / (de.inputs[1].value + de.inputs[2].value))
    )
    assert any(g.label == "Revenue CAGR 5y" for g in c.growth)


def test_lenders_get_nii_and_no_cash_quality():
    for sym in ("BAJFINANCE", "HDFCBANK"):
        c = compute(disc(sym))
        metrics = {s.metric for s in c.trajectory}
        assert "NII" in metrics and "Operating margin (OPM)" not in metrics and not c.cash_applicable
        nii = next(s for s in c.trajectory if s.metric == "NII").points[-1]
        assert nii.value == nii.inputs[0].value - nii.inputs[1].value
    assert "Deposits" in {s.metric for s in compute(disc("HDFCBANK")).balance}


def test_cagr_rules():
    c = compute(disc("POLYCAB"))
    rev = next(s for s in c.trajectory if s.metric == "Revenue").points
    g = cagr(rev[-6], rev[-1], "x")
    assert g.value == pytest.approx(((rev[-1].value / rev[-6].value) ** (1 / 5) - 1) * 100)
    neg = rev[-6].model_copy(update={"value": -5.0})
    assert cagr(neg, rev[-1], "x") is None  # base ≤ 0 → not meaningful, never a number


def test_year_labels():
    assert year_label(date(2026, 3, 31)) == "FY26" and year_label(date(2025, 12, 31)) == "Dec 2025"
