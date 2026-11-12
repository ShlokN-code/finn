"""Step 3 — MAP: one cheap-model call per transcript → validated, quote-checked facts.

The model only reads: it copies statements, numbers as printed and verbatim quotes with page numbers. Code then
validates every item (Pydantic, item by item, so one bad item never sinks the rest), finds each quote in the
page text (checker), requires the item's number to be printed in its own quote, drops anything said by an analyst
or moderator as guidance, and stores the result per (document hash, extractor, prompt version) — a document is
never sent to a model twice, and a later build reads the same facts (the ledger can't flip between builds).
"""

from __future__ import annotations

import logging
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from finn.llm import LLMRequest, LLMUnavailable
from finn.research import store
from finn.research.checker import Checker, number_in_quote, strip_boilerplate
from finn.research.metrics import KEYS

log = logging.getLogger("finn.research.extract")

EXTRACTOR = "map_transcript"
PROMPT_VERSION = "v1"
PURPOSE = f"research.map_transcript.{PROMPT_VERSION}"
# Bump when validation/checking changes: stored extractions are re-validated from the cached model response
# (llm_calls), so the fix applies without another model call.
VALIDATOR_VERSION = 2
MAX_OUTPUT = 16_000

SYSTEM = """You extract facts from ONE earnings-call transcript of an Indian listed company, for an audit trail.
Rules:
- Use ONLY this transcript. Never use outside knowledge, news, or what you know about the company.
- Copy numbers exactly as printed ("20-22%", "₹1,500 crore", "150 bps"). Never calculate, convert or round.
- Every item needs a verbatim quote (8–60 words) copied character-for-character from the transcript, and the page
  number from the [[p.N]] marker of the page where the quote appears.
- Guidance = forward-looking statements by MANAGEMENT (company executives) only: targets, outlooks, plans, dates.
  Never record an analyst's or moderator's words as guidance.
- If something is not in the transcript, leave it out. Do not guess."""

PROMPT = f"""Extract from the transcript below:

1. guidance — every forward-looking statement by management (up to 30): a target, range, floor/ceiling, plan,
   launch or date. kind: point (single number), range (low–high), at_least (≥, "at least", "minimum", "over"),
   at_most (≤, "below", "not more than", "maximum"), qualitative (no number: a launch, entry, plan or intention).
   - metric: as management named it. metric_key: the closest of {", ".join(KEYS)}.
   - measure: level (a value, e.g. margin 20%), growth (a % growth rate), change (a change, e.g. "+50 bps").
   - target_low/target_high: the numbers as printed (a point target: both equal; at_least: target_low only;
     at_most: target_high only; qualitative: none). unit_text: the unit as printed (%, bps, crore, lakh, million,
     billion, USD million, x, days, GW, …).
   - currency: INR, USD, constant_currency (said "constant currency"/"cc"), unspecified, or not_money.
   - scope: consolidated, standalone, segment (name it in segment), or unspecified.
   - period_text: the period exactly as said. period_type: fy (a named fiscal year), quarter, half, by_fy (by/until
     a fiscal year), this_fy ("this year", "current fiscal"), next_fy ("next year"), next_n_years (with years),
     medium_term, or unspecified. fy: the 4-digit calendar year the fiscal year ENDS in when it is named
     (FY27 → 2027, "2026-27" → 2027); quarter 1–4 and half 1–2 when named.
   - statement: ≤ 20 words, plain English. search_terms: 2–4 distinctive words from the statement.
2. actuals — results management reports in this call for metrics a standard P&L may not show (AUM growth,
   constant-currency growth, credit cost, NIM, GNPA, volumes, order book, deal wins, utilisation, segment revenue,
   …) and any figure that answers earlier guidance (up to 30). value as printed; same fields as guidance.
3. analyst_questions — each distinct analyst question (up to 25): analyst, firm, topic (≤ 5 words), metric_key,
   gist (≤ 15 words), quote of the question, page.
4. segments (up to 8): name, value as printed and unit_text, or share_pct, period_text, quote, page.
5. capex (up to 5): amount as printed, unit_text, period_text, purpose, quote, page.
6. risks management names (up to 6): text (≤ 20 words), quote, page."""

