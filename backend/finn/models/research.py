"""Research contracts: Dossier (any NSE ticker), Promise Ledger, build jobs, Ask.

Stable shape for the frontend: every section is a fixed field that is ALWAYS present, with a `meta` saying whether
it is ready, partial, building or unavailable (and why). Later work only changes `meta.status` and fills content —
it never adds or removes a section. Bump SCHEMA_VERSION on any breaking change; stored dossiers with an older
version are rebuilt rather than served.

Rules carried by these types (CLAUDE.md): numbers are `Figure`s and sentences are `Claim`s, so every number and claim
has provenance; verdicts on numeric promises are decided in code (`verdict_by = "code"`), qualitative ones by a
strong model whose id is recorded (`verdict_model`).
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import AwareDatetime, ConfigDict, Field

from finn.models.common import Basis, Citation, Claim, Figure, Model, Period
from finn.models.core import Driver, ResultsDetail, Series

SCHEMA_VERSION = 1

SectionStatus = Literal["ready", "partial", "building", "unavailable"]
SectionReason = Literal[
    "not_built_yet",  # section not produced by this build yet (job still running)
    "no_screener_page",
    "no_transcripts",
    "few_transcripts",
    "scanned_documents",
    "no_annual_report",
    "not_meaningful_for_lenders",
    "llm_quota",  # model quota exhausted — resumes after `resume_after`
    "llm_unavailable",
    "nse_pending",
    "nse_unavailable",
    "below_min_n",
    "not_found_in_sources",
    "source_unreachable",
]


class SectionMeta(Model):
    status: SectionStatus
    reason: SectionReason | None = None
    note: str | None = Field(None, description="Human line, e.g. 'Based on 3 calls' or 'Available after tonight's "
                             "refresh'")  # fmt: skip
    as_of: AwareDatetime | None = Field(None, description="When this section's content was built (UTC)")
    resume_after: AwareDatetime | None = Field(None, description="When a quota-blocked section resumes (UTC)")
    written_by: str | None = Field(None, description="Model id when the text was written by a model")


# ---------------------------------------------------------------------------------------------
# Documents read
# ---------------------------------------------------------------------------------------------


class DocumentRef(Model):
    id: str = Field(description="sha256 of the PDF bytes (or of the URL when it could not be downloaded)")
    kind: Literal["transcript", "annual_report", "investor_presentation"]
    title: str = Field(description="e.g. 'Q2 FY27 earnings call transcript', 'Annual Report FY26'")
    period: Period | None = Field(None, description="Quarter the call discussed / year of the annual report")
    call_date: date | None = None
    url: str
    status: Literal["read", "scanned", "too_large", "failed", "not_pdf", "skipped"]
    status_note: str | None = None
    pages: int | None = None


# ---------------------------------------------------------------------------------------------
# Promise Ledger
# ---------------------------------------------------------------------------------------------

PromiseKind = Literal["point", "range", "at_least", "at_most", "qualitative"]
Verdict = Literal["kept", "missed", "goalposts_moved", "quietly_dropped", "not_yet_due", "cant_score"]


class PromiseBasis(Model):
    currency: Literal["INR", "USD", "constant_currency", "unspecified", "not_money"]
    scope: Literal["consolidated", "standalone", "segment", "unspecified"]
    segment: str | None = Field(None, description="Segment name when scope == 'segment'")


class PromiseStatement(Model):
    """One call's version of a promise (restatements across calls are grouped into one thread)."""

    doc_id: str
    call_label: str = Field(description="e.g. 'Q1 FY27 call'")
    made_on: date
    kind: PromiseKind
    target_low: float | None = Field(None, description="Normalised (₹ Cr for money, percentage points for %/bps)")
    target_high: float | None = None
    unit: str | None = Field(None, description="Normalised unit: 'INR_CR', 'PCT', 'USD_MN', 'DAYS', 'X', …")
    raw_target: str | None = Field(None, description="Target exactly as said, e.g. '20-22%', '₹1,500 crore'")
    period_text: str | None = Field(None, description="Period exactly as said, e.g. 'this fiscal', 'by FY28'")
    quote: Citation = Field(description="Verbatim quote with page — checked against the transcript text")
    speaker: str | None = None


