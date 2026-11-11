"""Orchestrates one dossier build: discover → compute → documents → extract → ledger → judge → reduce → publish.

Each stage fills its sections and publishes, so the client sees sections turn ready one by one. A stage that
can't run (missing input, quota) leaves an honest status on its sections; it never raises past this module except
on a bug. The last good dossier is the starting point, so a failed rebuild never blanks a ready section.
"""

from __future__ import annotations

import logging
from datetime import datetime

from finn.calendar import now_utc
from finn.llm import LLMUnavailable, PostgresLLMLog, Router
from finn.models.research import Dossier, SectionMeta
from finn.research import store
from finn.research.documents import get_document
from finn.research.extract import map_transcript
from finn.research.jobs import Outcome, Progress
from finn.research.ledger import Call
from finn.research.skeleton import empty_dossier

log = logging.getLogger("finn.research.build")

PIPELINE_VERSION = "1"


def meta(status: str, reason: str | None = None, note: str | None = None, as_of: datetime | None = None,
         **kw) -> SectionMeta:  # fmt: skip
    return SectionMeta(status=status, reason=reason, note=note, as_of=as_of, **kw)


def build(conn, symbol: str, progress: Progress, job_id: int | None = None, router=None) -> Outcome:
    from finn.research.discover import discover

    sec = store.security(conn, symbol)
    name = (sec or {}).get("name") or symbol
    now = now_utc()
    prev = store.load_dossier(store.get_dossier_row(conn, symbol))
    d = prev.model_copy(deep=True) if prev else empty_dossier(symbol, name, now)
    d.built_at = now

    # 1. Discover (screener tables + document index)
    progress.step("discover", "running", message="Finding the company's financials and documents")
    disc = discover(symbol)
    if disc.status == "ok":
        progress.step("discover", "done", f"{len(disc.transcripts)} transcripts, "
                      f"{'an' if disc.annual_report else 'no'} annual report, {disc.basis} financials")  # fmt: skip
    else:
        progress.step("discover", "failed", disc.note)

    # 2. Compute (code only, no model)
    progress.step("compute", "running", message="Computing trajectory, cash and balance sheet")
    apply_compute(d, disc, prev, now)
    progress.step("compute", "done" if disc.status == "ok" else "skipped")
    store.publish(conn, d, complete=False)

    # 3. Documents (transcripts; the annual report comes with the red-flags stage)
    links = disc.transcripts if disc.status == "ok" else []
    progress.count(transcripts_total=len(links))
    progress.step("documents", "running")
    docs = []
    for link in links:
        docs.append(get_document(conn, symbol, link))
        progress.count(transcripts_read=sum(x.ref.status == "read" for x in docs))
    d.sources = [x.ref for x in docs]
    readable = [x for x in docs if x.ref.status == "read"]
    progress.step("documents", "done" if links else "skipped", f"{len(readable)} of {len(links)} transcripts readable")

    # 4. Extract (one cheap call per transcript, cached by document hash + prompt version)
    router = router or Router.default(PostgresLLMLog(conn))
    stats0 = router.stats.as_dict()
    progress.step("extract", "running")
    calls: list[Call] = []
    quota: LLMUnavailable | None = None
    guidance = dropped = 0
    for doc in readable:
        if quota is not None:
            break
        try:
            facts, st = map_transcript(conn, router, doc.sha256, doc.pages, {"symbol": symbol, "job_id": job_id})
        except LLMUnavailable as e:
            quota = e
            log.warning("MAP stopped for %s: %s", symbol, e)
            break
        dropped += int(st.get("dropped_total") or st.get("checked", 0) - st.get("found", 0) - st.get("reanchored", 0))
        guidance += len(facts.get("guidance", []))
        made = doc.ref.call_date or (doc.ref.period.end if doc.ref.period else now.date())
        calls.append(Call(doc.ref.id, doc.ref.url, f"{doc.ref.period.label if doc.ref.period else ''} call".strip(),
                          made, doc.pages, facts, now))  # fmt: skip
        progress.count(guidance_found=guidance, quotes_dropped=dropped)
    d.quality.quotes_dropped = dropped
    progress.step("extract", "waiting" if quota else "done" if calls else "skipped",
                  f"{len(calls)} of {len(readable)} calls extracted")  # fmt: skip

    # 5. Ledger, analysts, drivers (code)
    progress.step("ledger", "running", message="Scoring promises against what was delivered")
    apply_ledger(d, symbol, disc, links, docs, calls, quota, now)
    progress.step("ledger", "done" if calls else "skipped", f"{len(d.ledger.promises)} promises")

    # 6–7. Judge + reduce (strong model) — Thursday's stage; sections say so meanwhile.
    for key in ("judge", "reduce"):
        progress.step(key, "skipped", "Comes with the full build")
    st = router.stats.as_dict()
    d.cost = d.cost.model_copy(update={
        "calls": st["calls"] - stats0["calls"], "cache_hits": st["cache_hits"] - stats0["cache_hits"],
        "tokens_in": st["tokens_in"] - stats0["tokens_in"], "tokens_out": st["tokens_out"] - stats0["tokens_out"],
        "est_usd": round(st["est_cost_usd"] - stats0["est_cost_usd"], 6), "models": st["by_model"],
    })  # fmt: skip
    progress.step("publish", "done", message="Published" if not quota else
                  f"Published what's ready — the rest resumes after {_ist(quota.retry_after)}")  # fmt: skip
    store.publish(conn, d, complete=False)
    stats = {**d.cost.model_dump(), "calls_read": len(calls), "guidance": guidance}
    if quota is not None and quota.kind == "quota" and quota.retry_after:
        return Outcome("waiting_quota", stats=stats, error=str(quota)[:300], resume_after=quota.retry_after)
    return Outcome("partial", stats=stats)


