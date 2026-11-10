from fastapi.testclient import TestClient

from api.main import app


def test_version_reports_render_commit(monkeypatch):
    monkeypatch.setenv("RENDER_GIT_COMMIT", "4f059120abcdef")
    body = TestClient(app).get("/version").json()
    assert body["commit"] == "4f059120abcdef" and body["short"] == "4f05912"


def test_version_without_commit(monkeypatch):
    monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)
    monkeypatch.delenv("GIT_COMMIT", raising=False)
    assert TestClient(app).get("/version").json()["commit"] is None
