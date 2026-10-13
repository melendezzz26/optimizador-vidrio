"""Adaptador Inventory contra PostgreSQL temporal real, nunca destinos remotos."""

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import sys
from threading import Barrier
from types import ModuleType
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, declarative_base

from app.modules.inventory.application.dto import (
    CreatePlancha, CreateRetazo, CreateTipoVidrio, PlanchaData, RetazoData,
    TipoVidrioData, UpdatePlancha, UpdateRetazo,
)
from app.modules.inventory.application.service import InventoryService
from app.modules.inventory.domain.exceptions import InventoryConflictError, InventoryNotFoundError
from app.modules.inventory.domain.writeoff import BajaManual, TipoEventoBajaManual
from tests.integration.postgres_support import new_database, upgrade
from tests.integration.test_r4_migration import insert_r3_context


# Igual que tests/model_contracts.py: cargar los modelos reales con solo Base,
# sin ejecutar shared.database.session (carga .env y construye un engine global).
isolated_base = ModuleType("app.shared.database")
isolated_base.Base = declarative_base()
with patch.dict(sys.modules, {"app.shared.database": isolated_base}):
    from app.models import MovimientoInventario
    from app.modules.inventory.infrastructure.repository import SqlAlchemyInventoryRepository


NOW = datetime(2026, 10, 5, 12, 30, tzinfo=timezone.utc)
HEAD = "ta036a1b2c3d"


@pytest.fixture(scope="module")
def inventory_database(isolated_postgres):
    assert isolated_postgres.host == "127.0.0.1"
    assert isolated_postgres.username == "r1_test"
    with new_database(isolated_postgres) as engine:
        assert engine.url.host == "127.0.0.1" and engine.url.username == "r1_test"
        result = upgrade(engine, "head")
        assert result.returncode == 0, result.stderr
        with engine.connect() as connection:
            assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == HEAD
        yield engine


@pytest.fixture
def engine(inventory_database):
    # Limpieza solo en la base sintética creada por new_database.
    assert inventory_database.url.host == "127.0.0.1"
    assert inventory_database.url.username == "r1_test"
    with inventory_database.begin() as connection:
        connection.exec_driver_sql("TRUNCATE TABLE roles, tipos_vidrio RESTART IDENTITY CASCADE")
    yield inventory_database


class TrackedSession(Session):
    closed_by_repository = False

    def close(self):
        self.closed_by_repository = True
        super().close()


@pytest.fixture
def repository(engine):
    sessions = []

    def factory():
        session = TrackedSession(bind=engine, expire_on_commit=True)
        sessions.append(session)
        return session

    return SqlAlchemyInventoryRepository(factory), sessions


def create_tipo(repo, nombre="Claro", estado=True):
    tipo = repo.create_tipo_vidrio(nombre=nombre, descripcion=None, estado=estado)
    seed_test_thicknesses(repo, tipo.id_tipo_vidrio)
    return repo.get_tipo_vidrio(tipo.id_tipo_vidrio)


def seed_test_thicknesses(repo, identifier):
    # Combinaciones sintéticas explícitas para probar el adaptador, no datos base.
    repo._require_session().execute(sa.text(
        "INSERT INTO tipos_vidrio_espesores(id_tipo_vidrio, espesor_mm) "
        "VALUES (:id, :espesor)"
    ), [{"id": identifier, "espesor": Decimal(value)} for value in ("3", "4", "5.5", "6", "8")])


def plancha_values(tipo, **changes):
    return dict(ancho_mm=Decimal("1000.25"), alto_mm=Decimal("500.75"),
                espesor_mm=Decimal("5.5"), cantidad=2, estado=True,
                fecha_registro=NOW, id_tipo_vidrio=tipo) | changes


def retazo_values(tipo, **changes):
    return dict(codigo="R-001", espesor_mm=Decimal("4"),
                geometria={"type": "POLIGONO_CONVEXO", "vertices_mm": [[0, 0], [4, 0], [0, 3]]},
                area_mm2=Decimal("6.00"), estado=True, fecha_registro=NOW,
                id_tipo_vidrio=tipo, id_ejecucion_origen=None) | changes


def seed_writeoff_actor(engine):
    with engine.begin() as connection:
        connection.exec_driver_sql("INSERT INTO roles(id_rol,nombre) VALUES (1,'Administrador')")
        connection.exec_driver_sql(
            """INSERT INTO usuarios(
                id_usuario,dni,nombres,apellidos,usuario,password_hash,id_rol,fecha_creacion
            ) VALUES (1,'12345678','Admin','Inventory','A12345678','hash',1,CURRENT_TIMESTAMP)"""
        )


def create_writeoff_resources(repo):
    with repo.transaction():
        tipo = create_tipo(repo)
        plancha = repo.create_plancha(**plancha_values(tipo.id_tipo_vidrio, cantidad=1))
        retazo = repo.create_retazo(**retazo_values(tipo.id_tipo_vidrio))
    return plancha, retazo


