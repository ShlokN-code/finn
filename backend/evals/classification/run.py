"""Classification eval: accuracy of the ladder on a labelled set of real NSE filings.

python -m evals.classification.run            # rules only (tiers a+b); model-tier items count as abstained
python -m evals.classification.run --model    # full ladder with the cheap model (uses the LLM cache/log)

Labels in labelled.jsonl were written by Claude from the subject + exchange label and are marked
'needs review' until a human checks them (see `note` for the uncertain ones).
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from finn.classification.ladder import Classifier
from finn.sources.nse import announcement_to_filing

HERE = Path(__file__).resolve().parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", action="store_true")
    args = ap.parse_args()
    items = [json.loads(line) for line in (HERE / "labelled.jsonl").read_text().splitlines() if line.strip()]

    router, conn = None, None
    if args.model:
        from finn.db import connect
        from finn.ingest.pipeline import make_classifier

        conn = connect()

        class _R:  # minimal Run stand-in for make_classifier
            pass

        r = _R()
        r.conn = conn
        clf, router = make_classifier(r, None)  # no PDF fetcher: subject-only (cheaper, deterministic)
    else:
        clf = Classifier(None)

    per_tier: dict[str, Counter] = defaultdict(Counter)
    wrong = []
    for it in items:
        f = announcement_to_filing(it["row"])
        c = clf.classify(f)
        ok = str(c.category) == it["label"]
        per_tier[c.tier]["n"] += 1
        per_tier[c.tier]["correct"] += ok
        if not ok and c.tier != "failed":
            wrong.append((c.tier, f.symbol, it["label"], str(c.category), f.subject[:90]))

    n = len(items)
    decided = sum(t["n"] for k, t in per_tier.items() if k != "failed")
    correct = sum(t["correct"] for t in per_tier.values())
    print(f"labelled filings: {n}   mode: {'full ladder' if args.model else 'rules only'}")
    print(f"{'tier':10}{'n':>5}{'correct':>9}{'accuracy':>10}")
    for tier in ("exchange", "rule", "model", "failed"):
        t = per_tier.get(tier)
        if t:
            acc = "—" if tier == "failed" else f"{100 * t['correct'] / t['n']:.0f}%"
            print(f"{tier:10}{t['n']:>5}{t['correct']:>9}{acc:>10}")
    print(f"\naccuracy on decided: {100 * correct / max(decided, 1):.1f}% ({correct}/{decided}); "
          f"coverage {100 * decided / n:.0f}%; overall {100 * correct / n:.1f}%")  # fmt: skip
    if router:
        print(f"llm: {router.stats.as_dict()}")
    if wrong:
        print("\nmisses:")
        for w in wrong:
            print(f"  [{w[0]}] {w[1]}: expected {w[2]}, got {w[3]} — {w[4]}")
    if conn:
        conn.close()


if __name__ == "__main__":
    main()
