from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health_db_without_dsn(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    r = client.get("/health/db")
    assert r.status_code == 503
    assert r.json()["error"] == "DATABASE_URL not set"


def test_health_sources_is_cached(monkeypatch):
    from api import diagnostics

    calls = []
    monkeypatch.setattr(diagnostics, "_cache", None)
    monkeypatch.setattr(diagnostics, "run_probes", lambda: calls.append(1) or {"checked_at": "t", "probes": []})
    assert diagnostics.get_probes(now=1000.0)["cache_age_s"] == 0
    assert diagnostics.get_probes(now=1000.0 + 60)["cache_age_s"] == 60  # within TTL → cached
    diagnostics.get_probes(now=1000.0 + diagnostics.CACHE_TTL_S + 1)  # expired → recomputed
    assert len(calls) == 2
    r = client.get("/health/sources")
    assert r.status_code == 200 and "probes" in r.json()
