"""Utilidades de pruebas: PostgreSQL temporal propio, sin destinos remotos."""

from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import uuid

import pytest
import sqlalchemy as sa

BACKEND = Path(__file__).resolve().parents[2]


def _run(args, **kwargs):
    # En Windows postgres puede heredar handles de pg_ctl: usar archivos evita
    # esperar EOF de pipes que permanecerían abiertos mientras vive el servidor.
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        result = subprocess.run(
            [str(a) for a in args], stdout=stdout, stderr=stderr,
            stdin=subprocess.DEVNULL, timeout=90,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            **kwargs,
        )
        stdout.seek(0)
        stderr.seek(0)
        result.stdout = stdout.read().decode("utf-8", errors="replace")
        result.stderr = stderr.read().decode("utf-8", errors="replace")
        return result


@pytest.fixture(scope="session")
def isolated_postgres(tmp_path_factory):
    with temporary_postgres(tmp_path_factory.mktemp("newglass-migrations-postgres")) as cluster:
        yield cluster


@contextmanager
def temporary_postgres(root):
    """Owned loopback cluster, also used by the real HTTP/browser test server."""
    configured = os.environ.get("NEWGLASS_TEST_PG_BIN")
    found = shutil.which("initdb")
    directory = Path(configured) if configured else (Path(found).parent if found else Path("C:/Program Files/PostgreSQL/18/bin"))
    suffix = ".exe" if os.name == "nt" else ""
    initdb, pg_ctl = (directory / (name + suffix) for name in ("initdb", "pg_ctl"))
    if not initdb.is_file() or not pg_ctl.is_file():
        pytest.skip("No hay binarios PostgreSQL locales para crear un clúster aislado.")
    data = root / "data"
    result = _run([initdb, "-D", data, "-U", "r1_test", "-A", "trust", "--no-locale", "--encoding=UTF8"])
    assert result.returncode == 0, result.stderr
    with (data / "postgresql.conf").open("a", encoding="utf-8") as config:
        config.write("\nunix_socket_directories = ''\ntimezone = 'UTC'\n")
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    # No sockets Unix ni interfaces externas; el cluster es exclusivo de la suite.
    try:
        result = _run([pg_ctl, "-D", data, "-l", root / "postgres.log", "-o", f"-h 127.0.0.1 -p {port}", "-w", "start"])
        assert result.returncode == 0, result.stderr
        yield sa.URL.create("postgresql+psycopg", username="r1_test", host="127.0.0.1", port=port, database="postgres")
    finally:
        if (data / "postmaster.pid").exists():
            stopped = _run([pg_ctl, "-D", data, "-m", "fast", "-w", "stop"])
            assert stopped.returncode == 0, stopped.stderr


def upgrade(engine, revision):
    # URL construida por la fixture: no se acepta ninguna conexión externa.
    assert engine.url.host == "127.0.0.1" and engine.url.username == "r1_test"
    environment = {**os.environ, "DATABASE_URL": engine.url.render_as_string(hide_password=False), "PYTHONIOENCODING": "utf-8"}
    return _run([sys.executable, "-B", "-m", "alembic", "upgrade", revision], cwd=BACKEND, env=environment)


@contextmanager
def new_database(cluster):
    name = "r1_" + uuid.uuid4().hex
    admin = sa.create_engine(cluster, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.exec_driver_sql(f'CREATE DATABASE "{name}"')
    admin.dispose()
    engine = sa.create_engine(cluster.set(database=name))
    try:
        yield engine
    finally:
        engine.dispose()
    # Los datos sintéticos quedan únicamente en el directorio temporal del
    # clúster detenido; pytest administra su retención. No se toca otro servicio.


def schema_snapshot(engine, tables):
    inspector = sa.inspect(engine)
    result = {}
    for table in tables:
        result[table] = {
            "columns": [(c["name"], str(c["type"]), c["nullable"], c["default"]) for c in inspector.get_columns(table)],
            "pk": inspector.get_pk_constraint(table), "fk": inspector.get_foreign_keys(table),
            "unique": inspector.get_unique_constraints(table), "check": inspector.get_check_constraints(table),
            "indexes": inspector.get_indexes(table),
        }
    return result