class Promise(Model):
    """A promise thread: the same metric, basis and period across calls, and what happened to it.
    Exported to TypeScript as `MgmtPromise` (avoids shadowing JS `Promise`)."""

    model_config = ConfigDict(title="MgmtPromise")

    id: str = Field(description="Deterministic hash of the code-built thread key")
    symbol: str
    metric: str = Field(description="As management named it, e.g. 'EBITDA margin'")
    metric_key: str = Field(description="Controlled vocabulary key, e.g. 'ebitda_margin', 'credit_cost', 'other'")
    measure: Literal["level", "growth", "change", "qualitative"]
    kind: PromiseKind
    basis: PromiseBasis
    period: Period | None = Field(None, description="Resolved in code; null = no date given (medium term)")
    statement: str = Field(description="Normalised one-liner built in code, e.g. 'EBITDA margin 11–13% in FY27'")
    statements: list[PromiseStatement] = Field(min_length=1, description="Oldest first")
    scored_target: PromiseStatement | None = Field(
        None, description="The statement scored: the last target given before the period ended"
    )
    revision: Literal["none", "raised", "lowered", "narrowed", "delayed", "revised"] = Field(
        description="raised/lowered judged by the metric's direction (lower credit cost = raised ambition)"
    )
    verdict: Verdict
    verdict_by: Literal["code", "model"]
    verdict_model: str | None = Field(None, description="Model id that wrote a qualitative verdict")
    verdict_reason: Claim | None = Field(None, description="Why, citing the promise and the evidence (both calls)")
    delivered: Figure | None = Field(None, description="What was delivered, with provenance")
    delivered_source: Literal["screener", "management_reported", "xbrl"] | None = None
    dropped_note: str | None = Field(None, description="e.g. 'Not mentioned in the 2 calls since Q1 FY26'")
    driver_ids: list[str] = Field(default_factory=list)


class TrendHalf(Model):
    kept: int
    n: int


class Credibility(Model):
    shown: bool = Field(description="Whether the % score and trend are shown (n ≥ min_n). The tally 'kept of n' is "
                        "always shown, e.g. '2 of 4 kept'")  # fmt: skip
    score_pct: float | None = Field(None, description="kept ÷ n × 100, computed in code; display only when shown")
    kept: int
    n: int = Field(description="kept + missed + goalposts_moved + quietly_dropped")
    numeric_n: int = Field(description="Of n, verdicts decided in code")
    qualitative_n: int = Field(description="Of n, verdicts written by a strong model")
    min_n: int = 5
    trend: Literal["up", "down", "flat"] | None = None
    recent: TrendHalf | None = Field(None, description="Promises settled by results reported in the last 4 calls")
    earlier: TrendHalf | None = None
    formula: str


class LedgerCounts(Model):
    kept: int = 0
    missed: int = 0
    goalposts_moved: int = 0
    quietly_dropped: int = 0
    not_yet_due: int = 0
    cant_score: int = 0
    raised: int = Field(0, description="Threads whose target was raised (a badge, not a verdict)")


# ---------------------------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------------------------


class SnapshotSection(Model):
    meta: SectionMeta
    lines: list[Claim] = Field(default_factory=list, description="Business description, segments, mix")
    segments: list[Figure] = Field(default_factory=list, description="Segment revenue/share as reported")
    headline: list[Figure] = Field(default_factory=list, description="Market cap, revenue, PAT, ROCE/ROE …")


class TrajectorySection(Model):
    meta: SectionMeta
    series: list[Series] = Field(default_factory=list, description="5–12 years: revenue, margins, ROCE, PAT")
    growth: list[Figure] = Field(default_factory=list, description="CAGRs (computed in code)")
    note: Claim | None = Field(None, description="One line on what is growing / compressing")


class LedgerSection(Model):
    """Header example: '2 of 4 kept · 9 not yet due · next test: FY27 results' — from credibility.kept/n,
    counts.not_yet_due and next_test_label."""

    meta: SectionMeta
    promises: list[Promise] = Field(default_factory=list)
    credibility: Credibility | None = None
    counts: LedgerCounts = Field(default_factory=LedgerCounts)
    calls_read: int = 0
    decks_read: int = Field(0, description="Investor decks read for delivered figures the calls didn't state")
    next_test: Period | None = Field(None, description="Earliest period at which a not-yet-due promise is tested")
    next_test_label: str | None = Field(None, description="e.g. 'FY27 results'")
    next_test_on: date | None = Field(None, description="When those results should be out (period end + lag)")
    next_test_count: int = Field(0, description="Promises that fall due at next_test")


class SeriesSection(Model):
    meta: SectionMeta
    series: list[Series] = Field(default_factory=list)
    latest: list[Figure] = Field(default_factory=list, description="Latest-year values for the headline row")


class PressurePoint(Model):
    theme: str
    claim: Claim = Field(description="What analysts keep asking, citing the questions")
    n_calls: int = Field(description="Distinct calls where it was asked (≥ 2)")
    metric_key: str | None = None


class AnalystsSection(Model):
    meta: SectionMeta
    points: list[PressurePoint] = Field(default_factory=list)


class RedFlag(Model):
    kind: Literal["auditor_opinion", "contingent_liabilities", "related_party", "pledging", "disappearing_kpi", "other"]
    claim: Claim
    figures: list[Figure] = Field(default_factory=list)
    severity: Literal["high", "medium", "low"]


