"""Citation checker for research (trust layer §10.6): every model quote must be found in its document's text.

Order of search: the page the model named, the pages either side (quotes straddle page breaks), then pages that
contain the quote's rarest words. Text on both sides is normalised (Unicode, case, curly quotes, dashes, line-break
hyphenation, whitespace). A quote that still isn't found may be re-anchored: replaced by the sentence on the
claimed page (±1) that overlaps it most AND contains the number the item is about — so the stored quote is always
verbatim source text. Otherwise the item is dropped and counted.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from finn.citations import normalise, quote_in_text

_HYPHEN_BREAK = re.compile(r"(\w)[-­]\s*\n\s*(\w)")
_SOFT = re.compile(r"(\w)-\s+(\w)")
_WORD = re.compile(r"[a-z][a-z0-9%]{3,}")
_NUM = re.compile(r"\d+(?:[.,]\d+)*")


def clean(text: str) -> str:
    """Join words broken across lines with a hyphen ('manu-\\nfacturing' → 'manufacturing')."""
    return _HYPHEN_BREAK.sub(r"\1\2", text)


def norm(text: str) -> str:
    return normalise(_SOFT.sub(r"\1\2", clean(text)))


@dataclass
class CheckStats:
    checked: int = 0
    found: int = 0
    page_fixed: int = 0
    reanchored: int = 0
    dropped: int = 0
    reasons: Counter = field(default_factory=Counter)

    def as_dict(self) -> dict:
        return {**{k: v for k, v in self.__dict__.items() if k != "reasons"}, "reasons": dict(self.reasons)}


@dataclass
class Located:
    page: int  # 1-based
    quote: str  # verbatim source text (the model's quote, or the re-anchored sentence)
    method: str  # exact | fuzzy | page_fixed | reanchored


class Checker:
    def __init__(self, pages: list[str]):
        self.raw = pages
        self.pages = [norm(p) for p in pages]
        self.stats = CheckStats()
        df: Counter = Counter()
        for p in self.pages:
            df.update(set(_WORD.findall(p)))
        self._df = df

    def _on(self, i: int, q: str) -> bool:
        if not (0 <= i < len(self.pages)):
            return False
        return q in self.pages[i] or quote_in_text(q, self.pages[i]) or (
            i + 1 < len(self.pages) and q in (self.pages[i] + " " + self.pages[i + 1]))  # fmt: skip

    def _candidates(self, q: str, claimed: int | None) -> list[int]:
        order: list[int] = []
        if claimed is not None:
            order += [claimed - 1, claimed - 2, claimed]  # 0-based: claimed, previous, next
        words = sorted(set(_WORD.findall(q)), key=lambda w: self._df.get(w, 0))[:3]
        if words:
            order += [i for i, p in enumerate(self.pages) if all(w in p for w in words)]
        seen, out = set(), []
        for i in order:
            if 0 <= i < len(self.pages) and i not in seen:
                seen.add(i)
                out.append(i)
        return out

    def locate(self, quote: str | None, page: int | None, anchor_number: str | float | None = None) -> Located | None:
        """Find `quote` (claimed on 1-based `page`). Returns where it really is, or None (dropped)."""
        self.stats.checked += 1
        if not quote or len(norm(quote)) < 8:
            self.stats.dropped += 1
            self.stats.reasons["empty_or_short"] += 1
            return None
        parts = [p for p in re.split(r"\s*(?:\.\.\.|…)\s*", quote) if len(norm(p)) >= 8] or [quote]
        q = norm(parts[0])
        for i in self._candidates(q, page):
            if self._on(i, q) and all(self._on(i, norm(p)) or self._on(i - 1, norm(p)) for p in parts[1:]):
                self.stats.found += 1
                if page is not None and i != page - 1:
                    self.stats.page_fixed += 1
                    return Located(i + 1, quote, "page_fixed")
                return Located(i + 1, quote, "exact")
        if anchor_number is not None and page is not None:
            hit = self._reanchor(quote, page, anchor_number)
            if hit:
                self.stats.reanchored += 1
                return hit
        self.stats.dropped += 1
        self.stats.reasons["not_in_source"] += 1
        return None

    def _reanchor(self, quote: str, page: int, number) -> Located | None:
        want = set(_WORD.findall(norm(quote)))
        num = _num_str(number)
        best: tuple[float, int, str] | None = None
        for i in (page - 1, page - 2, page):
            if not (0 <= i < len(self.raw)):
                continue
            for sent in _sentences(clean(self.raw[i])):
                ns = norm(sent)
                if num and num not in _NUM.findall(ns.replace(",", "")):
                    continue
                words = set(_WORD.findall(ns))
                if not words:
                    continue
                score = len(want & words) / len(want | words)
                if best is None or score > best[0]:
                    best = (score, i, " ".join(sent.split()))
        if best and best[0] >= 0.35:
            return Located(best[1] + 1, best[2], "reanchored")
        return None


def _sentences(text: str) -> list[str]:
    flat = " ".join(text.split())
    return [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"'“])", flat) if 20 <= len(s) <= 600]


def _num_str(x) -> str | None:
    if x is None:
        return None
    if isinstance(x, int | float):
        f = float(x)
        return str(int(f)) if f.is_integer() else f"{f:g}"
    m = _NUM.search(str(x).replace(",", ""))
    return m.group(0) if m else None


def numbers_in(text: str) -> list[float]:
    """Every number printed in `text` (Indian separators removed)."""
    out = []
    for m in _NUM.findall(text.replace(",", "")):
        try:
            out.append(float(m))
        except ValueError:
            pass
    return out


def number_in_quote(value: float | None, quote: str) -> bool:
    """The model's target/actual must be printed in its own (verified) quote — no invented numbers."""
    if value is None:
        return True
    return any(abs(n - value) < 1e-9 or abs(n - value) <= abs(value) * 1e-6 for n in numbers_in(quote))


def strip_boilerplate(pages: list[str]) -> list[str]:
    """Drop header/footer lines that repeat on more than half the pages (company name, address, page numbers),
    so quotes don't straddle them and the prompt stays short."""
    if len(pages) < 4:
        return pages
    counts: Counter = Counter()
    for p in pages:
        counts.update({re.sub(r"\d+", "#", ln.strip().lower()) for ln in p.splitlines() if ln.strip()})
    common = {k for k, v in counts.items() if v > len(pages) / 2 and len(k) < 120}
    return ["\n".join(ln for ln in p.splitlines() if re.sub(r"\d+", "#", ln.strip().lower()) not in common)
            for p in pages]  # fmt: skip
