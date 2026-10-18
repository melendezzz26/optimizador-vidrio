"""Restricción de rutas por permiso (HU-002 T02, SPEC-HU-003 RN-01)."""
import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.modules.authentication.presentation.dependencies import get_user_reader, require_permission
from app.shared.security import create_access_token
from tests.auth_support import InMemoryUserReader, token_for


@pytest.fixture
def client():
    app = FastAPI()

    @app.get("/solo-administrador")
    def protected(user=Depends(require_permission("GESTIONAR_USUARIOS"))):
        return {"rol": user.role}

    app.dependency_overrides[get_user_reader] = InMemoryUserReader
    with TestClient(app) as test_client:
        yield test_client


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_role_with_the_permission_is_allowed(client):
    response = client.get("/solo-administrador", headers=bearer(token_for("Administrador")))
    assert response.status_code == 200
    assert response.json() == {"rol": "Administrador"}


@pytest.mark.parametrize("role", ["Almacenero", "Operario"])
def test_role_without_the_permission_gets_403(client, role):
    response = client.get("/solo-administrador", headers=bearer(token_for(role)))
    assert response.status_code == 403
    assert response.json()["detail"] == "No tienes el permiso: GESTIONAR_USUARIOS"


def test_request_without_a_session_gets_401(client):
    assert client.get("/solo-administrador").status_code == 401


def test_permission_uses_the_current_role_and_not_the_one_in_the_token(client):
    # La cuenta es de un Operario, pero su token (emitido antes) dice Administrador.
    operator_token = token_for("Operario")
    operator_id = int(jwt.decode(operator_token, options={"verify_signature": False})["sub"])
    stale_token = create_access_token(operator_id, f"T{operator_id:08d}", "Administrador")
    assert client.get("/solo-administrador", headers=bearer(stale_token)).status_code == 403


def test_inventory_keeps_using_the_same_dependency():
    from app.modules.inventory.presentation import dependencies as inventory_dependencies

    assert inventory_dependencies.require_permission is require_permission