def writeoff_command():
    return BajaManual(
        tipo_evento=TipoEventoBajaManual.BAJA_ROTURA,
        motivo="Daño detectado en inspección",
        observacion="Acta de almacén",
        cantidad_afectada=1,
    )


def assert_released(engine, sessions):
    assert sessions and all(session.closed_by_repository for session in sessions)
    assert all(not session.in_transaction() for session in sessions)
    assert engine.pool.checkedout() == 0


def test_real_unique_constraint_names(engine):
    inspector = sa.inspect(engine)
    assert {c["name"] for c in inspector.get_unique_constraints("tipos_vidrio")} == {"tipos_vidrio_nombre_key"}
    assert {c["name"] for c in inspector.get_unique_constraints("retazos")} == {"retazos_codigo_key"}


def test_tipo_roundtrip_exact_name_and_unfiltered_list(repository, engine):
    repo, sessions = repository
    with repo.transaction():
        active = repo.create_tipo_vidrio(nombre="Claro", descripcion="Descripción", estado=True)
        inactive = create_tipo(repo, nombre="claro", estado=False)
        assert type(active) is TipoVidrioData and active.id_tipo_vidrio > 0
        assert repo.tipo_nombre_exists("Claro") and repo.tipo_nombre_exists("claro")
        assert not repo.tipo_nombre_exists("CLARO") and not repo.tipo_nombre_exists("ausente")
    with repo.transaction():
        assert repo.get_tipo_vidrio(active.id_tipo_vidrio) == active
        assert repo.get_tipo_vidrio(999999) is None
        assert {item.id_tipo_vidrio: item for item in repo.list_tipos_vidrio()} == {
            active.id_tipo_vidrio: active, inactive.id_tipo_vidrio: inactive}
    assert len(sessions) == 2
    assert_released(engine, sessions)


def test_duplicate_tipo_is_translated_and_whole_transaction_rolls_back(repository, engine):
    repo, sessions = repository
    with repo.transaction():
        create_tipo(repo)
    with pytest.raises(InventoryConflictError) as caught:
        with repo.transaction():
            create_tipo(repo, nombre="Debe revertirse")
            create_tipo(repo)
    assert isinstance(caught.value.__cause__, IntegrityError)
    assert caught.value.__cause__.orig.diag.constraint_name == "tipos_vidrio_nombre_key"
    with repo.transaction():
        assert not repo.tipo_nombre_exists("Debe revertirse")
        assert len(repo.list_tipos_vidrio()) == 1
    assert_released(engine, sessions)


def test_plancha_roundtrip_updates_only_editable_fields(repository, engine):
    repo, sessions = repository
    with repo.transaction():
        tipo = create_tipo(repo)
        other = create_tipo(repo, nombre="Otro")
        original = repo.create_plancha(**plancha_values(tipo.id_tipo_vidrio))
        assert type(original) is PlanchaData and original.id_plancha > 0
    with repo.transaction():
        assert repo.get_plancha(original.id_plancha) == original
        assert repo.get_plancha(999999) is None
        assert original.fecha_registro.utcoffset() == timedelta(0)
        assert all(isinstance(getattr(original, field), Decimal)
                   for field in ("ancho_mm", "alto_mm", "espesor_mm"))
        updated = repo.save_plancha(replace(original, ancho_mm=Decimal("2000.75"),
            alto_mm=Decimal("1000.25"), espesor_mm=Decimal("8"), cantidad=0, estado=False,
            id_tipo_vidrio=other.id_tipo_vidrio, fecha_registro=NOW + timedelta(days=1)))
        assert updated.fecha_registro == NOW and updated.id_plancha == original.id_plancha
    with repo.transaction():
        assert repo.get_plancha(original.id_plancha) == updated
        assert repo.list_planchas() == [updated]
        assert updated.cantidad == 0 and updated.estado is False
        assert updated.id_tipo_vidrio == other.id_tipo_vidrio
    assert_released(engine, sessions)


def test_retazo_roundtrip_defensive_copy_exact_code_and_update(repository, engine):
    repo, sessions = repository
    geometry = retazo_values(1)["geometria"]
    expected_geometry = deepcopy(geometry)
    with repo.transaction():
        tipo = create_tipo(repo)
        original = repo.create_retazo(**retazo_values(tipo.id_tipo_vidrio, geometria=geometry))
        assert type(original) is RetazoData and original.id_retazo > 0
        assert original.area_mm2 == Decimal("6.00") and isinstance(original.area_mm2, Decimal)
        assert original.id_ejecucion_origen is None
        geometry["vertices_mm"][0][0] = 999
        original.geometria["vertices_mm"][1][0] = 999
        assert repo.get_retazo(original.id_retazo).geometria == expected_geometry
        assert repo.retazo_codigo_exists("R-001")
        assert not repo.retazo_codigo_exists("r-001")
        assert not repo.retazo_codigo_exists("R-001", exclude_id=original.id_retazo)
        assert repo.retazo_codigo_exists("R-001", exclude_id=999999)
        assert not repo.retazo_codigo_exists("ausente")
    with repo.transaction():
        current = repo.get_retazo(original.id_retazo)
        assert current.geometria == expected_geometry and current.fecha_registro == NOW
        assert current.fecha_registro.utcoffset() == timedelta(0)
        assert repo.get_retazo(999999) is None
        listed = repo.list_retazos()
        listed[0].geometria["vertices_mm"][0][0] = 777
        assert repo.get_retazo(original.id_retazo).geometria == expected_geometry
        new_geometry = {"type": "RECTANGULO", "width_mm": 10, "height_mm": 20}
        updated = repo.save_retazo(replace(current, codigo="R-002", espesor_mm=Decimal("6"),
            geometria=new_geometry, area_mm2=Decimal("200.00"), estado=False,
            fecha_registro=NOW + timedelta(days=1), id_ejecucion_origen=999999))
        new_geometry["width_mm"] = 999
        assert updated.geometria["width_mm"] == 10
        assert updated.id_retazo == current.id_retazo and updated.fecha_registro == NOW
        assert updated.id_ejecucion_origen is None
    with repo.transaction():
        assert repo.get_retazo(updated.id_retazo) == updated
        assert repo.list_retazos() == [updated] and updated.estado is False
    assert_released(engine, sessions)


