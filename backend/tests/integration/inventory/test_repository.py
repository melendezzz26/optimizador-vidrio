"""Adaptador Inventory contra PostgreSQL temporal real, nunca destinos remotos."""

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import sys
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
from tests.integration.postgres_support import new_database, upgrade
from tests.integration.test_r4_migration import insert_r3_context


# Igual que tests/model_contracts.py: cargar los modelos reales con solo Base,
# sin ejecutar shared.database.session (carga .env y construye un engine global).
isolated_base = ModuleType("app.shared.database")
isolated_base.Base = declarative_base()
with patch.dict(sys.modules, {"app.shared.database": isolated_base}):
    from app.modules.inventory.infrastructure.repository import SqlAlchemyInventoryRepository


NOW = datetime(2026, 10, 5, 12, 30, tzinfo=timezone.utc)
HEAD = "b4d5e6f7a8c9"


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
    return repo.create_tipo_vidrio(nombre=nombre, descripcion=None, estado=estado)


def plancha_values(tipo, **changes):
    return dict(ancho_mm=Decimal("1000.25"), alto_mm=Decimal("500.75"),
                espesor_mm=Decimal("5.5"), cantidad=2, estado=True,
                fecha_registro=NOW, id_tipo_vidrio=tipo) | changes


def retazo_values(tipo, **changes):
    return dict(codigo="R-001", espesor_mm=Decimal("4"),
                geometria={"type": "POLIGONO_CONVEXO", "vertices_mm": [[0, 0], [4, 0], [0, 3]]},
                area_mm2=Decimal("6.00"), estado=True, fecha_registro=NOW,
                id_tipo_vidrio=tipo, id_ejecucion_origen=None) | changes


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
        insert_r3_context(connection)
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
