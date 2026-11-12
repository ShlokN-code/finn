# FINN

Your portfolio's editor for Indian equities (NSE): it reads every filing, price move and transcript, and shows only what changes your view, with proof.

Built for the ENAM AI Engineer Build Challenge. Product spec: [docs/PRODUCT.md](docs/PRODUCT.md) · Decisions: [docs/DECISIONS.md](docs/DECISIONS.md) · Data sources: [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) · Deploy: [docs/DEPLOY.md](docs/DEPLOY.md) · Plan: [docs/PLAN.md](docs/PLAN.md)

> Status (13 Nov 2026): all five phases are built.
> - **Push:** filings → classification → event threads → ranked Brief and Telegram alerts.
> - **Pull:** a dossier for any NSE ticker, with a Promise Ledger and provenance on every number.
> - **Ask**, scoped to one company.
> - **Evals:** classification, results extraction and Promise Ledger.
> - **Cost report**, a daily smoke test and a scripted evaluator walkthrough.

## Live

| | URL |
|---|---|
| App (Vercel) | https://finn-tau-red.vercel.app (a laptop shows a QR landing with a live phone preview; a phone opens the Brief) |
| API (Render, Singapore) | https://finn-api-4ejm.onrender.com — `/ping`, `/version`, `/health/db`, `/health/sources` |
| Database | Supabase Postgres, Mumbai (not public) |

The free Render instance can take up to ~50 s to wake. cron-job.org pings `/ping` every 10 minutes, and the first paint never waits for Render: it comes from the edge-cached Brief or the saved showcase day.

## Layout

| Path | What |
|---|---|
| `web/` | Next.js 16 (App Router) PWA · TypeScript · Tailwind · shadcn/ui · framer-motion → Vercel. `web/e2e/` = Playwright walkthrough |
| `backend/finn/` | Shared Python package (sources, classification, ranking, extraction, research, llm, models) |
| `backend/api/` | FastAPI app → Render (Brief, research, Ask, Telegram webhook) |
| `backend/jobs/` | Scheduled jobs (ingest, results, alerts, nightly research refresh, smoke) |
| `backend/evals/` | Eval sets and reports: classification, results, research, cost, push check |
| `backend/db/migrations/` | SQL migrations (`python -m jobs.migrate`) |
| `backend/data/snapshots/` | Frozen showcase day(s) for replay mode |
| `.github/workflows/` | `ci` · `ingest` (+ nightly `research-refresh`) · `backfill` · `keepalive` · `smoke` · `spike-ci` |

## Run locally

Python 3.12 venv at the repo root:

```bash
/opt/anaconda3/bin/python3.12 -m venv .venv && .venv/bin/pip install -e "backend[api,jobs,dev]"
```

```bash
cd backend && ../.venv/bin/uvicorn api.main:app --reload --port 8000
```

