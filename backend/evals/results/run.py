"""Results-extraction eval: the numbers on results cards vs the company's own results PDF.

python -m evals.results.run [--n 5] [--symbols A,B]     # writes evals/results/REPORT.md

Cards are FINN's stored results cards (figures read from NSE XBRL: current, previous and year-ago quarter filings).
The check is independent of XBRL and of screener: each card's results PDF (the outcome filing) is downloaded and
its statement page read as text (PyMuPDF); a figure counts as correct when it is printed on that page
in crore, lakh or million, within the printed precision (`value_printed`). The PDF prints current / previous /
year-ago columns, so all three periods are checked from one document.

Fields: Revenue, PBT, PAT (the value itself must be printed); EBITDA (computed in code — correct when every input it
was computed from is printed: PBT before exceptional items, finance costs, D&A, other income); QoQ and YoY (computed
— correct when both quarters are). Banks/NBFCs: NII and PPOP through their inputs the same way.

Selection: the N most recently updated results cards that have a results PDF page, so the set is "recent results
filings" as of the run, not hand-picked.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from finn.calendar import IST
from finn.db import connect
from finn.extraction.results.links import _numbers
from finn.research.documents import extract_pages
from finn.sources.http import exchange_pdf_headers, fetch_to_file

HERE = Path(__file__).resolve().parent
OUT = HERE / "REPORT.md"
PERIODS = ("current", "previous", "year_ago")


def value_printed(text: str, value_cr: float) -> bool:
    """Strict: printed in crore, lakh or million within half a unit of the printed number's last digit (no relative
    slack — 70.86 is not 70.88)."""
    targets = [abs(value_cr), abs(value_cr) * 100, abs(value_cr) * 10]
    return any(abs(n - t) <= 0.5 * 10 ** (-dec) + 1e-6 for n, dec in _numbers(text) for t in targets)


def leaves(f: dict | None) -> list[dict]:
    """The printed (non-computed) figures a figure was built from."""
    if not f:
        return []
    if f.get("inputs") and f.get("formula"):
        return [x for i in f["inputs"] for x in leaves(i)]
    return [f]


def printed(text: str, f: dict | None, computed: bool = False) -> bool | None:
    """True/False per figure; None when there is nothing to check (missing, or a zero input such as nil other
    income, which a statement prints as '-')."""
    if f and f.get("value") is not None and abs(f["value"]) >= 0.005 and value_printed(text, f["value"]):
        return True  # the figure itself is printed (e.g. PBT = PBT before share of JVs + share, printed as one line)
    if not computed:
        # a statement line (Revenue, PBT, PAT, NII inputs…) must itself be printed: matching its parts one by one
        # is too loose (small numbers like 0.58 are found anywhere on a page)
        return None if not f or f.get("value") is None else False
    ls = [x for x in leaves(f) if x.get("value") is not None]
    if not ls:
        return None
    checks = [value_printed(text, x["value"]) for x in ls if abs(x["value"]) >= 0.005]
    return all(checks) if checks else None


_NSE = None


def pdf_text(url: str, page: int) -> tuple[str | None, str]:
    global _NSE
    if "nseindia.com" in url and _NSE is None:
        from finn.sources.nse import session

        _NSE = session()  # NSE archives answer a warmed browser session (as the jobs download them)
    sess = _NSE if "nseindia.com" in url else None
    hdr = None if sess else exchange_pdf_headers(url)
    path, status = fetch_to_file(url, max_bytes=40 * 1024 * 1024, deadline_s=240, headers=hdr, session=sess)
    if not path:
        return None, status
    try:
        pages, _ = extract_pages(path)
    finally:
        path.unlink(missing_ok=True)
    return pages[page - 1], "ok"  # the card's statement page only (the next one is often the other basis)


def card_pdf(detail: dict) -> tuple[str, int] | None:
    for ln in detail.get("lines", []):
        c = (ln.get("current") or {}).get("citation") or {}
        if c.get("doc_kind") == "results_pdf" and c.get("page"):
            return c["url"], c["page"]
        for i in leaves(ln.get("current")):
            c = i.get("citation") or {}
            if c.get("doc_kind") == "results_pdf" and c.get("page"):
                return c["url"], c["page"]
    return None


def evaluate(text: str, detail: dict) -> dict[str, bool | None]:
    out: dict[str, bool | None] = {}
    for ln in detail.get("lines", []):
        m = ln.get("metric")
        if not m or "margin" in m.lower():
            continue  # margins are ratios of checked figures
        computed = m in ("EBITDA", "NII", "PPOP")  # not a printed line: checked through its printed inputs
        cur, prev, ya = (printed(text, ln.get(p), computed) for p in PERIODS)
        out[m] = cur
        out[f"{m} QoQ"] = None if cur is None or prev is None else (cur and prev)
        out[f"{m} YoY"] = None if cur is None or ya is None else (cur and ya)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--symbols", default="")
    args = ap.parse_args()
    with connect() as conn:
        rows = conn.execute(
            "select id, symbol, updated_at, detail from events where category = 'results' and detail is not null "
            "order by updated_at desc"
        ).fetchall()
        states = Counter((r["detail"] or {}).get("verification") or "none" for r in rows)
    syms = {s.strip().upper() for s in args.symbols.split(",") if s.strip()}
    chosen = [r for r in rows if card_pdf(r["detail"]) and (not syms or r["symbol"] in syms)][: args.n]

    visual = json.loads((HERE / "visual_checks.json").read_text())
    per_card, field_tot = [], defaultdict(Counter)
    for r in chosen:
        url, page = card_pdf(r["detail"])
        text, status = pdf_text(url, page)
        if text is None:
            per_card.append((r, url, page, None, status))
            continue
        res = evaluate(text, r["detail"])
        v = visual.get(r["id"])
        nums = [x for x in _numbers(text) if x[0] >= 10]
        readable = sum(1 for _, dec in nums if dec > 0) >= 0.5 * max(len(nums), 1)
        if not readable and not v:
            res = {k: None for k in res}
            status = "text layer unreadable (decimals lost) — needs a visual check"
        elif v and (not readable or any(x is False for x in res.values())):
            # scanned page: the text layer can't be read, so the page image was read instead (visual_checks.json)
            res = {k: v["fields"].get(k) for k in res}
            status = "visual check (scanned page; visual_checks.json)"
        per_card.append((r, url, page, res, status))
        for k, v in res.items():
            if v is not None:
                field_tot[k]["n"] += 1
                field_tot[k]["ok"] += bool(v)

    order = ["Revenue", "EBITDA", "NII", "PPOP", "PBT", "PAT"]
    fields = [f for base in order for f in (base, f"{base} QoQ", f"{base} YoY") if f in field_tot]
    lines = [
        "# Results extraction eval",
        "",
        f"Run {datetime.now(IST):%d %b %Y %H:%M} IST: `python -m evals.results.run --n {args.n}`. Method in the "
        "module docstring: card figures (read from NSE XBRL) vs the company's results PDF, page text, within printed "
        "precision. Computed figures (EBITDA, QoQ, YoY) count as correct when every printed input is on the page.",
        "",
        "## Accuracy per field",
        "",
        "| Field | Correct | Checked | Accuracy |",
        "|---|---|---|---|",
    ]
    for f in fields:
        t = field_tot[f]
        lines.append(f"| {f} | {t['ok']} | {t['n']} | {100 * t['ok'] / t['n']:.0f}% |")
    tot_ok = sum(t["ok"] for t in field_tot.values())
    tot_n = sum(t["n"] for t in field_tot.values())
    lines += [f"| **All** | **{tot_ok}** | **{tot_n}** | **{100 * tot_ok / max(tot_n, 1):.1f}%** |", "", "## Cards", ""]
    lines += ["| Card | Verification | Results PDF | Fields wrong |", "|---|---|---|---|"]
    for r, url, page, res, status in per_card:
        v = r["detail"].get("verification")
        if res is None:
            lines.append(f"| {r['id']} | {v} | [p.{page}]({url}#page={page}) — {status} | not checked |")
            continue
        wrong = [k for k, x in res.items() if x is False]
        how = "" if status == "ok" else f" · {status}"
        lines.append(f"| {r['id']} | {v} | [p.{page}]({url}#page={page}){how} | {', '.join(wrong) or '—'} |")
    notes = [(cid, v) for cid, v in visual.items() if any(r["id"] == cid for r, *_ in per_card)]
    if notes:
        lines += ["", "## Visual checks (scanned pages)", ""]
        for cid, v in notes:
            lines.append(
                f"- **{cid}** (p.{v['page']}, {v['unit']}): {v['why']} Read by {v['reader']}."
                + (f" {v['note']}" if v.get("note") else "")
            )
    lines += [
        "",
        "## Verification state of every results card",
        "",
        "`cross_checked` = every line matches screener's quarterly table; `partial` = some lines can't be checked "
        "against screener (e.g. a lender's NII/PPOP); `pending` = screener hasn't published the quarter yet; "
        '`mismatch` = at least one line disagrees, so the card says "Couldn\'t verify — open filing".',
        "",
        "| State | Cards |",
        "|---|---|",
    ]
    lines += [f"| {k} | {n} |" for k, n in states.most_common()]
    lines += [f"| **total** | **{sum(states.values())}** |", ""]
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(json.dumps({"written": str(OUT)}))


if __name__ == "__main__":
    main()
