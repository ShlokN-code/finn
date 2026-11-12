"""Ingest pipeline steps shared by the jobs. Each step is independent: a failing source records its error in
source_status / the run's failures and the run continues — readers keep serving the last good data (rule 7).
"""

from __future__ import annotations

import logging
import os
import time
import traceback
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

from finn import store
from finn.calendar import ist_today, previous_quarter_end, set_holidays, year_ago_quarter_end
from finn.classification.ladder import Classifier
from finn.events.threader import thread
from finn.extraction.results import build as results_build
from finn.extraction.results import compute, xbrl
from finn.llm import PostgresLLMLog, Router
from finn.sources import nse, screener
from finn.sources.http import FetchError, NSESession, fetch_capped
from finn.sources.prices import fetch_bars, needs_restatement

log = logging.getLogger("finn.ingest")

BACKFILL_PERIOD = "1y"
INCREMENTAL_DAYS = 15  # calendar days ≈ 10 sessions
MAX_PDF_BYTES = 12 * 1024 * 1024
MAX_XBRL_BYTES = 8 * 1024 * 1024
RESULTS_PDF_BYTES = 32 * 1024 * 1024  # board outcomes bundle scanned auditor reports: 18–25 MB is common


@dataclass
class Run:
    job: str
    conn: object
    stats: dict = field(default_factory=dict)
    failures: list = field(default_factory=list)
    run_id: int | None = None
    t0: float = field(default_factory=time.monotonic)

    def __enter__(self):
        # FINN_TRIGGER (set by the workflow) tells the external scheduler apart from a manual dispatch
        trigger = os.environ.get("FINN_TRIGGER") or os.environ.get("GITHUB_EVENT_NAME", "local")
        self.run_id = store.start_run(self.conn, self.job, trigger)
        return self

    def fail(self, step: str, scope: str, err: BaseException | str) -> None:
        msg = err if isinstance(err, str) else f"{type(err).__name__}: {err}"
        log.warning("[%s] %s failed: %s", step, scope, msg)
        self.failures.append({"step": step, "scope": scope, "error": str(msg)[:500]})

    def step(self, name: str, fn, *args, **kw):
        t = time.monotonic()
        try:
            out = fn(self, *args, **kw)
        except Exception as e:  # a step crashing must not stop the others
            self.fail(name, "all", e)
            log.error(traceback.format_exc())
            out = None
        self.stats.setdefault("timings_s", {})[name] = round(time.monotonic() - t, 1)
        return out

    def __exit__(self, exc_type, exc, tb):
        if exc:
            self.fail("job", "all", exc)
        status = "failed" if exc else ("partial" if self.failures else "ok")
        self.stats["duration_s"] = round(time.monotonic() - self.t0, 1)
        store.finish_run(self.conn, self.run_id, status, self.stats, self.failures)
        write_summary(self, status)
        return False


# --- steps ------------------------------------------------------------------------------------


def step_holidays(run: Run, s: NSESession) -> None:
    try:
        days = nse.fetch_holidays(s)
        store.upsert_holidays(run.conn, days, "nse_holiday_master")
        store.mark_source(run.conn, "nse_holidays", "all", ok=True, rows=len(days))
    except Exception as e:
        store.mark_source(run.conn, "nse_holidays", "all", ok=False, error=str(e)[:300])
        run.fail("holidays", "all", e)
    set_holidays(store.load_holidays(run.conn))


def step_securities(run: Run, s: NSESession) -> None:
    rows = nse.fetch_equity_list(s)
    if not rows:
        store.mark_source(run.conn, "nse_equity_list", "all", ok=False, error="empty or blocked")
        run.fail("securities", "all", "equity list empty or blocked")
        return
    n = store.upsert_securities(run.conn, rows)
    store.mark_source(run.conn, "nse_equity_list", "all", ok=True, rows=n)
    run.stats["securities"] = n


