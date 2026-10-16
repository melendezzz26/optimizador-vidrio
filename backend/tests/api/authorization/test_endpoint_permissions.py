"""S1-RBAC: cada endpoint exige el permiso del mapa de la SPEC (§4.4), leído de la base.

Para cada endpoint se usa una cuenta de un rol de prueba con permisos a medida:
- con todos los permisos MENOS el exigido → 403 (CA-03);
- con SOLO el permiso exigido → la autorización lo deja pasar (CA-04).
  La respuesta puede ser 404 o 422 porque no se envían datos reales: lo que
  importa es que no sea 401 ni 403.
"""
import pytest
from fastapi.testclient import TestClient

from app.core.permissions import CODIGOS
from app.modules.authentication.presentation.dependencies import get_permission_reader
from main import app
from tests.auth_support import InMemoryPermissionReader, token_for, use_in_memory_accounts

ROLE = "RolDePrueba"

ENDPOINTS = [
    ("GET", "/api/users", "users.view"),
    ("GET", "/api/users/roles", "users.view"),
    ("GET", "/api/users/1", "users.view"),
    ("POST", "/api/users", "users.manage"),
    ("PATCH", "/api/users/1", "users.manage"),
    ("GET", "/api/inventory/tipos-vidrio", "inventory.view"),
    ("GET", "/api/inventory/planchas", "inventory.view"),
    ("GET", "/api/inventory/planchas/1/movimientos", "inventory.view"),
    ("GET", "/api/inventory/retazos", "inventory.view"),
    ("GET", "/api/inventory/retazos/1/movimientos", "inventory.view"),
    ("POST", "/api/inventory/tipos-vidrio", "inventory.manage"),
    ("POST", "/api/inventory/planchas", "inventory.manage"),
    ("PATCH", "/api/inventory/planchas/1", "inventory.manage"),
    ("POST", "/api/inventory/planchas/1/baja", "inventory.manage"),
    ("POST", "/api/inventory/retazos", "inventory.manage"),
    ("PATCH", "/api/inventory/retazos/1", "inventory.manage"),
    ("POST", "/api/inventory/retazos/1/baja", "inventory.manage"),
    ("GET", "/api/orders", "orders.view"),
    ("GET", "/api/orders/1", "orders.view"),
    ("GET", "/api/clients", "orders.view"),
    ("POST", "/api/orders", "orders.create"),
    ("POST", "/api/clients", "orders.create"),
    ("PUT", "/api/orders/1", "orders.update"),
    ("DELETE", "/api/orders/1", "orders.cancel"),
    ("POST", "/api/optimization/start", "optimization.execute"),
    ("POST", "/api/optimization/rasterize", "optimization.execute"),
    ("POST", "/api/optimization/runs", "optimization.execute"),
    ("GET", "/api/optimization/runs/1", "optimization.view"),
    ("GET", "/api/roles", "roles.view"),
    ("GET", "/api/permissions", "roles.view"),
    ("PUT", "/api/roles/1/permissions", "roles.manage"),
]


class _FailingDependency:
    """Sustituye servicios y repositorios: si la autorización deja pasar, no toca ninguna base."""

    def __getattr__(self, name):
        raise LookupError("Sin datos en esta prueba")


@pytest.fixture
def client_with(monkeypatch):
    """Cliente cuyo rol de prueba tiene exactamente los permisos indicados."""
    from app.modules.optimization.presentation.run_routes import get_run_unit_of_work
    from app.modules.optimization.presentation.run_auth import get_run_user_reader, get_run_permission_reader
    from app.modules.authentication.presentation.dependencies import get_user_reader
    from app.modules.clients.presentation.dependencies import get_client_repository
    from app.modules.inventory.presentation.dependencies import get_inventory_service
    from app.modules.users.presentation.dependencies import (
        get_role_permission_repository,
        get_user_repository,
    )

    def _client(permissions: set[str]) -> TestClient:
        use_in_memory_accounts(app)
        app.dependency_overrides[get_permission_reader] = (
            lambda: InMemoryPermissionReader({ROLE: frozenset(permissions)})
        )
        app.dependency_overrides[get_run_user_reader] = app.dependency_overrides[get_user_reader]
        app.dependency_overrides[get_run_permission_reader] = app.dependency_overrides[get_permission_reader]
        for dependency in (get_inventory_service, get_user_repository, get_client_repository,
                           get_role_permission_repository, get_run_unit_of_work):
            app.dependency_overrides[dependency] = _FailingDependency
        return TestClient(app, raise_server_exceptions=False)

    yield _client
    app.dependency_overrides.clear()


def call(client, method, path):
    return client.request(method, path, headers={"Authorization": f"Bearer {token_for(ROLE)}"})


def test_endpoint_map_uses_only_catalog_codes_and_covers_every_code_with_an_endpoint():
    used = {code for _, _, code in ENDPOINTS}
    assert used <= CODIGOS
    # Códigos sin endpoint todavía: llegan con resultados y confirmación de optimización.
    assert CODIGOS - used == {"optimization.confirm"}


@pytest.mark.parametrize("method, path, code", ENDPOINTS)
def test_without_the_required_permission_the_endpoint_answers_403(client_with, method, path, code):
    response = call(client_with(set(CODIGOS) - {code}), method, path)
    assert response.status_code == 403, response.text


@pytest.mark.parametrize("method, path, code", ENDPOINTS)
def test_with_only_the_required_permission_authorization_lets_the_request_through(
    client_with, method, path, code,
):
    response = call(client_with({code}), method, path)
    assert response.status_code not in (401, 403), response.text


def test_without_any_permission_every_endpoint_answers_403(client_with):
    client = client_with(set())
    assert {call(client, method, path).status_code for method, path, _ in ENDPOINTS} == {403}