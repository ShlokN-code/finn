"""Step 6 — JUDGE (strong call #1): qualitative promises and cross-call patterns that code can't score.

Code picks the candidates (qualitative promises, and undated numeric ones whose later restatements may move the
goalposts), retrieves the best passages from LATER calls for each (BM25), and asks the strong model for a verdict
that must quote one of those passages. Code then checks every evidence quote against the passage text and requires
evidence from a later call than the promise for kept / missed / goalposts moved — "citing both calls". The model can
never assert 'quietly dropped' (code's text search owns that), and anything it can't support becomes "Can't score".

The prompt has no 'today' in it, so an unchanged dossier makes no strong call (the router's cache answers).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from finn.citations import quote_in_text
from finn.llm import LLMRequest
from finn.models import Claim
from finn.models.research import Promise
from finn.research.bm25 import BM25, passages
from finn.research.checker import Checker
from finn.research.ledger import Call

log = logging.getLogger("finn.research.judge")

PROMPT_VERSION = "v2"
PURPOSE = f"research.judge.{PROMPT_VERSION}"
MAX_CANDIDATES = 25
PASSAGES_EACH = 3

SYSTEM = """You audit whether a listed Indian company's management kept its promises, using ONLY the passages given
(verbatim excerpts from the company's own later earnings calls). Never use outside knowledge or news.
For each promise choose:
- kept: a later passage says it was done or achieved as promised.
- missed: a later passage says it did not happen, failed, or fell short.
- goalposts_moved: a later passage pushes the date out, shrinks the scope, or replaces it with a weaker target.
- raised: a later passage sets a more ambitious target for the same thing (not a verdict, just a revision).
- not_yet_due: a later passage says it is still in progress and the date has not passed.
- cant_score: the passages don't say.
Use kept or missed only when the passage itself states the outcome ("we launched", "we achieved", "we could not").
Never compare numbers yourself: if deciding would need comparing figures (e.g. growth vs a range or vs the
industry), answer cant_score.
For kept, missed, goalposts_moved and raised you MUST quote the passage (8–40 words, copied exactly) and give its id.
Keep reasons under 25 words, plain and factual. Do not calculate anything."""

SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {"type": "array", "items": {"type": "object", "properties": {
            "id": {"type": "string"},
            "verdict": {"type": "string",
                        "enum": ["kept", "missed", "goalposts_moved", "raised", "not_yet_due", "cant_score"]},
            "passage_id": {"type": "string", "nullable": True},
            "quote": {"type": "string", "nullable": True},
            "reason": {"type": "string"},
        }, "required": ["id", "verdict", "reason"]}},
    },
    "required": ["verdicts"],
}  # fmt: skip


@dataclass
class JudgeResult:
    judged: int = 0
    changed: int = 0
    rejected: int = 0
    model: str | None = None


def candidates(promises: list[Promise]) -> list[Promise]:
    out = [p for p in promises if p.verdict in ("cant_score", "not_yet_due")
           and (p.measure == "qualitative" or p.period is None)]  # fmt: skip
    out.sort(key=lambda p: p.statements[-1].made_on, reverse=True)
    return out[:MAX_CANDIDATES]


def build_request(promises: list[Promise], calls: list[Call], tags: dict) -> tuple[LLMRequest | None, dict]:
    """The strong-model request (None when there is nothing to judge) and the passage index it refers to."""
    cands = candidates(promises)
    if not cands:
        return None, {}
    made = {c.doc_id: c.made_on for c in calls}
    label = {c.doc_id: c.label for c in calls}
    index = BM25([ps for c in calls for ps in passages(c.doc_id, c.pages)])
    pid_map: dict[str, tuple] = {}
    blocks = []
    for i, p in enumerate(cands, start=1):
        last = p.statements[-1]
        later = {doc for doc, d in made.items() if d > last.made_on}
        if not later:
            continue
        query = " ".join([p.metric, p.statement, last.quote.quote or ""])
        hits = index.search(query, PASSAGES_EACH, where=lambda ps, later=later: ps.doc_id in later)
        if not hits:
            continue
        lines = [f"PROMISE {p.id}: \"{last.quote.quote}\" — {last.call_label}, said {last.made_on:%d %b %Y}; "
                 f"period: {p.period.label if p.period else last.period_text or 'none given'}"]  # fmt: skip
        for j, (_, ps) in enumerate(hits, start=1):
            pid = f"E{i}.{j}"
            pid_map[pid] = (ps, p.id)
            lines.append(f"  [{pid}] {label[ps.doc_id]} ({made[ps.doc_id]:%d %b %Y}), p.{ps.page}: {ps.text}")
        blocks.append("\n".join(lines))
    if not blocks:
        return None, {}
    prompt = "Promises and the later-call passages that may speak to them:\n\n" + "\n\n".join(blocks)
    return LLMRequest(purpose=PURPOSE, system=SYSTEM, prompt=prompt, schema=SCHEMA, max_output_tokens=12000,
                      timeout_s=90, thinking_budget=1024, tags=tags), pid_map  # fmt: skip


def apply(promises: list[Promise], data: dict, pid_map: dict, calls: list[Call], model: str,
          settled: dict) -> JudgeResult:  # fmt: skip
    """Validate the model's verdicts and write the ones that survive into the promises (in place)."""
    by_id = {p.id: p for p in promises}
    docs = {c.doc_id: c for c in calls}
    checkers: dict[str, Checker] = {}
    res = JudgeResult(model=model)
    for v in data.get("verdicts") or []:
        p = by_id.get(v.get("id"))
        if p is None:
            continue
        res.judged += 1
        verdict = v.get("verdict")
        if verdict not in ("kept", "missed", "goalposts_moved", "raised"):
            continue  # 'not yet due' / 'can't score' from the model never overrides code
        if verdict in ("kept", "missed") and p.measure != "qualitative":
            res.rejected += 1  # a numeric target is kept or missed only by code's comparison, never the model's
            continue
        hit = pid_map.get(v.get("passage_id") or "")
        quote = (v.get("quote") or "").strip()
        if not hit or hit[1] != p.id or not quote or not quote_in_text(quote, hit[0].text):
            res.rejected += 1
            continue
        ps = hit[0]
        call = docs.get(ps.doc_id)
        if call is None or call.made_on <= p.statements[-1].made_on:
            res.rejected += 1  # evidence must come from a later call than the promise
            continue
        chk = checkers.setdefault(call.doc_id, Checker(call.pages))
        loc = chk.locate(quote, ps.page)
        if loc is None:
            res.rejected += 1
            continue
        evidence = call.cite(loc.page, loc.quote)
        if verdict == "raised":
            p.revision = "raised"
            res.changed += 1
            continue
        reason = " ".join(str(v.get("reason") or "").split())[:240] or verdict.replace("_", " ").capitalize()
        p.verdict, p.verdict_by, p.verdict_model = verdict, "model", model
        if verdict == "goalposts_moved" and p.revision == "none":
            p.revision = "revised"
        p.verdict_reason = Claim(text=reason, status="verified", citations=[p.statements[-1].quote, evidence])
        p.dropped_note = None
        settled[p.id] = call.made_on
        res.changed += 1
    return res
