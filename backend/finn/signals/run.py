"""Daily signal step: compute every tracked stock's signal for the session, store it, and create a
price_volume event when any subscriber's rules (or the defaults) fire. Per-user filtering happens at dispatch."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta

from finn import store
from finn.cards.build import CATEGORY_LABEL
from finn.models import AlertSettings, Citation, Event, Figure, MoveExplanation, PriceVolumeDetail
from finn.signals import price_volume as pv

log = logging.getLogger("finn.signals")
LOOKBACK_DAYS = 130  # ≥ 60 sessions for σ, 20 for volume


def _fig(label: str, value: float, unit: str, url: str, locator: str, now: datetime) -> Figure:
    cite = Citation(source_type="price_feed", url=url, title="Yahoo Finance daily prices (adjusted)",
                    locator=locator, retrieved_at=now)  # fmt: skip
    return Figure(label=label, value=value, unit=unit, status="unverified", citation=cite)


def detail_for(sig: pv.Signal, explanations: list[pv.Explanation], fired: list[str], now: datetime):
    url = f"https://finance.yahoo.com/quote/{sig.symbol}.NS/history"
    loc = f"yahoo:{sig.symbol}.NS/{sig.date}"
    exps = [MoveExplanation(kind=e.kind, text=e.text,
                            citation=Citation(source_type="exchange_filing", url=e.url, exchange="NSE",
                                              retrieved_at=now) if e.url else None)
            for e in explanations]  # fmt: skip
    return PriceVolumeDetail(
        trading_date=sig.date,
        move_pct=_fig("Move (adjusted)", sig.move_pct, "PCT", url, loc, now),
        sector_move_pct=_fig(pv.INDEX_NAME.get(sig.sector_index, sig.sector_index), sig.sector_move_pct, "PCT",
                             f"https://finance.yahoo.com/quote/{sig.sector_index}/history",
                             f"yahoo:{sig.sector_index}/{sig.date}", now)
        if sig.sector_move_pct is not None else None,
        sector_index=pv.INDEX_NAME.get(sig.sector_index, sig.sector_index),
        relative_move_pct=None if sig.relative_move_pct is None else Figure(
            label="Move vs sector", value=sig.relative_move_pct, unit="PCT", status="unverified",
            formula="stock move − sector index move",
            inputs=[_fig("Move (adjusted)", sig.move_pct, "PCT", url, loc, now)]),
        z_score=round(sig.z, 2) if sig.z is not None else None,
        volume_ratio=_fig("Volume vs 20-day avg", sig.volume_ratio, "X", url, loc, now)
        if sig.volume_ratio is not None else None,
        day_label=sig.day_label, mechanical_pct=sig.mechanical_pct, triggers=fired, explanations=exps,
    )  # fmt: skip


def title_for(sig: pv.Signal, fired: list[str]) -> str:
    parts = [f"{sig.move_pct:+.1f}% on {sig.date:%d %b}"]
    if "volume" in fired and sig.volume_ratio:
        parts.append(f"volume {sig.volume_ratio:.1f}× normal")
    return f"Price/volume: {' · '.join(parts)}"


def so_what_for(explanations: list[pv.Explanation]) -> str:
    k = explanations[0].kind
    return {"filing": "Move follows a filing — read it", "bulk_block_deal": "A large deal went through today",
            "sector_move": "Mostly a sector move", "index_move": "Mostly a market move",
            "none": "No disclosure explains this move"}[k]  # fmt: skip


def step_signals(run, symbols: list[str], day: date, settings_list: list[AlertSettings]) -> None:
    conn, now = run.conn, datetime.now(UTC)
    bars = store.load_bars(conn, symbols + pv.INDEX_TICKERS, day - timedelta(days=LOOKBACK_DAYS))
    actions = store.actions_on(conn, symbols, day)
    deals = store.deals_on(conn, symbols, day)
    nifty = bars.get(pv.NIFTY)
    stats = {"day": str(day), "signals": 0, "events": [], "no_bar": []}
    settings_list = settings_list or [AlertSettings()]
    prevs = {s: pv.previous_session(bars.get(s, []), day) for s in symbols}
    lo = min((pv.session_window(day, p)[0] for p in prevs.values() if p), default=pv.at_close(day - timedelta(1)))
    filings = store.material_filings(conn, symbols, lo, pv.at_close(day))
    for sym in symbols:
        sector = pv.sector_index(sym, store.symbol_industry(conn, sym))
        sig = pv.compute(sym, bars.get(sym, []), day, actions.get(sym, []), sector, bars.get(sector), nifty)
        if sig is None or prevs[sym] is None:
            stats["no_bar"].append(sym)
            continue
        fired = sorted({t for st in settings_list for t in pv.triggers(sig, st)})
        exps = pv.explain(sig, filings.get(sym, []), deals.get(sym, []), prevs[sym], CATEGORY_LABEL)
        detail = detail_for(sig, exps, fired, now)
        store.upsert_price_signal(conn, sig, detail.model_dump(mode="json"))
        stats["signals"] += 1
        if not fired:
            continue
        eid = f"{sym}:price_volume:{day.isoformat()}"
        ev = Event(id=eid, key=eid, symbol=sym, category="price_volume", title=title_for(sig, fired),
                   started_at=pv.at_close(day), updated_at=now, so_what=so_what_for(exps), detail=detail)  # fmt: skip
        store.upsert_synthetic_event(conn, ev)
        stats["events"].append(f"{sym} {sig.move_pct:+.1f}% {','.join(fired)}")
    run.stats["signals"] = stats