class RedFlagsSection(Model):
    meta: SectionMeta
    items: list[RedFlag] = Field(default_factory=list)
    checked: list[str] = Field(
        default_factory=list, description="What was checked and found clean, e.g. 'Auditor opinion: unmodified'"
    )


class BullBearSection(Model):
    meta: SectionMeta
    bull: list[Claim] = Field(default_factory=list, max_length=3)
    bear: list[Claim] = Field(default_factory=list, max_length=3)


class DriversSection(Model):
    meta: SectionMeta
    items: list[Driver] = Field(default_factory=list, max_length=3)


class ExchangeDataSection(Model):
    """NSE-backed enrichment (fetched by GitHub Actions; never blocks the core sections)."""

    meta: SectionMeta
    latest_results: ResultsDetail | None = None
    pledging: list[Figure] = Field(default_factory=list)


class DossierQuality(Model):
    quotes_checked: int = 0
    quotes_dropped: int = Field(0, description="Model quotes not found in the source text — dropped")
    quotes_reanchored: int = Field(0, description="Quotes moved to the page/sentence where they actually are")
    claims_dropped: int = Field(0, description="Model claims dropped (unknown fact id, number mismatch)")


class DossierCost(Model):
    calls: int = 0
    cache_hits: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    est_usd: float = Field(0.0, description="At paid list prices; the free tier bills nothing")
    models: dict[str, int] = Field(default_factory=dict, description="Model id → calls")


class Dossier(Model):
    """Research dossier for any NSE ticker. Primary sources only; every number/claim cited."""

    schema_version: int = SCHEMA_VERSION
    symbol: str
    name: str
    template: Literal["standard", "bank", "nbfc"] = Field(description="Banks/NBFCs: NII, PAT, ROE; no EBITDA")
    basis: Basis | None = Field(None, description="Consolidated by default; standalone when that's all there is")
    as_of: AwareDatetime = Field(description="Freshness of the underlying data (latest source fetch)")
    built_at: AwareDatetime
    snapshot: SnapshotSection
    trajectory: TrajectorySection
    ledger: LedgerSection
    cash_quality: SeriesSection
    balance_sheet: SeriesSection
    analysts: AnalystsSection
    red_flags: RedFlagsSection
    bull_bear: BullBearSection
    drivers: DriversSection
    exchange_data: ExchangeDataSection
    ask_chips: list[str] = Field(default_factory=list, max_length=3)
    sources: list[DocumentRef] = Field(default_factory=list, description="Every document considered")
    screener_url: str | None = None
    quality: DossierQuality = Field(default_factory=DossierQuality)
    cost: DossierCost = Field(default_factory=DossierCost)


# ---------------------------------------------------------------------------------------------
# Jobs, responses, Ask
# ---------------------------------------------------------------------------------------------


class JobStep(Model):
    key: str = Field(description="discover | documents | extract | compute | ledger | judge | reduce | publish")
    label: str
    status: Literal["pending", "running", "done", "skipped", "failed", "waiting"]
    detail: str | None = None


class JobCounters(Model):
    transcripts_total: int = 0
    transcripts_read: int = 0
    guidance_found: int = 0
    quotes_dropped: int = 0


class DossierJob(Model):
    id: int
    symbol: str
    status: Literal["queued", "running", "waiting_quota", "done", "partial", "failed"]
    reason: Literal["requested", "nightly", "new_document", "prewarm", "resume"]
    queue_position: int | None = Field(None, description="1 = next; null when running or finished")
    stage: str | None = None
    steps: list[JobStep] = Field(default_factory=list)
    counters: JobCounters = Field(default_factory=JobCounters)
    message: str = Field(description="e.g. 'Reading 4 of 8 transcripts · 23 guidance statements found'")
    queued_at: AwareDatetime
    started_at: AwareDatetime | None = None
    updated_at: AwareDatetime
    finished_at: AwareDatetime | None = None
    resume_after: AwareDatetime | None = None
    error: str | None = None


class DossierResponse(Model):
    symbol: str
    dossier: Dossier | None = Field(None, description="Last good dossier (may be partial); null = never built")
    job: DossierJob | None = Field(None, description="Active or most recent build")
    dossier_version: int = Field(0, description="Increments on every publish; refetch when it changes")


class AskAnswer(Model):
    status: Literal["answered", "not_found", "unavailable"]
    question: str
    answer: Claim | None = Field(None, description="Status 'not_found' → 'Not found in sources'")
    figures: list[Figure] = Field(default_factory=list)
    resume_after: AwareDatetime | None = None
    model: str | None = None
    reason: (
        Literal["no_dossier", "no_sources", "visitor_cap", "quota", "model_unavailable", "unsupported_number"] | None
    ) = Field(None, description="Why the answer is unavailable / not found (plain words in the UI)")
    cached: bool = Field(False, description="Served from the answer cache (no model call, not counted)")
    remaining_today: int | None = Field(None, description="Questions this visitor has left today (IST)")
