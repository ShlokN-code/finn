"""Level-1 relevance: does an event touch a driver the user confirmed? (PRODUCT §5; DECISIONS: driver boost)

Rules only, no model. A driver is matched only on strong evidence, otherwise there is no boost:

- **Results** (numbers shown, not "Couldn't verify"): the card's own lines — Revenue/NII → Growth, EBITDA margin →
  Margins, PAT → Profit.
- **Category**: capex → Capex, Capacity; credit rating → Leverage; dividend / bonus / buyback → Payout.
- **Specific words** in the event's headline or so-what, for drivers that name something concrete (order book,
  capacity, deposits, asset quality…), whole words only, from a curated list. Generic words ("growth", "share",
  "investment", "costs", "margin" alone outside results) never count — too weak to boost.

Driver ids are `SYMBOL:slug` with slug = label lower-cased, spaces → hyphens (finn.research.insights).
"""

from __future__ import annotations

import re

from finn.research.metrics import METRICS

RESULTS_LINES = {"Revenue": "Growth", "NII": "Growth", "EBITDA margin": "Margins", "PAT": "Profit"}
CATEGORY = {"capex": ("Capex", "Capacity"), "credit_rating": ("Leverage",), "dividend": ("Payout",),
            "bonus_split": ("Payout",)}  # fmt: skip
KEYWORD_LABELS = {"Capacity", "Capex", "Order book", "Deal wins", "Customers", "Market share", "Deposits",
                  "Asset quality", "Leverage", "Utilisation", "Volumes", "Working capital", "Payout"}  # fmt: skip
GENERIC = {"share", "investment", "invest", "plant", "costs", "margin", "margins", "savings", "provisions",
           "customer", "inventory days", "commission"}  # fmt: skip
EXTRA = {"Order book": ("order book", "orders", "order win", "letter of award", "contract"),
         "Capacity": ("capacity", "commissioned", "commissioning", "new plant", "new facility"),
         "Volumes": ("volumes", "volume", "sales volume", "production"),
         "Leverage": ("debt", "borrowings", "leverage", "deleveraging", "net debt")}  # fmt: skip


def _slug(label: str) -> str:
    return label.lower().replace(" ", "-")


SLUG_LABEL = {_slug(m.label): m.label for m in METRICS.values()}


def label_for(driver_id: str) -> str | None:
    return SLUG_LABEL.get(driver_id.split(":", 1)[-1])


def _keywords() -> dict[str, tuple[str, ...]]:
    out: dict[str, set[str]] = {}
    for m in METRICS.values():
        if m.label in KEYWORD_LABELS:
            out.setdefault(m.label, set()).update(s for s in m.synonyms if s not in GENERIC and len(s) >= 4)
    for label, words in EXTRA.items():
        out.setdefault(label, set()).update(words)
    return {k: tuple(sorted(v)) for k, v in out.items()}


KEYWORDS = _keywords()
_RE = {label: re.compile(r"\b(?:" + "|".join(map(re.escape, ws)) + r")\b", re.I) for label, ws in KEYWORDS.items()}


def touched(event: dict) -> set[str]:
    """Driver labels this event touches on strong evidence."""
    out: set[str] = set(CATEGORY.get(event.get("category") or "", ()))
    detail = event.get("detail") or {}
    if detail.get("kind") == "results" and detail.get("verification") != "mismatch":
        for ln in detail.get("lines") or []:
            if (lab := RESULTS_LINES.get(ln.get("metric") or "")) and ln.get("current"):
                out.add(lab)
    if event.get("category") != "results":
        text = " ".join(str(event.get(k) or "") for k in ("title", "so_what"))
        out |= {label for label, rx in _RE.items() if rx.search(text)}
    return out


def match(event: dict, confirmed_ids: list[str]) -> list[tuple[str, str]]:
    """(driver id, label) for the user's confirmed drivers of this event's company that it touches."""
    sym = event.get("symbol")
    mine = [(d, label_for(d)) for d in confirmed_ids if d.split(":", 1)[0] == sym]
    hit = touched(event)
    return [(d, lab) for d, lab in mine if lab and lab in hit]
