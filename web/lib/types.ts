/* AUTO-GENERATED from backend/finn/models (Pydantic) — do not edit by hand.
 * Regenerate: npm run gen:types */

export type SourceType =
  | "exchange_filing"
  | "xbrl"
  | "annual_report"
  | "concall_transcript"
  | "investor_presentation"
  | "screener_table"
  | "price_feed"
  | "web_profile";
export type VerificationStatus = "verified" | "unverified" | "not_found";
export type Unit =
  "INR_CR" | "INR" | "INR_PER_SHARE" | "PCT" | "BPS" | "X" | "DAYS" | "YEARS" | "COUNT" | "SHARES";
/**
 * FINN's filing taxonomy (PRODUCT.md §4 'Category treatment').
 */
export type Category =
  | "results"
  | "mna"
  | "management_change"
  | "litigation"
  | "credit_rating"
  | "pledging"
  | "capex"
  | "press_release"
  | "insider_trading"
  | "fund_raise"
  | "dividend"
  | "bonus_split"
  | "earnings_call"
  | "agm_egm"
  | "postal_ballot"
  | "investor_meetings"
  | "price_volume"
  | "routine"
  | "unclassified";
/**
 * Level-0 relevance: effect on the company's business — not a stock call.
 */
export type Impact = "positive" | "negative" | "mixed" | "neutral";
/**
 * Where a filing sits in an event thread (intimation → outcome → deck → call → transcript → ad).
 */
export type EventStage =
  | "intimation"
  | "outcome"
  | "presentation"
  | "call"
  | "transcript"
  | "newspaper_ad"
  | "clarification"
  | "other";

/**
 * A push notification decision (stored server-side to enforce budget, batching, quiet hours, dedup).
 */
export interface Alert {
  body: string;
  channels: ("telegram" | "webpush")[];
  /**
   * e.g. 'Ex-dividend today'
   */
  day_label: string | null;
  event_id: string | null;
  /**
   * In priority order
   */
  explanations: MoveExplanation[];
  id: string;
  /**
   * Adjusted close-to-close move
   */
  move_pct: Figure | null;
  severity: "critical" | "normal";
  status: "queued" | "sent" | "batched" | "held_quiet_hours" | "over_budget" | "suppressed" | "failed";
  status_reason: string | null;
  symbol: string;
  title: string;
  /**
   * For price/volume alerts (IST trading day)
   */
  trading_date: string | null;
  trigger: "filing" | "price_move" | "volume_spike";
  triggered_at: string;
  /**
   * Volume ÷ 20-day average
   */
  volume_ratio: number | null;
  z_score: number | null;
}
export interface MoveExplanation {
  citation: Citation | null;
  kind: "filing" | "bulk_block_deal" | "sector_move" | "index_move" | "none";
  /**
   * e.g. 'Q2 results filed 16:05' or '⚠️ No disclosure explains this move'
   */
  text: string;
}
/**
 * Where a number or claim came from. Every Figure/Claim that is not `not_found` carries one.
 */
export interface Citation {
  exchange: ("NSE" | "BSE") | null;
  /**
   * Machine locator when there is no page, e.g. 'in-capmkt:ProfitBeforeTax@OneD' or 'screener:quarters/Net Profit/Sep 2026'
   */
  locator: string | null;
  /**
   * 1-based PDF page
   */
  page: number | null;
  /**
   * When the source was published (UTC)
   */
  published_at: string | null;
  /**
   * Verbatim snippet supporting the value/claim
   */
  quote: string | null;
  /**
   * When FINN fetched it (UTC) — drives freshness stamps
   */
  retrieved_at: string;
  source_type: SourceType;
  /**
   * Human title, e.g. 'Q2 FY27 earnings call transcript'
   */
  title: string | null;
  /**
   * Direct link to the document (exchange PDF, XBRL, etc.)
   */
  url: string;
}
/**
 * A number with provenance. Money is float ₹ crore; see DECISIONS.md (float vs Decimal).
 */
export interface Figure {
  /**
   * Consolidated/standalone — always set for financials
   */
  basis: ("consolidated" | "standalone") | null;
  /**
   * Cross-check detail, e.g. 'screener: 49,243 (Δ 0.00%)'
   */
  check_note: string | null;
  citation: Citation | null;
  /**
   * For computed figures: human-readable formula
   */
  formula: string | null;
  /**
   * For computed figures: the sourced inputs
   */
  inputs: Figure[];
  /**
   * e.g. 'Revenue from operations', 'EBITDA margin'
   */
  label: string;
  period: Period | null;
  /**
   * Value exactly as printed, e.g. '1,23,456.78'
   */
  raw: string | null;
  /**
   * Unit as printed, e.g. 'lakh', 'million', 'crore'
   */
  raw_unit: string | null;
  status: VerificationStatus;
  unit: Unit;
  /**
   * Null if and only if status == not_found
   */
  value: number | null;
}
/**
 * A reporting period. `label` is Indian-FY style and is computed in code, never by a model.
 */
