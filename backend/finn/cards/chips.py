"""Inline chips for dividends and bonus/splits — from NSE's corporate-actions feed, no model (rule: rules first)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from finn.citations import filing_doc
from finn.models import ChipDetail, Citation, Figure


def chip_for(event: dict, actions: list[dict], filing: dict | None) -> ChipDetail | None:
    """The corporate action this event announces: same kind, ex-date from 5 days before to 120 days after."""
    start: date = event["started_at"].date()
    kinds = ("dividend",) if event["category"] == "dividend" else ("bonus", "split")
    cands = [a for a in actions if a["kind"] in kinds and start - timedelta(days=5) <= a["ex_date"] <= start +
             timedelta(days=120)]  # fmt: skip
    if not cands:
        return None
    a = min(cands, key=lambda a: a["ex_date"])
    rec = a.get("record_date")
    when = f"record {rec:%d %b}" if rec else f"ex {a['ex_date']:%d %b}"
    doc = filing_doc(filing) if filing else None
    url = doc[0] if doc else f"https://www.nseindia.com/get-quotes/equity?symbol={event['symbol']}"
    cite = Citation(source_type="exchange_filing", url=url, title=f"NSE corporate action: {a['subject'][:80]}",
                    exchange="NSE", locator=f"nse:corporate-actions/{event['symbol']}/{a['ex_date']}",
                    retrieved_at=a.get("fetched_at") or datetime.now(UTC))  # fmt: skip
    amount = None
    if a["kind"] == "dividend" and a.get("amount_per_share"):
        amount = Figure(label="Dividend per share", value=a["amount_per_share"], unit="INR_PER_SHARE",
                        status="verified", citation=cite, raw=a["subject"])  # fmt: skip
        text = f"₹{a['amount_per_share']:g} dividend · {when}"
    elif a["kind"] == "bonus" and a.get("ratio_new"):
        text = f"Bonus {a['ratio_new']:g}:{a['ratio_held']:g} · {when}"
    elif a["kind"] == "split" and a.get("ratio_new"):
        text = f"Split {a['ratio_new']:g}:1 · {when}"
    else:
        text = f"{a['subject'][:60]} · {when}"
    return ChipDetail(text=text, ex_date=a["ex_date"], record_date=rec, amount=amount, citation=cite)
