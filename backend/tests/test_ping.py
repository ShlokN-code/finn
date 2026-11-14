"""/ping: tiny plain-text keepalive (cron-job.org rejected the edge-compressed /health/db reply). It answers at
once; the DB check runs in the background at most every 5 minutes and the next ping reports its result."""

import time

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


def _reset():
    m._db_state.update(at=0.0, ok=True, running=False)


def _wait_db_check():
    for _ in range(200):
        if not m._db_state["running"]:
            return
        time.sleep(0.01)


def test_ping_ok_plain_uncompressed_and_head(monkeypatch):
    _reset()
    conns = []
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setattr(m.psycopg, "connect", lambda dsn, connect_timeout: conns.append(FakeConn()) or conns[-1])
    c = TestClient(m.app)
    r = c.get("/ping", headers={"Accept-Encoding": "gzip, br"})
    assert r.status_code == 200 and r.text == "ok"
    assert r.headers["content-type"].startswith("text/plain") and r.headers["content-length"] == "2"
    assert "no-transform" in r.headers["cache-control"] and r.headers.get("content-encoding") == "identity"
    _wait_db_check()
    assert conns[0].sql == "select 1"  # the background check ran
    assert "app;dur=" in r.headers["server-timing"]
    h = c.head("/ping")
    assert h.status_code == 200 and h.text == ""


def test_ping_reports_db_down_on_the_next_ping_without_waiting(monkeypatch):
    _reset()
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")

    def slow_fail(dsn, connect_timeout):
        time.sleep(0.3)  # a slow, failing database must not delay the ping itself
        return FakeConn(fail=True)

    monkeypatch.setattr(m.psycopg, "connect", slow_fail)
    c = TestClient(m.app)
    t0 = time.perf_counter()
    r = c.get("/ping")
    assert r.status_code == 200 and time.perf_counter() - t0 < 0.25
    _wait_db_check()
    r2 = c.get("/ping")
    assert r2.status_code == 503 and r2.text == "db down"


def test_version_reports_uptime():
    v = TestClient(m.app).get("/version").json()
    assert v["uptime_s"] >= 0 and "rss_mb" in v
