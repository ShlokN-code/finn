"""Promise Ledger accuracy → evals/research/LEDGER.md.

python -m evals.research.ledger_report

For every stored dossier: the ledger's verdict counts (n per ticker), and every quote the dossier cites from a
transcript, deck or annual report re-checked against the stored text of the page it cites (`research_doc_text`,
the same text the build read; fuzzy match after normalising whitespace, quote marks and line-break hyphens). The
independent audit (a fresh agent reading the PDFs itself) is the sample recorded in PLAN.md, reproduced here.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from finn.calendar import IST
from finn.citations import quote_in_text
from finn.db import connect
from finn.research import store

HERE = Path(__file__).resolve().parent
OUT = HERE / "LEDGER.md"
DOC_TYPES = {"concall_transcript", "investor_presentation", "annual_report"}

AUDIT = [
    ("BAJFINANCE", "missed (code): MSME growth 10–12% FY26 → 6%", "p4", "p4", "yes", "yes"),
    ("INFY", "goalposts moved (code): FY27 CC growth 1.5–3.5% → 1–2%", "p4", "p4", "yes", "yes"),
    ("POLYCAB", "goalposts moved (model): EPC margin \"high\" → \"mid-to-high single digits\"", "p7", "p8", "yes",
     "yes, soft"),
    ("BAJFINANCE", "missed (code): franchise ≥ 120 M FY26 → 119.3 M", "p4", "p3", "yes", "yes, debatable"),
    ("PERSISTENT", "kept (code): ETR 23–23.5% FY25 → 23.2%", "p14", "p13", "yes", "yes"),
]  # fmt: skip


def citations(obj, path=""):
    """Every citation-shaped dict in a dossier payload, with the section it sits in."""
    if isinstance(obj, dict):
        if "source_type" in obj and "url" in obj and "retrieved_at" in obj:
            yield path.split(".")[0], obj
        for k, v in obj.items():
            yield from citations(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for v in obj:
            yield from citations(v, path)


def main() -> None:
    rows, totals = [], Counter()
    page_cache: dict[str, list[str] | None] = {}
    with connect() as conn:
        syms = [r["symbol"] for r in conn.execute("select symbol from dossiers order by symbol").fetchall()]
        docs = {r["url"]: r["sha256"] for r in conn.execute(
            "select url, sha256 from research_documents where sha256 is not null").fetchall()}  # fmt: skip
        for sym in syms:
            row = store.get_dossier_row(conn, sym)
            d = store.load_dossier(row)
            if d is None:
                continue
            v = Counter(p.verdict for p in d.ledger.promises)
            by = Counter(p.verdict_by for p in d.ledger.promises if p.verdict in ("kept", "missed", "goalposts_moved"))
            seen, ok, elided, missing = set(), 0, 0, []
            for section, c in citations(row["payload"]):
                if c.get("source_type") not in DOC_TYPES or not c.get("quote") or not c.get("page"):
                    continue
                key = (c["url"], c["page"], c["quote"])
                if key in seen:
                    continue
                seen.add(key)
                sha = docs.get(c["url"])
                if sha not in page_cache:
                    page_cache[sha] = store.load_text(conn, sha) if sha else None
                pages = page_cache[sha]
                text = pages[c["page"] - 1] if pages and 1 <= c["page"] <= len(pages) else None
                parts = [x.strip() for x in re.split(r"\.\.\.|…", c["quote"]) if len(x.strip()) >= 8]
                if text and quote_in_text(c["quote"], text):
                    ok += 1
                elif text and len(parts) > 1 and all(quote_in_text(x, text) for x in parts):
                    ok += 1
                    elided += 1  # an analyst question shortened with "...": every part is verbatim on the page
                else:
                    missing.append((section, c["page"], c["quote"][:80]))
            cr = d.ledger.credibility
            tally = ("—" if cr is None else f"{cr.kept} of {cr.n}"
                     + (f" · {cr.score_pct:.0f}%" if cr.shown and cr.score_pct else ""))  # fmt: skip
            rows.append([sym, len(d.ledger.promises), v["kept"], v["missed"], v["goalposts_moved"],
                         v["quietly_dropped"], v["not_yet_due"], v["cant_score"], tally,
                         f"{by['code']} / {by['model']}",
                         f"{ok}/{len(seen)}" + (f" ({elided} elided)" if elided else "")])  # fmt: skip
            totals["elided"] += elided
            totals["quotes"] += len(seen)
            totals["ok"] += ok
            totals["promises"] += len(d.ledger.promises)
            for m in missing:
                print(f"  {sym}: quote not on cited page — {m}")

    head = ["Ticker", "Promises", "Kept", "Missed", "Goalposts moved", "Quietly dropped", "Not yet due",
            "Can't score", "Credibility (kept of n)", "Settled by code / model", "Quotes on cited page"]  # fmt: skip
    md = [
        "# Promise Ledger accuracy",
        "",
        f"Run {datetime.now(IST):%d %b %Y %H:%M} IST: `python -m evals.research.ledger_report` over every stored "
        "dossier.",
        "",
        "## Quotes and verdicts per ticker",
        "",
        "Quotes: every distinct quote a dossier cites from a transcript, deck or annual report (all sections — "
        "ledger, analysts, drivers, risks, bull/bear), re-checked against the stored text of the page it cites. "
        "n = scored promises (kept + missed + goalposts moved + quietly dropped); the % is shown only from n ≥ 5.",
        "",
        "| " + " | ".join(head) + " |",
        "|" + "---|" * len(head),
    ]
    md += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    md += [
        "",
        f"**{totals['ok']} of {totals['quotes']} cited quotes are on their cited page** "
        f"({100 * totals['ok'] / max(totals['quotes'], 1):.1f}%), across {totals['promises']} promises in "
        f'{len(rows)} dossiers. {totals["elided"]} of them are analyst questions shortened with "..." — every '
        "part is verbatim on the cited page; the rest match as one passage. Quotes that matched only after "
        "normalisation (line-break hyphens, curly quotes, whitespace) count as on the page.",
        "",
        "## Independent audit (sample)",
        "",
        "11 Nov 2026, 16:20 IST: five verdicts drawn with `random.Random(1111)` from the 11 scored verdicts then "
        "stored (forced: one missed, one goalposts moved, one model-judged; two at random). A fresh agent that had "
        "not seen the build downloaded the PDFs from BSE itself and read every cited page.",
        "",
        "| # | Ticker | Verdict (by) | Quote 1 on page | Quote 2 on page | Numbers match | Verdict follows |",
        "|---|---|---|---|---|---|---|",
    ]
    md += [f"| {i} | {a[0]} | {a[1]} | yes {a[2]} | yes {a[3]} | {a[4]} | {a[5]} |" for i, a in enumerate(AUDIT, 1)]
    md += [
        "",
        "Result: 10/10 quotes on their cited pages, numbers correct, 5/5 verdicts follow from the evidence. Items 3 "
        'and 4 are softer by nature (an undated outlook; a projection phrased as "well on course"); the verdict '
        "reason quotes both calls so a reader can judge. Full notes in docs/PLAN.md.",
        "",
    ]
    OUT.write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
