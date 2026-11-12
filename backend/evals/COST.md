# Cost report

Generated 12 Nov 2026 17:35 IST by `python -m evals.cost_report` from `llm_calls` (702 model attempts, 520 answered, 10 Nov – 12 Nov 2026 UTC) and the job tables. **FINN pays $0**: everything runs on free tiers (Gemini AI Studio, Groq, GitHub Actions on a public repo, Render, Vercel, Supabase). Dollar figures are what the same calls would cost at the paid **list price** (Flash-Lite $0.3/2.5 and Flash $0.75/3.75 per million input/output tokens).

All-time: 2664.8K tokens in, 1094.1K out, **$3.64 at list price**.

## Push side (scheduled ingest)

Model calls only happen for filings the exchange label and rules can't classify, newly tagged events (impact tag + one-liner) and new management profiles. A run with nothing new makes no call.

| Run | Runs logged | Model calls / run (avg) | List-price cost / run | Median duration |
|---|---|---|---|---|
| 30-min filing check | 46 | 1.2 (max 33) | $0.0009 (max $0.0250) | 99 s |
| Daily post-close ingest (16:30) | 3 | 21.7 (max 34) | $0.0145 (max $0.0219) | 406 s |
| 07:00 alerts release | 5 | 0.0 (max 0) | $0.0000 (max $0.0000) | 2 s |

Push-side calls per IST day (classification, tagging, management profiles):

| IST day | Attempts | Answered | List price |
|---|---|---|---|
| Tue 10 Nov | 207 | 187 | $0.11 |
| Wed 11 Nov | 134 | 112 | $0.0958 |
| Thu 12 Nov | 7 | 7 | $0.0046 |

## Rules before models: how filings were classified

| Tier | Filings | Share |
|---|---|---|
| rule | 520 | 54.8% |
| exchange | 262 | 27.6% |
| model | 166 | 17.5% |
| failed | 1 | 0.1% |

949 stored filings. `exchange` = NSE's label alone, `rule` = subject regex, `model` = Flash-Lite (reading the first PDF pages when the subject says nothing), `failed` = retried next run.

## Research dossiers

"First build" is the ticker's first job that called a model. The totals add every later job: resumes after a quota pause and rebuilds after a prompt or pipeline change during development (a new prompt version is a cache miss by design). An unchanged ticker's rebuild re-reads nothing: transcripts, extractions and model answers are cached by content hash.

| Ticker | First build | Cheap calls (all jobs) | Strong calls | Failed attempts | Tokens in / out | List price (all jobs) | Jobs |
|---|---|---|---|---|---|---|---|
| PGEL | job 50: 11 cheap + 2 strong, $0.25 | 11 | 2 | 2 | 135.2K / 79.8K | $0.25 | 1 |
| POLYCAB | job 3: 7 cheap + 0 strong, $0.20 | 7 | 9 | 17 | 125.4K / 74.7K | $0.24 | 12 |
| LAXMIDENTL | job 38: 8 cheap + 2 strong, $0.22 | 10 | 5 | 6 | 143.7K / 75.4K | $0.24 | 3 |
| PERSISTENT | job 6: 8 cheap + 0 strong, $0.20 | 9 | 8 | 7 | 155.0K / 71.0K | $0.24 | 7 |
| BAJFINANCE | job 5: 2 cheap + 0 strong, $0.0439 | 8 | 9 | 7 | 136.3K / 71.5K | $0.23 | 12 |
| INFY | job 4: 8 cheap + 0 strong, $0.21 | 9 | 7 | 9 | 218.4K / 63.6K | $0.23 | 10 |
| JASH | job 51: 9 cheap + 2 strong, $0.22 | 9 | 2 | 12 | 118.3K / 71.4K | $0.22 | 1 |
| HCC | job 49: 9 cheap + 2 strong, $0.15 | 9 | 2 | 0 | 105.5K / 43.0K | $0.15 | 1 |
| HGINFRA | job 47: 7 cheap + 2 strong, $0.12 | 7 | 2 | 6 | 77.6K / 39.1K | $0.12 | 1 |
| TATACAP | job 48: 5 cheap + 0 strong, $0.11 | 5 | 2 | 5 | 106.7K / 33.2K | $0.12 | 2 |
| GESHIP | job 53: 8 cheap + 2 strong, $0.11 | 8 | 2 | 2 | 127.5K / 25.7K | $0.11 | 1 |
| BALKRISIND | job 54: 0 cheap + 1 strong, $0.0027 | 0 | 1 | 7 | 875 / 553 | $0.0027 | 1 |
| JPOLYINVST | job 37: 0 cheap + 1 strong, $0.0026 | 0 | 1 | 0 | 818 / 538 | $0.0026 | 2 |

