"""Code-built sections from extracted facts: what analysts keep asking, suggested drivers, segments, Ask chips.

Counting and ranking happen here; the strong model (REDUCE) may later reword pressure points, but which topics
recur, and how often, is decided in code from cited questions.
"""

from __future__ import annotations

import re
from collections import defaultdict

from finn.models import Claim, Driver, Figure
from finn.models.research import PressurePoint, Promise
from finn.research import metrics
from finn.research.ledger import Call, normalise_unit

MAX_POINTS = 5


def _theme(q: dict) -> tuple[str, str | None]:
    key = q.get("metric_key") or "other"
    if key != "other":
        return metrics.label(key), key
    return (q.get("topic") or "Other").strip().capitalize()[:40], None


def pressure_points(calls: list[Call]) -> list[PressurePoint]:
    """Themes asked about in ≥ 2 distinct calls, most-asked first, each citing up to 3 of the questions."""
    by: dict[str, dict] = defaultdict(lambda: {"calls": set(), "qs": [], "key": None})
    for c in calls:
        for q in c.facts.get("analyst_questions", []):
            theme, key = _theme(q)
            b = by[theme.lower()]
            b["theme"], b["key"] = theme, key
            b["calls"].add(c.doc_id)
            b["qs"].append((c, q))
    out = []
    for b in by.values():
        n = len(b["calls"])
        if n < 2 or b["theme"].lower() == "other":
            continue
        latest = sorted(b["qs"], key=lambda cq: cq[0].made_on, reverse=True)
        picks, seen = [], set()
        for c, q in latest:
            if c.doc_id not in seen:
                seen.add(c.doc_id)
                picks.append((c, q))
            if len(picks) == 3:
                break
        gist = picks[0][1].get("gist") or ""
        text = f"Asked in {n} of {len(calls)} calls. Latest: “{gist.rstrip('?')}?”"
        out.append(PressurePoint(
            theme=b["theme"], n_calls=n, metric_key=b["key"],
            claim=Claim(text=text, status="verified", citations=[c.cite(q["page"], q["quote"]) for c, q in picks]),
        ))  # fmt: skip
    out.sort(key=lambda p: -p.n_calls)
    return out[:MAX_POINTS]


def drivers(symbol: str, calls: list[Call], promises: list[Promise]) -> list[Driver]:
    """2–3 suggested drivers: what management guides on most + what analysts ask about most (by driver label)."""
    score: dict[str, dict] = defaultdict(lambda: {"g": 0, "q": 0, "keys": set(), "cite": None})
    for c in calls:
        for g in c.facts.get("guidance", []):
            if g["metric_key"] == "other":
                continue
            s = score[metrics.label(g["metric_key"])]
            s["g"] += 1
            s["keys"].add(g["metric_key"])
            s["cite"] = s["cite"] or c.cite(g["page"], g["quote"])
        for q in c.facts.get("analyst_questions", []):
            if q.get("metric_key", "other") == "other":
                continue
            s = score[metrics.label(q["metric_key"])]
            s["q"] += 1
            s["keys"].add(q["metric_key"])
            s["cite"] = s["cite"] or c.cite(q["page"], q["quote"])
    ranked = sorted(score.items(), key=lambda kv: -(kv[1]["g"] * 2 + kv[1]["q"]))
    out = []
    for label, s in ranked:
        if s["g"] + s["q"] < 3 or s["cite"] is None or label == "Other":
            continue
        slug = label.lower().replace(" ", "-")
        out.append(Driver(
            id=f"{symbol}:{slug}", symbol=symbol, label=label, status="suggested",
            description=f"Management guided on it {s['g']} time(s); analysts asked about it {s['q']} time(s) "
                        f"across {len(calls)} calls",
            source=Claim(text=f"{label}: most-discussed in the company's own calls", status="verified",
                         citations=[s["cite"]]),
            promise_ids=[p.id for p in promises if p.metric_key in s["keys"]],
        ))  # fmt: skip
        if len(out) == 3:
            break
    return out


_SHARE_WORDS = r"share|contribut|of (?:our |the )?(?:total|overall|revenue|sales|business|topline)|mix"


def segments(call: Call | None) -> list[Figure]:
    """Segment figures from the latest call, as reported (with quote). A % counts only as a share of the business
    when its quote says so and the call's shares don't add up past 100% (else they are growth rates); other
    values must be money."""
    if call is None:
        return []
    segs = call.facts.get("segments", [])
    claimed = [x["share_pct"] for x in segs if x.get("share_pct") is not None and 0 < x["share_pct"] <= 100]
    shares_ok = sum(claimed) <= 105
    out = []
    for sgm in segs:
        share = sgm.get("share_pct")
        if shares_ok and share is not None and 0 < share <= 100 and re.search(_SHARE_WORDS, sgm["quote"].lower()):
            value, unit, raw = share, "PCT", f"{share:g}%"
        elif sgm.get("value") is not None:
            fam, f = normalise_unit(sgm.get("unit_text"), "INR", "revenue")
            if fam != "INR_CR":
                continue
            value, unit, raw = sgm["value"] * f, fam, f"{sgm['value']:g} {sgm.get('unit_text') or ''}".strip()
        else:
            continue
        out.append(Figure(label=sgm["name"], value=value, unit=unit, status="verified", raw=raw,
                          raw_unit=sgm.get("unit_text"), citation=call.cite(sgm["page"], sgm["quote"])))  # fmt: skip
    return out[:8]


def ask_chips(drv: list[Driver], has_ledger: bool) -> list[str]:
    chips = [f"What has management said about {d.label.lower()}?" for d in drv[:2]]
    if has_ledger:
        chips.append("Which promises did management miss?")
    return chips[:3]
