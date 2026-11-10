"""Metric vocabulary for the Promise Ledger: keys the model chooses from, which direction is good, labels for
drivers, synonyms for the 'quietly dropped' text search, and which screener rows may score a promise.

Direction is decided here (code), never by the model: 'higher' (growth, margins), 'lower' (credit cost, NPAs,
costs), 'neutral' (plans like capex, where delivering more or less than said both differ from the promise).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Metric:
    key: str
    label: str  # driver label shown on cards ('Margins', 'Asset quality', 'Growth', …)
    direction: str  # higher | lower | neutral
    synonyms: tuple[str, ...] = field(default_factory=tuple)


METRICS: dict[str, Metric] = {m.key: m for m in [
    Metric("revenue", "Growth", "higher", ("revenue", "sales", "top line", "topline", "turnover")),
    Metric("revenue_growth", "Growth", "higher", ("revenue growth", "sales growth", "grow", "growth", "top line")),
    Metric("volume_growth", "Volumes", "higher", ("volume", "volumes", "tonnage", "units")),
    Metric("ebitda", "Margins", "higher", ("ebitda", "operating profit")),
    Metric("ebitda_margin", "Margins", "higher", ("ebitda margin", "margin", "margins")),
    Metric("ebit_margin", "Margins", "higher", ("ebit margin", "operating margin", "margin", "margins")),
    Metric("gross_margin", "Margins", "higher", ("gross margin", "contribution margin", "margin")),
    Metric("pat", "Profit", "higher", ("pat", "net profit", "profit after tax", "bottom line", "earnings")),
    Metric("pat_growth", "Profit", "higher", ("profit growth", "pat growth", "earnings growth")),
    Metric("eps", "Profit", "higher", ("eps", "earnings per share")),
    Metric("capex", "Capex", "neutral", ("capex", "capital expenditure", "investment", "invest")),
    Metric("capacity", "Capacity", "higher", ("capacity", "plant", "commission", "commissioning")),
    Metric("order_book", "Order book", "higher", ("order book", "orderbook", "backlog")),
    Metric("order_inflow", "Order book", "higher", ("order inflow", "order intake", "orders", "deal wins", "tcv")),
    Metric("deal_wins", "Deal wins", "higher", ("deal wins", "tcv", "large deals", "deal value")),
    Metric("market_share", "Market share", "higher", ("market share", "share")),
    Metric("debt", "Leverage", "lower", ("debt", "borrowings", "leverage")),
    Metric("net_debt", "Leverage", "lower", ("net debt", "net cash", "debt")),
    Metric("working_capital_days", "Working capital", "lower", ("working capital", "receivable", "inventory days")),
    Metric("cost_savings", "Costs", "higher", ("cost savings", "cost optimisation", "cost optimization", "savings")),
    Metric("opex_growth", "Costs", "lower", ("opex", "operating expenses", "costs")),
    Metric("headcount", "People", "neutral", ("headcount", "employees", "hiring", "freshers")),
    Metric("attrition", "People", "lower", ("attrition", "churn")),
    Metric("utilisation", "Utilisation", "higher", ("utilisation", "utilization")),
    Metric("dividend_payout", "Payout", "higher", ("dividend", "payout", "buyback")),
    Metric("roce", "Returns", "higher", ("roce", "return on capital")),
    Metric("roe", "Returns", "higher", ("roe", "return on equity")),
    Metric("tax_rate", "Tax", "neutral", ("tax rate", "effective tax")),
    # lenders
    Metric("aum_growth", "Growth", "higher", ("aum", "assets under management", "book growth", "loan book")),
    Metric("loan_growth", "Growth", "higher", ("loan growth", "advances", "credit growth", "loan book")),
    Metric("deposit_growth", "Deposits", "higher", ("deposit", "deposits", "casa")),
    Metric("nim", "Margins", "higher", ("nim", "net interest margin", "margin", "margins")),
    Metric("credit_cost", "Asset quality", "lower", ("credit cost", "credit costs", "loan loss", "provisions")),
    Metric("gnpa", "Asset quality", "lower", ("gnpa", "gross npa", "gross stage 3", "stage 3", "asset quality")),
    Metric("nnpa", "Asset quality", "lower", ("nnpa", "net npa", "net stage 3", "stage 3", "asset quality")),
    Metric("cost_to_income", "Costs", "lower", ("cost to income", "cost-to-income", "opex to", "cost income")),
    Metric("roa", "Returns", "higher", ("roa", "return on assets")),
    Metric("customer_growth", "Customers", "higher", ("customer", "customers", "franchise")),
    Metric("other", "Other", "neutral", ()),
]}  # fmt: skip

KEYS = list(METRICS)


def direction(key: str) -> str:
    return METRICS.get(key, METRICS["other"]).direction


def label(key: str) -> str:
    return METRICS.get(key, METRICS["other"]).label


def synonyms(key: str) -> tuple[str, ...]:
    return METRICS.get(key, METRICS["other"]).synonyms


# Screener rows that may score a promise — a whitelist, because names hide different definitions (INFY's
# 'operating margin' is EBIT margin; screener's OPM % is EBITDA margin). (metric_key, measure) → row spec.
# Only INR or unspecified-currency promises, on a scope that matches the screener page, are scored this way.
SCREENER_SCORABLE: dict[tuple[str, str], dict] = {
    ("revenue", "level"): {"section": "profit-loss", "rows": ("Sales", "Revenue"), "unit": "INR_CR"},
    ("revenue_growth", "growth"): {"section": "profit-loss", "rows": ("Sales", "Revenue"), "unit": "PCT", "yoy": True},
    ("revenue", "growth"): {"section": "profit-loss", "rows": ("Sales", "Revenue"), "unit": "PCT", "yoy": True},
    ("pat", "level"): {"section": "profit-loss", "rows": ("Net Profit",), "unit": "INR_CR"},
    ("pat_growth", "growth"): {"section": "profit-loss", "rows": ("Net Profit",), "unit": "PCT", "yoy": True},
    ("pat", "growth"): {"section": "profit-loss", "rows": ("Net Profit",), "unit": "PCT", "yoy": True},
    ("ebitda_margin", "level"): {"section": "profit-loss", "rows": ("OPM %",), "unit": "PCT", "needs_word": "ebitda"},
    ("gnpa", "level"): {"section": "quarters", "rows": ("Gross NPA %",), "unit": "PCT", "quarterly_only": True},
    ("nnpa", "level"): {"section": "quarters", "rows": ("Net NPA %",), "unit": "PCT", "quarterly_only": True},
}
