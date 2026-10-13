from sqlalchemy import CheckConstraint
from sqlalchemy.dialects import postgresql

from app.models import MovimientoInventario


def test_movement_model_declares_contract_fields_and_server_timestamp():
    table = MovimientoInventario.__table__

    assert set(table.columns.keys()) == {
        "id_movimiento",
        "cantidad_afectada",
        "id_plancha",
        "id_retazo",
        "tipo_evento",
        "motivo",
        "observacion",
        "id_usuario",
        "fecha",
        "id_optimizacion",
    }
    assert table.c.id_movimiento.primary_key
    assert table.c.id_plancha.nullable and table.c.id_retazo.nullable
    assert not table.c.tipo_evento.nullable
    assert not table.c.motivo.nullable
    assert table.c.observacion.nullable
    assert not table.c.id_usuario.nullable
    assert table.c.id_optimizacion.nullable
    assert table.c.fecha.type.timezone
    assert table.c.fecha.server_default is not None
    assert {fk.target_fullname for fk in table.foreign_keys} == {
        "planchas.id_plancha",
        "retazos.id_retazo",
        "usuarios.id_usuario",
        "optimizaciones.id_optimizacion",
    }
    assert all(fk.ondelete is None for fk in table.foreign_keys)


def test_xor_and_event_constraints_are_declared_in_database_metadata():
    table = MovimientoInventario.__table__
    checks = {constraint.name: str(constraint.sqltext) for constraint in table.constraints
              if isinstance(constraint, CheckConstraint)}

    assert "(id_plancha IS NOT NULL) <> (id_retazo IS NOT NULL)" in checks.values()
    event_check = checks["ck_movimientos_inventario_tipo_evento"]
    assert all(event in event_check for event in (
        "BAJA_ROTURA", "BAJA_MERMA", "BAJA_ERROR_REGISTRO",
        "BAJA_RETIRO", "CONSUMO_OPTIMIZACION",
    ))
    assert "length(trim(motivo)) > 0" in checks.values()


def test_manual_baja_indexes_are_partial_and_exclude_optimization_consumption():
    table = MovimientoInventario.__table__
    indexes = {index.name: index for index in table.indexes}
    assert "uq_movimientos_baja_manual_plancha" not in indexes
    manual_events = (
        "BAJA_ROTURA", "BAJA_MERMA", "BAJA_ERROR_REGISTRO", "BAJA_RETIRO"
    )

    for name, resource_column in (
        ("uq_movimientos_baja_manual_retazo", "id_retazo"),
    ):
        index = indexes[name]
        assert index.unique
        assert [column.name for column in index.columns] == [resource_column]
        predicate = str(index.dialect_options["postgresql"]["where"].compile(
            dialect=postgresql.dialect()
        ))
        assert all(event in predicate for event in manual_events)
        assert "CONSUMO_OPTIMIZACION" not in predicate


def test_movement_has_orm_relationships_for_contract_references():
    assert set(MovimientoInventario.__mapper__.relationships.keys()) == {
        "plancha", "retazo", "usuario", "optimizacion"
    }
