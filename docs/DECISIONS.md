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
- **Decision:** `finn/llm/` routes `cheap` → Gemini Flash-Lite, `strong` → Gemini Flash; model ids come from env (`GEMINI_MODEL_CHEAP/STRONG`) and are checked against the key's live model list with `python -m finn.llm.check` (verified 10 Nov 2026: `gemini-3.5-flash-lite`, `gemini-3.8-flash`). PDFs go inline (first 2 pages only, cut with pypdf) when a subject is boilerplate. Every call is cached by content hash in `llm_calls`, which is also the token/cost log (USD estimate at paid list price, even though the free tier bills nothing). Router enforces requests/minute (sleeps) and requests/day (counted from the log, Pacific-midnight day like Gemini's), defaults 10 RPM / 400 RPD — conservative because per-model free limits are only shown in the AI Studio dashboard. On quota/error: Groq (`llama-3.1-8b-instant`, text only, optional key — *replaced by `qwen/qwen3.8-27b` on 10 Nov 2026, see below*) → `LLMUnavailable` → filing stays `unclassified` with tier `failed` and is retried next run.
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
- **Surprise:** results: `1 + min(1, |PAT YoY − median of the 4 prior quarters' PAT YoY| / 20 pp)` from screener's 13 quarters. *Update (first real alert):* YoYs above +100% are low-base effects and are left out of the trailing median (TATASTEEL's +319/+825/+147 % had made a +16 % quarter look like a ×2 surprise); fewer than two comparable quarters, or a current YoY above +100 %, → no surprise factor (×1.0); price/volume: `clamp(|z|/2, 1, 2)`; others 1.0. Guidance deviation is a hook for the Promise Ledger.
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
- Per subscriber, per new event on their holdings (and only events after they connected): push category → snooze → feedback (non-critical events scoring < 0.2 after "not useful" stay in the Brief) → quiet hours 22:00–07:00 IST (critical = results, M&A, management change, rating downgrade break through — *corrected 11 Nov 2026, see "Quiet hours: what breaks through"*) → budget 5 messages / IST day (critical not counted; overflow `over_budget`, stays in the Brief) → batching (≥ 2 normal alerts in one run → one "N updates on your holdings" message counting once).
- Results are pushed once their numbers are built, or 6 h after the outcome regardless.
- One `alerts` row per (subscriber, event): reruns never resend; quiet-hours holds are reconsidered by the 07:00 IST cron.

## 2026-11-10 · Telegram connection
- Bare `/start` (no token) subscribes the chat to the demo portfolio (equal weights), says so, and sends a test alert (product owner). `/start <token>` uses the holdings the web uploaded; tokens are single-use, 15 minutes, stored hashed. The browser keeps a subscriber secret (stored hashed) to update or delete its server copy; `/stop` deletes everything.
- Webhook calls are rejected unless they carry `TELEGRAM_WEBHOOK_SECRET`. Group chats are ignored.

## 2026-11-10 · Management-change profiles; Tavily optional
- The cheap model copies the profile as printed (roles, periods, qualifications, quotes); code parses years, decides insider (an earlier role at this company or "associated with the company since…"), computes the outgoing person's tenure, and drops anything whose quote isn't in the filing text.
- Web enrichment via Tavily (product owner): snippets only, social feeds excluded, items must quote a snippet, shown as "web · unverified". *Superseded 2026-11-10 — see "Management web background" below.* Without `TAVILY_API_KEY`, or on quota/errors, the card ships from the filing alone (`web_enrichment = unavailable`) and a later run retries.

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

## 2026-11-10 · Deploy safety: light constants, api-only import check, /version
- **Context:** Render's deploy of 4f05912 failed. The ranking module imported a constant from the results builder, which pulls in the screener scraper (`bs4`), and Render installs only the `api` extras. The previous deploy stayed live, so nothing was visibly broken.
- **Decision:**
  - Shared thresholds live in the dependency-free `finn/constants.py`.
  - `beautifulsoup4` and `lxml` join the `api` extras, because Phase 3 research on Render needs screener anyway.
  - A CI job `api-import` installs only `.[api]` and imports `api.main`.
  - `GET /version` returns Render's `RENDER_GIT_COMMIT`.
  - After every push, `scripts/check_deploy.sh` waits until `/version` matches `HEAD`.
- **Alternatives:**
  - Installing all extras on Render: rejected. It is slower to build, and yfinance and pandas aren't needed there.
  - Lazy imports only: rejected, because they are easy to regress. CI catches it either way.

## 2026-11-10 · Management web background: what counts, and in what order
- **Context:** the first live card (IDEA, Manoj Murali COO) got its only web fact from a news article that restated the filing (the same degrees). That raised whether news may be used at all.
- **Decision (product owner):** the primary-sources rule governs research (pull). Push-side enrichment of a person's professional background may use web snippets, news included. The scope is now spelled out in CLAUDE.md rule 2. Web facts must also earn their place:
  - **Source order:** code classifies each URL and ranks the snippets in this order before the model sees them. The kind is shown on the fact ("web · unverified · Professional profile").
    1. Professional profiles: LinkedIn, theorg, crunchbase snippets. A second Tavily search scoped to linkedin.com finds them, and result pages are never fetched.
    2. Company leadership and bio pages.
    3. Prior employers' sites.
    4. News.
  - **New facts only:**
    - The prompt lists what the filing already states.
    - Code drops restated qualifications and achievements (distinctive-word overlap) and roles at companies the filing already names.
    - Web dates for a filing role are kept only when the filing gives none (`period_citation`).
    - Achievements are a new kind (`PersonProfile.achievements`).
    - A search that only restates the filing ends as `nothing_found`.
  - **Labels:** every web fact keeps "web · unverified", its snippet URL and its verbatim quote, and the quote is checked against the snippet text.
- **Cost:** 2 Tavily credits per appointee (general + LinkedIn-scoped), within the free tier at FINN's volume.

## 2026-11-10 · LLM calls: backoff, then Groq on locally extracted text
- **Context:** Gopika Pant's (IDEA) profile came back empty after Gemini returned 503 "high demand" through its two built-in retries. The Groq fallback has never run (no `GROQ_API_KEY` in any environment yet).
- **Decision:**
  - **Retries:** 5xx, network errors and per-minute 429s are retried by the router with exponential backoff (2, 4, 8, 16 s), and every attempt is logged. A per-day 429 or our own daily budget marks the provider exhausted for the run. The retry loop moved out of the Gemini provider so all providers behave the same.
  - **Text-only providers:** when a provider (Groq) can't take a PDF, the router extracts the PDF's text locally (pypdf, first 12 pages) and sends that. Only a scanned PDF with no text layer stays Gemini-only.
  - **Retrying empty cards:** management events without a profile are re-selected every run until one is built.
