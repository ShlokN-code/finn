"""EOD prices from Yahoo (yfinance): split/bonus-adjusted Close + Volume, dividend-adjusted Adj Close.

Yahoo rate-limits bursts, so symbols go in chunks of 5 with pauses and one retry pass for failures.
Yahoo's corporate-action columns are ignored (NSE's feed is the source of truth — DECISIONS.md).
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from datetime import date

log = logging.getLogger("finn.prices")

CHUNK = 5
PAUSE_S = 3.0
RESTATE_TOL = 0.005  # 0.5 %: a stored close this far from Yahoo's means history was re-adjusted


@dataclass
class Bar:
    symbol: str
    date: date
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    adj_close: float | None
    volume: int | None


def _f(x) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) else v


def fetch_bars(symbols: list[str], *, period: str | None = None, start: date | None = None) -> dict[str, list[Bar]]:
    """Daily bars per NSE symbol (Yahoo '<SYM>.NS'). Pass `period` ('1y', '1mo') or `start`.
    Returns only symbols that came back with data; callers record the rest as failed."""
    import yfinance as yf  # heavy import; only jobs need it

    out: dict[str, list[Bar]] = {}

    def run(batch: list[str]) -> None:
        for i in range(0, len(batch), CHUNK):
            chunk = batch[i : i + CHUNK]
            try:
                df = yf.download(
                    [f"{t}.NS" for t in chunk],
                    period=period,
                    start=start,
                    auto_adjust=False,
                    actions=False,
                    group_by="ticker",
                    progress=False,
                    threads=False,
                )
            except Exception as e:  # yfinance raises assorted errors (rate limit, JSON)
                log.warning("yfinance chunk %s failed: %s", chunk, e)
                time.sleep(PAUSE_S * 2)
                continue
            for t in chunk:
                try:
                    sub = df[f"{t}.NS"].dropna(how="all")
                except KeyError:
                    continue
                bars = [
                    Bar(
                        t,
                        idx.date(),
                        _f(r.get("Open")),
                        _f(r.get("High")),
                        _f(r.get("Low")),
                        _f(r.get("Close")),
                        _f(r.get("Adj Close")),
                        int(v) if (v := _f(r.get("Volume"))) is not None else None,
                    )
                    for idx, r in sub.iterrows()
                ]
                bars = [b for b in bars if b.close is not None]
                if bars:
                    out[t] = bars
            time.sleep(PAUSE_S)

    run(symbols)
    missing = [t for t in symbols if t not in out]
    if missing:
        log.info("retrying %d symbols after a pause: %s", len(missing), missing)
        time.sleep(PAUSE_S * 3)
        run(missing)
    return out


def needs_restatement(stored: dict[date, float], fresh: list[Bar], tol: float = RESTATE_TOL) -> bool:
    """True if any overlapping day's stored close differs from Yahoo's by more than `tol` (relative).

    Yahoo rewrites the whole history after a split/bonus; a 10-day incremental upsert would then leave older
    rows on the old basis, so the caller refetches the full year.
    """
    for b in fresh:
        old = stored.get(b.date)
        if old is None or b.close is None or old <= 0:
            continue
        if abs(b.close - old) / old > tol:
            return True
    return False
