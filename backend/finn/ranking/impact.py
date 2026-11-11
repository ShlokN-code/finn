"""Level-0 relevance + one-liner facts: one cheap-model call per non-results event.

The model reads the filing (subject + first two PDF pages) and returns, as printed: an impact tag for the
company's *business* (not a stock call), a ≤20-word reason with a verbatim quote, a ≤10-word "so what", and
category facts (amounts, ratings, pledge %). Code then parses money, orders ratings, compares pledge levels
and checks the quote exists in the PDF text. Results, price/volume and dividend/bonus events never get here
(decided in code). Primary source only: the prompt forbids outside knowledge.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime

from finn.citations import filing_doc, page_of, pdf_text, quote_in_text
from finn.llm import LLMRequest, LLMUnavailable, Router
from finn.models import Citation, Claim, Figure, OneLinerDetail
from finn.numbers import parse_money
from finn.ranking import ratings

log = logging.getLogger("finn.impact")

SYSTEM = (
    "You read one Indian stock-exchange filing and report what it says. Use ONLY the filing text provided — "
    "never news, analyst views or your own knowledge of the company. Do not do arithmetic or compare numbers; "
    "copy amounts, ratings and percentages exactly as printed. impact = the likely effect on the company's "
    "BUSINESS (not its share price): positive, negative, mixed, or neutral when it is procedural. 'quote' must "
    "be copied verbatim from the filing (one sentence or phrase, ≤ 30 words) and support the reason. 'so_what' "
    "is ≤ 10 words for a busy fund manager. Leave a fact empty when the filing doesn't state it."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "impact": {"type": "string", "enum": ["positive", "negative", "mixed", "neutral"]},
        "reason": {"type": "string"},
        "so_what": {"type": "string"},
        "quote": {"type": "string"},
        "amount": {"type": "string", "description": "Main money amount as printed, with unit (e.g. 'Rs 450 crore')"},
        "amount_label": {"type": "string", "description": "What the amount is (order value, issue size, capex…)"},
        "counterparty": {"type": "string"},
        "rating_agency": {"type": "string"},
        "rating_previous": {"type": "string", "description": "As printed, e.g. 'CRISIL AA+/Stable'"},
        "rating_new": {"type": "string"},
        "pledge_before_pct": {"type": "string"},
        "pledge_after_pct": {"type": "string"},
        "person": {"type": "string"},
        "transaction": {"type": "string", "description": "buy / sell / pledge / revoke — as stated"},
    },
    "required": ["impact", "reason", "so_what", "quote"],
}

SKIP = {"results", "price_volume", "dividend", "bonus_split", "routine", "unclassified", "investor_meetings"}


@dataclass
class Tagged:
    impact: str | None
    reason: Claim | None
    so_what: str | None
    detail: OneLinerDetail | None
    tier: str  # model | failed
    note: str | None = None


def _ten_words(s: str) -> str:
    words = s.split()
    return " ".join(words[:10]).rstrip(",;:—-")


def _pct(s: str | None) -> float | None:
    m = re.search(r"-?\d+(?:\.\d+)?", s or "")
    return float(m.group(0)) if m else None


def tag_event(router: Router, event: dict, filing: dict, pdf: bytes | None, company: str) -> Tagged:
    text, pages = pdf_text(pdf, max_pages=2)
    prompt = (f"Company: {company} (NSE: {event['symbol']})\nFINN category: {event['category']}\n"
              f"Exchange category: {filing.get('exchange_category')}\nSubject: {filing['subject']}\n"
              f"Filed: {filing['filed_at']:%Y-%m-%d}\n")  # fmt: skip
    if text:
        prompt += "\nFiling text (first pages):\n" + text[:12000]
    elif not pdf:
        prompt += "\n(No filing text available — judge from the subject only; quote the subject.)"
    req = LLMRequest(purpose="tag_event", system=SYSTEM, prompt=prompt, schema=SCHEMA,
                     pdf=pdf if (pdf and not text) else None, pdf_required=bool(pdf and not text),
                     max_output_tokens=600)  # fmt: skip
    try:
        res = router.run("cheap", req)
    except LLMUnavailable as e:
        return Tagged(None, None, None, None, "failed", f"llm unavailable: {e}"[:300])
    return build_tagged(res.data, event, filing, text or filing["subject"], pages)


def build_tagged(d: dict, event: dict, filing: dict, source_text: str, pages: list[str]) -> Tagged:
    """Model output → Tagged, with every check done in code."""
    now = datetime.now(UTC)
    quote = (d.get("quote") or "").strip()
    found = quote_in_text(quote, source_text)
    page = page_of(quote, pages) if found and pages else None
    doc = filing_doc(filing)
    url, kind, raw = doc if doc else (None, None, None)
    cite = Citation(source_type="exchange_filing", url=url, doc_kind=kind, raw_url=raw, title=filing["subject"][:120],
                    exchange="NSE",
                    page=page, quote=quote[:300] if found else None, published_at=filing["filed_at"],
                    retrieved_at=now) if url else None  # fmt: skip
    impact = d.get("impact") if d.get("impact") in ("positive", "negative", "mixed", "neutral") else None
    reason = None
    if cite and d.get("reason"):
        reason = Claim(text=d["reason"].strip()[:200], status="verified" if found else "unverified", citations=[cite])
    facts = {k: str(v).strip() for k, v in d.items()
             if k not in ("impact", "reason", "so_what", "quote") and v and str(v).strip()}  # fmt: skip
    key_fig = None
    if facts.get("amount") and cite:
        try:
            cr, raw, unit = parse_money(facts["amount"])
            in_src = quote_in_text(raw, source_text) or raw.replace(",", "") in source_text.replace(",", "")
            key_fig = Figure(
                label=facts.get("amount_label") or "Amount",
                value=cr,
                unit="INR_CR",
                status="verified" if in_src else "unverified",
                citation=cite,
                raw=raw,
                raw_unit=unit,
            )
        except ValueError:
            pass  # no unit printed → no figure (never guess a unit)
    direction = None
    if event["category"] == "credit_rating":
        direction = ratings.direction(facts.get("rating_previous"), facts.get("rating_new"))
    elif event["category"] == "pledging":
        b, a = _pct(facts.get("pledge_before_pct")), _pct(facts.get("pledge_after_pct"))
        if b is not None and a is not None:
            direction = "up" if a > b else "down" if a < b else "unchanged"
    line_text = d.get("reason") or filing["subject"]
    line = Claim(text=line_text.strip()[:200], status="verified" if found else "unverified",
                 citations=[cite]) if cite else Claim(text=line_text[:200], status="not_found")  # fmt: skip
    detail = OneLinerDetail(line=line, key_figure=key_fig, direction=direction, facts=facts)
    so_what = _ten_words(d.get("so_what") or "") or None
    return Tagged(impact, reason, so_what, detail, "model", None if found else "quote not found in filing text")
