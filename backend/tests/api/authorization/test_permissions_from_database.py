"""S1-RBAC: los permisos se leen de rol_permisos en la base (CA-01, CA-02, CA-05).

Usa la aplicación real con la base de prueba (SQLite) y el lector SQLAlchemy:
sin dobles de prueba para la autorización.
"""
import pytest
from sqlalchemy import delete, select

from app.core.permissions import ASIGNACION_INICIAL
from app.models import Permiso, Rol, RolPermiso
from app.modules.authentication.infrastructure.sqlalchemy_permission_reader import (
    SqlAlchemyPermissionReader,
)
from app.shared.security import create_access_token

ADMIN = "F70000001"
WAREHOUSE = "A70000002"
OPERATOR = "O70000003"


def bearer(user_id: int, username: str, role: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user_id, username, role)}"}


def _ids(db, role: str, code: str) -> tuple[int, int]:
    role_id = db.scalar(select(Rol.id_rol).where(Rol.nombre == role))
    permission_id = db.scalar(select(Permiso.id_permiso).where(Permiso.codigo == code))
    return role_id, permission_id


def grant(session_factory, role: str, code: str) -> None:
    with session_factory() as db:
        role_id, permission_id = _ids(db, role, code)
        db.add(RolPermiso(id_rol=role_id, id_permiso=permission_id))
        db.commit()


def revoke(session_factory, role: str, code: str) -> None:
    with session_factory() as db:
        role_id, permission_id = _ids(db, role, code)
        db.execute(delete(RolPermiso).where(
            RolPermiso.id_rol == role_id, RolPermiso.id_permiso == permission_id,
        ))
        db.commit()


@pytest.mark.parametrize("role", ["Administrador", "Almacenero", "Operario"])
def test_reader_returns_the_initial_assignment_stored_in_the_database(db_session, role):
    reader = SqlAlchemyPermissionReader(db_session)
    assert reader.permissions_for_role(role) == ASIGNACION_INICIAL[role]
    assert reader.permissions_for_role("RolInexistente") == frozenset()


def test_reader_answers_by_role_and_code(db_session):
    reader = SqlAlchemyPermissionReader(db_session)
    assert reader.role_has_permission("Administrador", "roles.manage")
    assert reader.role_has_permission("Almacenero", "inventory.manage")
    assert not reader.role_has_permission("Almacenero", "users.view")
    assert not reader.role_has_permission("Operario", "codigo.inexistente")


def test_users_endpoint_follows_the_database_without_logging_in_again(client, create_user, session_factory):
    admin_id = create_user(ADMIN, "Administrador")
    warehouse_id = create_user(WAREHOUSE, "Almacenero")
    admin = bearer(admin_id, ADMIN, "Administrador")
    warehouse = bearer(warehouse_id, WAREHOUSE, "Almacenero")

    assert client.get("/api/users", headers=admin).status_code == 200
    assert client.get("/api/users", headers=warehouse).status_code == 403

    # El administrador concede users.view al Almacenero: rige en la siguiente petición.
    grant(session_factory, "Almacenero", "users.view")
    assert client.get("/api/users", headers=warehouse).status_code == 200
    # Ver no es gestionar: crear sigue prohibido.
    assert client.post("/api/users", json={}, headers=warehouse).status_code == 403

    revoke(session_factory, "Almacenero", "users.view")
    assert client.get("/api/users", headers=warehouse).status_code == 403


def test_removing_a_permission_from_the_administrator_also_applies(client, create_user, session_factory):
    """Ningún rol tiene acceso por su nombre: también el Administrador depende de rol_permisos."""
    admin_id = create_user(ADMIN, "Administrador")
    admin = bearer(admin_id, ADMIN, "Administrador")
    revoke(session_factory, "Administrador", "users.view")
    assert client.get("/api/users", headers=admin).status_code == 403


def test_a_forged_token_role_does_not_grant_permissions(client, create_user):
    """CA-06 (token alterado): el rol se toma de la base, no del token."""
    operator_id = create_user(OPERATOR, "Operario")
    forged = bearer(operator_id, OPERATOR, "Administrador")
    response = client.get("/api/users", headers=forged)
    assert response.status_code == 403
    assert response.json() == {"detail": "No tienes permiso para realizar esta acción."}