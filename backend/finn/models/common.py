"""Shared building blocks: provenance (Citation), sourced numbers (Figure), sourced text (Claim)."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class Model(BaseModel):
    # serialization_defaults_required: the API always emits every field, so TS types mark them required.
    model_config = ConfigDict(extra="forbid", use_enum_values=True, json_schema_serialization_defaults_required=True)


class SourceType(StrEnum):
    exchange_filing = "exchange_filing"  # NSE/BSE announcement PDF
    xbrl = "xbrl"  # NSE XBRL / iXBRL instance
    annual_report = "annual_report"
    concall_transcript = "concall_transcript"
    investor_presentation = "investor_presentation"
    screener_table = "screener_table"  # screener.in standardised tables (cross-check only)
    price_feed = "price_feed"  # Yahoo / NSE bhavcopy
    web_profile = "web_profile"  # only for incoming-executive background (spec exception)


class VerificationStatus(StrEnum):
    verified = "verified"  # cross-checked against a second source, or quote found in source text
    unverified = "unverified"  # sourced but not independently confirmed (or cross-check disagreed)
    not_found = "not_found"  # not present in sources — value must be null; UI says "Not found in sources"


class Unit(StrEnum):
    inr_cr = "INR_CR"  # all money internally in ₹ crore
    inr = "INR"  # per-share prices, small amounts
    inr_per_share = "INR_PER_SHARE"
    pct = "PCT"  # 12.3 means 12.3 %
    ratio = "X"  # 1.4x
    days = "DAYS"
    count = "COUNT"
    shares = "SHARES"


Basis = Literal["consolidated", "standalone"]


class Citation(Model):
    """Where a number or claim came from. Every Figure/Claim that is not `not_found` carries one."""

    source_type: SourceType
    url: str = Field(min_length=1, description="Direct link to the document (exchange PDF, XBRL, etc.)")
    title: str | None = Field(None, description="Human title, e.g. 'Q2 FY27 earnings call transcript'")
    exchange: Literal["NSE", "BSE"] | None = None
    page: int | None = Field(None, ge=1, description="1-based PDF page")
    quote: str | None = Field(None, description="Verbatim snippet supporting the value/claim")
    locator: str | None = Field(
        None,
        description="Machine locator when there is no page, e.g. 'in-capmkt:ProfitBeforeTax@OneD' "
        "or 'screener:quarters/Net Profit/Sep 2026'",
    )
    published_at: AwareDatetime | None = Field(None, description="When the source was published (UTC)")
    retrieved_at: AwareDatetime = Field(description="When FINN fetched it (UTC) — drives freshness stamps")


class Period(Model):
    """A reporting period. `label` is Indian-FY style and is computed in code, never by a model."""

    kind: Literal["quarter", "half_year", "nine_months", "year", "ttm", "instant"]
    start: date | None = None  # None for 'instant' (balance-sheet date)
    end: date
    label: str = Field(description="e.g. 'Q2 FY27' (Jul–Sep 2026), 'FY26', 'H1 FY27', '30 Sep 2026'")


class Figure(Model):
    """A number with provenance. Money is float ₹ crore; see DECISIONS.md (float vs Decimal)."""

    label: str = Field(description="e.g. 'Revenue from operations', 'EBITDA margin'")
    value: float | None = Field(description="Null if and only if status == not_found")
    unit: Unit
    period: Period | None = None
    basis: Basis | None = Field(None, description="Consolidated/standalone — always set for financials")
    status: VerificationStatus
    citation: Citation | None = None
    raw: str | None = Field(None, description="Value exactly as printed, e.g. '1,23,456.78'")
    raw_unit: str | None = Field(None, description="Unit as printed, e.g. 'lakh', 'million', 'crore'")
    check_note: str | None = Field(None, description="Cross-check detail, e.g. 'screener: 49,243 (Δ 0.00%)'")
    formula: str | None = Field(None, description="For computed figures: human-readable formula")
    inputs: list[Figure] = Field(default_factory=list, description="For computed figures: the sourced inputs")

    @model_validator(mode="after")
    def _provenance_rules(self) -> Figure:
        if self.status == VerificationStatus.not_found:
            if self.value is not None:
                raise ValueError("not_found figures must have value=None (never guess)")
        else:
            if self.value is None:
                raise ValueError("value is required unless status is not_found")
            if self.citation is None and not self.inputs:
                raise ValueError("a figure needs a citation, or inputs if it is computed")
        if self.formula and not self.inputs:
            raise ValueError("computed figures (with formula) must list their inputs")
        return self


class Claim(Model):
    """A sentence of text with provenance (snapshot lines, red flags, bull/bear bullets, impact reasons)."""

    text: str
    status: VerificationStatus
    citations: list[Citation] = Field(default_factory=list)

    @model_validator(mode="after")
    def _needs_citation(self) -> Claim:
        if self.status != VerificationStatus.not_found and not self.citations:
            raise ValueError("a claim needs at least one citation unless status is not_found")
        return self


class Category(StrEnum):
    """FINN's filing taxonomy (PRODUCT.md §4 'Category treatment')."""

    results = "results"
    mna = "mna"
    management_change = "management_change"
    litigation = "litigation"
    credit_rating = "credit_rating"
    pledging = "pledging"
    capex = "capex"
    press_release = "press_release"
    insider_trading = "insider_trading"
    fund_raise = "fund_raise"
    dividend = "dividend"
    bonus_split = "bonus_split"
    earnings_call = "earnings_call"
    agm_egm = "agm_egm"
    postal_ballot = "postal_ballot"
    investor_meetings = "investor_meetings"
    routine = "routine"  # known-boring compliance filings; always hidden, grouped by Filing.hidden_reason
    unclassified = "unclassified"  # nothing (exchange label, rules, model) could classify it


class Impact(StrEnum):
    """Level-0 relevance: effect on the company's business — not a stock call."""

    positive = "positive"
    negative = "negative"
    mixed = "mixed"
    neutral = "neutral"


Figure.model_rebuild()
