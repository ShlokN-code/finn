"""The one door to every model (CLAUDE.md: routing module with tiers, caching and cost logging).

    router = Router.default(log=PostgresLLMLog(conn))
    result = router.run("cheap", req)      # → LLMResult, or raises LLMUnavailable

- Cache: by content hash (purpose + model + prompt + schema + PDF hash). A hit costs nothing and skips limits.
- Limits are per MODEL (each free-tier model has its own quota): requests/minute and tokens/minute (sleeps), and
  requests/day counted from the log, so the API, its worker and job runs share one budget. Limiters are
  process-wide and thread-safe. A per-day 429 retires only that model for the run, never the whole provider.
- Research lane: purposes starting 'research.' also share daily caps (RESEARCH_CHEAP_RPD, RESEARCH_ASK_RPD) and a
  lower cheap-tier TPM, so dossier builds can never starve push-side classification.
- Retries: a 5xx/network error or a per-minute 429 is retried with exponential backoff (2, 4, 8, 16 s) before
  moving on; a per-day 429 or our own daily budget marks the provider exhausted for the run.
- Strong tier = Gemini's chain (GEMINI_MODEL_STRONG, then GEMINI_MODEL_STRONG_FALLBACKS); never Flash-Lite and
  never Groq. LLMResult.model names the model that actually answered.
- Fallback chain per tier: Gemini → Groq (text only: a PDF is replaced by its text, extracted locally; a
  scanned PDF with no text layer can't go to Groq) → LLMUnavailable, which callers turn into an honest
  "unclassified"/"not found" state — never a guess.
- Every call (ok or not) is logged with tokens, latency and an estimated USD cost.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import deque
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Literal, Protocol

from finn.llm.base import LLMRequest, LLMResult, Provider, ProviderError, QuotaExceeded, Tier, TransientError

log = logging.getLogger("finn.llm")

# (requests/min, requests/day) per provider — the push side's long-standing defaults (GEMINI_RPM/RPD override).
DEFAULT_LIMITS = {"gemini": (10, 400), "groq": (20, 800)}
# Per-model free-tier limits (rpm, rpd, tpm), product owner's AI Studio dashboard 11 Nov 2026. Flash-Lite's RPD is
# shared with the push side; non-Lite Flash models are the strong chain (5 RPM / 20 RPD each).
FLASH_LIMITS = (5, 20, 240_000)
LITE_TPM = 240_000
GROQ_TPM = 8_000
GROQ_MAX_TOKENS = 6_000  # a request must fit inside Groq's free 8K tokens/min, with room for the reply
RESEARCH_TPM = 150_000  # research's share of Flash-Lite's 250K TPM
BACKOFF_S = (2.0, 4.0, 8.0, 16.0)  # pauses between attempts on one provider (~30 s worst case)
PDF_TEXT_PAGES = 12


class LLMUnavailable(RuntimeError):
    """No provider could answer (no key, quota exhausted, or errors). Callers degrade honestly.

    kind: 'quota' (daily quota or our own cap — retry after `retry_after`), 'transient' (busy/errors — retry soon),
    'too_large' (no configured model can take a request this big), 'config' (no provider/key)."""

    def __init__(self, msg: str, kind: Literal["quota", "transient", "too_large", "config"] = "transient",
                 retry_after: datetime | None = None):  # fmt: skip
        super().__init__(msg)
        self.kind, self.retry_after = kind, retry_after


class LLMLog(Protocol):
    def get_cached(self, content_hash: str) -> dict | None: ...

    def record(self, row: dict) -> None: ...

    def count_today(self, provider: str, model: str | None = None, purpose_prefix: str | None = None) -> int: ...


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

    def count_today(self, provider: str, model: str | None = None, purpose_prefix: str | None = None) -> int:
        return sum(
            1
            for r in self.rows
            if r["provider"] == provider
            and (model is None or r["model"] == model)
            and (purpose_prefix is None or r["purpose"].startswith(purpose_prefix))
        )


class PostgresLLMLog:
    """llm_calls table: cache + token/cost log. The day boundary is midnight Pacific (Gemini's RPD reset).
    Daily counts include failed attempts: Google counted 29 timed-out/503 calls against gemini-3.8-flash's 20 a day
    (11 Nov 2026), so only counting successes over-spends the quota."""

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

    def count_today(self, provider: str, model: str | None = None, purpose_prefix: str | None = None) -> int:
        # A model matches itself and its served versions ('gemini-3.8-flash-001') — never a longer sibling name:
        # a plain prefix made 'gemini-3.5-flash' count every 'gemini-3.5-flash-lite' call against its own 20/day.
        r = self.conn.execute(
            "select count(*) as n from public.llm_calls where provider = %s and created_at >= "
            "(date_trunc('day', now() at time zone 'America/Los_Angeles') at time zone 'America/Los_Angeles') "
            "and (%s::text is null or model = %s or model ~ ('^' || regexp_replace(%s, '([.+*?^$()])', '\\\1', 'g') "
            "|| '-[0-9]+$')) and (%s::text is null or purpose like %s || '%%')",
            (provider, model, model, model, purpose_prefix, purpose_prefix),
        ).fetchone()
        return int(r["n"])


class _Limiter:
    """Requests/min and tokens/min for one model, shared by every thread in the process. The wait is computed
    under the lock and slept outside it, so other models' callers are never blocked."""

    def __init__(self, rpm: int, rpd: int, tpm: int | None = None):
        self.rpm, self.rpd, self.tpm = rpm, rpd, tpm
        self.hits: deque[tuple[float, int]] = deque()  # (time, estimated tokens)
        self.lock = threading.Lock()

    def wait(self, tokens: int = 0, tpm_cap: int | None = None, sleep=time.sleep) -> None:
        cap = min(x for x in (self.tpm, tpm_cap) if x) if (self.tpm or tpm_cap) else None
        while True:
            with self.lock:
                now = time.monotonic()
                while self.hits and now - self.hits[0][0] > 60:
                    self.hits.popleft()
                pause = 0.0
                if len(self.hits) >= self.rpm:
                    pause = 60 - (now - self.hits[0][0]) + 0.5
                elif cap and self.hits and sum(t for _, t in self.hits) + tokens > cap:
                    pause = 60 - (now - self.hits[0][0]) + 0.5
                if pause <= 0:
                    self.hits.append((now, tokens))
                    return
            sleep(pause)


# A model in a fallback chain that keeps failing (overloaded: 503s, timeouts) is skipped for a while so the next
# model answers at once instead of after minutes of retries. Process-wide, like the limiters.
COOLDOWN_S = 600
CHAIN_ATTEMPTS = 2  # attempts on a model that has a fallback after it (the last model keeps the full backoff)
_COOLING: dict[tuple[str, str], float] = {}

_LIMITERS: dict[tuple[str, str], _Limiter] = {}
_LIMITERS_LOCK = threading.Lock()


def reset_limiters() -> None:
    """Forget per-minute history (tests)."""
    with _LIMITERS_LOCK:
        _LIMITERS.clear()
        _COOLING.clear()


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def research_caps() -> dict[str, int]:
    """Daily caps for purposes in the research lane (prefix → max calls per Pacific day, across all models)."""
    return {
        "research.ask": _env_int("RESEARCH_ASK_RPD", 40),
        "research.cheap": _env_int("RESEARCH_CHEAP_RPD", 220),
        "research.strong": _env_int("RESEARCH_STRONG_RPD", 80),  # 4 strong models × 20 a day
    }


@dataclass
class Stats:
    calls: int = 0
    cache_hits: int = 0
    failures: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    est_cost_usd: float = 0.0
    by_provider: dict[str, int] = field(default_factory=dict)
    by_model: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {**self.__dict__, "est_cost_usd": round(self.est_cost_usd, 6), "by_model": dict(self.by_model)}


class Router:
    def __init__(self, providers: list[Provider], log: LLMLog, limits: dict | None = None,
                 sleep=time.sleep):  # fmt: skip
        """limits: optional overrides keyed by provider name or (provider, model) → (rpm, rpd[, tpm])."""
        self.providers = providers
        self._sleep = sleep
        self._pdf_text: dict[str | None, str] = {}
        self.log = log
        self.stats = Stats()
        self._limits = limits or {}
        self._exhausted: set[tuple[str, str]] = set()

    @classmethod
    def default(cls, log: LLMLog) -> Router:
        from finn.llm.gemini import Gemini
        from finn.llm.groq import Groq

        providers = [p for p in (Gemini(), Groq()) if p.available()]
        return cls(providers, log)

    # --- limits ---------------------------------------------------------------------------------

    def _limiter(self, provider: str, model: str) -> _Limiter:
        key = (provider, model)
        with _LIMITERS_LOCK:
            if key not in _LIMITERS:
                _LIMITERS[key] = _Limiter(*self._limits_for(provider, model))
            return _LIMITERS[key]

    def _limits_for(self, provider: str, model: str) -> tuple[int, int, int | None]:
        o = self._limits.get((provider, model)) or self._limits.get(provider)
        if o:
            return (o[0], o[1], o[2] if len(o) > 2 else None)
        if provider == "gemini" and "lite" not in model and "flash" in model:
            rpm, rpd, tpm = FLASH_LIMITS
            return (_env_int("GEMINI_STRONG_RPM", rpm), _env_int("GEMINI_STRONG_RPD", rpd), tpm)
        rpm, rpd = DEFAULT_LIMITS.get(provider, (10, 200))
        tpm = LITE_TPM if provider == "gemini" else GROQ_TPM if provider == "groq" else None
        up = provider.upper()
        return (_env_int(f"{up}_RPM", rpm), _env_int(f"{up}_RPD", rpd), tpm)

    @staticmethod
    def _lane(req: LLMRequest, tier: Tier) -> str | None:
        if not req.purpose.startswith("research."):
            return None
        if req.purpose.startswith("research.ask"):
            return "research.ask"
        return f"research.{tier}"

    def _lane_used(self, lane: str, tier: Tier) -> int:
        # Lane counts are across providers; ask counts by purpose prefix, cheap/strong by every research purpose
        # of that tier (purposes encode the tier: research.ask*, research.map*/research.ar* cheap, research.judge*/
        # research.reduce* strong).
        prefixes = {"research.ask": ["research.ask"], "research.cheap": ["research.map", "research.ar",
                    "research.ask"], "research.strong": ["research.judge", "research.reduce"]}[lane]  # fmt: skip
        return sum(self.log.count_today(p.name, None, pre) for p in self.providers for pre in prefixes)

    # --- run --------------------------------------------------------------------------------------

    def run(self, tier: Tier, req: LLMRequest) -> LLMResult:
        from finn.calendar import next_quota_reset

        errors: list[str] = []
        kinds: set[str] = set()
        lane = self._lane(req, tier)
        if lane:
            cap = research_caps()[lane]
            if self._lane_used(lane, tier) >= cap:
                # Cached answers are still served below; only new calls are refused.
                hit = self._cached(tier, req)
                if hit:
                    return hit
                raise LLMUnavailable(f"research daily cap {cap} reached ({lane})", "quota", next_quota_reset())
        chain = [(p, m) for p in self.providers for m in _models(p, tier)]
        for idx, (p, model) in enumerate(chain):
            sendable = req if (p.supports_pdf() or not req.pdf) else self._as_text(req)
            if sendable is None:
                errors.append(f"{p.name}: needs the PDF and it has no text layer")
                kinds.add("too_large")
                continue
            key = sendable.content_hash(model)
            hit = self.log.get_cached(key)
            if hit:
                self.stats.cache_hits += 1
                resp = hit["response"]
                data = resp if isinstance(resp, dict) else json.loads(resp)
                return LLMResult(
                    data, hit["provider"], hit["model"], hit.get("tokens_in"), hit.get("tokens_out"), cached=True
                )
            if p.name == "groq" and sendable.est_tokens() > GROQ_MAX_TOKENS:
                errors.append(f"groq: request too large for its free tier (~{sendable.est_tokens()} tokens)")
                kinds.add("too_large")
                continue
            if (p.name, model) in self._exhausted:
                errors.append(f"{model}: quota exhausted earlier in this run")
                kinds.add("quota")
                continue
            lim = self._limiter(p.name, model)
            if self.log.count_today(p.name, model) >= lim.rpd:
                self._exhausted.add((p.name, model))
                errors.append(f"{model}: daily budget {lim.rpd} reached")
                kinds.add("quota")
                continue
            # only the strong chain short-circuits; the push side keeps full retries on Flash-Lite before Groq
            has_next = tier == "strong" and idx < len(chain) - 1
            if has_next and _COOLING.get((p.name, model), 0) > time.monotonic():
                errors.append(f"{model}: skipped — overloaded in the last {COOLDOWN_S // 60} min")
                kinds.add("transient")
                continue
            lim.wait(sendable.est_tokens(), RESEARCH_TPM if lane and tier == "cheap" else None, self._sleep)
            row = {
                "content_hash": key, "provider": p.name, "model": model, "tier": tier, "purpose": req.purpose,
                "request": {"system": req.system, "prompt": req.prompt, "pdf_sha256": _pdf_hash(sendable.pdf),
                            "document_sha256": sendable.document_sha(), "tags": req.tags},
            }  # fmt: skip
            res = self._attempt(p, model, sendable, row, errors, kinds, CHAIN_ATTEMPTS if has_next else None)
            if res is None:
                if has_next and "transient" in kinds:
                    _COOLING[(p.name, model)] = time.monotonic() + COOLDOWN_S
                continue
            pin, pout = p.price(model)
            cost = ((res.tokens_in or 0) * pin + (res.tokens_out or 0) * pout) / 1e6
            self.stats.tokens_in += res.tokens_in or 0
            self.stats.tokens_out += res.tokens_out or 0
            self.stats.est_cost_usd += cost
            self.stats.by_provider[p.name] = self.stats.by_provider.get(p.name, 0) + 1
            self.stats.by_model[res.model] = self.stats.by_model.get(res.model, 0) + 1
            self.log.record(
                {
                    **row,
                    "model": res.model or model,
                    "ok": True,
                    "response": res.data,
                    "tokens_in": res.tokens_in,
                    "tokens_out": res.tokens_out,
                    "est_cost_usd": cost,
                    "latency_ms": res.latency_ms,
                }
            )
            log.info("llm %s/%s %s in=%s out=%s $%.6f %sms", p.name, res.model, req.purpose, res.tokens_in,
                     res.tokens_out, cost, res.latency_ms)  # fmt: skip
            return res
        if not self.providers:
            raise LLMUnavailable("no LLM provider configured", "config")
        kind = "quota" if kinds == {"quota"} or ("quota" in kinds and "transient" not in kinds) else (
            "too_large" if kinds == {"too_large"} else "transient")  # fmt: skip
        raise LLMUnavailable("; ".join(errors) or "no LLM provider configured", kind,
                             next_quota_reset() if kind == "quota" else None)  # fmt: skip

    def _cached(self, tier: Tier, req: LLMRequest) -> LLMResult | None:
        for p in self.providers:
            for model in _models(p, tier):
                hit = self.log.get_cached(req.content_hash(model))
                if hit:
                    self.stats.cache_hits += 1
                    resp = hit["response"]
                    data = resp if isinstance(resp, dict) else json.loads(resp)
                    return LLMResult(data, hit["provider"], hit["model"], hit.get("tokens_in"),
                                     hit.get("tokens_out"), cached=True)  # fmt: skip
        return None

    def _attempt(self, p: Provider, model: str, req: LLMRequest, row: dict, errors: list[str],
                 kinds: set[str], max_attempts: int | None = None) -> LLMResult | None:  # fmt: skip
        """One model, with exponential backoff on transient errors and per-minute 429s."""
        pauses = (*BACKOFF_S, None) if max_attempts is None else (*BACKOFF_S[: max_attempts - 1], None)
        for attempt, pause in enumerate(pauses, start=1):
            self.stats.calls += 1
            log.info("llm call %s/%s %s pdf=%s attempt %d", p.name, model, req.purpose, bool(req.pdf), attempt)
            try:
                return p.generate(req, model)
            except (QuotaExceeded, TransientError) as e:
                self.stats.failures += 1
                self.log.record({**row, "ok": False, "error": f"attempt {attempt}: {e}"[:500]})
                daily = isinstance(e, QuotaExceeded) and e.daily
                if daily or pause is None:
                    if daily:
                        self._exhausted.add((p.name, model))
                    kinds.add("quota" if daily else "transient")
                    errors.append(f"{model}: {e}" + ("" if daily else f" (after {attempt} attempts)"))
                    return None
                self._sleep(pause)
            except ProviderError as e:  # bad JSON, 4xx, truncated output: retrying the same request won't help
                self.stats.failures += 1
                self.log.record({**row, "ok": False, "error": str(e)[:500]})
                kinds.add("transient")
                errors.append(f"{model}: {e}")
                return None
        return None

    def _as_text(self, req: LLMRequest) -> LLMRequest | None:
        """The request for a text-only provider: the PDF replaced by its text layer, extracted locally. None when
        the PDF is required and has no text (scanned) — that request can only go to a PDF-capable model."""
        from finn.citations import pdf_text

        key = _pdf_hash(req.pdf)
        if key not in self._pdf_text:
            self._pdf_text[key] = pdf_text(req.pdf, max_pages=PDF_TEXT_PAGES)[0].strip()
        text = self._pdf_text[key]
        if not text:
            return None if req.pdf_required else _without_pdf(req)
        prompt = f"{req.prompt}\n\nDocument text (extracted from the attached PDF):\n{text[:24000]}"
        return replace(req, prompt=prompt, pdf=None, pdf_required=False)


def _models(p: Provider, tier: Tier) -> list[str]:
    chain = getattr(p, "models_for", None)
    if chain:
        return chain(tier)
    m = p.model_for(tier)
    return [m] if m else []


def _without_pdf(req: LLMRequest) -> LLMRequest:
    return replace(req, pdf=None, pdf_required=False)


def _pdf_hash(pdf: bytes | None) -> str | None:
    import hashlib

    return hashlib.sha256(pdf).hexdigest() if pdf else None