def step_prices(run: Run, symbols: list[str], backfill: bool = False) -> None:
    counts = store.price_row_counts(run.conn, symbols)
    full = [s for s in symbols if backfill or counts.get(s, 0) < 200]
    incr = [s for s in symbols if s not in full]
    written, restated, ok = 0, [], set()
    if incr:
        start = ist_today() - timedelta(days=INCREMENTAL_DAYS)
        bars = fetch_bars(incr, start=start)
        for sym in incr:
            if sym not in bars:
                continue
            stored = store.stored_closes(run.conn, sym, start)
            if needs_restatement(stored, bars[sym]):
                restated.append(sym)
            else:
                written += store.upsert_prices(run.conn, bars[sym])
                ok.add(sym)
                store.mark_source(run.conn, "yahoo_prices", sym, ok=True, rows=len(bars[sym]))
        full += restated
    if full:
        bars = fetch_bars(full, period=BACKFILL_PERIOD)
        for sym in full:
            if sym in bars:
                store.replace_prices(run.conn, sym, bars[sym])
                written += len(bars[sym])
                ok.add(sym)
                store.mark_source(run.conn, "yahoo_prices", sym, ok=True, rows=len(bars[sym]))
    for sym in symbols:
        if sym not in ok:
            store.mark_source(run.conn, "yahoo_prices", sym, ok=False, error="no data from Yahoo")
            run.fail("prices", sym, "no data from Yahoo (rate limit?)")
    run.stats["prices"] = {"rows_written": written, "backfilled": sorted(set(full) - set(restated)),
                           "restated": restated}  # fmt: skip


def step_announcements(run: Run, s: NSESession, symbols: list[str], frm: date, to: date) -> None:
    now = datetime.now(UTC)
    total = 0
    for sym in symbols:
        try:
            rows = nse.fetch_announcements(s, sym, frm, to)
            items = []
            for r in rows:
                try:
                    items.append((nse.announcement_to_filing(r, now), r, r.get("fileSize")))
                except Exception as e:
                    run.fail("announcements.parse", sym, e)
            total += store.upsert_filings(run.conn, items)
            store.mark_source(run.conn, "nse_announcements", sym, ok=True, rows=len(items))
        except Exception as e:
            store.mark_source(run.conn, "nse_announcements", sym, ok=False, error=str(e)[:300])
            run.fail("announcements", sym, e)
    run.stats["announcements"] = total


def step_board_meetings(run: Run, s: NSESession, symbols: list[str], since: date) -> None:
    now = datetime.now(UTC)
    total = 0
    for sym in symbols:
        try:
            rows = nse.fetch_board_meetings(s, sym)
            items = []
            for r in rows:
                f = nse.board_meeting_to_filing(r, now)
                if f and f.filed_at.date() >= since:
                    items.append((f, r, r.get("attFileSize")))
            total += store.upsert_filings(run.conn, items)
            store.mark_source(run.conn, "nse_board_meetings", sym, ok=True, rows=len(items))
        except Exception as e:
            store.mark_source(run.conn, "nse_board_meetings", sym, ok=False, error=str(e)[:300])
            run.fail("board_meetings", sym, e)
    run.stats["board_meetings"] = total


def step_corporate_actions(run: Run, s: NSESession, symbols: list[str]) -> None:
    total = 0
    for sym in symbols:
        try:
            rows = nse.fetch_corporate_actions(s, sym)
            items = [(a, r) for r in rows if (a := nse.to_corporate_action(r))]
            total += store.upsert_actions(run.conn, items)
            store.mark_source(run.conn, "nse_corporate_actions", sym, ok=True, rows=len(items))
        except Exception as e:
            store.mark_source(run.conn, "nse_corporate_actions", sym, ok=False, error=str(e)[:300])
            run.fail("corporate_actions", sym, e)
    run.stats["corporate_actions"] = total


def step_deals(run: Run, s: NSESession, symbols: list[str], frm: date, to: date) -> None:
    """API for the window, plus the archive CSV (the API lags the latest session by a day or more)."""
    tracked = set(symbols)
    out = {}
    for kind in ("bulk", "block"):
        deals, errors = {}, []
        try:
            deals.update({d.id: d for d in nse.fetch_deals(s, kind, frm, to)})
        except (FetchError, ValueError) as e:
            errors.append(f"api: {e}")
        try:
            deals.update({d.id: d for d in nse.fetch_deals_archive(s, kind)})
        except (FetchError, ValueError) as e:
            errors.append(f"archive: {e}")
        mine = [d for d in deals.values() if d.symbol in tracked]
        store.upsert_deals(run.conn, mine)
        ok = bool(deals) or not errors
        store.mark_source(run.conn, f"nse_{kind}_deals", "all", ok=ok, rows=len(deals), error="; ".join(errors))
        if errors:
            run.fail("deals", kind, "; ".join(errors))
        out[kind] = {"market_rows": len(deals), "tracked": len(mine)}
    run.stats["deals"] = out


