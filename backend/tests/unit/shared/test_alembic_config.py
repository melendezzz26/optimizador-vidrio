"""Ejecuta env.py con contexto/engine simulados; nunca migra ni conecta."""
from contextlib import nullcontext
from pathlib import Path
import runpy
from unittest.mock import Mock

from alembic import context
from alembic.config import Config
import pytest
import sqlalchemy
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

BACKEND = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("offline", [True, False])
def test_alembic_preserves_encoded_password_and_tls(monkeypatch, offline):
    url = "postgresql+psycopg://synthetic:p%25ss%40word@127.0.0.1:5432/synthetic?sslmode=require"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("DB_CONNECT_TIMEOUT", "3")
    for name in ("DB_POOL_SIZE", "DB_MAX_OVERFLOW", "DB_POOL_TIMEOUT"):
        monkeypatch.delenv(name, raising=False)
    config = Config()
    monkeypatch.setattr(context, "config", config, raising=False)
    monkeypatch.setattr(context, "is_offline_mode", lambda: offline)
    configure = Mock()
    monkeypatch.setattr(context, "configure", configure)
    monkeypatch.setattr(context, "begin_transaction", nullcontext)
    migrations = Mock()
    monkeypatch.setattr(context, "run_migrations", migrations)
    connection = object()
    engine = Mock()
    engine.connect.return_value = nullcontext(connection)
    factory = Mock(return_value=engine)
    monkeypatch.setattr(sqlalchemy, "engine_from_config", factory)

    runpy.run_path(str(BACKEND / "alembic" / "env.py"))

    assert config.get_main_option("sqlalchemy.url") == url
    assert make_url(config.get_main_option("sqlalchemy.url")).password == "p%ss@word"
    assert make_url(config.get_main_option("sqlalchemy.url")).query["sslmode"] == "require"
    migrations.assert_called_once_with()  # Solo el mock, no Alembic real.
    if offline:
        factory.assert_not_called()
        assert configure.call_args.kwargs["url"] == url
    else:
        assert factory.call_args.args[0]["sqlalchemy.url"] == url
        assert factory.call_args.kwargs["poolclass"] is NullPool
        assert factory.call_args.kwargs["connect_args"] == {"connect_timeout": 3}
        assert configure.call_args.kwargs["connection"] is connection
