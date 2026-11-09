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
