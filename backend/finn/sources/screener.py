"""screener.in standardised tables — used to cross-check results (never as the cited source of a number).

robots.txt allows /company/<SYM>/consolidated/ and /company/<SYM>/; we never follow /company/source/*.
One request per 3 s (http throttle), cached for an hour. Units: "Figures in Rs. Crores".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from bs4 import BeautifulSoup

from finn.numbers import parse_indian_number
from finn.sources.http import FetchError, finn_session, polite_get

BASE = "https://www.screener.in/company"
_MONTH_END = {"Mar": (3, 31), "Jun": (6, 30), "Sep": (9, 30), "Dec": (12, 31)}


@dataclass
class QuarterTable:
    symbol: str
    basis: str  # what the page says it shows: consolidated | standalone
    url: str
    unit_note: str
    periods: list[date]  # quarter ends, oldest → newest
    rows: dict[str, list[float | None]] = field(default_factory=dict)  # label → values aligned with periods
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def value(self, label: str, quarter_end: date) -> float | None:
        if label not in self.rows or quarter_end not in self.periods:
            return None
        return self.rows[label][self.periods.index(quarter_end)]

    def has(self, quarter_end: date) -> bool:
        return quarter_end in self.periods


def _period(text: str) -> date | None:
    m = re.match(r"([A-Z][a-z]{2})\s+(\d{4})$", text.strip())
    if not m or m.group(1) not in _MONTH_END:
        return None
    mo, d = _MONTH_END[m.group(1)]
    return date(int(m.group(2)), mo, d)


def _num(text: str) -> float | None:
    t = text.strip().replace("%", "")
    if not t:
        return None
    try:
        return parse_indian_number(t)
    except ValueError:
        return None


def parse_quarters(html: str, symbol: str, url: str) -> QuarterTable | None:
    soup = BeautifulSoup(html, "lxml")
    sec = soup.select_one("section#quarters")
    table = sec.select_one("table.data-table") if sec else None
    if not table:
        return None
    note = sec.select_one("p.sub")
    unit_note = " ".join(note.get_text(" ", strip=True).split()) if note else ""
    if "crore" not in unit_note.lower():
        return None  # never guess a unit
    basis = "standalone" if unit_note.lower().startswith("standalone") else "consolidated"
    heads = [th.get_text(strip=True) for th in table.select("thead th")][1:]
    periods = [_period(h) for h in heads]
    if not periods or any(p is None for p in periods):
        return None
    rows: dict[str, list[float | None]] = {}
    for tr in table.select("tbody tr"):
        cells = [td.get_text(" ", strip=True) for td in tr.select("td")]
        if not cells:
            continue
        label = cells[0].replace("\xa0", " ").rstrip(" +").strip()
        if label.startswith("YoY") or label == "Raw PDF":
            continue
        rows[label] = [_num(c) for c in cells[1 : 1 + len(periods)]]
    return QuarterTable(symbol, basis, url, unit_note, periods, rows)  # type: ignore[arg-type]


def fetch_quarters(symbol: str, basis: str = "consolidated", session=None) -> QuarterTable | None:
    url = f"{BASE}/{symbol}/consolidated/" if basis == "consolidated" else f"{BASE}/{symbol}/"
    r = polite_get(session or finn_session(), url, ttl=3600)
    if not r.ok:
        raise FetchError(url, r.status_code)
    return parse_quarters(r.text, symbol, url)


# ---------------------------------------------------------------------------------------------
# Research (Phase 3): every standardised table, document links, and the capex schedule.
# ---------------------------------------------------------------------------------------------

_MONTHS = {m: i for i, m in enumerate(("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov",
                                        "Dec"), start=1)}  # fmt: skip


@dataclass
class Column:
    label: str  # as printed: 'Mar 2026', 'TTM', 'Sep 2026'
    end: date | None  # period end (month end); None for TTM
    kind: str  # 'year' | 'interim' (a half-year column on the balance sheet) | 'ttm' | 'quarter'


@dataclass
class Table:
    section: str  # screener section id: quarters | profit-loss | balance-sheet | cash-flow | ratios | shareholding
    basis: str  # consolidated | standalone
    url: str
    unit_note: str
    columns: list[Column]
    rows: dict[str, list[float | None]] = field(default_factory=dict)
    raw: dict[str, list[str]] = field(default_factory=dict)  # values exactly as printed
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def get(self, row: str, col: Column) -> float | None:
        if row not in self.rows:
            return None
        return self.rows[row][self.columns.index(col)]

    def raw_value(self, row: str, col: Column) -> str | None:
        return self.raw.get(row, [None] * len(self.columns))[self.columns.index(col)]

    def years(self) -> list[Column]:
        return [c for c in self.columns if c.kind == "year"]

    def has(self, *rows: str) -> bool:
        return all(r in self.rows for r in rows)


def _month_end(mon: int, year: int) -> date:
    import calendar as _cal

    return date(year, mon, _cal.monthrange(year, mon)[1])


def _column(label: str) -> Column | None:
    t = label.strip()
    if t.upper() == "TTM":
        return Column(t, None, "ttm")
    m = re.match(r"([A-Z][a-z]{2})\s+(\d{4})", t)  # '15m' transition years print as 'Mar 2016 15m'
    if not m or m.group(1) not in _MONTHS:
        return None
    return Column(t, _month_end(_MONTHS[m.group(1)], int(m.group(2))), "year")


def year_end_month(cols: list[Column]) -> int | None:
    """The company's fiscal year-end month: the most common month among annual columns (Mar for most)."""
    months = [c.end.month for c in cols if c.end]
    return max(set(months), key=months.count) if months else None


