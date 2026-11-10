# Decisions

Short records of key decisions: context, decision, alternatives considered, why.

---

## 2026-11-10 · Python 3.12 venv from the Anaconda interpreter
- **Context:** The only 3.12 on the dev machine is Anaconda's; the system default is 3.13. Must not use the Anaconda base env.
- **Decision:** `.venv/` at repo root created with `/opt/anaconda3/bin/python3.12 -m venv`. A venv carries none of base's packages. Render pins 3.12 via `backend/.python-version` and `PYTHON_VERSION`.
- **Alternatives:** `brew install python@3.12`; `uv`. Both add tooling for no gain today.

## 2026-11-10 · Money as float ₹ crore, with explicit numeric rules
- **Context:** Float vs Decimal for money. Doubles carry ~15–16 significant digits, so float error never reaches a displayed digit at our magnitudes. The real risks are elsewhere.
- **Decision:** `float` in contracts and JSON. `finn/numbers.py` enforces: (1) `approx_equal` with source-aware tolerances — never `==` (screener rounds to whole crore; filings to lakh); (2) compute on unrounded values, round only for display, half-up via `round_display` (2.675 → 2.68); (3) `pct_change` returns None on a ≤0 base (show "n/m"/"turned profitable"). `Figure.raw`/`raw_unit` keep the value exactly as printed for provenance.
- **Alternatives:** `Decimal` end to end — serialises as strings in JSON (awkward TS types, more conversions) and doesn't fix any of the real risks.

## 2026-11-10 · Contracts: Pydantic → JSON Schema → generated TypeScript
- **Context:** CLAUDE.md requires models defined once and mirrored to TS.
- **Decision:** Pydantic models are the source of truth. `python -m finn.models.export_schema` → `web/lib/schema.json` → `json-schema-to-typescript` → `web/lib/types.ts`. CI fails if either is stale. Serialization-mode schema marks defaulted fields required (the API always emits them).
- **Alternatives:** hand-written TS mirror (drifts silently); OpenAPI codegen (pulls in the whole API surface, heavier).
- **Related choices:** `Promise` is exported to TS as `MgmtPromise` (avoids shadowing JS `Promise`). Added `Figure` (number + unit + period + basis + status + citation; computed figures list their `inputs`) and `Claim` (text + citations) so "every number and claim carries provenance" is enforced by validators, not convention. `Card` is computed on read, never stored.

## 2026-11-10 · Web reaches the API through a Vercel route-handler proxy
- **Context:** Render's free tier sleeps; a cold start can take ~50 s. CORS and exposing the API URL are avoidable.
- **Decision:** Browser → `web/app/api/*` (Vercel) → Render. The page renders instantly and shows a "waking the API" state; the proxy allows 55 s.
- **Alternatives:** browser calls Render directly (CORS, URL exposed); server component fetch (blank page during cold start).

## 2026-11-10 · Database access via Supabase session pooler; RLS on
- **Context:** Render free tier has no IPv6; Supabase's direct connection host is IPv6-only.
- **Decision:** API connects with the **Session pooler** URI (IPv4, port 5432) using psycopg 3. Every table has RLS enabled with no policies, so the public anon key (PostgREST) can read nothing; the API's role bypasses RLS. Before real data, switch the API to a least-privilege role.
- **Alternatives:** supabase-py over PostgREST (extra hop, service-role key in the API anyway).

## 2026-11-10 · Keep-alive
- **Context:** Render free sleeps after ~15 min idle; Supabase free pauses after 7 days idle; evaluators may open the app weeks later.
- **Decision:** `keepalive.yml` pings `/health` and `/health/db` every 10 min (repo variable `API_BASE_URL`). One always-on service ≈ 744 h/month, within Render's 750 free hours — so only one Render service.

