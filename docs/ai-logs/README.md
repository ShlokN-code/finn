# AI build history

FINN was built in seven Claude Code sessions, one per phase, between 9 and 14 Nov 2026. The opening prompt of each phase came from the product owner. Claude proposed a plan and waited for approval before writing code.

| Phase | Dates (IST) | What it built | Log |
|---|---|---|---|
| 0 — Setup | 10 Nov | Data spike (NSE, BSE, Yahoo, screener, XBRL from laptop, GitHub runners and Render), monorepo, Pydantic → TypeScript contracts, skeleton deploy (Vercel → Render → Supabase) | [phase-0-setup.md](phase-0-setup.md) (full) · [phase-0-spike.md](phase-0-spike.md) (condensed) |
| 1 — Ingestion + trust layer | 10 Nov | Adjusted prices, NSE announcements and board meetings, corporate actions, bulk/block deals, classification ladder (label → rules → model), event threads, frozen showcase day | [phase-1-ingestion.md](phase-1-ingestion.md) |
| 2 — Ranking, cards, alerts, Telegram | 10–11 Nov | Results cards from three XBRL filings, cross-checked with screener; ranking and feedback rules; price/volume signals; management profiles; alert dispatch; Telegram bot; cron-job.org scheduler | [phase-2-ranking.md](phase-2-ranking.md) (complete, condensed) · [phase-2-ranking-export-part2.md](phase-2-ranking-export-part2.md) (full export, second half) |
| 3 — Research engine + Promise Ledger | 11 Nov | Any-ticker dossier from screener and BSE-hosted transcripts and decks, Promise Ledger (code scores numbers, model judges language), citation checker, unseen-ticker acceptance | [phase-3-research.md](phase-3-research.md) |
| 4 — Frontend | 11–12 Nov | Mobile PWA: Brief, provenance sheet, dossier and ledger, Portfolio, Rules, QR landing with live phone preview, first paint under 1 s with Render asleep | [phase-4-frontend.md](phase-4-frontend.md) |
| 5 — Hardening, evals, cost | 12–14 Nov | Ask, cost report, results and ledger evals, nightly refresh, Portfolio and Rules editing, PWA, robustness on random tickers, walkthrough, smoke test, live push check; then the blind held-out eval and the `/ping` latency fix | [part 1](phase-5-hardening-part1.md) · [part 2](phase-5-hardening-part2.md) (condensed; part 2 is a fork of part 1 after turn 12) |
| 6 — Docs and submission | 14 Nov | README for evaluators (screenshots, QR, architecture, evals, cost, limitations), decisions audit against the spec, these logs (redacted, phase-checked) and this index, final checks | [phase-6-docs.md](phase-6-docs.md) (condensed) |

## Two formats

- **Full:** Claude Code's `/export` of the session. Prompts, replies and tool calls, with tool output truncated as shown in the terminal.
- **Condensed:** made from the session transcript by [`scripts/transcript_to_md.py`](../../scripts/transcript_to_md.py). Prompts, replies, one line per tool call and the end-of-turn recaps. Phase 2's export lost the turns before a context compaction, so its complete log is the condensed one. Phases 5 and 6 are condensed too. Phase 5 has two parts because its second session was forked from the first. Part 1 leaves out one unrelated question (a market-sizing slide) asked at the end of that session.

## Redaction

The repo is public. Before committing, every log is scanned for:
- secrets: database URLs, API keys, bot tokens, `*_KEY=` / `*_SECRET=` / `*_TOKEN=` values;
- personal data: email addresses, phone numbers, Telegram chat IDs, local paths.

Hits are replaced with `<redacted>`, and home paths with `~`. The only secrets found were a `.env` diff in the Phase 2 export (8 values plus 8 wrapped tails). They were never committed. `transcript_to_md.py` runs the same privacy scan and exits 2 on a hit.
