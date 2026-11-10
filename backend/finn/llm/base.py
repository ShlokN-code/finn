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
    max_output_tokens: int = 512

    def content_hash(self, model: str) -> str:
        h = hashlib.sha256()
        for part in (self.purpose, model, self.system, self.prompt, json.dumps(self.schema, sort_keys=True)):
            h.update(part.encode())
            h.update(b"\x00")
        if self.pdf:
            h.update(hashlib.sha256(self.pdf).digest())
        return h.hexdigest()


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

    def supports_pdf(self) -> bool: ...

    def generate(self, req: LLMRequest, model: str) -> LLMResult: ...

    # USD per 1M tokens (in, out) for the cost log; free tiers still log the list-price estimate.
    def price(self, model: str) -> tuple[float, float]: ...
