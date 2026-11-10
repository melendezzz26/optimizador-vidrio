"""TA-QA-006: un rechazo por rol no confirma cortes ni consume stock real (CA-03, D-03).

Corre con PostgreSQL de pruebas (CI); en Windows se omite. Cada caso tiene un
control positivo con el rol autorizado sobre los mismos datos: así se descarta
que el 403 se deba a datos no confirmables o a una baja imposible.
"""
from sqlalchemy import select

from app.models import MovimientoInventario, Plancha, Retazo
from app.modules.inventory.application.service import InventoryService
from app.modules.inventory.infrastructure.repository import SqlAlchemyInventoryRepository
from app.modules.inventory.presentation.dependencies import get_inventory_service
from app.modules.authentication.presentation.dependencies import FORBIDDEN_MESSAGE
from app.shared.security import create_access_token
from main import app
from .test_confirmation_api import completed as completed_run
from .test_comparisons_v2_api import api, start, completed as completed_comparison  # noqa: F401
from .test_runs_api import run_api, prepared  # noqa: F401
from tests.integration.optimization.test_confirmation import snapshot

WAREHOUSE = "A73000002"
FORBIDDEN = {"code": "FORBIDDEN", "message": FORBIDDEN_MESSAGE}


def warehouse_headers(create_user) -> dict:
    user_id = create_user(WAREHOUSE, "Almacenero")
    return {"Authorization": "Bearer " + create_access_token(user_id, WAREHOUSE, "Almacenero")}


def test_warehouse_cannot_confirm_a_run_and_nothing_changes(run_api, session_factory, create_user):
    client, _, operator, *_ = run_api
    url, _ = completed_run(run_api)
    warehouse = warehouse_headers(create_user)
    before = snapshot(session_factory)

    denied = client.post(url + "/confirm", headers=warehouse)

    assert denied.status_code == 403, denied.text
    assert denied.json() == {"detail": FORBIDDEN}
    assert snapshot(session_factory) == before
    # Control positivo: el Operario sí confirma la misma ejecución.
    assert client.post(url + "/confirm", headers=operator).status_code == 200


def test_warehouse_cannot_confirm_a_comparison_v2_and_nothing_changes(api, session_factory, create_user):
    client, _, _, operator, _, _ = api
    path, _ = start(api, "seguridad-v2-request")
    current = completed_comparison(api, path)
    chosen = current.executions[0].execution_id
    selected = client.put(path + "/selection", headers=operator,
                          json={"execution_id": chosen, "expected_version": current.version})
    assert selected.status_code == 200, selected.text
    body = {"execution_id": chosen, "expected_version": selected.json()["version"]}
    warehouse = {**warehouse_headers(create_user), "Idempotency-Key": "seguridad-v2-denied"}
    before = snapshot(session_factory)

    denied = client.post(path + "/confirm", headers=warehouse, json=body)

    assert denied.status_code == 403, denied.text
    assert denied.json() == {"detail": FORBIDDEN}
    assert snapshot(session_factory) == before
    with session_factory() as s:
        assert s.get(Plancha, 5).cantidad == 2
        assert s.scalars(select(MovimientoInventario)).all() == []
    # Control positivo: el Operario sí confirma la misma selección.
    confirmed = client.post(path + "/confirm", headers={**operator, "Idempotency-Key": "seguridad-v2-allowed"},
                            json=body)
    assert confirmed.status_code == 200, confirmed.text


def test_operator_cannot_write_off_a_sheet_or_remnant_and_nothing_changes(client, session_factory, create_user, prepared):
    operator_id, _, _ = prepared
    operator = {"Authorization": "Bearer " + create_access_token(operator_id, "O73000001", "Operario")}
    warehouse = warehouse_headers(create_user)
    app.dependency_overrides[get_inventory_service] = (
        lambda: InventoryService(SqlAlchemyInventoryRepository(session_factory)))
    try:
        remnant = client.post("/api/inventory/retazos", headers=warehouse, json={
            "codigo": "SEG-RET-01", "espesor_mm": 6, "id_tipo_vidrio": 7,
            "geometria": {"type": "RECTANGULO", "width_mm": 100, "height_mm": 100},
        })
        assert remnant.status_code == 201, remnant.text
        writeoffs = [
            ("/api/inventory/planchas/5/baja",
             {"tipo_evento": "BAJA_ROTURA", "motivo": "Prueba de seguridad", "cantidad_afectada": 1}),
            (f"/api/inventory/retazos/{remnant.json()['id_retazo']}/baja",
             {"tipo_evento": "BAJA_ROTURA", "motivo": "Prueba de seguridad"}),
        ]
        before = snapshot(session_factory, (Plancha, Retazo, MovimientoInventario))

        for path, body in writeoffs:
            denied = client.post(path, headers=operator, json=body)
            assert denied.status_code == 403, denied.text
            assert denied.json() == {"detail": FORBIDDEN_MESSAGE}

        assert snapshot(session_factory, (Plancha, Retazo, MovimientoInventario)) == before
        # Control positivo: el Almacenero sí da de baja las mismas unidades.
        for path, body in writeoffs:
            assert client.post(path, headers=warehouse, json=body).status_code == 201
    finally:
        app.dependency_overrides.pop(get_inventory_service, None)
