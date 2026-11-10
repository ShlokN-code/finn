"""Freeze one rich trading day for the Showcase replay mode (PRODUCT.md §11).

Writes everything the Brief needs for the portfolio on IST day D — filings (classified), the events they
belong to (full timelines), prices with 20 prior sessions, nearby corporate actions, that day's deals and
source freshness — to the `snapshots` table AND to backend/data/snapshots/<D>.json (committed to git, so the
replay survives a Supabase pause; rule 7).

python -m jobs.snapshot                 # suggest the richest day of the last 30 and freeze it
python -m jobs.snapshot --date 2026-10-30
python -m jobs.snapshot --suggest       # only print the ranking
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from finn import store
from finn.calendar import IST, ist_today
from finn.db import connect
from finn.portfolio import tracked_symbols

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "snapshots"
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="")
    ap.add_argument("--symbols", default="")
    ap.add_argument("--suggest", action="store_true")
    args = ap.parse_args()
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
