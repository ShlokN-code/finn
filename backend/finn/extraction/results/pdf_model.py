"""Last-resort results extraction for scanned PDFs (no text layer): the multimodal cheap model copies the
three quarter columns as printed; code parses numbers and units and computes everything. The numbers are
unverified until screener agrees (and the card says "Couldn't verify" otherwise)."""

from __future__ import annotations

from datetime import UTC, date, datetime

from finn.calendar import previous_quarter_end, year_ago_quarter_end
from finn.extraction.results.compute import Fact, QuarterFacts
from finn.extraction.results.pdf_table import _UNIT, ROWS
from finn.llm import LLMRequest, LLMUnavailable, Router
from finn.models import Citation
from finn.numbers import parse_indian_number, to_crore_any

SYSTEM = (
    "You copy numbers from an Indian company's quarterly results statement (a scanned PDF). Copy exactly as "
    "printed — no arithmetic, no rounding, no unit conversion. Use the first three 'Quarter ended' columns in "
    "order: current quarter, preceding quarter, same quarter last year. Prefer the CONSOLIDATED statement if "
    "present. Leave out rows that are not printed."
)
ROW_ITEM = {"type": "array", "items": {"type": "string"}, "description": "Three values as printed"}
SCHEMA = {
    "type": "object",
    "properties": {
        "basis": {"type": "string", "enum": ["consolidated", "standalone"]},
        "unit_header": {"type": "string", "description": "The unit line as printed, e.g. '(₹ in lakhs)'"},
        "page": {"type": "integer"},
        "rows": {"type": "object", "properties": {k: ROW_ITEM for k in ROWS}},
    },
    "required": ["basis", "unit_header", "page", "rows"],
}


def quarters_from_model(router: Router, pdf: bytes, quarter_end: date, url: str, filed_at: datetime | None):
    req = LLMRequest(purpose="results_pdf_scan", system=SYSTEM, prompt=f"Quarter ended {quarter_end:%d %b %Y}. "
                     "Return the statement's rows.", schema=SCHEMA, pdf=pdf, pdf_required=True,
                     max_output_tokens=1200)  # fmt: skip
    try:
        d = router.run("cheap", req).data
    except LLMUnavailable:
        return None
    m = _UNIT.search(d.get("unit_header") or "")
    if not m:
        return None  # never guess a unit
    unit = (m.group(1) or m.group(2)).lower().rstrip("s")
    unit = {"lac": "lakh", "mn": "million"}.get(unit, unit)
    basis = d.get("basis") if d.get("basis") in ("consolidated", "standalone") else "consolidated"
    ends = [quarter_end, previous_quarter_end(quarter_end), year_ago_quarter_end(quarter_end)]
    qs = [QuarterFacts(e, basis) for e in ends]
    now = datetime.now(UTC)
    page = d.get("page") if isinstance(d.get("page"), int) and d["page"] > 0 else None
    for key, vals in (d.get("rows") or {}).items():
        if key not in ROWS or not isinstance(vals, list):
            continue
        for col, raw in enumerate(vals[:3]):
            try:
                v = 0.0 if str(raw).strip() in ("-", "–", "—") else parse_indian_number(str(raw))
            except ValueError:
                continue
            cite = Citation(source_type="exchange_filing", url=url, title=f"Results PDF ({basis}, scanned)",
                            exchange="NSE", page=page, locator=f"pdf-scan:{key}/col{col + 1}", published_at=filed_at,
                            retrieved_at=now)  # fmt: skip
            qs[col].facts[key] = Fact(to_crore_any(v, unit), cite, str(raw), unit, to_crore_any(0.5, unit))
    if not qs[0].facts:
        return None
    return basis, {"current": qs[0], "previous": qs[1], "year_ago": qs[2]}