def test_retazo_preserves_existing_nonnull_origin(repository, engine):
    repo, _ = repository
    with engine.begin() as connection:
        insert_r3_context(connection, with_catalog=True, with_piece_material=True)
    with repo.transaction():
        original = repo.create_retazo(**retazo_values(1, id_ejecucion_origen=1))
    with repo.transaction():
        updated = repo.save_retazo(replace(original, estado=False, id_ejecucion_origen=None))
    with repo.transaction():
        assert repo.get_retazo(original.id_retazo) == updated
        assert updated.id_ejecucion_origen == 1


@pytest.mark.parametrize("operation", ["create", "save"])
def test_duplicate_retazo_is_translated_on_create_and_update(repository, engine, operation):
    repo, sessions = repository
    with repo.transaction():
        tipo = create_tipo(repo)
        first = repo.create_retazo(**retazo_values(tipo.id_tipo_vidrio))
        second = repo.create_retazo(**retazo_values(tipo.id_tipo_vidrio, codigo="R-002"))
    with pytest.raises(InventoryConflictError) as caught:
        with repo.transaction():
            if operation == "create":
                repo.create_retazo(**retazo_values(tipo.id_tipo_vidrio))
            else:
                repo.save_retazo(replace(second, codigo=first.codigo))
    assert caught.value.__cause__.orig.sqlstate == "23505"
    assert caught.value.__cause__.orig.diag.constraint_name == "retazos_codigo_key"
    with repo.transaction():
        assert len(repo.list_retazos()) == 2
        assert repo.get_retazo(second.id_retazo) == second
    assert_released(engine, sessions)


def test_save_missing_records_never_inserts(repository):
    repo, _ = repository
    missing_plancha = PlanchaData(id_plancha=999999, **plancha_values(1))
    missing_retazo = RetazoData(id_retazo=999999, **retazo_values(1))
    for method, value in ((repo.save_plancha, missing_plancha), (repo.save_retazo, missing_retazo)):
        with pytest.raises(InventoryNotFoundError):
            with repo.transaction():
                method(value)
    with repo.transaction():
        assert repo.list_planchas() == [] and repo.list_retazos() == []


def test_save_detects_record_deleted_since_snapshot(repository, engine):
    repo, sessions = repository
    with repo.transaction():
        tipo = create_tipo(repo)
        snapshot = repo.create_plancha(**plancha_values(tipo.id_tipo_vidrio))
    with repo.transaction():
        stale = repo.get_plancha(snapshot.id_plancha)
        with engine.begin() as connection:
            connection.execute(sa.text("DELETE FROM planchas WHERE id_plancha = :id"), {"id": snapshot.id_plancha})
        with pytest.raises(InventoryNotFoundError):
            repo.save_plancha(replace(stale, cantidad=0))
    assert_released(engine, sessions)


def test_body_exception_rolls_back_and_instance_is_reusable(repository, engine):
    repo, sessions = repository
    with pytest.raises(RuntimeError, match="fallo del cuerpo"):
        with repo.transaction():
            create_tipo(repo)
            raise RuntimeError("fallo del cuerpo")
    assert_released(engine, sessions)
    with repo.transaction():
        assert repo.list_tipos_vidrio() == []
        create_tipo(repo, nombre="Recuperado")
    with repo.transaction():
        assert repo.tipo_nombre_exists("Recuperado")
    assert_released(engine, sessions)


@pytest.mark.parametrize("failure,sqlstate", [("check", "23514"), ("foreign-key", "23503"), ("other-unique", "23505")])
def test_unexpected_integrity_errors_are_not_conflicts(repository, engine, failure, sqlstate):
    repo, sessions = repository
    with pytest.raises(IntegrityError) as caught:
        with repo.transaction():
            tipo = create_tipo(repo)
            if failure == "check":
                repo.create_plancha(**plancha_values(tipo.id_tipo_vidrio, cantidad=-1))
            elif failure == "foreign-key":
                repo.create_plancha(**plancha_values(999999))
            else:
                sessions[-1].execute(sa.text("INSERT INTO roles(id_rol,nombre) VALUES (1,'Uno'), (1,'Dos')"))
    assert caught.value.orig.sqlstate == sqlstate
    with repo.transaction():
        assert repo.list_tipos_vidrio() == [] and repo.list_planchas() == []
    assert_released(engine, sessions)


