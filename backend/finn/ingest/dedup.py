"""NSE↔BSE dedup: the same document filed on both exchanges is kept once (the later copy points at the
earlier via Filing.duplicate_of).

Matching, strongest first:
  1. same symbol, attachment sizes agree at NSE's printed precision ('228.94 KB', '1.98 MB'), |Δt| ≤ 1 day;
  2. no size on one side: subject-token similarity ≥ 0.6 and |Δt| ≤ 15 min.
Pairs are assigned one-to-one by smallest time gap, so two identical-size PDFs filed minutes apart
(e.g. 'Outcome of Board Meeting' and 'Financial Results' carrying the same file) pair up in time order.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from finn.models import Filing

MAX_GAP_S = 86400
SUBJECT_ONLY_GAP_S = 900
SUBJECT_SIM = 0.6


@dataclass
class Doc:
    filing: Filing
    size_bytes: int | None = None  # BSE gives exact bytes
    size_text: str | None = None  # NSE gives '228.94 KB' / '1.98 MB'


def _size_matches(nse_text: str, bse_bytes: int) -> bool:
    m = re.match(r"\s*([\d.]+)\s*(KB|MB|GB|B)\b", nse_text, re.I)
    if not m:
        return False
    value, unit = float(m.group(1)), m.group(2).upper()
    scale = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}[unit]
    decimals = len(m.group(1).split(".")[1]) if "." in m.group(1) else 0
    return round(bse_bytes / scale, decimals) == round(value, decimals)


_WORD = re.compile(r"[a-z0-9]+")
_STOP = {"the", "of", "and", "to", "for", "a", "an", "in", "on", "under", "regulation", "lodr", "sebi",
         "announcement", "company", "limited", "ltd", "has", "informed", "exchange", "about", "regarding"}  # fmt: skip


def subject_similarity(a: str, b: str) -> float:
    ta = {w for w in _WORD.findall(a.lower()) if w not in _STOP}
    tb = {w for w in _WORD.findall(b.lower()) if w not in _STOP}
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def match(nse: list[Doc], bse: list[Doc]) -> list[tuple[Doc, Doc]]:
    """One-to-one NSE↔BSE pairs judged to be the same document."""
    cands: list[tuple[float, int, int]] = []
    for i, n in enumerate(nse):
        for j, b in enumerate(bse):
            if n.filing.symbol != b.filing.symbol:
                continue
            gap = abs((n.filing.filed_at - b.filing.filed_at).total_seconds())
            if gap > MAX_GAP_S:
                continue
            if n.size_text and b.size_bytes:
                if _size_matches(n.size_text, b.size_bytes):
                    cands.append((gap, i, j))
            elif gap <= SUBJECT_ONLY_GAP_S and subject_similarity(n.filing.subject, b.filing.subject) >= SUBJECT_SIM:
                cands.append((gap + 0.5, i, j))
    cands.sort()
    used_n, used_b, pairs = set(), set(), []
    for _, i, j in cands:
        if i in used_n or j in used_b:
            continue
        used_n.add(i)
        used_b.add(j)
        pairs.append((nse[i], bse[j]))
    return pairs


def mark_duplicates(nse: list[Doc], bse: list[Doc]) -> int:
    """Set duplicate_of on the later copy of each matched pair. Returns the number of pairs."""
    pairs = match(nse, bse)
    for n, b in pairs:
        first, later = (n, b) if n.filing.filed_at <= b.filing.filed_at else (b, n)
        later.filing.duplicate_of = first.filing.id
        first.filing.duplicate_of = None
    return len(pairs)
