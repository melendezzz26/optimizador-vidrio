"""Restricción de rutas por permiso leído de la base (S1-RBAC; antes HU-002 T02)."""
import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.modules.authentication.presentation.dependencies import (
    get_permission_reader,
    get_user_reader,
    require_permission,
)
from app.shared.security import create_access_token
from tests.auth_support import InMemoryPermissionReader, InMemoryUserReader, token_for

FORBIDDEN = "No tienes permiso para realizar esta acción."


@pytest.fixture
def assignment():
    """Permisos por rol de esta prueba; se pueden cambiar entre peticiones."""
    return {"Administrador": {"users.manage"}, "Almacenero": set(), "Operario": set()}


@pytest.fixture
def client(assignment):
    app = FastAPI()

    @app.get("/gestion-usuarios")
    def protected(user=Depends(require_permission("users.manage"))):
        return {"rol": user.role}

    app.dependency_overrides[get_user_reader] = InMemoryUserReader
    app.dependency_overrides[get_permission_reader] = lambda: InMemoryPermissionReader(assignment)
    with TestClient(app) as test_client:
        yield test_client


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_role_with_the_permission_is_allowed(client):
    response = client.get("/gestion-usuarios", headers=bearer(token_for("Administrador")))
    assert response.status_code == 200
    assert response.json() == {"rol": "Administrador"}


@pytest.mark.parametrize("role", ["Almacenero", "Operario"])
def test_role_without_the_permission_gets_403_with_a_generic_message(client, role):
    response = client.get("/gestion-usuarios", headers=bearer(token_for(role)))
    assert response.status_code == 403
    # No revela qué permiso falta (PLAN §2.4).
    assert response.json() == {"detail": FORBIDDEN}


def test_request_without_a_session_gets_401(client):
    assert client.get("/gestion-usuarios").status_code == 401


def test_permission_uses_the_current_role_and_not_the_one_in_the_token(client):
    # La cuenta es de un Operario, pero su token (emitido antes) dice Administrador.
    operator_token = token_for("Operario")
    operator_id = int(jwt.decode(operator_token, options={"verify_signature": False})["sub"])
    stale_token = create_access_token(operator_id, f"T{operator_id:08d}", "Administrador")
    assert client.get("/gestion-usuarios", headers=bearer(stale_token)).status_code == 403


def test_a_permission_change_applies_on_the_next_request_with_the_same_token(client, assignment):
    """RN-02: no hay caché ni hace falta volver a iniciar sesión."""
    token = token_for("Almacenero")
    assert client.get("/gestion-usuarios", headers=bearer(token)).status_code == 403
    assignment["Almacenero"].add("users.manage")
    assert client.get("/gestion-usuarios", headers=bearer(token)).status_code == 200
    assignment["Almacenero"].discard("users.manage")
    assert client.get("/gestion-usuarios", headers=bearer(token)).status_code == 403


def test_the_administrator_role_name_alone_grants_nothing(client, assignment):
    """La autorización depende de rol_permisos, no del nombre del rol."""
    assignment["Administrador"].clear()
    response = client.get("/gestion-usuarios", headers=bearer(token_for("Administrador")))
    assert response.status_code == 403


@pytest.mark.parametrize("code", ["GESTIONAR_USUARIOS", "users.delete", ""])
def test_unknown_permission_codes_fail_when_the_route_is_declared(code):
    """RN-08 / CA-11: un código fuera del catálogo rompe la importación, no la producción."""
    with pytest.raises(ValueError, match="Permiso desconocido"):
        require_permission(code)


def test_inventory_keeps_using_the_same_dependency():
    from app.modules.inventory.presentation import dependencies as inventory_dependencies

    assert inventory_dependencies.require_permission is require_permission