def make_classifier(run: Run, s: NSESession | None) -> tuple[Classifier, Router]:
    router = Router.default(PostgresLLMLog(run.conn))
    if not router.providers:
        log.warning("no LLM key configured — tier (c) disabled; leftovers stay unclassified")

    def pdf_fetcher(url: str) -> bytes | None:
        if s is None:
            return None
        data = fetch_capped(s, url, max_bytes=MAX_PDF_BYTES, deadline_s=60)
        return data if data and data.startswith(b"%PDF") else None

    return Classifier(router if router.providers else None, pdf_fetcher), router


def step_classify(run: Run, s: NSESession | None, symbols: list[str] | None) -> None:
    clf, router = make_classifier(run, s)
    todo = store.filings_to_classify(run.conn, symbols)
    clf.names.update(store.company_names(run.conn, sorted({f.symbol for f in todo})))
    for f in todo:
        c = clf.classify(f)
        c.apply(f)
        store.save_classification(run.conn, f, c.tier, c.note)
    run.stats["classification"] = clf.stats.as_dict()
    run.stats["llm"] = router.stats.as_dict()
    for msg in clf.stats.failures[:50]:
        scope = msg.split(" ")[1].rstrip(":") if " " in msg else "?"
        run.failures.append({"step": "classify", "scope": scope, "error": " ".join(msg.split())})


def step_thread(run: Run, symbols: list[str]) -> None:
    filings = store.filings_for_symbols(run.conn, symbols)
    events, assignment = thread(filings)
    n = store.save_events(run.conn, symbols, events, assignment)
    run.stats["events"] = {"events": n, "threaded_filings": sum(1 for v in assignment.values() if v),
                           "filings": len(filings)}  # fmt: skip


def results_quarters(period_end: date) -> list[date]:
    """Current, previous and year-ago quarter ends for a results event."""
    return [period_end, previous_quarter_end(period_end), year_ago_quarter_end(period_end)]


def step_results_fetch(run: Run, s: NSESession, symbols: list[str], days: int = 45) -> None:
    """XBRL for every recent results event: current, previous and year-ago quarter, both bases.
    Already-stored instances are skipped (they never change; a revision has its own URL)."""
    events = store.recent_results_events(run.conn, symbols, days)
    stats = {"events": len(events), "downloaded": 0, "already_stored": 0, "missing": []}
    for sym in sorted({e["symbol"] for e in events}):
        need: set[date] = set()
        for e in (e for e in events if e["symbol"] == sym and e["period"]):
            need.update(results_quarters(date.fromisoformat(e["period"]["end"])))
        try:
            refs = nse.fetch_integrated_results(s, sym)
        except FetchError as err:
            store.mark_source(run.conn, "nse_results_xbrl", sym, ok=False, error=str(err)[:300])
            run.fail("results_fetch", sym, err)
            continue
        have = store.stored_xbrl_urls(run.conn, sym)
        stats["ixbrl_linked"] = stats.get("ixbrl_linked", 0) + store.set_ixbrl_urls(run.conn, refs)
        for q in sorted(need):
            mine = [r for r in refs if r.period_end == q]
            if not mine:
                stats["missing"].append(f"{sym} {q}")
            for ref in mine:
                if ref.xbrl_url in have:
                    stats["already_stored"] += 1
                    continue
                xml = fetch_capped(s, ref.xbrl_url, max_bytes=MAX_XBRL_BYTES, deadline_s=60)
                if not xml or b"<" not in xml[:200]:
                    run.fail("results_fetch", sym, f"XBRL download failed: {ref.xbrl_url}")
                    continue
                try:
                    parsed = xbrl.parse_instance(xml)
                except Exception as err:  # malformed instance: record, keep going
                    run.fail("results_fetch", sym, f"XBRL parse failed {ref.xbrl_url}: {err}")
                    continue
                store.upsert_results_filing(run.conn, ref, parsed, xbrl.gz(xml))
                stats["downloaded"] += 1
        store.mark_source(run.conn, "nse_results_xbrl", sym, ok=True, rows=len(refs))
    run.stats["results_fetch"] = stats


