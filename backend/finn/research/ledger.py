"""Step 5 — the Promise Ledger, decided in code (rule 1: the LLM reads, code calculates).

Input: per-call facts from MAP (guidance + actuals, quotes already verified). Output: promise threads with verdicts.

Rules (documented in DECISIONS.md, tested in tests/test_ledger.py):
- Thread = same metric_key, measure, segment, unit family, currency and scope, and the same resolved period.
  'unspecified' currency/scope joins the single specified group; with none specified it stays unspecified.
- Delivered figure: screener for a whitelist of rows (metrics.SCREENER_SCORABLE) when currency is INR/unspecified
  and scope matches the screener page; otherwise a management-reported actual for the same metric, measure,
  period and basis, with its quote. Never across currencies (INR vs USD vs constant currency) or scopes.
- Scored against the last target given before the period ended (product owner, 11 Nov 2026).
- Revisions within a thread, judged by the metric's direction: unfavourable change or a later date = ↘ goalposts
  moved (that is the verdict); favourable = ↗ raised; same midpoint, tighter = narrowed; neutral metric = revised.
- Not yet due: period not over, or results not out yet. Can't score: no date, a benchmark-relative target, or no
  delivered figure in sources. Neither counts toward credibility.
- Quietly dropped: no delivered figure, ≥ 2 readable later calls, and a lenient text search finds none of the
  promise's words in any of them.
- Credibility = kept ÷ (kept + missed + goalposts moved + quietly dropped); shown when n ≥ 5.
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime

from finn.models import Citation, Claim, Figure, Period
from finn.models.research import Credibility, LedgerCounts, Promise, PromiseBasis, PromiseStatement, TrendHalf
from finn.numbers import pct_change
from finn.research import metrics
from finn.research.checker import norm
from finn.research.periods import resolve, results_due

MIN_N = 5
TREND_CALLS = 4
TREND_MIN_HALF = 3
TREND_DELTA_PP = 15.0

# Tolerances: a point target allows normal rounding of a spoken number; range/threshold bounds allow only the
# rounding of the reported figure. Per unit family: (point, bound); 'rel' families are fractions of the target.
TOL_ABS = {"PCT": (0.5, 0.1), "DAYS": (2.0, 0.5), "X": (0.05, 0.01)}
TOL_REL = (0.025, 0.005)


# --- inputs ----------------------------------------------------------------------------------------------------


@dataclass
class Call:
    doc_id: str
    url: str
    label: str  # 'Q2 FY27 call'
    made_on: date
    pages: list[str]
    facts: dict
    retrieved_at: datetime

    kind: str = "transcript"  # transcript | deck (a deck only supplies delivered figures — never promises)

    def cite(self, page: int, quote: str) -> Citation:
        if self.kind == "deck":
            return Citation(source_type="investor_presentation", url=self.url, title=self.label, page=page,
                            quote=quote, retrieved_at=self.retrieved_at)  # fmt: skip
        return Citation(source_type="concall_transcript", url=self.url, title=f"{self.label} transcript", page=page,
                        quote=quote, retrieved_at=self.retrieved_at)  # fmt: skip


@dataclass
class Stmt:
    call: Call
    item: dict
    period: Period | None
    unit: str | None  # normalised unit family: PCT | INR_CR | USD_MN | X | DAYS | <other text> | None
    low: float | None
    high: float | None
    currency: str
    scope: str
    segment: str
    factor: float = 1.0  # printed unit → normalised unit (bps → pp: 0.01)

    @property
    def made_on(self) -> date:
        return self.call.made_on

    def mid(self) -> float | None:
        vals = [v for v in (self.low, self.high) if v is not None]
        return sum(vals) / len(vals) if vals else None

    def precision(self) -> float:
        """Half a unit of the target's last printed digit, in normalised units ('1.85%' → 0.005 pp; '40 bps' →
        0.005 pp; '20%' → 0.5 pp): a bound can't be met by more than the rounding of what management said."""
        decs = 0
        for v in (self.item.get("target_low"), self.item.get("target_high")):
            if v is not None:
                txt = f"{float(v):.6f}".rstrip("0").rstrip(".")
                decs = max(decs, len(txt.split(".")[1]) if "." in txt else 0)
        return 0.5 * 10**-decs * self.factor

    def width(self) -> float:
        return (self.high - self.low) if self.low is not None and self.high is not None else 0.0


