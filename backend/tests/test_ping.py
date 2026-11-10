"""/ping: tiny plain-text keepalive (cron-job.org rejected the edge-compressed /health/db reply)."""

from fastapi.testclient import TestClient

import api.main as m


class FakeConn:
    def __init__(self, fail=False):
        self.fail, self.sql = fail, None

    def __enter__(self):
        if self.fail:
            raise m.psycopg.OperationalError("down")
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql):
        self.sql = sql
        return self

    def fetchone(self):
        return (1,)


def test_ping_ok_plain_uncompressed_and_head(monkeypatch):
    conns = []
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setattr(m.psycopg, "connect", lambda dsn, connect_timeout: conns.append(FakeConn()) or conns[-1])
    c = TestClient(m.app)
    r = c.get("/ping", headers={"Accept-Encoding": "gzip, br"})
    assert r.status_code == 200 and r.text == "ok"
    assert r.headers["content-type"].startswith("text/plain") and r.headers["content-length"] == "2"
    assert "no-transform" in r.headers["cache-control"] and r.headers.get("content-encoding") == "identity"
    assert conns[0].sql == "select 1"
    h = c.head("/ping")
    assert h.status_code == 200 and h.text == ""


def test_ping_reports_db_down(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setattr(m.psycopg, "connect", lambda dsn, connect_timeout: FakeConn(fail=True))
    r = TestClient(m.app).get("/ping")
    assert r.status_code == 503 and r.text == "db down"
