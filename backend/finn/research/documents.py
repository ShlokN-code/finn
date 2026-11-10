"""Step 2 — documents: download each PDF once, extract text page by page, keep only the text.

- A URL is downloaded at most once (research_documents); the PDF's sha256 keys its text (research_doc_text), so the
  same file under two URLs is extracted once. PDFs are streamed to a temp file and deleted after extraction.
- PyMuPDF reads one page at a time from the file (low memory on Render's 512 MB).
- Scanned documents (no text layer) are reported as 'scanned' and skipped — never guessed at.
- A document left in 'extracting' (the process died mid-extraction, e.g. out of memory) is marked failed rather
  than retried forever, so one bad PDF can't crash-loop the worker.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from finn.calendar import now_utc
from finn.models.research import DocumentRef
from finn.research import store
from finn.sources.http import exchange_pdf_headers, fetch_to_file

log = logging.getLogger("finn.research.documents")

EXTRACTOR = "pymupdf"
MAX_BYTES = {"transcript": 15_000_000, "annual_report": 60_000_000, "investor_presentation": 30_000_000}
SCANNED_CHARS_PER_PAGE = 200  # median below this → no usable text layer
MIN_TRANSCRIPT_PAGES = 3  # shorter files are letters/notices (e.g. "audio recording link"), not transcripts


@dataclass
class Doc:
    ref: DocumentRef
    sha256: str | None
    pages: list[str] | None  # None unless status == 'read'


def extract_pages(path) -> tuple[list[str], int]:
    """Per-page text with PyMuPDF, one page at a time."""
    import pymupdf

    pages: list[str] = []
    with pymupdf.open(path) as pdf:
        n = pdf.page_count
        for i in range(n):
            page = pdf.load_page(i)
            pages.append(page.get_text("text") or "")
            del page
    pymupdf.TOOLS.store_shrink(100)
    return pages, n


def is_scanned(pages: list[str]) -> bool:
    if not pages:
        return True
    lens = sorted(len(p.strip()) for p in pages)
    return lens[len(lens) // 2] < SCANNED_CHARS_PER_PAGE


_MONTHS = "january|february|march|april|may|june|july|august|september|october|november|december"
_DATE_RE = [
    re.compile(rf"\b({_MONTHS})\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(20\d\d)\b", re.I),
    re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MONTHS}),?\s+(20\d\d)\b", re.I),
]


def call_date(pages: list[str], month_hint: date | None) -> date | None:
    """The call's date from the transcript's first pages (e.g. 'October 23, 2026'), near screener's month."""
    months = _MONTHS.split("|")
    text = "\n".join(pages[:2])
    for rx in _DATE_RE:
        for m in rx.finditer(text):
            g = m.groups()
            mon, day = (g[0], g[1]) if g[0].isalpha() else (g[1], g[0])
            try:
                d = date(int(g[2]), months.index(mon.lower()) + 1, int(day))
            except ValueError:
                continue
            if month_hint is None or abs((d - month_hint).days) <= 62:
                return d
    return None


def get_document(conn, symbol: str, link, now: datetime | None = None) -> Doc:
    """`link` is a discover.DocLink. Returns the document with its page texts when readable."""
    now = now or now_utc()
    row = store.get_document(conn, link.url)
    period = None
    if link.quarter_end:
        from finn.calendar import quarter_period

        period = quarter_period(link.quarter_end)

    def ref(status: str, note: str | None = None, pages: int | None = None, sha: str | None = None,
            when: date | None = None) -> DocumentRef:  # fmt: skip
        return DocumentRef(id=sha or hashlib.sha256(link.url.encode()).hexdigest(), kind=link.kind, title=link.title,
                           period=period, call_date=when, url=link.url, status=status, status_note=note,
                           pages=pages)  # fmt: skip

    if row and row["status"] == "read" and row["sha256"]:
        pages = store.load_text(conn, row["sha256"])
        if pages is not None:
            return Doc(ref("read", None, len(pages), row["sha256"], row["call_date"]), row["sha256"], pages)
    if row and row["status"] in ("scanned", "too_large", "not_pdf"):
        return Doc(ref(row["status"], row["status_note"], row["pages"], row["sha256"], row["call_date"]),
                   row["sha256"], None)  # fmt: skip
    if row and row["status"] == "failed" and row["fetched_at"] and now - row["fetched_at"] < timedelta(hours=12):
        return Doc(ref("failed", row["status_note"]), None, None)  # retried after 12 h, not on every build
    if row and row["status"] == "extracting" and row["fetched_at"] and now - row["fetched_at"] > timedelta(minutes=10):
        store.upsert_document(conn, link.url, symbol, link.kind, status="failed", fetched_at=now,
                              status_note="Extraction did not finish (worker restarted)")  # fmt: skip
        return Doc(ref("failed", "Extraction did not finish (worker restarted)"), None, None)

    store.upsert_document(conn, link.url, symbol, link.kind, title=link.title, period_label=link.period_label,
                          status="extracting", fetched_at=now)  # fmt: skip
    path, status = fetch_to_file(link.url, max_bytes=MAX_BYTES[link.kind], headers=exchange_pdf_headers(link.url))
    if path is None:
        st = "too_large" if status == "too_large" else "failed"
        note = "Larger than FINN reads on its free server" if st == "too_large" else status.removeprefix("failed:")
        store.upsert_document(conn, link.url, symbol, link.kind, status=st, status_note=note, fetched_at=now)
        return Doc(ref(st, note), None, None)
    try:
        head = path.open("rb").read(5)
        if head != b"%PDF-":
            store.upsert_document(conn, link.url, symbol, link.kind, status="not_pdf", fetched_at=now,
                                  status_note="The link did not return a PDF")  # fmt: skip
            return Doc(ref("not_pdf", "The link did not return a PDF"), None, None)
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        sha = h.hexdigest()
        size = path.stat().st_size
        pages = store.load_text(conn, sha)
        if pages is None:
            pages, _ = extract_pages(path)
            if is_scanned(pages):
                store.upsert_document(conn, link.url, symbol, link.kind, sha256=sha, pages=len(pages), bytes=size,
                                      status="scanned", status_note="Scanned — no text layer", fetched_at=now)  # fmt: skip
                return Doc(ref("scanned", "Scanned — not read", len(pages), sha), sha, None)
            store.save_text(conn, sha, pages, EXTRACTOR)
    finally:
        path.unlink(missing_ok=True)
    if link.kind == "transcript" and len(pages) < MIN_TRANSCRIPT_PAGES:
        note = f"Only {len(pages)} page(s) — not a transcript"
        store.upsert_document(conn, link.url, symbol, link.kind, sha256=sha, pages=len(pages), bytes=size,
                              status="failed", status_note=note, fetched_at=now)  # fmt: skip
        return Doc(ref("failed", note, len(pages), sha), sha, None)
    when = call_date(pages, link.call_month) if link.kind == "transcript" else None
    store.upsert_document(conn, link.url, symbol, link.kind, sha256=sha, pages=len(pages), bytes=size, status="read",
                          status_note=None, call_date=when, fetched_at=now)  # fmt: skip
    return Doc(ref("read", None, len(pages), sha, when), sha, pages)