_STR = {"type": "string"}
_NUM = {"type": "number", "nullable": True}
_INT = {"type": "integer", "nullable": True}
_BASIS = {
    "currency": {"type": "string", "enum": ["INR", "USD", "constant_currency", "unspecified", "not_money"]},
    "scope": {"type": "string", "enum": ["consolidated", "standalone", "segment", "unspecified"]},
    "segment": {"type": "string", "nullable": True},
}
_PERIOD = {
    "period_text": _STR,
    "period_type": {"type": "string", "enum": ["fy", "quarter", "half", "by_fy", "this_fy", "next_fy", "next_n_years",
                                               "medium_term", "unspecified"]},  # fmt: skip
    "fy": _INT, "quarter": _INT, "half": _INT, "years": _INT,
}  # fmt: skip
_CITE = {"quote": _STR, "page": {"type": "integer"}}
SCHEMA = {
    "type": "object",
    "properties": {
        "guidance": {"type": "array", "items": {"type": "object", "properties": {
            "metric": _STR, "metric_key": {"type": "string", "enum": KEYS},
            "measure": {"type": "string", "enum": ["level", "growth", "change", "qualitative"]},
            "kind": {"type": "string", "enum": ["point", "range", "at_least", "at_most", "qualitative"]},
            "target_low": _NUM, "target_high": _NUM, "unit_text": {"type": "string", "nullable": True},
            **_BASIS, **_PERIOD, "statement": _STR, "search_terms": {"type": "array", "items": _STR},
            "speaker": _STR,
            "speaker_role": {"type": "string", "enum": ["management", "analyst", "moderator", "other"]},
            **_CITE,
        }, "required": ["metric", "metric_key", "measure", "kind", "currency", "scope", "period_text", "period_type",
                        "statement", "speaker", "speaker_role", "quote", "page"]}},
        "actuals": {"type": "array", "items": {"type": "object", "properties": {
            "metric": _STR, "metric_key": {"type": "string", "enum": KEYS},
            "measure": {"type": "string", "enum": ["level", "growth", "change"]},
            "value": {"type": "number"}, "unit_text": {"type": "string", "nullable": True},
            **_BASIS, **_PERIOD, "speaker": _STR, **_CITE,
        }, "required": ["metric", "metric_key", "measure", "value", "currency", "scope", "period_text", "period_type",
                        "quote", "page"]}},
        "analyst_questions": {"type": "array", "items": {"type": "object", "properties": {
            "analyst": _STR, "firm": {"type": "string", "nullable": True}, "topic": _STR,
            "metric_key": {"type": "string", "enum": KEYS}, "gist": _STR, **_CITE,
        }, "required": ["topic", "metric_key", "gist", "quote", "page"]}},
        "segments": {"type": "array", "items": {"type": "object", "properties": {
            "name": _STR, "value": _NUM, "unit_text": {"type": "string", "nullable": True}, "share_pct": _NUM,
            "period_text": {"type": "string", "nullable": True}, **_CITE,
        }, "required": ["name", "quote", "page"]}},
        "capex": {"type": "array", "items": {"type": "object", "properties": {
            "amount": _NUM, "unit_text": {"type": "string", "nullable": True},
            "period_text": {"type": "string", "nullable": True}, "purpose": _STR, **_CITE,
        }, "required": ["purpose", "quote", "page"]}},
        "risks": {"type": "array", "items": {"type": "object", "properties": {"text": _STR, **_CITE},
                                              "required": ["text", "quote", "page"]}},
    },
    "required": ["guidance", "actuals", "analyst_questions", "segments", "capex", "risks"],
}  # fmt: skip


# --- validated item shapes ---------------------------------------------------------------------------------


class _Item(BaseModel):
    quote: str
    page: int = Field(ge=1)
    quote_method: str | None = None  # exact | page_fixed | reanchored (set by the checker)


class Guidance(_Item):
    metric: str
    metric_key: str
    measure: Literal["level", "growth", "change", "qualitative"]
    kind: Literal["point", "range", "at_least", "at_most", "qualitative"]
    target_low: float | None = None
    target_high: float | None = None
    unit_text: str | None = None
    currency: str
    scope: str
    segment: str | None = None
    period_text: str
    period_type: str
    fy: int | None = None
    quarter: int | None = None
    half: int | None = None
    years: int | None = None
    statement: str
    search_terms: list[str] = Field(default_factory=list)
    speaker: str | None = None
    speaker_role: str = "management"


class Actual(_Item):
    metric: str
    metric_key: str
    measure: Literal["level", "growth", "change"]
    value: float
    unit_text: str | None = None
    currency: str
    scope: str
    segment: str | None = None
    period_text: str
    period_type: str
    fy: int | None = None
    quarter: int | None = None
    half: int | None = None
    years: int | None = None
    speaker: str | None = None


class Question(_Item):
    analyst: str | None = None
    firm: str | None = None
    topic: str
    metric_key: str
    gist: str


class Segment(_Item):
    name: str
    value: float | None = None
    unit_text: str | None = None
    share_pct: float | None = None
    period_text: str | None = None


class Capex(_Item):
    amount: float | None = None
    unit_text: str | None = None
    period_text: str | None = None
    purpose: str


class Risk(_Item):
    text: str


SHAPES = {"guidance": Guidance, "actuals": Actual, "analyst_questions": Question, "segments": Segment,
          "capex": Capex, "risks": Risk}  # fmt: skip


