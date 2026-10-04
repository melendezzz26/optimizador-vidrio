"""R1 sobre un clúster PostgreSQL efímero propio; nunca utiliza DATABASE_URL.

Requiere binarios PostgreSQL instalados (PATH, instalación Windows habitual o
NEWGLASS_TEST_PG_BIN). Si no existen, las pruebas se omiten explícitamente.
"""

from contextlib import contextmanager
import importlib.util
import os
from pathlib import Path
import runpy
import shutil
import socket
import subprocess
import sys
import tempfile
from types import ModuleType
from unittest.mock import patch
import uuid

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base


BACKEND = Path(__file__).resolve().parents[2]
R1 = "e1a2b3c4d5f6"
PREVIOUS = "c4e8a1f2b3d5"
LEGACY_PEDIDO = """INSERT INTO pedidos
    (id_pedido,fecha_registro,estado,espesor_mm,id_tipo_vidrio,id_usuario)
    VALUES (1,'2000-01-01','PENDIENTE',3,1,1); """


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
    configured = os.environ.get("NEWGLASS_TEST_PG_BIN")
    found = shutil.which("initdb")
    directory = Path(configured) if configured else (Path(found).parent if found else Path("C:/Program Files/PostgreSQL/18/bin"))
    suffix = ".exe" if os.name == "nt" else ""
    initdb, pg_ctl = (directory / (name + suffix) for name in ("initdb", "pg_ctl"))
    if not initdb.is_file() or not pg_ctl.is_file():
        pytest.skip("No hay binarios PostgreSQL locales para crear un clúster aislado.")
    root = tmp_path_factory.mktemp("newglass-r1-postgres")
    data = root / "data"
    result = _run([initdb, "-D", data, "-U", "r1_test", "-A", "trust", "--no-locale", "--encoding=UTF8"])
    assert result.returncode == 0, result.stderr
    with (data / "postgresql.conf").open("a", encoding="utf-8") as config:
        config.write("\nunix_socket_directories = ''\n")
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


def insert_legacy_account(connection):
    connection.exec_driver_sql("INSERT INTO roles (id_rol,nombre) VALUES (1,'Operario')")
    connection.exec_driver_sql("INSERT INTO tipos_vidrio (id_tipo_vidrio,nombre,estado) VALUES (1,'Sintetico',true)")
    connection.exec_driver_sql("""INSERT INTO usuarios
        (id_usuario,dni,nombres,apellidos,usuario,correo,password_hash,estado,id_rol)
        VALUES (1,'00000001','Prueba','Sintetica','P00000001','test@example.invalid','hash-sintetico',true,1)""")


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


@pytest.fixture
def legacy_db(isolated_postgres):
    with new_database(isolated_postgres) as engine:
        result = upgrade(engine, PREVIOUS)
        assert result.returncode == 0, result.stderr
        with engine.begin() as connection:
            insert_legacy_account(connection)
        yield engine


@pytest.fixture(scope="module")
def r1_db(isolated_postgres):
    with new_database(isolated_postgres) as engine:
        result = upgrade(engine, "head")
        assert result.returncode == 0, result.stderr
        yield engine


def test_clean_database_reaches_r1_and_matches_orm(r1_db):
    module = ModuleType("app.shared.database")
    module.Base = declarative_base()
    with patch.dict(sys.modules, {"app.shared.database": module}):
        runpy.run_path(str(BACKEND / "app/models.py"))
    with r1_db.connect() as connection:
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == R1
        context = MigrationContext.configure(connection, opts={"compare_type": True, "compare_server_default": True})
        assert compare_metadata(context, module.Base.metadata) == []


def test_legacy_account_preserved_and_excluded_tables_unchanged(legacy_db):
    excluded = ["configuraciones", "ejecuciones_optimizacion", "metricas_ejecucion"]
    before = schema_snapshot(legacy_db, excluded)
    with legacy_db.connect() as connection:
        start = connection.scalar(sa.text("SELECT clock_timestamp()"))
    result = upgrade(legacy_db, "head")
    assert result.returncode == 0, result.stderr
    assert schema_snapshot(legacy_db, excluded) == before
    with legacy_db.connect() as connection:
        finish = connection.scalar(sa.text("SELECT clock_timestamp()"))
        row = connection.execute(sa.text("SELECT id_usuario,dni,usuario,id_rol,fecha_creacion FROM usuarios")).one()
        assert tuple(row[:4]) == (1, "00000001", "P00000001", 1)
        assert start <= row.fecha_creacion <= finish
    assert "correo" not in {c["name"] for c in sa.inspect(legacy_db).get_columns("usuarios")}


