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
from finn.models.research import Dossier, DossierQuality, SectionMeta
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
    d.quality = DossierQuality()  # counts are per build, not cumulative

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
        d.quality.quotes_checked += int(st.get("checked") or 0)
        d.quality.quotes_reanchored += int(st.get("reanchored") or 0)
        made = doc.ref.call_date or (doc.ref.period.end if doc.ref.period else now.date())
        calls.append(Call(doc.ref.id, doc.ref.url, f"{doc.ref.period.label if doc.ref.period else ''} call".strip(),
                          made, doc.pages, facts, now))  # fmt: skip
        progress.count(guidance_found=guidance, quotes_dropped=dropped)
    d.quality.quotes_dropped = dropped
    progress.step("extract", "waiting" if quota else "done" if calls else "skipped",
                  f"{len(calls)} of {len(readable)} calls extracted")  # fmt: skip

    # 5. Ledger, analysts, drivers (code)
    progress.step("ledger", "running", message="Scoring promises against what was delivered")
    led = apply_ledger(d, symbol, disc, links, docs, calls, quota, now)
    progress.step("ledger", "done" if calls else "skipped", f"{len(d.ledger.promises)} promises")
    store.publish(conn, d, complete=False)

    # 6–7. Judge + reduce (strong model chain: 3.8 Flash → 3 Flash; never Flash-Lite). An unchanged dossier hits
    # the router's cache, so it costs no strong call.
    tags = {"symbol": symbol, "job_id": job_id}
    strong_quota = run_judge(d, led, calls, router, tags, progress, now) if led else None
    if disc.status == "ok" or calls:
        strong_quota = run_reduce(d, calls, router, tags, progress, now) or strong_quota
    else:
        progress.step("reduce", "skipped", "Nothing to summarise")
        d.bull_bear.meta = meta("unavailable", "not_found_in_sources", "No financials or transcripts to summarise", now)
    quota = quota or strong_quota
    st = router.stats.as_dict()
    d.cost = d.cost.model_copy(update={
        "calls": st["calls"] - stats0["calls"], "cache_hits": st["cache_hits"] - stats0["cache_hits"],
        "tokens_in": st["tokens_in"] - stats0["tokens_in"], "tokens_out": st["tokens_out"] - stats0["tokens_out"],
        "est_usd": round(st["est_cost_usd"] - stats0["est_cost_usd"], 6), "models": st["by_model"],
    })  # fmt: skip
    progress.step("publish", "done", message="Published" if not quota else
                  f"Published what's ready — the rest resumes after {_ist(quota.retry_after)}")  # fmt: skip
    complete = quota is None and all(
        getattr(d, k).meta.status in ("ready", "unavailable")
        for k in ("snapshot", "trajectory", "ledger", "cash_quality", "balance_sheet", "bull_bear")
    )
    store.publish(conn, d, complete=complete)
    stats = {**d.cost.model_dump(), "calls_read": len(calls), "guidance": guidance}
    if quota is not None and quota.kind == "quota" and quota.retry_after:
        return Outcome("waiting_quota", stats=stats, error=str(quota)[:300], resume_after=quota.retry_after)
    return Outcome("done" if complete else "partial", stats=stats)


def _tally_note(cr) -> str:
    """Below the minimum n the tally still shows; the % score and trend need min_n (product owner, 11 Nov)."""
    if cr.n == 0:
        return "No promise can be scored yet — see each one's status"
    return f"{cr.kept} of {cr.n} scored promises kept — a % score needs {cr.min_n} or more"


def _building(resume) -> str:
    return f"Building · resumes after {_ist(resume)} quota reset"


def run_judge(d: Dossier, led, calls, router, tags, progress: Progress, now: datetime) -> LLMUnavailable | None:
    from finn.research import judge
    from finn.research.ledger import count, credibility

    progress.step("judge", "running", message="Judging qualitative promises against later calls")
    req, pid_map = judge.build_request(d.ledger.promises, calls, tags)
    if req is None:
        progress.step("judge", "skipped", "No qualitative promise has later-call evidence to judge")
        return None
    try:
        res = router.run("strong", req)
    except LLMUnavailable as e:
        resume = e.retry_after if e.kind == "quota" else None
        note = f"Qualitative promises: {_building(resume)}" if resume else "Qualitative promises: judged next build"
        d.ledger.meta = d.ledger.meta.model_copy(update={"note": note, "resume_after": resume})
        progress.step("judge", "waiting" if resume else "failed", str(e)[:160])
        return e if resume else None
    jr = judge.apply(d.ledger.promises, res.data, pid_map, calls, res.model, led.settled)
    d.ledger.counts = count(d.ledger.promises)
    d.ledger.credibility = credibility(d.ledger.promises, led.settled, calls)
    cr = d.ledger.credibility
    if d.ledger.meta.status == "ready":
        note = None if cr.shown else _tally_note(cr)
        d.ledger.meta = d.ledger.meta.model_copy(update={"note": note, "written_by": res.model})
    d.quality.claims_dropped += jr.rejected
    progress.step("judge", "done", f"{jr.changed} verdict(s) by {res.model}; {jr.rejected} rejected (no evidence)")
    return None


