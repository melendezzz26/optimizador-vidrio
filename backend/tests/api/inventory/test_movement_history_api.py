from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.modules.inventory.application.dto import MovimientoInventarioData
from app.modules.inventory.domain.exceptions import InventoryNotFoundError
from app.modules.inventory.presentation.dependencies import get_inventory_service
from main import app
from tests.auth_support import token_for, use_in_memory_accounts


class FakeMovementHistoryService:
    def __init__(self):
        self.calls = []

    def _list(self, kind, identifier):
        self.calls.append((kind, identifier))
        if identifier == 404:
            raise InventoryNotFoundError("Recurso inexistente")
        if identifier == 7:
            return []
        return [
            MovimientoInventarioData(
                id_movimiento=17,
                id_plancha=identifier if kind == "plancha" else None,
                id_retazo=identifier if kind == "retazo" else None,
                tipo_evento="CONSUMO_OPTIMIZACION",
                motivo="Evento histórico",
                observacion=None,
                id_usuario=23,
                fecha=datetime(2026, 10, 11, 8, 15, tzinfo=timezone.utc),
                id_optimizacion=None,
            ),
        ]

    def list_plancha_movements(self, identifier):
        return self._list("plancha", identifier)

    def list_retazo_movements(self, identifier):
        return self._list("retazo", identifier)


@pytest.fixture
def history_client():
    service = FakeMovementHistoryService()
    app.dependency_overrides[get_inventory_service] = lambda: service
    use_in_memory_accounts(app)
    try:
        with TestClient(app) as test_client:
            yield test_client, service
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("resource", ["planchas", "retazos"])
def test_movement_history_requires_authentication(history_client, resource):
    client, _service = history_client

    response = client.get(f"/api/inventory/{resource}/7/movimientos")

    assert response.status_code == 401


@pytest.mark.parametrize("resource,kind", [("planchas", "plancha"), ("retazos", "retazo")])
def test_movement_history_returns_empty_list_for_authorized_user(history_client, resource, kind):
    client, service = history_client
    token = token_for("Operario")

    response = client.get(
        f"/api/inventory/{resource}/7/movimientos",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == []
    assert service.calls == [(kind, 7)]


@pytest.mark.parametrize("resource,kind", [("planchas", "plancha"), ("retazos", "retazo")])
def test_movement_history_returns_audit_fields_and_resource_reference(
    history_client, resource, kind,
):
    client, service = history_client
    token = token_for("Administrador")

    response = client.get(
        f"/api/inventory/{resource}/8/movimientos",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert {key: value for key, value in payload[0].items() if key != "fecha"} == {
        "id_movimiento": 17,
        "cantidad_afectada": None,
        "id_plancha": 8 if kind == "plancha" else None,
        "id_retazo": 8 if kind == "retazo" else None,
        "tipo_evento": "CONSUMO_OPTIMIZACION",
        "motivo": "Evento histórico",
        "observacion": None,
        "id_usuario": 23,
        "id_optimizacion": None,
    }
    assert datetime.fromisoformat(payload[0]["fecha"].replace("Z", "+00:00")) == datetime(
        2026, 10, 11, 8, 15, tzinfo=timezone.utc,
    )
    assert service.calls == [(kind, 8)]


@pytest.mark.parametrize("resource", ["planchas", "retazos"])
def test_movement_history_maps_missing_resource_and_requires_stock_permission(history_client, resource):
    client, _service = history_client
    admin_token = token_for("Administrador")
    missing = client.get(
        f"/api/inventory/{resource}/404/movimientos",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert missing.status_code == 404

    unauthorized_token = token_for("UsuarioSinPermiso")
    forbidden = client.get(
        f"/api/inventory/{resource}/7/movimientos",
        headers={"Authorization": f"Bearer {unauthorized_token}"},
    )
    assert forbidden.status_code == 403
