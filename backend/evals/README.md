# evals

Small labelled sets and the reports they produce. The headline numbers are in the [root README](../../README.md#evals). Run everything from `backend/`. Model calls are cached in `llm_calls`, so a rerun on unchanged inputs costs nothing.

## classification/
- `labelled.jsonl` is the **dev set**: 60 real NSE announcements from portfolio companies, Aug–Nov 2026.
  - Claude drafted the labels. The product owner reviewed them on 10 Nov: 4 corrected, 7 confirmed against the PDF.
  - The rules were written from the same months of filings, so the dev score is optimistic.
- `heldout.jsonl` is the **held-out set**: 20 filings from 11–12 Nov 2026, from companies FINN had never seen.
  - Drawn by `draw_heldout.py --seed 20261112`, stratified by NSE label, one filing per company.
  - `heldout_raw.jsonl` holds the raw exchange rows. `heldout_to_label.csv` is the sheet the labeller got: the category list and the material-over-routine rule only.
  - Labelled blind by an independent agent that read each PDF. Its labels are in `heldout_agent_labels.jsonl`, committed in `5e015db` before the classifier ran.
  - The product owner reviewed the 6 disagreements: 4 confirmed, 2 corrected. Corrected rows say so in `labelled_by` and keep the agent's label in `note`.
  - **Frozen:** no rule or prompt is changed because of a held-out miss.
- `run.py --set dev|heldout`: rules only. Filings that would go to the model count as abstained. Add `--model` for the full ladder (needs `.env`).

## results/
- `run.py [--n 5] [--symbols …]` checks card figures (read from NSE XBRL) against the company's own results PDF, within printed precision, and writes [REPORT.md](results/REPORT.md).
- `visual_checks.json` records scanned pages that were read from the rendered image.

## research/
- `ledger_report.py` writes [LEDGER.md](research/LEDGER.md): it checks every cited quote against its stored page, adds the independent audit of 5 verdicts, and builds the per-ticker table.
- `draw_unseen.py --seed … [--robust N]` draws NSE tickers FINN has never built, from a logged seed. `nifty100_2026-11-11.csv` is the Nifty 100 list it uses.
- `robustness.py --symbols …` runs drawn tickers through the deployed app (build, Ask, Brief) and writes [ROBUSTNESS.md](research/ROBUSTNESS.md).

## Other
- `cost_report.py` writes [COST.md](COST.md): model calls, tokens and list-price cost per job, plus free-tier usage.
- [PUSH_CHECK.md](PUSH_CHECK.md) traces one real filing from the scheduler to Telegram.
