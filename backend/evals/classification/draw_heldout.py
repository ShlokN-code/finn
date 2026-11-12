"""Draw the blind held-out classification set (PLAN.md, Phase 5). Never runs the classifier.

python -m evals.classification.draw_heldout --seed 20261112 --from 2026-11-11 --to 2026-11-12 --n 20

- Pool: every NSE equity announcement in the window (all companies, one API call per day), minus any symbol in
  the dev set or in the `filings` table (the ~950-filing pull the rules were written from).
- Stratified across NSE's own label (`desc`): round-robin over labels in a seeded order, one filing per label
  per round, so no label dominates. At least 3 content-free subjects (only "Copy of Newspaper Publication" /
  "the captioned subject" / the label repeated), picked first.
- Writes `heldout_to_label.csv` (for the product owner: an empty `category` column, allowed categories listed at
  the top) and `heldout_raw.jsonl` (the raw exchange rows, no labels). `heldout.jsonl` is built from the two
  by `--merge` once the CSV is labelled, and committed before the first run.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
CSV_PATH = HERE / "heldout_to_label.csv"
RAW_PATH = HERE / "heldout_raw.jsonl"
OUT_PATH = HERE / "heldout.jsonl"

CATEGORIES = [
    ("results", "quarterly/annual results: intimation of the board meeting, outcome, results press release/deck, results newspaper ad"),
    ("mna", "acquisitions, mergers, demergers, stake sales, a subsidiary's IPO"),
    ("management_change", "appointment/resignation of a director, KMP, CEO/MD/CFO, company secretary, auditor"),
    ("litigation", "court/tribunal orders, regulator penalties, tax demands, disputes"),
    ("credit_rating", "rating assigned, upgraded, downgraded, reaffirmed, withdrawn"),
    ("pledging", "promoter pledge created/released/invoked"),
    ("capex", "board-approved capacity, plant, expansion spend"),
    ("press_release", "order wins, product launches, operational/business updates, other announcements"),
    ("insider_trading", "SAST / PIT disclosures of insider or promoter trades"),
    ("fund_raise", "QIP, rights, preferential issue, NCD/CP/bond allotment or issue, borrowing"),
    ("dividend", "dividend declared, record date for a dividend"),
    ("bonus_split", "bonus issue, stock split, record date for either"),
    ("earnings_call", "results call schedule, audio/video recording link, call transcript"),
    ("agm_egm", "AGM/EGM notices, outcomes, scrutiniser reports, annual report, book closure"),
    ("postal_ballot", "postal ballot notice, results, scrutiniser report"),
    ("investor_meetings", "analyst/investor meetings and conferences not about results (hidden drawer)"),
    ("routine", "known-boring compliance: trading window, ESOP allotments, compliance certificates, "
     "share-transfer/demat notices, non-material newspaper ads, policy uploads (hidden drawer)"),
]  # fmt: skip

CONTENT_FREE = re.compile(
    r"^(?:.{0,80}has informed the exchange (?:about|regarding) )?(?:copy of newspaper publication|"
    r"[^.]{0,40}captioned subject[^.]*|newspaper (?:publication|clippings?)|updates?|general updates?)\.?$",
    re.I,
)


def excluded_symbols() -> set[str]:
    syms = {json.loads(line)["row"]["symbol"] for line in (HERE / "labelled.jsonl").read_text().splitlines() if line}
    from finn.db import connect

    with connect() as conn:
        syms |= {r["symbol"] for r in conn.execute("select distinct symbol from public.filings").fetchall()}
    return syms


def fetch_day(s, d: date) -> list[dict]:
    from finn.sources.nse import _get

    dmy = d.strftime("%d-%m-%Y")
    data = _get(s, "corporate-announcements", {"index": "equities", "from_date": dmy, "to_date": dmy})
    rows = data if isinstance(data, list) else data.get("data", [])
    return [r for r in rows if isinstance(r, dict)]


def draw(rows: list[dict], n: int, seed: int, min_blind: int = 3) -> list[dict]:
    rng = random.Random(seed)
    blind = [r for r in rows if CONTENT_FREE.match(" ".join((r.get("attchmntText") or "").split()))]
    picked = rng.sample(blind, min(min_blind, len(blind)))
    seen_sym = {r["symbol"] for r in picked}
    by_desc: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r not in picked:
            by_desc[r.get("desc") or "?"].append(r)
    labels = sorted(by_desc)
    rng.shuffle(labels)
    for lab in labels:
        rng.shuffle(by_desc[lab])
    while len(picked) < n and any(by_desc.values()):
        for lab in labels:
            if len(picked) >= n:
                break
            while by_desc[lab]:
                r = by_desc[lab].pop()
                if r["symbol"] not in seen_sym:  # one filing per company keeps the set diverse
                    picked.append(r)
                    seen_sym.add(r["symbol"])
                    break
    return sorted(picked, key=lambda r: r.get("sort_date") or "")


def write(rows: list[dict], seed: int, frm: date, to: date) -> None:
    keep = ("seq_id", "symbol", "sm_name", "desc", "an_dt", "attchmntFile", "sm_isin", "exchdisstime", "sort_date",
            "attchmntText", "fileSize", "hasXbrl", "smIndustry")  # fmt: skip
    with RAW_PATH.open("w") as f:
        for r in rows:
            f.write(json.dumps({k: r.get(k) for k in keep}, ensure_ascii=False) + "\n")
    with CSV_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([f"# Blind held-out set: {len(rows)} NSE filings, {frm} to {to}, seed {seed}. Fill the "
                    "'category' column with ONE value from the list below (exact spelling). Notes are optional."])  # fmt: skip
        w.writerow(["# When a filing could be routine or material, choose the material category (DECISIONS.md)."])
        for c, hint in CATEGORIES:
            w.writerow([f"#   {c}", hint])
        w.writerow([])
        w.writerow(["n", "seq_id", "company", "symbol", "filed_ist", "nse_label", "subject", "pdf_link", "category",
                    "notes"])  # fmt: skip
        for i, r in enumerate(rows, 1):
            w.writerow([i, r.get("seq_id"), r.get("sm_name"), r.get("symbol"), r.get("an_dt"), r.get("desc"),
                        " ".join((r.get("attchmntText") or "").split()), r.get("attchmntFile"), "", ""])  # fmt: skip


def merge(labelled_by: str = "reviewer (blind)") -> int:
    """CSV labels + raw rows → heldout.jsonl (same format as labelled.jsonl)."""
    raw = {r["seq_id"]: r for r in map(json.loads, RAW_PATH.read_text().splitlines())}
    allowed = {c for c, _ in CATEGORIES}
    out, problems = [], []
    with CSV_PATH.open(newline="") as f:
        lines = [row for row in csv.reader(f) if row and not row[0].startswith("#")]
    header, body = lines[0], lines[1:]
    for row in body:
        rec = dict(zip(header, row, strict=False))
        label = (rec.get("category") or "").strip()
        if label not in allowed:
            problems.append(f"row {rec.get('n')}: category {label!r} not allowed")
            continue
        r = raw[rec["seq_id"]]
        out.append({"row": {k: r.get(k) for k in ("seq_id", "symbol", "desc", "an_dt", "attchmntFile", "sm_isin",
                                                   "exchdisstime", "sort_date", "attchmntText")},
                    "label": label, "note": (rec.get("notes") or "").strip() or None, "labelled_by": labelled_by})  # fmt: skip
    if problems:
        raise SystemExit("\n".join(problems))
    OUT_PATH.write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in out))
    return len(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20261112)
    ap.add_argument("--from", dest="frm", default=None)
    ap.add_argument("--to", default=None)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--merge", action="store_true", help="labelled CSV → heldout.jsonl")
    args = ap.parse_args()
    if args.merge:
        print(f"heldout.jsonl: {merge()} filings")
        return
    from finn.sources.nse import session

    to = date.fromisoformat(args.to) if args.to else date.today()
    frm = date.fromisoformat(args.frm) if args.frm else to - timedelta(days=1)
    s = session()
    rows, d = [], frm
    while d <= to:
        rows += fetch_day(s, d)
        d += timedelta(days=1)
    excl = excluded_symbols()
    pool = [r for r in rows if r.get("symbol") and r["symbol"] not in excl]
    picked = draw(pool, args.n, args.seed)
    write(picked, args.seed, frm, to)
    print(f"{datetime.now():%Y-%m-%d %H:%M} window {frm}..{to}: {len(rows)} announcements, {len(excl)} symbols "
          f"excluded, pool {len(pool)} from {len({r['symbol'] for r in pool})} companies, "
          f"{len({r.get('desc') for r in pool})} NSE labels → {len(picked)} drawn (seed {args.seed})")  # fmt: skip
    for r in picked:
        print(f"  {r['symbol']:12} {r.get('desc', '')[:40]:40} {' '.join((r.get('attchmntText') or '').split())[:70]}")


if __name__ == "__main__":
    main()
