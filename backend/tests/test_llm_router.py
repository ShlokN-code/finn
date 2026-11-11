import json

import pytest

from finn.llm import LLMRequest, LLMResult, LLMUnavailable, MemoryLLMLog, ProviderError, QuotaExceeded, Router


class Fake:
    def __init__(self, name, *, pdf=True, fail=None, data=None):
        self.name, self._pdf, self.fail, self.data, self.calls = name, pdf, fail, data or {"category": "results"}, []

    def model_for(self, tier):
        return f"{self.name}-{tier}"

    def supports_pdf(self):
        return self._pdf

    def price(self, model):
        return (1.0, 2.0)

    def generate(self, req, model):
        self.calls.append(req)
        if self.fail:
            raise self.fail
        return LLMResult(self.data, self.name, model, tokens_in=1000, tokens_out=100, latency_ms=5)


def req(**kw):
    base = dict(purpose="classify_filing", system="sys", prompt="subject", schema={"type": "object"})
    return LLMRequest(**{**base, **kw})


def test_cache_hit_skips_provider():
    log, g = MemoryLLMLog(), Fake("gemini")
    r = Router([g], log)
    assert r.run("cheap", req()).data == {"category": "results"}
    second = r.run("cheap", req())
    assert second.cached and len(g.calls) == 1
    assert r.stats.cache_hits == 1


def test_cost_logged():
    log = MemoryLLMLog()
    Router([Fake("gemini")], log).run("cheap", req())
    row = log.rows[-1]
    assert row["ok"] and row["tokens_in"] == 1000 and row["est_cost_usd"] == pytest.approx((1000 * 1 + 100 * 2) / 1e6)


def test_quota_falls_back_then_unavailable():
    log = MemoryLLMLog()
    g, q = Fake("gemini", fail=QuotaExceeded("429")), Fake("groq", pdf=False, data={"category": "capex"})
    r = Router([g, q], log)
    assert r.run("cheap", req()).provider == "groq"
    # gemini is now marked exhausted for the run: not called again
    r.run("cheap", req(prompt="other"))
    assert len(g.calls) == 1


def test_pdf_required_skips_text_only_provider():
    r = Router([Fake("groq", pdf=False)], MemoryLLMLog())
    with pytest.raises(LLMUnavailable):
        r.run("cheap", req(pdf=b"%PDF", pdf_required=True))


def test_text_only_provider_gets_request_without_pdf():
    q = Fake("groq", pdf=False)
    Router([q], MemoryLLMLog()).run("cheap", req(pdf=b"%PDF"))
    assert q.calls[0].pdf is None


def test_daily_budget_enforced():
    log = MemoryLLMLog()
    r = Router([Fake("gemini")], log, limits={"gemini": (100, 1)})
    r.run("cheap", req())
    with pytest.raises(LLMUnavailable, match="daily budget"):
        r.run("cheap", req(prompt="new"))


def test_errors_are_logged_and_raise_unavailable():
    log = MemoryLLMLog()
    with pytest.raises(LLMUnavailable):
        Router([Fake("gemini", fail=ProviderError("bad json"))], log).run("cheap", req())
    assert log.rows[-1]["ok"] is False


def test_no_providers():
    with pytest.raises(LLMUnavailable):
        Router([], MemoryLLMLog()).run("cheap", req())


class Flaky(Fake):
    """Fails with the given errors in order, then succeeds."""

    def __init__(self, name, errors, **kw):
        super().__init__(name, **kw)
        self.errors = list(errors)

    def generate(self, req, model):
        self.calls.append(req)
        if self.errors:
            raise self.errors.pop(0)
        return LLMResult(self.data, self.name, model, tokens_in=10, tokens_out=5, latency_ms=5)


