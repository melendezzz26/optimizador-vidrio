"""TA-037 T02: contrato 422 LOAD_LIMIT_EXCEEDED por HTTP real -> PostgreSQL (CA-02, CA-04)."""
from decimal import Decimal

import pytest
from sqlalchemy import delete, func, select

from app.models import (EjecucionOptimizacion, MovimientoInventario, Optimizacion, OptimizacionPedido,
                        Pedido, Permiso, Pieza, Plancha, Retazo, RolPermiso)
from app.modules.optimization.presentation.run_schemas import ErrorResponseV1
from tests.api.optimization.test_runs_api import BASE, parse, run_api  # noqa: F401
from tests.integration.optimization.test_runs import prepared  # noqa: F401


def snapshot(session_factory, ids):
    """Estado observable que un rechazo no debe tocar."""
    with session_factory() as s:
        return dict(
            orders=[s.get(Pedido, i).estado for i in ids],
            runs=[s.scalar(select(func.count()).select_from(m)) for m in
                  (Optimizacion, OptimizacionPedido, EjecucionOptimizacion)],
            sheets=[(p.id_plancha, p.cantidad, p.estado) for p in s.scalars(select(Plancha).order_by(Plancha.id_plancha))],
            remnants=s.scalar(select(func.count()).select_from(Retazo)),
            movements=s.scalar(select(func.count()).select_from(MovimientoInventario)),
        )


def assert_load_limit(response, name, maximum, actual):
    assert response.status_code == 422, response.text
    assert "location" not in response.headers
    assert response.headers["content-type"].startswith("application/json")
    detail = ErrorResponseV1.model_validate(response.json()).detail
    assert detail.code == "LOAD_LIMIT_EXCEEDED"
    assert (detail.limit.name, detail.limit.maximum, detail.limit.actual) == (name, maximum, actual)
    assert not any(s in detail.message for s in ("SELECT", "Traceback", "piezas.", "sqlalchemy"))
    return detail


def test_units_over_limit_answer_422_and_change_nothing(run_api, session_factory):
    client, ids, headers, *_ = run_api
    with session_factory() as s:
        s.scalar(select(Pieza).where(Pieza.id_pedido == ids[0])).cantidad = 149  # 149 + 2 = 151
        s.commit()
    before = snapshot(session_factory, ids)
    response = client.post(BASE, json={"order_ids": ids}, headers=headers)
    detail = assert_load_limit(response, "units_per_run", 150, 151)
    assert detail.message.startswith("Los pedidos seleccionados suman 151 unidades")
    assert snapshot(session_factory, ids) == before
    assert before["orders"] == ["PENDIENTE", "PENDIENTE"] and before["runs"] == [0, 0, 0]


def test_units_at_exact_limit_are_accepted(run_api, session_factory):
    client, ids, headers, *_ = run_api
    with session_factory() as s:
        s.scalar(select(Pieza).where(Pieza.id_pedido == ids[0])).cantidad = 148  # 148 + 2 = 150
        s.commit()
    events = parse(client.post(BASE, json={"order_ids": ids}, headers=headers))
    assert events[0]["data"]["total_units"] == 150


def test_stock_over_limit_answer_422_with_material_scope(run_api, session_factory):
    client, ids, headers, *_ = run_api
    with session_factory() as s:
        s.get(Plancha, 5).cantidad = 1000  # una sola fila; se cuenta sin expandir
        s.commit()
    before = snapshot(session_factory, ids)
    detail = assert_load_limit(client.post(BASE, json={"order_ids": ids}, headers=headers),
                               "stock_units_per_material", 50, 1000)
    assert detail.limit.scope["id_tipo_vidrio"] == 7 and Decimal(detail.limit.scope["espesor_mm"]) == 6
    assert snapshot(session_factory, ids) == before


def test_stock_at_exact_limit_is_accepted_and_inventory_is_not_consumed(run_api, session_factory):
    client, ids, headers, *_ = run_api
    with session_factory() as s:
        s.get(Plancha, 5).cantidad = 50
        s.commit()
    events = parse(client.post(BASE, json={"order_ids": ids}, headers=headers))
    assert events[-1]["event"] == "optimization_completed"
    with session_factory() as s:
        assert s.get(Plancha, 5).cantidad == 50  # simular no consume stock
        assert s.scalar(select(func.count()).select_from(MovimientoInventario)) == 0


def test_too_many_orders_are_rejected_before_any_lookup(run_api, session_factory):
    client, ids, headers, *_ = run_api
    missing = list(range(900001, 900022))  # 21 ids inexistentes: 422 antes que 404
    assert_load_limit(client.post(BASE, json={"order_ids": missing}, headers=headers), "orders_per_run", 20, 21)


def test_permission_is_checked_before_the_load_limit(run_api, session_factory):
    client, ids, headers, *_ = run_api
    with session_factory() as s:
        permission = s.scalar(select(Permiso.id_permiso).where(Permiso.codigo == "optimization.execute"))
        s.execute(delete(RolPermiso).where(RolPermiso.id_rol == 3, RolPermiso.id_permiso == permission))
        s.commit()
    response = client.post(BASE, json={"order_ids": list(range(1, 22))}, headers=headers)
    assert response.status_code == 403
    assert ErrorResponseV1.model_validate(response.json()).detail.code == "FORBIDDEN"


def test_error_contract_requires_limit_exactly_for_load_errors():
    limit = {"name": "units_per_run", "maximum": 150, "actual": 151, "scope": None}
    assert ErrorResponseV1.model_validate({"detail": {"code": "INVALID_INPUT", "message": "x"}}).detail.limit is None
    with pytest.raises(ValueError):
        ErrorResponseV1.model_validate({"detail": {"code": "LOAD_LIMIT_EXCEEDED", "message": "x"}})
    with pytest.raises(ValueError):
        ErrorResponseV1.model_validate({"detail": {"code": "INVALID_INPUT", "message": "x", "limit": limit}})