def _results_from_pdf(run: Run, s: NSESession, url: str, qe: date, ev: dict, stats: dict):
    """XBRL not filed yet: the results PDF's table (text layer), else the multimodal model (scanned)."""
    from finn.citations import pdf_text
    from finn.classification.ladder import first_pages
    from finn.extraction.results import pdf_model, pdf_table

    raw = fetch_capped(s, url, max_bytes=MAX_PDF_BYTES, deadline_s=60)
    if not raw or not raw.startswith(b"%PDF"):
        return None, None
    filed = next((datetime.fromisoformat(t["at"]) for t in ev["timeline"] if t["stage"] == "outcome"), None)
    _, pages = pdf_text(raw, max_pages=12)
    if any(p.strip() for p in pages):
        got = pdf_table.quarters_from_pdf(pages, qe, url, filed)
        if got:
            stats.setdefault("pdf_table", 0)
            stats["pdf_table"] += 1
            return got, "pdf_table"
    router = Router.default(PostgresLLMLog(run.conn))
    if not router.providers:
        return None, None
    got = pdf_model.quarters_from_model(router, first_pages(raw, 6) or raw, qe, url, filed)
    if got:
        stats.setdefault("pdf_model", 0)
        stats["pdf_model"] += 1
        return got, "pdf_model"
    return None, None


def _results_doc(run: Run, s: NSESession | None, outcome_ids: list[str], basis: str, revenue_cr: float | None,
                 stats: dict):  # fmt: skip
    """The results PDF and the page with this basis's statement (cached in results_pdf_pages). Looking a page up
    needs the PDF, so only a run with an NSE session (Actions) can find new pages; others reuse stored ones."""
    from finn.citations import pdf_text
    from finn.extraction.results.links import ResultsDoc, find_results_page

    pdfs = store.outcome_pdfs(run.conn, outcome_ids)
    if not pdfs:
        return None
    known = store.results_pdf_pages(run.conn, [p["id"] for p in pdfs], basis)
    for p in pdfs:
        k = known.get(p["id"])
        if k and k["page"]:
            return ResultsDoc(k["url"], k["page"])
    if s is None:
        return None
    for p in pdfs:
        if p["id"] in known:
            continue  # looked before, no statement page in it
        raw = fetch_capped(s, p["attachment_url"], max_bytes=RESULTS_PDF_BYTES, deadline_s=120)
        if not raw or not raw.startswith(b"%PDF"):
            store.save_results_pdf_page(run.conn, p["id"], basis, p["attachment_url"], None, False, "not a PDF")
            continue
        _, pages = pdf_text(raw, max_pages=40)
        m = find_results_page(pages, basis, revenue_cr) if any(t.strip() for t in pages) else None
        note = None if m else ("no text layer (scanned)" if not any(t.strip() for t in pages) else "no statement page")
        store.save_results_pdf_page(run.conn, p["id"], basis, p["attachment_url"], m.page if m else None,
                                    bool(m and m.value_on_page), note)  # fmt: skip
        stats["pdf_pages_found" if m else "pdf_pages_missing"] = stats.get("pdf_pages_found" if m else
                                                                           "pdf_pages_missing", 0) + 1  # fmt: skip
        if m:
            return ResultsDoc(p["attachment_url"], m.page)
    return None


def _with_readable_links(run: Run, s: NSESession | None, sym: str, outcome_ids: list[str], detail, reason, stats):
    """Point every results figure at the results PDF page (→ iXBRL view → raw XBRL, labelled)."""
    from finn.extraction.results.links import apply_links, revenue_input_cr

    if detail.source_path != "xbrl":
        return detail, reason  # PDF-sourced cards already cite the PDF page
    doc = _results_doc(run, s, outcome_ids, detail.basis, revenue_input_cr(detail), stats)
    return apply_links(detail, reason, symbol=sym, pdf=doc, ixbrl=store.ixbrl_map(run.conn, sym))


def step_results_relink(run: Run, symbols: list[str], days: int, s: NSESession | None = None) -> None:
    """Rewrite the links of stored results cards without recomputing a number (backfill after the link change)."""
    from finn.models import Claim, ResultsDetail

    stats: dict = {"relinked": 0, "skipped": 0}
    if s is not None:  # NSE's iXBRL links for instances stored before they were recorded
        for sym in symbols:
            try:
                stats["ixbrl_linked"] = stats.get("ixbrl_linked", 0) + store.set_ixbrl_urls(
                    run.conn, nse.fetch_integrated_results(s, sym)
                )
            except FetchError as err:
                run.fail("results_relink", sym, err)
    for ev in store.recent_results_events(run.conn, symbols, days):
        d = ev["detail"] or {}
        if d.get("kind") != "results" or d.get("source_path") != "xbrl":
            stats["skipped"] += 1
            continue
        outcome_ids = [t["filing_id"] for t in ev["timeline"] if t["stage"] == "outcome"]
        detail = ResultsDetail.model_validate(d)
        reason = Claim.model_validate(ev["impact_reason"]) if ev.get("impact_reason") else None
        detail, reason = _with_readable_links(run, s, ev["symbol"], outcome_ids, detail, reason, stats)
        store.update_event_links(run.conn, ev["id"], detail.model_dump(mode="json"),
                                 reason.model_dump(mode="json") if reason else None)  # fmt: skip
        stats["relinked"] += 1
    run.stats["results_relink"] = stats