def parse_table(soup_or_html, section: str, url: str, fetched_at: datetime | None = None) -> Table | None:
    soup = soup_or_html if isinstance(soup_or_html, BeautifulSoup) else BeautifulSoup(soup_or_html, "lxml")
    sec = soup.select_one(f"section#{section}")
    table = sec.select_one("table.data-table") if sec else None
    if not table:
        return None
    note = sec.select_one("p.sub")
    unit_note = " ".join(note.get_text(" ", strip=True).split()) if note else ""
    if section not in ("ratios", "shareholding") and "crore" not in unit_note.lower():
        return None  # never guess a unit
    basis = "standalone" if unit_note.lower().startswith("standalone") else "consolidated"
    heads = [th.get_text(" ", strip=True) for th in table.select("thead th")][1:]
    cols = [_column(h) for h in heads]
    if not cols or any(c is None for c in cols):
        return None
    if section == "quarters":
        for c in cols:
            c.kind = "quarter"
    else:  # a column whose month isn't the fiscal year-end is an interim (half-year) column
        ye = year_end_month([c for c in cols if c.kind == "year"][:-1] or cols)  # type: ignore[arg-type]
        for c in cols:
            if c.kind == "year" and ye and c.end.month != ye:  # type: ignore[union-attr]
                c.kind = "interim"
    rows: dict[str, list[float | None]] = {}
    raw: dict[str, list[str]] = {}
    for tr in table.select("tbody tr"):
        cells = [td.get_text(" ", strip=True) for td in tr.select("td")]
        if not cells:
            continue
        label = cells[0].replace("\xa0", " ").rstrip(" +").strip()
        if label == "Raw PDF" or label.startswith("CFO/EBITDA"):
            continue
        vals = cells[1 : 1 + len(cols)]
        rows[label] = [_num(c) for c in vals]
        raw[label] = vals
    return Table(section, basis, url, unit_note, cols, rows, raw, fetched_at or datetime.now(UTC))  # type: ignore[arg-type]


def parse_company(soup: BeautifulSoup) -> dict:
    h1 = soup.select_one("h1")
    ids = soup.select_one("[data-company-id]")
    ratios: dict[str, str] = {}
    for li in soup.select("#top-ratios li"):
        name = li.select_one(".name")
        val = li.select_one(".value")
        if name and val:
            ratios[" ".join(name.get_text(" ", strip=True).split())] = " ".join(val.get_text(" ", strip=True).split())
    return {
        "name": h1.get_text(" ", strip=True) if h1 else None,
        "company_id": ids.get("data-company-id") if ids else None,
        "warehouse_id": ids.get("data-warehouse-id") if ids else None,
        "top_ratios": ratios,
    }


def parse_documents(soup: BeautifulSoup) -> dict:
    """Transcript links (concall entries with a 'Transcript' link only — never notes/PPT/recordings) newest first,
    and annual-report links newest first."""
    out: dict[str, list[dict]] = {"transcripts": [], "annual_reports": []}
    docs = soup.select_one("section#documents")
    if not docs:
        return out
    cc = docs.select_one(".concalls")
    for li in cc.select("li") if cc else []:
        period = li.select_one(".ink-600") or li.select_one("div")
        label = " ".join(period.get_text(" ", strip=True).split()) if period else ""
        m = re.match(r"([A-Z][a-z]{2})\s+(\d{4})", label)
        for a in li.select("a[href]"):
            if a.get_text(strip=True).lower().startswith("transcript") and m and m.group(1) in _MONTHS:
                out["transcripts"].append({"month": date(int(m.group(2)), _MONTHS[m.group(1)], 1),
                                           "label": m.group(0), "url": a["href"]})  # fmt: skip
                break
    ar = docs.select_one(".annual-reports")
    for a in ar.select("a[href]") if ar else []:
        text = " ".join(a.get_text(" ", strip=True).split())
        m = re.search(r"(20\d{2})", text)
        out["annual_reports"].append({"title": text, "year": int(m.group(1)) if m else None, "url": a["href"]})
    return out


def fetch_page(symbol: str, consolidated: bool = True, session=None):
    """The company page (cached 1 h). Returns the response; 404 = screener has no page for this symbol."""
    url = f"{BASE}/{symbol}/consolidated/" if consolidated else f"{BASE}/{symbol}/"
    return polite_get(session or finn_session(), url, ttl=3600)


def fetch_schedule(company_id: str, parent: str, section: str, consolidated: bool, session=None) -> dict | None:
    """A table's '+' breakdown, e.g. parent='Cash from Investing Activity' → 'Fixed assets purchased' by year.
    robots.txt allows /api/company/<id>/schedules/. Returns {row: {period label: raw value}} or None."""
    params = {"parent": parent, "section": section}
    if consolidated:
        params["consolidated"] = ""
    r = polite_get(session or finn_session(), f"https://www.screener.in/api/company/{company_id}/schedules/",
                   params=params, ttl=3600)  # fmt: skip
    if not r.ok or "json" not in (r.content_type or ""):
        return None
    try:
        data = r.json()
    except ValueError:
        return None
    return {k: {p: v for p, v in vals.items() if p != "setAttributes"} for k, vals in data.items()
            if isinstance(vals, dict)}  # fmt: skip