## 2026-11-10 · Data-source choices from the spike (details in DATA_SOURCES.md)
- **Prices:** Yahoo (yfinance) for EOD. Its `Close` and `Volume` are already split/bonus-adjusted (verified against NSE raw: HDFCBANK 25-Aug-2025 ₹1,964.10 raw vs ₹982.05 on Yahoo; volume exactly 2×). `Adj Close` additionally adjusts for dividends. Yahoo's corporate-action *metadata* is unreliable (BAJFINANCE's 1:2 split + 4:1 bonus shows as one "2:1 split"), so **NSE `corporates-corporateActions` is the source of truth for ex-dates and labels**. Fallback: NSE `historicalOR/generateSecurityWiseHistoricalData` (raw) + our own adjustment.
- **Results:** XBRL first via NSE `integrated-filing-results` (from the Mar-2025 quarter) and `corporates-financial-results` (≤ Dec-2024). Each XBRL instance holds only the current quarter + YTD, so QoQ/YoY come from three filings' XBRL (current, previous, year-ago), cross-checked against screener's quarterly table. The PDF path (three columns in one document, per PRODUCT.md) remains the fallback.
- **Where jobs run:** from GitHub Actions (US datacenter IPs) NSE, Yahoo, screener and XBRL all work; **BSE returns 403 to every API call but serves its PDFs**. So NSE is the only exchange feed for scheduled ingest; BSE announcements are local/backup only, while BSE-hosted documents (screener's transcript/annual-report links) remain usable. Render's IPs are untested until the API is live.
- **User-Agent:** NSE/BSE reject non-browser UAs (and NSE archives tarpit them), so exchange calls use a browser UA after a homepage cookie warm-up. Everything else identifies as `FINN-research/0.1`. Exchange calls are spaced ≥ 2–2.5 s per host with backoff.

## 2026-11-10 · Holdings: browser by default, opt-in server copy for push
- **Context:** The spec says holdings never leave the phone, but personalised Telegram/web-push alerts need the server to know what the user holds.
- **Decision (product owner):** Holdings live in localStorage by default. Connecting Telegram (or web push) uploads a server copy of **symbols + weights only** (no quantities or cost), keyed to that chat/subscription. The connect screen says so; "Disconnect & delete" removes it. The in-app Brief still ranks on the phone.
- **Alternatives:** browser-only (push limited to generic or watchlist-free alerts); full accounts/login (rejected in the spec — friction for evaluators).
- **Update (Phase 2, product owner):** ranking now runs only on the server (see "Ranking lives only in Python"), so the phone sends symbols + weights with each `/brief` request. Wording everywhere: **"Holdings are used only to rank your Brief and are never stored, unless you turn on Telegram alerts."** `/brief` never logs request bodies; share quantities still never leave the phone.
- **Implications:** a `push_subscriptions` table (chat id, symbols, weights, created_at) with RLS; a delete endpoint; `Holding.quantity` never leaves the device.

## 2026-11-10 · Corporate actions: NSE feed is the source of truth
- **Context:** Yahoo's prices are correctly split/bonus-adjusted, but its action records are not (BAJFINANCE's 1:2 split + 4:1 bonus on 16-Jun-2025 appears as one "2:1 split").
- **Decision:** Ex-dates and labels ("Ex-dividend today", "Bonus 1:1") come from NSE `corporates-corporateActions`. Price-feed action columns are ignored. Alert logic uses adjusted returns and suppresses only the mechanical part of an ex-date move.
- **Alternatives:** trust Yahoo's actions (wrong labels/ratios); BSE corporate actions (API blocked from GitHub runners).

## 2026-11-10 · Results from three XBRL filings, cross-checked; PDF fallback
- **Context:** The spec assumed one results filing gives current / previous / year-ago columns. NSE's XBRL instances carry only the current quarter (+ YTD).
- **Decision:** For each results event, pull the XBRL for the current, previous and year-ago quarter (same consolidated/standalone basis) from `integrated-filing-results` (Mar-2025 onward) or `corporates-financial-results` (≤ Dec-2024). Compute QoQ/YoY and EBITDA in code. Cross-check against screener's quarterly table with `approx_equal`; mismatch → `unverified` with a `check_note`. If any XBRL is missing, fall back to the results PDF's three-column table.
- **Alternatives:** PDF first (table parsing is error-prone, needs a model for scanned files); screener only (secondary source — fine for cross-checks, not as the cited source).
- **Why:** XBRL is structured, exact and primary; three small files (~0.1 MB each) are cheap.

