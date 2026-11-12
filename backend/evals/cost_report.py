"""Cost report → backend/evals/COST.md, computed from the LLM log (`llm_calls`) and the job tables.

python -m evals.cost_report            # writes evals/COST.md
python -m evals.cost_report --stdout

Every model attempt is a row in `llm_calls` (ok = answered; failed attempts bill nothing but count against free
daily quotas). `est_cost_usd` is computed at the paid **list price** when the call is made, although FINN runs on
free tiers and pays nothing. Days are Pacific (Gemini's quota day) for quota usage, IST for everything else.
"""

from __future__ import annotations

import argparse
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from finn.calendar import IST
from finn.db import connect
from finn.llm.gemini import PRICES

HERE = Path(__file__).resolve().parent
OUT = HERE / "COST.md"

PUSH_PURPOSES = ("classify_filing", "tag_event", "management_profile", "management_web", "results_pdf")
FREE_RPD = {"gemini-3.5-flash-lite": 500, "gemini-3.8-flash": 20, "gemini-3-flash-preview": 20,
            "gemini-3.6-flash": 20, "gemini-3.5-flash": 20}  # fmt: skip  # AI Studio dashboard, 11 Nov 2026


def usd(x: float | None) -> str:
    x = x or 0.0
    return f"${x:.4f}" if x < 0.1 else f"${x:.2f}"


def k(n: int | None) -> str:
    n = n or 0
    return f"{n / 1000:.1f}K" if n >= 1000 else str(n)


