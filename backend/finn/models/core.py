"""Core FINN contracts: Filing, Event, Card, Alert, Holding, Driver, Promise, Dossier.

Pydantic is the source of truth; web/lib/types.ts is generated from these (see scripts/gen_types).
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import AwareDatetime, ConfigDict, Field, field_validator

from finn.models.common import (
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
    category_source: Literal["rule", "model"] | None = None
    category_confidence: float | None = Field(None, ge=0, le=1)
    stage: EventStage | None = None
    hidden_reason: str | None = Field(None, description="Set when routine, e.g. 'Trading-window notice'")
    duplicate_of: str | None = Field(None, description="Filing.id of the same document on the other exchange")
    event_id: str | None = None


class TimelineItem(Model):
    stage: EventStage
    filing_id: str
    at: AwareDatetime
    label: str


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
    score: ScoreBreakdown
    as_of: AwareDatetime = Field(description="Freshness of the underlying data")

    @field_validator("so_what")
    @classmethod
    def _so_what_short(cls, v: str) -> str:
        if len(v.split()) > 10:
            raise ValueError("so_what must be 10 words or fewer")
        return v


class MoveExplanation(Model):
    kind: Literal["filing", "bulk_block_deal", "sector_move", "index_move", "none"]
    text: str = Field(description="e.g. 'Q2 results filed 16:05' or '⚠️ No disclosure explains this move'")
    citation: Citation | None = None


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
    """One portfolio position. Lives in the browser (localStorage); the server only sees it transiently."""

    symbol: str
    quantity: float | None = Field(None, gt=0, description="Shares; used for weight and ₹ impact")
    weight_pct: float | None = Field(None, gt=0, le=100, description="If the user pasted weights instead")
    drivers: list[Driver] = Field(default_factory=list)
    thesis: str | None = Field(None, description="Optional Level-2 thesis line")
    price_alert_pct: float | None = Field(None, gt=0, description="Per-stock override of the ±4% default")
    snoozed_until: AwareDatetime | None = None
    added_at: AwareDatetime


# ---------------------------------------------------------------------------------------------
# Research
# ---------------------------------------------------------------------------------------------


class Promise(Model):
    """A forward-looking management statement and what happened to it (Promise Ledger).
    Exported to TypeScript as `MgmtPromise` to avoid shadowing the built-in JS `Promise`."""

    model_config = ConfigDict(title="MgmtPromise")  # merged with Model.model_config

    id: str
    symbol: str
    statement: str = Field(description="Short normalised statement, e.g. 'EBITDA margin 20–22% in FY27'")
    made_in: Citation = Field(description="Transcript/deck with page and verbatim quote")
    made_on: date
    speaker: str | None = None
    metric: str | None = Field(None, description="e.g. 'EBITDA margin', 'capacity (GW)'")
    target_low: float | None = None
    target_high: float | None = None
    target_unit: str | None = None
    due: Period | None = None
    verdict: Literal["kept", "missed", "goalposts_moved", "quietly_dropped", "pending", "unverifiable"]
    verdict_reason: Claim | None = None
    delivered: Figure | None = None
    superseded_by: str | None = Field(None, description="Promise.id that moved the goalposts")


class Series(Model):
    metric: str
    unit: str
    basis: Literal["consolidated", "standalone"] | None = None
    points: list[Figure]


class DossierSection(Model):
    status: Literal["ready", "partial", "not_found"]
    note: str | None = Field(None, description="e.g. 'Not found in sources: segment revenue'")


class Dossier(Model):
    """Research dossier for any NSE ticker. Primary sources only; every number/claim cited."""

    symbol: str
    name: str
    template: Literal["standard", "bank", "nbfc"] = Field(description="Banks/NBFCs: NII, PPOP, PAT; no EBITDA")
    as_of: AwareDatetime
    snapshot: list[Claim] = Field(default_factory=list)
    headline_figures: list[Figure] = Field(default_factory=list)
    trajectory: list[Series] = Field(default_factory=list)
    trajectory_note: Claim | None = None
    promises: list[Promise] = Field(default_factory=list)
    credibility: Figure | None = Field(None, description="Management credibility score (computed in code)")
    cash_quality: list[Series] = Field(default_factory=list)
    balance_sheet: list[Series] = Field(default_factory=list)
    analyst_questions: list[Claim] = Field(default_factory=list)
    red_flags: list[Claim] = Field(default_factory=list)
    bull: list[Claim] = Field(default_factory=list, max_length=3)
    bear: list[Claim] = Field(default_factory=list, max_length=3)
    sections: dict[str, DossierSection] = Field(default_factory=dict, description="Per-section status")
    sources: list[Citation] = Field(default_factory=list, description="Every document read")