@dataclass
class Thread:
    key: tuple
    stmts: list[Stmt] = field(default_factory=list)


# --- unit normalisation (code, never the model) -----------------------------------------------------------------

_MONEY = [(r"\blakh|\blac", 0.01), (r"\bcrore|\bcr\b", 1.0), (r"\bbillion|\bbn\b", 100.0),
          (r"\bmillion|\bmn\b|\bmln\b", 0.1), (r"\btrillion|\btn\b", 100000.0)]  # fmt: skip
_USD = [(r"\bbillion|\bbn\b", 1000.0), (r"\bmillion|\bmn\b|\bmln\b", 1.0)]


# Metrics whose 'million'/'crore' is money. For anything else (customers, units, tonnes) a 'million' is a count.
MONEY_KEYS = {"revenue", "ebitda", "pat", "eps", "capex", "order_book", "order_inflow", "deal_wins", "debt", "net_debt",
              "cost_savings", "dividend_payout", "other"}  # fmt: skip
_COUNT = [(r"\bbillion|\bbn\b", 1e9), (r"\bmillion|\bmn\b|\bmln\b", 1e6), (r"\bcrore|\bcr\b", 1e7),
          (r"\blakh|\blac", 1e5), (r"\bthousand|\bk\b", 1e3)]  # fmt: skip


def normalise_unit(unit_text: str | None, currency: str, metric_key: str = "other") -> tuple[str | None, float]:
    """(unit family, multiplier to that family). bps → percentage points; INR money → ₹ crore; USD → USD million;
    a count metric's 'million'/'lakh' → COUNT (never money)."""
    u = (unit_text or "").strip().lower()
    if not u:
        return None, 1.0
    money = currency in ("INR", "USD") or "₹" in u or "rs" in u.split() or "inr" in u or (
        currency != "not_money" and metric_key in MONEY_KEYS)  # fmt: skip
    if "bps" in u or "basis point" in u:
        return "PCT", 0.01
    if "%" in u or "percent" in u or "per cent" in u:
        return "PCT", 1.0
    if not money and not re.search(r"usd|\$|dollar", u):
        for rx, f in _COUNT:
            if re.search(rx, u):
                return "COUNT", f
    if currency == "USD" or "usd" in u or "$" in u or "dollar" in u:
        for rx, f in _USD:
            if re.search(rx, u):
                return "USD_MN", f
        return None, 1.0
    for rx, f in _MONEY:
        if re.search(rx, u):
            return "INR_CR", f
    if re.fullmatch(r"x|times|-?fold", u):
        return "X", 1.0
    if "day" in u:
        return "DAYS", 1.0
    return u.upper()[:20], 1.0


def _stmt(call: Call, it: dict, ye_month: int) -> Stmt:
    unit, f = normalise_unit(it.get("unit_text"), it.get("currency", "unspecified"), it.get("metric_key", "other"))
    lo, hi = it.get("target_low"), it.get("target_high")
    period = resolve(it.get("period_type", "unspecified"), it.get("fy"), it.get("quarter"), it.get("half"),
                     it.get("years"), call.made_on, ye_month)  # fmt: skip
    seg = norm(it.get("segment") or "") if it.get("scope") == "segment" else ""
    return Stmt(call, it, period, unit, lo * f if lo is not None else None, hi * f if hi is not None else None,
                it.get("currency", "unspecified"), it.get("scope", "unspecified"), seg, f)  # fmt: skip


# --- grouping -----------------------------------------------------------------------------------------------------


def _family_key(s: Stmt) -> tuple:
    key = s.item["metric_key"]
    other = norm(s.item.get("metric", "")) if key == "other" else ""
    return (key, other, s.item["measure"], s.segment, s.unit)


def _qual_words(s: Stmt) -> set[str]:
    text = norm(f"{s.item.get('metric', '')} {s.item.get('statement', '')}")
    return {w for w in re.findall(r"[a-z]{4,}", text)}


def _jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


# Board and personnel housekeeping isn't a business promise (an interim chairman's tenure, an AGM date). Only
# business, financial and operational commitments enter the ledger.
_GOVERNANCE = re.compile(
    r"\b(chairman|chairperson|director|board|independent|appoint\w*|tenure|interim|ceo|cfo|md|"
    r"managing director|company secretary|agm|egm|record date|book closure|auditor)\b",
    re.I,
)


