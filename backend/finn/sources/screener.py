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
