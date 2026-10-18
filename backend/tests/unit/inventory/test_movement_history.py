from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.modules.inventory.application.dto import MovimientoInventarioData
from app.modules.inventory.application.service import InventoryService
from app.modules.inventory.domain.exceptions import InventoryNotFoundError
from app.modules.inventory.infrastructure.repository import SqlAlchemyInventoryRepository


class FakeMovementHistoryRepository:
    def __init__(self, plancha_history=None, retazo_history=None):
        self.histories = {
            "plancha": plancha_history if plancha_history is not None else {},
            "retazo": retazo_history if retazo_history is not None else {},
        }
        self.read_sessions = 0
        self.read_rollbacks = 0

    @contextmanager
    def read_transaction(self):
        self.read_sessions += 1
        try:
            yield
        finally:
            self.read_rollbacks += 1

    def transaction(self):
        raise AssertionError("El historial debe usar una sesión de solo lectura.")

    def list_plancha_movements(self, identifier):
        return self.histories["plancha"].get(identifier)

    def list_retazo_movements(self, identifier):
        return self.histories["retazo"].get(identifier)


def movement_data(**changes):
    values = {
        "id_movimiento": 41,
        "id_plancha": 7,
        "id_retazo": None,
        "tipo_evento": "BAJA_ROTURA",
        "motivo": "Daño detectado",
        "observacion": "Inspección de almacén",
        "id_usuario": 12,
        "fecha": datetime(2026, 10, 11, 9, 30, tzinfo=timezone.utc),
        "id_optimizacion": None,
    }
    return MovimientoInventarioData(**(values | changes))


@pytest.mark.parametrize("kind", ["plancha", "retazo"])
def test_history_service_preserves_repository_dtos_and_uses_read_session(kind):
    movement = movement_data(
        id_plancha=7 if kind == "plancha" else None,
        id_retazo=7 if kind == "retazo" else None,
    )
    histories = {7: [movement]}
    repo = FakeMovementHistoryRepository(
        plancha_history=histories if kind == "plancha" else {7: []},
        retazo_history=histories if kind == "retazo" else {7: []},
    )
    service = InventoryService(repo)

    result = getattr(service, f"list_{kind}_movements")(7)

    assert result == [movement]
    assert result[0] == movement
    assert repo.read_sessions == 1
    assert repo.read_rollbacks == 1


@pytest.mark.parametrize("kind", ["plancha", "retazo"])
def test_history_service_returns_empty_for_existing_resource(kind):
    repo = FakeMovementHistoryRepository(
        plancha_history={7: []}, retazo_history={7: []},
    )

    assert getattr(InventoryService(repo), f"list_{kind}_movements")(7) == []


@pytest.mark.parametrize("kind", ["plancha", "retazo"])
def test_history_service_returns_not_found_for_missing_resource(kind):
    repo = FakeMovementHistoryRepository()

    with pytest.raises(InventoryNotFoundError):
        getattr(InventoryService(repo), f"list_{kind}_movements")(404)

    assert repo.read_sessions == 1
    assert repo.read_rollbacks == 1


def test_repository_movement_mapping_preserves_audit_fields():
    row = SimpleNamespace(
        id_movimiento=5,
        id_plancha=None,
        id_retazo=9,
        tipo_evento="CONSUMO_OPTIMIZACION",
        motivo="Consumo reservado para el flujo futuro",
        observacion=None,
        id_usuario=3,
        fecha=datetime(2026, 10, 10, 14, 20, tzinfo=timezone.utc),
        id_optimizacion=22,
        cantidad_afectada=None,
    )

    result = SqlAlchemyInventoryRepository._to_movement(row)

    assert result == MovimientoInventarioData(
        id_movimiento=5,
        id_plancha=None,
        id_retazo=9,
        tipo_evento="CONSUMO_OPTIMIZACION",
        motivo="Consumo reservado para el flujo futuro",
        observacion=None,
        id_usuario=3,
        fecha=row.fecha,
        id_optimizacion=22,
    )