# Accounting schedules aren't commitments either: an ESOP / share-based-payment charge forecast is arithmetic on
# grants already made, and calling it "quietly dropped" would be a false accusation.
_ACCOUNTING = re.compile(r"\b(esops?|esos|share[- ]based|stock options?|employee stock|sbc)\b", re.I)


def is_business_promise(it: dict) -> bool:
    if _ACCOUNTING.search(it.get("metric", "")):
        return False
    if it.get("metric_key") not in ("other", "headcount"):
        return True
    return not _GOVERNANCE.search(f"{it.get('metric', '')} {it.get('statement', '')}")


def group(stmts: list[Stmt]) -> list[Thread]:
    """Numeric statements → threads by family + period, with 'unspecified' basis merged into a single specified
    one. Qualitative statements stay one per thread (the strong model links paraphrases across calls)."""
    threads: list[Thread] = []
    fams: dict[tuple, list[Stmt]] = defaultdict(list)
    for s in stmts:
        if s.item["kind"] == "qualitative" or s.item["measure"] == "qualitative":
            # A restatement in a later call (same metric, mostly the same words) joins the earlier thread.
            words = _qual_words(s)
            home = next((t for t in threads if t.key[0] == "qual" and t.key[1] == s.item["metric_key"]
                         and all(o.call.doc_id != s.call.doc_id for o in t.stmts)
                         and _jaccard(words, _qual_words(t.stmts[0])) >= 0.5), None)  # fmt: skip
            if home is not None:
                home.stmts.append(s)
            else:
                threads.append(Thread(("qual", s.item["metric_key"], s.call.doc_id, s.item["quote"][:40]), [s]))
        else:
            fams[(*_family_key(s), s.period.end if s.period else None)].append(s)
    for fk, group_ in fams.items():
        # merge targets: fully specified bases; a partly/un-specified statement joins the single compatible one
        full = {(s.currency, s.scope) for s in group_ if "unspecified" not in (s.currency, s.scope)}
        buckets: dict[tuple, list[Stmt]] = defaultdict(list)
        for s in group_:
            b = (s.currency, s.scope)
            if "unspecified" in b:
                match = [x for x in full if b[0] in ("unspecified", x[0]) and b[1] in ("unspecified", x[1])]
                if len(match) == 1:
                    b = match[0]
            buckets[b].append(s)
        for b, ss in buckets.items():
            # One call can give two different numbers for the same metric (a 180 bps headwind, 80–100 bps of it
            # offset): those are separate statements, not a revision — a thread holds one statement per call.
            lanes: list[list[Stmt]] = []
            for st in sorted(ss, key=lambda x: x.made_on):
                lane = next((ln for ln in lanes if all(o.call.doc_id != st.call.doc_id for o in ln)), None)
                if lane is None:
                    lanes.append([st])
                else:
                    lane.append(st)
            for i, ln in enumerate(lanes):
                threads.append(Thread((*fk, *b) if i == 0 else (*fk, *b, i), ln))
    return threads


# --- delivered figures --------------------------------------------------------------------------------------------


def _screener_delivered(t: Thread, disc) -> Figure | None:
    from finn.research.compute import sourced

    s = t.stmts[-1]
    spec = metrics.SCREENER_SCORABLE.get((s.item["metric_key"], s.item["measure"]))
    if not spec or disc is None or disc.status != "ok" or s.period is None:
        return None
    if s.currency not in ("INR", "unspecified") or s.segment:
        return None
    if s.scope not in ("unspecified", disc.basis) or s.unit != spec["unit"]:
        return None
    if spec.get("needs_word") and spec["needs_word"] not in norm(s.item["metric"] + " " + s.item["quote"]):
        return None
    table = disc.table(spec["section"])
    if s.period.kind == "quarter":
        table = disc.table("quarters")
    elif spec.get("quarterly_only") or s.period.kind != "year":
        return None
    if table is None:
        return None
    row = next((r for r in spec["rows"] if r in table.rows), None)
    cols = [c for c in table.columns if c.end == s.period.end and c.kind in ("year", "quarter")]
    if row is None or not cols:
        return None
    cur = sourced(table, row, cols[0], s.item["metric"], "PCT" if "%" in row else "INR_CR")
    if cur is None:
        return None
    if not spec.get("yoy"):
        return cur
    prev_end = date(s.period.end.year - 1, s.period.end.month, s.period.end.day)
    pcols = [c for c in table.columns if c.end == prev_end and c.kind == cols[0].kind]
    prev = sourced(table, row, pcols[0], s.item["metric"]) if pcols else None
    if prev is None or prev.value is None:
        return None
    g = pct_change(cur.value, prev.value)  # type: ignore[arg-type]
    if g is None:
        return None
    from finn.research.compute import computed

    return computed(f"{s.item['metric']} (YoY)", g, "PCT", [prev, cur], f"{row} {cols[0].label} ÷ {pcols[0].label} − 1",
                    s.period)  # fmt: skip