def test_integrity_error_during_commit_is_translated_and_rolled_back(repository, engine):
    repo, sessions = repository
    with pytest.raises(InventoryConflictError):
        with repo.transaction():
            create_tipo(repo)

            def conflict_at_commit(session):
                session.execute(sa.text("INSERT INTO tipos_vidrio(nombre) VALUES ('Claro')"))

            sa.event.listen(sessions[-1], "before_commit", conflict_at_commit, once=True)
    assert_released(engine, sessions)
    with repo.transaction():
        assert repo.list_tipos_vidrio() == []


def test_nested_transaction_rejected_without_replacing_session(repository, engine):
    repo, sessions = repository
    with repo.transaction():
        first = create_tipo(repo)
        with pytest.raises(RuntimeError, match="(?i)(anidad|activa)"):
            with repo.transaction():
                pytest.fail("No debe entrar en una transacción anidada")
        assert len(sessions) == 1
        assert repo.get_tipo_vidrio(first.id_tipo_vidrio) == first
    assert_released(engine, sessions)


def test_all_repository_methods_require_transaction(repository):
    repo, sessions = repository
    operations = [
        lambda: repo.get_tipo_vidrio(1), lambda: repo.tipo_nombre_exists("Claro"),
        lambda: create_tipo(repo), repo.list_tipos_vidrio,
        lambda: repo.get_plancha(1), lambda: repo.create_plancha(**plancha_values(1)),
        repo.list_planchas, lambda: repo.save_plancha(PlanchaData(id_plancha=1, **plancha_values(1))),
        lambda: repo.get_retazo(1), lambda: repo.retazo_codigo_exists("R-001"),
        lambda: repo.create_retazo(**retazo_values(1)), repo.list_retazos,
        lambda: repo.save_retazo(RetazoData(id_retazo=1, **retazo_values(1))),
    ]
    for operation in operations:
        with pytest.raises(RuntimeError, match="transaction"):
            operation()
    assert sessions == []


def test_service_complete_flow_with_decimal_geometry_and_fresh_repository(repository, engine):
    repo, _ = repository
    service = InventoryService(repo, now=lambda: NOW)
    tipo = service.create_tipo_vidrio(CreateTipoVidrio(nombre="Claro"))
    with repo.transaction():
        seed_test_thicknesses(repo, tipo.id_tipo_vidrio)
        tipo = repo.get_tipo_vidrio(tipo.id_tipo_vidrio)
    plancha = service.create_plancha(CreatePlancha(ancho_mm=Decimal("1000.25"), alto_mm=500,
        espesor_mm=Decimal("5.5"), cantidad=2, id_tipo_vidrio=tipo.id_tipo_vidrio))

    geometry = {"type": "RECTANGULO", "width_mm": Decimal("1000.25"), "height_mm": 20}
    retazo = service.create_retazo(CreateRetazo(codigo="MANUAL", geometria=geometry,
        espesor_mm=4, id_tipo_vidrio=tipo.id_tipo_vidrio))

    expected_geometry = {"type": "RECTANGULO", "width_mm": 1000.25, "height_mm": 20}
    assert retazo.geometria == expected_geometry
    assert retazo.area_mm2 == Decimal("20005.00")

    assert service.list_tipos_vidrio() == [tipo]
    assert service.list_planchas() == [plancha]
    assert service.list_retazos() == [retazo]

    plancha = service.update_plancha(plancha.id_plancha, UpdatePlancha(cantidad=0, estado=False))
    retazo = service.update_retazo(retazo.id_retazo, UpdateRetazo(
        geometria={"type": "CIRCUNFERENCIA", "radius_mm": Decimal("10")}, estado=False))

    fresh = InventoryService(SqlAlchemyInventoryRepository(lambda: Session(engine)))
    assert fresh.list_planchas() == [plancha]
    assert fresh.list_retazos() == [retazo]

    assert retazo.geometria["radius_mm"] == 10
    assert retazo.area_mm2 == Decimal("314.16") and retazo.id_ejecucion_origen is None

def test_geometria_is_native_jsonb_without_decimal_wrapper(repository, engine):
    repo, _ = repository
    with repo.transaction():
        tipo = create_tipo(repo)
        geometry = {"type": "POLIGONO_CONVEXO", "vertices_mm": [[0, 0], [Decimal("10.5"), 0], [0, Decimal("20.25")]]}
        original = repo.create_retazo(**retazo_values(tipo.id_tipo_vidrio, geometria=geometry))

    with engine.begin() as conn:
        raw_json = conn.scalar(sa.text("SELECT geometria::text FROM retazos WHERE id_retazo = :id"), {"id": original.id_retazo})
        assert "__decimal__" not in raw_json
        assert '"type": "POLIGONO_CONVEXO"' in raw_json

        import json
        parsed = json.loads(raw_json)
        assert parsed["vertices_mm"][1][0] == 10.5
        assert parsed["vertices_mm"][2][1] == 20.25


