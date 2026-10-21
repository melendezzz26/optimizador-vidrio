"""S1-01: real HTTP and PostgreSQL from HU-015 preview through confirmation."""
import pytest

from app.models import Pedido, Pieza, Plancha, Retazo, MovimientoInventario
from tests.integration.optimization.test_confirmation import snapshot, invariant
from .test_runs_api import run_api, prepared, parse  # noqa: F401


@pytest.mark.parametrize("count", [1, 2])
def test_preview_raster_first_fit_persisted_result_and_confirmation(run_api, session_factory, monkeypatch, count):
    client, ids, headers, _, calculator = run_api
    ids = ids[:count]
    before = snapshot(session_factory)
    stock_before = snapshot(session_factory, (Plancha, Retazo, MovimientoInventario))
    for identifier in ids:
        for _ in range(2):
            response = client.post("/api/optimization/start", json={"id_pedido": identifier}, headers=headers)
            assert response.status_code == 200, response.text
            assert response.json() == {"id_pedido": identifier, "estado": "PENDIENTE"}
            assert snapshot(session_factory) == before
        order = client.get(f"/api/orders/{identifier}", headers=headers).json()
        for piece in order["piezas"]:
            raster = client.post("/api/optimization/rasterize", headers=headers, json={
                "id_pedido": identifier, "id_pieza": piece["id_pieza"], "resolution_mm": 1})
            assert raster.status_code == 200, raster.text
            assert raster.json()["geometria"] == piece["geometria"]
            assert snapshot(session_factory) == before

    # Inspect the real acceptance boundary before the actual calculation runs.
    calculate = calculator.execute
    accepted = []

    def observe_acceptance(identifier, *args, **kwargs):
        with session_factory() as db:
            assert all(db.get(Pedido, i).estado == "EN_OPTIMIZACION" for i in ids)
        assert snapshot(session_factory, (Plancha, Retazo, MovimientoInventario)) == stock_before
        accepted.append(identifier)
        return calculate(identifier, *args, **kwargs)

    monkeypatch.setattr(calculator, "execute", observe_acceptance)
    response = client.post("/api/optimization/runs", json={"order_ids": ids}, headers=headers)
    events = parse(response)
    assert len(accepted) == 1
    assert events[-1]["data"]["estado"] == "COMPLETADA"
    assert snapshot(session_factory, (Plancha, Retazo, MovimientoInventario)) == stock_before
    with session_factory() as db:
        assert all(db.get(Pedido, i).estado == "OPTIMIZADO" for i in ids)

    def no_recalculation(*args, **kwargs):
        pytest.fail("GET and confirmation must use the persisted First Fit result")

    monkeypatch.setattr("app.modules.optimization.domain.first_fit.FirstFitOptimizer.optimize", no_recalculation)
    url = response.headers["location"]
    canonical = client.get(url, headers=headers)
    assert canonical.status_code == 200
    result = canonical.json()
    assert result["completo"] and result["confirmable"]
    assert len(result["placements"]) == count * 2
    assert client.get(url, headers=headers).json() == result
    confirmation = client.post(url + "/confirm", headers=headers)
    assert confirmation.status_code == 200, confirmation.text
    with session_factory() as db:
        assert all(db.get(Pedido, i).estado == "CONFIRMADO" for i in ids)
        assert db.get(Plancha, 5).cantidad == 2 - count
        movements = db.query(MovimientoInventario).all()
        assert sum(m.cantidad_afectada for m in movements) == count
        assert all(m.tipo_evento == "CONSUMO_OPTIMIZACION" and m.id_optimizacion == accepted[0]
                   and m.id_usuario is not None for m in movements)
    confirmed = snapshot(session_factory)
    assert client.get(url, headers=headers).json()["confirmed"]
    assert client.post(url + "/confirm", headers=headers).status_code == 409
    assert snapshot(session_factory) == confirmed
    invariant(session_factory)


def test_historical_in_progress_preview_never_normalizes_or_enables_first_fit(run_api, session_factory):
    client, ids, headers, *_ = run_api
    identifier = ids[0]
    with session_factory() as db:
        db.get(Pedido, identifier).estado = "EN_OPTIMIZACION"
        piece = db.query(Pieza).filter_by(id_pedido=identifier).one().id_pieza
        db.commit()
    before = snapshot(session_factory)
    assert client.post("/api/optimization/start", headers=headers,
                       json={"id_pedido": identifier}).status_code == 409
    raster = client.post("/api/optimization/rasterize", headers=headers, json={
        "id_pedido": identifier, "id_pieza": piece, "resolution_mm": 1})
    assert raster.status_code == 200, raster.text
    response = client.post("/api/optimization/runs", headers=headers, json={"order_ids": ids})
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "STATE_CONFLICT"
    assert snapshot(session_factory) == before
