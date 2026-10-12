from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.modules.inventory.application.dto import MovimientoInventarioData
from app.modules.inventory.domain.exceptions import InventoryConflictError, InventoryNotFoundError
from app.modules.inventory.presentation.dependencies import get_inventory_service
from app.shared.security import decode_access_token
from main import app
from tests.auth_support import token_for, use_in_memory_accounts


class FakeWriteoffService:
    def __init__(self):
        self.calls = []

    def _writeoff(self, resource, identifier, command, id_usuario):
        if identifier == 404:
            raise InventoryNotFoundError("Recurso inexistente")
        if identifier == 409:
            raise InventoryConflictError("Recurso en conflicto")
        self.calls.append((resource, identifier, command, id_usuario))
        return MovimientoInventarioData(
            id_movimiento=10,
            id_plancha=identifier if resource == "plancha" else None,
            id_retazo=identifier if resource == "retazo" else None,
            tipo_evento=command.tipo_evento.value,
            motivo=command.motivo,
            observacion=command.observacion,
            id_usuario=id_usuario,
            fecha=datetime(2026, 10, 11, tzinfo=timezone.utc),
            id_optimizacion=None,
        )

    def writeoff_plancha(self, identifier, command, *, id_usuario):
        return self._writeoff("plancha", identifier, command, id_usuario)

    def writeoff_retazo(self, identifier, command, *, id_usuario):
        return self._writeoff("retazo", identifier, command, id_usuario)


@pytest.fixture
def writeoff_client():
    service = FakeWriteoffService()
    app.dependency_overrides[get_inventory_service] = lambda: service
    use_in_memory_accounts(app)
    try:
        with TestClient(app) as test_client:
            yield test_client, service
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "resource,role",
    [
        ("planchas", "Almacenero"),
        ("retazos", "Administrador"),
    ],
)
def test_manual_writeoff_uses_authenticated_actor_and_returns_audit_data(
    writeoff_client, resource, role,
):
    client, service = writeoff_client
    token = token_for(role)
    actor_id = int(decode_access_token(token)["sub"])

    response = client.post(
        f"/api/inventory/{resource}/7/baja",
        json={
            "tipo_evento": "BAJA_RETIRO",
            "motivo": "Retiro solicitado",
            "observacion": "Acta 123",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["estado"] is False
    assert payload["movimiento"]["id_usuario"] == actor_id
    assert payload["movimiento"]["tipo_evento"] == "BAJA_RETIRO"
    assert payload["movimiento"]["observacion"] == "Acta 123"
    assert service.calls[0][3] == actor_id


@pytest.mark.parametrize("resource", ["planchas", "retazos"])
@pytest.mark.parametrize(
    "body",
    [
        {"tipo_evento": "CONSUMO_OPTIMIZACION", "motivo": "Consumo"},
        {"tipo_evento": "BAJA_ROTURA", "motivo": "Rotura", "id_usuario": 999},
        {"tipo_evento": "BAJA_ROTURA", "motivo": "Rotura", "fecha": "2026-10-11T00:00:00Z"},
        {"tipo_evento": "BAJA_ROTURA", "motivo": "Rotura", "id_optimizacion": 1},
        {"tipo_evento": "BAJA_ROTURA", "motivo": "   "},
    ],
)
def test_manual_writeoff_rejects_reserved_or_client_owned_fields(writeoff_client, resource, body):
    client, service = writeoff_client
    token = token_for("Administrador")
    response = client.post(
        f"/api/inventory/{resource}/7/baja",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
    assert service.calls == []


@pytest.mark.parametrize("resource", ["planchas", "retazos"])
@pytest.mark.parametrize("identifier,expected", [(404, 404), (409, 409)])
def test_manual_writeoff_maps_not_found_and_conflict(writeoff_client, resource, identifier, expected):
    client, _service = writeoff_client
    token = token_for("Administrador")
    response = client.post(
        f"/api/inventory/{resource}/{identifier}/baja",
        json={"tipo_evento": "BAJA_ROTURA", "motivo": "Rotura"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == expected


@pytest.mark.parametrize("resource,role", [("planchas", "Operario"), ("retazos", "Operario")])
def test_manual_writeoff_requires_inventory_management_permission(writeoff_client, resource, role):
    client, service = writeoff_client
    token = token_for(role)
    response = client.post(
        f"/api/inventory/{resource}/7/baja",
        json={"tipo_evento": "BAJA_ROTURA", "motivo": "Rotura"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert service.calls == []
