"""Probe de readiness contra PostgreSQL temporal de la suite."""
import sqlalchemy as sa

from app.shared import database
from app.shared.observability.health import check_database
from .postgres_support import new_database


def test_postgres_probe_sets_transaction_local_timeout(isolated_postgres, monkeypatch):
    with new_database(isolated_postgres) as engine:
        monkeypatch.setattr(database, "engine", engine)
        statements = []
        def record(conn, cursor, statement, parameters, context, executemany):
            statements.append((statement, parameters))
        sa.event.listen(engine, "before_cursor_execute", record)
        assert check_database() is True
        assert any("set_config" in sql and params["timeout"] == "3000" for sql, params in statements)
        assert any(sql == "SELECT 1" for sql, _ in statements)
        with engine.connect() as connection:
            # SET LOCAL no contamina la conexión que vuelve al pool.
            assert connection.exec_driver_sql("SHOW statement_timeout").scalar_one() == "0"
