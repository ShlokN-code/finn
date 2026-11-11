"""Citation checker (trust layer §10.6): a model's quote must exist in the source text (fuzzy match).

Exchange PDFs come with odd spacing, line breaks and ligatures, so both sides are normalised; a quote passes
if it appears verbatim after normalisation, or if a window of the text matches it at ≥ 0.85 similarity.
"""

from __future__ import annotations

import io
import logging
import re
import unicodedata
from difflib import SequenceMatcher

log = logging.getLogger("finn.citations")
THRESHOLD = 0.85


def normalise(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).lower()
    s = s.replace("’", "'").replace("“", '"').replace("”", '"').replace("–", "-").replace("—", "-")
    return re.sub(r"[^a-z0-9%₹.,:/()'\-]+", " ", s).strip()


def quote_in_text(quote: str | None, text: str | None) -> bool:
    if not quote or not text:
        return False
    q, t = normalise(quote), normalise(text)
    if len(q) < 8:
        return False
    if q in t:
        return True
    n = len(q)
    best = 0.0
    step = max(1, n // 4)
    for i in range(0, max(1, len(t) - n + 1), step):
        r = SequenceMatcher(None, q, t[i : i + n + n // 10], autojunk=False).ratio()
        best = max(best, r)
        if best >= THRESHOLD:
            return True
    return False


def pdf_text(pdf: bytes | None, max_pages: int = 6) -> tuple[str, list[str]]:
    """(all text, per-page texts) for the first pages; ('', []) when unreadable (scanned/encrypted)."""
    if not pdf:
        return "", []
    try:
        from pypdf import PdfReader

        pages = [p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages[:max_pages]]
    except Exception as e:
        log.warning("pdf text failed: %s", e)
        return "", []
    return "\n".join(pages), pages


def page_of(quote: str, pages: list[str]) -> int | None:
    for i, p in enumerate(pages, start=1):
        if quote_in_text(quote, p):
            return i
    return None


def filing_doc(f: dict) -> tuple[str, str, str | None] | None:
    """(url, doc_kind, raw_url) for an exchange filing, most readable first: the attached PDF, else NSE's iXBRL
    (HTML) view, else the raw XBRL labelled as machine-readable. None when the filing has no usable link
    (NSE sometimes sends '-')."""
    att = (f.get("attachment_url") or "").strip()
    xbrl = (f.get("xbrl_url") or "").strip() or None
    if att and att != "-" and att.startswith("http"):
        low = att.lower().split("?")[0]
        kind = "zip" if low.endswith(".zip") else "raw_xbrl" if low.endswith(".xml") else "pdf"
        if kind != "raw_xbrl":
            return att, kind, None
        xbrl = xbrl or att
    raw = f.get("raw") if isinstance(f.get("raw"), dict) else {}
    ix = (f.get("ixbrl_url") or raw.get("ixbrl") or "").strip()
    if ix.startswith("http") and ix.lower().endswith(".html"):
        return ix, "ixbrl", xbrl
    if xbrl and xbrl.startswith("http"):
        return xbrl, "raw_xbrl", xbrl
    return None