@pytest.mark.parametrize("kind", ["plancha", "retazo"])
def test_writeoff_persists_movement_and_deactivates_resource_atomically(repository, engine, kind):
    repo, _sessions = repository
    seed_writeoff_actor(engine)
    plancha, retazo = create_writeoff_resources(repo)
    resource = plancha if kind == "plancha" else retazo
    identifier = resource.id_plancha if kind == "plancha" else resource.id_retazo

    movement = getattr(InventoryService(repo), f"writeoff_{kind}")(
        identifier, writeoff_command(), id_usuario=1,
    ).movimiento

    assert movement.id_plancha == (identifier if kind == "plancha" else None)
    assert movement.id_retazo == (identifier if kind == "retazo" else None)
    assert movement.id_usuario == 1
    assert movement.tipo_evento == "BAJA_ROTURA"
    assert movement.fecha.utcoffset() == timedelta(0)
    with engine.connect() as connection:
        state_column = "estado"
        table = "planchas" if kind == "plancha" else "retazos"
        id_column = "id_plancha" if kind == "plancha" else "id_retazo"
        assert connection.scalar(
            sa.text(f"SELECT {state_column} FROM {table} WHERE {id_column}=:id"),
            {"id": identifier},
        ) is False
        assert connection.scalar(
            sa.text("SELECT count(*) FROM movimientos_inventario WHERE id_movimiento=:id"),
            {"id": movement.id_movimiento},
        ) == 1
        assert connection.scalar(
            sa.text(f"SELECT count(*) FROM {table} WHERE {id_column}=:id"),
            {"id": identifier},
        ) == 1


@pytest.mark.parametrize("kind", ["plancha", "retazo"])
def test_writeoff_not_found_inactive_without_history_and_duplicate_conflict(repository, engine, kind):
    repo, _sessions = repository
    seed_writeoff_actor(engine)
    plancha, retazo = create_writeoff_resources(repo)
    resource = plancha if kind == "plancha" else retazo
    identifier = resource.id_plancha if kind == "plancha" else resource.id_retazo
    service = InventoryService(repo)
    writeoff = getattr(service, f"writeoff_{kind}")

    with pytest.raises(InventoryNotFoundError):
        writeoff(999999, writeoff_command(), id_usuario=1)

    patch_type = UpdatePlancha(estado=False) if kind == "plancha" else UpdateRetazo(estado=False)
    getattr(service, f"update_{kind}")(identifier, patch_type)

    # El estado inactivo heredado no equivale a una baja histórica.
    table = "planchas" if kind == "plancha" else "retazos"
    id_column = "id_plancha" if kind == "plancha" else "id_retazo"
    with engine.connect() as connection:
        assert connection.scalar(
            sa.text(f"SELECT estado FROM {table} WHERE {id_column}=:id"),
            {"id": identifier},
        ) is False
        assert connection.scalar(
            sa.text(
                "SELECT count(*) FROM movimientos_inventario "
                f"WHERE {id_column}=:id"
            ),
            {"id": identifier},
        ) == 0

    command = writeoff_command()
    if kind == "plancha":
        with pytest.raises(InventoryConflictError):
            writeoff(identifier, command, id_usuario=1)
        return
    movement = writeoff(identifier, command, id_usuario=1).movimiento
    assert movement.id_plancha == (identifier if kind == "plancha" else None)
    assert movement.id_retazo == (identifier if kind == "retazo" else None)
    assert movement.id_usuario == 1
    assert movement.tipo_evento == "BAJA_ROTURA"
    assert movement.motivo == command.motivo
    assert movement.observacion == command.observacion

    # Una baja confirmada sí impide una segunda baja.
    with pytest.raises(InventoryConflictError):
        writeoff(identifier, writeoff_command(), id_usuario=1)

    with engine.connect() as connection:
        assert connection.scalar(
            sa.text(f"SELECT estado FROM {table} WHERE {id_column}=:id"),
            {"id": identifier},
        ) is False
        rows = connection.execute(
            sa.text(
                "SELECT id_movimiento, id_usuario, tipo_evento, motivo, observacion "
                f"FROM movimientos_inventario WHERE {id_column}=:id"
            ),
            {"id": identifier},
        ).all()
        assert [tuple(row) for row in rows] == [
            (
                movement.id_movimiento,
                1,
                "BAJA_ROTURA",
                command.motivo,
                command.observacion,
            )
        ]


