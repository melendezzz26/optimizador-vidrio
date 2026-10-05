"""TA-013: catálogo, API y migración sobre PostgreSQL temporal aislado."""

from collections import defaultdict
from decimal import Decimal
import os
import sys
from uuid import uuid4

from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import crear_token
from app.modules.inventory.application.dto import CreatePlancha, CreateRetazo, UpdatePlancha, UpdateRetazo
from app.modules.inventory.application.service import InventoryService
from app.modules.inventory.domain.exceptions import InventoryValidationError
from app.modules.inventory.presentation.dependencies import get_inventory_service
from tests.catalog_contract import EXPECTED_CATALOG
from tests.integration.inventory.test_repository import SqlAlchemyInventoryRepository
from tests.integration.postgres_support import BACKEND, _run, new_database, upgrade
from tests.model_contracts import current_metadata


R4 = "b4d5e6f7a8c9"
TA013 = "1c8754481a08"


def migration():
    config = Config()
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_heads() == [TA013]
    revision = scripts.get_revision(TA013)
    assert revision.down_revision == R4
    return revision.module


def persisted_catalog(connection):
    rows = connection.execute(sa.text(
        "SELECT tv.nombre, tve.espesor_mm FROM tipos_vidrio tv "
        "JOIN tipos_vidrio_espesores tve USING (id_tipo_vidrio) ORDER BY tve.espesor_mm"
    ))
    grouped = defaultdict(list)
    for name, thickness in rows:
        grouped[name].append(thickness)
    return {name: tuple(values) for name, values in grouped.items()}


def downgrade(engine):
    assert engine.url.host == "127.0.0.1" and engine.url.username == "r1_test"
    environment = {**os.environ, "DATABASE_URL": engine.url.render_as_string(hide_password=False),
                   "PYTHONIOENCODING": "utf-8"}
    return _run([sys.executable, "-B", "-m", "alembic", "downgrade", R4], cwd=BACKEND, env=environment)


@pytest.fixture(scope="module")
def catalog_db(isolated_postgres):
    assert isolated_postgres.host == "127.0.0.1" and isolated_postgres.username == "r1_test"
    with new_database(isolated_postgres) as engine:
        assert engine.url.host == "127.0.0.1" and engine.url.username == "r1_test"
        result = upgrade(engine, "head")
        assert result.returncode == 0, result.stderr
        yield engine


@pytest.fixture
def service(catalog_db):
    # Los casos de uso confirman savepoints; el rollback exterior aísla cada test.
    with catalog_db.connect() as connection:
        transaction = connection.begin()
        repo = SqlAlchemyInventoryRepository(
            lambda: Session(bind=connection, join_transaction_mode="create_savepoint"))
        try:
            yield InventoryService(repo)
        finally:
            transaction.rollback()


def test_seed_has_six_types_28_pairs_and_is_idempotent(catalog_db):
    with catalog_db.begin() as connection:
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == TA013
        before = connection.execute(sa.text("SELECT * FROM tipos_vidrio ORDER BY id_tipo_vidrio")).all()
        migration()._seed_catalog(connection)
        migration()._seed_catalog(connection)
        assert connection.execute(sa.text("SELECT * FROM tipos_vidrio ORDER BY id_tipo_vidrio")).all() == before
        assert len(before) == 6
        assert connection.scalar(sa.text("SELECT COUNT(*) FROM tipos_vidrio_espesores")) == 28
        assert persisted_catalog(connection) == EXPECTED_CATALOG
    result = upgrade(catalog_db, "head")
    assert result.returncode == 0, result.stderr


