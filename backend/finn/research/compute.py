"""Step 4 — compute: trajectory, cash quality and balance sheet from screener's standardised tables, in code.

Every value is a `Figure`: read straight from a screener row (citation locator 'screener:<section>/<row>/<period>',
status verified — the value is what the cited table prints), or computed here with its formula and inputs.
Lenders (banks/NBFCs) get NII, PAT, ROE, ROA and asset quality instead of EBITDA, ROCE and cash conversion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from finn.models import Citation, Figure, Period, Series
from finn.numbers import approx_equal, parse_indian_number
from finn.sources.screener import Column, Table

YEARS = 10  # trajectory length
SECTION_TITLE = {
    "quarters": "screener.in quarterly results",
    "profit-loss": "screener.in profit & loss",
    "balance-sheet": "screener.in balance sheet",
    "cash-flow": "screener.in cash flows",
    "ratios": "screener.in ratios",
    "top-ratios": "screener.in key ratios",
}


@dataclass
class Computed:
    template: str
    headline: list[Figure] = field(default_factory=list)
    trajectory: list[Series] = field(default_factory=list)
    growth: list[Figure] = field(default_factory=list)
    cash: list[Series] = field(default_factory=list)
    cash_latest: list[Figure] = field(default_factory=list)
    cash_applicable: bool = True
    balance: list[Series] = field(default_factory=list)
    balance_latest: list[Figure] = field(default_factory=list)
    facts: dict[str, Figure] = field(default_factory=dict)  # fact id → figure (for the ledger / REDUCE)


# --- periods and figures -----------------------------------------------------------------------------------


def year_label(end: date) -> str:
    """Indian FY label for March year-ends (FY26 = Apr 2025–Mar 2026); other year-ends by their end month."""
    return f"FY{end.year % 100:02d}" if end.month == 3 else end.strftime("%b %Y")


def year_start(end: date) -> date:
    return date(end.year, 1, 1) if end.month == 12 else date(end.year - 1, end.month + 1, 1)


def period_for(col: Column, ttm_end: date | None = None) -> Period:
    if col.kind == "ttm":
        end = ttm_end or date.today()
        return Period(kind="ttm", start=end - timedelta(days=364), end=end, label="TTM")
    end = col.end
    assert end is not None
    if col.kind == "interim":
        return Period(kind="instant", start=None, end=end, label=end.strftime("%d %b %Y").lstrip("0"))
    if col.kind == "quarter":
        from finn.calendar import quarter_period

        return quarter_period(end)
    return Period(kind="year", start=year_start(end), end=end, label=year_label(end))


def _cite(t: Table, row: str, col: Column) -> Citation:
    return Citation(
        source_type="screener_table",
        url=t.url,
        title=SECTION_TITLE.get(t.section, "screener.in"),
        locator=f"screener:{t.section}/{row}/{col.label}",
        retrieved_at=t.fetched_at,
    )


def sourced(t: Table | None, row: str, col: Column, label: str | None = None, unit: str = "INR_CR",
            ttm_end: date | None = None) -> Figure | None:  # fmt: skip
    if t is None or row not in t.rows or col not in t.columns:
        return None
    v = t.get(row, col)
    if v is None:
        return None
    return Figure(label=label or row, value=v, unit=unit, period=period_for(col, ttm_end), basis=t.basis,
                  status="verified", citation=_cite(t, row, col), raw=t.raw_value(row, col),
                  raw_unit="crore" if unit == "INR_CR" else None)  # fmt: skip


def computed(label: str, value: float, unit: str, inputs: list[Figure], formula: str,
             period: Period | None = None, check_note: str | None = None, ok: bool = True) -> Figure:  # fmt: skip
    status = "verified" if ok and all(i.status == "verified" for i in inputs) else "unverified"
    return Figure(label=label, value=value, unit=unit, period=period or inputs[-1].period, basis=inputs[-1].basis,
                  status=status, formula=formula, inputs=inputs, check_note=check_note)  # fmt: skip


def _series(metric: str, unit: str, pts: list[Figure], basis: str | None) -> Series | None:
    pts = [p for p in pts if p is not None]
    return Series(metric=metric, unit=unit, basis=basis, points=pts) if len(pts) >= 2 else None  # type: ignore[arg-type]


def row_series(t: Table | None, row: str, metric: str | None = None, unit: str = "INR_CR",
               n: int = YEARS) -> Series | None:  # fmt: skip
    if t is None or row not in t.rows:
        return None
    pts = [sourced(t, row, c, metric or row, unit) for c in t.years()[-n:]]
    return _series(metric or row, unit, pts, t.basis)  # type: ignore[arg-type]


def _first(t: Table | None, *rows: str) -> str | None:
    return next((r for r in rows if t is not None and r in t.rows), None)


# --- growth ------------------------------------------------------------------------------------------------


def cagr(start: Figure, end: Figure, label: str) -> Figure | None:
    """Compound annual growth between two year-end figures; None on a base ≤ 0 or irregular spacing."""
    if start.value is None or end.value is None or start.value <= 0 or end.value <= 0:
        return None
    assert start.period and end.period
    days = (end.period.end - start.period.end).days
    n = round(days / 365.25)
    if n < 1 or abs(days - n * 365.25) > 20:  # a 15-month transition year breaks the series
        return None
    v = ((end.value / start.value) ** (1 / n) - 1) * 100
    per = Period(kind="year", start=start.period.end + timedelta(days=1), end=end.period.end,
                 label=f"{n}y to {end.period.label}")  # fmt: skip
    return computed(label, v, "PCT", [start, end], f"({end.label} ÷ {start.label})^(1/{n}) − 1", per)


def cagrs(s: Series | None, name: str, spans=(3, 5, 10)) -> list[Figure]:
    if s is None:
        return []
    out = []
    for n in spans:
        if len(s.points) > n:
            f = cagr(s.points[-1 - n], s.points[-1], f"{name} CAGR {n}y")
            if f:
                out.append(f)
    return out


# --- main ----------------------------------------------------------------------------------------------------


def compute(d) -> Computed:
    """`d` is a finn.research.discover.Discovery with status 'ok'."""
    c = Computed(template=d.template)
    if d.template == "standard":
        _standard(d, c)
    else:
        _lender(d, c)
    _headline(d, c)
    return c


def _standard(d, c: Computed) -> None:
    pl, bs, cf, ra = (d.table(s) for s in ("profit-loss", "balance-sheet", "cash-flow", "ratios"))
    sales_row = _first(pl, "Sales", "Revenue") or "Sales"
    revenue = row_series(pl, sales_row, "Revenue")
    opm = row_series(pl, "OPM %", "Operating margin (OPM)", "PCT")
    pat = row_series(pl, "Net Profit", "PAT")
    roce = row_series(ra, "ROCE %", "ROCE", "PCT")
    c.trajectory = [s for s in (revenue, opm, pat, roce) if s]
    c.growth = cagrs(revenue, "Revenue") + cagrs(pat, "PAT")

    # Cash quality: CFO, CFO/PAT, FCF = CFO + fixed assets purchased (+ sold), cross-checked against screener's
    # own Free Cash Flow row.
    cfo_pts, ratio_pts, fcf_pts, capex_pts = [], [], [], []
    for col in cf.years()[-YEARS:] if cf else []:
        cfo = sourced(cf, "Cash from Operating Activity", col, "CFO")
        p = sourced(pl, "Net Profit", next((x for x in pl.columns if x.label == col.label), col), "PAT") if pl else None
        if cfo:
            cfo_pts.append(cfo)
        if cfo and p and p.value and p.value > 0:
            ratio_pts.append(computed("CFO/PAT", cfo.value / p.value, "X", [cfo, p], "CFO ÷ PAT"))  # type: ignore[operator]
        fcf = _fcf(d, cf, col, cfo)
        if fcf:
            fcf_pts.append(fcf)
            purchased = fcf.inputs[1]
            capex_pts.append(computed("Capex", -purchased.value, "INR_CR", [purchased],  # type: ignore[operator]
                                      "− fixed assets purchased (cash spent on fixed assets)"))  # fmt: skip
    cfo_s, ratio_s = _series("CFO", "INR_CR", cfo_pts, d.basis), _series("CFO/PAT", "X", ratio_pts, d.basis)
    fcf_s, capex_s = (
        _series("Free cash flow", "INR_CR", fcf_pts, d.basis),
        _series("Capex", "INR_CR", capex_pts, d.basis),
    )
    c.cash = [s for s in (cfo_s, ratio_s, fcf_s, capex_s) if s]
    if len(cfo_pts) >= 5 and len(ratio_pts) >= 5:  # 5-year cash conversion: ΣCFO ÷ ΣPAT
        last5 = ratio_pts[-5:]
        cfo5 = [f.inputs[0] for f in last5]
        pat5 = [f.inputs[1] for f in last5]
        v = sum(f.value for f in cfo5) / sum(f.value for f in pat5)  # type: ignore[misc]
        c.cash_latest.append(computed("CFO/PAT (5y)", v, "X", cfo5 + pat5, "ΣCFO ÷ ΣPAT over 5 years",
                                      Period(kind="year", start=cfo5[0].period.start, end=cfo5[-1].period.end,
                                             label=f"5y to {cfo5[-1].period.label}")))  # fmt: skip
    if fcf_pts:
        c.cash_latest.append(fcf_pts[-1])

    # Balance sheet: borrowings, D/E (computed), working-capital days and cash conversion cycle (screener rows).
    borrow_row = _first(bs, "Borrowings", "Borrowing")
    de_pts = []
    for col in bs.years()[-YEARS:] if bs else []:
        b = sourced(bs, borrow_row, col, "Borrowings") if borrow_row else None
        eq = sourced(bs, "Equity Capital", col)
        res = sourced(bs, "Reserves", col)
        if b and eq and res and (eq.value + res.value) > 0:  # type: ignore[operator]
            de_pts.append(computed("Debt/Equity", b.value / (eq.value + res.value), "X", [b, eq, res],  # type: ignore[operator]
                                   "Borrowings ÷ (Equity Capital + Reserves)"))  # fmt: skip
    c.balance = [s for s in (
        row_series(bs, borrow_row, "Borrowings") if borrow_row else None,
        _series("Debt/Equity", "X", de_pts, d.basis),
        row_series(ra, "Working Capital Days", "Working capital days", "DAYS"),
        row_series(ra, "Cash Conversion Cycle", "Cash conversion cycle", "DAYS"),
        row_series(ra, "Debtor Days", "Debtor days", "DAYS"),
        row_series(ra, "Inventory Days", "Inventory days", "DAYS"),
    ) if s]  # fmt: skip
    c.balance_latest = [s.points[-1] for s in c.balance if s.metric in ("Debt/Equity", "Working capital days")]
    for s in c.trajectory + c.cash + c.balance:
        _register(c, s)
    for g in c.growth + c.cash_latest:
        c.facts[_fact_id(g)] = g


def _fcf(d, cf: Table, col: Column, cfo: Figure | None) -> Figure | None:
    if cfo is None or not d.capex or col.label not in d.capex:
        return None
    try:
        capex_v = parse_indian_number(d.capex[col.label])
        sold_v = parse_indian_number(d.fixed_assets_sold[col.label]) if d.fixed_assets_sold and \
            d.fixed_assets_sold.get(col.label) else 0.0  # fmt: skip
    except ValueError:
        return None
    sched = Citation(source_type="screener_table", url=cf.url, title="screener.in cash flows (investing schedule)",
                     locator=f"screener:cash-flow/Cash from Investing Activity/Fixed assets purchased/{col.label}",
                     retrieved_at=cf.fetched_at)  # fmt: skip
    capex = Figure(label="Fixed assets purchased", value=capex_v, unit="INR_CR", period=cfo.period, basis=cf.basis,
                   status="verified", citation=sched, raw=d.capex[col.label], raw_unit="crore")  # fmt: skip
    inputs, formula, v = [cfo, capex], "CFO + fixed assets purchased", cfo.value + capex_v  # type: ignore[operator]
    if sold_v:  # screener's own Free Cash Flow = CFO + fixed assets purchased + fixed assets sold
        sold = Figure(label="Fixed assets sold", value=sold_v, unit="INR_CR", period=cfo.period, basis=cf.basis,
                      status="verified", raw=d.fixed_assets_sold[col.label], raw_unit="crore",
                      citation=sched.model_copy(update={"locator": sched.locator.replace(
                          "Fixed assets purchased", "Fixed assets sold")}))  # fmt: skip
        inputs, formula, v = [cfo, capex, sold], "CFO + fixed assets purchased + fixed assets sold", v + sold_v
    screener_fcf = cf.get("Free Cash Flow", col) if "Free Cash Flow" in cf.rows else None
    note, ok = None, True
    if screener_fcf is not None:
        # screener rounds each row to whole crore, so a sum of 2–3 rows may differ by up to ~2
        if approx_equal(v, screener_fcf, abs_tol=2.0, rel_tol=0.0):
            note = f"screener Free Cash Flow: {cf.raw_value('Free Cash Flow', col)} ✓"
        else:
            note, ok = f"screener Free Cash Flow prints {cf.raw_value('Free Cash Flow', col)}", False
    return computed("Free cash flow", v, "INR_CR", inputs, formula, check_note=note, ok=ok)


def _lender(d, c: Computed) -> None:
    c.cash_applicable = False
    pl, bs, q, ra = (d.table(s) for s in ("profit-loss", "balance-sheet", "quarters", "ratios"))
    revenue = row_series(pl, "Revenue", "Revenue (interest earned + income)")
    pat = row_series(pl, "Net Profit", "PAT")
    nii_pts = []
    for col in pl.years()[-YEARS:] if pl else []:
        rev, intr = sourced(pl, "Revenue", col), sourced(pl, "Interest", col)
        if rev and intr:
            nii_pts.append(computed("NII", rev.value - intr.value, "INR_CR", [rev, intr],  # type: ignore[operator]
                                    "Revenue − Interest (screener definition)"))  # fmt: skip
    nii = _series("NII", "INR_CR", nii_pts, d.basis)
    roe = row_series(ra, "ROE %", "ROE", "PCT")
    c.trajectory = [s for s in (nii, pat, roe, revenue) if s]
    c.growth = cagrs(nii, "NII") + cagrs(pat, "PAT")
    gnpa = _series("Gross NPA", "PCT", [sourced(q, "Gross NPA %", col, "Gross NPA", "PCT") for col in
                                         (q.columns if q else [])], d.basis)  # type: ignore[arg-type]  # fmt: skip
    nnpa = _series("Net NPA", "PCT", [sourced(q, "Net NPA %", col, "Net NPA", "PCT") for col in
                                       (q.columns if q else [])], d.basis)  # type: ignore[arg-type]  # fmt: skip
    if gnpa:
        c.trajectory.append(gnpa)
    if nnpa:
        c.trajectory.append(nnpa)
    borrow_row = _first(bs, "Borrowing", "Borrowings")
    eq_pts, roa_pts = [], []
    years = bs.years()[-YEARS - 1 :] if bs else []
    for i, col in enumerate(years):
        eq, res = sourced(bs, "Equity Capital", col), sourced(bs, "Reserves", col)
        if eq and res:
            eq_pts.append(computed("Net worth", eq.value + res.value, "INR_CR", [eq, res],  # type: ignore[operator]
                                   "Equity Capital + Reserves"))  # fmt: skip
        if i > 0 and pl:
            ta0, ta1 = sourced(bs, "Total Assets", years[i - 1]), sourced(bs, "Total Assets", col)
            plcol = next((x for x in pl.columns if x.label == col.label), None)
            np_ = sourced(pl, "Net Profit", plcol, "PAT") if plcol else None
            if ta0 and ta1 and np_ and (ta0.value + ta1.value) > 0:  # type: ignore[operator]
                roa_pts.append(computed("ROA", np_.value / ((ta0.value + ta1.value) / 2) * 100, "PCT",  # type: ignore[operator]
                                        [np_, ta0, ta1], "PAT ÷ average total assets × 100"))  # fmt: skip
    c.balance = [s for s in (
        row_series(bs, "Deposits", "Deposits") if bs and "Deposits" in bs.rows else None,
        row_series(bs, borrow_row, "Borrowings") if borrow_row else None,
        _series("Net worth", "INR_CR", eq_pts[-YEARS:], d.basis),
        _series("ROA", "PCT", roa_pts, d.basis),
    ) if s]  # fmt: skip
    c.balance_latest = [s.points[-1] for s in c.balance if s.metric in ("ROA", "Net worth")]
    for s in c.trajectory + c.balance:
        _register(c, s)
    for g in c.growth:
        c.facts[_fact_id(g)] = g


def _headline(d, c: Computed) -> None:
    tr = d.top_ratios or {}
    mc = tr.get("Market Cap")
    if mc:
        try:
            v = parse_indian_number(mc.replace("₹", "").replace("Cr.", "").strip())
            asof = d.fetched_at if isinstance(d.fetched_at, datetime) else None
            c.headline.append(Figure(
                label="Market cap", value=v, unit="INR_CR", status="verified", raw=mc, raw_unit="crore",
                period=Period(kind="instant", end=(asof or datetime.now()).date(), label="today"),
                citation=Citation(source_type="screener_table", url=d.url, title=SECTION_TITLE["top-ratios"],
                                  locator="screener:top-ratios/Market Cap", retrieved_at=asof or datetime.now()),
            ))  # fmt: skip
        except ValueError:
            pass
    for s in c.trajectory:
        if s.metric in ("Revenue", "PAT", "NII", "ROCE", "ROE", "Operating margin (OPM)"):
            c.headline.append(s.points[-1])
    five = [g for g in c.growth if g.label in ("Revenue CAGR 5y", "NII CAGR 5y", "PAT CAGR 5y")]
    c.headline.extend(five)
    for h in c.headline:
        c.facts.setdefault(_fact_id(h), h)


def _fact_id(f: Figure) -> str:
    per = f.period.label if f.period else ""
    return f"S:{f.label}:{per}".replace(" ", "_")


def _register(c: Computed, s: Series) -> None:
    for p in s.points:
        c.facts.setdefault(_fact_id(p), p)
