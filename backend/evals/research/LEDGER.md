# Promise Ledger accuracy

Run 12 Nov 2026 15:02 IST: `python -m evals.research.ledger_report` over every stored dossier.

## Quotes and verdicts per ticker

Quotes: every distinct quote a dossier cites from a transcript, deck or annual report (all sections — ledger, analysts, drivers, risks, bull/bear), re-checked against the stored text of the page it cites. n = scored promises (kept + missed + goalposts moved + quietly dropped); the % is shown only from n ≥ 5.

| Ticker | Promises | Kept | Missed | Goalposts moved | Quietly dropped | Not yet due | Can't score | Credibility (kept of n) | Settled by code / model | Quotes on cited page |
|---|---|---|---|---|---|---|---|---|---|---|
| BAJFINANCE | 37 | 8 | 4 | 1 | 0 | 15 | 9 | 8 of 13 · 62% | 13 / 0 | 69/69 |
| HDFCBANK | 13 | 1 | 0 | 0 | 0 | 4 | 8 | 1 of 1 | 0 / 1 | 25/25 (3 elided) |
| INFY | 18 | 4 | 1 | 1 | 0 | 5 | 7 | 4 of 6 · 67% | 6 / 0 | 51/51 |
| JPOLYINVST | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | 0 / 0 | 0/0 |
| LAXMIDENTL | 16 | 1 | 2 | 0 | 1 | 6 | 6 | 1 of 4 | 3 / 0 | 29/29 |
| PERSISTENT | 11 | 1 | 0 | 1 | 0 | 4 | 5 | 1 of 2 | 1 / 1 | 30/30 |
| POLYCAB | 24 | 0 | 0 | 2 | 0 | 8 | 14 | 0 of 2 | 0 / 2 | 61/61 |

**265 of 265 cited quotes are on their cited page** (100.0%), across 119 promises in 7 dossiers. 3 of them are analyst questions shortened with "..." — every part is verbatim on the cited page; the rest match as one passage. Quotes that matched only after normalisation (line-break hyphens, curly quotes, whitespace) count as on the page.

## Independent audit (sample)

11 Nov 2026, 16:20 IST: five verdicts drawn with `random.Random(1111)` from the 11 scored verdicts then stored (forced: one missed, one goalposts moved, one model-judged; two at random). A fresh agent that had not seen the build downloaded the PDFs from BSE itself and read every cited page.

| # | Ticker | Verdict (by) | Quote 1 on page | Quote 2 on page | Numbers match | Verdict follows |
|---|---|---|---|---|---|---|
| 1 | BAJFINANCE | missed (code): MSME growth 10–12% FY26 → 6% | yes p4 | yes p4 | yes | yes |
| 2 | INFY | goalposts moved (code): FY27 CC growth 1.5–3.5% → 1–2% | yes p4 | yes p4 | yes | yes |
| 3 | POLYCAB | goalposts moved (model): EPC margin "high" → "mid-to-high single digits" | yes p7 | yes p8 | yes | yes, soft |
| 4 | BAJFINANCE | missed (code): franchise ≥ 120 M FY26 → 119.3 M | yes p4 | yes p3 | yes | yes, debatable |
| 5 | PERSISTENT | kept (code): ETR 23–23.5% FY25 → 23.2% | yes p14 | yes p13 | yes | yes |

Result: 10/10 quotes on their cited pages, numbers correct, 5/5 verdicts follow from the evidence. Items 3 and 4 are softer by nature (an undated outlook; a projection phrased as "well on course"); the verdict reason quotes both calls so a reader can judge. Full notes in docs/PLAN.md.