export interface Period {
  end: string;
  kind: "quarter" | "half_year" | "nine_months" | "year" | "ttm" | "instant";
  /**
   * e.g. 'Q2 FY27' (Jul–Sep 2026), 'FY26', 'H1 FY27', '30 Sep 2026'
   */
  label: string;
  start: string | null;
}
/**
 * Notification rules (PRODUCT §6). Defaults are the spec's.
 */
export interface AlertSettings {
  batching: boolean;
  daily_budget: number;
  /**
   * Per-symbol override of ±%
   */
  per_stock_pct: {
    [k: string]: number | undefined;
  };
  price_move_pct: number;
  push_categories: Category[];
  /**
   * IST
   */
  quiet_end: string;
  /**
   * IST
   */
  quiet_start: string;
  sector_relative: boolean;
  volatility_aware: boolean;
  volume_multiple: number;
}
/**
 * A ranked Brief item. COMPUTED on read from Event + holdings + rules; never stored.
 */
export interface Card {
  /**
   * Driver labels for the 👁 tag
   */
  affects_drivers: string[];
  /**
   * Freshness of the underlying data
   */
  as_of: string;
  /**
   * @maxItems 3
   */
  ask_chips: [] | [string] | [string, string] | [string, string, string];
  card_type: "results" | "management_change" | "price_volume" | "what_to_watch" | "one_liner" | "inline_chip";
  category: Category;
  detail: (ResultsDetail | ManagementDetail | OneLinerDetail | ChipDetail | PriceVolumeDetail) | null;
  event_id: string;
  headline: string;
  /**
   * Same as event_id (one card per event)
   */
  id: string;
  impact: Impact | null;
  impact_reason: Claim | null;
  key_figures: Figure[];
  next_action: string | null;
  /**
   * ₹ effect on this holding, when computable
   */
  rupee_impact: Figure | null;
  score: ScoreBreakdown;
  /**
   * ≤10 words
   */
  so_what: string;
  /**
   * Source chips (first = primary filing)
   */
  sources: Citation[];
  symbol: string;
  timeline: TimelineItem[];
}
export interface ResultsDetail {
  basis: "consolidated" | "standalone";
  /**
   * Methodology note shown on tap: how EBITDA is defined; for banks, the PAT basis
   */
  ebitda_note: string | null;
  /**
   * The results filing to open when unverified
   */
  filing_url: string | null;
  kind: "results";
  lines: ResultsLine[];
  /**
   * 8-quarter margin sparkline (screener table)
   */
  margin_series: Series | null;
  quarter: Period;
  /**
   * Where the current quarter came from: XBRL → PDF table → multimodal model on the PDF
   */
  source_path: "xbrl" | "pdf_table" | "pdf_model";
  template: "standard" | "bank" | "nbfc";
  /**
   * Mean PAT YoY % of the 4 prior quarters (screener, computed in code) — ranking 'surprise'
   */
  trend_pat_yoy_pct: number | null;
  /**
   * cross_checked: every line agrees with screener + sanity checks. partial: every comparable line agrees, but some line has no screener counterpart (named in the note). pending: screener has not published the quarter yet. mismatch: show 'Couldn't verify — open filing', no numbers.
   */
  verification: "cross_checked" | "partial" | "pending" | "mismatch";
  verification_note: string | null;
}
/**
 * One results metric: three sourced quarters plus QoQ/YoY computed in code.
 */
export interface ResultsLine {
  /**
   * Cross-check of the current value against screener's quarterly table
   */
  check: "match" | "mismatch" | "not_in_screener" | "not_checked";
  current: Figure;
  /**
   * e.g. 'Revenue', 'EBITDA', 'EBITDA margin', 'PAT', 'NII', 'PPOP'
   */
  metric: string;
  /**
   * Previous quarter (same basis)
   */
  previous: Figure | null;
  /**
   * % change (bps for margins); null value = not meaningful
   */
  qoq: Figure | null;
  /**
   * Same quarter last year (same basis)
   */
  year_ago: Figure | null;
  yoy: Figure | null;
}
export interface Series {
  basis: ("consolidated" | "standalone") | null;
  metric: string;
  points: Figure[];
  unit: string;
}
export interface ManagementDetail {
  kind: "management_change";
  people: PersonProfile[];
  /**
   * The card is complete from the filing alone; web snippets only add to it
   */
  web_enrichment: "done" | "unavailable" | "not_run" | "nothing_found";
  web_note: string | null;
}
export interface PersonProfile {
  change: "appointed" | "resigned" | "re_designated" | "retired" | "other";
  effective: string | null;
  /**
   * Decided in code: a prior role at this company/group
   */
  insider: boolean | null;
  insider_reason: string | null;
  name: string;
  prior_roles: PriorRole[];
  /**
   * Verbatim profile paragraph from the filing
   */
  profile: Claim | null;
  qualifications: Claim[];
  /**
   * Position named in the filing, e.g. 'Chief Financial Officer'
   */
  role: string;
  /**
   * Outgoing person's tenure, computed in code
   */
  tenure_years: Figure | null;
}
export interface PriorRole {
  citation: Citation;
  company: string;
  /**
   * Null = to date / not stated
   */
  end_year: number | null;
  role: string | null;
  source: "filing" | "web";
  start_year: number | null;
}
/**
 * A sentence of text with provenance (snapshot lines, red flags, bull/bear bullets, impact reasons).
 */
