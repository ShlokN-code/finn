# Plan — backlog of agreed items

Work agreed in sessions but not yet built. Tick an item (`- [x]`, with the commit hash) when it is done and verified; don't delete it.
Product scope lives in PRODUCT.md; reasons live in DECISIONS.md. The phase breakdown is kept outside the repo — each phase's prompt arrives at the start of its session.

## Start of next phase

- [x] **Fix `--font-sans`.** `web/app/globals.css` (written by `shadcn init`) sets `--font-sans: var(--font-sans)`, a self-reference, so text falls back to a serif font. Point it at the Geist variable from `app/layout.tsx` (`--font-geist-sans`) and check on a phone. — `a747b11`; verified on the deployed app at 375 px: body font resolves to Geist.

## Research dossier — on-demand NSE data via GitHub Actions dispatch

**Cut in Phase 5: not built.** The README lists it under "Deliberately left out". The items below stay as the design.

Background: NSE returns 403 to Render; GitHub-hosted runners are not blocked (DATA_SOURCES.md). A ticker never seen before gets its NSE-only data (XBRL results, corporate actions, filings) from a dispatched GitHub Actions job. Decision: DECISIONS.md, "On-demand NSE data via workflow dispatch".

- [ ] **Core dossier works without NSE.** Snapshot, trajectory, Promise Ledger, cash quality and balance sheet are built from screener tables + BSE-hosted PDFs (transcripts, annual reports, decks) on Render. NSE data only enriches (XBRL-verified results, corporate actions, filing timeline) and never blocks or delays the core sections.
- [ ] **Validate before dispatch.** Only dispatch for symbols in the NSE equity list (refreshed nightly by a job, served as static JSON). Unknown symbol → no dispatch, plain "not an NSE ticker" message.
- [ ] **One dispatch per ticker per day; reuse running jobs.** Record dispatches in Supabase (`nse_dispatches`: symbol, IST date, status, run id, requested_at, finished_at). Before dispatching: if a row exists for (symbol, today) that is queued/running/succeeded, reuse it (poll its status) instead of starting another.
- [ ] **Workflow `nse-ticker.yml`** (`workflow_dispatch` with input `symbol`): validates the input against the equity list again, fetches that ticker's NSE filings, corporate actions and last 5 quarters' XBRL, writes to Supabase, updates the `nse_dispatches` row. Polite rate limits as in the spikes; `concurrency: nse-${{ inputs.symbol }}` so duplicate runs for one ticker never overlap.
- [ ] **Token.** Fine-grained GitHub personal access token, repository access **only `ShlokN-code/finn`**, permission **Actions: Read and write** (nothing else), **expires in 90 days**. Stored only as Render env var `GITHUB_DISPATCH_TOKEN`; add to `.env.example` as a placeholder. Note the expiry date in DECISIONS.md and set a reminder before the deadline + 90 days.
- [ ] **Failure fallback.** If the dispatch call fails (token expired, GitHub down, rate limit) or the run fails, the NSE-backed sections show "Available after tonight's refresh" — never an error — and the nightly job picks the ticker up.
- [ ] **UI.** Dossier streams core sections immediately; NSE-backed sections show "Fetching exchange data… (~1–2 min)" while the run is in progress, then fill in. Freshness stamp per section.
- [ ] **Tests.** Equity-list validation; once-per-day/reuse logic; fallback message on dispatch failure (mocked GitHub API).
- [ ] **Verify** with a ticker outside the demo set (CLAUDE.md quality rule).

## Phase 1 — ingestion + trust layer (10 Nov 2026)