def _actual_delivered(t: Thread, calls: list[Call], ye_month: int, pid: str | None = None):
    s = t.stmts[-1]
    if s.period is None:
        return None, None
    for call in sorted(calls, key=lambda c: c.made_on):
        if call.made_on < s.period.end:
            continue
        for a in call.facts.get("actuals", []):
            if a.get("for_promise") not in (None, pid):
                continue  # a deck figure was requested for one specific promise
            if a["metric_key"] != s.item["metric_key"] or a["measure"] != s.item["measure"]:
                continue
            if not _same_metric(s.item, a):
                continue
            unit, f = normalise_unit(a.get("unit_text"), a.get("currency", "unspecified"), a["metric_key"])
            if unit != s.unit:
                continue
            cur = a.get("currency", "unspecified")
            if cur != s.currency and "unspecified" not in (cur, s.currency):
                continue
            if "constant_currency" in (cur, s.currency) and cur != s.currency:
                continue  # never compare constant-currency with reported growth
            if a.get("scope") not in ("unspecified", s.scope) and s.scope != "unspecified":
                continue
            seg = norm(a.get("segment") or "") if a.get("scope") == "segment" else ""
            if seg != s.segment:
                continue
            p = resolve(a.get("period_type", "unspecified"), a.get("fy"), a.get("quarter"), a.get("half"),
                        a.get("years"), call.made_on, ye_month)  # fmt: skip
            if p is None or p.end != s.period.end or p.kind != s.period.kind:
                continue
            fig = Figure(label=a["metric"], value=a["value"] * f, unit=_unit_enum(unit), period=p,
                         basis=None if s.scope not in ("consolidated", "standalone") else s.scope, status="verified",
                         citation=call.cite(a["page"], a["quote"]), raw_unit=a.get("unit_text"),
                         raw=f"{a['value']:g} {a.get('unit_text') or ''}".strip())  # fmt: skip
            return fig, call
    return None, None


# Keys precise enough that the key alone identifies the metric; for the rest (headcount, capex, capacity, other…)
# the names must also share a word — 'fresher hiring' is not 'total headcount'.
TIGHT_KEYS = {"revenue", "revenue_growth", "ebitda", "ebitda_margin", "ebit_margin", "gross_margin", "pat",
              "pat_growth", "eps", "nim", "credit_cost", "gnpa", "nnpa", "aum_growth", "loan_growth", "deposit_growth",
              "cost_to_income", "roe", "roa", "roce", "attrition", "tax_rate", "dividend_payout"}  # fmt: skip
_STOP = {"the", "and", "for", "our", "total", "overall", "of", "in", "rate", "level", "growth", "number", "company"}


def _same_metric(g: dict, a: dict) -> bool:
    if g["metric_key"] in TIGHT_KEYS:
        return True
    gw = {w for w in re.findall(r"[a-z]{3,}", norm(g.get("metric", ""))) if w not in _STOP}
    aw = {w for w in re.findall(r"[a-z]{3,}", norm(a.get("metric", ""))) if w not in _STOP}
    return bool(gw & aw)


def _unit_enum(u: str | None) -> str:
    return {"PCT": "PCT", "INR_CR": "INR_CR", "X": "X", "DAYS": "DAYS"}.get(u or "", "COUNT")


def _fmt_count(v: float, like: str | None = None) -> str:
    """A count in the scale the target was given in ('million' target → '119.3 million')."""
    scales = ((1e9, "billion"), (1e7, "crore"), (1e6, "million"), (1e5, "lakh"))
    for div, name in scales:
        if like and name in like.lower():
            return f"{v / div:,.2f}".rstrip("0").rstrip(".") + f" {name}"
    for div, name in scales:
        if abs(v) >= div:
            return f"{v / div:,.2f}".rstrip("0").rstrip(".") + f" {name}"
    return f"{v:,.0f}"


