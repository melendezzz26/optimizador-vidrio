"""Configuración T02: datos sintéticos y engines sin conexiones remotas."""
import os
from pathlib import Path
import runpy
import secrets
import subprocess
import sys
from textwrap import dedent

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url

from app.shared.config import (
    cors_origins,
    database_engine_options,
    database_url,
    required_value,
    token_minutes,
)

BACKEND = Path(__file__).resolve().parents[3]
POOL_VARIABLES = ("DB_POOL_SIZE", "DB_MAX_OVERFLOW", "DB_POOL_TIMEOUT", "DB_CONNECT_TIMEOUT")
SYNTHETIC_URL = "postgresql+psycopg://test:p%25ss%40word@127.0.0.1:5432/test?sslmode=require"


@pytest.fixture(autouse=True)
def isolated_options(monkeypatch):
    for name in (*POOL_VARIABLES, "CORS_ORIGINS", "TOKEN_MINUTOS"):
        monkeypatch.delenv(name, raising=False)


def test_cors_development_defaults():
    assert cors_origins() == ["http://localhost:5173", "http://127.0.0.1:5173"]


@pytest.mark.parametrize("raw, expected", [
    ("https://one.example", ["https://one.example"]),
    (" https://one.example , , https://two.example, ", ["https://one.example", "https://two.example"]),
    ("https://one.example,https://one.example", ["https://one.example"]),
    (" , , ", []),
    ("", []),
])
def test_cors_explicit_origins(monkeypatch, raw, expected):
    monkeypatch.setenv("CORS_ORIGINS", raw)
    assert cors_origins() == expected


@pytest.mark.parametrize("origin", [
    "*", "https://one.example,*", "https://*.example", "null",
    "https://one.example/optimizador-vidrio/", "https://one.example/",
    "https://one.example?query=1", "https://one.example#fragment",
    "https://user:password@one.example", "ftp://one.example",
    "https://one.example:invalid", "https://one.example:99999",
    "https://one.example:", "https://one.example:0", "https://one .example",
])
def test_cors_rejects_invalid_origins_without_echoing_them(monkeypatch, origin):
    monkeypatch.setenv("CORS_ORIGINS", origin)
    with pytest.raises(RuntimeError, match="CORS_ORIGINS") as error:
        cors_origins()
    assert origin not in str(error.value)


