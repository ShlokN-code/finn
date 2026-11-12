"""Portfolio screen data (PRODUCT §7): prices, status dot, calendar, results scoreboard. All arithmetic in code.

Status dot (DECISIONS: status dot), from what FINN already knows, newest evidence first:
  pressure — a material event tagged negative in the last 30 days (results, M&A, management change, litigation,
             credit rating, pledging), or the stock is down 15 % or more over ~1 month (adjusted closes);
  watch    — any event tagged negative or mixed in the last 30 days, a price move no disclosure explains in the last
             7 days, or down 8 % or more over ~1 month;
  intact   — none of these. "unknown" when FINN has neither prices nor events for the symbol.
The reason names the trigger, so the dot is never a black box.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from finn.calendar import ist_today, now_utc, to_ist
from finn.cards.season import season_strip
from finn.models import CalendarItem, Citation, HoldingStatus, PortfolioResponse, PortfolioRow

CRITICAL = {"results", "mna", "management_change", "litigation", "credit_rating", "pledging"}
SPARK_SESSIONS = 23  # ≈ 1 month of trading days incl. both ends
PRESSURE_MOVE, WATCH_MOVE = -15.0, -8.0
CAL_DAYS = 60


def _pct(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None or b == 0 else (a - b) / b * 100


def prices(conn, symbols: list[str]) -> dict[str, list[dict]]:
    rows = conn.execute(
        "select symbol, date, close, adj_close from (select symbol, date, close, adj_close, row_number() over "
        "(partition by symbol order by date desc) rn from public.prices_daily where symbol = any(%s)) t "
        "where rn <= %s order by symbol, date",
        (symbols, SPARK_SESSIONS),
    ).fetchall()
    out: dict[str, list[dict]] = {}
    for r in rows:
        out.setdefault(r["symbol"], []).append(r)
    return out


def status_for(sym: str, events: list[dict], month_pct: float | None, now: datetime) -> HoldingStatus:
    recent = sorted((e for e in events if e["symbol"] == sym), key=lambda e: e["updated_at"], reverse=True)
    d30, d7 = now - timedelta(days=30), now - timedelta(days=7)
    for e in recent:
        if e["updated_at"] >= d30 and e.get("impact") == "negative" and e["category"] in CRITICAL:
            return HoldingStatus(
                level="pressure",
                event_id=e["id"],
                reason=f"{_label(e)} tagged negative · {to_ist(e['updated_at']):%d %b}",
            )
    if month_pct is not None and month_pct <= PRESSURE_MOVE:
        return HoldingStatus(level="pressure", reason=f"Down {abs(month_pct):.1f}% over the last month")
    for e in recent:
        if e["updated_at"] >= d30 and e.get("impact") in ("negative", "mixed"):
            return HoldingStatus(
                level="watch",
                event_id=e["id"],
                reason=f"{_label(e)} tagged {e['impact']} · {to_ist(e['updated_at']):%d %b}",
            )
        if (
            e["updated_at"] >= d7
            and e["category"] == "price_volume"
            and "no disclosure" in (e.get("so_what") or "").lower()
        ):
            return HoldingStatus(
                level="watch", event_id=e["id"], reason=f"Unexplained price move · {to_ist(e['updated_at']):%d %b}"
            )
    if month_pct is not None and month_pct <= WATCH_MOVE:
        return HoldingStatus(level="watch", reason=f"Down {abs(month_pct):.1f}% over the last month")
    if month_pct is None and not recent:
        return HoldingStatus(level="unknown", reason="FINN has no prices or filings for this symbol yet")
    return HoldingStatus(level="intact", reason="No negative filing in 30 days; no sharp fall this month")


LABELS = {
    "results": "Results",
    "mna": "M&A",
    "management_change": "Management change",
    "litigation": "Litigation",
    "credit_rating": "Credit rating",
    "pledging": "Pledging",
}


def _label(e: dict) -> str:
    return LABELS.get(e["category"], e["category"].replace("_", " ").capitalize())


def _parse_dmy(s: str | None) -> date | None:
    try:
        return datetime.strptime(s or "", "%d-%b-%Y").date()
    except ValueError:
        return None


def calendar(conn, symbols: list[str], today: date) -> list[CalendarItem]:
    out: dict[tuple, CalendarItem] = {}
    rows = conn.execute(
        "select symbol, raw->>'bm_date' d, raw->>'bm_purpose' p, attachment_url u from public.filings "
        "where symbol = any(%s) and exchange_id like 'BM-%%'",
        (symbols,),
    ).fetchall()
    for r in rows:
        d = _parse_dmy(r["d"])
        if d is None or not today <= d <= today + timedelta(days=CAL_DAYS):
            continue
        purpose = (r["p"] or "Board meeting").strip()
        kind = "results" if "result" in purpose.lower() else "board_meeting"
        label = "Results board meeting" if kind == "results" else f"Board meeting · {purpose}"
        url = r["u"] if r["u"] and r["u"] not in ("-", "") and not r["u"].endswith(".xml") else None
        out.setdefault((r["symbol"], d, kind), CalendarItem(symbol=r["symbol"], on=d, kind=kind, label=label, url=url))
    for r in conn.execute(
        "select symbol, ex_date, subject, kind from public.corporate_actions where symbol = any(%s) "
        "and ex_date between %s and %s",
        (symbols, today, today + timedelta(days=CAL_DAYS)),
    ).fetchall():
        k = (
            r["kind"]
            if r["kind"] in ("dividend", "bonus_split")
            else (
                "bonus_split"
                if r["kind"] in ("bonus", "split")
                else "agm"
                if "agm" in (r["subject"] or "").lower()
                else "other"
            )
        )
        out.setdefault(
            (r["symbol"], r["ex_date"], k),
            CalendarItem(symbol=r["symbol"], on=r["ex_date"], kind=k, label=f"Ex-date · {r['subject']}"),
        )
    # one row per company and day: a results board meeting wins over its plain "intimation" duplicate
    best: dict[tuple, CalendarItem] = {}
    rank = {"results": 0, "dividend": 1, "bonus_split": 1, "agm": 2, "board_meeting": 3, "other": 4}
    for c in out.values():
        k = (c.symbol, c.on, c.kind in ("dividend", "bonus_split", "agm", "other"))
        if k not in best or rank[c.kind] < rank[best[k].kind]:
            best[k] = c
    return sorted(best.values(), key=lambda c: (c.on, c.symbol))


def portfolio(conn, symbols: list[str], now: datetime | None = None) -> PortfolioResponse:
    now = now or now_utc()
    today = ist_today(now)
    px = prices(conn, symbols)
    names = {
        r["symbol"]: r["name"]
        for r in conn.execute(
            "select symbol, name from public.securities where symbol = any(%s)", (symbols,)
        ).fetchall()
    }
    events = conn.execute(
        "select id, symbol, category, impact, so_what, updated_at from public.events where symbol = any(%s) "
        "and updated_at >= %s",
        (symbols, now - timedelta(days=31)),
    ).fetchall()
    exd = {
        r["symbol"]: r
        for r in conn.execute(
            "select symbol, subject from public.corporate_actions where symbol = any(%s) and ex_date = %s",
            (symbols, today),
        ).fetchall()
    }
    rows = []
    for sym in symbols:
        p = px.get(sym, [])
        adj = [r["adj_close"] or r["close"] for r in p]
        last = p[-1] if p else None
        day = _pct(adj[-1], adj[-2]) if len(adj) >= 2 else None
        month = _pct(adj[-1], adj[0]) if len(adj) >= 15 else None
        rows.append(
            PortfolioRow(
                symbol=sym,
                name=names.get(sym),
                last_close=float(last["close"]) if last else None,
                close_date=last["date"] if last else None,
                day_change_pct=day,
                month_change_pct=month,
                spark=[round(float(x), 2) for x in adj],
                status=status_for(sym, events, month, now),
                ex_date_today=f"Ex today · {exd[sym]['subject']}" if sym in exd else None,
            )
        )
    as_of = max((r.close_date for r in rows if r.close_date), default=None)
    src = Citation(
        source_type="price_feed",
        url="https://finance.yahoo.com/",
        title="Yahoo Finance daily closes (split/bonus-adjusted; day change on dividend-adjusted closes)",
        retrieved_at=now,
    )
    return PortfolioResponse(
        rows=rows,
        calendar=calendar(conn, symbols, today),
        season=season_strip(conn, symbols, now),
        prices_as_of=as_of,
        price_source=src,
    )