## 2026-11-10 · Promise Ledger: code judges numbers, the model judges language
- **Context:** The spec gave Promise Ledger verdicts to the strong model, which conflicts with rule 1 (no comparisons by a model).
- **Decision:** For numeric promises the model only extracts metric, target value/range, period and quote; code compares the delivered `Figure` against the target and sets kept/missed. The strong model judges qualitative promises and cross-call patterns — goalposts moved (target/date revised in a later call) and quietly dropped (no longer mentioned) — and must cite both calls.
- **Alternatives:** the model judges everything (violates rule 1, unauditable); code only (can't recognise a revised or abandoned promise phrased differently).

## 2026-11-10 · One card per event; one price/volume event per stock per day
- **Decision:** `Card.id = event_id`. Price/volume alerts become synthetic events keyed `SYMBOL:price_volume:YYYY-MM-DD` (IST trading day), so one stock gets at most one price/volume card per day, and feedback/undo apply to it like any other card.
- **Alternatives:** separate card ids per alert (duplicates on volatile days; feedback scattered).

## 2026-11-10 · Holding takes quantity or weight
- **Decision:** `Holding.quantity` and `Holding.weight_pct` are both optional; either one gives position weight. Quantity also enables ₹ impact. Paste-import accepts either.
- **Alternatives:** require quantity (most people paste tickers with weights, not share counts).

## 2026-11-10 · Filing.duplicate_of kept, low priority
- **Context:** NSE↔BSE dedup was planned, but BSE's APIs are blocked from GitHub runners, so scheduled ingest only sees NSE.
- **Decision:** Keep the field (BSE may be used locally or later), but don't build dedup until BSE ingest is actually running.
- **Update (Phase 1, product owner):** dedup logic + tests are built (`finn/ingest/dedup.py`, BSE parser in `finn/sources/bse.py`) against the saved BSE samples; BSE is still not wired into the jobs. See "NSE↔BSE dedup" below.

## 2026-11-10 · NSE is fetched only by GitHub Actions; the API never calls NSE
- **Context:** `GET /health/sources` on Render (AWS Singapore) shows NSE returns 403 for everything — APIs, archive PDFs, XBRL, equity list. GitHub-hosted runners (Azure US) are not blocked. BSE PDFs and screener work from both.
- **Decision:** All NSE ingestion runs in GitHub Actions jobs and writes to Supabase (and raw documents to storage). The Render API reads only from Supabase, screener and BSE-hosted PDFs. The equity list for autocomplete is refreshed by a job and served as static JSON.
- **On demand:** a never-seen ticker gets its NSE-only data from a dispatched GitHub job — see "On-demand NSE data via workflow dispatch" below.
- **Alternatives:** proxying NSE through a residential IP (fragile, against the spirit of rule 6); moving the API to another host (no evidence another free datacenter host is unblocked, and GitHub runners already work).
- **Diagnostics:** `/health/sources` stays in the API — cached 15 min and single-flight, so it can't be used to hammer the sources.

## 2026-11-10 · On-demand NSE data via workflow dispatch (with guardrails)
- **Context:** NSE blocks Render, so the API cannot fetch NSE data for a ticker that hasn't been ingested. GitHub-hosted runners can.
- **Decision (product owner):** For a never-seen ticker, the API dispatches a GitHub Actions workflow that fetches that ticker's NSE data into Supabase (~1–2 min). Guardrails:
  - Dispatch only for symbols in the NSE equity list.
  - At most one dispatch per ticker per IST day; if a run for that ticker is queued or running, reuse it.
  - Fine-grained GitHub token: this repo only, Actions permission only, 90-day expiry; stored only on Render.
  - If dispatch or the run fails, NSE-backed sections say "Available after tonight's refresh" — no error state; the nightly job covers it.
  - The dossier's core sections (snapshot, trajectory, Promise Ledger, cash, balance sheet) run on screener + BSE PDFs alone; NSE data only enriches and never blocks.
- **Alternatives:** wait for the nightly job (simpler, but a curious evaluator sees gaps for hours); fetch NSE via a residential proxy (fragile, impolite).
- **Plan:** docs/PLAN.md, "Research dossier — on-demand NSE data".

## 2026-11-10 · Cheap LLM tier: Gemini free tier, Groq as text-only fallback
- **Context:** Classification leftovers (and later bulk extraction) need a cheap model. Product owner chose Google AI Studio's free tier (no billing).
- **Decision:** `finn/llm/` routes `cheap` → Gemini Flash-Lite, `strong` → Gemini Flash; model ids come from env (`GEMINI_MODEL_CHEAP/STRONG`) and are checked against the key's live model list with `python -m finn.llm.check` (verified 10 Nov 2026: `gemini-3.5-flash-lite`, `gemini-3.8-flash`). PDFs go inline (first 2 pages only, cut with pypdf) when a subject is boilerplate. Every call is cached by content hash in `llm_calls`, which is also the token/cost log (USD estimate at paid list price, even though the free tier bills nothing). Router enforces requests/minute (sleeps) and requests/day (counted from the log, Pacific-midnight day like Gemini's), defaults 10 RPM / 400 RPD — conservative because per-model free limits are only shown in the AI Studio dashboard. On quota/error: Groq (`llama-3.1-8b-instant`, text only, optional key) → `LLMUnavailable` → filing stays `unclassified` with tier `failed` and is retried next run.
- **Privacy:** free-tier inputs may be used by Google to improve its products. Acceptable: FINN only sends public exchange filings (no holdings, no user data).
- **Alternatives:** Claude Haiku (paid; offered first); no model tier (leftovers stay unclassified).

