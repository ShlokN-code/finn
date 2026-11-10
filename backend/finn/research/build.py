"""Orchestrates one dossier build: discover → compute → documents → extract → ledger → judge → reduce → publish.

Each stage fills its sections and publishes, so the client sees sections turn ready one by one. A stage that
can't run (missing input, quota) leaves an honest status on its sections; it never raises past this module except
on a bug. The last good dossier is the starting point, so a failed rebuild never blanks a ready section.
"""

from __future__ import annotations

import logging
from datetime import datetime

from finn.calendar import now_utc
from finn.models.research import Dossier, SectionMeta
from finn.research import store
from finn.research.jobs import Outcome, Progress
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

    # 3+. Documents, extraction, ledger, synthesis — later stages fill these sections.
    for key in ("documents", "extract", "ledger", "judge", "reduce"):
        progress.step(key, "skipped", "Not available in this build yet")
    progress.step("publish", "done", message="Published")
    store.publish(conn, d, complete=False)
    return Outcome("partial", stats={})


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
