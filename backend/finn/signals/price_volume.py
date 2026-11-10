"""EOD price/volume signals (PRODUCT §6), all arithmetic in code.

- Move: adjusted close-to-close (Yahoo `adj_close`: split/bonus- and dividend-adjusted).
- Ex-dates come from NSE corporate actions. Yahoo usually restates history on the ex-date, so the mechanical
  drop never shows; if it hasn't yet (the day's return sits closer to the mechanical factor than to zero),
  we divide the factor out and test only the residual, and label the day either way.
- Volume ratio: today ÷ mean of the previous 20 sessions. z-score: today's return ÷ σ of the previous 60.
- Sector-relative: stock move minus its Nifty sector index move (Yahoo index series).
- Explanations, first that fits: filing → bulk/block deal → sector/index move → "No disclosure explains this".
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from finn.calendar import IST
from finn.models import AlertSettings

VOL_WINDOW, Z_WINDOW = 20, 60
Z_MIN = 2.0  # volatility-aware: a move must also be ≥ 2σ for this stock
MECH_MIN = 0.02  # actions moving the price < 2 % mechanically need no correction (dividends via adj_close)
EXPLAIN_SHARE = 0.5  # a sector/index move explains the stock's move if same direction and ≥ half its size
NIFTY = "^NSEI"

# Nifty sector indices on Yahoo (checked 10 Nov 2026: full daily history). Thin series are not used.
INDUSTRY_INDEX = [
    (("bank",), "^NSEBANK"),
    (("finance", "financial", "nbfc", "insurance"), "NIFTY_FIN_SERVICE.NS"),
    (("software", "computers", "it services"), "^CNXIT"),
    (("pharma", "healthcare", "hospital"), "^CNXPHARMA"),
    (("automobile", "auto ancillar", "tyres"), "^CNXAUTO"),
    (("steel", "metal", "mining", "aluminium", "copper", "zinc"), "^CNXMETAL"),
    (("power", "refiner", "oil", "gas", "petroleum"), "^CNXENERGY"),
    (("cigarette", "food", "fmcg", "personal care", "beverage", "tea"), "^CNXFMCG"),
    (("cement", "construction", "infrastructure", "telecom"), "^CNXINFRA"),
    (("realty", "real estate"), "^CNXREALTY"),
    (("retail", "jewellery", "consumer", "textile", "apparel"), "^CNXCONSUM"),
]
# NSE gives no industry for these demo/test names; mapped by hand (labelled in the card).
SYMBOL_INDEX = {"HAL": "^CNXPSE", "COCHINSHIP": "^CNXPSE", "ALKEM": "^CNXPHARMA", "DIXON": "^CNXCONSUM",
                "KALYANKJIL": "^CNXCONSUM", "TRENT": "^CNXCONSUM"}  # fmt: skip
INDEX_NAME = {"^NSEI": "Nifty 50", "^NSEBANK": "Nifty Bank", "NIFTY_FIN_SERVICE.NS": "Nifty Financial Services",
              "^CNXIT": "Nifty IT", "^CNXPHARMA": "Nifty Pharma", "^CNXAUTO": "Nifty Auto",
              "^CNXMETAL": "Nifty Metal", "^CNXENERGY": "Nifty Energy", "^CNXFMCG": "Nifty FMCG",
              "^CNXINFRA": "Nifty Infrastructure", "^CNXREALTY": "Nifty Realty", "^CNXCONSUM": "Nifty Consumption",
              "^CNXPSE": "Nifty PSE"}  # fmt: skip
INDEX_TICKERS = sorted(INDEX_NAME)


def sector_index(symbol: str, industry: str | None) -> str:
    if symbol in SYMBOL_INDEX:
        return SYMBOL_INDEX[symbol]
    ind = (industry or "").lower()
    for words, idx in INDUSTRY_INDEX:
        if any(w in ind for w in words):
            return idx
    return NIFTY


@dataclass
class Bar:
    date: date
    close: float
    adj_close: float
    volume: float | None


@dataclass
class Action:
    ex_date: date
    kind: str
    subject: str
    ratio_new: float | None = None
    ratio_held: float | None = None
    amount_per_share: float | None = None


@dataclass
class Signal:
    symbol: str
    date: date
    move_pct: float  # adjusted, mechanical part removed
    raw_move_pct: float
    mechanical_pct: float | None
    z: float | None
    volume_ratio: float | None
    sector_index: str
    sector_move_pct: float | None
    index_move_pct: float | None
    day_label: str | None
    notes: list[str] = field(default_factory=list)

    @property
    def relative_move_pct(self) -> float | None:
        return None if self.sector_move_pct is None else self.move_pct - self.sector_move_pct


def mechanical_factor(a: Action, prev_close: float) -> float | None:
    """Price multiplier an action causes on its ex-date (bonus 1:1 → 0.5; split 2:1 → 0.5; ₹10 dividend on
    ₹500 → 0.98). None when unknown."""
    if a.kind == "bonus" and a.ratio_new and a.ratio_held:
        return a.ratio_held / (a.ratio_held + a.ratio_new)
    if a.kind == "split" and a.ratio_new:
        return 1 / a.ratio_new
    if a.kind == "dividend" and a.amount_per_share and prev_close > 0:
        return (prev_close - a.amount_per_share) / prev_close
    return None


def day_label(actions: list[Action]) -> str | None:
    labels = []
    for a in actions:
        if a.kind == "dividend":
            labels.append(f"Ex-dividend today (₹{a.amount_per_share:g}/share)" if a.amount_per_share
                          else "Ex-dividend today")  # fmt: skip
        elif a.kind == "bonus" and a.ratio_new and a.ratio_held:
            labels.append(f"Bonus {a.ratio_new:g}:{a.ratio_held:g} ex-date today")
        elif a.kind == "split":
            labels.append("Split ex-date today")
        else:
            labels.append(f"Ex-date today: {a.subject[:60]}")
    return " · ".join(labels) or None


def _ret(bars: list[Bar], i: int, adj: bool = True) -> float:
    a, b = (bars[i].adj_close, bars[i - 1].adj_close) if adj else (bars[i].close, bars[i - 1].close)
    return a / b - 1


def _index_move(index_bars: list[Bar] | None, d: date) -> float | None:
    if not index_bars:
        return None
    for i, b in enumerate(index_bars):
        if b.date == d and i > 0:
            return _ret(index_bars, i, adj=False) * 100
    return None


def compute(
    symbol: str,
    bars: list[Bar],
    day: date,
    actions: list[Action],
    sector: str,
    sector_bars: list[Bar] | None,
    nifty_bars: list[Bar] | None,
) -> Signal | None:
    """Signal for `day`, or None without the day's bar or a previous one."""
    bars = sorted(bars, key=lambda b: b.date)
    idx = next((i for i, b in enumerate(bars) if b.date == day), None)
    if idx is None or idx == 0:
        return None
    r = _ret(bars, idx)
    raw = r
    today_actions = [a for a in actions if a.ex_date == day]
    mech = None
    notes: list[str] = []
    for a in today_actions:
        f = mechanical_factor(a, bars[idx - 1].close)
        if f is None or abs(f - 1) < MECH_MIN:
            continue
        # Not yet restated by Yahoo if the observed ratio sits nearer the mechanical factor than to 1.
        if abs((1 + r) - f) < abs((1 + r) - 1):
            mech = (f - 1) * 100
            r = (1 + r) / f - 1
            notes.append(f"Removed mechanical {mech:+.1f}% ({a.subject[:40]}): price history not yet restated")
    rets = [_ret(bars, j) for j in range(max(1, idx - Z_WINDOW), idx)]
    z = None
    if len(rets) >= 20:
        mu = sum(rets) / len(rets)
        sd = math.sqrt(sum((x - mu) ** 2 for x in rets) / (len(rets) - 1))
        z = r / sd if sd > 0 else None
    vols = [b.volume for b in bars[max(0, idx - VOL_WINDOW) : idx] if b.volume]
    vr = None
    if len(vols) >= 10 and bars[idx].volume:
        vr = bars[idx].volume / (sum(vols) / len(vols))
        if mech is not None:  # unrestated volume history is on the old share count
            vr *= 1 + mech / 100
    return Signal(
        symbol=symbol, date=day, move_pct=r * 100, raw_move_pct=raw * 100, mechanical_pct=mech, z=z,
        volume_ratio=vr, sector_index=sector, sector_move_pct=_index_move(sector_bars, day),
        index_move_pct=_index_move(nifty_bars, day), day_label=day_label(today_actions), notes=notes,
    )  # fmt: skip