# --- verdicts -------------------------------------------------------------------------------------------------------


_LOWER_WORDS = re.compile(
    r"\b(cost|costs|loss|losses|npa|npas|stage 3|slippage|debt|leverage|borrowing|attrition|"
    r"days|delinquen\w*|write[- ]?offs?|provisions?)\b",
    re.I,
)
_BETTER_UP = re.compile(r"\b(improv\w*|expan\w*|increas\w*|gain\w*|accretion|uplift|saving\w*|benefit)\b", re.I)
_BETTER_DOWN = re.compile(r"\b(impact|headwind|drag|pressure|compress\w*|dilution|erosion|hit)\b", re.I)


def direction_for(item: dict, stmts: list[Stmt]) -> str:
    """Which way is good, decided in code: the metric key's direction; for keys without one ('other'), the metric's
    own words (cost, loss, NPA, debt, days → lower). An unsigned change ('+40–50 bps') is read from its words —
    'improvement/expansion/saving' (more is better) vs 'impact/headwind/drag' (less is better); with neither, it
    has no direction and an off-range result can't be scored as a miss."""
    text = f"{item.get('metric', '')} {item.get('statement', '')}"
    if item.get("measure") == "change" and all((x.low or 0) >= 0 and (x.high or 0) >= 0 for x in stmts):
        if _BETTER_DOWN.search(text):
            return "lower"
        if _BETTER_UP.search(text):
            return "higher"
        return "unknown"
    d = metrics.direction(item.get("metric_key", "other"))
    lower = _LOWER_WORDS.search(item.get("metric", "")) and "saving" not in text.lower()
    if d == "neutral" and item.get("metric_key") in ("other", "debt") and lower:
        return "lower"
    return d


def _different_measure(target: Stmt, value: float) -> bool:
    """A level (money, count) more than 3× or under ⅓ of its target is almost always another measure (new customers
    vs total customers, a segment vs the company) — never scored as a beat or a miss."""
    mid = target.mid()
    if target.unit not in ("INR_CR", "USD_MN", "COUNT") or target.item["measure"] != "level" or not mid or mid <= 0:
        return False
    return not (mid / 3 <= value <= mid * 3)


def _tol(unit: str | None, target: float, point: bool) -> float:
    if unit in TOL_ABS:
        return TOL_ABS[unit][0 if point else 1]
    return abs(target) * TOL_REL[0 if point else 1]


def compare(kind: str, lo: float | None, hi: float | None, value: float, unit: str | None,
            direction: str, precision: float | None = None) -> tuple[str, str]:  # fmt: skip
    """(kept|missed, how) for a delivered value against a target. Pure function — see DECISIONS.md.
    `precision` caps the tolerance on range/threshold bounds at the rounding of the printed target."""

    def btol(unit, x):
        t = _tol(unit, x, False)
        return min(t, precision) if precision is not None else t

    if kind == "at_least" and lo is not None:
        return ("kept", "at or above") if value >= lo - btol(unit, lo) else ("missed", "below")
    if kind == "at_most" and hi is not None:
        return ("kept", "at or below") if value <= hi + btol(unit, hi) else ("missed", "above")
    point = kind == "point" or lo is None or hi is None or lo == hi
    a = lo if lo is not None else hi
    b = hi if hi is not None else lo
    if a is None or b is None:
        return "missed", "no target"
    a, b = min(a, b), max(a, b)
    ta, tb = (_tol(unit, a, True), _tol(unit, b, True)) if point else (btol(unit, a), btol(unit, b))
    if a - ta <= value <= b + tb:
        return "kept", "within"
    above = value > b
    if direction == "higher" and above or direction == "lower" and not above:
        return "kept", "beat"
    return "missed", "above" if above else "below"


def revision(stmts: list[Stmt], direction: str) -> tuple[str, Stmt | None]:
    """Most significant change across successive targets (lowered > revised > raised > narrowed)."""
    rank = {"none": 0, "narrowed": 1, "raised": 2, "revised": 3, "lowered": 4}
    best, by = "none", None
    for prev, cur in zip(stmts, stmts[1:], strict=False):
        m0, m1 = prev.mid(), cur.mid()
        if m0 is None or m1 is None:
            continue
        eps = _tol(cur.unit, m0, False)
        if abs(m1 - m0) <= eps:
            kind = "narrowed" if cur.width() < prev.width() - eps else "none"
        elif direction in ("neutral", "unknown"):
            kind = "revised"
        else:
            up = m1 > m0
            kind = "raised" if up == (direction == "higher") else "lowered"
        if rank[kind] >= rank[best] and kind != "none":  # the latest change of the most significant kind
            best, by = kind, cur
    return best, by