```bash
cd web && npm install && API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

Tests and checks:

```bash
cd backend && ../.venv/bin/pytest -q && ../.venv/bin/ruff check .
```

```bash
cd web && npm run lint && npm run typecheck
```

Evaluator walkthrough against the deployed site (phone 375 px + laptop 1280 px):

```bash
cd web && npx playwright install chromium && npm run e2e
```

## Ingestion and schedules

All NSE data is fetched by GitHub Actions (NSE blocks Render) and written to Supabase. cron-job.org triggers `workflow_dispatch`, and GitHub's own cron is the backup:

| Job | When (IST) |
|---|---|
| Filing checks | every 30 min, 08:00–22:30, weekdays (exchange holidays included) |
| Daily post-close ingest | 16:30 |
| Alerts held overnight | released at 07:00 |
| Research refresh (portfolio + demo dossiers) | nightly, with the first filing slot from 22:00 |
| Smoke test (see below) | daily, 09:00 |

Pipeline: prices (Yahoo, adjusted) · announcements + board-meeting intimations · corporate actions · bulk/block deals → classification ladder (NSE label → rules → Gemini Flash-Lite for leftovers) → event threads → results cards from three XBRL filings, cross-checked with screener → Level-0 tags → ranking → Telegram (budget, batching, quiet hours, snooze).

## Contracts

Pydantic models in `backend/finn/models/` are the source of truth. After changing them:

```bash
cd web && npm run gen:schema && npm run gen:types
```

CI fails if `web/lib/schema.json` or `web/lib/types.ts` is stale.

## Evals

### Announcement classification

| Set | Mode | Accuracy on decided | Coverage | Overall |
|---|---|---|---|---|
| Dev (60 filings, Aug–Nov 2026, portfolio) | Rules only | 96.5 % (55/57) | 95 % | 91.7 % |
| Dev | Full ladder (+ Flash-Lite, first PDF pages for content-free subjects) | 100 % (60/60) | 100 % | 100 % |
| **Held-out** (20 filings, 11–12 Nov 2026, other companies, labelled blind) | Rules only | *pending the blind labels* | | |
| **Held-out** | Full ladder | *pending the blind labels* | | |

The dev set is optimistic: the rules were written from those same three months of filings. The held-out set was drawn by `python -m evals.classification.draw_heldout --seed 20261112`. It is stratified by NSE label, one filing per company, includes 3 content-free subjects, and excludes every company in the dev set or the filings table. The product owner labelled it before the classifier ever ran on it. It is frozen: no rule or prompt change is made from its misses.

Run with `python -m evals.classification.run --set dev|heldout [--model]` from `backend/`.

Live tier split over all 947 stored filings: 27.7 % NSE label · 54.8 % rules · 17.4 % model · 0.1 % failed (retried next run).

### Results extraction ([backend/evals/results/REPORT.md](backend/evals/results/REPORT.md))

Method: card figures (read from NSE XBRL) are checked against the company's own results PDF, statement page, within printed precision. The five most recent results cards were used. Scanned pages were read from the rendered image, and the readings are recorded in `visual_checks.json`.

| Field | Revenue | EBITDA | PBT | PAT | QoQ (all lines) | YoY (all lines) |
|---|---|---|---|---|---|---|
| Correct | 5/5 | 5/5 | 5/5 | 5/5 | 19/20 | 18/20 |

**57/60 fields (95 %).** The three misses are TITAGARH's comparatives, which were restated in the Q2 filing (discontinued operations). FINN computes YoY/QoQ against the earlier XBRL as first reported.

Verification state across all 15 results cards: 12 cross-checked with screener · 2 partial · 1 couldn't verify (numbers hidden).
- Partial: BAJFINANCE's NII/PPOP have no screener row; TATA POWER's Q1 doesn't match screener's.
- Couldn't verify: ALKEM, whose Q2 XBRL isn't on NSE yet.

### Promise Ledger ([backend/evals/research/LEDGER.md](backend/evals/research/LEDGER.md))

- **265/265 cited quotes are on their cited page** across 7 dossiers (119 promises). Every quote is re-checked against the stored page text.
- **Independent audit:** a separate agent read the PDFs itself for a sample of 5 verdicts. 10/10 quotes were on their pages and all 5 verdicts follow from the evidence.

| Ticker | Promises | Kept | Missed | Goalposts moved | Quietly dropped | Credibility |
|---|---|---|---|---|---|---|
| BAJFINANCE | 37 | 8 | 4 | 1 | 0 | 8 of 13 · 62 % |
| INFY | 18 | 4 | 1 | 1 | 0 | 4 of 6 · 67 % |
| LAXMIDENTL | 16 | 1 | 2 | 0 | 1 | 1 of 4 |
| POLYCAB | 24 | 0 | 0 | 2 | 0 | 0 of 2 |
| PERSISTENT | 11 | 1 | 0 | 1 | 0 | 1 of 2 |
| HDFCBANK | 13 | 1 | 0 | 0 | 0 | 1 of 1 |

### End to end

- **Live push check** ([backend/evals/PUSH_CHECK.md](backend/evals/PUSH_CHECK.md)): ALKEM's CFO appointment, filed on NSE at 13:58:26 IST, reached Telegram at 14:03:28 IST through the scheduler, classification and ranking.
- **Walkthrough** (`web/e2e/walkthrough.spec.ts`, against the deployed site at 375 px and 1280 px): 15/15 checks pass, covering:
  - landing + QR + live preview;
  - the Brief;
  - swipe + UNDO;
  - a card's readable source;
  - the ledger's provenance sheet;
  - Ask;
  - Rules;
  - the Connect Telegram deep link.
- **Robustness** ([backend/evals/research/ROBUSTNESS.md](backend/evals/research/ROBUSTNESS.md)): 5 random NSE tickers (logged seed) through the deployed API.
- **Smoke test** (`.github/workflows/smoke.yml`, daily): GETs cached pages and API routes only and fails loudly.

## Cost ([backend/evals/COST.md](backend/evals/COST.md))

FINN pays $0: Gemini, Groq, GitHub Actions, Render, Vercel and Supabase are all on free tiers. At paid list price:

| Unit | Model calls | List price |
|---|---|---|
| 30-min filing check | 1.4 cheap on average (0 when nothing is new) | ≈ $0.001 |
| Daily post-close ingest | ~33 cheap | ≈ $0.02 |
| First-time dossier (with transcripts) | ~8 cheap + 2 strong | ≈ $0.21 |
| Cached dossier / nightly refresh with no new document | 0 (cached; summary reused) | $0 |
| Ask (new question) | 1 cheap | ≈ $0.0008 |
| Drivers for one holding | ≤ 3 cheap | ≈ $0.07 |

27.7 % of filings are classified by NSE's own label and 54.8 % by rules. Only 17.4 % need a model.

## Known limitations (what happens if nobody touches it for a month)

| Risk | When | What FINN does |
|---|---|---|
| **Gemini model retired or renamed** (`gemini-3.5-flash-lite`, the strong chain 3.8 Flash → 3 Flash → 3.6 Flash) | Google retires preview models with weeks of notice | Model ids come from env vars (`GEMINI_MODEL_*`), so the fix is one value, checked with `python -m finn.llm.check`. Until then: filings are still classified by NSE label and rules (~82 %); the rest stay "unclassified · retried next run" in the hidden drawer. Groq (qwen) takes short text calls and Ask. The strong chain falls through to the next model. If every strong model is gone, dossiers keep their last good summary and new builds say "written on the next build". |
| **GitHub token used by cron-job.org expires** | the date set when it was created (DEPLOY.md §6a) | Dispatches return 401 and cron-job.org emails after 3 failures. GitHub's own cron (backup) keeps the filing checks, daily ingest and alerts running, less punctually. |
| **GitHub disables scheduled workflows** after 60 days without a commit to a public repo | ~mid-January 2027 if untouched | cron-job.org's dispatches don't depend on schedules and keep working. Only the backup cron and the daily smoke stop. |
| **Supabase free tier pauses** after 7 days without activity | only if every job stops | The 30-minute jobs and the 10-minute `/ping` (which runs `SELECT 1`) keep it active. If it does pause: the Brief serves the phone's last copy or the showcase day, labelled; the 4 demo dossiers fall back to committed fixtures ("Saved copy from 11 Nov 2026"); the showcase file lives in git. |
| **Render free tier**: sleeps after 15 min; 750 instance-hours a month | always | Keepalive keeps it warm, and one always-on instance uses ≤ 744 h. If keepalive stops, the first request waits ~50 s; the app shows cached data and "waking up" instead of a blank screen. |
| **NSE changes its API or blocks GitHub's runners** | unpredictable | Filing checks fail and are logged in `ingest_runs`. The Brief shows a "stale" banner once the feed is more than 2 h behind its expected slot, with "Data as of …" on every screen. The smoke test fails when data is over 4 days old. Stopgap: run ingest from a residential machine (`python -m jobs.check_filings --force`). |
| **screener.in redesign** | unpredictable | The parser checks each section. Results cross-checks become "pending" (numbers shown, unverified). New dossier builds can't compute trajectory, cash or balance sheet, which show "not found in sources"; existing dossiers keep their last good copy. |
| **Yahoo prices rate-limit or change** | occasionally | Price/volume signals skip that day; filings and results are unaffected. Ex-dates come from NSE, not Yahoo. |
| **Free-model daily quotas** | every day | Builds park as "waiting for quota" and resume after the 13:30 IST reset; sections already built stay readable. Ask stops at 40 new answers a day (8 per visitor); cached answers stay free. |
| **New listings** | weekly | The autocomplete list is a committed static file (`nse-symbols.json`), so a new IPO isn't offered until it's refreshed. A symbol typed into the URL still works if Render's copy of the equity list has it. |

Other limitations, by design:
- **Restated comparatives:** prior quarters come from the XBRL as first reported (see the results eval).
- **Annual-report red flags and the on-demand NSE "exchange data" section** are not built; they are hidden rather than shown as "coming soon".
- **Web push** is not offered; Telegram is the push channel (PRODUCT §12).

## AI logs

Each phase's Claude Code session is saved as readable markdown in `docs/ai-logs/` (the desktop app has no export). At the end of a session, from the repo root:

```bash
python3 scripts/transcript_to_md.py --out docs/ai-logs/phase-N-name.md --title "Phase N — name" --summary "What the phase delivered"
```

It picks the newest transcript for this repo in `~/.claude/projects/` and keeps messages, replies and one-line tool summaries. It exits 2 if it finds emails, local paths or secret-like strings; review before committing (the repo is public).
