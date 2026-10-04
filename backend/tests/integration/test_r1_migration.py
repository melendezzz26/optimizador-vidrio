"""R1 sobre un clúster PostgreSQL efímero propio; nunca utiliza DATABASE_URL.

Requiere binarios PostgreSQL instalados (PATH, instalación Windows habitual o
NEWGLASS_TEST_PG_BIN). Si no existen, las pruebas se omiten explícitamente.
"""

import importlib.util
from pathlib import Path
import runpy
import sys
from types import ModuleType
from unittest.mock import patch

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base

from .postgres_support import new_database, schema_snapshot, upgrade


BACKEND = Path(__file__).resolve().parents[2]
R1 = "e1a2b3c4d5f6"
PREVIOUS = "c4e8a1f2b3d5"
LEGACY_PEDIDO = """INSERT INTO pedidos
    (id_pedido,fecha_registro,estado,espesor_mm,id_tipo_vidrio,id_usuario)
    VALUES (1,'2000-01-01','PENDIENTE',3,1,1); """


def insert_legacy_account(connection):
    connection.exec_driver_sql("INSERT INTO roles (id_rol,nombre) VALUES (1,'Operario')")
    connection.exec_driver_sql("INSERT INTO tipos_vidrio (id_tipo_vidrio,nombre,estado) VALUES (1,'Sintetico',true)")
    connection.exec_driver_sql("""INSERT INTO usuarios
        (id_usuario,dni,nombres,apellidos,usuario,correo,password_hash,estado,id_rol)
        VALUES (1,'00000001','Prueba','Sintetica','P00000001','test@example.invalid','hash-sintetico',true,1)""")


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
        result = upgrade(engine, R1)
        assert result.returncode == 0, result.stderr
        yield engine


def test_clean_database_reaches_r1_historical_contract(r1_db):
    module = ModuleType("app.shared.database")
    module.Base = declarative_base()
    with patch.dict(sys.modules, {"app.shared.database": module}):
        runpy.run_path(str(BACKEND / "app/models.py"))
    with r1_db.connect() as connection:
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == R1
        # Las siete entidades R1 y las tablas de ejecución siguen vigentes.
        # CONFIGURACION se contrasta abajo con su contrato histórico, no con R2.
        context = MigrationContext.configure(connection, opts={
            "compare_type": True, "compare_server_default": True,
            "include_object": lambda obj, name, type_, reflected, compare_to:
                not (type_ == "table" and name == "configuraciones"),
        })
        assert compare_metadata(context, module.Base.metadata) == []
    inspector = sa.inspect(r1_db)
    tables = set(inspector.get_table_names()) - {"alembic_version"}
    assert len(tables) == 10
    assert sum(len(inspector.get_columns(t)) for t in tables) == 68
    columns = {c["name"]: c for c in inspector.get_columns("configuraciones")}
    float_names = {
        "separacion_mm", "margen_mm", "resolucion_raster", "paso_angular",
        "area_minima_retazo", "dimension_minima_retazo",
    }
    assert set(columns) == float_names | {"id_configuracion", "fecha_actualizacion"}
    assert all(not c["nullable"] for c in columns.values())
    assert all(isinstance(columns[n]["type"], sa.Float) for n in float_names)
    assert isinstance(columns["id_configuracion"]["type"], sa.Integer)
    assert isinstance(columns["fecha_actualizacion"]["type"], sa.DateTime)
    assert not columns["fecha_actualizacion"]["type"].timezone
    assert all(c["default"] is None for n, c in columns.items() if n != "id_configuracion")
    assert inspector.get_pk_constraint("configuraciones")["constrained_columns"] == ["id_configuracion"]
    assert not inspector.get_check_constraints("configuraciones")
    assert not inspector.get_unique_constraints("configuraciones")
    assert not inspector.get_foreign_keys("configuraciones")
    assert not inspector.get_indexes("configuraciones")


def test_legacy_account_preserved_and_excluded_tables_unchanged(legacy_db):
    excluded = ["configuraciones", "ejecuciones_optimizacion", "metricas_ejecucion"]
    before = schema_snapshot(legacy_db, excluded)
    with legacy_db.connect() as connection:
        start = connection.scalar(sa.text("SELECT clock_timestamp()"))
    result = upgrade(legacy_db, R1)
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
    result = upgrade(legacy_db, R1)
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
    result = upgrade(legacy_db, R1)
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