def _target_str(s: Stmt) -> str:
    raw_lo, raw_hi, u = s.item.get("target_low"), s.item.get("target_high"), s.item.get("unit_text") or ""
    sep = "" if u.strip() in ("%", "x") else " "
    if s.item["kind"] == "at_least" and raw_lo is not None:
        return f"≥ {raw_lo:g}{sep}{u}".strip()
    if s.item["kind"] == "at_most" and raw_hi is not None:
        return f"≤ {raw_hi:g}{sep}{u}".strip()
    if raw_lo is not None and raw_hi is not None and raw_lo != raw_hi:
        return f"{raw_lo:g}–{raw_hi:g}{sep}{u}".strip()
    v = raw_lo if raw_lo is not None else raw_hi
    return f"{v:g}{sep}{u}".strip() if v is not None else ""


def _ps(s: Stmt) -> PromiseStatement:
    return PromiseStatement(
        doc_id=s.call.doc_id, call_label=s.call.label, made_on=s.made_on, kind=s.item["kind"], target_low=s.low,
        target_high=s.high, unit=s.unit, raw_target=_target_str(s) or None, period_text=s.item.get("period_text"),
        quote=s.call.cite(s.item["page"], s.item["quote"]), speaker=s.item.get("speaker"),
    )  # fmt: skip


def _mentions(terms: list[str], pages: list[str]) -> bool:
    text = " ".join(norm(p) for p in pages)
    for t in terms:
        t = norm(t)
        if len(t) >= 3 and re.search(rf"(?<![a-z0-9]){re.escape(t)}(?![a-z0-9])", text):
            return True
    return False


@dataclass
class Ledger:
    promises: list[Promise]
    credibility: Credibility
    counts: LedgerCounts
    settled: dict[str, date]
    # promise id → its period, for promises that are "can't score" only because no delivered figure was found in
    # the calls (the deck lookup reads the deck that closes that period)
    unscored: dict[str, Period] = field(default_factory=dict)


