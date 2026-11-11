"""Tiny BM25 over transcript passages (no vector database): enough to find the later-call passages that speak to a
promise (JUDGE) and the passages that answer a question (Ask)."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from finn.research.checker import clean

_TOK = re.compile(r"[a-z0-9]+")
_STOP = set("""a an the and or of to in on for with at by from as is are was were be been it its this that these those
we our you your they their i he she will would should could can may might have has had do does did not no so if
then than there here what which who whom how when where also just about into over under more most very much any some
all each per vs""".split())  # fmt: skip
PASSAGE_WORDS = 110


def _stem(t: str) -> str:
    """Light suffix stripping so 'launched'/'launches'/'launching' match 'launch'."""
    for suf in ("ing", "ed", "es", "s"):
        if len(t) > len(suf) + 3 and t.endswith(suf):
            return t[: -len(suf)]
    return t


def tokens(text: str) -> list[str]:
    return [_stem(t) for t in _TOK.findall(text.lower()) if t not in _STOP and len(t) > 1]


@dataclass
class Passage:
    doc_id: str
    page: int  # 1-based
    text: str


def passages(doc_id: str, pages: list[str], size: int = PASSAGE_WORDS) -> list[Passage]:
    out = []
    for i, p in enumerate(pages, start=1):
        words = " ".join(clean(p).split()).split(" ")
        for j in range(0, len(words), size - 20):  # 20-word overlap so a sentence isn't cut in half
            chunk = " ".join(words[j : j + size]).strip()
            if len(chunk) >= 20:
                out.append(Passage(doc_id, i, chunk))
    return out


class BM25:
    def __init__(self, docs: list[Passage], k1: float = 1.4, b: float = 0.75):
        self.docs, self.k1, self.b = docs, k1, b
        self.toks = [Counter(tokens(d.text)) for d in docs]
        self.lens = [sum(c.values()) for c in self.toks]
        self.avg = (sum(self.lens) / len(self.lens)) if self.lens else 1.0
        df: Counter = Counter()
        for c in self.toks:
            df.update(c.keys())
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def search(self, query: str, k: int = 3, where=None) -> list[tuple[float, Passage]]:
        q = tokens(query)
        scored = []
        for i, d in enumerate(self.docs):
            if where and not where(d):
                continue
            c, ln, s = self.toks[i], self.lens[i], 0.0
            for t in q:
                f = c.get(t)
                if f:
                    s += self.idf.get(t, 0) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * ln / self.avg))
            if s > 0:
                scored.append((s, d))
        scored.sort(key=lambda x: -x[0])
        return scored[:k]
