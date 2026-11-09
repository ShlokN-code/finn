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
