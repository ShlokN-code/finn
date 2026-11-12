"""Cross-check results lines against screener's quarterly table, plus sanity checks (trust layer §10.3).

Outcomes: every current figure agrees → cross_checked; all comparable ones agree but some line has no
screener counterpart (NBFC interest income, impairment), or only a previous/year-ago figure disagrees → partial
(those QoQ/YoY marked unverified); screener hasn't published the quarter → pending; a current-quarter
disagreement or failed sanity check → mismatch ("Couldn't verify — open filing", no numbers).

Screener derives some rows differently from the statement. A value that doesn't match directly may match
through one documented reconciliation (each uses only sourced facts, and the check note names it):
  PBT    = profit for the period + tax expense (screener's PBT; differs when there are discontinued ops)
  EBITDA + share of associates/JVs (screener counts a JV loss inside operating expenses)
  PAT    = profit attributable to owners
  Revenue − excise duty (screener's Sales is net of excise when the filing itemises it: ITC, RELIANCE)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from finn.extraction.results.compute import LABELS, QuarterFacts, metric, tolerance_cr
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


def _reconciliations(template: str, m: str, fig: Figure, q: QuarterFacts) -> list[tuple[float, float, str]]:
    """(value, extra tolerance, name) alternatives for screener's way of deriving row `m`."""
    out = []
    pat, tax, share, own = q.get("pat"), q.get("tax"), q.get("share_assoc"), q.get("pat_owners")
    exc = q.get("excise")
    if m == "Revenue" and exc and exc.value_cr > 0:
        out.append((fig.value - exc.value_cr, exc.half_unit_cr, "revenue from operations − excise duty"))
    if template != "bank" and m == "PBT" and pat and tax:
        out.append((pat.value_cr + tax.value_cr, pat.half_unit_cr + tax.half_unit_cr, "profit for the period + tax"))
    if m == "EBITDA" and share and abs(share.value_cr) >= 0.005:
        out.append((fig.value + share.value_cr, share.half_unit_cr, "EBITDA + share of associates/JVs"))
    if m == "PAT" and own:
        out.append((own.value_cr, own.half_unit_cr, "profit attributable to owners"))
    return out


def _component(template: str, m: str) -> str | None:
    """For lines screener can only check in part: the label of the input that its row verifies."""
    if template == "nbfc" and m == "NII":
        return LABELS["finance_costs"]
    if template == "nbfc" and m == "PPOP":
        return LABELS["pbt"]
    return None


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
    prior_problems: list[str] = []  # previous / year-ago quarter only: the card stays, those changes are unverified
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
            note = f"screener {rows} {q.quarter_end:%b %Y}: {theirs:,.0f} (ours {ours:,.2f}, tolerance {tol:.1f})"
            if not ok:
                for alt, extra, name in _reconciliations(template, line.metric, fig, q):
                    if approx_equal(alt, theirs, abs_tol=tol + extra, rel_tol=0.001):
                        ok = True
                        note += f"; matches as {name} = {alt:,.2f}"
                        break
            comp = _component(template, line.metric)
            if comp and fig.inputs:
                ins = [_mark(i, "verified" if ok else "unverified", note) if i.label == comp else i
                       for i in fig.inputs]  # fmt: skip
                whole = all(i.status == "verified" for i in ins)
                upd[slot] = fig.model_copy(update={"inputs": ins, "status": "verified" if whole else "unverified",
                                                   "check_note": note})  # fmt: skip
            else:
                upd[slot] = _mark(fig, "verified" if ok else "unverified", note)
            if not ok:
                (problems if slot == "current" else prior_problems).append(
                    f"{line.metric} {q.quarter_end:%b %Y}: {note}"
                )
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
    if prior_problems:
        # Every current-quarter figure agrees; an earlier quarter doesn't (screener restates or derives it
        # differently). The numbers stay, and the QoQ/YoY resting on that quarter are marked unverified.
        return CheckResult("partial", "This quarter's figures match screener; an earlier quarter doesn't, so its "
                           "change is unverified: " + "; ".join(prior_problems)[:700], out)  # fmt: skip
    unchecked = [ln.metric for ln in out if ln.current is not None and ln.current.status != "verified"]
    if unchecked:
        return CheckResult("partial", f"Not checkable against screener (shown from the filing): "
                           f"{', '.join(unchecked)}", out)  # fmt: skip
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