def _ist(dt: datetime | None) -> str:
    from finn.calendar import to_ist

    return f"{to_ist(dt):%H:%M} IST" if dt else "the quota resets"


def apply_ledger(d: Dossier, symbol: str, disc, links, docs, calls, quota, now: datetime) -> None:
    from finn.research import insights
    from finn.research.ledger import build_ledger

    resume = quota.retry_after if quota is not None and quota.kind == "quota" else None
    unread = len([x for x in docs if x.ref.status == "read"]) - len(calls)
    if not links:
        reason = "no_screener_page" if disc.status != "ok" else "no_transcripts"
        note = "No earnings-call transcripts found" if disc.status == "ok" else disc.note
        for sec in (d.ledger, d.analysts, d.drivers):
            sec.meta = meta("unavailable", reason, note, now)
        return
    if not calls:
        scanned = all(x.ref.status == "scanned" for x in docs)
        if quota is not None:
            m = meta("building", "llm_quota", f"Reading transcripts resumes after {_ist(resume)}", now,
                     resume_after=resume)  # fmt: skip
        elif scanned:
            m = meta("unavailable", "scanned_documents", "Transcripts are scanned images — not read", now)
        else:
            m = meta("unavailable", "no_transcripts", "No readable transcripts", now)
        for sec in (d.ledger, d.analysts, d.drivers):
            if sec.meta.status != "ready":  # keep a previous good build's sections
                sec.meta = m
        return
    led = build_ledger(symbol, calls, disc, now.date(), disc.year_end_month or 3)
    d.ledger.promises, d.ledger.credibility, d.ledger.counts = led.promises, led.credibility, led.counts
    d.ledger.calls_read = len(calls)
    if quota is not None:
        d.ledger.meta = meta("partial", "llm_quota", f"Read {len(calls)} of {len(calls) + unread} calls — the rest "
                             f"after {_ist(resume)}", now, resume_after=resume)  # fmt: skip
    elif len(calls) < 4:
        d.ledger.meta = meta("partial", "few_transcripts", f"Based on {len(calls)} call(s)", now)
    else:
        note = None if led.credibility.shown else f"Credibility needs {led.credibility.min_n}+ scored promises " \
            f"(have {led.credibility.n})"  # fmt: skip
        d.ledger.meta = meta("ready", None, note, now)
    d.analysts.points = insights.pressure_points(calls)
    d.analysts.meta = meta("ready" if d.analysts.points else "unavailable",
                           None if d.analysts.points else "not_found_in_sources",
                           None if d.analysts.points else "No topic was raised in two or more calls", now)  # fmt: skip
    d.drivers.items = insights.drivers(symbol, calls, led.promises)
    d.drivers.meta = meta("ready" if d.drivers.items else "unavailable",
                          None if d.drivers.items else "not_found_in_sources", None, now)  # fmt: skip
    latest = max(calls, key=lambda c: c.made_on)
    d.snapshot.segments = insights.segments(latest)
    d.ask_chips = insights.ask_chips(d.drivers.items, bool(led.promises))