## 2026-11-10 · `Category.routine` and a three-tier `category_source`
- **Context:** PRODUCT.md had only `unclassified` for the hidden drawer, mixing "known boring" with "couldn't tell", which hides how well classification works.
- **Decision (product owner):** add `routine` (always hidden; `hidden_reason` names the drawer group: Newspaper ad, Trading-window notice, ESOP allotment / grant, Compliance certificate, …). `unclassified` now means every tier failed. `Filing.category_source` = `exchange | rule | model` (the ladder tier) plus `category_model`; the DB also keeps `classify_tier = failed` and a `classify_note` (rule name / model reason / failure).

## 2026-11-10 · Classification ladder order and scope
- **Decision:** (a) NSE `desc` only when the label alone is unambiguous ("Change in Management", "Credit Rating", "ESOP/ESOS/ESPS", …); (b) ordered regex rules on the subject with NSE boilerplate stripped ("X Limited has informed the Exchange regarding …"), then weak fallbacks on coarse labels; (c) the model. Exchange-sought clarifications ("news item captioned …") always go to the model — keyword rules would classify the quoted headline, not the filing.
- **Measured** on 757 real portfolio filings (Aug–Nov 2026) before the model: 33 % exchange, 49 % rule, 17 % left for the model.

## 2026-11-10 · Event threading heuristics
- **Decision:** results threads keyed `SYM:results:<Q label>`; the quarter is read from the text ("quarter ended 30th June 2026", "Q1 FY2027", "period ended Jun 30, 2026") or inferred from the filing date (season = quarter end − 15 d to + 75 d). Investor presentations within 2 days of a results outcome and newspaper ads within 3 days of an event's last filing attach as satellites. Other material categories cluster per symbol+category when filings are ≤ 7 days apart. Routine / investor-meeting / unclassified filings are not threaded (hidden drawer). Event id = its key, and each run re-threads a symbol's full history in one transaction, so threading is idempotent.
- **Board-meeting intimations** come from NSE's `corporate-board-meetings` feed (they rarely appear in the announcements feed) and are stored as filings with exchange id `BM-<hash>`, so the results thread starts at the intimation.
- **Known limits:** two unrelated filings of one category within 7 days merge (e.g. two separate appointments); a subsidiary's results intimation can land in the parent's thread.

## 2026-11-10 · Filing checks run 08:30–22:00 IST, holidays included
- **Context:** The phase brief said "30-minute filing checks during market hours". Most results land after the close (RELIANCE 19:40, INFY 16:08), and companies file on exchange holidays (COCHINSHIP and KALYANKJIL hold results board meetings on 10 Nov, a trading holiday).
- **Decision:** `*/30 3-16 * * 1-5` UTC (08:30–22:00 IST, weekdays); the script gates the window and does not skip exchange holidays. Prices are skipped on non-trading days. The repo is public, so Actions minutes are free.

## 2026-11-10 · Migrations applied by a job
- **Decision:** `python -m jobs.migrate` applies `backend/db/migrations/*.sql` in order and records them in `schema_migrations`; the daily workflow runs it first. Replaces the manual SQL-editor step (0001 is idempotent and was re-recorded).