@pytest.mark.parametrize("kind", ["plancha", "retazo"])
def test_legacy_inactive_resource_without_writeoff_can_be_reactivated(repository, engine, kind):
    repo, _sessions = repository
    plancha, retazo = create_writeoff_resources(repo)
    resource = plancha if kind == "plancha" else retazo
    identifier = resource.id_plancha if kind == "plancha" else resource.id_retazo
    service = InventoryService(repo)
    inactive = UpdatePlancha(estado=False) if kind == "plancha" else UpdateRetazo(estado=False)
    active = UpdatePlancha(estado=True) if kind == "plancha" else UpdateRetazo(estado=True)

    assert getattr(service, f"update_{kind}")(identifier, inactive).estado is False
    assert getattr(service, f"update_{kind}")(identifier, active).estado is True
    with engine.connect() as connection:
        assert connection.scalar(sa.text("SELECT count(*) FROM movimientos_inventario")) == 0


@pytest.mark.parametrize("kind", ["plancha", "retazo"])
def test_manual_writeoff_prevents_reactivation_and_preserves_history(repository, engine, kind):
    repo, _sessions = repository
    seed_writeoff_actor(engine)
    plancha, retazo = create_writeoff_resources(repo)
    resource = plancha if kind == "plancha" else retazo
    identifier = resource.id_plancha if kind == "plancha" else resource.id_retazo
    resource_table = "planchas" if kind == "plancha" else "retazos"
    resource_id_column = "id_plancha" if kind == "plancha" else "id_retazo"
    service = InventoryService(repo)
    command = writeoff_command()

    movement = getattr(service, f"writeoff_{kind}")(
        identifier, command, id_usuario=1,
    ).movimiento

    def persisted_snapshot():
        with engine.connect() as connection:
            state = connection.scalar(
                sa.text(
                    f"SELECT estado FROM {resource_table} "
                    f"WHERE {resource_id_column} = :id"
                ),
                {"id": identifier},
            )
            rows = connection.execute(
                sa.text(
                    "SELECT id_movimiento, id_usuario, tipo_evento, motivo, "
                    "id_plancha, id_retazo "
                    "FROM movimientos_inventario "
                    f"WHERE {resource_id_column} = :id ORDER BY id_movimiento"
                ),
                {"id": identifier},
            ).all()
        return state, [tuple(row) for row in rows]

    state_before_reactivation, movements_before_reactivation = persisted_snapshot()
    assert state_before_reactivation is False
    assert len(movements_before_reactivation) == 1
    assert movements_before_reactivation[0] == (
        movement.id_movimiento,
        1,
        "BAJA_ROTURA",
        command.motivo,
        identifier if kind == "plancha" else None,
        identifier if kind == "retazo" else None,
    )

    patch = UpdatePlancha(estado=True) if kind == "plancha" else UpdateRetazo(estado=True)
    with pytest.raises(InventoryConflictError):
        getattr(service, f"update_{kind}")(identifier, patch)

    state_after_reactivation, movements_after_reactivation = persisted_snapshot()
    assert state_after_reactivation is False
    assert movements_after_reactivation == movements_before_reactivation
    assert len(movements_after_reactivation) == 1


@pytest.mark.parametrize("kind", ["plancha", "retazo"])
@pytest.mark.parametrize("failure", ["movement", "resource_update"])
def test_writeoff_failures_roll_back_both_rows(repository, engine, monkeypatch, kind, failure):
    repo, _sessions = repository
    seed_writeoff_actor(engine)
    plancha, retazo = create_writeoff_resources(repo)
    resource = plancha if kind == "plancha" else retazo
    identifier = resource.id_plancha if kind == "plancha" else resource.id_retazo

    if failure == "movement":
        original = getattr(repo, f"create_{kind}_writeoff_movement")

        def fail_after_movement(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError("fallo tras insertar movimiento")

        monkeypatch.setattr(repo, f"create_{kind}_writeoff_movement", fail_after_movement)
    else:
        original = getattr(repo, f"save_{kind}")

        def fail_after_state_update(data):
            original(data)
            raise RuntimeError("fallo tras actualizar recurso")

        monkeypatch.setattr(repo, f"save_{kind}", fail_after_state_update)

    with pytest.raises(RuntimeError):
        getattr(InventoryService(repo), f"writeoff_{kind}")(
            identifier, writeoff_command(), id_usuario=1,
        )

    with engine.connect() as connection:
        table = "planchas" if kind == "plancha" else "retazos"
        id_column = "id_plancha" if kind == "plancha" else "id_retazo"
        assert connection.scalar(
            sa.text(f"SELECT estado FROM {table} WHERE {id_column}=:id"),
            {"id": identifier},
        ) is True
        assert connection.scalar(sa.text("SELECT count(*) FROM movimientos_inventario")) == 0


@pytest.mark.parametrize("kind", ["plancha", "retazo"])
def test_concurrent_writeoffs_serialize_on_resource_row_lock(repository, engine, kind):
    repo, _sessions = repository
    seed_writeoff_actor(engine)
    plancha, retazo = create_writeoff_resources(repo)
    resource = plancha if kind == "plancha" else retazo
    identifier = resource.id_plancha if kind == "plancha" else resource.id_retazo
    barrier = Barrier(2)
    lock_queries = []

    def capture_lock(_conn, _cursor, statement, _parameters, _context, _executemany):
        sql = statement.upper()
        if "FOR UPDATE" in sql and ("PLANCHAS" in sql or "RETAZOS" in sql):
            lock_queries.append(sql)

    sa.event.listen(engine, "before_cursor_execute", capture_lock)

    def attempt():
        barrier.wait(timeout=10)
        service = InventoryService(SqlAlchemyInventoryRepository(lambda: Session(engine)))
        try:
            getattr(service, f"writeoff_{kind}")(
                identifier, writeoff_command(), id_usuario=1,
            )
            return "success"
        except InventoryConflictError:
            return "conflict"

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(lambda _index: attempt(), range(2)))
    finally:
        sa.event.remove(engine, "before_cursor_execute", capture_lock)

    assert sorted(outcomes) == ["conflict", "success"]
    assert len(lock_queries) == 2
    with engine.connect() as connection:
        assert connection.scalar(sa.text("SELECT count(*) FROM movimientos_inventario")) == 1


