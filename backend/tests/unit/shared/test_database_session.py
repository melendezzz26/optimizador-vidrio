"""Sesión de base de datos por petición (SPEC-HU-001, sección 9)."""
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.shared.database import engine, get_db


def test_tests_never_use_the_shared_database():
    # tests/conftest.py fija una base SQLite en memoria antes de importar la app.
    assert engine.url.get_backend_name() == "sqlite"


def test_get_db_yields_a_working_session():
    dependency = get_db()
    db = next(dependency)
    try:
        assert isinstance(db, Session)
        assert db.execute(text("select 1")).scalar() == 1
    finally:
        dependency.close()


def test_get_db_closes_the_session_when_the_request_ends(monkeypatch):
    closed = []
    original_close = Session.close

    def tracking_close(self):
        closed.append(self)
        original_close(self)

    monkeypatch.setattr(Session, "close", tracking_close)
    dependency = get_db()
    db = next(dependency)
    dependency.close()
    assert closed == [db]


def test_get_db_closes_the_session_when_the_request_fails(monkeypatch):
    closed = []
    original_close = Session.close

    def tracking_close(self):
        closed.append(self)
        original_close(self)

    monkeypatch.setattr(Session, "close", tracking_close)
    dependency = get_db()
    db = next(dependency)
    try:
        dependency.throw(RuntimeError("fallo durante la petición"))
    except RuntimeError:
        pass
    assert closed == [db]


def test_each_request_gets_its_own_session():
    first, second = get_db(), get_db()
    try:
        assert next(first) is not next(second)
    finally:
        first.close()
        second.close()
