# Plan — backlog of agreed items

Work agreed in sessions but not yet built. Tick an item (`- [x]`, with the commit hash) when it is done and verified; don't delete it.
Product scope lives in PRODUCT.md; reasons live in DECISIONS.md. The phase breakdown is kept outside the repo — each phase's prompt arrives at the start of its session.

## Start of next phase

- [ ] **Fix `--font-sans`.** `web/app/globals.css` (written by `shadcn init`) sets `--font-sans: var(--font-sans)`, a self-reference, so text falls back to a serif font. Point it at the Geist variable from `app/layout.tsx` (`--font-geist-sans`) and check on a phone. — CSS fixed in `a747b11`; phone check pending (not yet deployed).

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
- [ ] **Push and verify on GitHub Actions:** dispatch `ingest` with job = daily, then job = filings; check the job summary and `source_status`. Needs repo secret `DATABASE_URL` (and `GEMINI_API_KEY`, already added).
- [ ] **Review the eval labels** in `backend/evals/classification/labelled.jsonl` (written by Claude; `note` marks uncertain ones) and add a held-out set from other symbols/months.
- [ ] **Re-capture the snapshot by Fri 13 Nov** if a heavier results day lands this week (`python -m jobs.snapshot --suggest`).
- [ ] **Rules:** press releases announcing results or new facilities without the words "results"/"capacity" fall to `press_release` (2 eval misses, PERSISTENT).
- [ ] **Backfill older filings** in daily slices if the Brief or calendar needs more than 120 days.

