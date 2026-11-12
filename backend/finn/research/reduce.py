"""Step 7 — REDUCE (strong call #2): snapshot lines, one trajectory line, 3 bull and 3 bear bullets.

The model gets only extracted facts and computed numbers, each with an id (F1, F2, …), and must cite fact ids for
every sentence. It never writes a number: numbers appear as {F12} placeholders that code replaces with the fact's
own value (rule 1 — the LLM reads, code calculates). A sentence with any other digit, or no valid fact id, is
dropped and counted. Citations come from the cited facts, so every claim links to a document page or table row.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from finn.format import money_cr
from finn.llm import LLMRequest
from finn.models import Citation, Claim, Figure
from finn.models.research import Dossier
from finn.research.ledger import Call

PROMPT_VERSION = "v4"
PURPOSE = f"research.reduce.{PROMPT_VERSION}"

SYSTEM = """You write a short, neutral research summary of an Indian listed company for a professional investor,
using ONLY the numbered facts given (from the company's own filings, calls and standardised financial tables).
Never use outside knowledge, news, opinions about the share price, or advice to buy or sell.
Rules:
- Every sentence cites the fact ids it rests on.
- Prefer placeholders for numbers: write {F12} and it is filled in from fact F12 WITH its unit (₹, Cr, %, x, days
  are included — don't add them). Only facts marked [number] have a placeholder. You may type a number only if it
  appears in a fact you cite. Never spell numbers out in words. Put fact ids in fact_ids, not in the text.
  Period names like FY26 or Q2 FY27 are fine.
- Plain English, at most 25 words per sentence. No hype words."""

PROMPT_TAIL = """Write:
- snapshot: 2–4 sentences — what the business does and how it is doing (segments, scale, recent trajectory).
- trajectory_note: 1 sentence on what is growing and what is compressing.
- bull: exactly 3 bullets — the strongest evidence-backed positives.
- bear: exactly 3 bullets — the strongest evidence-backed risks or weaknesses (missed or moved promises count)."""

_CLAIM = {"type": "object", "properties": {"text": {"type": "string"},
                                           "fact_ids": {"type": "array", "items": {"type": "string"}}},
          "required": ["text", "fact_ids"]}  # fmt: skip
SCHEMA = {
    "type": "object",
    "properties": {"snapshot": {"type": "array", "items": _CLAIM}, "trajectory_note": _CLAIM,
                   "bull": {"type": "array", "items": _CLAIM}, "bear": {"type": "array", "items": _CLAIM}},
    "required": ["snapshot", "trajectory_note", "bull", "bear"],
}  # fmt: skip

_PLACEHOLDER = re.compile(r"\{(F\d+)\}")
_NUMS = re.compile(r"\d+(?:\.\d+)?")
_ID_TAIL = re.compile(r"\s*\(?\bfacts?[_ ]?ids?\b\s*:?\s*\[?\s*(?:F\d+\s*,?\s*)*\]?\)?\s*$", re.I)
_ID_LIST = re.compile(r"\s*[\[{(]\s*F\d+(?:\s*,\s*F\d+)+\s*[\]})]")


def _tidy(text: str) -> str:
    """Units the model wrapped around a placeholder that already carries them ('₹{F3} Cr' → '₹₹1,571 Cr Cr')."""
    text = re.sub(r"₹\s*₹", "₹", text)
    text = re.sub(r"\b(Cr|days|x)\.?\s+\1\b", r"\1", text)
    text = re.sub(r"%\s*(?:%|percent\b|per cent\b)", "%", text)
    text = re.sub(r"(\d)x\s+times\b", r"\1x", text)
    return re.sub(r"\s+([.,;])", r"\1", text).strip()


_W = (
    r"(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|"
    r"eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred)"
)
_SPELLED = re.compile(rf"\b{_W}(?:[- ]{_W})*(?:\s+(?:to|and)\s+{_W}(?:[- ]{_W})*)?\s+(?:percent|per cent|basis points|"
                      rf"bps|crores?|lakhs?|millions?|billions?)\b|\b(?:twenty|thirty|forty|fifty|sixty|seventy|eighty|"
                      rf"ninety)[- ]{_W}\b", re.I)  # fmt: skip
_PERIOD_TOKENS = re.compile(r"\b(?:Q[1-4]\s*)?FY\s?\d{2,4}\b|\bH[12]\b|\bQ[1-4]\b|\b(?:19|20)\d{2}\b")


@dataclass
class Fact:
    id: str
    line: str  # what the model sees
    display: str | None  # what a {F#} placeholder renders to — only figures have one
    citations: list[Citation]
    figure: Figure | None = None  # the figure behind a number fact (Ask returns it as a tappable figure)


@dataclass
class ReduceResult:
    snapshot: list[Claim] = field(default_factory=list)
    trajectory_note: Claim | None = None
    bull: list[Claim] = field(default_factory=list)
    bear: list[Claim] = field(default_factory=list)
    dropped: int = 0


def show(f: Figure) -> str:
    v = f.value
    if v is None:
        return "not found"
    if f.unit == "PCT":
        return f"{v:.1f}%"
    if f.unit == "INR_CR":
        return money_cr(v)
    if f.unit == "X":
        return f"{v:.2f}x"
    if f.unit == "DAYS":
        return f"{v:.0f} days"
    return f"{v:,.0f}"


def _fig_cites(f: Figure) -> list[Citation]:
    if f.citation:
        return [f.citation]
    out: list[Citation] = []
    for i in f.inputs:
        out.extend(_fig_cites(i))
    return out[:3]


def facts(d: Dossier, calls: list[Call]) -> list[Fact]:
    out: list[Fact] = []

    def add(line: str, display: str | None, cites: list[Citation], figure: Figure | None = None) -> None:
        if cites:
            fid = f"F{len(out) + 1}"
            out.append(Fact(fid, f"{fid}: {line}", display, cites, figure))

    def fig(f: Figure, prefix: str = "") -> None:
        per = f" ({f.period.label})" if f.period else ""
        add(f"{prefix}{f.label}{per} = {show(f)}", show(f), _fig_cites(f), f)

    for f in d.snapshot.headline:
        fig(f)
    for s in d.trajectory.series:
        if len(s.points) >= 2:
            fig(s.points[0], "earliest ")
            fig(s.points[-1], "latest ")
    for f in d.trajectory.growth + d.cash_quality.latest + d.balance_sheet.latest:
        fig(f)
    for f in d.snapshot.segments:
        fig(f, "segment ")
    for p in d.ledger.promises:
        if p.verdict in ("kept", "missed", "goalposts_moved", "quietly_dropped") or p.revision == "raised":
            reason = p.verdict_reason.text if p.verdict_reason else ""
            add(f"promise '{p.statement}' → {p.verdict.replace('_', ' ')}"
                f"{' (target raised)' if p.revision == 'raised' else ''}: {reason}", None,
                (p.verdict_reason.citations if p.verdict_reason else [])[:2] or [p.statements[-1].quote])  # fmt: skip
    cr = d.ledger.credibility
    if cr and cr.shown and cr.score_pct is not None:
        add(f"management credibility = {cr.kept} of {cr.n} scored promises kept", f"{cr.kept} of {cr.n}",
            [c for p in d.ledger.promises if p.verdict_reason for c in p.verdict_reason.citations][:2])  # fmt: skip
    for pp in d.analysts.points:
        add(f"analysts asked about {pp.theme} in {pp.n_calls} calls: {pp.claim.text}", None,
            pp.claim.citations[:2])  # fmt: skip
    latest = max(calls, key=lambda c: c.made_on) if calls else None
    if latest:
        for c in latest.facts.get("capex", [])[:3]:
            add(f"capex plan ({latest.label}): \"{c['quote']}\"", None,
                [latest.cite(c["page"], c["quote"])])  # fmt: skip
        for r in latest.facts.get("risks", [])[:4]:
            add(
                f"risk named by management ({latest.label}): {r['text']}",
                r["text"],
                [latest.cite(r["page"], r["quote"])],
            )
    return out


def build_request(d: Dossier, fs: list[Fact], tags: dict) -> LLMRequest | None:
    if len(fs) < 4:
        return None
    head = f"Company: {d.name} ({d.symbol}); figures are {d.basis or 'reported'}; template: {d.template}.\n\nFacts:\n"
    lines = [f"{f.line} [number]" if f.display is not None else f.line for f in fs]
    prompt = head + "\n".join(lines) + "\n\n" + PROMPT_TAIL
    return LLMRequest(purpose=PURPOSE, system=SYSTEM, prompt=prompt, schema=SCHEMA, max_output_tokens=12000,
                      timeout_s=90, thinking_budget=1024, tags=tags)  # fmt: skip


def render(raw: dict | None, fs: list[Fact]) -> tuple[Claim | None, bool]:
    """A model sentence → a cited Claim with placeholders filled from facts, or None (dropped)."""
    if not raw or not raw.get("text"):
        return None, False
    by = {f.id: f for f in fs}
    ids = [i for i in raw.get("fact_ids") or [] if i in by]
    text = " ".join(str(raw["text"]).split())
    for grp in _ID_LIST.findall(text) + _ID_TAIL.findall(text):  # '{F22, F15}' / 'Fact_ids: [F3]' in the text
        ids += [i for i in re.findall(r"F\d+", grp) if i in by]
    text = _ID_TAIL.sub("", _ID_LIST.sub("", text)).strip()
    used = _PLACEHOLDER.findall(text)
    if any(u not in by or by[u].display is None for u in used):
        return None, True  # placeholders stand for numbers only
    ids = list(dict.fromkeys(ids + used))
    bare = _PERIOD_TOKENS.sub("", _PLACEHOLDER.sub("", text))
    if _SPELLED.search(bare):
        return None, True  # a quantity spelled out in words dodges the number check
    typed = _NUMS.findall(bare.replace(",", ""))
    allowed = {n for i in ids for n in _NUMS.findall(_PERIOD_TOKENS.sub("", by[i].line).replace(",", ""))}
    if any(t not in allowed for t in typed):
        return None, True  # a number the model typed that none of its cited facts prints
    if not ids:
        return None, True
    text = _tidy(_PLACEHOLDER.sub(lambda m: by[m.group(1)].display, text))
    cites: list[Citation] = []
    for i in ids:
        for c in by[i].citations:
            if c not in cites:
                cites.append(c)
    return Claim(text=text, status="verified", citations=cites[:4]), False


def apply(data: dict, fs: list[Fact]) -> ReduceResult:
    out = ReduceResult()

    def many(items, limit):
        res = []
        for it in (items or [])[:limit]:
            c, dropped = render(it, fs)
            out.dropped += dropped
            if c:
                res.append(c)
        return res

    out.snapshot = many(data.get("snapshot"), 4)
    out.trajectory_note, dropped = render(data.get("trajectory_note"), fs)
    out.dropped += dropped
    out.bull = many(data.get("bull"), 3)
    out.bear = many(data.get("bear"), 3)
    return out
