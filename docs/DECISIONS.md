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
