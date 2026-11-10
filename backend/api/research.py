"""Research endpoints (Phase 3).

GET  /research/symbols          NSE equity list for autocomplete ([symbol, name]); cached for a day
GET  /research/{symbol}         DossierResponse: the last good dossier (instant) + the active/latest build job
POST /research/{symbol}/build   start a build (reuses an active job; a fresh dossier isn't rebuilt); daily cap
GET  /research/jobs/{id}        DossierJob — poll every ~3 s; refetch the dossier when dossier_version changes
POST /research/{symbol}/ask     company-scoped question → AskAnswer (cited, or 'Not found in sources')

Builds run in the background (finn.research.jobs.Worker), so no request here waits on a model.
"""

from __future__ import annotations

import os
import threading
import time
from datetime import timedelta

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from finn.calendar import now_utc
from finn.db import connect
from finn.models.research import AskAnswer, DossierResponse
from finn.research import store

router = APIRouter(prefix="/research", tags=["research"])

FRESH_FOR = timedelta(hours=24)
DAILY_FIRST_BUILDS = int(os.environ.get("RESEARCH_DAILY_BUILDS", "15"))

_symbols_lock = threading.Lock()
_symbols: dict = {"at": 0.0, "rows": [], "set": frozenset()}


def _securities(conn) -> dict:
    with _symbols_lock:
        if time.time() - _symbols["at"] > 86400 or not _symbols["rows"]:
            rows = store.all_securities(conn)
            _symbols.update(at=time.time(), rows=[[r["symbol"], r["name"]] for r in rows],
                            set=frozenset(r["symbol"] for r in rows))  # fmt: skip
        return _symbols


def _symbol(conn, raw: str) -> str:
    sym = raw.strip().upper()
    if sym not in _securities(conn)["set"]:
        raise HTTPException(404, detail=f"{sym} is not an NSE equity symbol")
    return sym


def _response(conn, sym: str) -> DossierResponse:
    row = store.get_dossier_row(conn, sym)
    job = store.active_job(conn, sym) or store.latest_job(conn, sym)
    return DossierResponse(
        symbol=sym,
        dossier=store.load_dossier(row),
        job=store.job_model(conn, job) if job else None,
        dossier_version=row["version"] if row else 0,
    )


@router.get("/symbols")
def symbols():
    with connect() as conn:
        return {"symbols": _securities(conn)["rows"]}


@router.get("/jobs/{job_id}")
def job(job_id: int):
    with connect() as conn:
        row = store.get_job(conn, job_id)
        if not row:
            raise HTTPException(404, detail="no such job")
        j = store.job_model(conn, row).model_dump(mode="json")
        d = store.get_dossier_row(conn, row["symbol"])
        return {**j, "dossier_version": d["version"] if d else 0}


@router.get("/{symbol}")
def get_dossier(symbol: str):
    with connect() as conn:
        sym = _symbol(conn, symbol)
        resp = _response(conn, sym)
        if resp.dossier:
            store.touch_opened(conn, sym)
        return resp.model_dump(mode="json")


@router.post("/{symbol}/build")
def build(symbol: str, force: bool = Query(False, description="Rebuild even if the dossier is fresh")):
    from finn.research.jobs import Worker

    with connect() as conn:
        sym = _symbol(conn, symbol)
        active = store.active_job(conn, sym)
        if active:
            return _response(conn, sym).model_dump(mode="json")
        row = store.get_dossier_row(conn, sym)
        current = store.load_dossier(row)
        if current and not force and row["status"] == "complete" and now_utc() - row["built_at"] < FRESH_FOR:
            return _response(conn, sym).model_dump(mode="json")
        if current is None:  # first-time builds spend model quota; cap them per IST day
            if store.count_requests_today(conn, "build") >= DAILY_FIRST_BUILDS:
                raise HTTPException(
                    429, detail="FINN has built its daily quota of new dossiers. Try again after midnight IST."
                )
            store.record_request(conn, sym, "build")
        store.enqueue(conn, sym, "requested", priority=10)
        Worker.poke()
        return _response(conn, sym).model_dump(mode="json")


class AskIn(BaseModel):
    question: str = Field(min_length=3, max_length=300)


@router.post("/{symbol}/ask")
def ask(symbol: str, body: AskIn):
    with connect() as conn:
        sym = _symbol(conn, symbol)
        try:
            from finn.research.ask import answer
        except ImportError:
            return AskAnswer(status="unavailable", question=body.question).model_dump(mode="json")
        return answer(conn, sym, body.question).model_dump(mode="json")