def test_transient_errors_back_off_exponentially_then_succeed():
    from finn.llm import TransientError

    pauses = []
    g = Flaky("gemini", [TransientError("503 high demand"), TransientError("503"), QuotaExceeded("429", daily=False)])
    log = MemoryLLMLog()
    r = Router([g], log, sleep=pauses.append)
    assert r.run("cheap", req()).provider == "gemini"
    assert pauses == [2.0, 4.0, 8.0] and len(g.calls) == 4
    assert sum(not row["ok"] for row in log.rows) == 3  # every failed attempt is logged


def test_busy_gemini_falls_back_to_groq_with_locally_extracted_text(monkeypatch):
    from finn import citations
    from finn.llm import TransientError

    monkeypatch.setattr(citations, "pdf_text", lambda pdf, max_pages=6: ("Ms Gopika Pant is appointed.", []))
    pauses = []
    g = Flaky("gemini", [TransientError("503")] * 5)
    q = Fake("groq", pdf=False, data={"people": []})
    r = Router([g, q], MemoryLLMLog(), sleep=pauses.append)
    res = r.run("cheap", req(pdf=b"%PDF-1.7 ...", pdf_required=True))
    assert res.provider == "groq" and len(g.calls) == 5 and pauses == [2.0, 4.0, 8.0, 16.0]
    sent = q.calls[0]
    assert sent.pdf is None and "Ms Gopika Pant is appointed." in sent.prompt
    assert "gemini" not in r._exhausted  # a busy model isn't out of quota: next request tries it again


def test_scanned_pdf_never_goes_to_text_only_provider(monkeypatch):
    from finn import citations

    monkeypatch.setattr(citations, "pdf_text", lambda pdf, max_pages=6: ("", []))
    r = Router([Fake("groq", pdf=False)], MemoryLLMLog(), sleep=lambda s: None)
    with pytest.raises(LLMUnavailable, match="no text layer"):
        r.run("cheap", req(pdf=b"%PDF-scan", pdf_required=True))


def test_daily_quota_is_not_retried():
    pauses = []
    g = Flaky("gemini", [QuotaExceeded("429 PerDay", daily=True)])
    r = Router([g, Fake("groq", pdf=False)], MemoryLLMLog(), sleep=pauses.append)
    assert r.run("cheap", req()).provider == "groq" and pauses == [] and len(g.calls) == 1


# --- Phase 3: per-model quotas, strong chain, research lane, document text ---------------------------------


class Chain(Fake):
    """A provider with a strong-tier chain whose models can fail independently."""

    def __init__(self, name, chain, fails=None, **kw):
        super().__init__(name, **kw)
        self.chain, self.fails = chain, fails or {}

    def models_for(self, tier):
        return self.chain[tier]

    def generate(self, req, model):
        self.calls.append((req, model))
        if model in self.fails:
            raise self.fails[model]
        return LLMResult(self.data, self.name, model, tokens_in=10, tokens_out=5, latency_ms=5)


CHAIN = {"cheap": ["lite"], "strong": ["flash-38", "flash-3", "flash-25"]}


def test_strong_daily_quota_leaves_cheap_alive():
    g = Chain("gemini", CHAIN, fails={"flash-38": QuotaExceeded("429 PerDay", daily=True)})
    r = Router([g], MemoryLLMLog(), sleep=lambda s: None)
    assert r.run("strong", req(purpose="research.judge.v1")).model == "flash-3"
    assert r.run("cheap", req(prompt="cheap one")).model == "lite"


def test_strong_chain_in_order_and_never_lite():
    out = Chain("gemini", CHAIN, fails={m: QuotaExceeded("429 PerDay", daily=True) for m in CHAIN["strong"]})
    r = Router([out], MemoryLLMLog(), sleep=lambda s: None)
    with pytest.raises(LLMUnavailable) as e:
        r.run("strong", req(purpose="research.reduce.v1"))
    assert e.value.kind == "quota" and e.value.retry_after is not None
    assert [m for _, m in out.calls] == ["flash-38", "flash-3", "flash-25"]  # never 'lite'


