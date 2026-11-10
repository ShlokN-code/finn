# evals

Small labelled sets. Accuracy is reported in the root README.

## classification/

- `labelled.jsonl`: 60 real NSE announcements (raw exchange row + expected FINN category). Labels were written by Claude from the subject and exchange label; `note` flags the uncertain ones. **Needs human review.**
- `run.py`: runs the classification ladder and reports accuracy per tier.
  - `python -m evals.classification.run`: rules only. Filings that would go to the model count as abstained.
  - `python -m evals.classification.run --model`: full ladder with Gemini. Needs `.env`; calls are cached in `llm_calls`.
- Known bias: the rules were tuned on the same Aug–Nov 2026 filings. Add held-out filings (other symbols or months) before trusting the number.