def test_application_preflight_uses_configured_origins(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://one.example,https://two.example")
    # Una app separada evita modificar el middleware de otras pruebas.
    app = runpy.run_path(str(BACKEND / "main.py"))["app"]
    with TestClient(app) as client:
        for origin in ("https://one.example", "https://two.example"):
            response = client.options("/", headers={
                "Origin": origin, "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            })
            assert response.status_code == 200
            assert response.headers["access-control-allow-origin"] == origin
            assert "access-control-allow-credentials" not in response.headers
        denied = client.options("/", headers={
            "Origin": "https://denied.example", "Access-Control-Request-Method": "POST",
        })
        assert denied.status_code == 400
        assert "access-control-allow-origin" not in denied.headers
        for extra in ({"Access-Control-Request-Method": "TRACE"},
                      {"Access-Control-Request-Headers": "x-unapproved"}):
            response = client.options("/", headers={
                "Origin": "https://one.example", "Access-Control-Request-Method": "POST", **extra,
            })
            assert response.status_code == 400


@pytest.mark.parametrize("name", ["SECRET_KEY", "DATABASE_URL"])
@pytest.mark.parametrize("value", [None, "", "   "])
def test_required_settings_have_no_default(monkeypatch, name, value):
    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)
    with pytest.raises(RuntimeError, match=name):
        required_value(name)


def test_database_url_is_preserved_including_tls_and_percent(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", SYNTHETIC_URL)
    assert database_url() == SYNTHETIC_URL
    assert make_url(database_url()).query == {"sslmode": "require"}


def test_invalid_database_url_is_not_echoed(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "invalid-sensitive-value")
    with pytest.raises(RuntimeError, match="DATABASE_URL") as error:
        database_url()
    assert "invalid-sensitive-value" not in str(error.value)


def test_default_and_explicit_token_lifetime(monkeypatch):
    assert token_minutes() == 480
    monkeypatch.setenv("TOKEN_MINUTOS", " 60 ")
    assert token_minutes() == 60


@pytest.mark.parametrize("value", ["", "abc", "1.5", "0", "-1", "9" * 40])
def test_invalid_token_lifetime_has_clear_error(monkeypatch, value):
    monkeypatch.setenv("TOKEN_MINUTOS", value)
    with pytest.raises(RuntimeError, match="TOKEN_MINUTOS"):
        token_minutes()


def test_engine_defaults_only_enable_pre_ping():
    assert database_engine_options(SYNTHETIC_URL) == {"pool_pre_ping": True}


def test_postgres_engine_uses_options_without_connecting(monkeypatch):
    values = (" 2 ", "0", "7", "3")  # Valores de prueba, no límites de Supabase.
    for name, value in zip(POOL_VARIABLES, values):
        monkeypatch.setenv(name, value)
    options = database_engine_options(SYNTHETIC_URL)
    assert options == {
        "pool_pre_ping": True, "pool_size": 2, "max_overflow": 0,
        "pool_timeout": 7, "connect_args": {"connect_timeout": 3},
    }
    monkeypatch.setattr(Engine, "connect", lambda *args: pytest.fail("Conexión no permitida"))
    engine = create_engine(SYNTHETIC_URL, **options)
    try:
        assert engine.pool._pre_ping is True
        assert engine.pool.size() == 2
        assert engine.pool.timeout() == 7
        assert engine.url.query["sslmode"] == "require"
    finally:
        engine.dispose()


@pytest.mark.parametrize("name", POOL_VARIABLES)
@pytest.mark.parametrize("value", ["", "abc", "1.5", "-1"])
def test_invalid_pool_settings_fail_clearly(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(RuntimeError, match=name):
        database_engine_options(SYNTHETIC_URL)


@pytest.mark.parametrize("name", ["DB_POOL_SIZE", "DB_POOL_TIMEOUT", "DB_CONNECT_TIMEOUT"])
def test_zero_does_not_disable_pool_or_timeout_limits(monkeypatch, name):
    monkeypatch.setenv(name, "0")
    with pytest.raises(RuntimeError, match=name):
        database_engine_options(SYNTHETIC_URL)


def test_sqlite_does_not_receive_postgres_options(monkeypatch):
    for name in POOL_VARIABLES:
        monkeypatch.setenv(name, "2")
    options = database_engine_options("sqlite://")
    assert options == {"pool_pre_ping": True}
    engine = create_engine("sqlite://", **options)
    engine.dispose()


def test_null_pool_keeps_only_pre_ping_and_connect_timeout(monkeypatch):
    for name in POOL_VARIABLES:
        monkeypatch.setenv(name, "2")
    assert database_engine_options(SYNTHETIC_URL, pooled=False) == {
        "pool_pre_ping": True, "connect_args": {"connect_timeout": 2},
    }


def test_application_and_engine_load_from_environment_without_dotenv():
    script = dedent('''\
        import os
        from unittest.mock import patch
        from sqlalchemy.engine import Engine
        with patch("dotenv.load_dotenv", return_value=False), \\
             patch.object(Engine, "connect", side_effect=AssertionError("No conectar")):
            import main
            from app.shared.database import engine
            from app.shared.security.tokens import SECRET_KEY, TOKEN_MINUTES
            assert SECRET_KEY == os.environ["SECRET_KEY"]
            assert TOKEN_MINUTES == 480
            assert str(engine.url) == "sqlite://"
            assert engine.pool._pre_ping is True
    ''')
    environment = {**os.environ, "DATABASE_URL": "sqlite://", "SECRET_KEY": secrets.token_urlsafe(48)}
    result = subprocess.run([sys.executable, "-B", "-c", script], cwd=BACKEND,
                            env=environment, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr


def test_system_environment_precedes_optional_dotenv(tmp_path):
    dotenv = tmp_path / ".env"
    dotenv.write_text("DATABASE_URL=sqlite:///file-only.db\nSECRET_KEY=file-only-synthetic\nTOKEN_MINUTOS=10\n", encoding="utf-8")
    script = dedent('''\
        import os, sys
        from unittest.mock import patch
        from dotenv import load_dotenv as real_load
        def load_test_file(*args, **kwargs):
            return real_load(sys.argv[1], **kwargs)
        with patch("dotenv.load_dotenv", side_effect=load_test_file) as load:
            from app.shared.config import database_url, required_value, token_minutes
            assert database_url() == "sqlite://"
            assert required_value("SECRET_KEY") == os.environ["SECRET_KEY"]
            assert token_minutes() == 480
            load.assert_called_once()
    ''')
    environment = {**os.environ, "DATABASE_URL": "sqlite://", "SECRET_KEY": secrets.token_urlsafe(48), "TOKEN_MINUTOS": "480"}
    environment.pop("PYTHON_DOTENV_DISABLED", None)
    result = subprocess.run([sys.executable, "-B", "-c", script, str(dotenv)], cwd=BACKEND,
                            env=environment, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
