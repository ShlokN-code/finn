"""Readable Open links: results PDF page finder, link-choice order, filing links (DECISIONS: readable links).

Fixtures are two pages cut from real Q2 FY27 results PDFs on NSE archives (page 1 = standalone statement,
page 2 = consolidated): TRENT (text layer) and HDFCBANK (OCR'd scan: zeros read as 'O' in places).
"""

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from finn.citations import filing_doc, pdf_text
from finn.extraction.results.links import (
    ResultsDoc,
    apply_links,
    find_results_page,
    readable,
    screener_quarters_url,
    value_printed,
)
from finn.models import Citation, Claim, Figure, Period, ResultsDetail, ResultsLine

FX = Path(__file__).parent / "fixtures" / "results_pdf"
NOW = datetime(2026, 11, 12, tzinfo=UTC)


def pages(name: str) -> list[str]:
    _, p = pdf_text((FX / name).read_bytes(), max_pages=10)
    return p


@pytest.mark.parametrize(
    "fixture,revenue_cr",
    [("trent_q2fy27_p3_p10.pdf", 5873.14), ("hdfcbank_q2fy27_p2_p9.pdf", 95131.63)],
)
def test_page_finder_matches_basis_and_finds_the_number(fixture, revenue_cr):
    p = pages(fixture)
    cons = find_results_page(p, "consolidated", revenue_cr)
    assert cons is not None and cons.page == 2 and cons.value_on_page
    stand = find_results_page(p, "standalone")
    assert stand is not None and stand.page == 1


def test_page_finder_needs_a_statement():
    assert find_results_page(["Outcome of board meeting. Dividend declared.", "Press release"], "consolidated") is None


def test_value_printed_in_crore_lakh_or_million():
    assert value_printed("Revenue from operations 49,244 48,100", 49244.0)  # crore
    assert value_printed("Revenue from operations 49,24,400.00", 49244.0)  # lakh
    assert value_printed("Revenue from operations 492,440", 49244.0)  # million
    assert not value_printed("Revenue from operations 12,345", 49244.0)


XBRL = "https://nsearchives.nseindia.com/corporate/xbrl/INTEGRATED_FILING_INDAS_1_WEB.xml"
IXBRL = "https://nsearchives.nseindia.com/corporate/ixbrl/INTEGRATED_FILING_INDAS_1_iXBRL_WEB.html"
PDF = "https://nsearchives.nseindia.com/corporate/X_Outcome.pdf"


def xcite(q="Q2 FY27") -> Citation:
    return Citation(source_type="xbrl", url=XBRL, title=f"XBRL results {q} (consolidated)", exchange="NSE",
                    locator="in-capmkt:RevenueFromOperations@OneD", retrieved_at=NOW)  # fmt: skip


def test_link_order_pdf_then_ixbrl_then_raw():
    kw = {"card_quarter": "Q2 FY27", "basis": "consolidated", "check_url": "https://www.screener.in/x#quarters"}
    a = readable(xcite(), pdf=ResultsDoc(PDF, 3), ixbrl={XBRL: IXBRL}, **kw)
    assert (a.url, a.page, a.doc_kind, a.raw_url) == (PDF, 3, "results_pdf", XBRL)
    assert a.locator == "in-capmkt:RevenueFromOperations@OneD" and a.source_type == "xbrl"
    b = readable(xcite(), pdf=None, ixbrl={XBRL: IXBRL}, **kw)
    assert (b.url, b.page, b.doc_kind, b.raw_url) == (IXBRL, None, "ixbrl", XBRL)
    c = readable(xcite(), pdf=None, ixbrl={}, **kw)
    assert (c.url, c.doc_kind, c.raw_url) == (XBRL, "raw_xbrl", XBRL)
    other = Citation(source_type="screener_table", url="https://www.screener.in/company/X/", retrieved_at=NOW)
    assert readable(other, pdf=ResultsDoc(PDF, 3), ixbrl={}, **kw) is other


def test_relinking_twice_is_stable():
    kw = {"card_quarter": "Q2 FY27", "basis": "consolidated", "check_url": None}
    once = readable(xcite(), pdf=None, ixbrl={XBRL: IXBRL}, **kw)
    twice = readable(once, pdf=ResultsDoc(PDF, 4), ixbrl={XBRL: IXBRL}, **kw)
    assert (twice.url, twice.page, twice.raw_url) == (PDF, 4, XBRL)


def fig(label, v, q="Q2 FY27", end=date(2026, 9, 30), inputs=()):
    per = Period(kind="quarter", start=None, end=end, label=q)
    if inputs:
        return Figure(label=label, value=v, unit="PCT", status="verified", period=per, formula="a/b-1",
                      inputs=list(inputs))  # fmt: skip
    return Figure(label=label, value=v, unit="INR_CR", status="verified", period=per, citation=xcite(q),
                  basis="consolidated")  # fmt: skip


def test_apply_links_rewrites_every_quarter_and_input():
    cur, prev = fig("Revenue", 100.0), fig("Revenue", 90.0, "Q1 FY27", date(2026, 6, 30))
    ln = ResultsLine(metric="Revenue", current=cur, previous=prev, year_ago=None,
                     qoq=fig("Revenue QoQ", 11.1, inputs=[cur, prev]), yoy=None, check="match")  # fmt: skip
    d = ResultsDetail(kind="results", quarter=Period(kind="quarter", start=None, end=date(2026, 9, 30),
                      label="Q2 FY27"), basis="consolidated", template="standard", source_path="xbrl",
                      verification="cross_checked", lines=[ln])  # fmt: skip
    reason = Claim(text="Revenue up", status="verified", citations=[xcite()])
    out, r = apply_links(d, reason, symbol="TRENT", pdf=ResultsDoc(PDF, 2), ixbrl={})
    o = out.lines[0]
    assert o.current.citation.url == PDF and o.current.citation.page == 2
    assert o.previous.citation.title == "Q2 FY27 results PDF (consolidated) · Q1 FY27 column"
    assert all(i.citation.doc_kind == "results_pdf" for i in o.qoq.inputs)
    assert o.current.citation.check_url == screener_quarters_url("TRENT", "consolidated")
    assert r.citations[0].url == PDF


def test_filing_doc_prefers_pdf_then_ixbrl():
    ix = "https://nsearchives.nseindia.com/corporate/ixbrl/PRIOR_INTIMATION_1_WEB.html"
    xml = "https://nsearchives.nseindia.com/corporate/xbrl/PRIOR_INTIMATION_1.xml"
    assert filing_doc({"attachment_url": PDF}) == (PDF, "pdf", None)
    assert filing_doc({"attachment_url": None, "xbrl_url": xml, "raw": {"ixbrl": ix}}) == (ix, "ixbrl", xml)
    assert filing_doc({"attachment_url": "-", "xbrl_url": xml}) == (xml, "raw_xbrl", xml)
    assert filing_doc({"attachment_url": "-"}) is None
    assert filing_doc({"attachment_url": "https://x/KMP_Doc.zip"})[1] == "zip"
