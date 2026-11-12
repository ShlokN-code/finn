"""Robustness run: random NSE tickers through the DEPLOYED app (Vercel proxy → Render), as an evaluator would.

python -m evals.research.robustness --symbols HGINFRA,TATACAP,HCC,PGEL,JASH [--base https://finn-tau-red.vercel.app]

Per ticker: GET /api/research/{sym} (before) → POST build → poll the job until done / partial / waiting_quota /
failed (or a timeout) → GET the dossier → section statuses → one Ask question → a Brief with the ticker as the
only holding. Writes evals/research/ROBUSTNESS.md (appends a dated run) and prints a JSON summary.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import requests

from finn.calendar import IST

HERE = Path(__file__).resolve().parent
OUT = HERE / "ROBUSTNESS.md"
SECTIONS = (
    "snapshot",
    "trajectory",
    "ledger",
    "cash_quality",
    "balance_sheet",
    "analysts",
    "red_flags",
    "bull_bear",
    "drivers",
    "exchange_data",
)
UA = {"User-Agent": "FINN-robustness/0.1"}


def call(method: str, url: str, **kw) -> tuple[int, dict | None, float]:
    t = time.monotonic()
    try:
        r = requests.request(method, url, timeout=60, headers=UA, **kw)
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else None
        return r.status_code, body, time.monotonic() - t
    except requests.RequestException as e:
        return 0, {"error": str(e)}, time.monotonic() - t


def run_one(base: str, sym: str, timeout_s: int) -> dict:
    out: dict = {"symbol": sym}
    st, body, dt = call("GET", f"{base}/api/research/{sym}")
    out["get_before"] = {"status": st, "has_dossier": bool(body and body.get("dossier")), "s": round(dt, 2)}
    st, body, dt = call("POST", f"{base}/api/research/{sym}/build")
    job = (body or {}).get("job") or {}
    out["build"] = {"status": st, "job": job.get("id"), "job_status": job.get("status"), "s": round(dt, 2)}
    t0 = time.monotonic()
    last = job
    while job.get("id") and time.monotonic() - t0 < timeout_s:
        st, j, _ = call("GET", f"{base}/api/research/jobs/{job['id']}")
        if st == 200 and j:
            last = j
            if j.get("status") in ("done", "partial", "failed", "waiting_quota"):
                break
        time.sleep(10)
    out["job"] = {
        "status": last.get("status"),
        "error": last.get("error"),
        "secs": round(time.monotonic() - t0),
        "stats": last.get("stats"),
    }
    st, body, _ = call("GET", f"{base}/api/research/{sym}")
    d = (body or {}).get("dossier") or {}
    out["sections"] = {
        k: f"{(d.get(k) or {}).get('meta', {}).get('status')}"
        + (
            f" · {(d.get(k) or {}).get('meta', {}).get('reason')}"
            if (d.get(k) or {}).get("meta", {}).get("reason")
            else ""
        )
        for k in SECTIONS
    }
    led = d.get("ledger") or {}
    out["ledger"] = {"promises": len(led.get("promises") or []), "counts": led.get("counts")}
    out["sources"] = len(d.get("sources") or [])
    st, a, dt = call(
        "POST", f"{base}/api/research/{sym}/ask", json={"question": "What did management say about growth?"}
    )
    out["ask"] = {
        "status": st,
        "answer_status": (a or {}).get("status"),
        "reason": (a or {}).get("reason"),
        "text": ((a or {}).get("answer") or {}).get("text"),
        "s": round(dt, 1),
    }
    st, b, dt = call(
        "POST", f"{base}/api/brief", json={"holdings": [{"symbol": sym, "weight_pct": 100}], "window": "7d"}
    )
    out["brief"] = {
        "status": st,
        "cards": len((b or {}).get("cards") or []),
        "hidden": (b or {}).get("hidden_total"),
        "data_as_of": (b or {}).get("data_as_of"),
        "s": round(dt, 1),
    }
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", required=True)
    ap.add_argument("--base", default="https://finn-tau-red.vercel.app")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--label", default="")
    args = ap.parse_args()
    syms = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    # Builds queue one at a time on Render; start them all, then poll each (its own timeout).
    results = [run_one(args.base, s, args.timeout) for s in syms]
    print(json.dumps(results, indent=1, default=str))
    lines = [
        f"\n## Run {datetime.now(IST):%d %b %Y %H:%M} IST {args.label}".rstrip(),
        "",
        "| Ticker | Build | Time | Calls | Sections ready | Ledger | Ask | Brief |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        ready = sum(1 for v in r["sections"].values() if v.startswith(("ready", "partial")))
        stats = r["job"].get("stats") or {}
        calls = f"{stats.get('calls', '—')} ({', '.join(f'{k} {v}' for k, v in (stats.get('models') or {}).items())})"
        lines.append(
            f"| {r['symbol']} | {r['job']['status']} | {r['job']['secs']} s | {calls} "
            f"| {ready}/{len(SECTIONS)} "
            f"| {r['ledger']['promises']} promises | {r['ask']['answer_status']}"
            f"{' · ' + r['ask']['reason'] if r['ask'].get('reason') else ''} | HTTP {r['brief']['status']}, "
            f"{r['brief']['cards']} cards |"
        )
    lines += ["", "<details><summary>Section states</summary>", ""]
    for r in results:
        lines.append(f"- **{r['symbol']}**: " + ", ".join(f"{k} {v}" for k, v in r["sections"].items()))
    lines += ["", "</details>", ""]
    if not OUT.exists():
        OUT.write_text(
            "# Robustness: random NSE tickers through the deployed app\n\nDraws: "
            "`python -m evals.research.draw_unseen --seed <seed> --robust 5` (seed logged per run).\n"
        )
    with OUT.open("a") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
