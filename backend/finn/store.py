"""Persistence for the ingest pipeline: idempotent upserts and the reads the pipeline needs.

Every write is an upsert keyed on the natural id, so re-running a job (or a backfill) is safe.
Classification fields are written only by save_classification, never clobbered by a re-fetch.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict
from datetime import date, datetime

from psycopg.types.json import Jsonb

from finn.models import Event, Filing
from finn.sources.nse import CorporateAction, Deal
from finn.sources.prices import Bar

# --- securities / holidays -------------------------------------------------------------------


def upsert_securities(conn, rows: Iterable[dict]) -> int:
    rows = [r for r in rows if r.get("symbol")]
    with conn.cursor() as cur:
        cur.executemany(
            "insert into public.securities (symbol, isin, name, series, updated_at) values (%s,%s,%s,%s, now()) "
            "on conflict (symbol) do update set isin = excluded.isin, name = excluded.name, "
            "series = excluded.series, updated_at = now()",
            [(r["symbol"], r.get("isin"), r.get("name"), r.get("series")) for r in rows],
        )
    return len(rows)


def company_names(conn, symbols: list[str]) -> dict[str, str]:
    rows = conn.execute("select symbol, name from public.securities where symbol = any(%s)", (symbols,)).fetchall()
    return {r["symbol"]: r["name"] for r in rows if r["name"]}


def upsert_holidays(conn, days: list[tuple[date, str]], source: str) -> int:
    with conn.cursor() as cur:
        cur.executemany(
            "insert into public.market_holidays (date, description, source) values (%s,%s,%s) "
            "on conflict (date) do update set description = excluded.description, source = excluded.source, "
            "fetched_at = now()",
            [(d, desc, source) for d, desc in days],
        )
    return len(days)


def load_holidays(conn) -> set[date]:
    return {r["date"] for r in conn.execute("select date from public.market_holidays")}


# --- prices -----------------------------------------------------------------------------------


def stored_closes(conn, symbol: str, since: date) -> dict[date, float]:
    rows = conn.execute(
        "select date, close from public.prices_daily where symbol = %s and date >= %s", (symbol, since)
    ).fetchall()
    return {r["date"]: r["close"] for r in rows if r["close"] is not None}


def price_row_counts(conn, symbols: list[str]) -> dict[str, int]:
    rows = conn.execute(
        "select symbol, count(*) as n from public.prices_daily where symbol = any(%s) group by symbol", (symbols,)
    ).fetchall()
    return {r["symbol"]: r["n"] for r in rows}


def replace_prices(conn, symbol: str, bars: list[Bar]) -> None:
    """Full-history replace (after a split/bonus restatement)."""
    with conn.transaction():
        conn.execute("delete from public.prices_daily where symbol = %s", (symbol,))
        upsert_prices(conn, bars)


def upsert_prices(conn, bars: list[Bar]) -> int:
    with conn.cursor() as cur:
        cur.executemany(
            "insert into public.prices_daily (symbol, date, open, high, low, close, adj_close, volume) "
            "values (%s,%s,%s,%s,%s,%s,%s,%s) on conflict (symbol, date) do update set open = excluded.open, "
            "high = excluded.high, low = excluded.low, close = excluded.close, adj_close = excluded.adj_close, "
            "volume = excluded.volume, fetched_at = now()",
            [(b.symbol, b.date, b.open, b.high, b.low, b.close, b.adj_close, b.volume) for b in bars],
        )
    return len(bars)


# --- filings ----------------------------------------------------------------------------------

_FILING_COLS = (
    "id, exchange, exchange_id, symbol, isin, bse_code, filed_at, exchange_category, subject, attachment_url, "
    "xbrl_url, category, category_source, category_model, category_confidence, stage, hidden_reason, "
    "duplicate_of, event_id, fetched_at"
)


def upsert_filings(conn, items: list[tuple[Filing, dict, str | None]]) -> int:
    """items: (filing, raw row, attachment size text). New rows are inserted unclassified; existing rows get
    refreshed source fields only (classification and threading are kept)."""
    with conn.cursor() as cur:
        cur.executemany(
            "insert into public.filings (id, exchange, exchange_id, symbol, isin, bse_code, filed_at, "
            "exchange_category, subject, attachment_url, attachment_size, xbrl_url, raw, fetched_at) "
            "values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) on conflict (id) do update set "
            "subject = excluded.subject, attachment_url = excluded.attachment_url, "
            "attachment_size = excluded.attachment_size, xbrl_url = excluded.xbrl_url, raw = excluded.raw, "
            "fetched_at = excluded.fetched_at",
            [
                (
                    f.id,
                    f.exchange,
                    f.exchange_id,
                    f.symbol,
                    f.isin,
                    f.bse_code,
                    f.filed_at,
                    f.exchange_category,
                    f.subject,
                    f.attachment_url,
                    size,
                    f.xbrl_url,
                    Jsonb(raw),
                    f.fetched_at,
                )
                for f, raw, size in items
            ],  # fmt: skip
        )
    return len(items)


def _filing(row: dict) -> Filing:
    return Filing(**{k: row[k] for k in _FILING_COLS.replace(" ", "").split(",")})


def filings_to_classify(conn, symbols: list[str] | None = None, retry_failed: bool = True) -> list[Filing]:
    """Unclassified filings, plus earlier failures caused by the model being unavailable (quota/no key)."""
    q = f"select {_FILING_COLS} from public.filings where (classify_tier is null"
    params: list = []
    if retry_failed:
        q += " or (classify_tier = 'failed' and classify_note like %s)"
        params.append("llm unavailable%")
    q += ")"
    if symbols:
        q += " and symbol = any(%s)"
        params.append(symbols)
    return [_filing(r) for r in conn.execute(q + " order by filed_at", params).fetchall()]


def save_classification(conn, f: Filing, tier: str, note: str | None) -> None:
    conn.execute(
        "update public.filings set category = %s, category_source = %s, category_model = %s, "
        "category_confidence = %s, stage = %s, hidden_reason = %s, classify_tier = %s, classify_note = %s "
        "where id = %s",
        (f.category, f.category_source, f.category_model, f.category_confidence, f.stage, f.hidden_reason, tier,
         note, f.id),
    )  # fmt: skip


def filings_for_symbols(conn, symbols: list[str]) -> list[Filing]:
    rows = conn.execute(
        f"select {_FILING_COLS} from public.filings where symbol = any(%s) and classify_tier is not null "
        "order by filed_at",
        (symbols,),
    ).fetchall()
    return [_filing(r) for r in rows]


def save_events(conn, symbols: list[str], events: list[Event], assignment: dict[str, str | None]) -> int:
    """Replace the threaded view for `symbols`: upsert events, drop events that no longer exist, set
    filings.event_id. Runs in one transaction so readers never see a half-threaded symbol."""
    keys = [e.id for e in events]
    with conn.transaction():
        with conn.cursor() as cur:
            cur.executemany(
                "insert into public.events (id, key, symbol, category, title, period, started_at, updated_at, "
                "timeline, figures, impact, impact_reason, driver_ids, refreshed_at) "
                "values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, now()) on conflict (id) do update set "
                "category = excluded.category, title = excluded.title, period = excluded.period, "
                "started_at = excluded.started_at, updated_at = excluded.updated_at, timeline = excluded.timeline, "
                "refreshed_at = now()",
                [
                    (
                        e.id,
                        e.key,
                        e.symbol,
                        e.category,
                        e.title,
                        Jsonb(e.period.model_dump(mode="json")) if e.period else None,
                        e.started_at,
                        e.updated_at,
                        Jsonb([t.model_dump(mode="json") for t in e.timeline]),
                        Jsonb([x.model_dump(mode="json") for x in e.figures]),
                        e.impact,
                        Jsonb(e.impact_reason.model_dump(mode="json")) if e.impact_reason else None,
                        Jsonb(e.driver_ids),
                    )
                    for e in events
                ],  # fmt: skip
            )
            conn.execute("delete from public.events where symbol = any(%s) and not (id = any(%s))", (symbols, keys))
            cur.executemany(
                "update public.filings set event_id = %s where id = %s and event_id is distinct from %s",
                [(ev, fid, ev) for fid, ev in assignment.items()],
            )
    return len(events)


# --- corporate actions & deals ----------------------------------------------------------------


def upsert_actions(conn, items: list[tuple[CorporateAction, dict]]) -> int:
    with conn.cursor() as cur:
        cur.executemany(
            "insert into public.corporate_actions (symbol, ex_date, subject, record_date, kind, ratio_new, "
            "ratio_held, amount_per_share, face_value, raw) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "on conflict (symbol, ex_date, subject) do update set record_date = excluded.record_date, "
            "kind = excluded.kind, ratio_new = excluded.ratio_new, ratio_held = excluded.ratio_held, "
            "amount_per_share = excluded.amount_per_share, raw = excluded.raw, fetched_at = now()",
            [
                (
                    a.symbol,
                    a.ex_date,
                    a.subject,
                    a.record_date,
                    a.kind,
                    a.ratio_new,
                    a.ratio_held,
                    a.amount_per_share,
                    a.face_value,
                    Jsonb(raw),
                )
                for a, raw in items
            ],  # fmt: skip
        )
    return len(items)


def upsert_deals(conn, deals: list[Deal]) -> int:
    with conn.cursor() as cur:
        cur.executemany(
            "insert into public.deals (id, date, symbol, kind, client, side, quantity, price, value_cr, remarks, raw) "
            "values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) on conflict (id) do nothing",
            [
                (
                    d.id,
                    d.date,
                    d.symbol,
                    d.kind,
                    d.client,
                    d.side,
                    d.quantity,
                    d.price,
                    d.value_cr,
                    d.remarks,
                    Jsonb(d.raw),
                )
                for d in deals
            ],  # fmt: skip
        )
    return len(deals)


# --- freshness & run log ----------------------------------------------------------------------


def mark_source(conn, source: str, scope: str, *, ok: bool, rows: int | None = None, error: str | None = None):
    conn.execute(
        "insert into public.source_status (source, scope, last_attempt_at, last_success_at, last_error, rows) "
        "values (%s, %s, now(), case when %s then now() end, %s, %s) on conflict (source, scope) do update set "
        "last_attempt_at = now(), last_success_at = case when %s then now() else source_status.last_success_at end, "
        "last_error = %s, rows = coalesce(%s, source_status.rows)",
        (source, scope, ok, None if ok else error, rows, ok, None if ok else error, rows),
    )


def start_run(conn, job: str, trigger: str) -> int:
    return conn.execute(
        "insert into public.ingest_runs (job, trigger) values (%s, %s) returning id", (job, trigger)
    ).fetchone()["id"]


def finish_run(conn, run_id: int, status: str, stats: dict, failures: list) -> None:
    conn.execute(
        "update public.ingest_runs set finished_at = now(), status = %s, stats = %s, failures = %s where id = %s",
        (status, Jsonb(stats), Jsonb(failures), run_id),
    )


def save_snapshot(conn, label: str, trading_date: date, payload: dict) -> None:
    conn.execute(
        "insert into public.snapshots (label, trading_date, payload) values (%s,%s,%s) on conflict (label) do "
        "update set trading_date = excluded.trading_date, payload = excluded.payload, created_at = now()",
        (label, trading_date, Jsonb(payload)),
    )


def jsonable(x):
    if isinstance(x, datetime | date):
        return x.isoformat()
    if hasattr(x, "__dataclass_fields__"):
        return {k: jsonable(v) for k, v in asdict(x).items()}
    if isinstance(x, dict):
        return {k: jsonable(v) for k, v in x.items()}
    if isinstance(x, list | tuple):
        return [jsonable(v) for v in x]
    return x


# --- results XBRL -----------------------------------------------------------------------------


def stored_xbrl_urls(conn, symbol: str) -> set[str]:
    rows = conn.execute("select xbrl_url from public.results_filings where symbol = %s", (symbol,)).fetchall()
    return {r["xbrl_url"] for r in rows}


def upsert_results_filing(conn, ref, parsed: dict, xml_gz: bytes | None) -> None:
    conn.execute(
        "insert into public.results_filings (symbol, period_end, basis, type_sub, audited, xbrl_url, broadcast_at, "
        "facts, xml_gz) values (%s,%s,%s,%s,%s,%s,%s,%s,%s) on conflict (symbol, period_end, basis, xbrl_url) do "
        "update set facts = excluded.facts, type_sub = excluded.type_sub, broadcast_at = excluded.broadcast_at, "
        "xml_gz = coalesce(excluded.xml_gz, results_filings.xml_gz), fetched_at = now()",
        (ref.symbol, ref.period_end, ref.basis, ref.type_sub, ref.audited, ref.xbrl_url, ref.broadcast_at,
         Jsonb(parsed), xml_gz),
    )  # fmt: skip


def results_filings(conn, symbol: str) -> list[dict]:
    """Stored XBRL instances for a symbol (no raw XML), newest version first within a quarter/basis."""
    return conn.execute(
        "select symbol, period_end, basis, type_sub, audited, xbrl_url, broadcast_at, facts, fetched_at "
        "from public.results_filings where symbol = %s order by period_end desc, basis, "
        "(type_sub = 'Revised') desc, broadcast_at desc nulls last",
        (symbol,),
    ).fetchall()


def recent_results_events(conn, symbols: list[str], days: int) -> list[dict]:
    """Results events with an outcome filing, updated in the last `days` days."""
    return conn.execute(
        "select id, symbol, period, timeline, detail, updated_at from public.events where category = 'results' "
        "and symbol = any(%s) and updated_at > now() - make_interval(days => %s) "
        "and exists (select 1 from jsonb_array_elements(timeline) t where t->>'stage' = 'outcome') "
        "order by updated_at desc",
        (symbols, days),
    ).fetchall()


def save_event_detail(conn, event_id: str, detail: dict | None, so_what: str | None, impact: str | None,
                      impact_reason: dict | None, impact_tier: str | None) -> None:  # fmt: skip
    conn.execute(
        "update public.events set detail = %s, so_what = %s, impact = %s, impact_reason = %s, impact_tier = %s, "
        "detail_at = now() where id = %s",
        (Jsonb(detail) if detail is not None else None, so_what, impact,
         Jsonb(impact_reason) if impact_reason is not None else None, impact_tier, event_id),
    )  # fmt: skip


def symbol_industry(conn, symbol: str) -> str | None:
    r = conn.execute(
        "select raw->>'smIndustry' as ind from public.filings where symbol = %s and raw ? 'smIndustry' "
        "order by filed_at desc limit 1",
        (symbol,),
    ).fetchone()
    return r["ind"] if r else None


def filing_urls(conn, ids: list[str]) -> dict[str, str | None]:
    rows = conn.execute("select id, attachment_url from public.filings where id = any(%s)", (ids,)).fetchall()
    return {r["id"]: r["attachment_url"] for r in rows}
