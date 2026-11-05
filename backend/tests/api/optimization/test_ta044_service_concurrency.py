"""TA-044: simultaneous service runs against the isolated PostgreSQL fixture."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import asyncio
import json
import time
from threading import Barrier, Event

import pytest
from sqlalchemy import func, select

from app.models import EjecucionOptimizacion, MovimientoInventario, Optimizacion, OptimizacionPedido, Plancha, Retazo
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.application.calculation import CalculateRun
from app.modules.optimization.infrastructure.stock_adapter import InventoryStockAdapter
from app.modules.inventory.infrastructure.repository import SqlAlchemyInventoryRepository
from app.modules.optimization.presentation.run_routes import get_run_calculator
from app.modules.optimization.presentation.run_stream import LiveRunStream
from app.modules.optimization.application.runs import AcceptRun
from app.shared.security import create_access_token
from main import app
from tests.api.optimization.test_runs_api import BASE, parse, run_api  # noqa: F401
from tests.integration.optimization.test_runs import prepared  # noqa: F401


def inventory(session_factory):
    with session_factory() as db:
        return (
            [tuple(row) for row in db.execute(select(Plancha.__table__).order_by(Plancha.id_plancha))],
            [tuple(row) for row in db.execute(select(Retazo.__table__).order_by(Retazo.id_retazo))],
            [tuple(row) for row in db.execute(select(MovimientoInventario.__table__).order_by(MovimientoInventario.id_movimiento))],
        )


def add_remnant(session_factory):
    with session_factory() as db:
        db.add(Retazo(id_retazo=9, codigo='TA044', geometria={'type': 'RECTANGULO', 'width_mm': 4, 'height_mm': 2},
                      area_mm2=8, espesor_mm=6, id_tipo_vidrio=7, estado=True, fecha_registro=datetime.now(timezone.utc)))
        db.commit()


@pytest.mark.parametrize("fail_first", [False, True])
def test_two_real_requests_isolate_failure_and_reject_third(
        run_api, run_admission, session_factory, create_user, monkeypatch, fail_first):
    client, ids, headers, uow, _ = run_api
    # Production constructs a calculator and inventory repository per request.
    # The common run_api fixture intentionally shares one calculator for its
    # single-request tests; use the real lifecycle for concurrent requests.
    monkeypatch.setitem(app.dependency_overrides, get_run_calculator,
                        lambda: CalculateRun(uow, InventoryStockAdapter(
                            SqlAlchemyInventoryRepository(session_factory))))
    second = create_user("O73000002")
    third = create_user("O73000003")
    second_headers = {"Authorization": "Bearer " + create_access_token(second, "O73000002", "Operario")}
    third_headers = {"Authorization": "Bearer " + create_access_token(third, "O73000003", "Operario")}
    entered = Barrier(3)
    resume = Event()
    original = FirstFitOptimizer.optimize

    def pause(self, problem, *args, **kwargs):
        entered.wait(timeout=20)
        assert resume.wait(20)
        if fail_first and problem.order_ids == (ids[0],):
            raise RuntimeError("synthetic isolated calculation failure")
        return original(self, problem, *args, **kwargs)

    monkeypatch.setattr(FirstFitOptimizer, "optimize", pause)
    add_remnant(session_factory)
    before = inventory(session_factory)
    def request(order, auth):
        start = time.perf_counter()
        response = client.post(BASE, json={"order_ids": [order]}, headers=auth)
        return response, time.perf_counter() - start

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(request, ids[0], headers)
        second_run = pool.submit(request, ids[1], second_headers)
        try:
            entered.wait(timeout=20)
            assert run_admission.active() == 2
            rejected = client.post(BASE, json={"order_ids": [ids[0]]}, headers=third_headers)
            assert rejected.status_code == 503
            assert rejected.json()["detail"]["code"] == "OPTIMIZER_BUSY"
            assert inventory(session_factory) == before
            with session_factory() as db:
                assert db.scalar(select(func.count()).select_from(Optimizacion)) == 2
        finally:
            resume.set()
        outcomes = [first.result(timeout=30), second_run.result(timeout=30)]
    responses = [response for response, _ in outcomes]
    print(f"TA044 service: fail_first={fail_first} request_seconds={[round(seconds, 3) for _, seconds in outcomes]}")
    events = [parse(response) for response in responses]
    assert events[0][0]["id_optimizacion"] != events[1][0]["id_optimizacion"]
    assert events[0][-1]["event"] == ("optimization_failed" if fail_first else "optimization_completed")
    assert events[1][-1]["event"] == "optimization_completed"
    for response, stream, auth in zip(responses, events, [headers, second_headers]):
        loaded = client.get(response.headers["location"], headers=auth)
        assert loaded.status_code == 200
        assert loaded.json()["estado"] == stream[-1]["data"]["estado"]
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Optimizacion)) == 2
        assert db.scalar(select(func.count()).select_from(EjecucionOptimizacion)) == 2
        links = db.execute(select(OptimizacionPedido.id_optimizacion, OptimizacionPedido.id_pedido)).all()
        assert set(links) == {(events[i][0]['id_optimizacion'], ids[i]) for i in range(2)}
        assert db.scalar(select(func.count()).select_from(EjecucionOptimizacion).outerjoin(
            Optimizacion, EjecucionOptimizacion.id_optimizacion == Optimizacion.id_optimizacion
        ).where(Optimizacion.id_optimizacion.is_(None))) == 0
    assert inventory(session_factory) == before


def test_disconnect_preserves_full_inventory_and_releases_worker(run_api, run_admission, session_factory, prepared):
    _, ids, _, uow, calculator = run_api
    actor = prepared[0]
    add_remnant(session_factory)
    before = inventory(session_factory)
    lease = run_admission.acquire(actor)
    accepted = AcceptRun(uow).execute(ids, actor)

    async def disconnect():
        stream = LiveRunStream(uow, calculator, lease=lease).lines(accepted)
        try:
            while json.loads(await anext(stream))['event'] != 'piece_placed':
                pass
        finally:
            await stream.aclose()

    asyncio.run(disconnect())
    with uow() as tx:
        run = tx.runs.get(accepted.optimization_id)
    assert run.status.value == 'FALLIDA' and not run.confirmable
    assert run_admission.active() == 0
    assert inventory(session_factory) == before