def build_ledger(symbol: str, calls: list[Call], disc, today: date, ye_month: int = 3) -> Ledger:
    calls = sorted(calls, key=lambda c: c.made_on)
    transcripts = [c for c in calls if c.kind == "transcript"]  # decks supply delivered figures only
    unscored: dict[str, Period] = {}
    stmts = [
        _stmt(c, it, ye_month) for c in transcripts for it in c.facts.get("guidance", []) if is_business_promise(it)
    ]
    threads = group(stmts)
    promises: list[Promise] = []
    settled: dict[str, date] = {}
    # 'delayed': the same target reappears for a later period, said before the earlier deadline
    by_family: dict[tuple, list[Thread]] = defaultdict(list)
    for t in threads:
        if t.key[0] != "qual":  # qualitative keys: ("qual", metric_key, doc, quote)
            by_family[t.key[:5] + t.key[6:]].append(t)
    delayed: dict[int, tuple[Thread, Stmt]] = {}
    for fam in by_family.values():
        for a in fam:
            pa = a.stmts[-1].period
            for b in fam:
                pb = b.stmts[0].period
                if a is b or pa is None or pb is None or pb.end <= pa.end:
                    continue
                first_b = b.stmts[0]
                # Only deadline-style targets ('by FY27') can slip; a level restated for the next year is normal.
                if a.stmts[-1].item.get("period_type") != "by_fy" or first_b.item.get("period_type") != "by_fy":
                    continue
                ma, mb = a.stmts[-1].mid(), first_b.mid()
                if (first_b.made_on > a.stmts[-1].made_on and first_b.made_on <= pa.end and ma is not None
                        and mb is not None and abs(ma - mb) <= _tol(first_b.unit, ma, True)):  # fmt: skip
                    delayed[id(a)] = (b, first_b)

    for t in threads:
        s0, last = t.stmts[0], t.stmts[-1]
        period = last.period
        scored = [s for s in t.stmts if period is None or s.made_on <= period.end] or [last]
        target = scored[-1]
        key = s0.item["metric_key"]
        direction = direction_for(s0.item, t.stmts)
        qual = t.key[0] == "qual"
        pid = hashlib.sha256(repr((symbol, t.key, s0.call.doc_id if qual else "")).encode()).hexdigest()[:16]
        rev, rev_by = ("none", None) if qual else revision(t.stmts, direction)
        delivered, dsrc, dcall = None, None, None
        if not qual:
            delivered = _screener_delivered(t, disc)
            dsrc = "screener" if delivered else None
            if delivered is None:
                delivered, dcall = _actual_delivered(t, calls, ye_month, pid)
                dsrc = "management_reported" if delivered else None
        promise_cite = target.call.cite(target.item["page"], target.item["quote"])
        verdict, why, cites = "cant_score", "", [promise_cite]
        relative = target.unit == "X" and target.item["measure"] == "growth"
        if id(t) in delayed:
            later, ls = delayed[id(t)]
            rev, verdict = "delayed", "goalposts_moved"
            why = f"Same target moved to {later.stmts[0].period.label} in the {ls.call.label}"  # type: ignore[union-attr]
            cites.append(ls.call.cite(ls.item["page"], ls.item["quote"]))
            settled[pid] = ls.made_on
        elif rev == "lowered" and rev_by is not None:
            verdict = "goalposts_moved"
            why = (f"Target cut to {_target_str(rev_by)} in the {rev_by.call.label}; first given as "
                   f"{_target_str(s0)} in the {s0.call.label}")  # fmt: skip
            first = s0.call.cite(s0.item["page"], s0.item["quote"])
            cites = [first, rev_by.call.cite(rev_by.item["page"], rev_by.item["quote"])]
            settled[pid] = rev_by.made_on
        elif qual:
            verdict = "not_yet_due" if period and today < results_due(period) else "cant_score"
            why = ("Due " + period.label) if verdict == "not_yet_due" and period else \
                "Qualitative promise — judged against later calls in the full build"  # fmt: skip
        elif period is None:
            why = "No clear period given, so it can't be scored"
        elif relative:
            why = "Target is relative to an outside benchmark (e.g. industry growth) — not scored in code"
        elif today <= period.end:
            verdict, why = "not_yet_due", f"Due {period.label} (ends {period.end:%d %b %Y})"
        elif delivered is not None and delivered.value is not None and _different_measure(target, delivered.value):
            why = (f"A figure was reported ({_fmt(delivered.value, target.unit, target.item.get('unit_text'))}) but it "
                   f"is far from the target's scale, so it is probably a different measure — not scored")  # fmt: skip
            delivered, dsrc = None, None
        elif delivered is not None and delivered.value is not None:
            kind = target.item["kind"]
            verdict, how = compare(
                kind, target.low, target.high, delivered.value, target.unit, direction, target.precision()
            )
            if direction == "unknown" and how in ("above", "below"):
                verdict, how = "cant_score", f"{how} the range, but the call doesn't say whether more is better"
            src = "screener" if dsrc == "screener" else (dcall.label if dcall else "a later call")
            got = (
                delivered.raw
                if delivered.raw and dsrc != "screener"
                else _fmt(delivered.value, target.unit, target.item.get("unit_text"))
            )
            why = f"Delivered {got} vs target {_target_str(target)} ({how}; {src})"
            if delivered.citation:
                cites.append(delivered.citation)
            settled[pid] = dcall.made_on if dcall else results_due(period)
        elif today < results_due(period):
            verdict, why = "not_yet_due", f"Awaiting {period.label} results"
        else:
            why = f"No delivered figure for {period.label} found in the sources read"
            unscored[pid] = period
        # quietly dropped: only unscored, with ≥ 2 readable later calls that never mention it
        dropped_note = None
        if verdict in ("cant_score", "not_yet_due") and delivered is None and not relative:
            later = [c for c in transcripts if c.made_on > last.made_on]
            if len(later) >= 2:
                terms = list(last.item.get("search_terms") or []) + list(metrics.synonyms(key))
                terms += [last.item.get("metric", "")]
                if not any(_mentions(terms, c.pages) for c in later):
                    verdict = "quietly_dropped"
                    dropped_note = f"Not mentioned in the {len(later)} calls since the {last.call.label}"
                    why = dropped_note
                    settled[pid] = later[-1].made_on
        period_txt = period.label if period else (last.item.get("period_text") or "no date")
        statement = (f"{s0.item['metric']} {_target_str(target)} ({period_txt})" if not qual
                     else f"{last.item.get('statement') or s0.item['metric']} ({period_txt})")  # fmt: skip
        promises.append(Promise(
            id=pid, symbol=symbol, metric=s0.item["metric"], metric_key=key,
            measure="qualitative" if qual else s0.item["measure"], kind=target.item["kind"],
            basis=PromiseBasis(currency=_cur(t.key[6] if not qual else last.currency),
                               scope=t.key[7] if not qual else last.scope, segment=last.item.get("segment") or None),
            period=period, statement=" ".join(statement.split()), statements=[_ps(s) for s in t.stmts],
            scored_target=_ps(target), revision=rev, verdict=verdict, verdict_by="code",
            verdict_reason=Claim(text=why, status="verified", citations=cites), delivered=delivered,
            delivered_source=dsrc, dropped_note=dropped_note,
        ))  # fmt: skip
    promises.sort(key=_order)
    return Ledger(promises, credibility(promises, settled, transcripts), count(promises), settled, unscored)


