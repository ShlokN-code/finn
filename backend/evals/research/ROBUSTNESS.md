# Robustness: random NSE tickers through the deployed app

Draws: `python -m evals.research.draw_unseen --seed <seed> --robust 5` (seed logged per run).

## Run 12 Nov 2026 16:46 IST (seed 20261112, deployed 2beb233)

| Ticker | Build | Time | Calls | Sections ready | Ledger | Ask | Brief |
|---|---|---|---|---|---|---|---|
| HGINFRA | partial | 498 s | — () | 8/10 | 20 promises | not_found · unsupported_number | HTTP 200, 0 cards |
| TATACAP | failed | 120 s | — () | 6/10 | 22 promises | answered | HTTP 200, 0 cards |
| HCC | partial | 135 s | — () | 8/10 | 21 promises | answered | HTTP 200, 0 cards |
| PGEL | partial | 80 s | — () | 8/10 | 41 promises | answered | HTTP 200, 0 cards |
| JASH | partial | 112 s | — () | 8/10 | 49 promises | answered | HTTP 200, 0 cards |

<details><summary>Section states</summary>

- **HGINFRA**: snapshot ready, trajectory ready, ledger ready, cash_quality ready, balance_sheet ready, analysts ready, red_flags building · not_built_yet, bull_bear partial · not_found_in_sources, drivers ready, exchange_data building · not_built_yet
- **TATACAP**: snapshot partial · not_built_yet, trajectory ready, ledger ready, cash_quality unavailable · not_meaningful_for_lenders, balance_sheet ready, analysts ready, red_flags building · not_built_yet, bull_bear building · not_built_yet, drivers ready, exchange_data building · not_built_yet
- **HCC**: snapshot ready, trajectory ready, ledger ready, cash_quality ready, balance_sheet ready, analysts ready, red_flags building · not_built_yet, bull_bear partial · not_found_in_sources, drivers ready, exchange_data building · not_built_yet
- **PGEL**: snapshot ready, trajectory ready, ledger ready, cash_quality ready, balance_sheet ready, analysts ready, red_flags building · not_built_yet, bull_bear partial · not_found_in_sources, drivers ready, exchange_data building · not_built_yet
- **JASH**: snapshot ready, trajectory ready, ledger ready, cash_quality ready, balance_sheet ready, analysts ready, red_flags building · not_built_yet, bull_bear partial · not_found_in_sources, drivers ready, exchange_data building · not_built_yet

</details>


## Run 12 Nov 2026 16:56 IST (rerun after fix, deployed 8252712)

| Ticker | Build | Time | Calls | Sections ready | Ledger | Ask | Brief |
|---|---|---|---|---|---|---|---|
| TATACAP | partial | 369 s | — () | 7/10 | 22 promises | answered | HTTP 200, 0 cards |

<details><summary>Section states</summary>

- **TATACAP**: snapshot ready, trajectory ready, ledger ready, cash_quality unavailable · not_meaningful_for_lenders, balance_sheet ready, analysts ready, red_flags building · not_built_yet, bull_bear partial · not_found_in_sources, drivers ready, exchange_data building · not_built_yet

</details>

