# Plan

Work items agreed but not yet built. Product scope lives in PRODUCT.md; reasons live in DECISIONS.md.

> No phase breakdown existed in the repo when this file was created (10 Nov 2026). Items below are grouped by when they were agreed to happen; merge them into the full phase plan when it is written down.

## Start of next phase

- [ ] **Fix `--font-sans`.** `web/app/globals.css` (written by `shadcn init`) sets `--font-sans: var(--font-sans)`, a self-reference, so text falls back to a serif font. Point it at the Geist variable from `app/layout.tsx` (`--font-geist-sans`) and check on a phone.

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
