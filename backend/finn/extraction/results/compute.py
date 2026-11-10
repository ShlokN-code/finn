"""Results lines from three quarters of sourced facts. All arithmetic is here (rule 1: code calculates).

Inputs are per-quarter facts in ₹ (XBRL) or ₹ crore (PDF), already tagged with a Citation. Outputs are
`ResultsLine`s whose current/previous/year-ago values are sourced Figures and whose QoQ/YoY are computed
Figures listing their inputs.

EBITDA (standard template) = profit before exceptional items and tax + finance costs + D&A − other income.
That is *operating* EBITDA: other income (treasury yield, dividends) and one-off exceptional items are
excluded, so it equals screener's "Operating Profit" (Sales − Expenses) and can be cross-checked.
Banks report no EBITDA: NII = interest earned − interest expended; PPOP as reported; PAT.
NBFCs: NII = interest income − finance costs; PPOP = PBT + impairment on financial instruments; PAT.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from finn.calendar import quarter_period
from finn.models import Citation, Figure, ResultsLine
from finn.numbers import pct_change

EBITDA_NOTE = (
    "EBITDA = profit before exceptional items and tax + finance costs + depreciation & amortisation − other "
    "income. Excludes other income and exceptional items (operating EBITDA, comparable with screener's "
    "'Operating Profit')."
)

# XBRL element candidates per input, first match wins (SEBI in-capmkt taxonomy; bank and NBFC formats differ).
ELEMENTS: dict[str, tuple[str, ...]] = {
    "revenue": ("RevenueFromOperations",),
    "other_income": ("OtherIncome",),
    "finance_costs": ("FinanceCosts",),
    "dna": ("DepreciationDepletionAndAmortisationExpense", "DepreciationAndAmortisationExpense"),
    "pbt": ("ProfitBeforeTax", "ProfitLossFromOrdinaryActivitiesBeforeTax"),
    "pbt_pre_exceptional": ("ProfitBeforeExceptionalItemsAndTax",),
    "exceptional": ("ExceptionalItemsBeforeTax", "ExceptionalItems"),
    "pat": ("ProfitLossForPeriod", "ProfitLossForThePeriod", "NetProfitLossForThePeriod"),
    "pat_owners": ("ProfitOrLossAttributableToOwnersOfParent", "ProfitLossAttributableToOwnersOfParent"),
    "expenses": ("Expenses",),
    # banks
    "interest_earned": ("InterestEarned",),
    "interest_expended": ("InterestExpended",),
    "ppop": ("OperatingProfitBeforeProvisionAndContingencies",),
    "provisions": ("ProvisionsOtherThanTaxAndContingencies",),
    # NBFCs (Ind AS Division III)
    "interest_income": ("InterestIncome",),
    "impairment": ("ImpairmentOnFinancialInstruments",),
}

LABELS = {
    "revenue": "Revenue from operations", "other_income": "Other income", "finance_costs": "Finance costs",
    "dna": "Depreciation & amortisation", "pbt": "Profit before tax", "exceptional": "Exceptional items",
    "pbt_pre_exceptional": "Profit before exceptional items and tax", "pat": "Profit for the period",
    "pat_owners": "Profit attributable to owners", "interest_earned": "Interest earned",
    "interest_expended": "Interest expended", "ppop": "Operating profit before provisions",
    "provisions": "Provisions and contingencies", "interest_income": "Interest income",
    "impairment": "Impairment on financial instruments", "expenses": "Total expenses",
}  # fmt: skip


@dataclass
class Fact:
    value_cr: float
    citation: Citation
    raw: str
    raw_unit: str
    half_unit_cr: float = 0.005  # rounding half-unit of the source, ₹ Cr (XBRL decimals=-7 → 0.5 Cr)


@dataclass
class QuarterFacts:
    """One quarter, one basis, from one source document."""

    quarter_end: date
    basis: str
    facts: dict[str, Fact] = field(default_factory=dict)  # keyed by input name (ELEMENTS keys)

    def get(self, key: str) -> Fact | None:
        return self.facts.get(key)


def facts_from_xbrl(row: dict, quarter_end: date) -> QuarterFacts:
    """A stored results_filings row → QuarterFacts for the quarter ending `quarter_end`."""
    from finn.extraction.results.xbrl import quarter_value

    facts = row["facts"]["facts"]
    out = QuarterFacts(quarter_end, row["basis"])
    retrieved = row.get("fetched_at") or datetime.now().astimezone()
    for key, names in ELEMENTS.items():
        for name in names:
            hit = quarter_value(facts, name, quarter_end)
            if hit is None:
                continue
            value_inr, f = hit
            dec = f.get("decimals")
            half = 0.5 * 10 ** (-int(dec)) / 1e7 if dec not in (None, "INF") else 0.0
            out.facts[key] = Fact(
                value_cr=value_inr / 1e7,
                citation=Citation(
                    source_type="xbrl",
                    url=row["xbrl_url"],
                    title=f"XBRL results {quarter_period(quarter_end).label} ({row['basis']})",
                    exchange="NSE",
                    locator=f"in-capmkt:{name}@{f.get('ctx')}",
                    published_at=row.get("broadcast_at"),
                    retrieved_at=retrieved,
                ),
                raw=f"{value_inr:.0f}",
                raw_unit="rupees",
                half_unit_cr=half,
            )
            break
    return out


def template_for(q: QuarterFacts, industry: str | None = None) -> str:
    if q.get("interest_earned"):
        return "bank"
    ind = (industry or "").lower()
    if q.get("impairment") or q.get("interest_income") and any(w in ind for w in ("finance", "nbfc", "financial")):
        return "nbfc"
    return "standard"


# --- figures --------------------------------------------------------------------------------------------


def _sourced(label: str, q: QuarterFacts, key: str) -> Figure | None:
    f = q.get(key)
    if f is None:
        return None
    return Figure(
        label=label, value=f.value_cr, unit="INR_CR", period=quarter_period(q.quarter_end), basis=q.basis,
        status="unverified", citation=f.citation, raw=f.raw, raw_unit=f.raw_unit,
    )  # fmt: skip


def _computed(label: str, value: float, unit: str, q: QuarterFacts, formula: str, inputs: list[Figure]) -> Figure:
    return Figure(
        label=label, value=value, unit=unit, period=quarter_period(q.quarter_end), basis=q.basis,
        status="unverified", formula=formula, inputs=inputs,
    )  # fmt: skip


def _inputs(q: QuarterFacts, keys: list[str]) -> list[Figure] | None:
    figs = [_sourced(LABELS[k], q, k) for k in keys]
    return None if any(f is None for f in figs) else figs  # type: ignore[return-value]


def metric(name: str, q: QuarterFacts | None) -> Figure | None:
    """One metric for one quarter, or None when an input is missing (never guessed)."""
    if q is None:
        return None
    if name == "Revenue":
        return _sourced("Revenue", q, "revenue")
    if name == "PBT":
        return _sourced("PBT", q, "pbt")
    if name == "PAT":
        return _sourced("PAT", q, "pat")
    if name == "PPOP" and q.get("ppop"):
        return _sourced("PPOP", q, "ppop")
    if name == "EBITDA":
        if q.get("pbt_pre_exceptional"):
            ins = _inputs(q, ["pbt_pre_exceptional", "finance_costs", "dna", "other_income"])
            if ins:
                v = ins[0].value + ins[1].value + ins[2].value - ins[3].value
                return _computed("EBITDA", v, "INR_CR", q, "PBT before exceptional items + finance costs + D&A "
                                 "− other income", ins)  # fmt: skip
        ins = _inputs(q, ["pbt", "finance_costs", "dna", "other_income"])
        if not ins:
            return None
        exc = _sourced(LABELS["exceptional"], q, "exceptional")
        v = ins[0].value + ins[1].value + ins[2].value - ins[3].value - (exc.value if exc else 0.0)
        formula = "PBT − exceptional items + finance costs + D&A − other income"
        return _computed("EBITDA", v, "INR_CR", q, formula, ins + ([exc] if exc else []))
    if name == "EBITDA margin":
        e, r = metric("EBITDA", q), metric("Revenue", q)
        if not e or not r or r.value <= 0:
            return None
        return _computed("EBITDA margin", e.value / r.value * 100, "PCT", q, "EBITDA ÷ revenue × 100", [e, r])
    if name == "NII":
        if q.get("interest_earned"):
            ins = _inputs(q, ["interest_earned", "interest_expended"])
            formula = "Interest earned − interest expended"
        else:
            ins = _inputs(q, ["interest_income", "finance_costs"])
            formula = "Interest income − finance costs"
        if not ins:
            return None
        return _computed("NII", ins[0].value - ins[1].value, "INR_CR", q, formula, ins)
    if name == "PPOP":  # NBFC: not reported as a line
        ins = _inputs(q, ["pbt", "impairment"])
        if not ins:
            return None
        return _computed("PPOP", ins[0].value + ins[1].value, "INR_CR", q,
                         "PBT + impairment on financial instruments", ins)  # fmt: skip
    raise ValueError(f"unknown metric {name}")


METRICS = {
    "standard": ["Revenue", "EBITDA", "EBITDA margin", "PBT", "PAT"],
    "bank": ["NII", "PPOP", "PAT"],
    "nbfc": ["NII", "PPOP", "PAT"],
}


def _change(label: str, cur: Figure, base: Figure | None, q: QuarterFacts) -> Figure | None:
    if base is None:
        return None
    if cur.unit == "PCT":  # margins: change in basis points
        return _computed(label, (cur.value - base.value) * 100, "BPS", q, "(current − base) × 100 bps", [cur, base])
    v = pct_change(cur.value, base.value)
    if v is None:  # base ≤ 0: not meaningful ("n/m", "turned profitable")
        return Figure(label=label, value=None, unit="PCT", period=quarter_period(q.quarter_end), basis=q.basis,
                      status="not_found", check_note="n/m: base quarter ≤ 0")  # fmt: skip
    return _computed(label, v, "PCT", q, "(current − base) ÷ base × 100", [cur, base])


def build_lines(template: str, cur: QuarterFacts, prev: QuarterFacts | None, ya: QuarterFacts | None):
    lines: list[ResultsLine] = []
    for m in METRICS[template]:
        c = metric(m, cur)
        if c is None:
            continue
        p, y = metric(m, prev), metric(m, ya)
        lines.append(
            ResultsLine(
                metric=m,
                current=c,
                previous=p,
                year_ago=y,
                qoq=_change(f"{m} QoQ", c, p, cur),
                yoy=_change(f"{m} YoY", c, y, cur),
                check="not_checked",
            )  # fmt: skip
        )
    return lines


def tolerance_cr(fig: Figure, facts: list[QuarterFacts]) -> float:
    """Rounding tolerance for comparing `fig` with screener (whole ₹ Cr): the source's half-units summed over
    every sourced input, plus screener's own 0.5 Cr."""
    halves = {f.citation.url + (f.citation.locator or ""): f.half_unit_cr for q in facts for f in q.facts.values()}

    def walk(x: Figure) -> float:
        if x.inputs:
            return sum(walk(i) for i in x.inputs)
        key = (x.citation.url + (x.citation.locator or "")) if x.citation else ""
        return halves.get(key, 0.005)

    return walk(fig) + 0.5
