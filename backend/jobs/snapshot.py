"""Freeze one rich trading day for the Showcase replay mode (PRODUCT.md §11).

Writes everything the Brief needs for the portfolio on IST day D — filings (classified), the events they
belong to (full timelines), prices with 20 prior sessions, nearby corporate actions, that day's deals and
source freshness — to the `snapshots` table AND to backend/data/snapshots/<D>.json (committed to git, so the
replay survives a Supabase pause; rule 7).

python -m jobs.snapshot                 # suggest the richest day of the last 30 and freeze it
python -m jobs.snapshot --date 2026-10-30
python -m jobs.snapshot --suggest       # only print the ranking
python -m jobs.snapshot --brief 2026-10-30   # freeze that day's ranked Brief for the web's Showcase replay

The frozen Brief ranks the snapshot day's events (as stored now, with their built card details) for the demo
portfolio, with each timeline cut at the end of that IST day, and writes it to
backend/data/snapshots/<D>.brief.json and web/public/showcase/brief.json (DECISIONS: Showcase replay).
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from finn import store
from finn.calendar import IST, ist_today
from finn.cards.brief import EVENT_COLS, hidden_counts, hidden_filings, hidden_items, load_filings, rank
from finn.cards.counts import brief_counts
from finn.cards.season import season_strip
from finn.db import connect
from finn.models import BriefResponse
from finn.portfolio import DEMO_WEIGHTS, tracked_symbols
from finn.ranking.score import REPEAT_WINDOW_DAYS

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "snapshots"
WEB_SHOWCASE = Path(__file__).resolve().parents[2] / "web" / "public" / "showcase" / "brief.json"
MATERIAL = ("results", "earnings_call", "mna", "management_change", "litigation", "credit_rating", "pledging",
            "capex", "press_release", "fund_raise", "insider_trading")  # fmt: skip


def rank_days(conn, symbols: list[str], days: int = 30) -> list[dict]:
    """Days ranked by material filings for the portfolio (results-thread filings weigh double)."""
    rows = conn.execute(
        "select (filed_at at time zone 'Asia/Kolkata')::date as d, "
        "count(*) filter (where category in ('results','earnings_call')) as results, "
        "count(*) filter (where category = any(%s)) as material, count(*) as total, "
        "count(distinct symbol) filter (where category = any(%s)) as symbols "
        "from public.filings where symbol = any(%s) and duplicate_of is null "
        "and filed_at >= now() - make_interval(days => %s) group by 1",
        (list(MATERIAL), list(MATERIAL), symbols, days),
    ).fetchall()
    for r in rows:
        r["score"] = 2 * r["results"] + r["material"] + r["symbols"]
    return sorted(rows, key=lambda r: r["score"], reverse=True)


def build(conn, d: date, symbols: list[str]) -> dict:
    start = datetime(d.year, d.month, d.day, tzinfo=IST).astimezone(UTC)
    end = start + timedelta(days=1)
    filings = conn.execute(
        "select id, exchange, exchange_id, symbol, isin, filed_at, exchange_category, subject, attachment_url, "
        "attachment_size, xbrl_url, category, category_source, category_model, category_confidence, classify_tier, "
        "classify_note, stage, hidden_reason, duplicate_of, event_id, fetched_at from public.filings "
        "where symbol = any(%s) and filed_at >= %s and filed_at < %s order by filed_at",
        (symbols, start, end),
    ).fetchall()
    event_ids = sorted({f["event_id"] for f in filings if f["event_id"]})
    events = conn.execute("select * from public.events where id = any(%s) order by updated_at desc",
                          (event_ids,)).fetchall()  # fmt: skip
    prices = conn.execute(
        "select * from (select symbol, date, open, high, low, close, adj_close, volume, "
        "row_number() over (partition by symbol order by date desc) as rn from public.prices_daily "
        "where symbol = any(%s) and date <= %s) t where rn <= 21 order by symbol, date",
        (symbols, d),
    ).fetchall()
    actions = conn.execute(
        "select symbol, ex_date, record_date, subject, kind, ratio_new, ratio_held, amount_per_share "
        "from public.corporate_actions where symbol = any(%s) and ex_date between %s and %s order by ex_date",
        (symbols, d - timedelta(days=7), d + timedelta(days=30)),
    ).fetchall()
    deals = conn.execute(
        "select date, symbol, kind, client, side, quantity, price, value_cr from public.deals "
        "where symbol = any(%s) and date = %s",
        (symbols, d),
    ).fetchall()
    freshness = conn.execute("select * from public.source_status where scope = any(%s) or scope = 'all'",
                             (symbols,)).fetchall()  # fmt: skip
    tiers: dict[str, int] = {}
    for f in filings:
        tiers[f["classify_tier"] or "pending"] = tiers.get(f["classify_tier"] or "pending", 0) + 1
    hidden = [f for f in filings if not f["event_id"]]
    for r in prices:
        r.pop("rn", None)
    return store.jsonable({
        "label": f"showcase-{d.isoformat()}",
        "trading_date": d,
        "frozen_at": datetime.now(UTC),
        "symbols": symbols,
        "summary": {"filings": len(filings), "events": len(events), "hidden_filings": len(hidden),
                    "tier_split": tiers, "deals": len(deals)},
        "filings": filings,
        "events": events,
        "prices": prices,
        "corporate_actions": actions,
        "deals": deals,
        "freshness": freshness,
    })  # fmt: skip


def _ts(x) -> datetime:
    return x if isinstance(x, datetime) else datetime.fromisoformat(str(x).replace("Z", "+00:00"))


def freeze_brief(conn, d: date, weights: dict[str, float]) -> BriefResponse:
    """The demo portfolio's Brief for IST day d, from the committed snapshot's events."""
    snap = json.loads((OUT_DIR / f"{d.isoformat()}.json").read_text())
    start = datetime(d.year, d.month, d.day, tzinfo=IST).astimezone(UTC)
    end = start + timedelta(days=1)
    ids = [e["id"] for e in snap["events"]]
    events = conn.execute(f"select {EVENT_COLS} from public.events where id = any(%s)", (ids,)).fetchall()
    for e in events:
        e["timeline"] = [t for t in (e.get("timeline") or []) if _ts(t["at"]) < end]
    events = [e for e in events if e["timeline"]]
    symbols = sorted(weights)
    context = conn.execute(
        "select id, symbol, category, started_at from public.events where symbol = any(%s) "
        "and started_at >= %s and started_at < %s",
        (symbols, start - timedelta(days=REPEAT_WINDOW_DAYS + 1), end),
    ).fetchall()
    cards = rank(events, load_filings(conn, events), weights, [], start, context)
    rows = hidden_filings(conn, symbols, start, end)
    frozen = _ts(snap["frozen_at"])
    return BriefResponse(
        cards=cards, hidden=hidden_counts(rows), hidden_total=len(rows), hidden_items=hidden_items(rows),
        counts=brief_counts(cards, len(rows), start), season=season_strip(conn, symbols, end - timedelta(seconds=1)),
        rules=[], data_as_of=min(end - timedelta(minutes=1), frozen), since=start, window="since",
        showcase=d.isoformat(),
    )  # fmt: skip


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="")
    ap.add_argument("--symbols", default="")
    ap.add_argument("--suggest", action="store_true")
    ap.add_argument("--brief", default="", help="Freeze the ranked Brief for this already-snapshotted IST day")
    args = ap.parse_args()
    if args.brief:
        d = date.fromisoformat(args.brief)
        with connect() as conn:
            b = freeze_brief(conn, d, DEMO_WEIGHTS)
        text = json.dumps(b.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":")) + "\n"
        for out in (OUT_DIR / f"{d.isoformat()}.brief.json", WEB_SHOWCASE):
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text)
        print(f"showcase brief {d}: {len(b.cards)} cards, {b.hidden_total} hidden, counts={b.counts.model_dump()}")
        print(f"  season: {b.season.reported if b.season else '-'} reported → {WEB_SHOWCASE}")
        return
    symbols = tracked_symbols(args.symbols or None)
    with connect() as conn:
        ranked = rank_days(conn, symbols)
        print("richest days (last 30):")
        for r in ranked[:7]:
            print(f"  {r['d']}  score={r['score']:3}  results={r['results']:3}  material={r['material']:3}  "
                  f"symbols={r['symbols']:2}  total={r['total']}")  # fmt: skip
        if args.suggest:
            return
        d = date.fromisoformat(args.date) if args.date else (ranked[0]["d"] if ranked else ist_today())
        payload = build(conn, d, symbols)
        store.save_snapshot(conn, payload["label"], d, payload)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{d.isoformat()}.json"
    out.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")
    print(f"snapshot {payload['label']}: {payload['summary']} → {out}")


if __name__ == "__main__":
    main()
