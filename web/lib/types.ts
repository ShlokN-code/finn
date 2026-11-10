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
export type Unit = "INR_CR" | "INR" | "INR_PER_SHARE" | "PCT" | "X" | "DAYS" | "COUNT" | "SHARES";
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
/**
 * A sentence of text with provenance (snapshot lines, red flags, bull/bear bullets, impact reasons).
 */
export interface Claim {
  citations: Citation[];
  status: VerificationStatus;
  text: string;
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
export interface Series {
  basis: ("consolidated" | "standalone") | null;
  metric: string;
  points: Figure[];
  unit: string;
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
 * One portfolio position. Lives in the browser (localStorage); the server only sees it transiently.
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
