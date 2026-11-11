"""Deck lookup: delivered figures the calls didn't state, read from the investor deck that closes the period.

Only for promises that are "can't score" solely because no delivered figure was found in the calls (an FY26 target
is closed by the Q4 FY26 deck). One cheap call per deck needed — never all decks — asking only for the missing
metrics. The answer goes through the same checks as a transcript: the quote must be on the cited page, its number
must be printed in the quote, and the quote must name the metric. The figure then enters the ledger as an actual
from a 'deck' document (cited as an investor presentation, page and quote) and code scores it as usual. A deck
never adds promises and never counts as a 'later call' for quietly-dropped or the credibility trend.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from finn.llm import LLMRequest, LLMUnavailable
from finn.models.research import DocumentRef, Promise
from finn.research import metrics, store
from finn.research.checker import Checker, norm, number_in_quote, strip_boilerplate
from finn.research.documents import get_document
from finn.research.ledger import Call

log = logging.getLogger("finn.research.deck")

EXTRACTOR = "deck_lookup"
PROMPT_VERSION = "v1"
PURPOSE = f"research.map_deck.{PROMPT_VERSION}"  # 'research.map*' → counted in the cheap research lane
MAX_DECKS = 3

SYSTEM = """You read ONE investor presentation of an Indian listed company and copy reported figures from it.
Use only this document. Copy numbers exactly as printed; never calculate, convert or round. For every figure give
a verbatim quote (5–40 words) copied from the page that contains the number and the metric's name, and the page
number from the [[p.N]] marker. If a requested figure is not in the deck, leave it out. Do not guess."""

SCHEMA = {
    "type": "object",
    "properties": {"figures": {"type": "array", "items": {"type": "object", "properties": {
        "request_id": {"type": "string"},
        "value": {"type": "number"},
        "unit_text": {"type": "string", "nullable": True},
        "currency": {"type": "string", "enum": ["INR", "USD", "constant_currency", "unspecified", "not_money"]},
        "scope": {"type": "string", "enum": ["consolidated", "standalone", "segment", "unspecified"]},
        "period_text": {"type": "string"},
        "period_type": {"type": "string", "enum": ["fy", "quarter", "half", "unspecified"]},
        "fy": {"type": "integer", "nullable": True},
        "quarter": {"type": "integer", "nullable": True},
        "half": {"type": "integer", "nullable": True},
        "quote": {"type": "string"},
        "page": {"type": "integer"},
    }, "required": ["request_id", "value", "currency", "scope", "period_text", "period_type", "quote", "page"]}}},
    "required": ["figures"],
}  # fmt: skip


@dataclass
class DeckResult:
    calls: list[Call] = field(default_factory=list)
    sources: list[DocumentRef] = field(default_factory=list)
    requested: int = 0
    found: int = 0
    quota: LLMUnavailable | None = None


def _ask(p: Promise) -> str:
    t = p.scored_target or p.statements[-1]
    basis = ", ".join(x for x in (p.basis.currency, p.basis.scope, p.basis.segment) if x and x != "unspecified")
    return (
        f"{p.metric} — {'growth rate' if p.measure == 'growth' else 'change' if p.measure == 'change' else 'value'}"
        f" for {p.period.label if p.period else '?'}{f' ({basis})' if basis else ''}; target was {t.raw_target}"
    )


def _names_metric(p: Promise, quote: str) -> bool:
    q = norm(quote)
    words = {w for w in re.findall(r"[a-z]{3,}", norm(p.metric))} - {"the", "and", "for", "growth", "rate"}
    words |= {norm(s) for s in metrics.synonyms(p.metric_key)}
    return any(re.search(rf"(?<![a-z0-9]){re.escape(w)}(?![a-z0-9])", q) for w in words if len(w) >= 3)


def lookup(conn, router, symbol: str, disc, promises: list[Promise], unscored: dict, now: datetime,
           tags: dict) -> DeckResult:  # fmt: skip
    out = DeckResult()
    by_id = {p.id: p for p in promises}
    need: dict = defaultdict(list)  # deck quarter end → promises
    for pid, period in unscored.items():
        p = by_id.get(pid)
        if p is not None and period.end in disc.decks:
            need[period.end].append(p)
    for qe in sorted(need, reverse=True)[:MAX_DECKS]:
        link, wanted = disc.decks[qe], need[qe]
        out.requested += len(wanted)
        doc = get_document(conn, symbol, link, now)
        out.sources.append(doc.ref)
        if doc.pages is None:
            continue
        ids = {f"R{i}": p for i, p in enumerate(wanted, start=1)}
        key = hashlib.sha256(json.dumps(sorted(_ask(p) for p in wanted)).encode()).hexdigest()[:12]
        version = f"{PROMPT_VERSION}:{key}"
        hit = store.get_extraction(conn, doc.sha256, EXTRACTOR, version)
        if hit:
            figures = hit["payload"]["figures"]
        else:
            asks = "\n".join(f"{rid}: {_ask(p)}" for rid, p in ids.items())
            text = "\n".join(f"[[p.{i}]]\n{pg.strip()}" for i, pg in enumerate(strip_boilerplate(doc.pages), start=1))
            req = LLMRequest(
                purpose=PURPOSE,
                system=SYSTEM,
                prompt=f"Find these reported figures:\n{asks}",
                schema=SCHEMA,
                document_text=text,
                max_output_tokens=4000,
                timeout_s=180,
                tags=tags,
            )
            try:
                res = router.run("cheap", req)
            except LLMUnavailable as e:
                out.quota = e
                break
            figures = _validate(res.data.get("figures") or [], ids, doc.pages)
            store.save_extraction(conn, doc.sha256, EXTRACTOR, version, res.model, {"figures": figures},
                                  {"requested": len(ids), "kept": len(figures)})  # fmt: skip
        actuals = []
        for f in figures:
            p = ids.get(f["request_id"])
            if p is None:
                continue
            actuals.append({
                "metric": p.metric, "metric_key": p.metric_key, "measure": p.measure if p.measure != "qualitative"
                else "level", "value": f["value"], "unit_text": f.get("unit_text"), "currency": f["currency"],
                "scope": f["scope"], "segment": p.basis.segment if f["scope"] == "segment" else None,
                "period_text": f["period_text"], "period_type": f["period_type"], "fy": f.get("fy"),
                "quarter": f.get("quarter"), "half": f.get("half"), "years": None, "quote": f["quote"],
                "page": f["page"], "for_promise": p.id,
            })  # fmt: skip
        out.found += len(actuals)
        made = link.call_month or qe
        out.calls.append(Call(doc.ref.id, link.url, link.title, made, doc.pages, {"guidance": [], "actuals": actuals},
                              now, kind="deck"))  # fmt: skip
    return out


def _validate(raw: list, ids: dict, pages: list[str]) -> list[dict]:
    chk = Checker(pages)
    out = []
    for f in raw:
        p = ids.get(f.get("request_id"))
        if p is None or not isinstance(f.get("value"), int | float):
            continue
        loc = chk.locate(f.get("quote"), f.get("page"), f["value"])
        if loc is not None and number_in_quote(float(f["value"]), loc.quote) and _names_metric(p, loc.quote):
            out.append({**f, "quote": loc.quote, "page": loc.page})
            continue
        cell = _table_cell(p, float(f["value"]), pages, f.get("page"))
        if cell:
            out.append({**f, "quote": cell[1], "page": cell[0]})
    return out


def _num_rx(v: float) -> str:
    """Regex for a number as a deck may print it: 1.92 / 1,92,000 / 119.3."""
    s = f"{v:.10g}"
    whole, _, frac = s.partition(".")
    digits = ",?".join(re.escape(ch) for ch in whole.lstrip("-"))
    return rf"(?<![\d.]){'-?' if v < 0 else ''}{digits}{r'\.' + frac if frac else ''}(?![\d])"


def _table_cell(p: Promise, value: float, pages: list[str], page: int | None) -> tuple[int, str] | None:
    """Deck tables come out of PDFs as columns, so a model's 'row' quote is rarely contiguous. Fallback: the metric's
    name and the exact number within 250 characters on the claimed page (±1); the stored quote is that verbatim
    span of page text (whitespace collapsed)."""
    if page is None:
        return None
    names = [w for w in re.findall(r"[a-z]{3,}", norm(p.metric)) if w not in ("the", "and", "for", "growth", "rate")]
    names += [norm(s) for s in metrics.synonyms(p.metric_key)]
    for i in (page - 1, page - 2, page):
        if not (0 <= i < len(pages)):
            continue
        flat = " ".join(pages[i].split())
        low = flat.lower()
        for m in re.finditer(_num_rx(value), flat):
            for nm in names:
                for k in re.finditer(rf"(?<![a-z0-9]){re.escape(nm)}(?![a-z0-9])", low):
                    a, b = sorted((k.start(), m.end()))
                    if b - a <= 250:
                        start = min(k.start(), m.start())
                        return i + 1, flat[start : max(k.end(), m.end())]
    return None
