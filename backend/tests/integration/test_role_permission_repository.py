"""S1-RBAC: el reemplazo de permisos es atómico (RN-07), sobre la base de prueba."""
import pytest
from sqlalchemy import select

from app.models import Permiso, RolPermiso
from app.modules.users.infrastructure.sqlalchemy_role_permission_repository import (
    SqlAlchemyRolePermissionRepository,
)

ROLE_IDS = {"Administrador": 1, "Almacenero": 2, "Operario": 3}  # Los de tests/conftest.py
WAREHOUSE = ROLE_IDS["Almacenero"]


def stored(session_factory) -> set[str]:
    with session_factory() as db:
        return set(db.scalars(
            select(Permiso.codigo)
            .join(RolPermiso, RolPermiso.id_permiso == Permiso.id_permiso)
            .where(RolPermiso.id_rol == WAREHOUSE)
        ))


def test_replace_overwrites_the_previous_set(session_factory):
    with session_factory() as db:
        role = SqlAlchemyRolePermissionRepository(db).replace_permissions(
            WAREHOUSE, frozenset({"orders.view"}),
        )
    assert role.permissions == {"orders.view"}
    assert stored(session_factory) == {"orders.view"}


def test_a_failure_while_inserting_rolls_back_the_delete(session_factory, monkeypatch):
    before = stored(session_factory)
    with session_factory() as db:
        repository = SqlAlchemyRolePermissionRepository(db)

        def fail(*args, **kwargs):
            raise RuntimeError("fallo simulado al insertar")

        monkeypatch.setattr(db, "add_all", fail)
        with pytest.raises(RuntimeError):
            repository.replace_permissions(WAREHOUSE, frozenset({"orders.view"}))
    # El DELETE previo se deshizo: no queda un estado intermedio.
    assert stored(session_factory) == before