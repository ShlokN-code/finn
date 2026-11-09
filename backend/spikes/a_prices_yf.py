"""Spike (a): EOD price/volume via yfinance.

Questions:
- Does yfinance work from this machine for .NS tickers?
- With auto_adjust=False, is 'Close' raw or split-adjusted? Is 'Volume' split-adjusted?
- What corporate-action data comes back (dividends, splits; are bonuses shown as splits)?
"""

from __future__ import annotations

import pandas as pd
import yfinance as yf

from _common import Result, log, save_sample

TICKERS = ["RELIANCE.NS", "HDFCBANK.NS", "BAJFINANCE.NS"]  # BAJFINANCE: split + bonus Jun 2025

res = Result("a_prices_yf")

for sym in TICKERS:
    log(f"\n--- {sym} ---")
    t = yf.Ticker(sym)
    df = t.history(period="3y", interval="1d", auto_adjust=False, actions=True)
    if not res.check(f"{sym} history returned rows", len(df) > 200, f"{len(df)} rows"):
        continue
    log(f"  columns: {list(df.columns)}")
    log(f"  range: {df.index.min().date()} → {df.index.max().date()} (tz={df.index.tz})")
    last = df.iloc[-1]
    log(f"  last: Close={last['Close']:.2f} AdjClose={last['Adj Close']:.2f} Vol={int(last['Volume'])}")

    divs = df[df["Dividends"] > 0][["Dividends"]]
    splits = df[df["Stock Splits"] > 0][["Stock Splits"]]
    log(f"  dividends: {len(divs)}  splits/bonus rows: {len(splits)}")
    for d, row in splits.iterrows():
        log(f"    split {d.date()}: ratio {row['Stock Splits']}")

    # Is Close split-adjusted? Look at the window around each split.
    split_windows = {}
    for d in splits.index:
        i = df.index.get_loc(d)
        win = df.iloc[max(0, i - 2): i + 2][["Open", "High", "Low", "Close", "Adj Close", "Volume"]]
        log(f"  window around {d.date()}:\n{win.round(2).to_string()}")
        prev_close, ex_open = df["Close"].iloc[i - 1], df["Open"].iloc[i]
        jump = ex_open / prev_close - 1
        ratio = splits.loc[d, "Stock Splits"]
        res.check(
            f"{sym} Close is split-adjusted across {d.date()}",
            abs(jump) < 0.2,
            f"prev close {prev_close:.2f} → ex-date open {ex_open:.2f} ({jump:+.1%}); ratio {ratio}",
        )
        split_windows[str(d.date())] = win.reset_index().astype({"Date": str}).to_dict("records")

    # Close vs Adj Close: Adj Close also folds in dividends.
    diff = (df["Close"] / df["Adj Close"] - 1).abs()
    log(f"  Close/AdjClose max gap {diff.max():.2%} (oldest rows); min {diff.min():.4%} (latest)")
    res.check(f"{sym} Adj Close differs from Close (dividend adjustment)", diff.max() > 0.001)

    # Metadata
    try:
        fi = t.fast_info
        log(f"  fast_info: currency={fi.get('currency')} exchange={fi.get('exchange')} "
            f"mcap={fi.get('marketCap')}")
    except Exception as e:  # noqa: BLE001
        log(f"  fast_info failed: {e}")

    save_sample(f"a_{sym}_tail.json", df.tail(5).reset_index().astype({"Date": str}).to_dict("records"))
    save_sample(f"a_{sym}_actions.json", {
        "dividends": {str(k.date()): v for k, v in divs["Dividends"].items()},
        "splits": {str(k.date()): v for k, v in splits["Stock Splits"].items()},
        "split_windows": split_windows,
    })

# Batch download (what the nightly job would use)
log("\n--- batch download ---")
batch = yf.download(TICKERS, period="5d", auto_adjust=False, actions=True,
                    group_by="ticker", progress=False, threads=False)
res.check("batch yf.download works", isinstance(batch, pd.DataFrame) and not batch.empty,
          f"shape {batch.shape}")

res.finish()
