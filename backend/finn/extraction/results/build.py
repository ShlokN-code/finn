"""Results event → ResultsDetail (+ so-what and Level-0 impact, decided in code from the figures).

Order of sources for the current quarter: XBRL → PDF table → multimodal model on the PDF. Previous and
year-ago quarters come from their own XBRL filings (the PDF fallback carries them as columns).
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass
from datetime import date

from finn.calendar import previous_quarter_end, quarter_period, year_ago_quarter_end
from finn.constants import BASE_EFFECT_PCT
from finn.extraction.results.compute import (
    BANK_PAT_NOTE,
    EBITDA_NOTE,
    QuarterFacts,
    build_lines,
    facts_from_xbrl,
    metric,
)
from finn.extraction.results.crosscheck import crosscheck
from finn.models import Citation, Claim, Figure, ResultsDetail, ResultsLine, Series
from finn.numbers import pct_change, round_display
from finn.sources.screener import QuarterTable

log = logging.getLogger("finn.results")


@dataclass
class Built:
    detail: ResultsDetail
    so_what: str
    impact: str | None
    impact_reason: Claim | None


def pick_xbrl(rows: list[dict], quarter_end: date, basis: str) -> dict | None:
    """Rows come newest-version first (Revised before Original, latest broadcast first)."""
    for r in rows:
        if r["period_end"] == quarter_end and r["basis"] == basis:
            return r
    return None


def quarters_from_xbrl(rows: list[dict], quarter_end: date, prefer: str = "consolidated"):
    """→ (basis, {"current", "previous", "year_ago"}) or None when the current quarter has no XBRL yet.
    All three on the same basis (consolidated by default; standalone when that is all the company files)."""
    for basis in (prefer, "standalone" if prefer == "consolidated" else "consolidated"):
        cur = pick_xbrl(rows, quarter_end, basis)
        if not cur:
            continue
        prev = pick_xbrl(rows, previous_quarter_end(quarter_end), basis)
        ya = pick_xbrl(rows, year_ago_quarter_end(quarter_end), basis)
        q = {
            "current": facts_from_xbrl(cur, quarter_end),
            "previous": facts_from_xbrl(prev, previous_quarter_end(quarter_end)) if prev else None,
            "year_ago": facts_from_xbrl(ya, year_ago_quarter_end(quarter_end)) if ya else None,
        }
        return basis, q
    return None


def margin_series(table: QuarterTable | None, n: int = 8) -> Series | None:
    """EBITDA-margin sparkline from screener (Operating Profit ÷ Sales, computed here), labelled as screener."""
    if table is None or "Operating Profit" not in table.rows:
        return None
    pts: list[Figure] = []
    for qe in table.periods[-n:]:
        op = table.value("Operating Profit", qe)
        sales = table.value("Sales", qe) or table.value("Revenue", qe)
        if op is None or not sales or sales <= 0:
            continue
        per = quarter_period(qe)

        def src(label: str, v: float, row: str, _qe=qe, _per=per) -> Figure:
            cite = Citation(
                source_type="screener_table",
                url=table.url,
                title="screener.in quarterly results",
                locator=f"screener:quarters/{row}/{_qe:%b %Y}",
                retrieved_at=table.fetched_at,
            )
            return Figure(label=label, value=v, unit="INR_CR", period=_per, basis=table.basis,
                          status="unverified", citation=cite)  # fmt: skip

        ins = [src("Operating Profit", op, "Operating Profit"), src("Sales", sales, "Sales")]
        pts.append(Figure(label="EBITDA margin", value=op / sales * 100, unit="PCT", period=per, basis=table.basis,
                          status="unverified", formula="Operating Profit ÷ Sales × 100", inputs=ins))  # fmt: skip
    if len(pts) < 2:
        return None
    return Series(metric="EBITDA margin (screener)", unit="PCT", basis=table.basis, points=pts)


def trend_pat_yoy(table: QuarterTable | None, quarter_end: date) -> float | None:
    """Median PAT YoY % over the four quarters before `quarter_end` (needs 8 earlier quarters on screener).
    YoYs above +100% are left out (low-base effects, e.g. a steelmaker recovering from a weak year); fewer than
    two comparable quarters → None (no surprise factor)."""
    if table is None or "Net Profit" not in table.rows:
        return None
    ps = [p for p in table.periods if p < quarter_end]
    vals = table.rows["Net Profit"]
    yoys = []
    for p in ps[-4:]:
        i = table.periods.index(p)
        if i >= 4 and vals[i] is not None and vals[i - 4] is not None:
            y = pct_change(vals[i], vals[i - 4])
            if y is not None and y <= BASE_EFFECT_PCT:
                yoys.append(y)
    return statistics.median(yoys) if len(yoys) >= 2 else None


def _fmt_pct(fig: Figure | None, unit_word: str = "") -> str | None:
    if fig is None or fig.value is None:
        return None
    if fig.unit == "BPS":
        v = round_display(fig.value, 0)
        return f"{'+' if v > 0 else '−' if v < 0 else '±'}{abs(v)} bps"
    v = round_display(fig.value, 1)
    return f"{'+' if v > 0 else '−' if v < 0 else '±'}{abs(v)}%"


def _line(lines: list[ResultsLine], m: str) -> ResultsLine | None:
    return next((x for x in lines if x.metric == m), None)


def impact_from_lines(template: str, lines: list[ResultsLine]) -> tuple[str | None, list[tuple[str, Figure]]]:
    """Level 0 for results, in code: top line and bottom line YoY both up → positive, both down → negative,
    otherwise mixed. Missing YoY on either → no tag."""
    top = _line(lines, "Revenue" if template == "standard" else "NII")
    bottom = _line(lines, "PAT")
    pairs = [(x.metric, x.yoy) for x in (top, bottom) if x and x.yoy and x.yoy.value is not None]
    if len(pairs) < 2:
        return None, pairs
    up = [f.value > 0 for _, f in pairs]
    return ("positive" if all(up) else "negative" if not any(up) else "mixed"), pairs


def so_what_for(template: str, lines: list[ResultsLine], verification: str) -> str:
    if verification == "mismatch":
        return "Couldn't verify the numbers — open the filing"
    top = _line(lines, "Revenue" if template == "standard" else "NII")
    second = _line(lines, "EBITDA margin") if template == "standard" else _line(lines, "PAT")
    parts = []
    if top and (s := _fmt_pct(top.yoy)):
        parts.append(f"{top.metric} {s} YoY")
    if second and (s := _fmt_pct(second.yoy)):
        name = "margin" if second.metric == "EBITDA margin" else second.metric
        parts.append(f"{name} {s}")
    return "; ".join(parts) or "Results filed"


def build_from_quarters(
    template: str,
    basis: str,
    quarter_end: date,
    quarters: dict[str, QuarterFacts | None],
    table: QuarterTable | None,
    source_path: str,
    filing_url: str | None,
) -> Built:
    lines = build_lines(template, quarters["current"], quarters["previous"], quarters["year_ago"])
    table_ok = table if table is not None and table.basis == basis else None
    chk = crosscheck(template, lines, quarters, table_ok)
    note = chk.note
    if table is not None and table_ok is None:
        note = f"screener shows {table.basis} figures only; {basis} not cross-checked"
    detail = ResultsDetail(
        template=template, basis=basis, quarter=quarter_period(quarter_end), source_path=source_path,
        verification=chk.verification if table_ok is not None or chk.verification == "mismatch" else "pending",
        verification_note=note, filing_url=filing_url, lines=chk.lines,
        margin_series=margin_series(table_ok) if template == "standard" else None,
        ebitda_note=EBITDA_NOTE if template == "standard"
        else BANK_PAT_NOTE if template == "bank" and basis == "consolidated" else None,
        trend_pat_yoy_pct=trend_pat_yoy(table_ok, quarter_end),
    )  # fmt: skip
    impact, pairs = impact_from_lines(template, chk.lines)
    reason = None
    if impact and detail.verification != "mismatch":
        text = ", ".join(f"{m} {_fmt_pct(f)} YoY" for m, f in pairs) + f" ({basis}, {detail.quarter.label})"
        cites = [c for _, f in pairs for i in f.inputs if (c := i.citation)][:2]
        status = "verified" if all(f.status == "verified" for _, f in pairs) else "unverified"
        if cites:
            reason = Claim(text=text, status=status, citations=cites)
    if detail.verification == "mismatch":
        impact = None
    return Built(detail, so_what_for(template, chk.lines, detail.verification), impact, reason)


def check_metric_presence(q: QuarterFacts, template: str) -> list[str]:
    from finn.extraction.results.compute import METRICS

    return [m for m in METRICS[template] if metric(m, q) is None]