def test_orm_matches_migrated_schema_and_composite_constraints(catalog_db):
    with catalog_db.connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection, opts={
            "compare_type": True, "compare_server_default": True,
        }), current_metadata()) == []
    inspector = sa.inspect(catalog_db)
    assert inspector.get_pk_constraint("tipos_vidrio_espesores")["constrained_columns"] == ["id_tipo_vidrio", "espesor_mm"]
    for table in ("planchas", "retazos", "pedidos"):
        fks = inspector.get_foreign_keys(table)
        composite = next(fk for fk in fks if fk["name"] == f"fk_{table}_tipo_espesor")
        assert composite["referred_table"] == "tipos_vidrio_espesores"
        assert composite["constrained_columns"] == ["id_tipo_vidrio", "espesor_mm"]
        assert any(fk["referred_table"] == "tipos_vidrio" for fk in fks)
        assert f"ck_{table}_espesor" not in {check["name"] for check in inspector.get_check_constraints(table)}


@pytest.mark.parametrize("statement,code", [
    ("INSERT INTO tipos_vidrio(nombre) VALUES ('Incoloro')", "23505"),
    ("INSERT INTO tipos_vidrio_espesores SELECT id_tipo_vidrio, 3 FROM tipos_vidrio WHERE nombre='Incoloro'", "23505"),
    ("INSERT INTO tipos_vidrio_espesores SELECT id_tipo_vidrio, 0 FROM tipos_vidrio WHERE nombre='Incoloro'", "23514"),
])
def test_database_rejects_duplicates_and_nonpositive_thickness(catalog_db, statement, code):
    with pytest.raises(IntegrityError) as caught:
        with catalog_db.begin() as connection:
            connection.execute(sa.text(statement))
    assert caught.value.orig.sqlstate == code


def insert_record(connection, table, tipo, thickness):
    parameters = {"tipo": tipo, "espesor": Decimal(thickness), "codigo": str(uuid4())}
    statements = {
        "planchas": "INSERT INTO planchas(ancho_mm,alto_mm,espesor_mm,cantidad,fecha_registro,id_tipo_vidrio) VALUES (10,20,:espesor,1,CURRENT_TIMESTAMP,:tipo)",
        "retazos": "INSERT INTO retazos(codigo,espesor_mm,geometria,area_mm2,fecha_registro,id_tipo_vidrio) VALUES (:codigo,:espesor,'{}',200,CURRENT_TIMESTAMP,:tipo)",
        "pedidos": "INSERT INTO pedidos(fecha_registro,estado,espesor_mm,id_tipo_vidrio,id_usuario_registro) VALUES (CURRENT_TIMESTAMP,'PENDIENTE',:espesor,:tipo,1)",
    }
    connection.execute(sa.text(statements[table]), parameters)


def insert_user(connection):
    connection.execute(sa.text("INSERT INTO roles(id_rol,nombre) VALUES (1,'Operario')"))
    connection.execute(sa.text(
        "INSERT INTO usuarios(id_usuario,dni,nombres,apellidos,usuario,password_hash,id_rol,fecha_creacion) "
        "VALUES (1,'00000001','Prueba','Catalogo','p00000001','hash-sintetico',1,CURRENT_TIMESTAMP)"
    ))


@pytest.mark.parametrize("table", ["planchas", "retazos", "pedidos"])
def test_postgresql_enforces_type_thickness_for_all_consumers(catalog_db, table):
    with catalog_db.connect() as connection:
        transaction = connection.begin()
        try:
            if table == "pedidos":
                insert_user(connection)
            ids = dict(connection.execute(sa.text("SELECT nombre,id_tipo_vidrio FROM tipos_vidrio")).all())
            for name, value, valid in (
                ("Incoloro", "12", True), ("Incoloro", "2", False),
                ("Espejo", "2", True), ("Espejo", "8", False),
                ("Catedral", "3.5", True), ("Catedral", "4", False),
            ):
                if valid:
                    insert_record(connection, table, ids[name], value)
                else:
                    with pytest.raises(IntegrityError) as caught:
                        with connection.begin_nested():
                            insert_record(connection, table, ids[name], value)
                    assert caught.value.orig.diag.constraint_name == f"fk_{table}_tipo_espesor"
        finally:
            transaction.rollback()