@pytest.mark.parametrize("sql,reason", [
    ("UPDATE roles SET nombre=repeat('x',31)", "roles.nombre"),
    ("UPDATE roles SET descripcion=repeat('x',151)", "roles.descripcion"),
    ("UPDATE usuarios SET dni='1234567X'", "usuarios.dni"),
    ("UPDATE usuarios SET usuario='100000001'", "usuarios.usuario"),
    ("INSERT INTO tipos_vidrio(id_tipo_vidrio,nombre,estado) VALUES (2,'Sintetico',true)", "duplicados"),
    ("INSERT INTO planchas(codigo,ancho_mm,alto_mm,espesor_mm,cantidad,estado,id_tipo_vidrio) VALUES ('S',10,10,3,1,true,1)", "planchas debe estar vacía"),
    ("INSERT INTO retazos(codigo,espesor_mm,geometria,area_mm2,estado,id_tipo_vidrio) VALUES ('R',3,'{}',100,true,1)", "retazos debe estar vacía"),
    ("INSERT INTO pedidos(fecha_registro,estado,espesor_mm,id_tipo_vidrio,id_usuario) VALUES ('2000-01-01','PENDIENTE',3,1,1)", "pedidos debe estar vacía"),
    (LEGACY_PEDIDO + "INSERT INTO piezas(tipo_forma,cantidad,geometria,area_mm2,id_pedido) VALUES ('RECTANGULO',1,NULL,100,1)", "geometria o area_mm2 NULL"),
    (LEGACY_PEDIDO + "INSERT INTO piezas(tipo_forma,cantidad,geometria,area_mm2,id_pedido) VALUES ('RECTANGULO',1,'{}',NULL,1)", "geometria o area_mm2 NULL"),
    (LEGACY_PEDIDO + "INSERT INTO piezas(tipo_forma,cantidad,geometria,area_mm2,id_pedido) VALUES ('RECTANGULO',1,'{}',1.001,1)", "piezas.area_mm2"),
])
def test_preflight_failure_leaves_schema_revision_and_data_unchanged(legacy_db, sql, reason):
    with legacy_db.begin() as connection:
        connection.exec_driver_sql(sql)
    tables = sa.inspect(legacy_db).get_table_names()
    before = schema_snapshot(legacy_db, tables)
    with legacy_db.connect() as connection:
        # Comparación en memoria de datos sintéticos; no se imprimen ni exportan.
        data_before = {t: connection.exec_driver_sql(f'SELECT * FROM "{t}" ORDER BY 1').all() for t in tables}
    result = upgrade(legacy_db, "head")
    assert result.returncode != 0 and reason in result.stderr
    assert schema_snapshot(legacy_db, tables) == before
    with legacy_db.connect() as connection:
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == PREVIOUS
        assert {t: connection.exec_driver_sql(f'SELECT * FROM "{t}" ORDER BY 1').all() for t in tables} == data_before


def test_unexpected_dependency_rolls_back_ddl_and_technical_date(legacy_db):
    with legacy_db.begin() as connection:
        connection.exec_driver_sql("CREATE VIEW correo_dependiente AS SELECT correo FROM usuarios")
    tables = sa.inspect(legacy_db).get_table_names()
    before = schema_snapshot(legacy_db, tables)
    result = upgrade(legacy_db, "head")
    assert result.returncode != 0 and "DependentObjectsStillExist" in result.stderr
    assert schema_snapshot(legacy_db, tables) == before
    with legacy_db.connect() as connection:
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == PREVIOUS
        assert connection.scalar(sa.text("SELECT count(*) FROM correo_dependiente")) == 1


@pytest.fixture(scope="module")
def migration_module():
    spec = importlib.util.spec_from_file_location("r1_revision", BACKEND / "alembic/versions/e1a2b3c4d5f6_r1_identidad_inventario_pedidos.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("value,accepted", [
    (0.01, True), (123.45, True), (1.0, True),
    (None, False), (float("nan"), False), (float("inf"), False), (float("-inf"), False),
    (-1.0, False), (0.0, False), (1.001, False), (1e16, False),
    (1234567890123456.0, False),
])
def test_numeric_preflight_against_real_postgres(r1_db, migration_module, value, accepted):
    with r1_db.connect() as connection:
        transaction = connection.begin()
        try:
            connection.exec_driver_sql("CREATE TEMP TABLE conversion_test (area_mm2 double precision)")
            connection.execute(sa.text("INSERT INTO conversion_test VALUES (:value)"), {"value": value})
            if accepted:
                migration_module._validate_numeric(connection, "conversion_test", "area_mm2", 18, 2, "area_mm2 > 0")
            else:
                with pytest.raises(RuntimeError, match="R1 abortada"):
                    migration_module._validate_numeric(connection, "conversion_test", "area_mm2", 18, 2, "area_mm2 > 0")
        finally:
            transaction.rollback()