- **First-time dossier with transcripts:** $0.18 at list price (mean of the first builds of 10 tickers): ~1 Flash-Lite MAP call per transcript (8 max) + up to 3 deck lookups, then 2 strong calls (JUDGE, REDUCE). MAP output tokens dominate (a transcript's facts and quotes are copied out).
- **Ticker without transcripts** (e.g. JPOLYINVST): 0 cheap calls, 1 strong call (REDUCE) ≈ $0.004.
- **Cached dossier:** $0 — 1 build jobs finished with no model call at all (everything from the cache; REDUCE's prompt has no date, so an unchanged dossier hits the cache).
- **Opening a dossier** never calls a model: it reads the stored copy.
- **Where the newest builds came from:** HGINFRA, TATACAP, HCC, PGEL, JASH = the Phase 5 robustness run (seed 20261112, through the deployed API); GESHIP, BALKRISIND, MAANALU = the walkthrough's manual "research a never-built ticker" step (`FINN_BUILD_TICKER`). Their calls are included above.

## Drivers builds ("What you're watching")

14 holdings, 87 attempts (44 answered), $1.07 in all at list price → **$0.0764 per holding** (≤ 3 Flash-Lite MAP calls on the latest transcripts; 0 strong calls by construction). The same MAP output is reused when that ticker's full dossier is built.

## Ask

11 answered model calls so far: **$0.0010 per question at list price** (~2.2K tokens in, ~123 out, ~2.5 s). 11 distinct answers cached, served 7 times from the cache at $0. Caps: 8 new answers per visitor per IST day; 40 per day for everyone together (Flash-Lite's `research.ask` lane).

## Free-tier usage vs limits

Per Pacific day (Gemini's quota day: resets 13:30 IST). Failed attempts count toward the daily quota, so the router counts them too.

| Pacific day | Model | Attempts | Answered | Free RPD | Used |
|---|---|---|---|---|---|
| 09 Nov | gemini-3.5-flash-lite | 6 | 6 | 500 | 1% |
| 10 Nov | gemini-3.5-flash-lite | 308 | 266 | 500 | 62% |
| 11 Nov | gemini-3-flash-preview | 23 | 19 | 20 | 115% |
| 11 Nov | gemini-3.5-flash | 3 | 0 | 20 | 15% |
| 11 Nov | gemini-3.5-flash-lite | 172 | 121 | 500 | 34% |
| 11 Nov | gemini-3.6-flash | 21 | 15 | 20 | 105% |
| 11 Nov | gemini-3.8-flash | 32 | 3 | 20 | 160% |
| 12 Nov | gemini-3-flash-preview | 15 | 15 | 20 | 75% |
| 12 Nov | gemini-3.5-flash-lite | 104 | 71 | 500 | 21% |
| 12 Nov | gemini-3.8-flash | 18 | 4 | 20 | 90% |

| Service | Free limit | FINN's use |
|---|---|---|
| Gemini Flash-Lite | 15 RPM, 250K TPM, 500 requests/day | push side peaks ~250/day in results season; research lanes capped at 220 (builds) + 40 (Ask); router stops at 400 |
| Gemini Flash models (strong) | 5 RPM, 20 requests/day each | 2 per new dossier; chain of 3 models = 60/day |
| Groq (qwen3.8-27b) | 8K tokens/min | fallback for short push calls and Ask only |
| GitHub Actions | free for public repos | ~160 short runs/week (filing checks, daily, alerts, keepalive) |
| Render (web service) | 750 instance-hours/month, sleeps after 15 min idle | one instance; cron-job.org pings `/ping` every 10 min in the day |
| Supabase | 500 MB database; pauses after 7 days without activity | see `select pg_database_size` (tens of MB); the 30-min jobs keep it active |
| Vercel (Hobby) | 100 GB transfer/month | static shell + edge-cached demo Brief |

## What it would cost at list price

| Item | Unit cost | Assumption | Per month |
|---|---|---|---|
| Push side (18 holdings) | $0.0692 / day | measured average per IST day | $2.07 |
| First-time dossiers | $0.18 | 15 per day (the daily cap), every day | $80.47 |
| Ask | $0.0010 | 40 per day (the daily cap) | $1.17 |
| Nightly refresh | $0 unless a new document | 1 new transcript/week per demo ticker ≈ 1 MAP + 2 strong | $0.72 |

If every daily cap were used every day, the list price would be about $83.71 a month, almost all of it first-time dossiers; a realistic month (a few new tickers a week) is a few dollars. On the free tiers it costs nothing. The binding constraint is the strong models' 20 requests a day each, not money: that is why numeric verdicts are computed in code and the summary is reused unless the document set changes.

Strong-model rows above 100% are attempts, not billed requests: on 11 Nov `gemini-3.8-flash` answered 503 (overloaded) and timed out on most attempts. The router counts every attempt against the day (conservative), and after two failures skips that model for 10 minutes.

