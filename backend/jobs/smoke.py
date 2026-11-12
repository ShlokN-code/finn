"""Daily smoke test of the deployed app (GitHub Actions `smoke.yml`). Standard library only, GETs only.

python -m jobs.smoke [--web https://finn-tau-red.vercel.app] [--api https://finn-api-4ejm.onrender.com]

Never triggers a build or a model call: every route here reads stored data (a cached dossier, the edge-cached demo
Brief, the symbol list, static files). Exits 1 with a list of failures, so the workflow fails and GitHub emails.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import UTC, datetime, timedelta

UA = {"User-Agent": "FINN-smoke/0.1 (+github actions)"}
STALE_AFTER = timedelta(days=4)  # filings feed: weekends + a holiday stay green; a dead pipeline doesn't


def get(url: str, timeout: float = 70) -> tuple[int, bytes, float]:
    t = time.monotonic()
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 — fixed https URLs
            return r.status, r.read(), time.monotonic() - t
    except urllib.error.HTTPError as e:
        return e.code, e.read() or b"", time.monotonic() - t
    except Exception as e:  # noqa: BLE001 — any failure is a smoke failure
        return 0, str(e).encode(), time.monotonic() - t


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--web", default="https://finn-tau-red.vercel.app")
    ap.add_argument("--api", default="https://finn-api-4ejm.onrender.com")
    a = ap.parse_args()
    fails: list[str] = []

    def check(name: str, url: str, test, timeout: float = 70) -> None:
        st, body, dt = get(url, timeout)
        try:
            ok, note = test(st, body)
        except Exception as e:  # noqa: BLE001
            ok, note = False, f"{type(e).__name__}: {e}"
        print(f"{'ok  ' if ok else 'FAIL'} {name:28} HTTP {st} {dt:5.1f}s  {note}")
        if not ok:
            fails.append(f"{name}: HTTP {st} — {note or body[:200]!r}")

    # API first: it wakes Render (free tier sleeps) before the web routes that proxy to it.
    check("api /ping", f"{a.api}/ping", lambda s, b: (s == 200 and b.strip() == b"ok", ""), 90)
    check("api /version", f"{a.api}/version", lambda s, b: (s == 200, json.loads(b).get("short", "")))
    check("api /health/db", f"{a.api}/health/db", lambda s, b: (s == 200 and json.loads(b)["status"] == "ok", ""))

    def page(s, b):
        return s == 200 and b"FINN" in b, f"{len(b) // 1024} KB"

    check("web / (landing)", f"{a.web}/", page)
    check("web /brief", f"{a.web}/brief", page)
    check("web /research/INFY", f"{a.web}/research/INFY", page)

    def demo(s, b):
        d = json.loads(b)
        asof = datetime.fromisoformat(d["data_as_of"].replace("Z", "+00:00")) if d.get("data_as_of") else None
        fresh = asof is not None and datetime.now(UTC) - asof < STALE_AFTER
        return s == 200 and "cards" in d and fresh, f"{len(d['cards'])} cards, data as of {d.get('data_as_of')}"

    check("web /api/brief/demo (7d)", f"{a.web}/api/brief/demo?window=7d", demo)

    def symbols(s, b):
        n = len(json.loads(b)["symbols"])
        return s == 200 and n > 2000, f"{n} symbols"

    check("web /api/research/symbols", f"{a.web}/api/research/symbols", symbols)

    def dossier(s, b):
        d = json.loads(b).get("dossier") or {}
        led = (d.get("ledger") or {}).get("promises") or []
        return s == 200 and d.get("symbol") == "INFY" and len(
            led
        ) > 0, f"{len(led)} promises, built {d.get('built_at')}"

    check("web /api/research/INFY", f"{a.web}/api/research/INFY", dossier)
    check("web /showcase/brief.json", f"{a.web}/showcase/brief.json",
          lambda s, b: (s == 200 and len(json.loads(b)["cards"]) > 0, ""))  # fmt: skip
    check("web /nse-symbols.json", f"{a.web}/nse-symbols.json", lambda s, b: (s == 200, ""))

    if fails:
        print("\nSMOKE FAILED:\n- " + "\n- ".join(fails))
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
