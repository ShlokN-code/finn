"""Cross-check results lines against screener's quarterly table, plus sanity checks (trust layer §10.3).

Outcomes: every checked value agrees → cross_checked; screener hasn't published the quarter → pending;
any disagreement or failed sanity check → mismatch ("Couldn't verify — open filing", no numbers shown).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from finn.extraction.results.compute import QuarterFacts, metric, tolerance_cr
from finn.models import Figure, ResultsLine
from finn.numbers import approx_equal
from finn.sources.screener import QuarterTable


def _row(t: QuarterTable, qe: date, *labels: str) -> float | None:
    for lab in labels:
        v = t.value(lab, qe)
        if v is not None:
            return v
    return None


def _screener_value(template: str, m: str, t: QuarterTable, qe: date) -> tuple[float | None, str]:
    """What screener says for metric `m` (or the comparable quantity) and a note naming the rows used."""
    if template == "standard":
        lab = {"Revenue": ("Sales", "Revenue"), "EBITDA": ("Operating Profit",), "PBT": ("Profit before tax",),
               "PAT": ("Net Profit",)}.get(m)  # fmt: skip
        return (_row(t, qe, *lab), "/".join(lab)) if lab else (None, "")
    if m == "PAT":
        return _row(t, qe, "Net Profit"), "Net Profit"
    if template == "bank":
        if m == "NII":
            rev, intr = _row(t, qe, "Revenue"), _row(t, qe, "Interest")
            return (rev - intr if rev is not None and intr is not None else None), "Revenue − Interest"
        if m == "PPOP":  # PPOP − provisions = PBT
            return _row(t, qe, "Profit before tax"), "Profit before tax (= PPOP − provisions)"
    if template == "nbfc":
        if m == "NII":  # NII isn't a screener row; check its finance-cost input
            return _row(t, qe, "Interest"), "Interest (= finance costs)"
        if m == "PPOP":
            return _row(t, qe, "Profit before tax"), "Profit before tax (PPOP input)"
    return None, ""


def _ours(template: str, m: str, fig: Figure, q: QuarterFacts) -> tuple[float | None, Figure | None]:
    """Our value comparable with _screener_value (for some bank/NBFC lines, a component of the metric)."""
    if template == "bank" and m == "PPOP":
        prov = q.get("provisions")
        return (fig.value - prov.value_cr, fig) if prov else (None, None)
    if template == "nbfc" and m == "NII":
        fc = q.get("finance_costs")
        return (fc.value_cr, fig) if fc else (None, None)
    if template == "nbfc" and m == "PPOP":
        pbt = metric("PBT", q)
        return (pbt.value, pbt) if pbt else (None, None)
    return fig.value, fig


@dataclass
class CheckResult:
    verification: str  # cross_checked | pending | mismatch
    note: str | None
    lines: list[ResultsLine]


def _mark(fig: Figure, status: str, note: str) -> Figure:
    return fig.model_copy(update={"status": status, "check_note": note})


def crosscheck(
    template: str,
    lines: list[ResultsLine],
    quarters: dict[str, QuarterFacts | None],
    table: QuarterTable | None,
) -> CheckResult:
    """quarters: {"current": q, "previous": q|None, "year_ago": q|None}."""
    problems: list[str] = []
    pending = table is None or not table.has(quarters["current"].quarter_end)
    all_q = [q for q in quarters.values() if q]
    out: list[ResultsLine] = []
    for line in lines:
        upd: dict = {}
        line_state = "not_checked" if table is None else ("not_in_screener" if pending else "match")
        for slot in ("current", "previous", "year_ago"):
            fig: Figure | None = getattr(line, slot)
            q = quarters.get(slot)
            if fig is None or q is None or table is None or fig.unit != "INR_CR":
                continue
            theirs, rows = _screener_value(template, line.metric, table, q.quarter_end)
            ours, tol_fig = _ours(template, line.metric, fig, q)
            if theirs is None or ours is None:
                continue
            tol = tolerance_cr(tol_fig, all_q) + (0.5 if "−" in rows else 0.0)
            ok = approx_equal(ours, theirs, abs_tol=tol, rel_tol=0.001)
            if not ok and line.metric == "PAT":  # screener may show the owners' share
                own = q.get("pat_owners")
                ok = own is not None and approx_equal(own.value_cr, theirs, abs_tol=tol, rel_tol=0.001)
            note = f"screener {rows} {q.quarter_end:%b %Y}: {theirs:,.0f} (ours {ours:,.2f}, tolerance {tol:.1f})"
            upd[slot] = _mark(fig, "verified" if ok else "unverified", note)
            if not ok:
                problems.append(f"{line.metric} {q.quarter_end:%b %Y}: {note}")
                if slot == "current":
                    line_state = "mismatch"
        new = line.model_copy(update={**upd, "check": line_state})
        out.append(new)
    out = propagate(out)
    problems += sanity(template, quarters["current"])
    if problems:
        return CheckResult("mismatch", "; ".join(problems)[:900], out)
    if pending:
        return CheckResult("pending", "screener has not published this quarter yet; re-checked each run", out)
    return CheckResult("cross_checked", None, out)


def propagate(lines: list[ResultsLine]) -> list[ResultsLine]:
    """A figure checked against screener keeps its result; any computed figure (margin, QoQ, YoY) is verified
    only when every input it rests on is, so a margin is ✓ only if both EBITDA and revenue are."""
    checked = {
        (f.label, f.period.end): f
        for ln in lines
        for f in (ln.current, ln.previous, ln.year_ago)
        if f and f.period and (f.check_note or "").startswith("screener")
    }

    def resolve(fig: Figure | None) -> Figure | None:
        if fig is None:
            return None
        hit = checked.get((fig.label, fig.period.end)) if fig.period else None
        if hit is not None:
            return hit
        if not fig.inputs:
            return fig
        ins = [resolve(i) for i in fig.inputs]
        ok = all(i.status == "verified" for i in ins)
        return fig.model_copy(update={"inputs": ins, "status": "verified" if ok else "unverified"})

    return [
        ln.model_copy(update={k: resolve(getattr(ln, k)) for k in ("current", "previous", "year_ago", "qoq", "yoy")})
        for ln in lines
    ]


def sanity(template: str, q: QuarterFacts) -> list[str]:
    """Hard failures only; each one makes the card 'Couldn't verify'."""
    out: list[str] = []
    if template == "standard":
        rev = q.get("revenue")
        if rev is None or rev.value_cr <= 0:
            out.append("revenue missing or ≤ 0")
        m = metric("EBITDA margin", q)
        if m is not None and not -50 <= m.value <= 80:
            out.append(f"EBITDA margin {m.value:.1f}% outside −50…80%")
        exp, oi, pre = q.get("expenses"), q.get("other_income"), q.get("pbt_pre_exceptional")
        if rev and exp and oi and pre:
            implied = rev.value_cr + oi.value_cr - exp.value_cr
            tol = rev.half_unit_cr + exp.half_unit_cr + oi.half_unit_cr + pre.half_unit_cr + 0.01
            if not approx_equal(implied, pre.value_cr, abs_tol=tol, rel_tol=0.002):
                out.append(f"revenue + other income − expenses = {implied:,.2f} ≠ PBT before exceptional "
                           f"{pre.value_cr:,.2f}")  # fmt: skip
    if q.get("pat") is None:
        out.append("PAT missing")
    return out
