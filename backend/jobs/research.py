"""Research jobs from the command line (GitHub Actions / local).

python -m jobs.research enqueue --symbols INFY,POLYCAB [--reason prewarm]   # add builds to the queue
python -m jobs.research drain [--max 20] [--minutes 40]                     # run queued builds here (a worker)
python -m jobs.research export --symbols INFY,BAJFINANCE --out ../web/public/fixtures   # frontend fixtures
python -m jobs.research resume                                              # re-queue builds parked for quota
python -m jobs.research drivers [--symbols HAL,ITC] [--dry-run]             # drivers only (Flash-Lite, no strong)
python -m jobs.research refresh [--scheduled]                               # nightly: portfolio + demo dossiers

Builds normally run on Render's worker thread; `drain` lets the nightly Actions run (7 GB RAM, same Supabase
queue) take work too. Both claim with SKIP LOCKED, so they never build the same job twice.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

from finn.db import connect
from finn.research import jobs, store

DEMO = ["BAJFINANCE", "INFY", "PERSISTENT", "POLYCAB"]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("enqueue")
    e.add_argument("--symbols", default=",".join(DEMO))
    e.add_argument("--reason", default="prewarm", choices=["requested", "nightly", "new_document", "prewarm"])
    d = sub.add_parser("drain")
    d.add_argument("--max", type=int, default=20)
    d.add_argument("--minutes", type=float, default=40)
    sub.add_parser("resume", help="Re-queue builds parked for model quota now (e.g. after adding a model)")
    dv = sub.add_parser("drivers", help="Suggested drivers for holdings: Flash-Lite MAP + code, never the strong tier")
    dv.add_argument("--symbols", default="", help="Default: demo portfolio holdings without drivers yet")
    dv.add_argument("--dry-run", action="store_true")
    rf = sub.add_parser("refresh", help="Nightly: rebuild portfolio + demo dossiers (model calls only for new docs)")
    rf.add_argument("--scheduled", action="store_true", help="cron slot: run only from 22:00 IST, once a day")
    rf.add_argument("--minutes", type=float, default=35)
    x = sub.add_parser("export")
    x.add_argument("--symbols", default="INFY,BAJFINANCE")
    x.add_argument("--out", default=str(Path(__file__).resolve().parents[2] / "web" / "public" / "fixtures"))
    args = ap.parse_args()

    with connect() as conn:
        if args.cmd == "enqueue":
            for sym in [s.strip().upper() for s in args.symbols.split(",") if s.strip()]:
                job, created = store.enqueue(conn, sym, args.reason, priority=50)
                print(f"{sym}: job {job['id']} {'queued' if created else 'already ' + job['status']}")
        elif args.cmd == "drain":
            worker = f"actions:{os.environ.get('GITHUB_RUN_ID', 'local')}"
            n = jobs.drain(conn, worker, args.max, args.minutes * 60)
            print(f"ran {n} job(s)")
        elif args.cmd == "resume":
            rows = conn.execute(
                "update public.research_jobs set status = 'queued', resume_after = null, updated_at = now() "
                "where status = 'waiting_quota' returning id, symbol"
            ).fetchall()
            print("re-queued:", ", ".join(f"{r['symbol']} (#{r['id']})" for r in rows) or "none")
        elif args.cmd == "drivers":
            run_drivers(conn, args.symbols, args.dry_run)
        elif args.cmd == "refresh":
            run_refresh(conn, args.scheduled, args.minutes)
        elif args.cmd == "export":
            out = Path(args.out)
            out.mkdir(parents=True, exist_ok=True)
            for sym in [s.strip().upper() for s in args.symbols.split(",") if s.strip()]:
                row = store.get_dossier_row(conn, sym)
                dossier = store.load_dossier(row)
                if dossier is None:
                    print(f"{sym}: no current dossier — skipped")
                    continue
                payload = {"symbol": sym, "dossier": dossier.model_dump(mode="json"), "job": None,
                           "dossier_version": row["version"]}  # fmt: skip
                (out / f"dossier_{sym}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
                print(f"{sym}: wrote {out / f'dossier_{sym}.json'}")


DB_SIZE_GUARD_MB = 400  # Supabase free tier: 500 MB


def refresh_symbols(conn) -> list[str]:
    """Demo tickers always; portfolio holdings only when they already have a dossier (first-time builds are for the
    demo tickers only — DECISIONS, Phase 3 budget)."""
    from finn.portfolio import DEMO_PORTFOLIO

    have = {r["symbol"] for r in conn.execute("select symbol from public.dossiers").fetchall()}
    return DEMO + [s for s in DEMO_PORTFOLIO if s in have and s not in DEMO]


def run_refresh(conn, scheduled: bool, minutes: float) -> None:
    """Nightly refresh (DECISIONS: nightly refresh). Each ticker is rebuilt through the normal queue, which makes
    model calls only for what changed: transcripts and extractions are cached by content hash, JUDGE's prompt has no
    date (router cache), and REDUCE is skipped when the document set and verdicts are unchanged (synthesis_hash).
    Screener tables and computed sections refresh every night at no model cost."""
    from finn.calendar import now_utc
    from finn.ingest.pipeline import Run
    from finn.ingest.schedule import refresh_due

    if scheduled:
        due, why = refresh_due(conn, now_utc())
        if not due:
            print(f"refresh: skipped ({why})")
            return
    with Run("research_refresh", conn) as run:
        mb = conn.execute("select pg_database_size(current_database()) / 1048576 as mb").fetchone()["mb"]
        run.stats["db_mb"] = int(mb)
        if mb > DB_SIZE_GUARD_MB:
            run.fail("refresh", "db", f"database is {mb} MB (guard {DB_SIZE_GUARD_MB} MB): refresh skipped")
            return
        syms = refresh_symbols(conn)
        ids = []
        for sym in syms:
            job, created = store.enqueue(conn, sym, "nightly", priority=60)
            ids.append(job["id"])
        conn.commit()
        worker = f"actions:{os.environ.get('GITHUB_RUN_ID', 'local')}:refresh"
        n = jobs.drain(conn, worker, len(syms) + 2, minutes * 60)
        rows = conn.execute(
            "select symbol, status, stats from public.research_jobs where id = any(%s) order by id", (ids,)
        ).fetchall()
        out = {}
        for r in rows:
            st = r["stats"] or {}
            out[r["symbol"]] = {"status": r["status"], "calls": st.get("calls", 0), "models": st.get("models", {})}
            if r["status"] not in ("done", "partial", "waiting_quota", "queued", "running"):
                run.fail("refresh", r["symbol"], f"build {r['status']}")
        run.stats.update({"symbols": syms, "ran_here": n, "jobs": out,
                          "model_calls": sum(v["calls"] or 0 for v in out.values())})  # fmt: skip
        print(json.dumps(run.stats, indent=1, default=str))


def run_drivers(conn, symbols_arg: str, dry_run: bool) -> None:
    from finn.llm import PostgresLLMLog, Router
    from finn.llm.gemini import DEFAULT_CHEAP
    from finn.portfolio import DEMO_WEIGHTS
    from finn.research import drivers_only as dv

    model = os.environ.get("GEMINI_MODEL_CHEAP") or DEFAULT_CHEAP
    used = dv.flash_lite_used_today(conn, model)
    budget = dv.plan_budget(used)
    print(f"{model}: {used} calls today (incl. failed) · headroom {dv.headroom(used)} · this run may spend {budget}")
    if budget == 0:
        print(f"skipped: fewer than {dv.MIN_HEADROOM} calls would stay free after a {dv.RUN_CAP}-call run")
        return
    if symbols_arg:
        syms = [s.strip().upper() for s in symbols_arg.split(",") if s.strip()]
    else:  # largest holdings first; skip those that already have drivers
        have = dv.load_many(conn, list(DEMO_WEIGHTS))
        syms = [s for s in sorted(DEMO_WEIGHTS, key=lambda s: -DEMO_WEIGHTS[s]) if not (have[s] or {}).get("items")]
    print("symbols:", ", ".join(syms) or "none")
    if dry_run or not syms:
        return
    router = dv.CheapOnly(
        Router.default(PostgresLLMLog(conn)), budget, used=lambda: dv.flash_lite_used_today(conn, model)
    )
    for sym in syms:
        r = dv.build_drivers(conn, sym, router)
        dv.save(conn, r)
        labels = ", ".join(i.label for i in r.section.items) or r.section.meta.reason or "none"
        print(
            f"{sym}: {r.calls_read} calls read · drivers: {labels} · spent so far {router.spent}"
            + (f" · stopped: {r.stopped}" if r.stopped else "")
        )
        if router.spent >= budget:
            print("run budget reached — the rest go next time")
            break
        if r.stopped and not r.calls_read:
            print("model unavailable — stopping; the rest go next run")
            break


if __name__ == "__main__":
    main()