def triggers(sig: Signal, settings: AlertSettings) -> list[str]:
    """Which alert rules fire for this user's settings: 'price' and/or 'volume'."""
    out = []
    thr = settings.per_stock_pct.get(sig.symbol, settings.price_move_pct)
    test = sig.relative_move_pct if settings.sector_relative and sig.relative_move_pct is not None else sig.move_pct
    if abs(test) >= thr and (not settings.volatility_aware or sig.z is None or abs(sig.z) >= Z_MIN):
        out.append("price")
    if sig.volume_ratio is not None and sig.volume_ratio >= settings.volume_multiple:
        out.append("volume")
    return out


# --- explanations -----------------------------------------------------------------------------------------

CLOSE = time(15, 30)


def session_window(day: date, prev_day: date) -> tuple[datetime, datetime]:
    """Filings that can explain `day`'s move: after the previous session's close up to this session's close."""
    return datetime.combine(prev_day, CLOSE, IST), datetime.combine(day, CLOSE, IST)


@dataclass
class Explanation:
    kind: str  # filing | bulk_block_deal | sector_move | index_move | none
    text: str
    url: str | None = None
    ref: dict | None = None


STAGE_RANK = {"outcome": 0, "other": 1, "clarification": 1, "presentation": 2, "call": 3, "transcript": 3,
              "intimation": 4, "newspaper_ad": 6}  # fmt: skip
