"""Card → Telegram message (HTML) + inline buttons: Open in FINN / Snooze."""

from __future__ import annotations

import os
from html import escape
from urllib.parse import quote

from finn.cards.build import CATEGORY_LABEL
from finn.format import figure_text
from finn.models import Card

IMPACT_DOT = {"positive": "🟢", "negative": "🔴", "mixed": "🟡", "neutral": "⚪"}
VERIFY = {"cross_checked": "✓ Cross-checked", "pending": "Cross-check pending",
          "mismatch": "⚠️ Couldn't verify — open filing"}  # fmt: skip


def web_base() -> str:
    return os.environ.get("WEB_BASE_URL", "").rstrip("/")


def card_url(card: Card) -> str | None:
    base = web_base()
    if base:
        return f"{base}/e/{quote(card.event_id, safe='')}"
    return card.sources[0].url if card.sources else None


def buttons(card: Card) -> list[list[dict]]:
    row: list[dict] = []
    if url := card_url(card):
        row.append({"text": "Open in FINN", "url": url})
    row.append({"text": "Snooze", "callback_data": f"snz:{card.symbol}"[:64]})
    return [row]


def card_text(card: Card, prefix: str | None = None) -> str:
    cat = CATEGORY_LABEL.get(card.category, card.category)
    dot = IMPACT_DOT.get(card.impact or "", "")
    lines = []
    if prefix:
        lines.append(prefix)
    lines.append(f"<b>{escape(card.symbol)}</b> · {escape(cat)} {dot}".rstrip())
    lines.append(escape(card.headline))
    lines.append(f"<i>{escape(card.so_what)}</i>")
    d = card.detail.model_dump(mode="json") if card.detail else {}
    if d.get("kind") == "results":
        if d.get("verification") != "mismatch":
            parts = []
            for ln in d.get("lines", []):
                yoy = ln.get("yoy") or {}
                extra = f" ({figure_text(yoy)} YoY)" if yoy.get("value") is not None else ""
                parts.append(f"{ln['metric']} {figure_text(ln['current'])}{extra}")
            lines.append(escape(" · ".join(parts)))
        lines.append(f"{VERIFY.get(d.get('verification'), '')} · {d.get('basis')} · {d['quarter']['label']}")
    elif d.get("kind") == "price_volume":
        for ex in d.get("explanations", [])[:2]:
            lines.append(escape(ex["text"]))
        if d.get("day_label"):
            lines.append(escape(d["day_label"]))
    elif card.key_figures:
        lines.append(
            escape(" · ".join(f"{f.label} {figure_text(f.model_dump(mode='json'))}" for f in card.key_figures))
        )
    if card.sources:
        lines.append(f'<a href="{escape(card.sources[0].url, quote=True)}">Source filing</a>')
    return "\n".join(lines)


def batch_text(cards: list[Card]) -> str:
    head = f"<b>{len(cards)} updates on your holdings</b>"
    rows = [f"• <b>{escape(c.symbol)}</b> {IMPACT_DOT.get(c.impact or '', '')} {escape(c.so_what)}" for c in cards]
    return "\n".join([head, *rows])


def batch_buttons() -> list[list[dict]]:
    base = web_base()
    return [[{"text": "Open FINN", "url": base}]] if base else []