def step_results_build(run: Run, symbols: list[str], days: int = 45, s: NSESession | None = None,
                       rebuild: bool = False) -> None:  # fmt: skip
    """Build/refresh results cards from stored XBRL + screener. Final cards (XBRL, cross-checked or partial)
    are left alone unless `rebuild`; pending and unverified ones are re-checked every run (screener publishes
    hours after results)."""
    stats = {"built": 0, "cross_checked": 0, "partial": 0, "pending": 0, "mismatch": 0, "no_xbrl_yet": [],
             "final": 0}  # fmt: skip
    for ev in store.recent_results_events(run.conn, symbols, days):
        old = ev["detail"] or {}
        if not rebuild and old.get("source_path") == "xbrl" and old.get("verification") in ("cross_checked", "partial"):
            stats["final"] += 1
            continue
        sym, qe = ev["symbol"], date.fromisoformat(ev["period"]["end"]) if ev["period"] else None
        if qe is None:
            continue
        outcome_ids = [t["filing_id"] for t in ev["timeline"] if t["stage"] == "outcome"]
        filing_url = next((u for u in store.filing_urls(run.conn, outcome_ids).values() if u), None)
        got = results_build.quarters_from_xbrl(store.results_filings(run.conn, sym), qe)
        source_path = "xbrl"
        if got is None:
            stats["no_xbrl_yet"].append(f"{sym} {qe}")
            if s is None or not filing_url:
                continue  # the PDF lives on NSE archives: Actions only
            got, source_path = _results_from_pdf(run, s, filing_url, qe, ev, stats)
            if got is None:
                continue
        basis, quarters = got
        template = compute.template_for(quarters["current"], store.symbol_industry(run.conn, sym))
        try:
            table = screener.fetch_quarters(sym, basis)
        except Exception as err:  # screener down → pending, retried next run (rule 7)
            run.fail("results_build", sym, f"screener: {err}")
            table = None
        b = results_build.build_from_quarters(template, basis, qe, quarters, table, source_path, filing_url)
        detail, reason = _with_readable_links(run, s, sym, outcome_ids, b.detail, b.impact_reason, stats)
        store.save_event_detail(
            run.conn, ev["id"], detail.model_dump(mode="json"), b.so_what, b.impact,
            reason.model_dump(mode="json") if reason else None, "code",
        )  # fmt: skip
        stats["built"] += 1
        stats[b.detail.verification] += 1
        if b.detail.verification == "mismatch":
            # a card state ("Couldn't verify — open filing"), not a run failure: it would otherwise mark every
            # 30-minute run partial for as long as the card exists (PLAN: ITC/RELIANCE)
            stats.setdefault("mismatch_cards", []).append(f"{sym}: {(b.detail.verification_note or '')[:200]}")
    run.stats["results"] = stats


TAG_LIMIT = 25  # model calls per run for Level-0 tags (bounded: shares the free-tier daily budget)


def primary_filing(event: dict, filings: dict[str, dict]) -> dict | None:
    """The filing that best states the event: an outcome or unstaged filing, newest first; ads last."""
    items = [filings[t["filing_id"]] for t in event["timeline"] if t["filing_id"] in filings]
    rank = {"newspaper_ad": 2, "intimation": 1}
    return min(items, key=lambda f: (rank.get(f.get("stage") or "", 0), -f["filed_at"].timestamp()), default=None)