SUBJECT_BOILERPLATE = r"^.*?\b(?:has )?(?:informed|submitted to) the Exchange(?: about| regarding|,)?\s*"


def explain(
    sig: Signal,
    filings: list[dict],
    deals: list[dict],
    prev_day: date,
    labels: dict[str, str] | None = None,
) -> list[Explanation]:
    """filings: material filings for the symbol ({filed_at, category, subject, attachment_url});
    deals: that day's bulk/block deals ({kind, client, side, value_cr})."""
    out: list[Explanation] = []
    lo, hi = session_window(sig.date, prev_day)
    inside = [f for f in filings if lo < f["filed_at"] <= hi]
    # The most substantive filing explains a move: an outcome beats its deck, call, transcript or newspaper ad.
    for f in sorted(inside, key=lambda f: (STAGE_RANK.get(f.get("stage") or "outcome", 5), -f["filed_at"].timestamp())):
        lab = (labels or {}).get(f["category"], f["category"].replace("_", " ").capitalize())
        when = f["filed_at"].astimezone(IST).strftime("%d %b %H:%M")
        subj = re.sub(SUBJECT_BOILERPLATE, "", f["subject"], flags=re.I).strip(" .'\"") or f["subject"]
        out.append(Explanation("filing", f"{lab} filed {when} IST: {subj[:90]}", f.get("attachment_url"), f))
        break
    if deals:
        d = max(deals, key=lambda d: d["value_cr"])
        verb = "bought" if d["side"].upper().startswith("B") else "sold"
        out.append(Explanation("bulk_block_deal", f"{d['kind'].capitalize()} deal: {d['client'][:50]} {verb} "
                               f"₹{d['value_cr']:,.1f} Cr", None, d))  # fmt: skip
    for kind, move, name in (("sector_move", sig.sector_move_pct, INDEX_NAME.get(sig.sector_index, sig.sector_index)),
                             ("index_move", sig.index_move_pct, "Nifty 50")):  # fmt: skip
        if kind == "sector_move" and sig.sector_index == NIFTY:
            continue
        if move is not None and move * sig.move_pct > 0 and abs(move) >= EXPLAIN_SHARE * abs(sig.move_pct):
            out.append(Explanation(kind, f"{name} moved {move:+.1f}% the same day"))
            break
    if not out:
        out.append(Explanation("none", "⚠️ No disclosure explains this move"))
    return out


def previous_session(bars: list[Bar], day: date) -> date | None:
    ds = sorted(b.date for b in bars if b.date < day)
    return ds[-1] if ds else None


def at_close(day: date) -> datetime:
    return datetime.combine(day, CLOSE, IST)


ONE_DAY = timedelta(days=1)