@pytest.mark.parametrize("kind", ["retazo"])
def test_partial_unique_index_violation_maps_to_inventory_conflict(repository, engine, kind):
    repo, _sessions = repository
    seed_writeoff_actor(engine)
    plancha, retazo = create_writeoff_resources(repo)
    resource = plancha if kind == "plancha" else retazo
    identifier = resource.id_plancha if kind == "plancha" else resource.id_retazo
    create_movement = getattr(repo, f"create_{kind}_writeoff_movement")

    with pytest.raises(InventoryConflictError) as caught:
        with repo.transaction():
            for _ in range(2):
                create_movement(
                    identifier,
                    tipo_evento="BAJA_RETIRO",
                    motivo="Retiro",
                    observacion=None,
                    id_usuario=1,
                )

    assert isinstance(caught.value.__cause__, IntegrityError)
    with engine.connect() as connection:
        assert connection.scalar(sa.text("SELECT count(*) FROM movimientos_inventario")) == 0


@pytest.mark.parametrize("kind", ["plancha", "retazo"])
def test_movement_history_is_empty_for_existing_resource_and_not_found_otherwise(repository, engine, kind):
    repo, sessions = repository
    plancha, retazo = create_writeoff_resources(repo)
    resource = plancha if kind == "plancha" else retazo
    identifier = resource.id_plancha if kind == "plancha" else resource.id_retazo
    service = InventoryService(repo)

    assert getattr(service, f"list_{kind}_movements")(identifier) == []
    with pytest.raises(InventoryNotFoundError):
        getattr(service, f"list_{kind}_movements")(999999)

    assert_released(engine, sessions)


@pytest.mark.parametrize("kind", ["plancha", "retazo"])
def test_movement_history_is_isolated_chronological_and_read_only(repository, engine, kind):
    repo, sessions = repository
    seed_writeoff_actor(engine)
    plancha, retazo = create_writeoff_resources(repo)
    target = plancha if kind == "plancha" else retazo
    other = retazo if kind == "plancha" else plancha
    other_kind = "retazo" if kind == "plancha" else "plancha"
    target_id = target.id_plancha if kind == "plancha" else target.id_retazo
    other_id = other.id_retazo if kind == "plancha" else other.id_plancha
    repeated_timestamp = NOW + timedelta(hours=1)
    latest_timestamp = NOW + timedelta(hours=2)

    def movement_for(resource_kind, identifier, event, reason, date, observation):
        return MovimientoInventario(
            id_plancha=identifier if resource_kind == "plancha" else None,
            id_retazo=identifier if resource_kind == "retazo" else None,
            tipo_evento=event,
            motivo=reason,
            observacion=observation,
            id_usuario=1,
            fecha=date,
            id_optimizacion=None,
        )

    # Sembrar el evento reservado prueba lectura histórica, no habilita su creación por API.
    first_tie = movement_for(
        kind, target_id, "CONSUMO_OPTIMIZACION", "Evento anterior A",
        repeated_timestamp, None,
    )
    later = movement_for(
        kind, target_id, "BAJA_ROTURA", "Rotura registrada",
        latest_timestamp, "Acta 81",
    )
    second_tie = movement_for(
        kind, target_id, "CONSUMO_OPTIMIZACION", "Evento anterior B",
        repeated_timestamp, "Nota B",
    )
    other_resource_movement = movement_for(
        "retazo" if kind == "plancha" else "plancha",
        other_id,
        "BAJA_MERMA",
        "Movimiento del otro recurso",
        NOW,
        None,
    )
    with Session(engine) as seed_session:
        with seed_session.begin():
            seed_session.add_all([later, first_tie, other_resource_movement, second_tie])
            seed_session.flush()
            expected_ids = [
                row.id_movimiento
                for row in sorted(
                    [first_tie, later, second_tie],
                    key=lambda row: (row.fecha, row.id_movimiento),
                )
            ]
            other_movement_id = other_resource_movement.id_movimiento

    writes = []

    def capture_writes(_conn, _cursor, statement, _parameters, _context, _executemany):
        operation = statement.lstrip().split(None, 1)[0].upper()
        if operation in {"INSERT", "UPDATE", "DELETE", "TRUNCATE"}:
            writes.append(statement)

    sa.event.listen(engine, "before_cursor_execute", capture_writes)
    try:
        history = getattr(InventoryService(repo), f"list_{kind}_movements")(target_id)
        other_history = getattr(InventoryService(repo), f"list_{other_kind}_movements")(other_id)
    finally:
        sa.event.remove(engine, "before_cursor_execute", capture_writes)

    assert writes == []
    assert [item.id_movimiento for item in history] == expected_ids
    assert all(
        item.id_plancha == (target_id if kind == "plancha" else None)
        and item.id_retazo == (target_id if kind == "retazo" else None)
        for item in history
    )
    assert [(item.tipo_evento, item.motivo, item.observacion, item.id_usuario, item.fecha.utcoffset(), item.id_optimizacion)
            for item in history] == [
        ("CONSUMO_OPTIMIZACION", "Evento anterior A", None, 1, timedelta(0), None),
        ("CONSUMO_OPTIMIZACION", "Evento anterior B", "Nota B", 1, timedelta(0), None),
        ("BAJA_ROTURA", "Rotura registrada", "Acta 81", 1, timedelta(0), None),
    ]
    assert [item.id_movimiento for item in other_history] == [other_movement_id]
    assert other_history[0].motivo == "Movimiento del otro recurso"
    assert_released(engine, sessions)