def table(head: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def build(conn) -> str:
    q = conn.execute
    span = q(
        "select min(created_at) a, max(created_at) b, count(*) n, count(*) filter (where ok) ok, "
        "sum(est_cost_usd) usd, sum(tokens_in) ti, sum(tokens_out) tout from llm_calls"
    ).fetchone()
    parts = [
        "# Cost report",
        "",
        f"Generated {datetime.now(IST):%d %b %Y %H:%M} IST by `python -m evals.cost_report` from `llm_calls` "
        f"({span['n']} model attempts, {span['ok']} answered, {span['a']:%d %b} – {span['b']:%d %b %Y} UTC) and the "
        "job tables. **FINN pays $0**: everything runs on free tiers (Gemini AI Studio, Groq, GitHub Actions on a "
        "public repo, Render, Vercel, Supabase). Dollar figures are what the same calls would cost at the paid "
        f"**list price** (Flash-Lite ${PRICES['flash-lite'][0]}/{PRICES['flash-lite'][1]} and Flash "
        f"${PRICES['flash'][0]}/{PRICES['flash'][1]} per million input/output tokens).",
        "",
        f"All-time: {k(span['ti'])} tokens in, {k(span['tout'])} out, **{usd(span['usd'])} at list price**.",
        "",
    ]

    # --- per scheduled ingest run -------------------------------------------------------------------------------
    rows = []
    for job, label in (
        ("check_filings", "30-min filing check"),
        ("ingest_daily", "Daily post-close ingest (16:30)"),
        ("alerts", "07:00 alerts release"),
    ):
        rs = q(
            "select stats from ingest_runs where job = %s and trigger in ('scheduler', 'schedule') "
            "and stats ? 'duration_s'",
            (job,),
        ).fetchall()
        if not rs:
            continue
        calls = [((r["stats"].get("llm") or {}).get("calls") or 0) for r in rs]
        cost = [((r["stats"].get("llm") or {}).get("est_cost_usd") or 0) for r in rs]
        dur = [r["stats"].get("duration_s") or 0 for r in rs]
        rows.append(
            [
                label,
                len(rs),
                f"{statistics.mean(calls):.1f} (max {max(calls)})",
                f"{usd(statistics.mean(cost))} (max {usd(max(cost))})",
                f"{statistics.median(dur):.0f} s",
            ]
        )
    days = q(
        "select (created_at at time zone 'Asia/Kolkata')::date d, count(*) n, count(*) filter (where ok) ok, "
        "sum(est_cost_usd) usd from llm_calls where split_part(purpose, '.', 1) = any(%s) group by 1 order by 1",
        (list(PUSH_PURPOSES),),
    ).fetchall()
    parts += [
        "## Push side (scheduled ingest)",
        "",
        "Model calls only happen for filings the exchange label and rules can't classify, newly tagged events "
        "(impact tag + one-liner) and new management profiles. A run with nothing new makes no call.",
        "",
        table(["Run", "Runs logged", "Model calls / run (avg)", "List-price cost / run", "Median duration"], rows),
        "",
        "Push-side calls per IST day (classification, tagging, management profiles):",
        "",
        table(
            ["IST day", "Attempts", "Answered", "List price"],
            [[f"{d['d']:%a %d %b}", d["n"], d["ok"], usd(d["usd"])] for d in days],
        ),
        "",
    ]

    # --- classification tiers ----------------------------------------------------------------------------------
    tiers = q(
        "select coalesce(classify_tier, 'not yet') t, count(*) n from filings group by 1 order by 2 desc"
    ).fetchall()
    total = sum(t["n"] for t in tiers)
    parts += [
        "## Rules before models: how filings were classified",
        "",
        table(["Tier", "Filings", "Share"], [[t["t"], t["n"], f"{100 * t['n'] / total:.1f}%"] for t in tiers]),
        "",
        f"{total} stored filings. `exchange` = NSE's label alone, `rule` = subject regex, `model` = Flash-Lite "
        "(reading the first PDF pages when the subject says nothing), `failed` = retried next run.",
        "",
    ]

    # --- research: first-time dossiers ---------------------------------------------------------------------------
    per = q("""
        with j as (select id, symbol from research_jobs)
        select j.symbol, c.tier, c.ok, count(*) n, sum(c.tokens_in) ti, sum(c.tokens_out) tout,
               sum(c.est_cost_usd) usd
        from llm_calls c join j on (c.request->'tags'->>'job_id')::bigint = j.id
        where c.purpose like 'research.%%' and c.purpose not like 'research.ask%%'
        group by 1, 2, 3 order by 1""").fetchall()
    agg: dict[str, dict] = defaultdict(lambda: defaultdict(float))
    for r in per:
        a = agg[r["symbol"]]
        key = f"{r['tier']}_{'ok' if r['ok'] else 'fail'}"
        a[key] += r["n"]
        a["ti"] += r["ti"] or 0
        a["tout"] += r["tout"] or 0
        a["usd"] += r["usd"] or 0
    first = {}
    for r in q("""select (c.request->'tags'->>'job_id')::bigint jid, j.symbol, sum(c.est_cost_usd) usd,
                         count(*) filter (where c.ok and c.tier = 'cheap') ch,
                         count(*) filter (where c.ok and c.tier = 'strong') st
                  from llm_calls c join research_jobs j on j.id = (c.request->'tags'->>'job_id')::bigint
                  where c.purpose like 'research.%%' and c.purpose not like 'research.ask%%'
                  group by 1, 2 order by 1""").fetchall():
        first.setdefault(r["symbol"], r)
    jobs = q(
        "select symbol, count(*) n, "
        "count(*) filter (where coalesce((stats->>'calls')::int, 0) = 0 and status = 'done') zero "
        "from research_jobs group by 1"
    ).fetchall()
    jmap = {j["symbol"]: j for j in jobs}
    rows = []
    for sym, a in sorted(agg.items(), key=lambda x: -x[1]["usd"]):
        f1 = first.get(sym)
        f1s = f"job {f1['jid']}: {f1['ch']} cheap + {f1['st']} strong, {usd(f1['usd'])}" if f1 else ""
        rows.append(
            [
                sym,
                f1s,
                int(a["cheap_ok"]),
                int(a["strong_ok"]),
                int(a["cheap_fail"] + a["strong_fail"]),
                f"{k(int(a['ti']))} / {k(int(a['tout']))}",
                usd(a["usd"]),
                jmap.get(sym, {}).get("n", ""),
            ]
        )
    full = [first[s_] for s_, a in agg.items() if a["cheap_ok"] >= 3 and s_ in first and first[s_]["ch"] >= 3]
    mean_full = statistics.mean(f["usd"] or 0 for f in full) if full else 0
    zero = sum(j["zero"] for j in jobs)
    parts += [
        "## Research dossiers",
        "",
        '"First build" is the ticker\'s first job that called a model. The totals add every later job: resumes '
        "after a quota pause and rebuilds after a prompt or pipeline change during development (a new prompt "
        "version is a cache miss by design). An unchanged ticker's rebuild re-reads nothing: transcripts, "
        "extractions and model answers are cached by content hash.",
        "",
        table(
            [
                "Ticker",
                "First build",
                "Cheap calls (all jobs)",
                "Strong calls",
                "Failed attempts",
                "Tokens in / out",
                "List price (all jobs)",
                "Jobs",
            ],
            rows,
        ),
        "",
        f"- **First-time dossier with transcripts:** {usd(mean_full)} at list price (mean of the first builds of "
        f"{len(full)} tickers): ~1 Flash-Lite MAP call per transcript (8 max) + up to 3 deck lookups, then 2 strong "
        "calls (JUDGE, REDUCE). MAP output tokens dominate (a transcript's facts and quotes are copied out).",
        "- **Ticker without transcripts** (e.g. JPOLYINVST): 0 cheap calls, 1 strong call (REDUCE) ≈ $0.004.",
        f"- **Cached dossier:** $0 — {zero} build jobs finished with no model call at all (everything from the cache; "
        "REDUCE's prompt has no date, so an unchanged dossier hits the cache).",
        "- **Opening a dossier** never calls a model: it reads the stored copy.",
        "",
    ]

    # --- drivers ------------------------------------------------------------------------------------------------
    dr = q("""select request->'tags'->>'symbol' s, count(*) n, count(*) filter (where ok) ok, sum(tokens_in) ti,
                     sum(tokens_out) tout, sum(est_cost_usd) usd
              from llm_calls where request->'tags'->>'mode' = 'drivers' group by 1""").fetchall()
    if dr:
        ok = [d for d in dr if d["ok"]]
        parts += [
            '## Drivers builds ("What you\'re watching")',
            "",
            f"{len(dr)} holdings, {sum(d['n'] for d in dr)} attempts ({sum(d['ok'] for d in dr)} answered), "
            f"{usd(sum(d['usd'] or 0 for d in dr))} in all at list price → "
            f"**{usd(sum(d['usd'] or 0 for d in ok) / max(len(ok), 1))} per holding** (≤ 3 Flash-Lite MAP calls on "
            "the latest transcripts; 0 strong calls by construction). The same MAP output is reused when that "
            "ticker's full dossier is built.",
            "",
        ]

    # --- ask ----------------------------------------------------------------------------------------------------
    a = q(
        "select count(*) n, count(*) filter (where ok) ok, avg(tokens_in) ti, avg(tokens_out) tout, "
        "avg(est_cost_usd) usd, avg(latency_ms) ms from llm_calls where purpose like 'research.ask%%'"
    ).fetchone()
    hits = q("select count(*) n, coalesce(sum(hits), 0) h from ask_answers").fetchone()
    parts += [
        "## Ask",
        "",
        f"{a['ok']} answered model calls so far: **{usd(a['usd'])} per question at list price** "
        f"(~{k(int(a['ti'] or 0))} tokens in, ~{int(a['tout'] or 0)} out, ~{(a['ms'] or 0) / 1000:.1f} s). "
        f"{hits['n']} distinct answers cached, served {hits['h']} times from the cache at $0. Caps: 8 new answers per "
        "visitor per IST day; 40 per day for everyone together (Flash-Lite's `research.ask` lane).",
        "",
    ]

    # --- free tier usage ----------------------------------------------------------------------------------------
    fu = q("""select (created_at at time zone 'America/Los_Angeles')::date d, model, count(*) n,
                     count(*) filter (where ok) ok, max(tokens_in) mx
              from llm_calls group by 1, 2 order by 1, 2""").fetchall()
    rows = [
        [
            f"{r['d']:%d %b}",
            r["model"],
            r["n"],
            r["ok"],
            FREE_RPD.get(r["model"], "—"),
            f"{100 * r['n'] / FREE_RPD[r['model']]:.0f}%" if r["model"] in FREE_RPD else "—",
        ]
        for r in fu
    ]
    parts += [
        "## Free-tier usage vs limits",
        "",
        "Per Pacific day (Gemini's quota day: resets 13:30 IST). Failed attempts count toward the daily quota, so "
        "the router counts them too.",
        "",
        table(["Pacific day", "Model", "Attempts", "Answered", "Free RPD", "Used"], rows),
        "",
        "| Service | Free limit | FINN's use |",
        "|---|---|---|",
        "| Gemini Flash-Lite | 15 RPM, 250K TPM, 500 requests/day | push side peaks ~250/day in results season; "
        "research lanes capped at 220 (builds) + 40 (Ask); router stops at 400 |",
        "| Gemini Flash models (strong) | 5 RPM, 20 requests/day each | 2 per new dossier; "
        "chain of 3 models = 60/day |",
        "| Groq (qwen3.8-27b) | 8K tokens/min | fallback for short push calls and Ask only |",
        "| GitHub Actions | free for public repos | ~160 short runs/week (filing checks, daily, alerts, keepalive) |",
        "| Render (web service) | 750 instance-hours/month, sleeps after 15 min idle | one instance; cron-job.org "
        "pings `/ping` every 10 min in the day |",
        "| Supabase | 500 MB database; pauses after 7 days without activity | see `select pg_database_size` "
        "(tens of MB); the 30-min jobs keep it active |",
        "| Vercel (Hobby) | 100 GB transfer/month | static shell + edge-cached demo Brief |",
        "",
    ]

    # --- projection ---------------------------------------------------------------------------------------------
    push_day = statistics.mean([d["usd"] or 0 for d in days]) if days else 0
    at_caps = push_day * 30 + mean_full * 450 + (a["usd"] or 0) * 1200
    parts += [
        "## What it would cost at list price",
        "",
        table(
            ["Item", "Unit cost", "Assumption", "Per month"],
            [
                [
                    "Push side (18 holdings)",
                    f"{usd(push_day)} / day",
                    "measured average per IST day",
                    usd(push_day * 30),
                ],
                [
                    "First-time dossiers",
                    usd(mean_full),
                    "15 per day (the daily cap), every day",
                    usd(mean_full * 15 * 30),
                ],
                ["Ask", usd(a["usd"]), "40 per day (the daily cap)", usd((a["usd"] or 0) * 40 * 30)],
                [
                    "Nightly refresh",
                    "$0 unless a new document",
                    "1 new transcript/week per demo ticker ≈ 1 MAP + 2 strong",
                    usd(4 * 4 * (mean_full / 4)),
                ],
            ],
        ),
        "",
        f"If every daily cap were used every day, the list price would be about {usd(at_caps)} a "
        "month, almost all of it first-time dossiers; a realistic month (a few new tickers a week) is a few dollars. "
        "On the free tiers it costs nothing. The binding constraint is the strong models' 20 requests a day each, "
        "not money: that is why numeric verdicts are computed in code and the summary is reused unless the "
        "document set changes.",
        "",
        "Strong-model rows above 100% are attempts, not billed requests: on 11 Nov `gemini-3.8-flash` answered "
        "503 (overloaded) and timed out on most attempts. The router counts every attempt against the day "
        "(conservative), and after two failures skips that model for 10 minutes.",
        "",
    ]
    return "\n".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()
    with connect() as conn:
        md = build(conn)
    if args.stdout:
        print(md)
    else:
        OUT.write_text(md + "\n")
        print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