export interface Claim {
  citations: Citation[];
  status: VerificationStatus;
  text: string;
}
export interface OneLinerDetail {
  /**
   * Rating upgrade/downgrade, pledge increase/decrease — decided in code
   */
  direction: ("up" | "down" | "new" | "unchanged") | null;
  /**
   * Extracted fields as printed
   */
  facts: {
    [k: string]: string | undefined;
  };
  key_figure: Figure | null;
  kind: "one_liner";
  line: Claim;
}
export interface ChipDetail {
  amount: Figure | null;
  citation: Citation | null;
  ex_date: string | null;
  kind: "chip";
  record_date: string | null;
  /**
   * e.g. '₹8 dividend · record 21 Nov'
   */
  text: string;
}
export interface PriceVolumeDetail {
  /**
   * e.g. 'Ex-dividend today'
   */
  day_label: string | null;
  /**
   * In priority order
   */
  explanations: MoveExplanation[];
  kind: "price_volume";
  /**
   * Ex-date mechanical move removed before testing
   */
  mechanical_pct: number | null;
  move_pct: Figure;
  /**
   * Stock minus sector (sector-relative mode)
   */
  relative_move_pct: Figure | null;
  sector_index: string | null;
  sector_move_pct: Figure | null;
  trading_date: string;
  triggers: ("price" | "volume")[];
  /**
   * Volume ÷ 20-session average
   */
  volume_ratio: Figure | null;
  z_score: number | null;
}
/**
 * score = category_weight × position_weight × relevance × novelty × surprise ('Why is this #1?').
 */
export interface ScoreBreakdown {
  category_weight: number;
  /**
   * e.g. 'Touches confirmed driver: Margins'
   */
  notes: string[];
  novelty: number;
  position_weight: number;
  relevance: number;
  surprise: number;
  total: number;
}
export interface TimelineItem {
  at: string;
  filing_id: string;
  label: string;
  stage: EventStage;
}
/**
 * Research dossier for any NSE ticker. Primary sources only; every number/claim cited.
 */
export interface Dossier {
  analyst_questions: Claim[];
  as_of: string;
  balance_sheet: Series[];
  /**
   * @maxItems 3
   */
  bear: [] | [Claim] | [Claim, Claim] | [Claim, Claim, Claim];
  /**
   * @maxItems 3
   */
  bull: [] | [Claim] | [Claim, Claim] | [Claim, Claim, Claim];
  cash_quality: Series[];
  /**
   * Management credibility score (computed in code)
   */
  credibility: Figure | null;
  headline_figures: Figure[];
  name: string;
  promises: MgmtPromise[];
  red_flags: Claim[];
  /**
   * Per-section status
   */
  sections: {
    [k: string]: DossierSection | undefined;
  };
  snapshot: Claim[];
  /**
   * Every document read
   */
  sources: Citation[];
  symbol: string;
  /**
   * Banks/NBFCs: NII, PPOP, PAT; no EBITDA
   */
  template: "standard" | "bank" | "nbfc";
  trajectory: Series[];
  trajectory_note: Claim | null;
}
/**
 * A forward-looking management statement and what happened to it (Promise Ledger).
 * Exported to TypeScript as `MgmtPromise` to avoid shadowing the built-in JS `Promise`.
 */
export interface MgmtPromise {
  delivered: Figure | null;
  due: Period | null;
  id: string;
  made_in: Citation;
  made_on: string;
  /**
   * e.g. 'EBITDA margin', 'capacity (GW)'
   */
  metric: string | null;
  speaker: string | null;
  /**
   * Short normalised statement, e.g. 'EBITDA margin 20–22% in FY27'
   */
  statement: string;
  /**
   * Promise.id that moved the goalposts
   */
  superseded_by: string | null;
  symbol: string;
  target_high: number | null;
  target_low: number | null;
  target_unit: string | null;
  verdict: "kept" | "missed" | "goalposts_moved" | "quietly_dropped" | "pending" | "unverifiable";
  verdict_reason: Claim | null;
}
export interface DossierSection {
  /**
   * e.g. 'Not found in sources: segment revenue'
   */
  note: string | null;
  status: "ready" | "partial" | "not_found";
}
/**
 * Something the user watches for a holding (Level-1 relevance), suggested from disclosures.
 */
