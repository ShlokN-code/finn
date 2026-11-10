# Plan — backlog of agreed items

Work agreed in sessions but not yet built. Tick an item (`- [x]`, with the commit hash) when it is done and verified; don't delete it.
Product scope lives in PRODUCT.md; reasons live in DECISIONS.md. The phase breakdown is kept outside the repo — each phase's prompt arrives at the start of its session.

## Start of next phase

- [x] **Fix `--font-sans`.** `web/app/globals.css` (written by `shadcn init`) sets `--font-sans: var(--font-sans)`, a self-reference, so text falls back to a serif font. Point it at the Geist variable from `app/layout.tsx` (`--font-geist-sans`) and check on a phone. — `a747b11`; verified on the deployed app at 375 px: body font resolves to Geist.

## Research dossier — on-demand NSE data via GitHub Actions dispatch

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
- [ ] **Confirm the schedule fires.** No scheduled `ingest` run had started by 16:40 IST on 10 Nov (new crons can take a while to register on GitHub). Check on 11 Nov that the 30-min filing checks (`check_filings`) and the 16:30 daily run appear in `ingest_runs` with trigger `schedule`.
- [x] **Review the eval labels** — reviewed 10 Nov: 4 corrected, 7 checked against the PDF and confirmed; material-over-routine rule added (`05536be`).
- [ ] **Held-out eval set** — moved to Phase 5 (below).
- [x] **Content-free newspaper ads** read by the model from their first PDF pages — full-ladder eval 98.3 %; 20 of 49 stored ads turned out material (see DECISIONS, "Ambiguous between routine and material").
- [ ] **Re-capture the snapshot by Fri 13 Nov** if a heavier results day lands this week (`python -m jobs.snapshot --suggest`).
- [ ] **Rules:** press releases announcing results or new facilities without the words "results"/"capacity" fall to `press_release` (2 eval misses, PERSISTENT).
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
- [ ] **Acceptance 1:** dispatch `results` on Actions for COCHINSHIP, TATASTEEL, DIVISLAB, HDFCBANK (bank), BAJFINANCE (NBFC), TRENT/POLYCAB (outside demo) → check numbers by hand against the PDFs; confirm ✓ or explain each mismatch.
- [ ] **Acceptance 2:** create the bot (DEPLOY.md §4), run `jobs.telegram_setup`, `/start` → test alert on the product owner's phone; Snooze and Open in FINN work.
- [x] Verify XBRL element names for banks and NBFCs on real instances — HDFCBANK, BAJFINANCE checked; layout fixes in DECISIONS — `7a00ff3`
- [ ] `TAVILY_API_KEY` when the product owner signs up (cards already work without it).
- [ ] Older results XBRL (≤ Dec-2024, `corporates-financial-results`) — only needed for year-ago comparisons before Mar-2025.

## Phase 5

- [ ] **Held-out classification eval (~20 filings, never used for tuning).** The current 60-filing set is a *dev* set: the rules were written from the same Aug–Nov 2026 filings, so its score is optimistic.
  - Pick ~20 new NSE filings that were not in the dev set or the ~750-filing pull used to write the rules: other symbols and/or later dates, stratified across NSE categories, including a few content-free subjects.
  - **Blind labelling:** the product owner labels them before anyone runs the classifier on them. Store as `backend/evals/classification/heldout.jsonl` (same format, `labelled_by: reviewer (blind)`), committed before the first run.
  - Freeze it: no rule or prompt changes based on held-out misses. Fixes go through the dev set, and the held-out number is reported as measured.
  - `run.py --set heldout|dev` reports each separately (rules only and full ladder).
  - **README reports both numbers:** dev set and held-out, side by side.

