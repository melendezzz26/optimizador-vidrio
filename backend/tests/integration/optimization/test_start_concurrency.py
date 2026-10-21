"""HU-015 preview reads never reserve orders or overwrite concurrent changes."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from unittest.mock import patch

import pytest
from sqlalchemy import func, select

from app.models import Pedido, Pieza, Optimizacion, EjecucionOptimizacion, MovimientoInventario
from app.modules.orders.infrastructure.repositories import SQLAlchemyOrderRepository
from app.modules.orders.application.ports import OrderMutationResult
from app.modules.optimization.application.resource_policy import DEFAULT_RASTER_BUDGET
from app.modules.optimization.application.use_cases import StartOptimizationUseCase
from app.modules.optimization.infrastructure.orders_adapter import OrdersOptimizationAdapter


@pytest.fixture
def pending(session_factory, create_user):
    actor = create_user("O70000001")
    piece = dict(tipo_forma="RECTANGULO", cantidad=5, dimensiones={"width_mm": 100, "height_mm": 50},
                 geometria={"type": "RECTANGULO", "width_mm": 100, "height_mm": 50},
                 id_tipo_vidrio=7, espesor_mm=6, area_mm2=5000)
    with session_factory() as db:
        return SQLAlchemyOrderRepository(db).create_order(actor, [piece], id_cliente=41)


def test_two_simultaneous_http_preparations_both_succeed_without_writes(client, session_factory, pending, password):
    login = client.post("/api/auth/login", json={"username": "O70000001", "password": password})
    assert login.status_code == 200
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    barrier = Barrier(2)
    original = SQLAlchemyOrderRepository.get_order

    def simultaneous(repository, identifier):
        snapshot = original(repository, identifier)
        barrier.wait(timeout=10)
        return snapshot

    def request():
        return client.post("/api/optimization/start", json={"id_pedido": pending}, headers=headers)

    with patch.object(SQLAlchemyOrderRepository, "get_order", simultaneous):
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(request) for _ in range(2)]
            responses = [f.result(timeout=20) for f in futures]
    assert [r.status_code for r in responses] == [200, 200], [r.text for r in responses]
    assert all(r.json() == {"id_pedido": pending, "estado": "PENDIENTE"} for r in responses)
    with session_factory() as observer:
        assert observer.get(Pedido, pending).estado == "PENDIENTE"
        assert observer.scalar(select(Pieza.cantidad).where(Pieza.id_pedido == pending)) == 5
        for model in (Optimizacion, EjecucionOptimizacion, MovimientoInventario):
            assert observer.scalar(select(func.count()).select_from(model)) == 0


@pytest.mark.parametrize("mutation", ["update", "cancel"])
def test_preview_does_not_block_or_overwrite_concurrent_order_mutation(session_factory, pending, mutation):
    read, release = Event(), Event()

    def preview():
        with session_factory() as db:
            gateway = OrdersOptimizationAdapter(SQLAlchemyOrderRepository(db))
            original = gateway.get_order

            def hold_snapshot(identifier):
                snapshot = original(identifier)
                read.set()
                assert release.wait(timeout=10)
                return snapshot

            with patch.object(gateway, "get_order", hold_snapshot):
                return StartOptimizationUseCase(gateway, DEFAULT_RASTER_BUDGET).execute(pending)

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(preview)
        try:
            assert read.wait(timeout=10)
            with session_factory() as db:
                repo = SQLAlchemyOrderRepository(db)
                if mutation == "update":
                    piece = repo.get_order(pending)["piezas"][0]
                    result = repo.update_order(pending, [piece | {"cantidad": 7}])
                else:
                    result = repo.cancel_order(pending)
                assert result is OrderMutationResult.UPDATED
        finally:
            release.set()
        assert future.result(timeout=15)["estado"] == "PENDIENTE"
    with session_factory() as observer:
        assert observer.get(Pedido, pending).estado == ("PENDIENTE" if mutation == "update" else "CANCELADO")
        if mutation == "update":
            assert observer.scalar(select(Pieza.cantidad).where(Pieza.id_pedido == pending)) == 7