def run_reduce(d: Dossier, calls, router, tags, progress: Progress, now: datetime) -> LLMUnavailable | None:
    from finn.research import reduce

    progress.step("reduce", "running", message="Writing the summary, bull and bear")
    fs = reduce.facts(d, calls)
    req = reduce.build_request(d, fs, tags)
    if req is None:
        progress.step("reduce", "skipped", "Too few facts to summarise")
        d.bull_bear.meta = meta("unavailable", "not_found_in_sources", "Too few sourced facts to summarise", now)
        return None
    try:
        res = router.run("strong", req)
    except LLMUnavailable as e:
        resume = e.retry_after if e.kind == "quota" else None
        if d.bull_bear.meta.status != "ready":  # keep a previous good summary
            d.bull_bear.meta = meta("building", "llm_quota" if resume else "llm_unavailable",
                                    _building(resume) if resume else "Will be written on the next build", now,
                                    resume_after=resume)  # fmt: skip
        if d.snapshot.meta.status != "ready":
            d.snapshot.meta = meta("partial", "llm_quota" if resume else "llm_unavailable",
                                   f"Business summary: {_building(resume)}" if resume else
                                   "Business summary: written on the next build", now, resume_after=resume)  # fmt: skip
        progress.step("reduce", "waiting" if resume else "failed", str(e)[:160])
        return e if resume else None
    out = reduce.apply(res.data, fs)
    d.quality.claims_dropped += out.dropped
    if out.snapshot:
        d.snapshot.lines = out.snapshot
        d.snapshot.meta = meta("ready", None, None, now, written_by=res.model)
    if out.trajectory_note:
        d.trajectory.note = out.trajectory_note
    d.bull_bear.bull, d.bull_bear.bear = out.bull, out.bear
    full = len(out.bull) == 3 and len(out.bear) == 3
    d.bull_bear.meta = meta("ready" if full else "partial", None if full else "not_found_in_sources",
                            None if full else "Fewer than 3 points were fully supported by sources", now,
                            written_by=res.model)  # fmt: skip
    progress.step("reduce", "done", f"by {res.model}; {out.dropped} unsupported sentence(s) dropped")
    return None


def _ist(dt: datetime | None) -> str:
    from finn.calendar import to_ist

    return f"{to_ist(dt):%H:%M} IST" if dt else "the quota resets"


def apply_ledger(d: Dossier, symbol: str, disc, links, docs, calls, quota, now: datetime):
    from finn.research import insights
    from finn.research.ledger import build_ledger

    resume = quota.retry_after if quota is not None and quota.kind == "quota" else None
    unread = len([x for x in docs if x.ref.status == "read"]) - len(calls)
    if not links:
        reason = "no_screener_page" if disc.status != "ok" else "no_transcripts"
        note = "No earnings-call transcripts found" if disc.status == "ok" else disc.note
        for sec in (d.ledger, d.analysts, d.drivers):
            sec.meta = meta("unavailable", reason, note, now)
        return None
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
        return None
    led = build_ledger(symbol, calls, disc, now.date(), disc.year_end_month or 3)
    d.ledger.promises, d.ledger.credibility, d.ledger.counts = led.promises, led.credibility, led.counts
    d.ledger.calls_read = len(calls)
    if quota is not None:
        d.ledger.meta = meta("partial", "llm_quota", f"Read {len(calls)} of {len(calls) + unread} calls — the rest "
                             f"after {_ist(resume)}", now, resume_after=resume)  # fmt: skip
    elif len(calls) < 4:
        d.ledger.meta = meta("partial", "few_transcripts", f"Based on {len(calls)} call(s)", now)
    else:
        note = None if led.credibility.shown else _tally_note(led.credibility)
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
    return led


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