## 2026-11-10 · Showcase snapshot stored twice
- **Decision:** `jobs/snapshot.py` freezes the portfolio's filings, events, prices (+20 prior sessions), nearby corporate actions, deals and freshness for one IST day into the `snapshots` table **and** `backend/data/snapshots/<date>.json` in git, so the replay survives a Supabase pause. PDFs are referenced by NSE archive URL, not mirrored.

## 2026-11-10 · Backfill depth
- **Decision:** prices 1 year (spec); filings 120 days for the first backfill. A full year of filings would need ~400 model calls for leftovers — the whole conservative daily budget. Older filings can be backfilled in daily slices later; research uses screener/BSE documents, not this feed.

## 2026-11-10 · Ambiguous between routine and material → material
- **Context:** Eval review (product owner). Hiding is FINN's core value, so a wrongly hidden material filing costs more than a routine one shown: the user can swipe the latter away, but never sees the former.
- **Decision:** when a filing could be routine or material, it is classified material.
  - Rules: only *strong* routine rules are final (trading window, ESOP, shareholder administration, compliance certificate, policy document, ESG rating). A *weak* routine match — today the newspaper-ad rule and NSE's "Copy of Newspaper Publication" label — yields to any material rule that also matches the subject, keeping the `newspaper_ad` stage (a results ad joins its results thread; an AGM-notice ad its AGM event).
  - Model: the prompt says to choose the material category when torn.
  - Content-free newspaper ads (subject only "Copy of Newspaper Publication" / "the advertisement on the captioned subject") are read by the model from their first two PDF pages. Material → that category with stage `newspaper_ad`; routine → stays in the drawer; model unavailable → stays hidden but is marked for retry (`classify_tier = failed`, note `llm unavailable…`). No readable PDF → keeps the routine label. On 120 days of portfolio filings: 49 such ads, 20 material (8 results, 8 AGM notices, 2 postal ballots, 2 M&A), 24 routine, 5 unreadable; 44 calls ≈ $0.03 at list price (free tier).
  - Threading: an ad filed in the last 15 days of a quarter is treated as forward-looking (e.g. a newspaper notice of the coming results board meeting).
- **Related label decisions:** NCD/debenture/CP allotments are `fund_raise` (debt raise), not routine; a listed subsidiary's IPO (Jio Platforms for RELIANCE) is `mna` (stake sale); results newspaper publications under Reg 33/47 are `results`; opening a facility is `press_release`, not capex (no board-approved spend).
- **Measured:** on ~750 real portfolio filings, 26 changed category: NCD allotments (10), results ads (6), AGM/postal-ballot notice ads (4), Jio IPO filings (5, four of which previously needed the model), 1 dividend ad. Stored filings were re-run through the rules (29 changed), re-threaded, and the 30 Oct snapshot refreshed.
- **Cost:** NBFCs that issue NCDs weekly (BAJFINANCE) now produce a fund-raise one-liner each time; the Brief's ranking and feedback weights must keep these low.
- **Alternatives:** keep routine-first ordering (cleaner Brief, but results ads and subsidiary IPOs vanish into the drawer).


## 2026-11-10 · Ranking lives only in Python; the phone sends holdings per request
- **Context:** Telegram alerts need ranking on the server; the spec had the in-app Brief ranking on the phone. Two implementations would drift.
- **Decision (product owner):** one implementation in `finn/ranking/`. The phone POSTs symbols + weights and its feedback rules to `/brief`; the API ranks and stores nothing (no request-body logging). Share quantities never leave the phone, so ₹ impact is computed there from the card's move %.
- **Wording everywhere:** "Holdings are used only to rank your Brief and are never stored, unless you turn on Telegram alerts."
- **Alternatives:** a TypeScript port with shared test vectors (two copies to keep in sync).

