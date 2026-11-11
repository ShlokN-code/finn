"""Step 1 — discover: screener's standardised tables and the document index for one ticker.

Consolidated first; standalone when screener has no consolidated tables (companies without subsidiaries). The
last 8 earnings-call transcripts and the latest annual report come from screener's document list (mostly
BSE-hosted PDFs, which Render can fetch). NSE-hosted links are skipped on Render (NSE blocks it).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from bs4 import BeautifulSoup

from finn.calendar import now_utc, quarter_end_on_or_before, quarter_period
from finn.sources.http import FetchError
from finn.sources.screener import (
    Table,
    fetch_page,
    fetch_schedule,
    parse_company,
    parse_documents,
    parse_table,
    year_end_month,
)

log = logging.getLogger("finn.research.discover")

SECTIONS = ("quarters", "profit-loss", "balance-sheet", "cash-flow", "ratios", "shareholding")
MAX_TRANSCRIPTS = 8


@dataclass
class DocLink:
    kind: str  # transcript | annual_report
    url: str
    title: str
    period_label: str | None  # quarter the call discussed ('Q2 FY27') / 'FY26' for an annual report
    call_month: date | None  # screener gives the call's month
    quarter_end: date | None = None


@dataclass
class Discovery:
    symbol: str
    status: str  # ok | no_screener_page | source_unreachable
    note: str | None = None
    basis: str | None = None
    url: str | None = None
    name: str | None = None
    company_id: str | None = None
    top_ratios: dict = field(default_factory=dict)
    tables: dict[str, Table] = field(default_factory=dict)
    transcripts: list[DocLink] = field(default_factory=list)  # newest first, ≤ 8, one per quarter
    annual_report: DocLink | None = None
    decks: dict = field(default_factory=dict)  # quarter end → DocLink of that quarter's investor deck
    capex: dict[str, str] | None = None  # 'Fixed assets purchased' by period label, as printed
    fixed_assets_sold: dict[str, str] | None = None
    year_end_month: int | None = None
    template: str = "standard"
    fetched_at: datetime = field(default_factory=now_utc)

    def table(self, section: str) -> Table | None:
        return self.tables.get(section)


def template_for(tables: dict[str, Table]) -> str:
    """Lenders have screener's 'Financing Profit' row; banks also report Deposits."""
    pl = tables.get("profit-loss") or tables.get("quarters")
    if pl is None or "Financing Profit" not in pl.rows:
        return "standard"
    bs = tables.get("balance-sheet")
    return "bank" if bs is not None and "Deposits" in bs.rows else "nbfc"


def transcript_quarter(call_month: date) -> date:
    """A call held in month M discusses the quarter that ended before M (Oct 2026 call → Q2 FY27)."""
    return quarter_end_on_or_before(call_month - timedelta(days=1))


def _from_html(symbol: str, html: str, url: str, fetched_at: datetime) -> Discovery:
    soup = BeautifulSoup(html, "lxml")
    tables = {s: t for s in SECTIONS if (t := parse_table(soup, s, url, fetched_at)) is not None}
    company = parse_company(soup)
    docs = parse_documents(soup)
    d = Discovery(symbol=symbol, status="ok", url=url, name=company["name"], company_id=company["company_id"],
                  top_ratios=company["top_ratios"], tables=tables, fetched_at=fetched_at)  # fmt: skip
    pl = tables.get("profit-loss")
    d.basis = (pl or next(iter(tables.values()), None)).basis if tables else None
    d.year_end_month = year_end_month(pl.years()) if pl else None
    d.template = template_for(tables)
    seen: set[date] = set()
    for t in docs["transcripts"]:
        qe = transcript_quarter(t["month"])
        if qe in seen or "nseindia.com" in t["url"]:
            continue
        seen.add(qe)
        label = quarter_period(qe).label
        d.transcripts.append(
            DocLink("transcript", t["url"], f"{label} earnings call transcript", label, t["month"], qe)
        )
        if len(d.transcripts) >= MAX_TRANSCRIPTS:
            break
    for t in docs["decks"]:
        qe = transcript_quarter(t["month"])
        if qe in d.decks or "nseindia.com" in t["url"]:
            continue
        label = quarter_period(qe).label
        d.decks[qe] = DocLink(
            "investor_presentation", t["url"], f"{label} investor presentation", label, t["month"], qe
        )
    for a in docs["annual_reports"]:
        if "nseindia.com" in a["url"]:
            continue
        label = f"FY{a['year'] % 100:02d}" if a["year"] else None
        d.annual_report = DocLink("annual_report", a["url"], a["title"], label, None)
        break
    return d


def discover(symbol: str, session=None, with_schedules: bool = True) -> Discovery:
    """Fetch and parse screener for `symbol`. Never raises for a missing page or an unreachable source."""
    try:
        r = fetch_page(symbol, consolidated=True, session=session)
        if r.status_code == 404:
            return Discovery(symbol, "no_screener_page", note=f"screener.in has no page for {symbol}")
        if not r.ok:
            raise FetchError(r.url, r.status_code)
        fetched = datetime.fromtimestamp(r.fetched_at).astimezone()
        d = _from_html(symbol, r.text, r.url, fetched)
        if "profit-loss" not in d.tables:  # no consolidated tables → standalone page
            r2 = fetch_page(symbol, consolidated=False, session=session)
            if r2.ok:
                d2 = _from_html(symbol, r2.text, r2.url, datetime.fromtimestamp(r2.fetched_at).astimezone())
                if "profit-loss" in d2.tables:
                    d2.transcripts, d2.annual_report = (
                        d2.transcripts or d.transcripts,
                        d2.annual_report or d.annual_report,
                    )
                    d = d2
    except FetchError as e:
        log.warning("screener unreachable for %s: %s", symbol, e)
        return Discovery(symbol, "source_unreachable", note=f"screener.in unreachable ({e.status or 'network'})")
    if not d.tables:
        d.status, d.note = "no_screener_page", f"screener.in shows no standardised financials for {symbol}"
    elif with_schedules and d.company_id and d.template == "standard":
        sched = fetch_schedule(d.company_id, "Cash from Investing Activity", "cash-flow",
                               consolidated=d.basis == "consolidated", session=session)  # fmt: skip
        if sched:
            d.capex = sched.get("Fixed assets purchased")
            d.fixed_assets_sold = sched.get("Fixed assets sold")
    return d
