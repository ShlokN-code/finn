"""Drivers-only builds for portfolio holdings (DECISIONS: "What you're watching" drivers without strong calls).

Drivers are pure code over MAP output (insights.drivers via build.apply_ledger), so a holding's suggested drivers
need only the Flash-Lite MAP of its latest calls. This module runs discover → latest 3 transcripts → MAP → code,
stores the drivers section in `drivers`, and never publishes a dossier — Research still shows the normal build
flow for that ticker, which then reuses the cached MAP output.

The strong tier is unreachable here: `CheapOnly` raises if anything asks for it. Before a run the caller checks
today's Flash-Lite count (failed attempts included) and caps the run so evaluators keep their share.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from psycopg.types.json import Jsonb

from finn.calendar import now_utc
from finn.llm import LLMUnavailable
from finn.models.research import DriversSection

log = logging.getLogger("finn.research.drivers")

TRANSCRIPTS = 3  # latest calls per holding — enough for "mentioned in 3+ places" without reading all 8
FLASH_LITE_RPD = 500  # free-tier daily requests (product owner's AI Studio dashboard, 11 Nov 2026)
RUN_CAP = 50  # Flash-Lite calls one drivers run may spend (product owner, 11 Nov)
MIN_HEADROOM = 150  # Flash-Lite calls that must stay free for evaluators and the push side after the run


class StrongTierBlocked(RuntimeError):
    pass


class CheapOnly:
    """Router wrapper for drivers-only builds: cheap tier only, and at most `budget` uncached calls."""

    def __init__(self, inner, budget: int):
        self.inner, self.budget, self.spent = inner, budget, 0
        self.stats = inner.stats

    def run(self, tier, req):
        if tier != "cheap":
            raise StrongTierBlocked(f"drivers-only builds never call the {tier} tier ({req.purpose})")
        if self.spent >= self.budget:
            raise LLMUnavailable("drivers run budget used", kind="quota")
        before = self.inner.stats.calls
        res = self.inner.run(tier, req)
        self.spent += self.inner.stats.calls - before
        return res


@dataclass
class DriversResult:
    symbol: str
    section: DriversSection
    calls_read: int
    stopped: str | None = None


def flash_lite_used_today(conn, model: str) -> int:
    """Calls to the cheap model since Pacific midnight, failed attempts included (they count against quota)."""
    from finn.llm.router import PostgresLLMLog

    return PostgresLLMLog(conn).count_today("gemini", model)


def headroom(used: int) -> int:
    return FLASH_LITE_RPD - used


def plan_budget(used: int) -> int:
    """Calls this run may spend: up to RUN_CAP, and only if MIN_HEADROOM stays free afterwards; else 0."""
    return RUN_CAP if headroom(used) - RUN_CAP >= MIN_HEADROOM else 0


def build_drivers(conn, symbol: str, router, now=None) -> DriversResult:
    from finn.research.build import apply_ledger
    from finn.research.discover import discover
    from finn.research.documents import get_document
    from finn.research.extract import map_transcript
    from finn.research.ledger import Call
    from finn.research.skeleton import empty_dossier

    now = now or now_utc()
    disc = discover(symbol)
    links = disc.transcripts[:TRANSCRIPTS] if disc.status == "ok" else []
    docs = [get_document(conn, symbol, link) for link in links]
    readable = [x for x in docs if x.ref.status == "read"]
    calls: list = []
    stopped: str | None = None
    stop_kind: str | None = None
    for doc in readable:
        try:
            facts, _ = map_transcript(conn, router, doc.sha256, doc.pages, {"symbol": symbol, "mode": "drivers"})
        except LLMUnavailable as e:
            stopped, stop_kind = str(e), e.kind
            break
        made = doc.ref.call_date or (doc.ref.period.end if doc.ref.period else now.date())
        label = f"{doc.ref.period.label if doc.ref.period else ''} call".strip()
        calls.append(Call(doc.ref.id, doc.ref.url, label, made, doc.pages, facts, now))
    d = empty_dossier(symbol, symbol, now)
    apply_ledger(d, symbol, disc, links, docs, calls, None, now)
    if stopped and not calls:
        quota = stop_kind == "quota"
        d.drivers.meta = d.drivers.meta.model_copy(update={
            "status": "building" if quota else "unavailable", "reason": "llm_quota" if quota else "llm_unavailable",
            "note": "Drivers resume after the quota reset" if quota else "Model busy; retried next run",
        })  # fmt: skip
    return DriversResult(symbol, d.drivers, len(calls), stopped)


def save(conn, r: DriversResult) -> None:
    conn.execute(
        "insert into public.drivers (symbol, section, calls_read, built_at) values (%s, %s, %s, now()) "
        "on conflict (symbol) do update set section = excluded.section, calls_read = excluded.calls_read, "
        "built_at = excluded.built_at",
        (r.symbol, Jsonb(r.section.model_dump(mode="json")), r.calls_read),
    )


def load_many(conn, symbols: list[str]) -> dict[str, dict | None]:
    """Drivers per symbol: a full dossier's section if it has drivers, else the drivers-only row, else None."""
    out: dict[str, dict | None] = {s: None for s in symbols}
    for r in conn.execute("select symbol, section from public.drivers where symbol = any(%s)", (symbols,)).fetchall():
        out[r["symbol"]] = r["section"]
    rows = conn.execute(
        "select symbol, payload->'drivers' as drivers from public.dossiers where symbol = any(%s)", (symbols,)
    ).fetchall()
    for r in rows:
        if r["drivers"] and (r["drivers"].get("items") or out[r["symbol"]] is None):
            out[r["symbol"]] = r["drivers"]
    return out