def document_text(pages: list[str], lo: int = 0, hi: int | None = None) -> str:
    """Pages lo..hi-1 with their absolute [[p.N]] markers (boilerplate stripped over the whole transcript)."""
    sp = strip_boilerplate(pages)
    hi = len(sp) if hi is None else hi
    return "\n".join(f"[[p.{i + 1}]]\n{sp[i].strip()}" for i in range(lo, hi))


def _anchor(kind: str, item: dict):
    if kind == "guidance":
        return item.get("target_low") if item.get("target_low") is not None else item.get("target_high")
    return {"actuals": item.get("value"), "segments": item.get("value") or item.get("share_pct"),
            "capex": item.get("amount")}.get(kind)  # fmt: skip


def validate(raw: dict, pages: list[str]) -> tuple[dict, dict]:
    """Model output → items that passed every check, plus check stats."""
    chk = Checker(pages)
    out: dict[str, list[dict]] = {k: [] for k in SHAPES}
    dropped = {"invalid": 0, "not_management": 0, "number_not_in_quote": 0, "bad_metric_key": 0}
    for kind, shape in SHAPES.items():
        for item in raw.get(kind) or []:
            if not isinstance(item, dict):
                dropped["invalid"] += 1
                continue
            if kind == "guidance" and item.get("speaker_role") not in (None, "management"):
                dropped["not_management"] += 1
                continue
            if "metric_key" in item and item["metric_key"] not in KEYS:
                item["metric_key"] = "other"
                dropped["bad_metric_key"] += 1
            anchor = _anchor(kind, item)
            loc = chk.locate(item.get("quote"), item.get("page"), anchor)
            if loc is None:
                continue
            item = {**item, "quote": loc.quote, "page": loc.page, "quote_method": loc.method}
            nums = [item.get("target_low"), item.get("target_high")] if kind == "guidance" else [anchor]
            if kind in ("guidance", "actuals") and not all(number_in_quote(n, loc.quote) for n in nums):
                dropped["number_not_in_quote"] += 1
                continue
            try:
                out[kind].append(shape.model_validate(item).model_dump())
            except ValidationError:
                dropped["invalid"] += 1
    return out, {**chk.stats.as_dict(), "dropped": dropped}


def map_transcript(conn, router, sha256: str, pages: list[str], tags: dict | None = None) -> tuple[dict | None, dict]:
    """Facts for one transcript: cached extraction, else one cheap call. Raises LLMUnavailable on quota."""
    hit = store.get_extraction(conn, sha256, EXTRACTOR, PROMPT_VERSION)
    if hit and (hit["stats"] or {}).get("validator") == VALIDATOR_VERSION:
        return hit["payload"], {**(hit["stats"] or {}), "cached": True, "model": hit["model"]}
    parts = _map_parts(router, pages, 0, len(pages), tags or {}, 0)
    raw = {k: [x for r in parts for x in (r.data.get(k) or [])] for k in SHAPES}
    facts, stats = validate(raw, pages)
    stats.update(validator=VALIDATOR_VERSION, model=parts[0].model, parts=len(parts),
                 tokens_in=sum(r.tokens_in or 0 for r in parts), tokens_out=sum(r.tokens_out or 0 for r in parts),
                 raw_counts={k: len(raw[k]) for k in SHAPES})  # fmt: skip
    store.save_extraction(conn, sha256, EXTRACTOR, PROMPT_VERSION, parts[0].model, facts, stats)
    return facts, stats


MAX_SPLIT_DEPTH = 2  # whole → halves → quarters
MIN_SPLIT_PAGES = 4


def _map_parts(router, pages: list[str], lo: int, hi: int, tags: dict, depth: int) -> list:
    """One MAP call over pages lo..hi-1; if the answer was cut off at the output limit (a long, dense call: IDEA,
    RELIANCE), the same pages in two halves, each with its own call. Quotes keep their absolute page numbers and
    are validated against the whole transcript, so the merged result checks exactly like a single call."""
    req = LLMRequest(purpose=PURPOSE, system=SYSTEM, prompt=PROMPT, schema=SCHEMA,
                     document_text=document_text(pages, lo, hi), max_output_tokens=MAX_OUTPUT, timeout_s=240,
                     tags={**tags, **({"part": f"p{lo + 1}-{hi}"} if (lo, hi) != (0, len(pages)) else {})})  # fmt: skip
    try:
        return [router.run("cheap", req)]
    except LLMUnavailable as e:
        if "truncated" not in str(e) or depth >= MAX_SPLIT_DEPTH or hi - lo < MIN_SPLIT_PAGES:
            raise
        log.info("MAP output truncated for pages %d-%d: splitting", lo + 1, hi)
        mid = (lo + hi) // 2
        return _map_parts(router, pages, lo, mid, tags, depth + 1) + _map_parts(router, pages, mid, hi, tags, depth + 1)


__all__ = ["map_transcript", "validate", "LLMUnavailable", "Guidance", "Actual", "Question"]
