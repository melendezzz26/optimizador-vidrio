import os
import sys

import pytest
import sqlalchemy as sa

from tests.integration.postgres_support import BACKEND, _run, new_database, upgrade
from tests.integration.test_hu014_movement_migration import _seed_resources, _insert_movement


def downgrade(engine):
    return _run([sys.executable, "-m", "alembic", "downgrade", "fa014e1a2b3c"], cwd=BACKEND,
                env={**os.environ, "PYTHON_DOTENV_DISABLED": "1",
                     "DATABASE_URL": engine.url.render_as_string(hide_password=False)})


def test_upgrade_preserves_unknown_history_and_allows_partial_writeoffs(isolated_postgres):
    with new_database(isolated_postgres) as engine:
        assert upgrade(engine, "fa014e1a2b3c").returncode == 0
        with engine.begin() as connection:
            _seed_resources(connection)
            _insert_movement(connection, event="BAJA_ROTURA", plancha=1)
            _insert_movement(connection, event="BAJA_ROTURA", retazo=1)
        assert upgrade(engine, "head").returncode == 0
        quantity_column = next(column for column in sa.inspect(engine).get_columns("movimientos_inventario")
                               if column["name"] == "cantidad_afectada")
        assert quantity_column["nullable"] is True  # Unknown history remains readable.
        assert quantity_column["default"] is None  # Never invent a historical quantity.
        with engine.begin() as connection:
            assert connection.execute(sa.text(
                "SELECT cantidad_afectada FROM movimientos_inventario ORDER BY id_movimiento"
            )).scalars().all() == [None, 1]
            connection.exec_driver_sql(
                "INSERT INTO movimientos_inventario(id_plancha,tipo_evento,motivo,id_usuario,cantidad_afectada) "
                "VALUES (1,'BAJA_MERMA','Baja parcial',1,2), (1,'BAJA_MERMA','Otra baja',1,1)"
            )
            for resource, quantity in (("id_plancha", 0), ("id_plancha", -1),
                                       ("id_retazo", 0), ("id_retazo", -1), ("id_retazo", 2)):
                with pytest.raises(sa.exc.IntegrityError), connection.begin_nested():
                    connection.exec_driver_sql(
                        f"INSERT INTO movimientos_inventario({resource},tipo_evento,motivo,id_usuario,cantidad_afectada) "
                        f"VALUES (3,'BAJA_MERMA','Inválido',1,{quantity})"
                    )
        assert downgrade(engine).returncode != 0
        with engine.connect() as connection:
            assert connection.scalar(sa.text("SELECT count(*) FROM movimientos_inventario")) == 4
            assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == "ta036a1b2c3d"


def test_empty_database_supports_safe_downgrade_and_reupgrade(isolated_postgres):
    with new_database(isolated_postgres) as engine:
        assert upgrade(engine, "head").returncode == 0
        result = downgrade(engine)
        assert result.returncode == 0, result.stderr
        assert upgrade(engine, "head").returncode == 0
