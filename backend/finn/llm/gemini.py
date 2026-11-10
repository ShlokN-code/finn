"""Google Gemini (AI Studio free tier) over REST generateContent.

Models come from env (GEMINI_MODEL_CHEAP / GEMINI_MODEL_STRONG) so they can be bumped without code changes;
`python -m finn.llm.check` lists what the key can actually use. PDFs go inline (application/pdf).
Free-tier inputs may be used by Google to improve its products — acceptable because FINN only sends public
exchange filings (DECISIONS.md).
"""

from __future__ import annotations

import base64
import json
import os
import time

import requests

from finn.llm.base import LLMRequest, LLMResult, ProviderError, QuotaExceeded, Tier, TransientError

BASE = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_CHEAP = "gemini-3.5-flash-lite"
DEFAULT_STRONG = "gemini-3.8-flash"
# Paid-tier list prices (USD / 1M tokens) — used only for the cost estimate in the log; free tier bills nothing.
PRICES = {"flash-lite": (0.30, 2.50), "flash": (0.75, 3.75)}


class Gemini:
    name = "gemini"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")

    def available(self) -> bool:
        return bool(self.api_key)

    def model_for(self, tier: Tier) -> str | None:
        if tier == "cheap":
            return os.environ.get("GEMINI_MODEL_CHEAP") or DEFAULT_CHEAP
        return os.environ.get("GEMINI_MODEL_STRONG") or DEFAULT_STRONG

    def supports_pdf(self) -> bool:
        return True

    def price(self, model: str) -> tuple[float, float]:
        return PRICES["flash-lite"] if "lite" in model else PRICES["flash"]

    def generate(self, req: LLMRequest, model: str) -> LLMResult:
        parts: list[dict] = []
        if req.pdf:
            parts.append({"inline_data": {"mime_type": "application/pdf", "data": base64.b64encode(req.pdf).decode()}})
        parts.append({"text": req.prompt})
        body = {
            "system_instruction": {"parts": [{"text": req.system}]},
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": req.max_output_tokens,
                "responseMimeType": "application/json",
                "responseSchema": req.schema,
            },
        }
        t0 = time.perf_counter()
        try:
            r = requests.post(
                f"{BASE}/models/{model}:generateContent",
                headers={"x-goog-api-key": self.api_key or "", "Content-Type": "application/json"},
                json=body,
                timeout=60,
            )
        except requests.RequestException as e:
            raise TransientError(f"gemini network error: {type(e).__name__}") from e
        ms = round((time.perf_counter() - t0) * 1000)
        if r.status_code == 429:  # per-day quotas name it ("PerDay"); otherwise a per-minute limit
            raise QuotaExceeded(f"gemini 429: {_short(r.text)}", daily="perday" in r.text.lower().replace("_", ""))
        if r.status_code >= 500:  # 503 "model is experiencing high demand" is transient; the router retries
            raise TransientError(f"gemini HTTP {r.status_code}: {_short(r.text)}")
        if not r.ok:
            raise ProviderError(f"gemini HTTP {r.status_code}: {_short(r.text)}")
        payload = r.json()
        try:
            text = "".join(p.get("text", "") for p in payload["candidates"][0]["content"]["parts"])
            data = json.loads(text)
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise ProviderError(f"gemini returned no parseable JSON: {str(payload)[:300]}") from e
        usage = payload.get("usageMetadata", {})
        return LLMResult(
            data=data,
            provider=self.name,
            model=payload.get("modelVersion") or model,
            tokens_in=usage.get("promptTokenCount"),
            tokens_out=(usage.get("candidatesTokenCount") or 0) + (usage.get("thoughtsTokenCount") or 0),
            latency_ms=ms,
            raw_text=text,
        )

    def list_models(self) -> list[str]:
        r = requests.get(f"{BASE}/models", headers={"x-goog-api-key": self.api_key or ""}, timeout=30)
        r.raise_for_status()
        return [
            m["name"].removeprefix("models/")
            for m in r.json().get("models", [])
            if "generateContent" in m.get("supportedGenerationMethods", [])
        ]


def _short(text: str) -> str:
    """One-line error text (Gemini returns pretty-printed JSON errors)."""
    try:
        return json.loads(text)["error"]["message"][:200]
    except (ValueError, KeyError, TypeError):
        return " ".join(text.split())[:200]