- **Alternatives:**
  - More Gemini retries only: rejected, because one busy model would still leave cards empty.
  - OCR for scanned PDFs: deferred; it isn't needed for the filings seen so far.

## 2026-11-10 · Groq fallback model
- **Context:** the first smoke test with the product owner's Groq key returned 404 `model_not_found` for `llama-3.1-8b-instant`, which Groq has retired. The fallback had never actually run.
- **Decision:** the default is now `qwen/qwen3.8-27b`, with `GROQ_MODEL` as an override. On a real-shaped management-profile extraction it gave the same answer as `openai/gpt-oss-20b` with 48 output tokens instead of 221 (gpt-oss spends tokens reasoning), which stretches Groq's free-tier token limits.

## 2026-11-10 · Web facts must be about this person, with dates from the quote
- **Context:** the IDEA rebuild (Gopika Pant, Anil Berera) exposed three ways a web fact could look sourced and still be wrong:
  - A board page's generic "Non-Executive & Independent Director" line was attached to Gopika Pant, though the quote didn't name her.
  - LinkedIn dates came from the model's `period` field. On a snippet that lists several Whirlpool roles, two runs gave 2017–2019 and 2008–2017.
  - An exchange filing found by search (IDEA's postal-ballot notice) was labelled "news".
- **Decision:**
  - **About this person:** a web fact is kept only if the person's surname is in the snippet's title (a profile page) or near the quote.
  - **Dates from the quote:** a role keeps dates only when the years are inside the quoted text, and the prompt requires quoting them. Otherwise the role shows without dates.
  - **Exchange filings:** search results on nseindia.com/bseindia.com are their own kind, "Exchange filing", ranked first.
  - **Passing mentions:** people only mentioned in passing (change "other" and nothing said about them, e.g. the company secretary who signs the letter) are dropped.
- **Why:** a quote that doesn't name the person, or a date the quote doesn't print, is a guess with a URL attached.

## 2026-11-10 · External scheduler: cron-job.org triggers keepalive and ingest; GitHub cron is the backup
- **Context:** GitHub's scheduler fires far less often than the cron says.
  - keepalive (every 10 min) ran on schedule 3 times in ~19 h (08:19, 16:03, 23:44 IST).
  - ingest (30-min filing checks, 16:30 daily, 07:00 alerts) ran once since going live around 16:30 IST, at 22:43 IST, which was outside the filing window, so it did nothing.

  Evaluators can't rely on that. GitHub also disables scheduled workflows on public repos after 60 days without commits.
- **Decision (approved by the product owner 10 Nov 2026; accounts set up by them):**
  - **Keepalive:** cron-job.org (free) pings `GET /ping` every 10 min. That wakes Render and runs `SELECT 1` on Supabase. *Update 11 Nov:* `/health/db` failed cron-job.org's test ("output too large"): the edge Brotli-compresses and chunk-streams it, and `HEAD` returned 405. `/ping` returns plain `ok` with `Content-Length: 2`, `Cache-Control: no-transform` (no edge compression) and GET+HEAD.
  - **Ingest:** cron-job.org calls GitHub's `workflow_dispatch` API for three jobs, all in Asia/Kolkata:
    - filings: every 30 min, 08:00–22:30, Mon–Fri;
    - daily: 16:30, Mon–Fri;
    - alerts: 07:00, every day.
  - **Token:** the call uses a fine-grained token limited to this repository with **Actions: Read and write** only (Metadata: Read-only is mandatory).
  - **`scheduled` input:** scheduler dispatches send `scheduled: "true"`.
    - A scheduled run respects the filing window, and is logged with `trigger = scheduler`.
    - It skips a slot that already ran: filings within 20 min; daily, a successful run since 16:00 IST today.
    - GitHub's own cron runs count as scheduled too.
    - Manual dispatches from the UI still force-run and never skip.
  - The GitHub cron entries stay as a backup; the slot check stops the two from doubling the work.
  - Setup is click-by-click in DEPLOY.md §6.
- **Alternatives:**
  - UptimeRobot for keepalive: works, with a 5-min free interval, but it's a second account and can't send the POST with a body that dispatches need. cron-job.org does both.
  - A Render endpoint that dispatches with a token held on Render: keeps the GitHub token off a third party, but a sleeping Render instance would delay or drop the trigger. That defeats the purpose.
  - Self-hosted cron: there's no always-on machine.
- **Risk:** the token sits in cron-job.org's job headers. If leaked, it can start, cancel, re-run or delete this repo's workflow runs and read their logs (secrets masked). It cannot read secrets or change code. It also expires; the failure emails (after 3 failures) surface that.
- **Cost:** free. Public repo, so Actions minutes are free. About 160 short runs a week.

## 2026-11-11 · Quiet hours: what breaks through
- **Context:** a KALYANKJIL results alert reached the product owner's Telegram at 00:43 IST, from the scheduler's test dispatch of the daily run. The code did what DECISIONS said: it used the feedback-floor "critical" list (results, M&A, any management change, rating downgrade) for quiet hours as well. PRODUCT.md only said "only critical items break through".
- **Decision (product owner):** only **M&A**, a **CEO/MD exit** and a **credit-rating downgrade** break quiet hours. Everything else, results included, is held and goes out with the 07:00 IST run.
  - "CEO exit" means a person whose role names CEO, chief executive or managing director, with change resigned or retired. It's read from the management card, or from the event title before the card is built.
  - Appointments, CFO changes and other management changes are held.
  - The broader "critical" list is unchanged for the feedback floor and the budget exemption: results still go out on their own and don't count against the 5-a-day budget.
- **Check:** none of the 49 stored management events match as an exit. The three titles mentioning a CEO/MD are appointments or an extended charge, so there are no false positives.

## 2026-11-11 · Research (Phase 3): where it runs, what it costs, how it degrades
- **Plan approved by the product owner on 11 Nov.** The full plan is summarised here; details live in the code docstrings.
- **Where it runs:**
  - Builds run on a worker thread inside the Render API (`RESEARCH_WORKER=1`, `uvicorn --workers 1`).
  - The worker claims from `research_jobs` in Supabase with `FOR UPDATE SKIP LOCKED`. A partial unique index allows one active job per ticker; other tickers queue.
  - A 30 s heartbeat runs on its own thread. A job with no heartbeat for 3 minutes is re-queued, up to 3 attempts. A lost database connection re-queues the job instead of failing it.
  - The nightly GitHub Actions run will claim from the same queue.
  - Render's disk is wiped on restart, so every cache lives in Postgres:
    - `research_documents`: URL → sha256 and status.
    - `research_doc_text`: gzipped page text keyed by sha256. The PDF itself is never kept.
    - `research_extractions`: validated facts per (sha256, extractor, prompt version).
    - `dossiers`: the last good dossier.
  - PDFs are streamed to a temp file and read page by page.
- **Screener is cited in research:** its standardised tables are a primary source for the dossier (spec §8). Values read from a row are `verified` and carry a `screener:<section>/<row>/<column>` locator.
  - Computed figures list their inputs.
  - FCF = CFO + fixed assets purchased + fixed assets sold, from the investing-activity schedule (`/api/company/<id>/schedules/`, which robots.txt allows). This equals screener's own Free Cash Flow row in all 10 POLYCAB years.
- **PyMuPDF (AGPL-3.0)** extracts text. That is acceptable because this repo is public; pypdfium2 would be the drop-in replacement.
- **Alternatives:**
  - Builds as GitHub Actions dispatches: rejected. Dispatches are slow to start, and a public build button would spend Actions runs.
  - Supabase Storage for text: rejected, because it means another key and API. Postgres has room: about 0.6 MB per ticker, in a 21 MB database.

## 2026-11-11 · LLM budget for research: per-model quotas, strong fallback chain, Groq only for Ask
- **Free tier (product owner's AI Studio dashboard):**
  - Flash-Lite: 15 RPM / 250K TPM / 500 RPD. The push side peaks at 251 a day.
  - gemini-3.8-flash, Gemini 3 Flash and Gemini 2.5 Flash: 5 RPM / 20 RPD each.
- **Router changes:**
  - Limits, daily counts and exhaustion are per model. A strong-model 429 no longer disables Flash-Lite.
  - The strong tier is a chain: `GEMINI_MODEL_STRONG` → `GEMINI_MODEL_STRONG_FALLBACKS`.
    - `gemini-2.5-flash` returns 404 "no longer available to new users" on this key, so the default chain is 3.8 Flash → `gemini-3-flash-preview`, 40 strong calls a day.
    - The chain never uses Flash-Lite (product owner) and never Groq. Each verdict records its model.
  - Research purposes (`research.*`) have their own daily caps (`RESEARCH_CHEAP_RPD` 220, `RESEARCH_ASK_RPD` 40, `RESEARCH_STRONG_RPD` 60) and 150K of Flash-Lite's TPM, so the push side keeps its share.
  - Daily counts include successful calls only.
- **Per dossier:**

  | Case | Cheap calls | Strong calls | Measured |
  |---|---|---|---|
  | First-time dossier | 8 (one per transcript) + 1 (annual report) | 2 or fewer | POLYCAB: 104K tokens in / 68K out, ≈ $0.20 at list price |
  | Cached dossier | 0 | 0 | |
  | New transcript | 1 | 2 | |

  The cap is 15 first-time dossiers per IST day (`RESEARCH_DAILY_BUILDS`). Pre-warming covers only the 4 demo tickers (product owner).
- **Quota out mid-build:**
  - The job parks as `waiting_quota` until the next Pacific midnight (13:30 IST in winter).
  - Sections already built stay published. The ledger says "Read N of M calls — the rest after 13:30 IST".
  - If every strong model is out, qualitative verdicts and synthesis show "Building · resumes after 13:30 IST quota reset".
- **Groq can't take a transcript:** the free-tier qwen3.8-27b allows 8K tokens a minute, and a transcript is 13–17K tokens. It serves Ask only. The router skips Groq for any request estimated above 6K tokens.
- **Other changes:**
  - `LLMRequest.document_text` is sent to the model, but only its hash is logged in `llm_calls`.
  - Truncated output (`MAX_TOKENS`) is an error, never parsed.
  - Flash-Lite rejects `thinkingBudget: 0`, so research leaves thinking unset on Flash-Lite.

## 2026-11-11 · Promise Ledger rules (code)
- **MAP (Flash-Lite, one call per transcript):**
  - The model copies guidance, actuals, analyst questions, segments, capex and risks. Each item has numbers as printed, a verbatim quote and a page.
  - Code validates item by item and finds each quote in the page text. The search order is the claimed page, then ±1, then pages holding the quote's rarest words, after normalising line-break hyphens, quote marks and whitespace.
  - A quote that isn't found is re-anchored to the sentence on the claimed page (±1) that contains most of the quote's words and the same number. Otherwise it is dropped and counted.
  - The item's own number must be printed in its quote.
  - Analyst and moderator statements are never guidance.
  - Facts are stored per document hash and prompt version. `VALIDATOR_VERSION` lets checker fixes re-validate cached model output without a new call.
- **Periods:** resolved in code from what the model read (`fy`, `quarter`, `this_fy`, `next_fy`, …) and the call date.
  - The company's fiscal year-end comes from screener.
  - "Next year" said within two months after a year-end is ambiguous, so it can't be scored.
  - Medium-term or unspecified targets get no date.
- **Threads:** metric key, measure, segment, unit family, currency, scope and period.
  - An unspecified basis joins the single specified group.
  - Qualitative statements stay one per thread until the strong model links paraphrases.
- **Delivered figure:**
  - Screener only for a whitelist of rows, with INR or unspecified currency and a matching scope: revenue, revenue/PAT YoY growth, PAT, EBITDA margin when the quote says EBITDA, and GNPA/NNPA by quarter. INFY's "operating margin" is EBIT margin, so it is never scored from OPM %.
  - Otherwise, the earliest later-call actual with the same key, measure, period, unit and basis, with its quote.
  - Constant currency is never compared with reported growth. Loose keys (headcount, capex, other…) also need a shared word in the metric names: "fresher hiring" is not "total headcount".
- **Verdicts** (`compare`, unit-tested):

  | Target | Kept when |
  |---|---|
  | Point | Within ±0.5 pp (%), ±2 days, ±2.5 % (money) |
  | Range / threshold | Within its bounds, plus the reported figure's rounding (±0.1 pp, ±0.5 %) |
  | Beyond the favourable bound | Kept ("beat"), using the metric's direction (code dictionary: credit cost and NPAs lower-is-better; capex neutral, so off-plan either way) |
- **Revisions:**
  - An unfavourable change or a later date → **goalposts moved**. That is the verdict, even if the lower target is then met.
  - A favourable change → **↗ raised**. A tighter range at the same midpoint → **narrowed**.
  - Scoring uses the last target given before the period ended (product owner).
- **Not yet due / can't score:**
  - **Not yet due:** the period isn't over, or results aren't due yet (60 days after a quarter, 75 after a half, 90 after a year).
  - **Can't score:** no date, a benchmark-relative target ("1.5–2x industry growth"), or no delivered figure in the sources read.
  - Neither counts toward credibility.
- **Quietly dropped:** only when there is no delivered figure, there are at least 2 readable later calls, and a lenient whole-word search for the promise's terms and the metric's synonyms finds nothing in any of them. Worded "Not mentioned in the N calls since the Q1 FY26 call". The model can never assert it.
- **Credibility:**
  - Formula: kept ÷ (kept + missed + goalposts moved + quietly dropped).
  - Code and model verdicts both count, with the split shown (product owner). Hidden below n = 5.
  - Trend compares promises settled in the last 4 calls with earlier ones. It is shown only when both halves have 3 or more and the difference is 15 pp or more.
- **Analysts and drivers are counted in code:**
  - Pressure points are themes asked in 2 or more calls, citing up to 3 questions.
  - Drivers are scored per label as 2 × guidance count + question count; the top 3 are suggested.

## 2026-11-11 · JUDGE and REDUCE (strong model), and how credibility is shown
- **JUDGE (strong call #1)**:
  - Candidates are qualitative promises plus undated numeric ones.
  - BM25 (`finn/research/bm25.py`, no vector database) retrieves the 3 best passages from later calls for each candidate.
  - Code-enforced rules:
    - A verdict must quote a passage verbatim, and the quote is checked.
    - The evidence must come from a later call than the promise, so every model verdict cites both calls.
    - **kept/missed from the model count only for qualitative promises.** Despite the prompt, the model called "utilisation 85.8%" kept against 83–85%. For numeric targets it may only flag a revision (goalposts moved or raised).
    - The model can never assert "quietly dropped".
    - Its "not yet due" or "can't score" never overrides code.
  - Board and personnel housekeeping (an interim chairman's tenure, AGM dates) is filtered out before the ledger.
  - Qualitative restatements across calls merge into one thread.
- **REDUCE (strong call #2)**: snapshot lines, a trajectory line, and 3 bull and 3 bear points, written from numbered facts only (computed figures, ledger verdicts, analyst themes, risks and capex from the latest call).
  - Numbers appear as `{F#}` placeholders, filled in code from figures with their units.
  - A typed number survives only if a cited fact's line prints it. A spelled-out quantity drops the sentence.
  - Citations come from the cited facts. Dropped sentences are counted in `quality.claims_dropped`.
- **Cost:**
  - Each strong call caps thinking at 1,024 tokens. Unbounded thinking truncated a 6,000-token answer.
  - Judge and reduce cost ≈ $0.005–0.012 per dossier at list price.
  - The prompts contain no date, so an unchanged dossier hits the cache and spends no strong call.
- **Router:**
  - `gemini-3.8-flash` was returning 503s and timing out after 3 minutes, even on a two-word prompt.
  - A strong model with a fallback after it now gets 2 attempts, then is skipped for 10 minutes, so `gemini-3-flash-preview` answers at once.
  - The push side keeps full retries on Flash-Lite before Groq.
- **Credibility display (product owner):** the "kept of n" tally is always shown with the verdict list. The % score and trend need n ≥ 5.
  - With honest rules no demo ticker reaches 5 scored promises (PERSISTENT 2, INFY 4, BAJFINANCE 4, POLYCAB 1).
  - The rest are not yet due or can't be scored:
    - Targets for FY30 or the medium term.
    - Benchmark-relative guidance.
    - Full-year figures that appear in the deck but not in the call.

## 2026-11-11 · Afternoon: acceptance on unseen tickers, deck lookup, direction and tolerance rules
- **Unseen-ticker draw**: `evals/research/draw_unseen.py`, seed 20261111, logged. Pool: NSE EQ minus every symbol already built or tested. One bank/NBFC by company name (the equity list has no industry field). One non-financial outside the Nifty 100 (NSE archive list, committed). Results are in PLAN.md.
- **Not promises**: ESOP and share-based-payment cost schedules are excluded alongside board housekeeping. LAXMIDENTL had two such schedules marked "quietly dropped".
- **Deck lookup** (product owner's step 3):
  - Covers promises that are "can't score" only because the calls never printed the delivered figure.
  - FINN reads the investor deck for the quarter that closes the period (screener's PPT link), up to 3 decks per build, with one Flash-Lite call per deck asking only for the missing metrics.
  - Checks:
    - The quote must be on the cited page, the number must appear in the quote, and the metric's name must be in the quote.
    - Fallback for decks whose table rows PDFs split into columns: the name and the exact number within 250 characters on the page, stored as that verbatim span.
  - A deck figure scores only the promise that requested it. It never adds promises, and never counts as a later call for quietly-dropped or the trend.
  - Cached per (deck sha, sorted list of requested metrics).
  - BAJFINANCE: 11 of 12 waiting figures found in 2 decks, and the tally went from 1 of 4 to 8 of 13.
- **Bound tolerance follows the target's printed precision**: half a unit of its last digit. "40–50 bps" is ±0.5 bp, "1.85–1.95%" is ±0.005 pp. It is never above the old caps (0.1 pp, 0.5 % relative). Point targets keep their ±0.5 pp / ±2.5 % allowance for spoken rounding.
- **Direction when the metric key has none**:
  - Code reads the metric's own words: cost, loss, NPA, debt, attrition or days mean lower is better.
  - For an unsigned change, "improvement/expansion/saving" means more is better, and "impact/headwind/drag" means less is better.
  - With neither, an off-range result is "can't score" with that reason, never a miss.
- **Delivered figures are shown as printed** ("7.54 %", "43 bps"), not rounded for the reason line.
- **Ledger header**: `next_test`, `next_test_label` ("FY27 results"), `next_test_on` (period end + results lag) and `next_test_count`, plus `decks_read`. The n ≥ 5 threshold is unchanged.
- **Ingest**:
  - A Gemini content refusal (`promptFeedback.blockReason`) is recorded as "model refused" and not retried every 30 minutes.
  - JSON written to Postgres drops NUL characters. One filing's NUL made every run's tagging step fail.

## 2026-11-12 · Phase 4 frontend: plan amendments (product owner)
- **Approved with amendments, 11 Nov evening:**
  1. Push and verify the deployed site after the Brief and after the Ledger, not only at the end.
  2. No empty tabs: Portfolio lists the holdings with their latest Brief event; Rules has Connect Telegram and Reset; the Brief has a visible "Connect Telegram" entry.
  3. Drivers queue: read today's Flash-Lite count from `llm_calls` first (failed attempts count), cap a run at 50 calls, and skip it if fewer than 150 would stay free afterwards.
  4. Strong models were out of quota until 13:30 IST: BuildProgress explains that and shows the ready sections meanwhile; a first-time build asks for one-tap confirmation.
  5. Verify the landing iframe on the deployed site (no X-Frame-Options conflict).
  6. Screenshots: 375 px light and dark for Brief, Research, Ledger and the provenance sheet; 1280 px for the landing only; the time saved goes into loading, error and stale states.
- **Deviation:** the first push came after Research and the Ledger rather than after the Brief, because amendment 2 ruled out shipping an empty Research tab.

## 2026-11-12 · Visual direction
- **Decision:** a printed financial page, not a dashboard.
  - Ink on warm paper (`#F7F6F2` / `#0F0F0E`), hairline rules between full-bleed rows, no shadows, gradients or decorative colour.
  - Newsreader (serif) for what you read: titles, headlines, claims and quotes. Geist for what you scan. Tabular numerals everywhere.
  - Colour only for signal: impact, verdicts, verification and warnings. Moves stay ink, with ▲/▼.
  - Dark mode follows `prefers-color-scheme` through a media-query variant, so there's no script and no flash.
- **Symbols:** the spec's ✅ ❌ ↘ ↗ 🔇 / 🟢🔴🟡⚪ states are drawn as monochrome glyphs in signal colour (✓ ✕ ↘ ↗, a muted-speaker icon, a 6 px dot plus a word), not system emoji. Same states; renders the same on every phone.
- **Headlines lead with meaning:** a results card's serif headline is its code-written line ("Revenue +46.7% YoY; margin −104 bps"). A management card names the person and role from the filing. Other cards use the exchange subject without its "Category:" prefix, with the so-what underneath.
- **Tappable numbers:** a dotted underline (amber when unverified). Every number opens a sheet with its document, page, verbatim quote and `url#page=N`; computed figures show their formula and inputs. Ledger delivered figures show as printed ("119.3 million", "7.54%").

## 2026-11-12 · First paint < 1 s while Render may be asleep
- **Decision:** the app shell is prerendered static HTML on Vercel's edge, and nothing on the critical path waits for Render. Brief data comes in this order:
  1. This phone's last Brief for the same holdings, rules and window (localStorage, one Brief kept at a time: a 7-day Brief is about 1 MB uncompressed).
  2. On a first visit with the demo portfolio: `GET /api/brief/demo`, a route handler that replies with `Vercel-CDN-Cache-Control: max-age=300, stale-while-revalidate=86400`. Only successful answers are cached. Measured on the deployed site: `MISS` then `HIT`, 55–160 ms from the edge.
  3. Nothing within 0.4 s of hydration: the saved showcase day (prefetched at load), under a banner. Live data replaces it in place if it lands before the first touch or scroll; after that a "Show live" pill appears, so content never swaps under your thumb.
     - Why a fallback at all: Vercel's edge cache is per region and is emptied by every deploy, so the first visitor in a region after a deploy waits for Render. Measured: 4.1 s cold vs ~0.1 s warm.
  4. Always: `POST /api/brief` with holdings, rules and queued swipes. On failure the last copy stays, with "couldn't refresh · retry".
- **Stale:** the feed is flagged when its last success is more than 2 h older than the most recent 30-minute check slot that should have run (08:30–22:00 IST, weekdays).
- **Freshness fix:** `data_as_of` now means the oldest NSE check among the *requested* holdings. Before, two one-off test tickers made every Brief look a day behind.
- **Alternatives:** a server-rendered Brief inside `use cache` (a cold Render at build time stalls or fails the build); a skeleton until Render answers (fails the "populated in < 1 s" bar on a cold start).

## 2026-11-12 · Brief contract, est. time saved, season strip, feedback
- **Contract:** `BriefRequest` / `BriefResponse` are Pydantic models exported to `types.ts`. The response adds:
  - `hidden_items` (the newest 300; every one still opens its PDF);
  - `counts`;
  - `season`;
  - `rules`;
  - `window`;
  - `showcase`.
- **est. time saved** (`finn/cards/counts.py`, shown with its formula on tap and always labelled "est."):

  est. = 30 s × routine filings hidden + 3 min × material filings in the window − the Brief's read time (30 s per card, 10 s per one-liner or chip); nearest minute under 10 min, else nearest 5; never below 0.

  It's calibrated so the spec's "41 hidden · ~35 min" holds for a small Brief. "Material filings" counts the distinct filings behind the shown cards that were filed inside the window.
- **Season strip** (`finn/cards/season.py`): shown from a quarter's end until 60 days after it (75 for Q4). It gives reported/total, cross-checked count, PAT YoY up/down and EBITDA margin YoY up/down, plus a per-holding scoreboard sheet.
  - A card that failed its cross-check counts as reported but contributes no numbers.
  - "Met guidance" is left out until results cards carry the ledger's guidance line.
- **Feedback stays in Python:** after its 5 s undo window, a swipe is queued on the phone and sent as `feedback[]` with the next Brief request, which fires immediately. `apply_feedback` applies it, and the response's `rules` replace the phone's copy. No ×0.8 maths in TypeScript.
- **Scopes:** "this stock" → `stock_category`, "all stocks" → `category`, "just this one" → `event`. Dismissing the sheet means "just this one". Reviewed (swipe right) changes no weight.

## 2026-11-12 · Showcase replay is a frozen Brief
- **Decision:** `python -m jobs.snapshot --brief 2026-10-30` ranks the snapshot day's events for the demo portfolio and writes `web/public/showcase/brief.json` (committed; 16 KB gzipped).
  - Events are used as stored now, with their built card details. Timelines are cut at the end of that IST day, and the season strip is computed as of that day.
  - It works with Render and Supabase both down. It isn't re-ranked live. Swipes made in the replay still create real rules, applied to the live Brief.
- **Alternatives:** a `/brief?showcase=` server mode. The snapshot's events carry no card details, so a replay built from it would lose every results table.

## 2026-11-12 · Holdings import and quantities
- **Decision:** paste or CSV, one per line. `SYMBOL 6%` is a weight; `SYMBOL 120` is a share quantity. Every symbol is checked against NSE's equity list.
  - Until prices are wired (Friday's `/portfolio`), quantity-only holdings split the weight the others leave equally. The UI says so.
  - Only symbols and weights go to `/brief`; quantities never leave the phone.

## 2026-11-12 · Drivers for the holdings without the strong quota
- **Decision:** `python -m jobs.research drivers` runs in the foreground (locally or from Actions), not on Render's queue, so no new job reason and no worker change.
  - Discover → the latest 3 transcripts → Flash-Lite MAP (the same cache as full builds) → `apply_ledger` in code → the drivers section saved to `drivers` (migration 0005).
  - No dossier is published: Research still shows the normal build for that ticker, which then reuses the cached MAP output.
- **Guards:**
  - `CheapOnly` wraps the router and raises `StrongTierBlocked` on any strong request.
  - The run stops at its call budget.
  - Before a run it reads today's Flash-Lite count from `llm_calls` (failed attempts included). The budget is 50 calls, and only if 500 − used − 50 ≥ 150; otherwise it skips.
  - Holdings are taken largest first; those that already have drivers are skipped.
- **Read path:** `GET /research/drivers?symbols=` returns a full dossier's drivers when present, else the drivers-only row. The web proxy passes a query string only to this route; `?force=true` on `/build` stays blocked, because it would spend quota.

## 2026-11-12 · Research UX rules
- **Builds:** never started by opening a page. "Research X" is a one-tap confirmation that says what it reads, how long it takes, and that summaries wait for the 13:30 IST quota reset when the strong models are out.
- **BuildProgress:** polls every 3 s, or every 60 s while parked for quota. It names the paused steps and the sections already readable.
- **Fallback:** if the API can't be reached, the 4 demo tickers fall back to their fixtures, labelled "Saved copy from 11 Nov 2026".
- **Section states:** building + `not_built_yet` (red flags, exchange data) renders a quiet "Coming soon"; `llm_quota` shows when it resumes; other reasons are explained in plain words.
- **Ask (until Friday):** the bar is always visible. Its 3 context suggestions per screen jump to the section, ledger filter or card that answers them. Free text says it arrives with the next release. `lib/ask`-style wiring is one place: `components/shell/ui-store.ts` `setAskContext`.

## 2026-11-12 · Readable Open links (product owner's bug: a figure opened raw XBRL XML on a phone)
- **Context:** results figures are read from NSE's XBRL instances, and their citation pointed at the `.xml`. On Android Chrome, Open showed a wall of tags. An audit of every stored link (cards, filings, dossiers) found the same problem in three more places:
  - 22 results impact reasons;
  - 45 board-meeting filings with only a prior-intimation XBRL link, shown as source chips on results, what-to-watch and one-liner cards, and in the hidden drawer;
  - one KMP `.zip` attachment, and 3 one-liner chips pointing at `-`.

  Filing PDFs, BSE transcripts and decks, Yahoo price history and web profiles were already readable.
- **Decision: a figure's Open goes to a human-readable document, in this order:**
  1. **Results PDF**, the outcome announcement in the card's own event thread, at the page with the statement for the card's basis, as `url#page=N`. The page is found in code (`finn/extraction/results/links.py`):
     - a candidate page prints ≥ 3 statement line items;
     - it scores for naming its basis in the heading, and loses for naming only the other basis;
     - it scores most when the card's revenue (or a lender's interest line) is printed on it in crore, lakh or million.

     Previous- and year-ago-quarter figures open the same PDF page, titled "… · Q1 FY27 column". Pages are cached in `results_pdf_pages` (migration 0006). Results PDFs may be up to 32 MB: board outcomes bundle scanned auditor reports, and 18–25 MB is common.
  2. **NSE's iXBRL (HTML) view** of the same instance, when there's no results PDF or no statement page. It's stored on `results_filings.ixbrl_url` from the integrated-filing list.
  3. **Raw XBRL** only as a small secondary "Raw XBRL (machine-readable)" link (`Citation.raw_url`), kept for auditability.
  4. **Screener cross-check** (`Citation.check_url`): the company page's `#quarters` section. Every screener citation also lands on its own section (`#profit-loss`, `#cash-flow`, …) from its locator.
- **Filing links everywhere** (`finn.citations.filing_doc`): the attached PDF, else NSE's iXBRL view (board-meeting rows keep it in `raw`), else raw XBRL labelled as such. `-` and empty links are dropped. ZIPs are labelled "ZIP file".
- **Contract:** `Citation.url` now means "the human-readable document to open". `source_type` still says where the value was read (`xbrl`), and the XBRL element stays in `locator`. Added `doc_kind`, `raw_url` and `check_url`, all optional, so stored data stays valid.
- **Provenance sheet:**
  - one row per document, with one Open button and the figures and XBRL elements it supplied listed underneath (previously the same XBRL file appeared once per input);
  - the button says what opens and shows the page ("Results PDF · p.3", "iXBRL view", "Raw XBRL"), because mobile PDF viewers often ignore `#page`;
  - figures never wrap mid-value; the label column wraps.
- **Where it runs:** the page finder needs the PDF, and NSE archives are blocked from Render, so new pages are found by the results job on GitHub Actions. Render and local runs reuse stored pages.
  - Existing cards were relinked by `python -m jobs.results --relink`: same numbers, new links, `detail_at` unchanged. It ran through the new `backfill.yml` workflow, which starts from `workflow_dispatch` or a committed request file under `backend/data/backfills/` (no API token on this machine).
- **Order of deploys:** Render had to serve the new contract before any card carried `doc_kind`, because the API's models forbid unknown fields. That was checked through the proxy's new `GET /api/version`, and the backfill was triggered afterwards.
- **No model calls:** page finding and relinking are code only.
- **Alternatives:**
  - Render the XBRL as an HTML table ourselves: rejected, because a reader should see the company's own document.
  - Link only the iXBRL view: rejected; it's readable, but it isn't the statement as the company printed it.
  - Leave XBRL and label it: rejected; it's still unreadable on a phone.

## 2026-11-12 · Phase 5 plan: amendments (product owner)
- **Order:** classification fixes → blind held-out set → Ask → cost report → results-extraction eval (A) → ledger table (B) → nightly refresh → fixes → robustness → walkthrough (C) → smoke (D) → live push check (E) → known limitations (F), then Portfolio/Rules → PWA → snapshot. Proof before new screen features. Time-box: Fri 13 Nov 14:00 IST; whatever isn't done moves below the cut line.
- **smoke.yml** only GETs cached data: it never triggers a build or an LLM call. The walkthrough's "research a never-built ticker" step runs only when started by hand, and its calls are counted in COST.md.
- **Driver boost** applies only to drivers the user confirmed. "Why #N" names the matched driver ("affects: Margins"). A weak keyword match gives no boost.
- **Snapshot re-capture** regenerates every copy together (DB, git JSON, web showcase file) and updates the banner date.
- **Deliberately left out** (to list): annual-report red flags, NSE on-demand dispatch / exchange-data section, web push, with reasons.
- Defaults accepted: Ask 8 per visitor per day; nightly refresh piggybacks on the first scheduled filing run at or after 22:00 IST; red flags and exchange data hidden instead of "Coming soon".

## 2026-11-12 · Classification: results press releases titled with the numbers (dev set only)
- **Context:** PLAN's persistent miss: "Persistent Achieves $452.4M Revenue in Q1 FY27 with 16.1% YoY Growth" fell to `press_release` because the subject never says "results".
- **Decision:** rule `results_press_release_titled`: a press-release subject that names a period (Q1 FY27, 2QFY2027, "quarter/half year … ended") **and** a P&L word (revenue, profit, PAT, EBITDA, margin, net income, earnings) → results / presentation. Production volumes ("2QFY2027 Production and Delivery Volumes") and operating milestones ("1 GW Module Production in Q2 FY27") carry no P&L word and stay press releases.
- **Measured:** across all 947 stored filings the rule matches 3, all genuine results press releases (EICHERMOT Q1, TATASTEEL Q1 and Q2); they were re-labelled and re-threaded. Dev set: rules only 96.5% of decided (55/57), full ladder 100% (60/60). The rules are now **frozen** for the held-out run. The remaining facility-opening case is labelled `press_release` by an earlier decision, so it is not a miss.

## 2026-11-12 · Ask: one company, facts + BM25 passages, Flash-Lite, cached, capped per visitor
- **Retrieval (code):** the dossier's numbered facts (the list REDUCE writes from: computed figures, ledger verdicts, analyst themes) plus the 6 best BM25 passages over the company's read transcripts and decks in `research_doc_text` (newest 12 documents). No vector store, no new documents fetched, so an answer never waits on a download.
- **Model:** one cheap call (`research.ask.v1`: Flash-Lite, Groq fallback for requests under 6K tokens; never the strong tier). The prompt forbids outside knowledge and calculation, and says "found=false" is a valid answer.
- **Code checks:** cited fact ids must exist; passage quotes must be in that passage's text; **every number in the answer must be printed in a cited fact or quote** (period labels like FY27 ignored), otherwise the answer is withheld as "Not found in sources" with reason `unsupported_number`. No surviving citation → "Not found in sources".
- **Cost guards:**
  - `ask_answers` caches per (symbol, normalised question, dossier version); a rebuilt dossier asks again. Cache hits cost nothing and don't count.
  - `ask_usage`: 8 new answers per visitor per IST day (`ASK_VISITOR_DAILY`). The visitor is `sha256(salt | IP | IST date)` truncated, so it can't be reversed or linked across days; the IP comes from Vercel's `x-forwarded-for`, forwarded by the proxy as `x-finn-client` on `/ask` only.
  - Someone calling Render directly could spoof that header; that only dodges the per-visitor cap. The router's `research.ask` lane (40/day across everyone, `RESEARCH_ASK_RPD`) is the hard ceiling, and it is separate from the push side's quota.
- **No dossier yet:** `unavailable / no_dossier` → "Research X first". Ask is not offered on the Brief/Portfolio (no company in scope); the suggestion chips there still jump to the answer.
- **Contract:** `AskAnswer` gains `reason`, `cached`, `remaining_today` (TypeScript regenerated).
- **Alternatives:** whole transcripts in the prompt (long-context, like MAP): 15K+ tokens per question would eat Flash-Lite's TPM shared with builds and rule out the Groq fallback; embeddings: a second provider and an index to keep fresh for a 40-a-day feature.

## 2026-11-12 · Nightly research refresh; summary reuse
- **Trigger:** no new scheduler entry. The ingest workflow's `pick` step marks `refresh=true` on a scheduled filing run at or after 21:55 IST, and a separate `research-refresh` job (own concurrency group, so it never blocks filing checks) runs `python -m jobs.research refresh --scheduled`, which runs once per IST day from 22:00 (`ingest_runs.job = research_refresh`). Weekdays only, like the filing slots. Manual: dispatch `job=refresh`.
- **What it rebuilds:** the 4 demo tickers always; portfolio holdings only when they already have a dossier (first-time builds stay demo-only, Phase 3 budget). Each goes through the normal build queue (priority 60, after any visitor's build at 10).
- **Model calls only for what changed:** transcripts and MAP extractions are cached by content hash; JUDGE's prompt has no date (router cache); **REDUCE is skipped when `synthesis_hash` is unchanged** — a hash of the document set (URL + content hash + status, plus MAP/JUDGE/REDUCE prompt versions) and every promise's verdict and revision. REDUCE's facts include the day's market cap, so before this every rebuild re-ran it. Screener tables and computed sections still refresh nightly at no model cost.
- **Kept summary is honest about its age:** the snapshot's `as_of` stays at the day it was written.
- **DB size guard:** the refresh skips (and logs a failure) above 400 MB (Supabase free tier: 500 MB).
- **Backfill:** `doc_set_hash` / `synthesis_hash` were never written before; they were computed for the 7 stored dossiers so tonight's first refresh doesn't spend 7 strong calls on unchanged summaries.

## 2026-11-12 · Results reconciliation: excise, PBT layouts, operating EBITDA, mismatch as a card state
- **ITC / RELIANCE revenue (PLAN item):** both statements print gross "Revenue from operations" and carry excise duty as an expense line (ITC ₹10,309.77 Cr, RELIANCE ₹2,260 Cr in Q2 FY27). Screener's Sales = revenue − excise (ITC 20,268.63 vs 20,269; RELIANCE 330,601 exactly). The XBRL itemises it as an `OtherExpenses` value in its own dimensional context with `DescriptionOfOtherExpenses = "Excise Duty"`; the parser now keeps those items (`OtherExpensesItem` + `meta.other_expense_items`) and the cross-check reconciles **revenue − excise duty**. The card keeps the revenue as printed (the primary source). 98 stored instances were re-parsed from `xml_gz`; no re-download.
- **PBT follows the statement's layout:** companies print PBT before the JV share (RELIANCE: 38,613, share added after tax) or after it (TATA POWER: 2,179.85 incl. JV share, regulatory deferral and exceptional items; SEBI's ProfitBeforeTax element there is 1,442.91). Candidates, all from sourced facts: PAT + tax → element + JV share (+ discontinued) → element. The build shows the candidate screener's Profit before tax agrees with; unconfirmed, PAT + tax (exact whenever the JV share is pre-tax and nothing is discontinued).
- **Operating EBITDA = revenue − (total expenses − finance costs − D&A)** when total expenses is tagged (else the old PBT-based route). Same value for an ordinary statement, but immune to where a filing places "PBT before exceptional items" (regulatory deferral, JV share).
- **States:** a disagreement only in the previous or year-ago quarter now makes the card **partial** (numbers shown; that quarter's figures and the QoQ/YoY resting on them unverified, note says why) instead of hiding the card. TATA POWER: every Q2 figure matches screener; screener's Q1 operating profit (3,860) is 153 below the company's own Q1 columns (4,013.29) — the Q1 regulatory-deferral movement — while its Q2 excludes the deferral, so we show the company's figures and mark Q1 unverified.
- **A mismatch is a card state, not a run failure** (`results.mismatch_cards` in the run stats). It used to mark every 30-minute run `partial`.
- **Measured:** after a full `jobs.results --rebuild`: 12 cross-checked, 2 partial (BAJFINANCE: NII/PPOP have no screener row; TATA POWER), 1 mismatch (ALKEM: PDF fallback, its Q2 XBRL isn't on NSE yet; the sanity check hides the numbers). Results eval vs the PDF: 57/60 fields.
- **Known limitation:** comparatives restated in a later filing (TITAGARH's Sep 2025 column, restated for discontinued operations) still come from the earlier XBRL as first reported, so that YoY differs from the PDF. Screener also shows the original figures, so the cross-check can't catch it.

## 2026-11-12 · MAP split on truncation; confirmed-driver boost in /brief
- **MAP split (IDEA, RELIANCE):** when a transcript's MAP answer is cut off at the 16K output limit, the same pages are sent again as two halves (and halves of those, at most twice), each with absolute `[[p.N]]` markers; the halves' items are merged and validated against the whole transcript, so quotes check exactly as before. Reactive, not by length: IDEA's 45K-character call overflowed while 100K-character INFY calls didn't. The whole-transcript text is byte-identical to before, so existing cache entries still hit. Result: IDEA (Leverage, Capacity, Customers) and RELIANCE (Capacity, Margins, Growth) now have drivers.
- **Driver boost (×1.5, PRODUCT §5 Level 1):** the phone sends its confirmed driver ids (`BriefRequest.drivers`, only for held symbols); `finn/ranking/drivers.py` matches events by rule, no model, strong evidence only:
  - results cards whose numbers are shown: Revenue/NII → Growth, EBITDA margin → Margins, PAT → Profit;
  - category: capex → Capex/Capacity, credit rating → Leverage, dividend/bonus → Payout;
  - concrete words in the headline or so-what for concrete drivers (order book/orders/letter of award, capacity/commissioning, deposits, asset quality, debt/borrowings…), whole words only. Generic words (growth, share, investment, costs, margin outside results) never boost (product owner: "if a keyword match is weak, don't boost").
- "Why #N" names it ("affects: Margins — a driver you're watching (×1.5)") and the card shows the 👁 "affects: Margins" tag. Suggested-but-unconfirmed drivers never boost. The cached Brief's signature includes the confirmed ids, so confirming a driver re-ranks immediately.

## 2026-11-12 · Portfolio: prices, status dot, calendar, scoreboard; editable alert rules
- **`POST /portfolio`** (symbols + weights only, nothing stored, code only): last close, day change and 1-month change on adjusted closes, a ~23-session sparkline, "Ex today" from NSE corporate actions, a status dot, the next 60 days' board meetings (results meetings win over their plain "intimation" duplicate) and ex-dates, and the results-season scoreboard (the Brief's `season_strip`). Symbols FINN doesn't track show "No prices yet" and a grey "No data" dot. The phone keeps the last good answer per holdings set.
- **Status dot rule (decided in code, shown with its reason):**
  - 🔴 *under pressure*: a material event (results, M&A, management change, litigation, credit rating, pledging) tagged negative in the last 30 days, or down ≥ 15 % over ~1 month;
  - 🟡 *watch*: any negative or mixed event in 30 days, a price move no disclosure explains in the last 7 days, or down ≥ 8 % over a month;
  - 🟢 *intact* otherwise.
  It uses only what FINN already computed (Level-0 tags, price signals); no model call. On today's demo portfolio: 3 under pressure (all litigation tagged negative), 9 watch, 6 intact.
- **Rules are editable**: price-move %, volume multiple, volatility/sector toggles, daily budget, batching, quiet hours, push categories, snoozes (add 1 day / 1 week, unsnooze). Stored on the phone; when Telegram is connected, loaded from and saved to the server copy (`PUT /subscriptions/me`, now with `snoozes`), debounced, with a visible sync state. Connecting Telegram uploads this phone's edited rules. Per-stock price-move overrides stay in the contract but have no editor yet.
- **Robustness fixes found by the random-ticker run:** a deck "quote" with no words (only a number) divided by zero in the re-anchor step and failed TATACAP's whole build; the re-anchor now refuses it, and any error in the optional deck lookup now skips that step instead of failing the dossier.

## 2026-11-12 · Walkthrough findings: stale build panel; a busy model parks the build
- **Stale "Building" panel (client):** when a job ended, the poll refetched the dossier and stopped. If that one refetch failed, the screen kept the old response, whose job said "running", with no poll behind it (BALKRISIND: built in 2.5 min, panel still "running" 14 min later). Now the job's own status is written first-hand from the job poll, and a failed final refetch is retried.
- **Busy model ≠ out of quota (server):** Flash-Lite answered 503 "high demand" to all 5 attempts for BALKRISIND's first transcript; the build published a "partial" dossier with an empty ledger. A transient MAP failure now parks the job as `waiting_quota` for 15 minutes with `error = "model busy: …"` (at most 4 attempts, then it publishes what it has), and BuildProgress says "The AI model is busy right now — FINN retries at HH:MM" instead of "quota used up".
- **Dossier page waits for a waking server by itself:** a "server is waking up" error (502/503/504/timeout) retries every 10 s for about 5 minutes. Before, the page sat on "Try again" (walkthrough, MAANALU, during a Render redeploy). The Brief already retried.
