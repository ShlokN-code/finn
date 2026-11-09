# FINN

Your portfolio's editor for Indian equities (NSE/BSE): it reads every filing, price move and transcript, and shows only what changes your view — with proof.

Built for the ENAM AI Engineer Build Challenge. Product spec: [docs/PRODUCT.md](docs/PRODUCT.md) · Decisions: [docs/DECISIONS.md](docs/DECISIONS.md) · Data sources: [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) · Deploy: [docs/DEPLOY.md](docs/DEPLOY.md)

> Status: skeleton. Data sources verified, contracts defined, web → API → database deployed. No product features yet.

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
| `backend/db/migrations/` | SQL run in Supabase |
| `.github/workflows/` | `ci` · `keepalive` · `spike-ci` |

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

## Contracts

Pydantic models in `backend/finn/models/` are the source of truth. After changing them:

```bash
cd web && npm run gen:schema && npm run gen:types
```

CI fails if `web/lib/schema.json` or `web/lib/types.ts` is stale.

## Evals

None yet — accuracy will be reported here once classification/extraction land.
