"""Groq (free tier, OpenAI-compatible) — optional text-only fallback when Gemini's quota is exhausted."""

from __future__ import annotations

import json
import os
import time

import requests

from finn.llm.base import LLMRequest, LLMResult, ProviderError, QuotaExceeded, Tier, TransientError

BASE = "https://api.groq.com/openai/v1"
# llama-3.1-8b-instant was retired (404 model_not_found, Nov 2026). Override with GROQ_MODEL.
DEFAULT_MODEL = "qwen/qwen3.8-27b"


class Groq:
    name = "groq"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")

    def available(self) -> bool:
        return bool(self.api_key)

    def model_for(self, tier: Tier) -> str | None:
        return (os.environ.get("GROQ_MODEL") or DEFAULT_MODEL) if tier == "cheap" else None

    def supports_pdf(self) -> bool:
        return False

    def price(self, model: str) -> tuple[float, float]:
        return (0.05, 0.08)  # rough list price; free tier bills nothing

    def generate(self, req: LLMRequest, model: str) -> LLMResult:
        schema_hint = json.dumps(req.schema)
        body = {
            "model": model,
            "temperature": 0,
            "max_tokens": req.max_output_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": f"{req.system}\nReply with one JSON object matching: {schema_hint}"},
                {"role": "user", "content": req.prompt},
            ],
        }
        t0 = time.perf_counter()
        try:
            r = requests.post(
                f"{BASE}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=body,
                timeout=60,
            )
        except requests.RequestException as e:
            raise TransientError(f"groq network error: {type(e).__name__}") from e
        ms = round((time.perf_counter() - t0) * 1000)
        if r.status_code == 429:  # Groq's free-tier limits are mostly per minute / per day of tokens
            raise QuotaExceeded(f"groq 429: {r.text[:200]}", daily="per day" in r.text.lower())
        if r.status_code >= 500:
            raise TransientError(f"groq HTTP {r.status_code}: {r.text[:300]}")
        if not r.ok:
            raise ProviderError(f"groq HTTP {r.status_code}: {r.text[:300]}")
        payload = r.json()
        try:
            text = payload["choices"][0]["message"]["content"]
            data = json.loads(text)
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise ProviderError(f"groq returned no parseable JSON: {str(payload)[:300]}") from e
        usage = payload.get("usage", {})
        return LLMResult(data, self.name, model, usage.get("prompt_tokens"), usage.get("completion_tokens"), ms,
                         raw_text=text)  # fmt: skip