def test_gemini_strong_chain_from_env(monkeypatch):
    from finn.llm.gemini import Gemini

    monkeypatch.setenv("GEMINI_MODEL_STRONG", "gemini-3.8-flash")
    chain = "gemini-3-flash-preview, gemini-3.5-flash-lite, gemini-2.5-flash"
    monkeypatch.setenv("GEMINI_MODEL_STRONG_FALLBACKS", chain)
    assert Gemini("k").models_for("strong") == ["gemini-3.8-flash", "gemini-3-flash-preview", "gemini-2.5-flash"]


def test_document_text_is_hashed_not_logged_and_tags_stay_out_of_the_key():
    log = MemoryLLMLog()
    g = Fake("gemini")
    r = Router([g], log)
    a = req(document_text="Page 1 text " * 50, tags={"symbol": "INFY"})
    r.run("cheap", a)
    row = log.rows[-1]
    assert "Page 1 text" not in json.dumps(row["request"]) and row["request"]["document_sha256"]
    assert row["request"]["tags"] == {"symbol": "INFY"}
    assert a.content_hash("m") == req(document_text="Page 1 text " * 50, tags={"job_id": 9}).content_hash("m")
    assert a.content_hash("m") != req(document_text="other text").content_hash("m")
    assert "Page 1 text" in g.calls[0].full_prompt()


def test_groq_skipped_when_request_too_large():
    q = Fake("groq", pdf=False)
    with pytest.raises(LLMUnavailable) as e:
        Router([q], MemoryLLMLog()).run("cheap", req(document_text="x" * 40_000))
    assert e.value.kind == "too_large" and q.calls == []


def test_research_lane_cap(monkeypatch):
    monkeypatch.setenv("RESEARCH_CHEAP_RPD", "2")
    r = Router([Fake("gemini")], MemoryLLMLog())
    r.run("cheap", req(purpose="research.map_transcript.v1", prompt="a"))
    r.run("cheap", req(purpose="research.map_transcript.v1", prompt="b"))
    assert r.run("cheap", req(purpose="research.map_transcript.v1", prompt="a")).cached  # cache still served
    with pytest.raises(LLMUnavailable) as e:
        r.run("cheap", req(purpose="research.map_transcript.v1", prompt="c"))
    assert e.value.kind == "quota"
    assert r.run("cheap", req(purpose="classify_filing", prompt="push side")).provider == "gemini"  # push unaffected


def test_truncated_gemini_output_is_an_error(monkeypatch):
    from finn.llm import gemini

    class Resp:
        status_code, ok, text = 200, True, ""

        def json(self):
            return {"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": [{"text": '{"a": ['}]}}]}

    monkeypatch.setattr(gemini.requests, "post", lambda *a, **k: Resp())
    with pytest.raises(ProviderError, match="truncated"):
        gemini.Gemini("k").generate(req(), "gemini-3.5-flash-lite")


def test_quota_reset_is_pacific_midnight():
    from datetime import UTC, datetime

    from finn.calendar import next_quota_reset, to_ist

    assert to_ist(next_quota_reset(datetime(2026, 11, 11, 20, 0, tzinfo=UTC))).strftime("%d %H:%M") == "12 13:30"


def test_overloaded_strong_model_is_skipped_quickly_then_cooled():
    from finn.llm import TransientError

    pauses = []
    g = Chain("gemini", CHAIN, fails={"flash-38": TransientError("503 high demand")})
    r = Router([g], MemoryLLMLog(), sleep=pauses.append)
    assert r.run("strong", req(purpose="research.judge.v1", prompt="a")).model == "flash-3"
    assert [m for _, m in g.calls] == ["flash-38", "flash-38", "flash-3"] and pauses == [2.0]  # 2 attempts, not 5
    r.run("strong", req(purpose="research.reduce.v1", prompt="b"))
    assert [m for _, m in g.calls][-1] == "flash-3" and len(g.calls) == 4  # cooled: no third try on flash-38