def test_api_returns_persisted_catalog_and_controlled_compatibility_errors(service):
    from main import app

    old_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_inventory_service] = lambda: service
    headers = {"Authorization": f"Bearer {crear_token(1, 'testuser', 'Administrador')}"}
    try:
        with TestClient(app) as client:
            response = client.get("/api/inventory/tipos-vidrio", headers=headers)
            assert response.status_code == 200
            actual = {row["nombre"]: tuple(Decimal(str(v)) for v in row["espesores_mm"]) for row in response.json()}
            assert actual == EXPECTED_CATALOG
            ids = {row["nombre"]: row["id_tipo_vidrio"] for row in response.json()}
            result = client.post("/api/inventory/planchas", headers=headers, json={
                "ancho_mm": 100, "alto_mm": 50, "cantidad": 1,
                "id_tipo_vidrio": ids["Incoloro"], "espesor_mm": 12,
            })
            assert result.status_code == 201
            assert client.patch(f"/api/inventory/planchas/{result.json()['id_plancha']}",
                headers=headers, json={"id_tipo_vidrio": ids["Espejo"]}).status_code == 422
            result = client.post("/api/inventory/retazos", headers=headers, json={
                "codigo": "TA013", "espesor_mm": 3.5, "id_tipo_vidrio": ids["Catedral"],
                "geometria": {"type": "RECTANGULO", "width_mm": 10, "height_mm": 20},
            })
            assert result.status_code == 201
            assert client.patch(f"/api/inventory/retazos/{result.json()['id_retazo']}",
                headers=headers, json={"espesor_mm": 4}).status_code == 422
            assert client.patch(f"/api/inventory/retazos/{result.json()['id_retazo']}",
                headers=headers, json={"id_tipo_vidrio": ids["Espejo"], "espesor_mm": 2}).status_code == 200
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(old_overrides)


def test_service_new_type_has_no_implicit_thicknesses(service):
    from app.modules.inventory.application.dto import CreateTipoVidrio

    tipo = service.create_tipo_vidrio(CreateTipoVidrio(nombre="Personalizado"))
    assert tipo.espesores_mm == ()
    with pytest.raises(InventoryValidationError):
        service.create_plancha(CreatePlancha(ancho_mm=10, alto_mm=20, cantidad=1,
            id_tipo_vidrio=tipo.id_tipo_vidrio, espesor_mm=4))


@pytest.mark.parametrize("kind", ["plancha", "retazo"])
def test_service_patch_composes_pairs_against_real_catalog(service, kind):
    ids = {row.nombre: row.id_tipo_vidrio for row in service.list_tipos_vidrio()}
    command = (CreatePlancha(ancho_mm=10, alto_mm=20, cantidad=1, id_tipo_vidrio=ids["Incoloro"], espesor_mm=4)
        if kind == "plancha" else CreateRetazo(codigo="PATCH", geometria={"type": "CIRCUNFERENCIA", "radius_mm": 10},
                                              id_tipo_vidrio=ids["Incoloro"], espesor_mm=4))
    record = getattr(service, f"create_{kind}")(command)
    identifier = getattr(record, f"id_{kind}")
    patch = UpdatePlancha if kind == "plancha" else UpdateRetazo
    update = getattr(service, f"update_{kind}")
    assert update(identifier, patch(id_tipo_vidrio=ids["Espejo"])).espesor_mm == Decimal("4")
    with pytest.raises(InventoryValidationError):
        update(identifier, patch(id_tipo_vidrio=ids["Catedral"]))
    assert update(identifier, patch(espesor_mm=2)).espesor_mm == Decimal("2")
    with pytest.raises(InventoryValidationError):
        update(identifier, patch(espesor_mm=8))
    result = update(identifier, patch(id_tipo_vidrio=ids["Catedral"], espesor_mm=Decimal("3.5")))
    assert result.id_tipo_vidrio == ids["Catedral"] and result.espesor_mm == Decimal("3.5")


