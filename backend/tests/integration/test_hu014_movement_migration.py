import sqlalchemy as sa
import pytest

from tests.integration.postgres_support import new_database, upgrade


REVISION = "fa014e1a2b3c"


def _seed_resources(connection):
    connection.exec_driver_sql("INSERT INTO roles(id_rol,nombre) VALUES (1,'Operario')")
    connection.exec_driver_sql(
        """INSERT INTO usuarios(
            id_usuario,dni,nombres,apellidos,usuario,password_hash,id_rol,fecha_creacion
        ) VALUES (1,'00000001','Persona','Prueba','A00000001','hash',1,CURRENT_TIMESTAMP)"""
    )
    tipo_vidrio_id = connection.scalar(
        sa.text("SELECT id_tipo_vidrio FROM tipos_vidrio WHERE nombre = 'Incoloro'")
    )
    assert tipo_vidrio_id is not None, "TA-013 debe crear el tipo de vidrio Incoloro"
    espesor = connection.scalar(
        sa.text(
            "SELECT espesor_mm FROM tipos_vidrio_espesores "
            "WHERE id_tipo_vidrio = :tipo_id AND espesor_mm = 3"
        ),
        {"tipo_id": tipo_vidrio_id},
    )
    assert espesor is not None, "TA-013 debe habilitar espesor 3 mm para Incoloro"

    connection.execute(
        sa.text(
            """INSERT INTO planchas(
                id_plancha,ancho_mm,alto_mm,espesor_mm,cantidad,id_tipo_vidrio,fecha_registro
            ) VALUES (:id,100,200,:espesor,4,:tipo_id,CURRENT_TIMESTAMP)"""
        ),
        [
            {"id": identifier, "espesor": espesor, "tipo_id": tipo_vidrio_id}
            for identifier in (1, 2, 3)
        ],
    )
    connection.execute(
        sa.text(
            """INSERT INTO retazos(
                id_retazo,codigo,espesor_mm,geometria,area_mm2,id_tipo_vidrio,fecha_registro
            ) VALUES (:id,:codigo,:espesor,'{}',100,:tipo_id,CURRENT_TIMESTAMP)"""
        ),
        [
            {
                "id": identifier,
                "codigo": f"R-{identifier}",
                "espesor": espesor,
                "tipo_id": tipo_vidrio_id,
            }
            for identifier in (1, 2, 3)
        ],
    )


def _insert_movement(connection, *, event, reason="Revisión", plancha=None, retazo=None,
                     actor=1, optimization=None):
    return connection.execute(
        sa.text(
            """INSERT INTO movimientos_inventario(
                id_plancha,id_retazo,tipo_evento,motivo,id_usuario,id_optimizacion
            ) VALUES (:plancha,:retazo,:event,:reason,:actor,:optimization)
            RETURNING id_movimiento,fecha"""
        ),
        {
            "plancha": plancha,
            "retazo": retazo,
            "event": event,
            "reason": reason,
            "actor": actor,
            "optimization": optimization,
        },
    ).one()


def _assert_rejected(connection, *, event="BAJA_ROTURA", reason="Revisión", plancha=None,
                      retazo=None, actor=1, optimization=None):
    with pytest.raises(sa.exc.IntegrityError):
        with connection.begin_nested():
            _insert_movement(
                connection,
                event=event,
                reason=reason,
                plancha=plancha,
                retazo=retazo,
                actor=actor,
                optimization=optimization,
            )


def test_hu014_migration_constraints_indexes_and_audit_defaults(isolated_postgres):
    with new_database(isolated_postgres) as engine:
        result = upgrade(engine, REVISION)
        assert result.returncode == 0, result.stderr

        inspector = sa.inspect(engine)
        assert "movimientos_inventario" in inspector.get_table_names()
        checks = {item["name"]: item["sqltext"] for item in inspector.get_check_constraints(
            "movimientos_inventario"
        )}
        assert "ck_movimientos_inventario_recurso_xor" in checks
        assert "ck_movimientos_inventario_tipo_evento" in checks
        assert "ck_movimientos_inventario_motivo_no_vacio" in checks
        fks = {fk["name"]: fk["referred_table"] for fk in inspector.get_foreign_keys(
            "movimientos_inventario"
        )}
        assert fks == {
            "fk_movimientos_inventario_plancha": "planchas",
            "fk_movimientos_inventario_retazo": "retazos",
            "fk_movimientos_inventario_usuario": "usuarios",
            "fk_movimientos_inventario_optimizacion": "optimizaciones",
        }
        indexes = {item["name"]: item for item in inspector.get_indexes("movimientos_inventario")}
        assert indexes["uq_movimientos_baja_manual_plancha"]["unique"]
        assert indexes["uq_movimientos_baja_manual_retazo"]["unique"]
        assert "BAJA_RETIRO" in indexes["uq_movimientos_baja_manual_plancha"]["dialect_options"]["postgresql_where"]
        assert "CONSUMO_OPTIMIZACION" not in indexes["uq_movimientos_baja_manual_plancha"]["dialect_options"]["postgresql_where"]

        with engine.begin() as connection:
            _seed_resources(connection)

            plancha_movement = _insert_movement(connection, event="BAJA_ROTURA", plancha=1)
            retazo_movement = _insert_movement(connection, event="BAJA_MERMA", retazo=1)
            assert plancha_movement.id_movimiento and plancha_movement.fecha.tzinfo is not None
            assert retazo_movement.id_movimiento and retazo_movement.fecha.tzinfo is not None

            # Una segunda baja de cualquier tipo manual se rechaza por recurso.
            _assert_rejected(connection, event="BAJA_RETIRO", plancha=1)
            _assert_rejected(connection, event="BAJA_ERROR_REGISTRO", retazo=1)

            # El índice es parcial: el evento reservado no queda dentro de la unicidad manual.
            _insert_movement(connection, event="CONSUMO_OPTIMIZACION", plancha=2)
            _insert_movement(connection, event="CONSUMO_OPTIMIZACION", plancha=2)
            _insert_movement(connection, event="BAJA_RETIRO", plancha=2)
            _assert_rejected(connection, event="BAJA_ROTURA", plancha=2)

            _assert_rejected(connection, plancha=None, retazo=None)
            _assert_rejected(connection, plancha=1, retazo=1)
            _assert_rejected(connection, reason="   ", plancha=3, event="BAJA_MERMA")
            _assert_rejected(connection, reason=None, plancha=3, event="BAJA_MERMA")
            _assert_rejected(connection, event="EVENTO_DESCONOCIDO", plancha=3)
            _assert_rejected(connection, plancha=999)
            _assert_rejected(connection, retazo=999)
            _assert_rejected(connection, actor=999, plancha=3)
            _assert_rejected(connection, optimization=999, plancha=3)

            with pytest.raises(sa.exc.IntegrityError):
                with connection.begin_nested():
                    connection.exec_driver_sql("DELETE FROM planchas WHERE id_plancha=1")
            with pytest.raises(sa.exc.IntegrityError):
                with connection.begin_nested():
                    connection.exec_driver_sql("DELETE FROM retazos WHERE id_retazo=1")

            stored = connection.execute(sa.text(
                "SELECT id_usuario,observacion,id_optimizacion FROM movimientos_inventario "
                "WHERE id_movimiento=:id"
            ), {"id": plancha_movement.id_movimiento}).one()
            assert stored == (1, None, None)