## 2026-11-10 · Ranking constants
- `score = category_weight × position_weight × relevance × novelty × surprise`; each factor is explained in `ScoreBreakdown.notes` ("Why is this #1?").
- **Category base:** results 1.0 · M&A 0.95 · management change 0.9 · credit rating 0.8 (downgrade 0.9, upgrade/reaffirm 0.5) · litigation 0.8 · pledging 0.8 (decrease 0.4) · price/volume 0.7 · capex 0.6 · press release 0.5 · insider trade 0.5 · fund raise 0.4 · dividend / bonus-split 0.3 · call / AGM / postal ballot 0.25 · hidden categories 0.
- **Position:** `0.40 + 0.285·√weight%`, capped 1.8 (≈0.80 at 2 %, ≈1.50 at 15 %, as the spec sketches); not held 0.4.
- **Relevance (Level 0):** positive/negative 1.2, mixed 1.1, neutral 0.8, untagged 1.0; Level-1 driver hit ×1.5 (hook; drivers arrive with the Promise Ledger).
- **Novelty:** event started inside the window 1.0; otherwise the most substantive filing inside the window (outcome 1.0, deck/call/transcript 0.6, intimation 0.5, ad/clarification 0.3). Same symbol+category repeats within 30 days ×0.5 each (floor 0.125) — BAJFINANCE's weekly NCD allotments sink instead of each looking like news.
- **Surprise:** results: `1 + min(1, |PAT YoY − mean of the 4 prior quarters' PAT YoY| / 20 pp)` from screener's 13 quarters; price/volume: `clamp(|z|/2, 1, 2)`; others 1.0. Guidance deviation is a hook for the Promise Ledger.
- **Feedback:** ×0.8 per "not useful" at the chosen scope (stock / category / stock+category / this event), ×1.25 per "useful", bounded [0.1, 2.0]; critical categories (results, M&A, management change, rating downgrade) never fall below 0.5× base. Rules are visible objects (`WeightRule`) with Reset.
- **Why these numbers:** hand-set and explainable; tests pin the spec's examples (position curve points, a big event in a small holding beating a small event in a big one).

## 2026-11-10 · Results card: operating EBITDA, three verification states
- **EBITDA = profit before exceptional items and tax + finance costs + D&A − other income.** Other income (treasury yield, dividends) and one-off exceptional items are excluded, so EBITDA reflects operations and equals screener's "Operating Profit" (Sales − Expenses) — which makes it cross-checkable. When only PBT is reported, exceptional items are added back from their own line. Banks: NII = interest earned − interest expended, PPOP as reported. NBFCs: NII = interest income − finance costs, PPOP = PBT + impairment on financial instruments.
- **Verification:** every line of each quarter is compared with screener's quarterly table with a tolerance summed from the sources' rounding (XBRL `decimals`, screener's whole crore). States: **cross_checked** (all agree + sanity checks pass), **pending** (screener hasn't published the quarter yet — numbers shown, labelled, re-checked every run), **mismatch** (any disagreement or failed sanity check → "Couldn't verify — open filing", no numbers, no impact tag). Margins, QoQ and YoY are verified only when every input is.
- **Sanity checks:** revenue > 0; EBITDA margin within −50…80 %; revenue + other income − expenses reconciles to PBT before exceptional items.
- **Order of sources:** XBRL (three filings) → results-PDF table (text layer; the PDF lands ~4 h before the XBRL — INFY 16:08 vs 20:16) → multimodal model for scanned PDFs. PDF-sourced cards upgrade to XBRL when it's filed (no re-alert).
- **Level-0 impact for results is decided in code:** revenue (NII for lenders) and PAT YoY both up → positive, both down → negative, else mixed.

## 2026-11-10 · Price/volume signals
- Moves from Yahoo `adj_close`; ex-dates and labels from NSE corporate actions. If on a bonus/split/large-dividend ex-date Yahoo hasn't restated history yet (the day's ratio sits closer to the mechanical factor than to 1), the factor is divided out and only the residual is tested; volume ratio is corrected the same way.
- Triggers per user settings: |move| ≥ threshold (per-stock override), and with volatility-aware on also |z| ≥ 2 (σ of the previous 60 sessions); sector-relative tests stock − sector index; volume ≥ N× the previous 20 sessions' mean.
- Sector index: Nifty sector indices on Yahoo mapped from NSE's `smIndustry` (names without an industry mapped by hand); fallback Nifty 50. Thin Yahoo series (Defence, Healthcare, Consumer Durables) are not used.
- Explanation chain: the most substantive material filing since the previous close (outcome before deck/ad) → the day's largest bulk/block deal → sector or index moved the same way by ≥ half the stock's move → "⚠️ No disclosure explains this move".
- One synthetic `price_volume` event per stock per day; re-threading never deletes them.

