"""HU-006: evolución histórica exclusivamente en PostgreSQL temporal propio."""
import json
import os
import sys
from decimal import Decimal

import pytest
import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.exc import IntegrityError

from tests.integration.postgres_support import BACKEND, _run, new_database, upgrade, schema_snapshot
from tests.model_contracts import current_metadata, historical_metadata

PREVIOUS = "1c8754481a08"
REVISION = "d6e7f8a9b0c1"


def downgrade(engine):
    assert engine.url.host == "127.0.0.1" and engine.url.username == "r1_test"
    env = {**os.environ, "DATABASE_URL": engine.url.render_as_string(hide_password=False),
           "PYTHONIOENCODING": "utf-8"}
    return _run([sys.executable, "-B", "-m", "alembic", "downgrade", PREVIOUS], cwd=BACKEND, env=env)


def seed_history(connection):
    connection.execute(sa.text("INSERT INTO roles(id_rol,nombre) VALUES (1,'Operario')"))
    connection.execute(sa.text(
        "INSERT INTO usuarios(id_usuario,dni,nombres,apellidos,usuario,password_hash,id_rol,fecha_creacion) "
        "VALUES (1,'00000001','Prueba','Historica','p00000001','hash-sintetico',1,'2026-01-01T00:00:00Z')"))
    material = connection.scalar(sa.text("SELECT id_tipo_vidrio FROM tipos_vidrio WHERE nombre='Incoloro'"))
    connection.execute(sa.text(
        "INSERT INTO pedidos(id_pedido,fecha_registro,estado,id_usuario_registro,id_tipo_vidrio,espesor_mm) "
        "VALUES (41,'2026-02-03T04:05:06Z','PENDIENTE',1,:material,6)"), {"material": material})
    pieces = [
        (51, "RECTANGULO", 2, {"type": "RECTANGULO", "width_mm": 10, "height_mm": 20}, "200.00"),
        (52, "CIRCUNFERENCIA", 1, {"type": "CIRCUNFERENCIA", "radius_mm": 10}, "314.16"),
        (53, "POLIGONO_CONVEXO", 3, {"type": "POLIGONO_CONVEXO", "vertices_mm": [[0, 0], [10, 0], [0, 10]]}, "50.00"),
    ]
    for identifier, shape, quantity, geometry, area in pieces:
        connection.execute(sa.text(
            "INSERT INTO piezas(id_pieza,id_pedido,tipo_forma,cantidad,dimensiones,geometria,area_mm2) "
            "VALUES (:id,41,:shape,:quantity,CAST(:dimensions AS jsonb),CAST(:geometry AS jsonb),:area)"),
            {"id": identifier, "shape": shape, "quantity": quantity,
             "dimensions": None if shape == "POLIGONO_CONVEXO" else json.dumps(geometry),
             "geometry": json.dumps(geometry), "area": Decimal(area)})
    return material


def snapshot(connection):
    return {
        table: connection.execute(sa.text(f"SELECT to_jsonb(t) FROM {table} t ORDER BY {pk}")).scalars().all()
        for table, pk in (("pedidos", "id_pedido"), ("piezas", "id_pieza"),
                          ("tipos_vidrio", "id_tipo_vidrio"), ("tipos_vidrio_espesores", "id_tipo_vidrio, espesor_mm"))
    }


def assert_schema(connection, metadata):
    assert compare_metadata(MigrationContext.configure(connection, opts={
        "compare_type": True, "compare_server_default": True,
    }), metadata) == []


def test_single_head_empty_database_and_orm(isolated_postgres):
    config = Config()
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_heads() == [REVISION]
    assert scripts.get_revision(REVISION).down_revision == PREVIOUS
    with new_database(isolated_postgres) as engine:
        result = upgrade(engine, "head")
        assert result.returncode == 0, result.stderr
        with engine.connect() as connection:
            assert_schema(connection, current_metadata())
            assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == REVISION
            assert connection.scalar(sa.text("SELECT COUNT(*) FROM tipos_vidrio_espesores")) == 28
            assert "espesor_mm" not in {c["name"] for c in sa.inspect(connection).get_columns("pedidos")}
        assert downgrade(engine).returncode == 0
        with engine.connect() as connection:
            assert_schema(connection, historical_metadata(PREVIOUS))