@pytest.fixture
def valid_r1_rows(r1_db):
    with r1_db.connect() as connection:
        transaction = connection.begin()
        connection.exec_driver_sql("INSERT INTO roles(id_rol,nombre) VALUES (1,'Operario')")
        connection.exec_driver_sql("INSERT INTO tipos_vidrio(id_tipo_vidrio,nombre) VALUES (1,'Sintetico')")
        connection.exec_driver_sql("""INSERT INTO usuarios(id_usuario,dni,nombres,apellidos,usuario,password_hash,id_rol,fecha_creacion)
            VALUES (1,'00000001','Prueba','Sintetica','P00000001','hash-sintetico',1,CURRENT_TIMESTAMP)""")
        connection.exec_driver_sql("""INSERT INTO planchas(id_plancha,ancho_mm,alto_mm,espesor_mm,cantidad,id_tipo_vidrio,fecha_registro)
            VALUES (1,100,200,5.5,0,1,CURRENT_TIMESTAMP)""")
        connection.exec_driver_sql("""INSERT INTO retazos(id_retazo,codigo,espesor_mm,geometria,area_mm2,id_tipo_vidrio,fecha_registro)
            VALUES (1,'R',5.5,'{}',100,1,CURRENT_TIMESTAMP)""")
        connection.exec_driver_sql("""INSERT INTO pedidos(id_pedido,fecha_registro,estado,espesor_mm,id_tipo_vidrio,id_usuario_registro)
            VALUES (1,CURRENT_TIMESTAMP,'PENDIENTE',5.5,1,1)""")
        connection.exec_driver_sql("""INSERT INTO piezas(id_pieza,tipo_forma,cantidad,geometria,area_mm2,id_pedido)
            VALUES (1,'RECTANGULO',1,'{}',100,1)""")
        try:
            yield connection
        finally:
            transaction.rollback()


@pytest.mark.parametrize("sql", [
    "UPDATE usuarios SET dni='1234567X'", "UPDATE usuarios SET usuario='100000001'",
    "UPDATE usuarios SET id_rol=999", "UPDATE usuarios SET fecha_creacion=NULL",
    "INSERT INTO usuarios(id_usuario,dni,nombres,apellidos,usuario,password_hash,id_rol,fecha_creacion) SELECT 2,dni,nombres,apellidos,'p00000002',password_hash,id_rol,fecha_creacion FROM usuarios",
    "INSERT INTO usuarios(id_usuario,dni,nombres,apellidos,usuario,password_hash,id_rol,fecha_creacion) SELECT 2,'00000002',nombres,apellidos,usuario,password_hash,id_rol,fecha_creacion FROM usuarios",
    "UPDATE planchas SET espesor_mm=7", "UPDATE planchas SET ancho_mm=0", "UPDATE planchas SET alto_mm=-1",
    "UPDATE planchas SET cantidad=-1", "UPDATE planchas SET id_tipo_vidrio=999",
    "UPDATE retazos SET espesor_mm=7", "UPDATE retazos SET area_mm2=0",
    "UPDATE pedidos SET estado='OTRO'", "UPDATE pedidos SET espesor_mm=7", "UPDATE pedidos SET id_usuario_registro=999",
    "UPDATE piezas SET tipo_forma='OTRA'", "UPDATE piezas SET cantidad=0", "UPDATE piezas SET geometria=NULL",
    "UPDATE piezas SET area_mm2=NULL", "UPDATE piezas SET area_mm2=0", "UPDATE piezas SET id_pedido=999",
    "INSERT INTO tipos_vidrio(id_tipo_vidrio,nombre) VALUES (2,'Sintetico')",
])
def test_database_rejects_invalid_r1_data(valid_r1_rows, sql):
    with pytest.raises(sa.exc.IntegrityError):
        valid_r1_rows.exec_driver_sql(sql)


def test_server_defaults_and_case_neutral_username(valid_r1_rows):
    for table in ("usuarios", "tipos_vidrio", "planchas", "retazos"):
        assert valid_r1_rows.scalar(sa.text(f"SELECT estado FROM {table}")) is True
    valid_r1_rows.exec_driver_sql("UPDATE usuarios SET usuario='p00000001', nombres='Otro nombre'")
    assert valid_r1_rows.scalar(sa.text("SELECT usuario FROM usuarios")) == "p00000001"
