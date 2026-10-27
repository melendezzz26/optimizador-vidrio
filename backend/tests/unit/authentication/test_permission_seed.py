"""S1-RBAC: la carga de permisos es idempotente y no deshace cambios del administrador."""
import pytest
from sqlalchemy import CheckConstraint, MetaData, create_engine, delete, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.permissions import ASIGNACION_INICIAL, CODIGOS
from app.models import Permiso, Rol, RolPermiso
from app.modules.authentication.infrastructure.permission_seed import seed_permissions

ROLES = ("Administrador", "Almacenero", "Operario")


@pytest.fixture
def make_session():
    """SQLite en memoria con roles, permisos y rol_permisos copiados del modelo real.

    Se quitan los CHECK porque usan sintaxis de PostgreSQL; se prueban en integración.
    """
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    metadata = MetaData()
    for table in (Rol.__table__, Permiso.__table__, RolPermiso.__table__):
        copy = table.to_metadata(metadata)
        for constraint in [c for c in copy.constraints if isinstance(c, CheckConstraint)]:
            copy.constraints.discard(constraint)
    metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    engine.dispose()


def add_roles(factory, names=ROLES):
    with factory() as db:
        db.add_all([Rol(nombre=name) for name in names])
        db.commit()


def assignment(factory) -> dict[str, set[str]]:
    with factory() as db:
        rows = db.execute(
            select(Rol.nombre, Permiso.codigo)
            .join(RolPermiso, RolPermiso.id_rol == Rol.id_rol)
            .join(Permiso, Permiso.id_permiso == RolPermiso.id_permiso)
        ).all()
    result = {name: set() for name in ROLES}
    for role, code in rows:
        result[role].add(code)
    return result


def remove_permission(factory, role, code):
    with factory() as db:
        role_id = db.scalar(select(Rol.id_rol).where(Rol.nombre == role))
        permission_id = db.scalar(select(Permiso.id_permiso).where(Permiso.codigo == code))
        db.execute(delete(RolPermiso).where(
            RolPermiso.id_rol == role_id, RolPermiso.id_permiso == permission_id,
        ))
        db.commit()


def test_new_database_gets_catalog_and_initial_assignment(make_session):
    add_roles(make_session)
    with make_session() as db:
        seed_permissions(db)
        assert set(db.scalars(select(Permiso.codigo))) == CODIGOS
    assert assignment(make_session) == {role: set(codes) for role, codes in ASIGNACION_INICIAL.items()}


def test_running_seed_twice_changes_nothing(make_session):
    add_roles(make_session)
    with make_session() as db:
        seed_permissions(db)
    before = assignment(make_session)
    with make_session() as db:
        seed_permissions(db)
        assert len(db.scalars(select(Permiso.id_permiso)).all()) == len(CODIGOS)
    assert assignment(make_session) == before


def test_seed_does_not_restore_a_permission_removed_by_the_administrator(make_session):
    add_roles(make_session)
    with make_session() as db:
        seed_permissions(db)
    remove_permission(make_session, "Almacenero", "inventory.manage")
    with make_session() as db:
        seed_permissions(db)
    assert "inventory.manage" not in assignment(make_session)["Almacenero"]


def test_roles_created_after_the_catalog_receive_their_initial_assignment(make_session):
    """Base nueva: la migración cargó los permisos cuando todavía no había roles."""
    with make_session() as db:
        seed_permissions(db)
    add_roles(make_session)
    with make_session() as db:
        seed_permissions(db)
    assert assignment(make_session) == {role: set(codes) for role, codes in ASIGNACION_INICIAL.items()}


def test_a_newly_added_catalog_permission_is_assigned_to_its_initial_roles(make_session):
    add_roles(make_session)
    with make_session() as db:
        seed_permissions(db)
        # Simula una base anterior a que existiera este código en el catálogo.
        db.execute(delete(Permiso).where(Permiso.codigo == "orders.cancel"))
        db.execute(delete(RolPermiso).where(~RolPermiso.id_permiso.in_(select(Permiso.id_permiso))))
        db.commit()
    with make_session() as db:
        seed_permissions(db)
    result = assignment(make_session)
    assert "orders.cancel" in result["Operario"]
    assert "orders.cancel" in result["Administrador"]
    assert "orders.cancel" not in result["Almacenero"]


# TA-039: el seed distingue una base nueva de un rol vaciado a propósito.

def empty_role(factory, role):
    """Deja el rol sin permisos, como un PUT de RN-06 con una lista vacía."""
    with factory() as db:
        role_id = db.scalar(select(Rol.id_rol).where(Rol.nombre == role))
        db.execute(delete(RolPermiso).where(RolPermiso.id_rol == role_id))
        db.commit()


@pytest.mark.parametrize("role", ["Almacenero", "Operario"])
def test_seed_does_not_refill_a_role_emptied_by_the_administrator(make_session, role):
    """CA-02: el rol sigue vacío después de 1 y de 2 ejecuciones."""
    add_roles(make_session)
    with make_session() as db:
        seed_permissions(db)
    empty_role(make_session, role)
    expected = assignment(make_session)
    for _ in range(2):
        with make_session() as db:
            seed_permissions(db)
        assert assignment(make_session) == expected
    assert assignment(make_session)[role] == set()


def test_seed_keeps_a_partially_configured_role(make_session):
    """CA-03: no recupera ninguno de los permisos retirados."""
    add_roles(make_session)
    with make_session() as db:
        seed_permissions(db)
    for code in ("orders.cancel", "optimization.execute", "optimization.confirm"):
        remove_permission(make_session, "Operario", code)
    expected = assignment(make_session)
    with make_session() as db:
        seed_permissions(db)
    assert assignment(make_session) == expected


def test_a_new_catalog_permission_reaches_an_emptied_role_alone(make_session):
    """CA-04 (P-02): el rol vacío recibe solo el permiso nuevo, no su asignación completa."""
    add_roles(make_session)
    with make_session() as db:
        seed_permissions(db)
        # Simula una base anterior a que existiera este código en el catálogo.
        db.execute(delete(Permiso).where(Permiso.codigo == "orders.cancel"))
        db.execute(delete(RolPermiso).where(~RolPermiso.id_permiso.in_(select(Permiso.id_permiso))))
        db.commit()
    empty_role(make_session, "Operario")
    with make_session() as db:
        seed_permissions(db)
    assert assignment(make_session)["Operario"] == {"orders.cancel"}


def test_a_role_created_by_this_seed_run_receives_its_initial_assignment(make_session):
    """CA-05: en una base ya inicializada, solo el rol recién creado recibe su asignación."""
    add_roles(make_session, ("Administrador", "Almacenero"))
    with make_session() as db:
        seed_permissions(db)
    empty_role(make_session, "Almacenero")
    with make_session() as db:
        db.add(Rol(nombre="Operario"))
        db.flush()
        seed_permissions(db, created_roles={"Operario"})
    result = assignment(make_session)
    assert result["Operario"] == set(ASIGNACION_INICIAL["Operario"])
    assert result["Almacenero"] == set()
    assert result["Administrador"] == set(ASIGNACION_INICIAL["Administrador"])