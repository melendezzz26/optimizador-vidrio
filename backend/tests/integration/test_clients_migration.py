"""HU-012: evolución CLIENTE y relación con PEDIDO sobre PostgreSQL temporal."""

import os
import sys

import pytest
import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.exc import IntegrityError

from tests.integration.postgres_support import (
    BACKEND,
    _run,
    new_database,
    upgrade,
)
from tests.model_contracts import current_metadata, historical_metadata


PREVIOUS = "d6e7f8a9b0c1"
REVISION = "ef6564220e70"


def downgrade(engine):
    assert engine.url.host == "127.0.0.1"
    assert engine.url.username == "r1_test"

    env = {
        **os.environ,
        "DATABASE_URL": engine.url.render_as_string(hide_password=False),
        "PYTHONIOENCODING": "utf-8",
    }

    return _run(
        [
            sys.executable,
            "-B",
            "-m",
            "alembic",
            "downgrade",
            PREVIOUS,
        ],
        cwd=BACKEND,
        env=env,
    )


def assert_schema(connection, metadata):
    assert compare_metadata(
        MigrationContext.configure(
            connection,
            opts={
                "compare_type": True,
                "compare_server_default": True,
            },
        ),
        metadata,
    ) == []


def seed_historical_order(connection):
    connection.execute(
        sa.text(
            "INSERT INTO roles(id_rol,nombre) "
            "VALUES (1,'Operario')"
        )
    )

    connection.execute(
        sa.text(
            """
            INSERT INTO usuarios(
                id_usuario,
                dni,
                nombres,
                apellidos,
                usuario,
                password_hash,
                id_rol,
                fecha_creacion
            )
            VALUES (
                1,
                '00000001',
                'Cliente',
                'Historico',
                'p00000001',
                'hash-sintetico',
                1,
                '2026-01-01T00:00:00Z'
            )
            """
        )
    )

    material = connection.scalar(
        sa.text(
            "SELECT id_tipo_vidrio "
            "FROM tipos_vidrio "
            "WHERE nombre='Incoloro'"
        )
    )

    connection.execute(
        sa.text(
            """
            INSERT INTO pedidos(
                id_pedido,
                fecha_registro,
                estado,
                id_usuario_registro
            )
            VALUES (
                41,
                '2026-02-03T04:05:06Z',
                'PENDIENTE',
                1
            )
            """
        )
    )

    geometry = (
        '{"type":"RECTANGULO",'
        '"width_mm":10,'
        '"height_mm":20}'
    )

    connection.execute(
        sa.text(
            """
            INSERT INTO piezas(
                id_pieza,
                id_tipo_vidrio,
                espesor_mm,
                tipo_forma,
                cantidad,
                dimensiones,
                geometria,
                area_mm2,
                id_pedido
            )
            VALUES (
                51,
                :material,
                6,
                'RECTANGULO',
                1,
                CAST(:geometry AS jsonb),
                CAST(:geometry AS jsonb),
                200.00,
                41
            )
            """
        ),
        {
            "material": material,
            "geometry": geometry,
        },
    )


def test_hu012_is_single_head_and_matches_current_orm(isolated_postgres):
    config = Config()
    config.set_main_option(
        "script_location",
        str(BACKEND / "alembic"),
    )

    scripts = ScriptDirectory.from_config(config)

    assert scripts.get_heads() == [REVISION]
    assert scripts.get_revision(REVISION).down_revision == PREVIOUS

    with new_database(isolated_postgres) as engine:
        result = upgrade(engine, "head")

        assert result.returncode == 0, result.stderr

        with engine.connect() as connection:
            assert connection.scalar(
                sa.text("SELECT version_num FROM alembic_version")
            ) == REVISION

            inspector = sa.inspect(connection)

            assert "clientes" in inspector.get_table_names()

            pedido_columns = {
                column["name"]
                for column in inspector.get_columns("pedidos")
            }

            assert "id_cliente" in pedido_columns

            assert_schema(connection, current_metadata())

        result = downgrade(engine)

        assert result.returncode == 0, result.stderr

        with engine.connect() as connection:
            inspector = sa.inspect(connection)

            assert "clientes" not in inspector.get_table_names()

            pedido_columns = {
                column["name"]
                for column in inspector.get_columns("pedidos")
            }

            assert "id_cliente" not in pedido_columns

            assert_schema(
                connection,
                historical_metadata(PREVIOUS),
            )

        result = upgrade(engine, REVISION)

        assert result.returncode == 0, result.stderr


def test_historical_orders_are_preserved_without_fake_clients(
    isolated_postgres,
):
    with new_database(isolated_postgres) as engine:
        assert upgrade(engine, PREVIOUS).returncode == 0

        with engine.begin() as connection:
            seed_historical_order(connection)

        result = upgrade(engine, REVISION)

        assert result.returncode == 0, result.stderr

        with engine.connect() as connection:
            assert connection.scalar(
                sa.text("SELECT COUNT(*) FROM clientes")
            ) == 0

            order = connection.execute(
                sa.text(
                    """
                    SELECT
                        id_pedido,
                        estado,
                        id_usuario_registro,
                        id_cliente
                    FROM pedidos
                    WHERE id_pedido = 41
                    """
                )
            ).mappings().one()

            assert order["id_pedido"] == 41
            assert order["estado"] == "PENDIENTE"
            assert order["id_usuario_registro"] == 1
            assert order["id_cliente"] is None

        result = downgrade(engine)

        assert result.returncode == 0, result.stderr

        with engine.connect() as connection:
            assert connection.scalar(
                sa.text(
                    "SELECT COUNT(*) "
                    "FROM pedidos "
                    "WHERE id_pedido = 41"
                )
            ) == 1


def test_cliente_document_pair_is_unique(isolated_postgres):
    with new_database(isolated_postgres) as engine:
        assert upgrade(engine, REVISION).returncode == 0

        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    """
                    INSERT INTO clientes(
                        tipo_documento,
                        numero_documento,
                        nombre_razon_social,
                        estado,
                        fecha_registro
                    )
                    VALUES (
                        'TEST',
                        '12345678',
                        'Cliente Uno',
                        TRUE,
                        '2026-10-08T00:00:00Z'
                    )
                    """
                )
            )

        with pytest.raises(IntegrityError) as caught:
            with engine.begin() as connection:
                connection.execute(
                    sa.text(
                        """
                        INSERT INTO clientes(
                            tipo_documento,
                            numero_documento,
                            nombre_razon_social,
                            estado,
                            fecha_registro
                        )
                        VALUES (
                            'TEST',
                            '12345678',
                            'Cliente Duplicado',
                            TRUE,
                            '2026-10-08T00:00:00Z'
                        )
                        """
                    )
                )

        assert (
            caught.value.orig.diag.constraint_name
            == "uq_clientes_tipo_numero_documento"
        )


def test_pedido_rejects_unknown_client(isolated_postgres):
    with new_database(isolated_postgres) as engine:
        assert upgrade(engine, PREVIOUS).returncode == 0

        with engine.begin() as connection:
            seed_historical_order(connection)

        assert upgrade(engine, REVISION).returncode == 0

        with pytest.raises(IntegrityError) as caught:
            with engine.begin() as connection:
                connection.execute(
                    sa.text(
                        """
                        UPDATE pedidos
                        SET id_cliente = 999999
                        WHERE id_pedido = 41
                        """
                    )
                )

        assert caught.value.orig.sqlstate == "23503"
        assert (
            caught.value.orig.diag.constraint_name
            == "fk_pedidos_cliente"
        )