def step_tag(run: Run, s: NSESession | None, symbols: list[str], days: int = 45) -> None:
    """Level-0 impact + one-liner facts (cheap model), management profiles (+ optional web), chips (code)."""
    from finn.cards.chips import chip_for
    from finn.citations import pdf_text
    from finn.classification.ladder import first_pages
    from finn.extraction import management
    from finn.ranking.impact import SKIP, tag_event

    router = Router.default(PostgresLLMLog(run.conn))
    events = store.events_to_tag(run.conn, symbols, days, 200)
    filings = store.filing_rows(run.conn, sorted({t["filing_id"] for e in events for t in e["timeline"]}))
    names = store.company_names(run.conn, sorted({e["symbol"] for e in events}))
    stats = {"candidates": len(events), "tagged": 0, "chips": 0, "management": 0, "failed": 0, "web": {}}
    calls = 0
    for e in events:
        f = primary_filing(e, filings)
        if f is None:
            continue
        if e["category"] in ("dividend", "bonus_split"):
            chip = chip_for(e, store.actions_for(run.conn, e["symbol"]), f)
            store.save_detail(run.conn, e["id"], chip.model_dump(mode="json") if chip else None)
            store.save_impact(run.conn, e["id"], None, None, chip.text[:60] if chip else None, "code")
            stats["chips"] += 1
            continue
        if e["category"] in SKIP or not router.providers or calls >= TAG_LIMIT:
            continue
        raw = None
        if s is not None and f.get("attachment_url"):
            raw = fetch_capped(s, f["attachment_url"], max_bytes=MAX_PDF_BYTES, deadline_s=60)
            raw = raw if raw and raw.startswith(b"%PDF") else None
        company = names.get(e["symbol"], e["symbol"])
        is_mgmt = e["category"] == "management_change"
        old = e.get("detail") or {}
        if e["impact_tier"] in (None, "failed"):
            calls += 1
            tagged = tag_event(router, e, f, first_pages(raw) if raw else None, company)
            store.save_impact(run.conn, e["id"], tagged.impact,
                              tagged.reason.model_dump(mode="json") if tagged.reason else None, tagged.so_what,
                              tagged.tier)  # fmt: skip
            if tagged.tier == "failed":
                stats["failed"] += 1
                continue
            stats["tagged"] += 1
            if not is_mgmt and tagged.detail:
                store.save_detail(run.conn, e["id"], tagged.detail.model_dump(mode="json"))
        if is_mgmt:
            from finn.models import ManagementDetail

            detail = ManagementDetail.model_validate(old) if old.get("kind") == "management_change" else None
            if detail is None:
                text, pages = pdf_text(raw, max_pages=8)
                calls += 1
                detail = management.extract(router, e, f, text, pages, first_pages(raw, 8) if raw else None,
                                            company)  # fmt: skip
            if detail is not None:
                detail = management.enrich(router, detail, company)
                stats["web"][detail.web_enrichment] = stats["web"].get(detail.web_enrichment, 0) + 1
                store.save_detail(run.conn, e["id"], detail.model_dump(mode="json"))
                if sw := management.so_what(detail):
                    run.conn.execute("update public.events set so_what = %s where id = %s", (sw, e["id"]))
                stats["management"] += 1
    run.stats["tag"] = stats
    run.stats["llm"] = router.stats.as_dict()


# --- reporting --------------------------------------------------------------------------------


def write_summary(run: Run, status: str) -> None:
    """Human summary to stdout and, in GitHub Actions, to the job summary page."""
    cls = run.stats.get("classification", {})
    lines = [f"## {run.job}: {status}", "", f"- duration: {run.stats.get('duration_s')} s"]
    for k in (
        "securities",
        "announcements",
        "board_meetings",
        "corporate_actions",
        "results_fetch",
        "results",
        "signals",
        "alerts",
    ):
        if k in run.stats:
            lines.append(f"- {k}: {run.stats[k]}")
    if "prices" in run.stats:
        lines.append(f"- prices: {run.stats['prices']}")
    if "deals" in run.stats:
        lines.append(f"- deals: {run.stats['deals']}")
    if cls:
        lines += ["", "### Classification tier split", "", "| tier | filings | % |", "|---|---|---|"]
        for tier in ("exchange", "rule", "model", "failed"):
            lines.append(f"| {tier} | {cls['tiers'].get(tier, 0)} | {cls['tier_pct'].get(tier, 0)} |")
        lines.append(f"\nLLM: {run.stats.get('llm')}")
    if "events" in run.stats:
        lines.append(f"- events: {run.stats['events']}")
    if run.failures:
        lines += ["", f"### Failures ({len(run.failures)})", ""]
        lines += [f"- `{f['step']}` {f['scope']}: {f['error'][:200]}" for f in run.failures[:40]]
    text = "\n".join(lines) + "\n"
    print(text, flush=True)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a") as fh:
            fh.write(text)
