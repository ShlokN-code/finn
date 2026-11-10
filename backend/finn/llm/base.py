"""Provider-agnostic LLM interface.

A provider turns an LLMRequest (text, optional PDF bytes, JSON schema) into an LLMResult with token counts.
Routing, caching, rate limiting and cost logging live in finn.llm.router, not in providers.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Literal, Protocol

Tier = Literal["cheap", "strong"]


@dataclass
class LLMRequest:
    purpose: str  # e.g. "classify_filing" — logged, part of the cache key
    system: str
    prompt: str
    schema: dict  # JSON schema of the expected object (OpenAPI-subset: type/properties/enum/required)
    pdf: bytes | None = None  # sent natively where supported; text-only providers skip requests that need it
    pdf_required: bool = False
    max_output_tokens: int = 512  # up to 8192 (research MAP); thinking tokens count against it on Gemini 3.x
    # Long text (a transcript) sent after the prompt. Only its sha256 is logged and hashed into the cache key,
    # so llm_calls never duplicates document text that research_doc_text already stores.
    document_text: str | None = None
    tags: dict = field(default_factory=dict)  # e.g. {"symbol": "INFY", "job_id": 12} — logged, not in the cache key
    timeout_s: float = 60
    thinking_budget: int | None = None  # Gemini thinkingConfig.thinkingBudget (0 = off); None = model default

    def content_hash(self, model: str) -> str:
        h = hashlib.sha256()
        for part in (self.purpose, model, self.system, self.prompt, json.dumps(self.schema, sort_keys=True)):
            h.update(part.encode())
            h.update(b"\x00")
        if self.pdf:
            h.update(hashlib.sha256(self.pdf).digest())
        if self.document_text:
            h.update(b"doc:" + self.document_sha().encode())
        return h.hexdigest()

    def document_sha(self) -> str | None:
        return hashlib.sha256(self.document_text.encode()).hexdigest() if self.document_text else None

    def full_prompt(self) -> str:
        """Prompt as sent: the instructions, then the document (if any) in a fenced block."""
        if not self.document_text:
            return self.prompt
        return f"{self.prompt}\n\n<document>\n{self.document_text}\n</document>"

    def est_tokens(self) -> int:
        """Rough input + output token estimate (≈3.5 chars/token for English filings) for TPM budgeting."""
        chars = len(self.system) + len(self.prompt) + len(self.document_text or "")
        return int(chars / 3.5) + (258 * 20 if self.pdf else 0) + self.max_output_tokens


@dataclass
class LLMResult:
    data: dict
    provider: str
    model: str
    tokens_in: int | None = None
    tokens_out: int | None = None
    latency_ms: int | None = None
    cached: bool = False
    raw_text: str | None = None
    extra: dict = field(default_factory=dict)


class QuotaExceeded(RuntimeError):
    """Provider rate/quota limit hit (HTTP 429). `daily` = the day's quota is gone (router stops using the
    provider for the run); otherwise it's a per-minute limit and the router backs off and retries."""

    def __init__(self, msg: str, daily: bool = True):
        super().__init__(msg)
        self.daily = daily


class ProviderError(RuntimeError):
    """Any other provider failure (bad JSON, 4xx)."""


class TransientError(ProviderError):
    """5xx ("model is experiencing high demand") or a network error: worth retrying after a pause."""


class Provider(Protocol):
    name: str

    def model_for(self, tier: Tier) -> str | None: ...

    # Optional: an ordered fallback chain for the tier (Gemini strong: 3.8 Flash → 3 Flash → 2.5 Flash).
    # Providers without it serve [model_for(tier)].
    # def models_for(self, tier: Tier) -> list[str]: ...

    def supports_pdf(self) -> bool: ...

    def generate(self, req: LLMRequest, model: str) -> LLMResult: ...

    # USD per 1M tokens (in, out) for the cost log; free tiers still log the list-price estimate.
    def price(self, model: str) -> tuple[float, float]: ...