def apply_compute(d: Dossier, disc, prev: Dossier | None, now: datetime) -> None:
    """Fill snapshot headline, trajectory, cash quality and balance sheet from screener (or say why not)."""
    from finn.research.compute import compute

    if disc.status != "ok":
        reason = "source_unreachable" if disc.status == "source_unreachable" else "no_screener_page"
        keep = reason == "source_unreachable" and prev is not None  # rule 7: serve the last good sections
        for sec in (d.trajectory, d.cash_quality, d.balance_sheet):
            if keep and sec.meta.status == "ready":
                sec.meta = sec.meta.model_copy(
                    update={
                        "note": f"{disc.note} — showing data as of {sec.meta.as_of:%d %b %Y}"
                        if sec.meta.as_of
                        else disc.note
                    }
                )
            else:
                sec.meta = meta(
                    "unavailable",
                    reason,
                    disc.note
                    if reason == "source_unreachable"
                    else f"No standardised financials for {d.symbol} (screener.in has no page)",
                )
        if not keep:
            d.snapshot.headline = []
        return
    c = compute(disc)
    asof = disc.fetched_at
    d.template, d.basis, d.screener_url, d.as_of = c.template, disc.basis, disc.url, asof  # type: ignore[assignment]
    basis_note = None if disc.basis == "consolidated" else "Standalone figures (no consolidated accounts on screener)"
    d.snapshot.headline = c.headline
    if d.snapshot.meta.status != "ready":
        d.snapshot.meta = meta("partial", "not_built_yet", "Headline numbers ready; business summary is being written",
                               asof)  # fmt: skip
    d.trajectory.series, d.trajectory.growth = c.trajectory, c.growth
    d.trajectory.meta = meta("ready", None, basis_note, asof)
    if c.cash_applicable:
        d.cash_quality.series, d.cash_quality.latest = c.cash, c.cash_latest
        if c.cash:
            has_fcf = any(s.metric == "Free cash flow" for s in c.cash)
            fcf_note = None if has_fcf else "Free cash flow: capex schedule not available on screener"
            d.cash_quality.meta = meta("ready" if not fcf_note else "partial", None, fcf_note or basis_note, asof)
        else:
            d.cash_quality.meta = meta("unavailable", "not_found_in_sources", "No cash-flow table on screener", asof)
    else:
        d.cash_quality.series, d.cash_quality.latest = [], []
        d.cash_quality.meta = meta("unavailable", "not_meaningful_for_lenders",
                                   "CFO/PAT and free cash flow aren't meaningful for lenders: loan growth runs "
                                   "through operating cash flow", asof)  # fmt: skip
    d.balance_sheet.series, d.balance_sheet.latest = c.balance, c.balance_latest
    d.balance_sheet.meta = meta("ready" if c.balance else "unavailable", None if c.balance else "not_found_in_sources",
                                basis_note, asof)  # fmt: skip
