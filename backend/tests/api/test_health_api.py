"""Health: contrato HTTP, plazo acotado y ausencia de filtraciones."""
from threading import Event
from time import monotonic

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.engine import Engine

from app.shared.observability import health
from main import app


def test_live_does_not_touch_database(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Liveness intentó conectar a BD")
    monkeypatch.setattr(Engine, "connect", forbidden)
    monkeypatch.setattr(Engine, "raw_connection", forbidden)
    monkeypatch.setattr(health, "check_database", forbidden)
    with TestClient(app) as client:
        response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_queries_select_one(monkeypatch):
    from app.shared.database import engine
    statements = []
    from sqlalchemy import event
    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)
    event.listen(engine, "before_cursor_execute", record)
    try:
        with TestClient(app) as client:
            response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ready"}
        assert "SELECT 1" in statements
    finally:
        event.remove(engine, "before_cursor_execute", record)


@pytest.mark.parametrize("failure", [RuntimeError("synthetic host user password SELECT PostgreSQL DATABASE_URL"), TimeoutError("synthetic timeout")])
def test_ready_sanitizes_failures(monkeypatch, failure, caplog):
    def fail():
        raise failure
    monkeypatch.setattr(health, "check_database", fail)
    with TestClient(app) as client:
        response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}
    assert "synthetic" not in response.text + caplog.text


def test_ready_timeout_does_not_queue_more_work(monkeypatch):
    entered, release, finished = Event(), Event(), Event()
    calls = []
    def blocked():
        calls.append(1)
        entered.set()
        try:
            release.wait(2)
            raise RuntimeError("synthetic late failure")
        finally:
            finished.set()
    monkeypatch.setattr(health, "check_database", blocked)
    monkeypatch.setattr(health, "READINESS_TIMEOUT_SECONDS", 0.05)
    try:
        with TestClient(app) as client:
            start = monotonic()
            response = client.get("/health/ready")
            assert entered.is_set()
            assert monotonic() - start < 0.75
            assert response.status_code == 503
            assert response.json() == {"status": "not_ready"}
            assert client.get("/health/ready").status_code == 503
            assert client.get("/health/live").status_code == 200
            assert calls == [1]
            release.set()
            assert finished.wait(1)
    finally:
        release.set()
        finished.wait(2)


def test_db_test_is_removed_from_http_and_openapi():
    with TestClient(app) as client:
        assert client.get("/db-test").status_code == 404
        paths = client.get("/openapi.json").json()["paths"]
    assert "/db-test" not in paths
    assert {"/health/live", "/health/ready"} <= paths.keys()
