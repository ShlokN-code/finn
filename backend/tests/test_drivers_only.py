"""Drivers-only builds never touch the strong tier and respect the run budget / headroom rule."""

import pytest

from finn.research import drivers_only as dv


class FakeStats:
    calls = 0


class FakeRouter:
    def __init__(self):
        self.stats = FakeStats()
        self.tiers = []

    def run(self, tier, req):
        self.tiers.append(tier)
        self.stats.calls += 1
        return "ok"


class Req:
    purpose = "research.judge.v1"


def test_strong_tier_is_blocked():
    inner = FakeRouter()
    r = dv.CheapOnly(inner, budget=5)
    with pytest.raises(dv.StrongTierBlocked):
        r.run("strong", Req())
    assert inner.tiers == []
    r.run("cheap", Req())
    assert inner.tiers == ["cheap"] and r.spent == 1


def test_budget_stops_further_calls():
    from finn.llm import LLMUnavailable

    r = dv.CheapOnly(FakeRouter(), budget=2)
    r.run("cheap", Req())
    r.run("cheap", Req())
    with pytest.raises(LLMUnavailable):
        r.run("cheap", Req())


@pytest.mark.parametrize("used,budget", [(0, 50), (300, 50), (301, 0), (480, 0)])
def test_plan_budget_keeps_150_free(used, budget):
    # 500/day free: a 50-call run is allowed only if ≥150 stay free afterwards (used ≤ 300).
    assert dv.plan_budget(used) == budget


def test_failed_attempts_count_against_the_budget():
    from finn.llm import LLMUnavailable

    log = {"n": 0}

    class Failing(FakeRouter):
        def run(self, tier, req):
            log["n"] += 5  # five logged attempts, all failed
            raise LLMUnavailable("busy")

    r = dv.CheapOnly(Failing(), budget=8, used=lambda: log["n"])
    with pytest.raises(LLMUnavailable):
        r.run("cheap", Req())
    assert r.spent == 5
    with pytest.raises(LLMUnavailable):
        r.run("cheap", Req())
    assert r.spent == 10
    with pytest.raises(LLMUnavailable, match="budget"):
        r.run("cheap", Req())
