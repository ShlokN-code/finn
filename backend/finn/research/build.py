"""Orchestrates one dossier build: discover → compute → documents → extract → ledger → judge → reduce → publish.

Each stage fills its sections and publishes, so the client sees sections turn ready one by one. A stage that
can't run (missing input, quota) leaves an honest status on its sections; it never raises past this module except
on a bug. The last good dossier is the starting point, so a failed rebuild never blanks a ready section.
"""

from __future__ import annotations

import logging

from finn.calendar import now_utc
from finn.research import store
from finn.research.jobs import Outcome, Progress
from finn.research.skeleton import empty_dossier

log = logging.getLogger("finn.research.build")


def build(conn, symbol: str, progress: Progress, job_id: int | None = None) -> Outcome:
    sec = store.security(conn, symbol)
    name = (sec or {}).get("name") or symbol
    now = now_utc()
    prev = store.load_dossier(store.get_dossier_row(conn, symbol))
    d = prev.model_copy(deep=True) if prev else empty_dossier(symbol, name, now)
    d.built_at = now

    progress.step("discover", "running", message="Finding the company's financials and documents")
    store.publish(conn, d, complete=False)
    for key in ("discover", "compute", "documents", "extract", "ledger", "judge", "reduce"):
        progress.step(key, "skipped", "Not available in this build yet")
    progress.step("publish", "done", message="Published (sections still building)")
    store.publish(conn, d, complete=False)
    return Outcome("partial", stats={})