- [x] EOD prices (Yahoo, split/bonus-adjusted close + dividend-adjusted adj close), 1 year, restatement check — `f7cd26e`, verified live (≈248 sessions × 18 holdings + TRENT, POLYCAB)
- [x] NSE announcements + board-meeting intimations; NSE↔BSE dedup logic + tests (BSE not wired, by decision) — `f7cd26e`, `d62aa65`
- [x] Corporate actions (ex-dates, ratios, ₹/share) and bulk/block deals (API ∪ archive CSV) — `f7cd26e`, `22b9b35`
- [x] Classification ladder with per-tier logging; Gemini free tier with Groq fallback — `cd5ada8`, `d62aa65`, `41c5d8b`
- [x] Event threading — `d62aa65`, `41c5d8b`
- [x] Trust layer: money parsing → ₹ Cr, NSE holidays, freshness (`source_status`, `fetched_at`) — `f7cd26e`, `07cf14a`
- [x] Frozen snapshot 2026-10-30 (DB + `backend/data/snapshots/`) — `41c5d8b`
- [x] Tests: dedup, threading, unit normalisation, classification rules, LLM router — 105 passing
- [x] Run against tickers outside the demo set (TRENT, POLYCAB) — clean
- [x] **Daily job verified on GitHub Actions** — run 42804318441 (dispatched 10 Nov 16:33 IST, commit `85ccaa4`): success in 2 m 54 s; `ingest_runs` #5 status ok, 0 failures; NSE reachable from the runner for every source; prices skipped (exchange holiday).
- [x] **Confirm the schedule fires.** Verified 11 Nov 2026 in `ingest_runs`: scheduler-triggered `check_filings` every 30 min from 08:31 to 16:38 IST (the 08:00 slot is outside the 08:30 window; the 16:30 slot queued behind the daily run in the shared concurrency group and ran at 16:38), `ingest_daily` at 16:31 (trigger `scheduler`), alerts at 00:43 and 07:00. Runs end `partial` only because ITC/RELIANCE results don't reconcile with screener (Friday item). Two causes fixed on the way (`4f2da3c`): a Gemini content refusal on one COCHINSHIP PDF was retried every run, and a NUL character in one filing failed the whole tagging step on every run.
- [x] **Review the eval labels** — reviewed 10 Nov: 4 corrected, 7 checked against the PDF and confirmed; material-over-routine rule added (`05536be`).
- [ ] **Held-out eval set** — moved to Phase 5 (below).
- [x] **Content-free newspaper ads** read by the model from their first PDF pages — full-ladder eval 98.3 %; 20 of 49 stored ads turned out material (see DECISIONS, "Ambiguous between routine and material").
- [x] **Re-capture the snapshot by Fri 13 Nov** if a heavier results day lands this week — checked 12 Nov: 30 Oct is still the richest day (score 32 vs this week's best 23), so no re-capture; the web showcase Brief for 30 Oct was regenerated with the results fixes — `d91328d`
- [x] **Rules:** press releases announcing results without the word "results" → `results_press_release_titled` (period + P&L word); the facility opening stays `press_release` by an earlier decision. Dev set rules-only 96.5 %, full ladder 60/60; rules frozen — `f527cd7`
- [ ] **Backfill older filings** in daily slices if the Brief or calendar needs more than 120 days.

## Phase 2 — ranking, cards, alerts, Telegram (10–11 Nov 2026)

- [x] Contracts (card details, `WeightRule`, `AlertSettings`), migration 0003, privacy wording — `2866877`
- [x] Results from three XBRL filings + screener cross-check (cross_checked / pending / mismatch), operating EBITDA, bank/NBFC templates — `4a1f183`, `57f8d22`
- [x] Results PDF fallback (text table → multimodal for scans) — `c731f53`
- [x] Ranking + feedback rules + `/brief` + card builder — `6cdadca`, novelty fix `e45cd32`
- [x] Telegram bot (/start [token], /stop, Snooze), `/telegram/link`, webhook, test alert — `6cdadca`, `d1d2073`
- [x] Price/volume signals with ex-date handling, sector-relative, explanations — `839579c`
- [x] Alert dispatch: budget, batching, quiet hours, snooze, idempotent — `38e43f4`
- [x] Level-0 tags, one-liners, chips, management profiles (+ optional Tavily) — `4de7ecf`
- [x] Web: reusable card components, `/e/<id>`, `/connect` — `e45cd32`
- [x] **Acceptance 1:** results run for 12 symbols → TATASTEEL Q2 FY27 (filed 7 Nov) cross-checked; PBT ₹5,455.15 Cr confirmed against screener by the product owner. 8 ✓, BAJFINANCE partial, COCHINSHIP pending screener; first-run mismatches explained and fixed — `7a00ff3`
- [x] **Acceptance 2:** @finn_shlok_bot webhook set; `/start` → test alert (TATASTEEL Q2 FY27 card) reached the product owner's phone; Open in FINN opened `/e/<id>`; Snooze → 1 day recorded — `6c29f8d`
- [x] Verify XBRL element names for banks and NBFCs on real instances — HDFCBANK, BAJFINANCE checked; layout fixes in DECISIONS — `7a00ff3`
- [ ] `TAVILY_API_KEY` when the product owner signs up (cards already work without it).
- [ ] Older results XBRL (≤ Dec-2024, `corporates-financial-results`) — only needed for year-ago comparisons before Mar-2025.

## Phase 3 — research engine + Promise Ledger (11–13 Nov 2026)

Plan approved 11 Nov; rules and budget in DECISIONS.md (three Phase 3 entries).

- [x] Contract (Dossier with fixed sections + status/reason, MgmtPromise threads, DossierJob, DossierResponse, AskAnswer), migration 0004, research API + proxy allow-list, background worker — `bfffd9e`; live on Render
- [x] Router: per-model quotas, strong chain (3.8 Flash → 3 Flash), TPM, research lane caps, hashed document text — `248aea6`
- [x] Screener discovery (all tables, transcripts, annual report, capex schedule) + computed trajectory / cash / balance sheet incl. lenders — `12a189a`
- [x] Transcripts (PyMuPDF, text in Supabase), citation checker, MAP extraction — `83eb047`
- [x] Numeric Promise Ledger + analysts + drivers in builds — `85c0cd4` (INFY local: 4 kept, 1 missed, 1 moved)
- [x] **Render env (product owner):** DEPLOY.md §7 — set 11 Nov
- [x] Build the 4 demo tickers on the deployed API; quotes checked — 20 of 20 verdict quotes on their cited pages (PERSISTENT, INFY, BAJFINANCE; POLYCAB has no scorable promise yet)
- [x] JUDGE (strong #1): qualitative promises + paraphrased cross-call links, citing both calls — `eebcf9a`, guards `56e9442`
- [x] REDUCE (strong #2): snapshot text, trajectory line, bull/bear with `{F#}` placeholders rendered in code — `eebcf9a` … `c434aa8`
- [x] Credibility tally always shown, % from n ≥ 5 (product owner) — `540cb77`
- [x] Strong chain + 3.6/3.5 Flash; daily budgets count failed attempts — `0c239b2`, `28296c0`
- [x] Rebuild the 4 demo tickers on Render and regenerate `web/public/fixtures/` (4 tickers incl. PERSISTENT) — 100 of 100 cited transcript quotes on their pages; every section ready except red flags / exchange data (Friday)

### Unseen-ticker acceptance (11 Nov 2026, 15:52 IST)

Draw: `python -m evals.research.draw_unseen --seed 20261111` → pool 2,375 EQ symbols after excluding 34 already built/tested (demo portfolio, demo tickers, anything in dossiers / research_documents / filings / results_filings / prices_daily, TRENT). Banks/NBFCs by company name (`FIN_RE`; the equity list carries no industry): 114 → **JPOLYINVST** (Jindal Poly Investment and Finance). Outside the Nifty 100 (NSE archive list, committed) and not financial: 2,190 → **LAXMIDENTL** (Laxmi Dental). Both have screener pages, so no extra draw. Built on Render through `POST /research/{sym}/build`, no code changes before the first run.

**Run 1 (deployed `75bfa59`, before fixes)**

| | JPOLYINVST (job 37) | LAXMIDENTL (job 38) |
|---|---|---|
| Build time | 8 s | 256 s |
| Calls | 0 cheap · 1 strong (gemini-3.6-flash) | 8 cheap (Flash-Lite) · 2 strong (3.6 Flash); 14 attempts incl. retries; ≈ $0.22 list |
| Documents | 0 transcripts on screener; annual report listed (not read yet) | 8/8 transcripts read (Q3 FY25–Q2 FY27); 432 quotes checked, 1 dropped, 5 re-anchored |
| Snapshot | ready (3 lines, headline figures) | ready |
| Trajectory | ready (10 y; template standard — screener shows this holding company in the standard format) | ready (7 y, listed Jan 2025) |
| Promise Ledger | unavailable · no_transcripts | ready: 18 promises — 1 kept, 1 missed (FY26 growth 16.3% vs 20–25%), 3 quietly dropped, 6 not yet due, 7 can't score; tally 1 of 5 |
| Cash quality | ready (CFO, CFO/PAT, FCF ✓ screener, capex) | ready |
| Balance sheet | ready | ready |
| Analysts | unavailable · no_transcripts | ready (Growth 8 calls, Margins 8, Market share 4…) |
| Red flags | building · not_built_yet (Friday) | building · not_built_yet (Friday) |
| Bull/bear | ready (3 + 3) | ready (3 + 3) |
| Drivers | unavailable · no_transcripts | ready (Growth, Margins, Profit) |
| Exchange data | building · not_built_yet (Friday) | building · not_built_yet (Friday) |

General bugs found: (1) the judge step stays `pending` when there is no ledger; (2) "ESOP expense ₹2.19 Cr / ₹6.35 Cr" — share-based-payment cost schedules — entered the ledger and were marked **quietly dropped**, the most serious claim FINN makes.

**Run 2 (deployed `719bd7e`: ESOP / share-based cost schedules aren't promises; judge step `skipped` without a ledger)**

| | JPOLYINVST (job 39) | LAXMIDENTL (job 40) |
|---|---|---|
| Build time | 5 s | 15 s (transcripts and extractions cached) |
| Calls | 0 cheap · 0 strong (summary cached) | 0 cheap · 1 strong (summary re-written: ledger facts changed) |
| Promise Ledger | unavailable · no_transcripts (unchanged); judge step now `skipped` | 16 promises (was 18): 1 kept, 1 missed, **1 quietly dropped (was 3)**, 6 not yet due, 7 can't score; tally 1 of 3 |
| Other sections | unchanged | unchanged |

The remaining "quietly dropped" (advertisement spend ≤ 5% of revenue, FY26 — not mentioned in the 5 calls since Q1 FY26) is a genuine guidance item.

**Run 3 (LAXMIDENTL with the deck lookup, `9b0ccbe`, job 45):** decks 2 read, 2 of 3 waiting figures found; FY26 PAT margin 13–15% → **missed** at 10.4% (Q4 FY26 investor presentation); tally 1 of 3 → 1 of 4; header "1 of 4 kept · 6 not yet due · next test: FY27 results (5)". 2 Flash-Lite calls, no strong call available (summary refresh parked until the 13:30 IST reset; the earlier summary stays).

### Independent spot-check (11 Nov 2026, 16:20 IST)

Five verdicts drawn across the 4 demo dossiers with `random.Random(1111)` from the 11 scored verdicts (forced: one missed, one goalposts moved, one model-judged; then two at random). A fresh subagent that had not seen this session got only each verdict, its cited PDFs and pages, downloaded the PDFs from BSE itself and read every page.

| # | Ticker | Verdict (by) | Quote 1 on page | Quote 2 on page | Numbers match | Verdict follows | Auditor's note |
|---|---|---|---|---|---|---|---|
| 1 | BAJFINANCE | missed (code): MSME growth 10–12% FY26 → 6% | yes p4 | yes p4 | yes | yes | Neither call states the growth base (likely AUM YoY); Q4 p11 confirms 6% |
| 2 | INFY | goalposts moved (code): FY27 CC growth 1.5–3.5% → 1–2% | yes p4 | yes p4 | yes | yes | Same metric and basis (YoY, constant currency) |
| 3 | POLYCAB | goalposts moved (model): EPC margin "high" → "mid-to-high single digits" | yes p7 | yes p8 | yes | yes, soft | A real cut at the bottom of the range, but vague and undated; actual margins were already below it |
| 4 | BAJFINANCE | missed (code): franchise ≥ 120 M FY26 → 119.3 M | yes p4 | yes p3 | yes | yes, debatable | "Well on course to cross 120 million" is a projection; under the rule it is a miss |
| 5 | PERSISTENT | kept (code): ETR 23–23.5% FY25 → 23.2% | yes p14 | yes p13 | yes | yes | Inside the range |

Result: 10/10 quotes on their cited pages, numbers correct, 5/5 verdicts follow from the evidence; nothing to fix. Items 3 and 4 are softer by nature (an undated outlook; a projection phrased as "well on course") — the verdict reason already quotes both calls so a reader can judge.


### Deck lookup (11 Nov 2026, 16:05 IST) — `71916fe`, count fix `9b0ccbe`

Promises that were can't-score only because the call never printed the delivered figure now read the deck for the quarter that closes the period (one Flash-Lite call per deck).

| Ticker | Decks read | Waiting figures found | Tally before → after | Header now |
|---|---|---|---|---|
| BAJFINANCE | 2 (Q4 FY26, Q4 FY25) | 11 of 12 | 1 of 4 → **8 of 13 · 61.5%** | 15 not yet due · next test: FY27 results (14) |
| INFY | 1 (Q4 FY25) | 2 of 2 | 2 of 4 → **4 of 6 · 66.7%** | 5 not yet due · next test: FY27 results (5) |
| PERSISTENT | 1 | 0 of 1 | 1 of 2 → 1 of 2 | 4 not yet due · next test: FY27 results |
| POLYCAB | 0 (nothing waiting on a figure) | — | 0 of 1 | 8 not yet due · next test: FY28 results |

Quote check on the deployed dossiers (every cited quote, all sections): **183/183 transcript quotes and 13/13 deck quotes on their cited pages.** Fixtures regenerated from Render.
Strong models: all four are out for the Pacific day (3.8 Flash, 3 Flash and 3.6 Flash used; 3.5 Flash answers our requests with a quota 429 — it has no free quota on this key). PERSISTENT and POLYCAB keep this afternoon's 3.6 Flash summaries; their parked jobs rewrite them after 13:30 IST on 12 Nov automatically.

**Friday morning (product owner, 11 Nov: cut if Friday gets tight):**
- [ ] ~~Annual report sections → red flags~~ **cut (Phase 5, below the line):** the section is hidden, not "Coming soon" — `591039a`
- [x] Ask: BM25 over the ticker's pages + facts → Flash-Lite (Groq fallback) → cited answer or "Not found in sources"; cache + 8/visitor/day — `72a0a77`, `707580a`
- [x] Nightly refresh on Actions (code-only recompute; rebuild only on a new document; first-time builds only for the 4 demo tickers); DB size guard — `68f7b81`, router cache across the chain `2beb233`; verified on INFY (job 46: summary reused, 0 live calls after the fix). **Reuse the previous summary unless the document set changed**: REDUCE's facts include the day's market cap, so a forced rebuild spends a strong call even with no new document
- [ ] ~~On-demand NSE dispatch → `exchange_data`~~ **cut (Phase 5):** hidden; listed under "deliberately left out"
- [x] Two tickers outside the demo set — seeded draw JPOLYINVST (NBFC/holding co, no transcripts → labelled partial) and LAXMIDENTL (full dossier); runs 1–3 recorded above
- [x] Cost report (`backend/evals/COST.md`, generated by `python -m evals.cost_report`); README cost section — `707580a`
- [x] Results cards: ITC and RELIANCE revenue doesn't reconcile with screener — excise duty itemised in XBRL, revenue − excise reconciles; PBT by statement layout; mismatch is a card state — `ae9a8fc`. Original note: ITC and RELIANCE revenue doesn't reconcile with screener (ITC ~50 % higher: gross vs net of excise/GST?) — logged as a run failure every 30 min; decide the reconciliation or log it as a card state, not a run failure
- [ ] Deck lookup: guidance items the extraction labels `change` that are really levels (BAJFINANCE "cost of funds 7.75–7.85%") stay can't-score — consider a MAP prompt v2 note on measure
- [x] Summary refresh reuse (`synthesis_hash`) — `68f7b81`: nightly/forced rebuilds re-run REDUCE whenever any fact changes (market cap moves daily); reuse the stored summary unless the document set or ledger verdicts changed
- [x] Frontend fixtures: validated INFY, BAJFINANCE, POLYCAB dossiers in `web/public/fixtures/` (`python -m jobs.research export`; built locally against Supabase — rebuild on Render once §7 is set)

## Phase 4 — frontend (11–12 Nov 2026)

Plan approved 11 Nov with six amendments (DECISIONS: "Phase 4 frontend: plan amendments").

- [x] Brief contract: `BriefRequest`/`BriefResponse`, hidden items, header counts + est. time saved, season strip, feedback in → rules out — `f7c253c`; freshness scoped to the requested holdings — `c5f3e95`
- [x] Showcase replay frozen as a ranked Brief (`jobs.snapshot --brief 2026-10-30` → `web/public/showcase/brief.json`) — `f7c253c`
- [x] Design system, shell (tab bar, Ask bar, sheet, undo toast, states), provenance sheet, restyled cards — `ea9c512`
- [x] Brief: cache-first, window chips, season strip + scoreboard, swipe 40% + scope + 5 s undo, Reviewed today, hidden drawer, Why #N, caught-up, Connect Telegram entry — `76061bc`
- [x] Research: NSE autocomplete, dossier sections with their own status, one-tap build confirmation, BuildProgress with the quota pause, fixture fallback — `76061bc`
- [x] Promise Ledger: tally, % only from n ≥ 5, filters, original → revised, provenance on every verdict and number — `76061bc`, copy fixes `3e5114d`
- [x] Portfolio (holdings + latest Brief event + paste/CSV import) and Rules (adjustments with Reset, Telegram connect, alert rules) — `76061bc`
- [x] QR landing with live phone iframe (no X-Frame-Options; verified on the deployed site), 3-step tour — `76061bc`, `f42e868`
- [x] Drivers-only builds (Flash-Lite only, 50-call cap, 150 headroom) + `GET /research/drivers` + "What you're watching" — `536fa91`
- [x] Loading / error / stale states checked with an unreachable API; auto-retry while waking; first-paint fallback at 0.9 s — `3e5114d`, `0936c0f`
- [x] Drivers for the holdings: 16 of 18 served (3 drivers each; RELIANCE 1). 0 strong calls; 73 Flash-Lite attempts across three runs (36 were Gemini 503 retries); budget now counts failed attempts — `536fa91`, `62d8029`
- [x] MAP output truncation → split into page halves on truncation; IDEA and RELIANCE drivers built — `f355d7f`. Original: MAP output truncates at 16K tokens on very long transcripts (IDEA, 2 of 3 RELIANCE calls): split the transcript or raise the output cap for MAP. ITC publishes no transcripts on screener (stays "drivers appear after research").
- [x] Confirmed drivers → ×1.5 Level-1 boost in `/brief`, strong matches only, "affects: Margins" in Why #N — `f355d7f`. Original: (today `brief()` never passes drivers to `score()`); needs an event→driver match rule
- [x] `POST /portfolio`: last close, day change, 1-month sparkline, status dot (rule in DECISIONS), upcoming calendar; Portfolio scoreboard — `9465006`
- [x] Rules editing (thresholds, categories, budget, quiet hours, snoozes) — `9465006`; per-stock override has no editor yet. Original: Rules editing (thresholds, categories, budget, quiet hours, snoozes) synced via `PUT /subscriptions/me` when Telegram is connected; push rule changes to a connected Telegram copy
- [x] PWA: manifest, icons, offline cache of the latest Brief (web push stays below the cut) — `8252712`
- [x] Wire `/ask` — `72a0a77`. Original: Wire `/ask` when Friday's backend lands: `setAskContext` chips → `POST /research/{sym}/ask` → answer sheet; enable free text
- [x] **Readable Open links** (bug from the product owner's phone): results figures open the results PDF at the statement page → iXBRL view → raw XBRL as a secondary link; filing links readable-first everywhere; provenance grouped by document with page-numbered buttons; figures nowrap — `c59a247`, `41d6096`, backfill workflow `74f383f`, relink run 43106362843 (`5b87c57`)
- [ ] Real-phone checks the browser pane can't do: iOS swipe vs scroll, haptics on Android, first paint on 4G
- [ ] Brief payload: a 7-day Brief is ~1 MB uncompressed (results figures carry full provenance trees); brotli makes the transfer small, but consider trimming duplicated `inputs` server-side

## Phase 5

Plan approved 12 Nov with amendments (DECISIONS: "Phase 5 plan: amendments"). Time-box Fri 13 Nov 14:00 IST.

- [x] Dev-set fix and rule freeze — `f527cd7`
- [x] Ask — `72a0a77`, `707580a` · Cost report — `707580a` · Results eval (A) and ledger accuracy (B) — `f8a99fa`
- [x] Nightly refresh — `68f7b81` · Results reconciliation — `ae9a8fc` · MAP split + driver boost — `f355d7f`
- [x] Walkthrough (C, Playwright, 15/15 on the deployed site) — `3fa7275` · Daily smoke (D) — `e20ab5f` · Live push check (E) — `4da693e` · README known limitations (F)
- [x] Portfolio + Rules editing — `9465006` · PWA + untracked-holdings notice — `8252712` · Showcase checked — `d91328d`
- [x] Red flags and exchange data hidden instead of "Coming soon" — `591039a`

### Robustness: 5 random NSE tickers through the deployed API (12 Nov 2026)

Draw: `python -m evals.research.draw_unseen --seed 20261112 --robust 5` → pool 2,356 after excluding 56 symbols (everything built, tested, ingested, in drivers/research jobs/Ask, the dev set and the held-out set) → **HGINFRA, TATACAP, HCC, PGEL, JASH**. Each one: dossier GET, build, poll, Ask, and a Brief with it as the only holding (`python -m evals.research.robustness`, results in `backend/evals/research/ROBUSTNESS.md`).

| Ticker | Build | Ledger | Ask | Brief | Finding |
|---|---|---|---|---|---|
| HGINFRA | partial (bull/bear 2 of 3 supported) | 20 promises | withheld: number not in sources | 0 cards | Render redeploys during the run re-queued the build twice (heartbeat requeue worked) |
| TATACAP (NBFC) | **failed** | — | answered | 0 cards | **General bug:** a deck quote with no words → ZeroDivisionError in re-anchor, whole build failed. Fixed + deck errors no longer fail a build — `9465006` |
| HCC | partial (bull/bear) | 21 | answered, cited | 0 cards | — |
| PGEL | partial (bull/bear) | 41 | answered, cited | 0 cards | — |
| JASH | partial (bull/bear) | 49 | answered, cited (33 s: model retries) | 0 cards | — |

**TATACAP rerun after the fix** (deployed `8252712`, job 52): partial in 369 s — snapshot, trajectory, ledger (22 promises), balance sheet, analysts, drivers ready; cash quality "not meaningful for lenders"; bull/bear 2 of 3 supported. 5 calls (≈ $0.005 list).

**General finding across all five:** a Brief whose holdings FINN doesn't ingest returned 0 cards and the global freshness stamp, which read as "You're caught up". Fixed: `BriefResponse.untracked` + a notice ("Not tracked yet … connect Telegram to add them") and no "caught up" — `8252712`.

### Walkthrough manual step: research a never-built ticker (12 Nov 2026)

`FINN_BUILD_TICKER=<SYM> npx playwright test -g "never built"` on the deployed site, tickers drawn with `--robust 1` (seeds 20261113–15). It found three general bugs, all fixed:

| Ticker | Result | Finding → fix |
|---|---|---|
| GESHIP | complete dossier, 8 cheap + 2 strong | The step only waited for the section frames; it now waits for the build to end — `4936870` |
| BALKRISIND | build ended in 2.5 min; the page still said "running" 14 min later | (1) a failed final refetch left a stale "running" job with no poll → job status written first, refetch retried; (2) Flash-Lite 503 ×5 published an empty ledger → a busy model parks the build 15 min — `383a7d2`; rebuilt: complete (job 55) |
| MAANALU | first try: page parked on "server is waking up" during a redeploy | dossier page now retries by itself — `3c512eb`; rerun **passed end to end in 5.8 min** (job 56, partial: bull/bear under 3 supported points) |

Final full walkthrough on `3c512eb`: **15/15**.

- [ ] **Next (classification, product owner 13 Nov):** read the first PDF page when the attachment name (`RESULTS…`, `Outcome_Board…`) or the event thread (a results board meeting that day) suggests results but the subject doesn't. Held-out misses Triveni/Page come from subjects that don't describe the PDF. Not done in Phase 5; the held-out set stays frozen.
- [x] **Held-out classification eval** — drawn `1c0007c`; labelled blind by an independent agent and committed before any run `5e015db`; reviewer corrected 2 of the 6 disagreements `0dfbf9f`. Rules only 66.7 % → 80.0 % of decided (50 % → 60 % overall); full ladder 70 % → 80 % (before → after review). Original item:
- [ ] **Held-out classification eval (~20 filings, never used for tuning).** The current 60-filing set is a *dev* set: the rules were written from the same Aug–Nov 2026 filings, so its score is optimistic.
  - Pick ~20 new NSE filings that were not in the dev set or the ~750-filing pull used to write the rules: other symbols and/or later dates, stratified across NSE categories, including a few content-free subjects.
  - **Blind labelling:** the product owner labels them before anyone runs the classifier on them. Store as `backend/evals/classification/heldout.jsonl` (same format, `labelled_by: reviewer (blind)`), committed before the first run.
  - Freeze it: no rule or prompt changes based on held-out misses. Fixes go through the dev set, and the held-out number is reported as measured.
  - `run.py --set heldout|dev` reports each separately (rules only and full ladder).
  - **README reports both numbers:** dev set and held-out, side by side.

## Phase 6 — docs and submission (14 Nov 2026)

- [x] AI logs for phases 0–4 — `6dc4a26`
  - Each file checked to hold one session, its own phase.
  - Phase 2's export had lost the turns before a context compaction, so its complete log was rebuilt from the transcript.
  - Redacted before the first commit: a `.env` diff in the Phase 2 export, and home paths.
  - Indexed in `docs/ai-logs/README.md`.
- [x] DECISIONS: every PRODUCT §12 decision now has an entry. Added: PWA, Telegram over web push, "LLM reads, code calculates", long context vs RAG, feedback rules, drivers from disclosures, "Brief". Plus the snippet-image decision. — `4622bf3`
- [x] README for evaluators. Screenshots are from the deployed site at 375 px with the demo portfolio. It also has the QR, Mermaid architecture, evals, cost, key decisions, known limitations, deliberately left out and next steps. — `8121cc4`; images and Mermaid checked on GitHub
- [x] Telegram screenshot from the product owner's phone → `docs/screenshots/telegram.png`. — `6d2bd32`
- [x] Phase 5 and 6 logs, built from the session transcripts. Phase 5 is in two parts, because the second session is a fork of the first. Phase check, redaction and index as before — `6ae0897` and the phase's last commit.
- [x] After the latency probe ended: `backend/evals/README.md` rewritten to the current state; Render redeployed — `4abac9c`.
- [x] Final checks, 14 Nov:
  - walkthrough 15/15 on the deployed site (3 tests skipped by design);
  - latest smoke run (#3, 16:18 IST) green;
  - Render `/version` = `4abac9c`, the last backend commit;
  - live site warmed after the final push.
- [ ] *Later (not for submission):* a reused dossier summary keeps the figures of the day it was written. INFY's snapshot text says market cap ₹4,67,921 Cr (11 Nov) beside today's ₹4,64,586 Cr tile. REDUCE already writes `{F#}` placeholders, so they could be re-filled with the current figures at read time, with no model call.