def test_history_inactive_type_renamed_constraint_and_safe_roundtrip(isolated_postgres):
    with new_database(isolated_postgres) as engine:
        assert upgrade(engine, PREVIOUS).returncode == 0
        with engine.begin() as connection:
            material = seed_history(connection)
            connection.execute(sa.text("UPDATE tipos_vidrio SET estado=FALSE WHERE id_tipo_vidrio=:id"), {"id": material})
            connection.exec_driver_sql("ALTER TABLE pedidos RENAME CONSTRAINT pedidos_id_tipo_vidrio_fkey TO custom_material_fk")
            before = snapshot(connection)
        result = upgrade(engine, REVISION)
        assert result.returncode == 0, result.stderr
        with engine.connect() as connection:
            after = snapshot(connection)
            assert after["pedidos"] == [{k: v for k, v in row.items() if k not in ("id_tipo_vidrio", "espesor_mm")}
                                        for row in before["pedidos"]]
            assert after["piezas"] == [row | {"id_tipo_vidrio": material, "espesor_mm": 6} for row in before["piezas"]]
            assert after["tipos_vidrio"] == before["tipos_vidrio"]
            assert after["tipos_vidrio_espesores"] == before["tipos_vidrio_espesores"]
            assert_schema(connection, current_metadata())
        result = downgrade(engine)
        assert result.returncode == 0, result.stderr
        with engine.connect() as connection:
            assert snapshot(connection) == before
            assert_schema(connection, historical_metadata(PREVIOUS))
        assert upgrade(engine, REVISION).returncode == 0


@pytest.mark.parametrize("change, message", [
    ("DELETE FROM piezas", "pedidos históricos sin piezas"),
    ("ALTER TABLE pedidos ALTER COLUMN espesor_mm DROP NOT NULL; UPDATE pedidos SET espesor_mm=NULL", "NULL"),
    ("ALTER TABLE pedidos DROP CONSTRAINT fk_pedidos_tipo_espesor; UPDATE pedidos SET espesor_mm=99", "parejas inexistentes"),
    ("ALTER TABLE piezas DROP CONSTRAINT piezas_id_pedido_fkey; UPDATE piezas SET id_pedido=999", "piezas huérfanas"),
])
def test_invalid_history_aborts_without_changes(isolated_postgres, change, message):
    with new_database(isolated_postgres) as engine:
        assert upgrade(engine, PREVIOUS).returncode == 0
        with engine.begin() as connection:
            seed_history(connection)
            for statement in change.split("; "):
                connection.exec_driver_sql(statement)
            before = snapshot(connection)
        schema = schema_snapshot(engine, ("pedidos", "piezas"))
        result = upgrade(engine, REVISION)
        assert result.returncode != 0 and message in result.stderr
        with engine.connect() as connection:
            assert snapshot(connection) == before
            assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == PREVIOUS
        assert schema_snapshot(engine, ("pedidos", "piezas")) == schema


def test_external_dependency_rolls_back_ddl_and_backfill(isolated_postgres):
    with new_database(isolated_postgres) as engine:
        assert upgrade(engine, PREVIOUS).returncode == 0
        with engine.begin() as connection:
            seed_history(connection)
            connection.exec_driver_sql("CREATE VIEW historical_material AS SELECT id_tipo_vidrio FROM pedidos")
            before = snapshot(connection)
        assert upgrade(engine, REVISION).returncode != 0
        with engine.connect() as connection:
            assert snapshot(connection) == before
            assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == PREVIOUS
            assert_schema(connection, historical_metadata(PREVIOUS))
            assert "historical_material" in sa.inspect(connection).get_view_names()


@pytest.mark.parametrize("change, code", [("espesor_mm=99", "23503"), ("id_tipo_vidrio=NULL", "23502"), ("espesor_mm=NULL", "23502")])
def test_piece_pair_constraint_and_not_null(isolated_postgres, change, code):
    with new_database(isolated_postgres) as engine:
        assert upgrade(engine, PREVIOUS).returncode == 0
        with engine.begin() as connection:
            seed_history(connection)
        assert upgrade(engine, REVISION).returncode == 0
        with pytest.raises(IntegrityError) as caught:
            with engine.begin() as connection:
                connection.exec_driver_sql(f"UPDATE piezas SET {change} WHERE id_pieza=51")
        assert caught.value.orig.sqlstate == code
        if code == "23503":
            assert caught.value.orig.diag.constraint_name == "fk_piezas_tipo_espesor"


@pytest.mark.parametrize("change, message", [
    ("UPDATE piezas SET espesor_mm=8 WHERE id_pieza=51", "pedidos multimaterial"),
    ("UPDATE piezas SET id_tipo_vidrio=(SELECT id_tipo_vidrio FROM tipos_vidrio WHERE nombre='Bronce') WHERE id_pieza=51", "pedidos multimaterial"),
    ("DELETE FROM piezas", "sin piezas"),
])
def test_unsafe_downgrade_is_blocked_before_ddl(isolated_postgres, change, message):
    with new_database(isolated_postgres) as engine:
        assert upgrade(engine, PREVIOUS).returncode == 0
        with engine.begin() as connection:
            seed_history(connection)
        assert upgrade(engine, REVISION).returncode == 0
        with engine.begin() as connection:
            connection.exec_driver_sql(change)
            before = snapshot(connection)
        result = downgrade(engine)
        assert result.returncode != 0 and message in result.stderr
        with engine.connect() as connection:
            assert snapshot(connection) == before
            assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == REVISION
            assert_schema(connection, current_metadata())
