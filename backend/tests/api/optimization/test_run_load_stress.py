"""TA-037 T04: peor caso de volumen sin OOM, por HTTP real -> PostgreSQL (CA-12).

Si el backend expandiera estas cantidades antes de validar, la prueba no terminaría:
2 147 483 647 unidades de stock o de piezas no caben en memoria. El tiempo acotado
demuestra que el rechazo ocurre antes de cualquier expansión.
"""
import time

import pytest
from sqlalchemy import func, select

from app.models import MovimientoInventario, Optimizacion, Pedido, Pieza, Plancha
from app.modules.orders.infrastructure.repositories import SQLAlchemyOrderRepository
from app.modules.optimization.presentation.run_schemas import ErrorResponseV1
from tests.api.optimization.test_runs_api import BASE, parse, run_api  # noqa: F401
from tests.integration.optimization.test_runs import prepared  # noqa: F401

MAX_INT = 2147483647


def timed_post(client, ids, headers):
    started = time.perf_counter()
    response = client.post(BASE, json={"order_ids": ids}, headers=headers)
    return response, time.perf_counter() - started


def assert_untouched(session_factory, ids, sheet_units):
    with session_factory() as s:
        assert [s.get(Pedido, i).estado for i in ids] == ["PENDIENTE"] * len(ids)
        assert s.scalar(select(func.count()).select_from(Optimizacion)) == 0
        assert s.get(Plancha, 5).cantidad == sheet_units
        assert s.scalar(select(func.count()).select_from(MovimientoInventario)) == 0


@pytest.mark.parametrize("target", ["stock", "piece"])
def test_maximum_database_quantity_is_rejected_quickly_without_expansion(run_api, session_factory, target):
    client, ids, headers, *_ = run_api
    with session_factory() as s:
        if target == "stock":
            s.get(Plancha, 5).cantidad = MAX_INT
        else:
            s.scalar(select(Pieza).where(Pieza.id_pedido == ids[0])).cantidad = MAX_INT
        s.commit()
    response, elapsed = timed_post(client, ids, headers)
    assert response.status_code == 422, response.text
    limit = ErrorResponseV1.model_validate(response.json()).detail.limit
    expected = "stock_units_per_material" if target == "stock" else "units_per_run"
    assert (limit.name, limit.actual) == (expected, MAX_INT + (2 if target == "piece" else 0))
    assert elapsed < 5
    assert_untouched(session_factory, ids, MAX_INT if target == "stock" else 2)


def test_exact_order_limit_with_real_orders_is_accepted(run_api, session_factory, prepared):
    client, ids, headers, *_ = run_api
    actor = prepared[0]
    piece = dict(tipo_forma="RECTANGULO", cantidad=1, dimensiones={"width_mm": 2, "height_mm": 2},
                 geometria={"type": "RECTANGULO", "width_mm": 2, "height_mm": 2}, id_tipo_vidrio=7,
                 espesor_mm=6, area_mm2=4)
    with session_factory() as s:
        repo = SQLAlchemyOrderRepository(s)
        extra = [repo.create_order(actor, [piece], id_cliente=41) for _ in range(18)]
    twenty = ids + extra
    events = parse(client.post(BASE, json={"order_ids": twenty}, headers=headers))
    assert events[0]["data"]["order_ids"] == sorted(twenty)
    assert events[-1]["event"] == "optimization_completed"


def test_twenty_one_real_orders_are_rejected_without_locking_any(run_api, session_factory, prepared):
    client, ids, headers, *_ = run_api
    actor = prepared[0]
    piece = dict(tipo_forma="RECTANGULO", cantidad=1, dimensiones={"width_mm": 2, "height_mm": 2},
                 geometria={"type": "RECTANGULO", "width_mm": 2, "height_mm": 2}, id_tipo_vidrio=7,
                 espesor_mm=6, area_mm2=4)
    with session_factory() as s:
        repo = SQLAlchemyOrderRepository(s)
        extra = [repo.create_order(actor, [piece], id_cliente=41) for _ in range(19)]
    response = client.post(BASE, json={"order_ids": ids + extra}, headers=headers)
    assert response.status_code == 422
    assert ErrorResponseV1.model_validate(response.json()).detail.limit.name == "orders_per_run"
    assert_untouched(session_factory, ids + extra, 2)