def next_test(promises: list[Promise], today: date) -> tuple[Period | None, date | None, int]:
    """The earliest period at which a not-yet-due promise is tested, when its results are due, and how many fall due
    then — for the ledger header ("next test: FY27 results")."""
    due = [p.period for p in promises if p.verdict == "not_yet_due" and p.period is not None]
    if not due:
        return None, None, 0
    first = min(due, key=lambda x: x.end)
    return first, results_due(first), sum(1 for x in due if x.end == first.end)


def count(promises: list[Promise]) -> LedgerCounts:
    counts = LedgerCounts()
    for p in promises:
        setattr(counts, p.verdict, getattr(counts, p.verdict) + 1)
        counts.raised += p.revision == "raised"
    return counts


def _cur(c: str) -> str:
    return c if c in ("INR", "USD", "constant_currency", "unspecified", "not_money") else "unspecified"


def _fmt(v: float, unit: str | None, like: str | None = None) -> str:
    if unit == "PCT":
        return f"{v:.1f}%"
    if unit == "INR_CR":
        from finn.format import money_cr

        return money_cr(v)
    num = f"{v:,.2f}".rstrip("0").rstrip(".")
    if unit == "X":
        return f"{num}x"
    if unit == "COUNT":
        return _fmt_count(v, like)
    return f"{num} {unit.lower()}" if unit else num


_ORDER = {"goalposts_moved": 0, "quietly_dropped": 1, "missed": 2, "kept": 3, "not_yet_due": 4, "cant_score": 5}


def _order(p: Promise):
    return (_ORDER[p.verdict], -(p.statements[-1].made_on.toordinal()))


def credibility(promises: list[Promise], settled: dict[str, date], calls: list[Call]) -> Credibility:
    scored = [p for p in promises if p.verdict in ("kept", "missed", "goalposts_moved", "quietly_dropped")]
    kept = sum(p.verdict == "kept" for p in scored)
    n = len(scored)
    formula = "kept ÷ (kept + missed + goalposts moved + quietly dropped); not-yet-due and can't-score excluded"
    recent_cut = sorted(c.made_on for c in calls)[-TREND_CALLS] if len(calls) >= TREND_CALLS else None
    trend = recent = earlier = None
    if recent_cut:
        r = [p for p in scored if settled.get(p.id, date.min) >= recent_cut]
        e = [p for p in scored if settled.get(p.id, date.min) < recent_cut]
        recent = TrendHalf(kept=sum(p.verdict == "kept" for p in r), n=len(r))
        earlier = TrendHalf(kept=sum(p.verdict == "kept" for p in e), n=len(e))
        if recent.n >= TREND_MIN_HALF and earlier.n >= TREND_MIN_HALF:
            delta = 100 * (recent.kept / recent.n - earlier.kept / earlier.n)
            trend = "up" if delta >= TREND_DELTA_PP else "down" if delta <= -TREND_DELTA_PP else "flat"
    return Credibility(
        shown=n >= MIN_N, score_pct=round(100 * kept / n, 1) if n else None, kept=kept, n=n,
        numeric_n=sum(p.verdict_by == "code" for p in scored),
        qualitative_n=sum(p.verdict_by == "model" for p in scored),
        min_n=MIN_N, trend=trend, recent=recent, earlier=earlier, formula=formula,
    )  # fmt: skip
