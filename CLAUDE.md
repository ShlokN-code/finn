# CLAUDE.md — FINN

FINN is a mobile-first financial investment agent for Indian equities (NSE/BSE). Push = it tells you what changed and why it matters. Pull = on-demand research on any NSE ticker, grounded in primary sources.

**The full product spec is in `docs/PRODUCT.md`. Read it before planning any feature.** Decisions are logged in `docs/DECISIONS.md`.

## How we work

- **Plan before code.** For any non-trivial task, propose a short plan (files, approach, trade-offs, risks) and wait for my approval.
- **Thin-but-working beats broad-but-broken.** Get one path working end to end before widening. Never leave the deployed app broken.
- **Ask when a decision is mine.** Product or UX choices, anything affecting the spec, anything costing money: ask. Implementation details: decide and tell me.
- **When you make a meaningful technical decision, add a short entry to `docs/DECISIONS.md`** (context → decision → alternatives → why).
- Small, focused commits with clear messages.

## Non-negotiable rules

1. **The LLM reads, code calculates.** No arithmetic, ratios, growth rates or comparisons done by a model. Models extract; Python computes.
2. **Primary sources only for research** (annual reports, concall transcripts, investor decks, exchange filings, screener.in standardised tables). Never news, broker notes, or the model's own knowledge of a company. Prompts must say so, and outputs must carry citations.
3. **Every number and claim carries provenance** (source URL, document, page, quote where applicable). If something can't be verified, return an explicit "unverified/not found" state — never a guess.
4. **Secrets never in code or git.** Use environment variables / GitHub Secrets. Keep `.env.example` updated.
5. **Cost discipline.** Rules before models. Cheap model for bulk classification/extraction; strong model only for synthesis. Cache every LLM call by content hash. Log tokens and estimated cost per call.
6. **Be polite to data sources.** Rate-limit, set a sensible User-Agent, cache raw downloads, and back off on errors.
7. **Always keep a fallback.** If a live source fails, serve the last good snapshot and say how fresh it is.

## Stack

- `web/` — Next.js (App Router) PWA, TypeScript, Tailwind, shadcn/ui, framer-motion. Deployed on Vercel. Mobile-first; desktop shows a landing page with a phone preview + QR.
- `backend/` — Python 3.11.
  - `backend/finn/` — shared package (sources, classification, ranking, extraction, research, llm routing, models).
  - `backend/api/` — FastAPI app (research on demand, Ask, Telegram webhook). Deployed on Render free tier.
  - `backend/jobs/` — scheduled scripts (ingest, rank, alerts, nightly dossier refresh, keep-alive).
- Database: Supabase Postgres (free tier).
- Schedules: GitHub Actions cron (times in UTC; IST = UTC+5:30). Every workflow also has `workflow_dispatch`.
- Push: Telegram Bot API + PWA web push.
- LLM access goes through one routing module (`backend/finn/llm/`) with a provider-agnostic interface, tiers (`cheap`, `strong`), caching, and cost logging.

## Data contracts

Shared JSON shapes are defined once (Pydantic in `backend/finn/models/`, mirrored as TypeScript types in `web/lib/types.ts`). Core types: `Filing`, `Event` (threaded filings), `Card`, `Alert`, `Holding`, `Driver`, `Dossier`, `Promise`, `Citation`. Change them deliberately and update both sides.

## Domain conventions

- Money in ₹ crore internally; normalise lakh/million on ingest. Display with Indian separators.
- Times in IST for display; store UTC.
- Quarters labelled Indian FY style (Q2 FY27 = Jul–Sep 2026).
- Results default to consolidated; always label consolidated/standalone.
- Banks/NBFCs: no EBITDA — use NII, PPOP, PAT.
- Prices: use adjusted series; never alert on the mechanical move from a dividend/bonus/split ex-date.

## Quality

- Unit tests for parsers, unit normalisation, EBITDA computation, ranking, threshold logic.
- `backend/evals/` holds small labelled sets (announcement classification, results extraction). Report accuracy in the README.
- Before calling a feature done: run it against at least one ticker outside the demo set.
