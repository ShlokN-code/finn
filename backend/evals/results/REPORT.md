# Results extraction eval

Run 12 Nov 2026 15:21 IST: `python -m evals.results.run --n 5`. Method in the module docstring: card figures (read from NSE XBRL) vs the company's results PDF, page text, within printed precision. Computed figures (EBITDA, QoQ, YoY) count as correct when every printed input is on the page.

## Accuracy per field

| Field | Correct | Checked | Accuracy |
|---|---|---|---|
| Revenue | 5 | 5 | 100% |
| Revenue QoQ | 5 | 5 | 100% |
| Revenue YoY | 5 | 5 | 100% |
| EBITDA | 5 | 5 | 100% |
| EBITDA QoQ | 5 | 5 | 100% |
| EBITDA YoY | 5 | 5 | 100% |
| PBT | 5 | 5 | 100% |
| PBT QoQ | 4 | 5 | 80% |
| PBT YoY | 4 | 5 | 80% |
| PAT | 5 | 5 | 100% |
| PAT QoQ | 5 | 5 | 100% |
| PAT YoY | 4 | 5 | 80% |
| **All** | **57** | **60** | **95.0%** |

## Cards

| Card | Verification | Results PDF | Fields wrong |
|---|---|---|---|
| TATAPOWER:results:Q2 FY27 | partial | [p.8](https://nsearchives.nseindia.com/corporate/VPTPCL_11112026172001_outcome_final.pdf#page=8) | — |
| KALYANKJIL:results:Q2 FY27 | cross_checked | [p.12](https://nsearchives.nseindia.com/corporate/KALYANKJIL_10112026170450_Results_q2_Signed.pdf#page=12) · visual check (scanned page; visual_checks.json) | — |
| TITAGARH:results:Q2 FY27 | cross_checked | [p.11](https://nsearchives.nseindia.com/corporate/TWL_10112026204612_OutcomeofBM10112026.pdf#page=11) · visual check (scanned page; visual_checks.json) | PBT QoQ, PBT YoY, PAT YoY |
| COCHINSHIP:results:Q2 FY27 | cross_checked | [p.10](https://nsearchives.nseindia.com/corporate/Aswi4739_10112026142305_SE_Intimation_Sgd.pdf#page=10) | — |
| TATASTEEL:results:Q2 FY27 | cross_checked | [p.15](https://nsearchives.nseindia.com/corporate/NIDHIFADNAVIS_07112026130531_BOARDOUTCOME-NOV7.pdf#page=15) | — |

## Visual checks (scanned pages)

- **KALYANKJIL:results:Q2 FY27** (p.12, Rs. in Millions): Scanned statement with a poor OCR text layer ('Jewelters lndia'), so the text check can't read its numbers. Read by Claude, from the rendered page image (110 dpi), 12 Nov 2026.
- **TITAGARH:results:Q2 FY27** (p.11, Rs. in Crores): The text layer drops decimal points ('8201' for 82.01), so the text check can't tell 57 from 57.27. Read by Claude, from the rendered page image (110 dpi), 12 Nov 2026. The year-ago column is 'Unaudited (Restated) (Refer Note 4)': Sep 2025 was restated for discontinued operations. The card's year-ago PBT/PAT are as first reported in the Sep 2025 XBRL (57.27 / 37.00); the previous-quarter PBT is 70.86 in the Q1 XBRL vs 70.88 printed here. EBITDA's inputs match (year-ago 83.62 printed inputs vs 83.63 on the card: rounding).

## Verification state of every results card

`cross_checked` = every line matches screener's quarterly table; `partial` = some lines can't be checked against screener (e.g. a lender's NII/PPOP); `pending` = screener hasn't published the quarter yet; `mismatch` = at least one line disagrees, so the card says "Couldn't verify — open filing".

| State | Cards |
|---|---|
| cross_checked | 14 |
| partial | 2 |
| mismatch | 1 |
| **total** | **17** |

