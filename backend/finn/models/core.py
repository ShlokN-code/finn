"""Core FINN contracts: Filing, Event, Card, Alert, Holding, Driver (research contracts: finn/models/research.py).

Pydantic is the source of truth; web/lib/types.ts is generated from these (see scripts/gen_types).
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, field_validator

from finn.models.common import (
    Basis,
    Category,
    Citation,
    Claim,
    Figure,
    Impact,
    Model,
    Period,
)

# ---------------------------------------------------------------------------------------------
# Push side: filings → events → cards / alerts
# ---------------------------------------------------------------------------------------------


class EventStage(StrEnum):
    """Where a filing sits in an event thread (intimation → outcome → deck → call → transcript → ad)."""

    intimation = "intimation"
    outcome = "outcome"
    presentation = "presentation"
    call = "call"  # call schedule / audio recording
    transcript = "transcript"
    newspaper_ad = "newspaper_ad"
    clarification = "clarification"
    other = "other"


class Filing(Model):
    """One exchange announcement, as ingested. NSE and BSE copies of the same document are both kept;
    the later one points at the first via `duplicate_of`."""

    id: str = Field(description="Stable id: '<exchange>:<exchange_id>', e.g. 'NSE:118230211'")
    exchange: Literal["NSE", "BSE"]
    exchange_id: str = Field(description="NSE seq_id / BSE NEWSID")
    symbol: str = Field(description="NSE symbol (canonical key across the app)")
    isin: str | None = None
    bse_code: str | None = None
    filed_at: AwareDatetime = Field(description="Exchange dissemination time (UTC)")
    exchange_category: str = Field(description="Exchange's own label, e.g. 'Change in Management'")
    subject: str = Field(description="Headline / attachment text from the exchange")
    attachment_url: str | None = None
    xbrl_url: str | None = None
    category: Category | None = Field(None, description="FINN category; null until classified")
    category_source: Literal["exchange", "rule", "model"] | None = Field(
        None,
        description="Classification ladder tier: exchange's own label → keyword rules → cheap model. "
        "Null with category 'unclassified' means every tier failed.",
    )
    category_model: str | None = Field(None, description="Model id when category_source == 'model'")
    category_confidence: float | None = Field(None, ge=0, le=1)
    stage: EventStage | None = None
    hidden_reason: str | None = Field(None, description="Set when routine, e.g. 'Trading-window notice'")
    duplicate_of: str | None = Field(None, description="Filing.id of the same document on the other exchange")
    event_id: str | None = None
    fetched_at: AwareDatetime | None = Field(None, description="When FINN fetched it (UTC) — freshness")


class TimelineItem(Model):
    stage: EventStage
    filing_id: str
    at: AwareDatetime
    label: str


class Series(Model):
    metric: str
    unit: str
    basis: Literal["consolidated", "standalone"] | None = None
    points: list[Figure]


class MoveExplanation(Model):
    kind: Literal["filing", "bulk_block_deal", "sector_move", "index_move", "none"]
    text: str = Field(description="e.g. 'Q2 results filed 16:05' or '⚠️ No disclosure explains this move'")
    citation: Citation | None = None


# --- Card-type details (stored on the Event, copied onto the Card) ------------------------------------------


class ResultsLine(Model):
    """One results metric: three sourced quarters plus QoQ/YoY computed in code."""

    metric: str = Field(description="e.g. 'Revenue', 'EBITDA', 'EBITDA margin', 'PAT', 'NII', 'PPOP'")
    current: Figure
    previous: Figure | None = Field(None, description="Previous quarter (same basis)")
    year_ago: Figure | None = Field(None, description="Same quarter last year (same basis)")
    qoq: Figure | None = Field(None, description="% change (bps for margins); null value = not meaningful")
    yoy: Figure | None = None
    check: Literal["match", "mismatch", "not_in_screener", "not_checked"] = Field(
        description="Cross-check of the current value against screener's quarterly table"
    )


class ResultsDetail(Model):
    kind: Literal["results"] = "results"
    template: Literal["standard", "bank", "nbfc"]
    basis: Basis
    quarter: Period
    source_path: Literal["xbrl", "pdf_table", "pdf_model"] = Field(
        description="Where the current quarter came from: XBRL → PDF table → multimodal model on the PDF"
    )
    verification: Literal["cross_checked", "partial", "pending", "mismatch"] = Field(
        description="cross_checked: every line agrees with screener + sanity checks. partial: every comparable "
        "line agrees, but some line has no screener counterpart (named in the note). pending: screener has not "
        "published the quarter yet. mismatch: show 'Couldn't verify — open filing', no numbers."
    )
    verification_note: str | None = None
    filing_url: str | None = Field(None, description="The results filing to open when unverified")
    lines: list[ResultsLine] = Field(default_factory=list)
    margin_series: Series | None = Field(None, description="8-quarter margin sparkline (screener table)")
    ebitda_note: str | None = Field(
        None, description="Methodology note shown on tap: how EBITDA is defined; for banks, the PAT basis"
    )
    trend_pat_yoy_pct: float | None = Field(
        None,
        description="Median PAT YoY % of the 4 prior quarters, YoYs above +100% (low-base effects) left out "
        "(screener, computed in code) — ranking 'surprise'",
    )


class PriorRole(Model):
    company: str
    role: str | None = None
    start_year: int | None = None
    end_year: int | None = Field(None, description="Null = to date / not stated")
    source: Literal["filing", "web"]
    citation: Citation
    period_citation: Citation | None = Field(
        None,
        description="When the filing names the role without dates and a web snippet supplies them (web · unverified)",
    )


class PersonProfile(Model):
    name: str
    role: str = Field(description="Position named in the filing, e.g. 'Chief Financial Officer'")
    change: Literal["appointed", "resigned", "re_designated", "retired", "other"]
    effective: date | None = None
    prior_roles: list[PriorRole] = Field(default_factory=list)
    qualifications: list[Claim] = Field(default_factory=list)
    insider: bool | None = Field(None, description="Decided in code: a prior role at this company/group")
    insider_reason: str | None = None
    tenure_years: Figure | None = Field(None, description="Outgoing person's tenure, computed in code")
    profile: Claim | None = Field(None, description="Verbatim profile paragraph from the filing")
    achievements: list[Claim] = Field(
        default_factory=list, description="Notable achievements from web snippets the filing doesn't state (unverified)"
    )


class ManagementDetail(Model):
    kind: Literal["management_change"] = "management_change"
    people: list[PersonProfile] = Field(default_factory=list)
    web_enrichment: Literal["done", "unavailable", "not_run", "nothing_found"] = Field(
        description="The card is complete from the filing alone; web snippets only add to it"
    )
    web_note: str | None = None


class OneLinerDetail(Model):
    kind: Literal["one_liner"] = "one_liner"
    line: Claim
    key_figure: Figure | None = None
    direction: Literal["up", "down", "new", "unchanged"] | None = Field(
        None, description="Rating upgrade/downgrade, pledge increase/decrease — decided in code"
    )
    facts: dict[str, str] = Field(default_factory=dict, description="Extracted fields as printed")


class ChipDetail(Model):
    kind: Literal["chip"] = "chip"
    text: str = Field(description="e.g. '₹8 dividend · record 21 Nov'")
    ex_date: date | None = None
    record_date: date | None = None
    amount: Figure | None = None
    citation: Citation | None = None


class PriceVolumeDetail(Model):
    kind: Literal["price_volume"] = "price_volume"
    trading_date: date
    move_pct: Figure = Field(description="Adjusted close-to-close move")
    sector_move_pct: Figure | None = None
    sector_index: str | None = None
    relative_move_pct: Figure | None = Field(None, description="Stock minus sector (sector-relative mode)")
    z_score: float | None = None
    volume_ratio: Figure | None = Field(None, description="Volume ÷ 20-session average")
    day_label: str | None = Field(None, description="e.g. 'Ex-dividend today'")
    mechanical_pct: float | None = Field(None, description="Ex-date mechanical move removed before testing")
    triggers: list[Literal["price", "volume"]] = Field(default_factory=list)
    explanations: list[MoveExplanation] = Field(default_factory=list, description="In priority order")


EventDetail = Annotated[
    ResultsDetail | ManagementDetail | OneLinerDetail | ChipDetail | PriceVolumeDetail,
    Field(discriminator="kind"),
]


class Event(Model):
    """Filings about one real-world event, threaded into a single unit (one card in the Brief)."""

    id: str
    key: str = Field(
        description="Threading key, e.g. 'INFY:results:Q2 FY27' or 'HDFCBANK:management_change:2026-11-06'"
    )
    symbol: str
    category: Category
    title: str
    period: Period | None = Field(None, description="For results events")
    started_at: AwareDatetime
    updated_at: AwareDatetime
    timeline: list[TimelineItem] = Field(default_factory=list)
    figures: list[Figure] = Field(default_factory=list, description="Extracted facts, e.g. results line items")
    impact: Impact | None = None
    impact_reason: Claim | None = None
    driver_ids: list[str] = Field(default_factory=list, description="Drivers this event touches")
    so_what: str | None = Field(None, description="≤10 words, written in code or by the Level-0 tagger")
    detail: EventDetail | None = Field(None, description="Card-type specific payload")


class ScoreBreakdown(Model):
    """score = category_weight × position_weight × relevance × novelty × surprise ('Why is this #1?')."""

    category_weight: float
    position_weight: float
    relevance: float
    novelty: float
    surprise: float
    total: float
    notes: list[str] = Field(default_factory=list, description="e.g. 'Touches confirmed driver: Margins'")


class Card(Model):
    """A ranked Brief item. COMPUTED on read from Event + holdings + rules; never stored."""

    id: str = Field(description="Same as event_id (one card per event)")
    event_id: str
    symbol: str
    card_type: Literal["results", "management_change", "price_volume", "what_to_watch", "one_liner", "inline_chip"]
    category: Category
    impact: Impact | None = None
    impact_reason: Claim | None = None
    headline: str
    so_what: str = Field(description="≤10 words")
    key_figures: list[Figure] = Field(default_factory=list)
    rupee_impact: Figure | None = Field(None, description="₹ effect on this holding, when computable")
    sources: list[Citation] = Field(default_factory=list, description="Source chips (first = primary filing)")
    timeline: list[TimelineItem] = Field(default_factory=list)
    next_action: str | None = None
    ask_chips: list[str] = Field(default_factory=list, max_length=3)
    affects_drivers: list[str] = Field(default_factory=list, description="Driver labels for the 👁 tag")
    detail: EventDetail | None = None
    score: ScoreBreakdown
    as_of: AwareDatetime = Field(description="Freshness of the underlying data")

    @field_validator("so_what")
    @classmethod
    def _so_what_short(cls, v: str) -> str:
        if len(v.split()) > 10:
            raise ValueError("so_what must be 10 words or fewer")
        return v


class Alert(Model):
    """A push notification decision (stored server-side to enforce budget, batching, quiet hours, dedup)."""

    id: str
    symbol: str
    trigger: Literal["filing", "price_move", "volume_spike"]
    event_id: str | None = None
    severity: Literal["critical", "normal"]
    title: str
    body: str
    triggered_at: AwareDatetime
    trading_date: date | None = Field(None, description="For price/volume alerts (IST trading day)")
    move_pct: Figure | None = Field(None, description="Adjusted close-to-close move")
    z_score: float | None = None
    volume_ratio: float | None = Field(None, description="Volume ÷ 20-day average")
    explanations: list[MoveExplanation] = Field(default_factory=list, description="In priority order")
    day_label: str | None = Field(None, description="e.g. 'Ex-dividend today'")
    channels: list[Literal["telegram", "webpush"]] = Field(default_factory=list)
    status: Literal["queued", "sent", "batched", "held_quiet_hours", "over_budget", "suppressed", "failed"]
    status_reason: str | None = None


# ---------------------------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------------------------


class Driver(Model):
    """Something the user watches for a holding (Level-1 relevance), suggested from disclosures."""

    id: str = Field(description="Slug, e.g. 'TATAPOWER:renewables-capacity'")
    symbol: str
    label: str = Field(description="Short tag shown on cards, e.g. 'Margins'")
    description: str
    status: Literal["suggested", "confirmed", "dismissed"]
    source: Claim | None = Field(None, description="Why FINN suggested it, with citation")
    promise_ids: list[str] = Field(default_factory=list, description="Related Promise Ledger items")


class Holding(Model):
    """One portfolio position. Lives in the browser (localStorage). Symbols + weights are sent with each /brief
    request and used only to rank it — never stored unless the user turns on Telegram alerts. `quantity` never
    leaves the phone."""

    symbol: str
    quantity: float | None = Field(None, gt=0, description="Shares; used for weight and ₹ impact")
    weight_pct: float | None = Field(None, gt=0, le=100, description="If the user pasted weights instead")
    drivers: list[Driver] = Field(default_factory=list)
    thesis: str | None = Field(None, description="Optional Level-2 thesis line")
    price_alert_pct: float | None = Field(None, gt=0, description="Per-stock override of the ±4% default")
    snoozed_until: AwareDatetime | None = None
    added_at: AwareDatetime


class WeightRule(Model):
    """A visible feedback adjustment (PRODUCT §5). Listed on the Rules screen; Reset deletes it."""

    id: str = Field(
        description="Deterministic from scope, e.g. 'stock:IDEA', 'category:fund_raise', "
        "'stock_category:BAJFINANCE:fund_raise', 'event:<event id>'"
    )
    scope: Literal["stock", "category", "stock_category", "event"]
    symbol: str | None = None
    category: Category | None = None
    event_id: str | None = None
    multiplier: float = Field(gt=0, description="Product of ×0.8 (not useful) and ×1.25 (useful) taps, bounded")
    not_useful_count: int = 0
    useful_count: int = 0
    updated_at: AwareDatetime


class AlertSettings(Model):
    """Notification rules (PRODUCT §6). Defaults are the spec's."""

    price_move_pct: float = Field(4.0, gt=0)
    per_stock_pct: dict[str, float] = Field(default_factory=dict, description="Per-symbol override of ±%")
    volume_multiple: float = Field(2.0, gt=1)
    volatility_aware: bool = True
    sector_relative: bool = True
    push_categories: list[Category] = Field(
        default_factory=lambda: [
            Category.results, Category.mna, Category.management_change, Category.litigation,
            Category.credit_rating, Category.pledging, Category.price_volume,
        ]
    )  # fmt: skip
    daily_budget: int = Field(5, ge=1)
    batching: bool = True
    quiet_start: str = Field("22:00", pattern=r"^\d{2}:\d{2}$", description="IST")
    quiet_end: str = Field("07:00", pattern=r"^\d{2}:\d{2}$", description="IST")


# ---------------------------------------------------------------------------------------------
# Research
# ---------------------------------------------------------------------------------------------


# Promise Ledger and Dossier contracts live in finn/models/research.py.