export interface Driver {
  description: string;
  /**
   * Slug, e.g. 'TATAPOWER:renewables-capacity'
   */
  id: string;
  /**
   * Short tag shown on cards, e.g. 'Margins'
   */
  label: string;
  /**
   * Related Promise Ledger items
   */
  promise_ids: string[];
  /**
   * Why FINN suggested it, with citation
   */
  source: Claim | null;
  status: "suggested" | "confirmed" | "dismissed";
  symbol: string;
}
/**
 * Filings about one real-world event, threaded into a single unit (one card in the Brief).
 */
export interface Event {
  category: Category;
  /**
   * Card-type specific payload
   */
  detail: (ResultsDetail | ManagementDetail | OneLinerDetail | ChipDetail | PriceVolumeDetail) | null;
  /**
   * Drivers this event touches
   */
  driver_ids: string[];
  /**
   * Extracted facts, e.g. results line items
   */
  figures: Figure[];
  id: string;
  impact: Impact | null;
  impact_reason: Claim | null;
  /**
   * Threading key, e.g. 'INFY:results:Q2 FY27' or 'HDFCBANK:management_change:2026-11-06'
   */
  key: string;
  /**
   * For results events
   */
  period: Period | null;
  /**
   * ≤10 words, written in code or by the Level-0 tagger
   */
  so_what: string | null;
  started_at: string;
  symbol: string;
  timeline: TimelineItem[];
  title: string;
  updated_at: string;
}
/**
 * One exchange announcement, as ingested. NSE and BSE copies of the same document are both kept;
 * the later one points at the first via `duplicate_of`.
 */
export interface Filing {
  attachment_url: string | null;
  bse_code: string | null;
  /**
   * FINN category; null until classified
   */
  category: Category | null;
  category_confidence: number | null;
  /**
   * Model id when category_source == 'model'
   */
  category_model: string | null;
  /**
   * Classification ladder tier: exchange's own label → keyword rules → cheap model. Null with category 'unclassified' means every tier failed.
   */
  category_source: ("exchange" | "rule" | "model") | null;
  /**
   * Filing.id of the same document on the other exchange
   */
  duplicate_of: string | null;
  event_id: string | null;
  exchange: "NSE" | "BSE";
  /**
   * Exchange's own label, e.g. 'Change in Management'
   */
  exchange_category: string;
  /**
   * NSE seq_id / BSE NEWSID
   */
  exchange_id: string;
  /**
   * When FINN fetched it (UTC) — freshness
   */
  fetched_at: string | null;
  /**
   * Exchange dissemination time (UTC)
   */
  filed_at: string;
  /**
   * Set when routine, e.g. 'Trading-window notice'
   */
  hidden_reason: string | null;
  /**
   * Stable id: '<exchange>:<exchange_id>', e.g. 'NSE:118230211'
   */
  id: string;
  isin: string | null;
  stage: EventStage | null;
  /**
   * Headline / attachment text from the exchange
   */
  subject: string;
  /**
   * NSE symbol (canonical key across the app)
   */
  symbol: string;
  xbrl_url: string | null;
}
/**
 * One portfolio position. Lives in the browser (localStorage). Symbols + weights are sent with each /brief
 * request and used only to rank it — never stored unless the user turns on Telegram alerts. `quantity` never
 * leaves the phone.
 */
export interface Holding {
  added_at: string;
  drivers: Driver[];
  /**
   * Per-stock override of the ±4% default
   */
  price_alert_pct: number | null;
  /**
   * Shares; used for weight and ₹ impact
   */
  quantity: number | null;
  snoozed_until: string | null;
  symbol: string;
  /**
   * Optional Level-2 thesis line
   */
  thesis: string | null;
  /**
   * If the user pasted weights instead
   */
  weight_pct: number | null;
}
/**
 * A visible feedback adjustment (PRODUCT §5). Listed on the Rules screen; Reset deletes it.
 */
export interface WeightRule {
  category: Category | null;
  event_id: string | null;
  /**
   * Deterministic from scope, e.g. 'stock:IDEA', 'category:fund_raise', 'stock_category:BAJFINANCE:fund_raise', 'event:<event id>'
   */
  id: string;
  /**
   * Product of ×0.8 (not useful) and ×1.25 (useful) taps, bounded
   */
  multiplier: number;
  not_useful_count: number;
  scope: "stock" | "category" | "stock_category" | "event";
  symbol: string | null;
  updated_at: string;
  useful_count: number;
}