@pytest.mark.parametrize("quantity,remaining", [(1, 9), (4, 6), (10, 0)])
def test_partial_writeoff_postgres_balance_history_and_order(repository, engine, quantity, remaining):
    repo, _sessions = repository
    seed_writeoff_actor(engine)
    plancha, retazo = create_writeoff_resources(repo)
    service = InventoryService(repo)
    service.update_plancha(plancha.id_plancha, UpdatePlancha(cantidad=10))
    result = service.writeoff_plancha(plancha.id_plancha, BajaManual(
        tipo_evento="BAJA_MERMA", motivo="Baja parcial", cantidad_afectada=quantity), id_usuario=1)
    assert result.cantidad == remaining and result.estado is (remaining > 0)
    with engine.connect() as connection:
        assert connection.execute(sa.text("SELECT cantidad,estado FROM planchas")).one() == (remaining, remaining > 0)
        assert connection.scalar(sa.text("SELECT cantidad_afectada FROM movimientos_inventario")) == quantity
    assert service.list_plancha_movements(plancha.id_plancha) == [result.movimiento]
    service.writeoff_retazo(retazo.id_retazo, BajaManual(tipo_evento="BAJA_RETIRO", motivo="Retiro"), id_usuario=1)
    other = service.create_retazo(CreateRetazo(codigo="Disponible", espesor_mm=4,
        id_tipo_vidrio=retazo.id_tipo_vidrio, geometria=retazo.geometria))
    assert [r.id_retazo for r in service.list_retazos()] == [other.id_retazo, retazo.id_retazo]
    assert service.list_retazo_movements(retazo.id_retazo)[0].cantidad_afectada == 1


def test_concurrent_partial_writeoffs_do_not_overspend_balance(repository, engine):
    repo, _sessions = repository
    seed_writeoff_actor(engine)
    plancha, _retazo = create_writeoff_resources(repo)
    InventoryService(repo).update_plancha(plancha.id_plancha, UpdatePlancha(cantidad=10))
    barrier = Barrier(2)
    from app.modules.inventory.domain.exceptions import InventoryValidationError
    def attempt(_index):
        service = InventoryService(SqlAlchemyInventoryRepository(lambda: Session(engine)))
        barrier.wait(timeout=10)
        try:
            return service.writeoff_plancha(plancha.id_plancha, BajaManual(
                tipo_evento="BAJA_ROTURA", motivo="Concurrente", cantidad_afectada=6), id_usuario=1).cantidad
        except InventoryValidationError:
            return "rejected"
    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(attempt, range(2)))
    assert sorted(map(str, outcomes)) == ["4", "rejected"]
    with engine.connect() as connection:
        assert connection.scalar(sa.text("SELECT cantidad FROM planchas")) == 4
        assert connection.scalar(sa.text("SELECT count(*) FROM movimientos_inventario")) == 1


def test_plancha_order_is_available_then_date_and_id_desc(repository):
    repo, _sessions = repository
    with repo.transaction():
        tipo = create_tipo(repo)
        unavailable = repo.create_plancha(**plancha_values(tipo.id_tipo_vidrio, estado=False))
        older = repo.create_plancha(**plancha_values(tipo.id_tipo_vidrio, fecha_registro=NOW-timedelta(days=1)))
        zero = repo.create_plancha(**plancha_values(tipo.id_tipo_vidrio, cantidad=0))
        newest = repo.create_plancha(**plancha_values(tipo.id_tipo_vidrio))
        tie = repo.create_plancha(**plancha_values(tipo.id_tipo_vidrio))
        rows = repo.list_planchas()
    assert [r.id_plancha for r in rows] == [tie.id_plancha, newest.id_plancha, older.id_plancha, zero.id_plancha, unavailable.id_plancha]