def test_upgrade_preserves_existing_inactive_type_and_rows(isolated_postgres):
    with new_database(isolated_postgres) as engine:
        assert upgrade(engine, R4).returncode == 0
        with engine.begin() as connection:
            identifier = connection.scalar(sa.text(
                "INSERT INTO tipos_vidrio(nombre,descripcion,estado) VALUES ('Incoloro',NULL,FALSE) RETURNING id_tipo_vidrio"))
            insert_record(connection, "planchas", identifier, "8")
            before = connection.execute(sa.text("SELECT * FROM planchas")).all()
        result = upgrade(engine, "head")
        assert result.returncode == 0, result.stderr
        with engine.connect() as connection:
            assert connection.execute(sa.text("SELECT id_tipo_vidrio,descripcion,estado FROM tipos_vidrio WHERE nombre='Incoloro'")).one() == (identifier, None, False)
            assert connection.execute(sa.text("SELECT * FROM planchas")).all() == before
            assert persisted_catalog(connection) == EXPECTED_CATALOG


@pytest.mark.parametrize("table", ["planchas", "retazos", "pedidos"])
def test_upgrade_aborts_and_rolls_back_incompatible_existing_data(isolated_postgres, table):
    with new_database(isolated_postgres) as engine:
        assert upgrade(engine, R4).returncode == 0
        with engine.begin() as connection:
            if table == "pedidos":
                insert_user(connection)
            identifier = connection.scalar(sa.text("INSERT INTO tipos_vidrio(nombre) VALUES ('Espejo') RETURNING id_tipo_vidrio"))
            insert_record(connection, table, identifier, "8")
            before = connection.execute(sa.text(f"SELECT * FROM {table}")).all()
        result = upgrade(engine, "head")
        assert result.returncode != 0 and f"TA-013 no puede migrar '{table}'" in result.stderr
        with engine.connect() as connection:
            assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == R4
            assert not sa.inspect(connection).has_table("tipos_vidrio_espesores")
            assert connection.execute(sa.text(f"SELECT * FROM {table}")).all() == before
            assert connection.scalar(sa.text("SELECT COUNT(*) FROM tipos_vidrio")) == 1


@pytest.mark.parametrize("table", ["planchas", "retazos", "pedidos"])
def test_downgrade_aborts_without_losing_new_thickness_data(isolated_postgres, table):
    with new_database(isolated_postgres) as engine:
        assert upgrade(engine, "head").returncode == 0
        with engine.begin() as connection:
            if table == "pedidos":
                insert_user(connection)
            identifier = connection.scalar(sa.text("SELECT id_tipo_vidrio FROM tipos_vidrio WHERE nombre='Incoloro'"))
            insert_record(connection, table, identifier, "12")
            before = connection.execute(sa.text(f"SELECT * FROM {table}")).all()
        result = downgrade(engine)
        assert result.returncode != 0 and "No se puede volver a v1.1" in result.stderr
        with engine.connect() as connection:
            assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == TA013
            assert connection.execute(sa.text(f"SELECT * FROM {table}")).all() == before
            assert persisted_catalog(connection) == EXPECTED_CATALOG


def test_safe_downgrade_preserves_types_and_legacy_compatible_rows(isolated_postgres):
    with new_database(isolated_postgres) as engine:
        assert upgrade(engine, "head").returncode == 0
        with engine.begin() as connection:
            identifier = connection.scalar(sa.text("SELECT id_tipo_vidrio FROM tipos_vidrio WHERE nombre='Espejo'"))
            insert_record(connection, "planchas", identifier, "4")
            before = connection.execute(sa.text("SELECT * FROM planchas")).all()
        result = downgrade(engine)
        assert result.returncode == 0, result.stderr
        with engine.connect() as connection:
            assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == R4
            assert connection.scalar(sa.text("SELECT COUNT(*) FROM tipos_vidrio")) == 6
            assert connection.execute(sa.text("SELECT * FROM planchas")).all() == before
            assert not sa.inspect(connection).has_table("tipos_vidrio_espesores")
            for table in ("planchas", "retazos", "pedidos"):
                assert f"ck_{table}_espesor" in {row["name"] for row in sa.inspect(connection).get_check_constraints(table)}
        assert upgrade(engine, "head").returncode == 0
        with engine.connect() as connection:
            assert persisted_catalog(connection) == EXPECTED_CATALOG
