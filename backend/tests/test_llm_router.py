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