## 2026-11-10 · Alerts: dispatch rules
- Per subscriber, per new event on their holdings (and only events after they connected): push category → snooze → feedback (non-critical events scoring < 0.2 after "not useful" stay in the Brief) → quiet hours 22:00–07:00 IST (critical = results, M&A, management change, rating downgrade break through) → budget 5 messages / IST day (critical not counted; overflow `over_budget`, stays in the Brief) → batching (≥ 2 normal alerts in one run → one "N updates on your holdings" message counting once).
- Results are pushed once their numbers are built, or 6 h after the outcome regardless.
- One `alerts` row per (subscriber, event): reruns never resend; quiet-hours holds are reconsidered by the 07:00 IST cron.

## 2026-11-10 · Telegram connection
- Bare `/start` (no token) subscribes the chat to the demo portfolio (equal weights), says so, and sends a test alert (product owner). `/start <token>` uses the holdings the web uploaded; tokens are single-use, 15 minutes, stored hashed. The browser keeps a subscriber secret (stored hashed) to update or delete its server copy; `/stop` deletes everything.
- Webhook calls are rejected unless they carry `TELEGRAM_WEBHOOK_SECRET`. Group chats are ignored.

## 2026-11-10 · Management-change profiles; Tavily optional
- The cheap model copies the profile as printed (roles, periods, qualifications, quotes); code parses years, decides insider (an earlier role at this company or "associated with the company since…"), computes the outgoing person's tenure, and drops anything whose quote isn't in the filing text.
- Web enrichment via Tavily (product owner): snippets only, LinkedIn and social sites excluded, items must quote a snippet, shown as "web · unverified". Without `TAVILY_API_KEY`, or on quota/errors, the card ships from the filing alone (`web_enrichment = unavailable`) and a later run retries.

## 2026-11-10 · Level-0 tags and one-liners
- One cheap-model call per non-results, non-price event (≤ 25 per run): impact, ≤ 20-word reason with a verbatim quote, ≤ 10-word so-what, category facts as printed. Code checks the quote against the PDF text (unverified if absent), parses amounts (no unit → no figure), and decides rating up/down on a coded scale and pledge increase/decrease. Dividend/bonus/split chips come from NSE corporate actions with no model.

## 2026-11-10 · Results: reconciling the XBRL layout with screener (first real run)
- **Context:** the first `results` run (12 symbols, Q2 FY27) gave 4 ✓, 1 pending and 5 "Couldn't verify". None were extraction errors; each was a difference in where a line sits:
  - SEBI's Ind AS XBRL tags `ProfitBeforeTax` *before* the share of associates/JVs and discontinued operations (DIXON, TATASTEEL, TRENT, JUBLFOOD).
  - Screener counts a JV *loss* inside operating expenses (TRENT).
  - HDFCBANK tagged minority interest under `ProfitLossOfMinorityInterest` in Q1 but as `ExceptionalItems` above PBT in Q2 and in the year-ago quarter, so its reported PAT mixes pre- and post-minority figures.
  - BAJFINANCE tags `InterestEarned`, so it had been treated as a bank and lost its NII line.
- **Decision:**
  - **PBT on the card** = XBRL PBT + share of associates/JVs + discontinued ops before tax (the printed consolidated PBT).
  - **Consolidated bank PAT** = PPOP − provisions − tax (+ share of associates), labelled "before minority interest", so every quarter is on the same basis.
  - **Bank template** only when the banking format's own lines exist (interest expended or PPOP).
  - **Cross-check reconciliations:** a figure that doesn't match screener directly may match through one documented reconciliation built only from sourced facts. The check note names it.
    - PBT = PAT + tax.
    - EBITDA + share of associates/JVs.
    - PAT attributable to owners.
  - **New state `partial`:** every comparable line agrees, but some line has no screener counterpart. Example: NBFC interest income and impairment, which make NII and PPOP unverifiable. The badge says "✓ Partly cross-checked" and the note names the lines. "✓ Cross-checked" now means every current figure is verified.
- **Alternatives:**
  - Widening tolerances: rejected; it would hide real errors.
  - Showing reported bank PAT: rejected; its QoQ would be wrong whenever the bank moves the minority line.
  - Defaulting banks to standalone: rejected; it contradicts the consolidated default.
- **Why:** each fix makes the card match what's printed or comparable over time. A genuinely wrong number still fails, and the tests cover that.
- **Known limit:** a consolidated bank's genuine exceptional item would be left out of PAT. The formula on tap says so.
