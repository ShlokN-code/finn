"""The one door to every model (CLAUDE.md: routing module with tiers, caching and cost logging).

    router = Router.default(log=PostgresLLMLog(conn))
    result = router.run("cheap", req)      # → LLMResult, or raises LLMUnavailable

- Cache: by content hash (purpose + model + prompt + schema + PDF hash). A hit costs nothing and skips limits.
- Limits: per-provider requests/minute (sleeps) and requests/day (counted from the log, so separate job runs
  share one budget). Defaults are conservative for free tiers; override with <PROVIDER>_RPM / <PROVIDER>_RPD.
- Fallback chain per tier: Gemini → Groq (text only; skipped when the request needs the PDF) → LLMUnavailable,
  which callers turn into an honest "unclassified"/"not found" state — never a guess.
- Every call (ok or not) is logged with tokens, latency and an estimated USD cost.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Protocol

from finn.llm.base import LLMRequest, LLMResult, Provider, ProviderError, QuotaExceeded, Tier

log = logging.getLogger("finn.llm")

DEFAULT_LIMITS = {"gemini": (10, 400), "groq": (20, 800)}  # (requests/min, requests/day) — conservative


class LLMUnavailable(RuntimeError):
    """No provider could answer (no key, quota exhausted, or errors). Callers degrade honestly."""


class LLMLog(Protocol):
    def get_cached(self, content_hash: str) -> dict | None: ...

    def record(self, row: dict) -> None: ...

    def count_today(self, provider: str) -> int: ...


@dataclass
class MemoryLLMLog:
    """In-process log (tests, dry runs without a DB)."""

    rows: list[dict] = field(default_factory=list)

    def get_cached(self, content_hash: str) -> dict | None:
        for r in reversed(self.rows):
            if r["content_hash"] == content_hash and r["ok"]:
                return r
        return None

    def record(self, row: dict) -> None:
        self.rows.append(row)

    def count_today(self, provider: str) -> int:
        return sum(1 for r in self.rows if r["provider"] == provider and not r.get("cached"))


class PostgresLLMLog:
    """llm_calls table: cache + token/cost log. The day boundary is midnight Pacific (Gemini's RPD reset)."""

    def __init__(self, conn):
        self.conn = conn

    def get_cached(self, content_hash: str) -> dict | None:
        return self.conn.execute(
            "select provider, model, response, tokens_in, tokens_out from public.llm_calls "
            "where content_hash = %s and ok order by id desc limit 1",
            (content_hash,),
        ).fetchone()

    def record(self, row: dict) -> None:
        from psycopg.types.json import Jsonb

        self.conn.execute(
            "insert into public.llm_calls (content_hash, provider, model, tier, purpose, request, response, ok, "
            "error, tokens_in, tokens_out, est_cost_usd, latency_ms) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "on conflict do nothing",
            (
                row["content_hash"], row["provider"], row["model"], row["tier"], row["purpose"],
                Jsonb(row["request"]), Jsonb(row.get("response")), row["ok"], row.get("error"),
                row.get("tokens_in"), row.get("tokens_out"), row.get("est_cost_usd"), row.get("latency_ms"),
            ),
        )  # fmt: skip

    def count_today(self, provider: str) -> int:
        r = self.conn.execute(
            "select count(*) as n from public.llm_calls where provider = %s and created_at >= "
            "(date_trunc('day', now() at time zone 'America/Los_Angeles') at time zone 'America/Los_Angeles')",
            (provider,),
        ).fetchone()
        return int(r["n"])


class _Limiter:
    def __init__(self, rpm: int, rpd: int):
        self.rpm, self.rpd = rpm, rpd
        self.hits: deque[float] = deque()

    def wait(self) -> None:
        now = time.monotonic()
        while self.hits and now - self.hits[0] > 60:
            self.hits.popleft()
        if len(self.hits) >= self.rpm:
            time.sleep(60 - (now - self.hits[0]) + 0.5)
        self.hits.append(time.monotonic())


@dataclass
class Stats:
    calls: int = 0
    cache_hits: int = 0
    failures: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    est_cost_usd: float = 0.0
    by_provider: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {**self.__dict__, "est_cost_usd": round(self.est_cost_usd, 6)}


class Router:
    def __init__(self, providers: list[Provider], log: LLMLog, limits: dict[str, tuple[int, int]] | None = None):
        self.providers = providers
        self.log = log
        self.stats = Stats()
        self._limiters: dict[str, _Limiter] = {}
        self._exhausted: set[str] = set()
        lim = {**DEFAULT_LIMITS, **(limits or {})}
        for p in providers:
            rpm, rpd = lim.get(p.name, (10, 200))
            rpm = int(os.environ.get(f"{p.name.upper()}_RPM", rpm))
            rpd = int(os.environ.get(f"{p.name.upper()}_RPD", rpd))
            self._limiters[p.name] = _Limiter(rpm, rpd)

    @classmethod
    def default(cls, log: LLMLog) -> Router:
        from finn.llm.gemini import Gemini
        from finn.llm.groq import Groq

        providers = [p for p in (Gemini(), Groq()) if p.available()]
        return cls(providers, log)

    def run(self, tier: Tier, req: LLMRequest) -> LLMResult:
        errors: list[str] = []
        for p in self.providers:
            model = p.model_for(tier)
            if model is None:
                continue
            if req.pdf_required and not p.supports_pdf():
                errors.append(f"{p.name}: needs PDF")
                continue
            sendable = req if (p.supports_pdf() or not req.pdf) else _without_pdf(req)
            key = sendable.content_hash(model)
            hit = self.log.get_cached(key)
            if hit:
                self.stats.cache_hits += 1
                resp = hit["response"]
                data = resp if isinstance(resp, dict) else json.loads(resp)
                return LLMResult(
                    data, hit["provider"], hit["model"], hit.get("tokens_in"), hit.get("tokens_out"), cached=True
                )
            if p.name in self._exhausted:
                errors.append(f"{p.name}: quota exhausted earlier in this run")
                continue
            lim = self._limiters[p.name]
            if self.log.count_today(p.name) >= lim.rpd:
                self._exhausted.add(p.name)
                errors.append(f"{p.name}: daily budget {lim.rpd} reached")
                continue
            lim.wait()
            row = {
                "content_hash": key, "provider": p.name, "model": model, "tier": tier, "purpose": req.purpose,
                "request": {"system": req.system, "prompt": req.prompt, "pdf_sha256": _pdf_hash(sendable.pdf)},
            }  # fmt: skip
            self.stats.calls += 1
            try:
                res = p.generate(sendable, model)
            except QuotaExceeded as e:
                self._exhausted.add(p.name)
                self.stats.failures += 1
                self.log.record({**row, "ok": False, "error": str(e)[:500]})
                errors.append(f"{p.name}: {e}")
                continue
            except ProviderError as e:
                self.stats.failures += 1
                self.log.record({**row, "ok": False, "error": str(e)[:500]})
                errors.append(f"{p.name}: {e}")
                continue
            pin, pout = p.price(model)
            cost = ((res.tokens_in or 0) * pin + (res.tokens_out or 0) * pout) / 1e6
            self.stats.tokens_in += res.tokens_in or 0
            self.stats.tokens_out += res.tokens_out or 0
            self.stats.est_cost_usd += cost
            self.stats.by_provider[p.name] = self.stats.by_provider.get(p.name, 0) + 1
            self.log.record(
                {
                    **row,
                    "ok": True,
                    "response": res.data,
                    "tokens_in": res.tokens_in,
                    "tokens_out": res.tokens_out,
                    "est_cost_usd": cost,
                    "latency_ms": res.latency_ms,
                }
            )
            log.info(
                "llm %s/%s %s in=%s out=%s $%.6f %sms",
                p.name,
                model,
                req.purpose,
                res.tokens_in,
                res.tokens_out,
                cost,
                res.latency_ms,
            )
            return res
        raise LLMUnavailable("; ".join(errors) or "no LLM provider configured")


def _without_pdf(req: LLMRequest) -> LLMRequest:
    return LLMRequest(req.purpose, req.system, req.prompt, req.schema, None, False, req.max_output_tokens)


def _pdf_hash(pdf: bytes | None) -> str | None:
    import hashlib

    return hashlib.sha256(pdf).hexdigest() if pdf else None
