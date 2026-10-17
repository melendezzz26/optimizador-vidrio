from decimal import Decimal as D

import pytest
from sqlalchemy import select

from app.models import Plancha, Pieza, Retazo, MovimientoInventario
from app.modules.inventory.application.service import InventoryService
from app.modules.inventory.infrastructure.repository import SqlAlchemyInventoryRepository
from app.modules.inventory.presentation.dependencies import get_inventory_service
from main import app
from .test_runs_api import run_api, prepared, parse  # noqa: F401
from tests.integration.optimization.test_confirmation import snapshot


@pytest.mark.parametrize('width,height', [(2140, 3300), (4000, 4000)])
def test_commercial_eight_units_simulate_confirm_and_origin_without_recalculation(run_api, session_factory, monkeypatch, width, height):
    client, ids, headers, *_ = run_api
    with session_factory() as session:
        sheet = session.get(Plancha, 5)
        sheet.ancho_mm, sheet.alto_mm, sheet.cantidad = width, height, 10
        piece = session.scalar(select(Pieza).where(Pieza.id_pedido == ids[0]))
        piece.cantidad = 8
        piece.dimensiones = {'width_mm': 600, 'height_mm': 800}
        piece.geometria = {'type': 'RECTANGULO', 'width_mm': 600, 'height_mm': 800}
        piece.area_mm2 = 480000
        session.commit()
    inventory_before = snapshot(session_factory, (Plancha, Retazo, MovimientoInventario))
    response = client.post('/api/optimization/runs', headers=headers, json={'order_ids': ids[:1]})
    events = parse(response)
    assert events[-1]['data']['estado'] == 'COMPLETADA'
    assert len([event for event in events if event['event'] == 'piece_placed']) == 8
    url = response.headers['location']
    result = client.get(url, headers=headers).json()
    assert result['placed_units'] == result['total_units'] == 8
    assert result['confirmable'] and result['metrics_available']
    assert D(result['configuracion']['resolucion_raster_mm']) == 1
    assert len(result['residual_regions']) == 1
    assert D(result['metrics']['area_material_total_mm2']) == width * height
    assert inventory_before == snapshot(session_factory, (Plancha, Retazo, MovimientoInventario))
    monkeypatch.setattr('app.modules.optimization.domain.first_fit.FirstFitOptimizer.optimize', lambda *a, **k: pytest.fail('No recalculation during confirmation/origin/GET'))
    receipt = client.post(url + '/confirm', headers=headers)
    assert receipt.status_code == 200, receipt.text
    created, = receipt.json()['remnants_created']
    with session_factory() as session:
        assert session.get(Plancha, 5).cantidad == 9
        remnant = session.get(Retazo, created['id_retazo'])
        assert remnant.id_ejecucion_origen is not None
    app.dependency_overrides[get_inventory_service] = lambda: InventoryService(SqlAlchemyInventoryRepository(session_factory))
    try:
        origin = client.get(f"/api/inventory/retazos/{created['id_retazo']}/origen", headers=headers)
        assert origin.status_code == 200, origin.text
        assert origin.json()['id_optimizacion'] == result['id_optimizacion']
        assert origin.json()['order_ids'] == ids[:1]
        assert origin.json()['source'] == created['source']
        assert client.get(f"/api/inventory/retazos/{created['id_retazo']}/origen").status_code == 401
        assert client.get('/api/inventory/retazos/999999/origen', headers=headers).status_code == 404
    finally:
        app.dependency_overrides.pop(get_inventory_service, None)
    confirmed = client.get(url, headers=headers).json()
    assert confirmed['confirmed'] and confirmed['residual_regions'] == result['residual_regions']
    assert client.post(url + '/confirm', headers=headers).status_code == 409
