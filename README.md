# FINN

Your portfolio's editor for Indian equities (NSE/BSE): it reads every filing, price move and transcript, and shows only what changes your view — with proof.

Built for the ENAM AI Engineer Build Challenge. Product spec: [docs/PRODUCT.md](docs/PRODUCT.md) · Decisions: [docs/DECISIONS.md](docs/DECISIONS.md) · Data sources: [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) · Deploy: [docs/DEPLOY.md](docs/DEPLOY.md) · Plan: [docs/PLAN.md](docs/PLAN.md)

> Status: Phase 1 — ingestion + trust layer. NSE filings, prices, corporate actions and deals flow into Supabase, classified and threaded into events, on a GitHub Actions schedule. No Brief UI yet.

## Live

| | URL |
|---|---|
| App (Vercel) | https://finn-tau-red.vercel.app |
| API (Render, Singapore) | https://finn-api-4ejm.onrender.com — `/health`, `/health/db`, `/health/sources` |
| Database | Supabase Postgres, Mumbai (not public) |

The free Render instance can take up to ~50 s to wake; `keepalive` pings it every 10 minutes.

## Layout

| Path | What |
|---|---|
| `web/` | Next.js 16 (App Router) PWA · TypeScript · Tailwind · shadcn/ui · framer-motion → Vercel |
| `backend/finn/` | Shared Python package (sources, classification, ranking, extraction, research, llm, models) |
| `backend/api/` | FastAPI app → Render |
| `backend/jobs/` | Scheduled jobs (GitHub Actions cron) |
| `backend/evals/` | Labelled eval sets |
| `backend/spikes/` | Standalone data-source probes (see DATA_SOURCES.md) |
| `backend/db/migrations/` | SQL migrations (`python -m jobs.migrate`) |
| `backend/data/snapshots/` | Frozen showcase day(s) for replay mode |
| `.github/workflows/` | `ci` · `ingest` · `keepalive` · `spike-ci` |
| `scripts/` | Dev utilities (`transcript_to_md.py` for AI logs) |

## Run locally

Python 3.12 venv at the repo root:

```bash
/opt/anaconda3/bin/python3.12 -m venv .venv && .venv/bin/pip install -e "backend[api,dev]"
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

## Ingestion

All NSE data is fetched by GitHub Actions (NSE blocks Render) and written to Supabase. Schedule (IST): daily ingest at 16:30, filing checks every 30 min 08:30–22:00 on weekdays (exchange holidays included). Every workflow run can also be started by hand (`ingest` → Run workflow → job = daily / filings / snapshot / migrate).

Locally, with `DATABASE_URL` and `GEMINI_API_KEY` in a root `.env` (see `.env.example`):

```bash
cd backend && ../.venv/bin/pip install -e ".[jobs,dev]" && ../.venv/bin/python -m jobs.migrate
```

```bash
cd backend && ../.venv/bin/python -m jobs.ingest_daily --backfill-days 120
```

```bash
cd backend && ../.venv/bin/python -m jobs.snapshot --suggest
```

Pipeline: prices (Yahoo, adjusted) · announcements + board-meeting intimations · corporate actions · bulk/block deals → classification ladder (NSE label → rules → Gemini Flash-Lite for leftovers) → event threads → `source_status` freshness and an `ingest_runs` row with the tier split.

## Contracts

Pydantic models in `backend/finn/models/` are the source of truth. After changing them:

```bash
cd web && npm run gen:schema && npm run gen:types
```

CI fails if `web/lib/schema.json` or `web/lib/types.ts` is stale.

## AI logs

Each phase's Claude Code session is saved as readable markdown in `docs/ai-logs/` (the desktop app has no export).
At the end of a session, from the repo root:

```bash
python3 scripts/transcript_to_md.py --out docs/ai-logs/phase-N-name.md --title "Phase N — name" --summary "What the phase delivered"
```

It picks the newest transcript for this repo in `~/.claude/projects/`, keeps messages, replies and one-line tool summaries, and exits 2 if it finds emails, local paths or secret-like strings — review before committing (the repo is public).

## Evals

**Announcement classification** (`backend/evals/classification/`, 60 real NSE filings from the demo portfolio, Aug–Nov 2026; labels written by Claude, pending human review):

| Mode | Accuracy on decided | Coverage | Overall |
|---|---|---|---|
| Rules only (exchange label + regex) | 96.5 % (55/57) | 95 % | 91.7 % |
| Full ladder (+ Gemini Flash-Lite for the 3 leftovers) | 96.7 % (58/60) | 100 % | 96.7 % |

Live tier split on the first backfill (824 portfolio filings, Jul–Nov 2026): 34 % exchange label · 52 % rules · 13 % model · 0 % failed after one retry pass (13 Gemini 503s on the first pass).

Caveat: the rules were written from the same three months of filings, so this is optimistic; a held-out set comes next. Run with `python -m evals.classification.run [--model]` from `backend/`.
