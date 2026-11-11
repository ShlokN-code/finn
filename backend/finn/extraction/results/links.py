"""Human-readable links for results figures (DECISIONS: readable Open links).

Results numbers are *read* from NSE's XBRL instances, but an XBRL file is a wall of tags. A figure's Open link
therefore points, in this order, to:
  1. the results PDF filed on the exchange (the outcome announcement in the card's event thread), at the page
     holding the statement for the figure's basis — found here in code from the PDF text;
  2. NSE's iXBRL (HTML) view of the same filing, when there's no PDF or no page;
  3. the raw XBRL only as a secondary "machine-readable" link (`Citation.raw_url`), kept for auditability.
Every results figure also carries `check_url`: screener's quarterly table, the independent cross-check.

Pure functions: no I/O. The pipeline downloads PDFs (Actions only — NSE archives are blocked from Render).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from finn.models import Citation, Claim, Figure, ResultsDetail

# Statement line items (start of a printed row). Banks/NBFCs use the interest lines.
LINE_ITEMS = [
    r"revenue from operations",
    r"total income",
    r"other income",
    r"finance costs?",
    r"depreciation",
    r"total expenses",
    r"profit\s*/?\s*\(?loss\)? before (?:exceptional items and )?tax",
    r"profit before tax",
    r"tax expense",
    r"interest earned",
    r"interest expended",
    r"operating profit before provisions",
]
_LINE_RE = [re.compile(p, re.I) for p in LINE_ITEMS]
_NUM = re.compile(r"\(?-?\d[\d,]*\.?\d*\)?")
HEAD_CHARS = 900  # the statement's title sits at the top of its page
FIGURE_FIELDS = ("current", "previous", "year_ago", "qoq", "yoy")


@dataclass
class PageMatch:
    page: int  # 1-based
    value_on_page: bool
    score: int


def _numbers(text: str) -> list[tuple[float, int]]:
    """(value, decimals printed) for every number on the page."""
    out = []
    for tok in _NUM.findall(text):
        t = tok.strip("()").replace(",", "")
        if not t or t in ("-", "."):
            continue
        try:
            out.append((abs(float(t)), len(t.split(".")[1]) if "." in t else 0))
        except ValueError:
            continue
    return out


def value_printed(text: str, value_cr: float | None) -> bool:
    """Is a ₹ crore value printed on the page in crore, lakh or million? A printed number matches within half a
    unit of its own last digit (or 0.05% for rounding of large values) — 111.46 is not 111.59."""
    if value_cr is None or value_cr == 0:
        return False
    targets = [abs(value_cr), abs(value_cr) * 100, abs(value_cr) * 10]  # crore, lakh, million
    for n, dec in _numbers(text):
        tol = 0.5 * 10 ** (-dec)
        for t in targets:
            if t >= 1 and abs(n - t) <= max(tol, t * 0.0005):
                return True
    return False


def find_results_page(pages: list[str], basis: str, revenue_cr: float | None = None) -> PageMatch | None:
    """The page holding the quarterly statement for `basis` ('consolidated' | 'standalone').

    A candidate page prints at least 3 statement line items. It scores for naming its basis in the heading, loses
    for naming only the other basis there, and scores most when the card's revenue (or NII input) is printed on
    it in crore, lakh or million — that also tells the reader the number is on the page we open.
    """
    other = "standalone" if basis == "consolidated" else "consolidated"
    best: PageMatch | None = None
    for i, text in enumerate(pages, start=1):
        low = text.lower()
        items = sum(1 for r in _LINE_RE if r.search(low))
        if items < 3:
            continue
        head = low[:HEAD_CHARS]
        score = items
        if basis in head:
            score += 6
        elif basis in low:
            score += 2
        if other in head and basis not in head:
            score -= 8
        if basis == "standalone" and "consolidated" in low and "standalone" not in low:
            score -= 8  # an unlabelled page in a PDF that also has a consolidated statement
        on_page = value_printed(text, revenue_cr)
        if on_page:
            score += 10
        if score <= items:  # nothing ties this page to the basis
            continue
        if best is None or score > best.score:
            best = PageMatch(i, on_page, score)
    return best


@dataclass
class ResultsDoc:
    url: str
    page: int | None


def _label_from_title(title: str | None) -> str | None:
    m = re.search(r"(Q[1-4] FY\d{2})", title or "")
    return m.group(1) if m else None


def screener_quarters_url(symbol: str, basis: str) -> str:
    return f"https://www.screener.in/company/{symbol}/{'consolidated/' if basis == 'consolidated' else ''}#quarters"


def readable(
    c: Citation | None,
    *,
    card_quarter: str,
    basis: str,
    pdf: ResultsDoc | None,
    ixbrl: dict[str, str],
    check_url: str | None,
    fact_quarter: str | None = None,
) -> Citation | None:
    """An XBRL citation → the most readable document for it (PDF page → iXBRL view → raw, labelled)."""
    if c is None or c.source_type != "xbrl":
        return c
    raw = c.raw_url or c.url
    q = fact_quarter or _label_from_title(c.title) or card_quarter
    column = "" if q == card_quarter else f" · {q} column"
    if pdf is not None:
        return c.model_copy(update={
            "url": pdf.url, "page": pdf.page, "doc_kind": "results_pdf", "raw_url": raw, "check_url": check_url,
            "title": f"{card_quarter} results PDF ({basis}){column}",
        })  # fmt: skip
    if raw in ixbrl:
        return c.model_copy(update={
            "url": ixbrl[raw], "page": None, "doc_kind": "ixbrl", "raw_url": raw, "check_url": check_url,
            "title": f"{q} results, iXBRL view ({basis})",
        })  # fmt: skip
    return c.model_copy(update={"url": raw, "doc_kind": "raw_xbrl", "raw_url": raw, "check_url": check_url})


def _figure(f: Figure | None, **kw) -> Figure | None:
    if f is None:
        return None
    return f.model_copy(update={
        "citation": readable(f.citation, fact_quarter=f.period.label if f.period else None, **kw),
        "inputs": [_figure(i, **kw) for i in f.inputs],
    })  # fmt: skip


def apply_links(
    detail: ResultsDetail,
    impact_reason: Claim | None,
    *,
    symbol: str,
    pdf: ResultsDoc | None,
    ixbrl: dict[str, str],
) -> tuple[ResultsDetail, Claim | None]:
    """Rewrite every XBRL citation in a results card (lines, their inputs, the impact reason)."""
    kw = {
        "card_quarter": detail.quarter.label,
        "basis": detail.basis,
        "pdf": pdf,
        "ixbrl": ixbrl,
        "check_url": screener_quarters_url(symbol, detail.basis),
    }
    lines = [ln.model_copy(update={k: _figure(getattr(ln, k), **kw) for k in FIGURE_FIELDS}) for ln in detail.lines]
    out = detail.model_copy(update={"lines": lines})
    if impact_reason is not None:
        impact_reason = impact_reason.model_copy(
            update={"citations": [readable(c, **kw) for c in impact_reason.citations]}
        )
    return out, impact_reason


def revenue_input_cr(detail: ResultsDetail) -> float | None:
    """The card's current revenue (NII inputs for lenders: interest earned / income) to look for on the page."""
    for ln in detail.lines:
        if ln.metric in ("Revenue",) and ln.current.value is not None:
            return ln.current.value
    for ln in detail.lines:
        for i in ln.current.inputs:
            if i.label.lower().startswith(("interest earned", "interest income", "revenue")) and i.value is not None:
                return i.value
    return None
