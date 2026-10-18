from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from time import monotonic, sleep
from unittest.mock import patch

import pytest
from sqlalchemy import func, select, text

from app.models import (Pedido, Pieza, Optimizacion, EjecucionOptimizacion,
                        MovimientoInventario)
from app.modules.orders.infrastructure.repositories import SQLAlchemyOrderRepository
from app.modules.orders.application.ports import OrderMutationResult
from app.modules.optimization.application.errors import InvalidRasterInput
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


def use_case(db):
    return StartOptimizationUseCase(OrdersOptimizationAdapter(SQLAlchemyOrderRepository(db)), DEFAULT_RASTER_BUDGET)


def wait_for_real_lock(factory):
    deadline = monotonic() + 5
    while monotonic() < deadline:
        with factory() as observer:
            waiting = observer.scalar(text(
                "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() "
                "AND wait_event_type = 'Lock' AND pid <> pg_backend_pid()"
            ))
        if waiting:
            return
        sleep(0.01)
    pytest.fail("El segundo intento no alcanzó una espera de bloqueo real en PostgreSQL.")


def test_two_simultaneous_http_starts_have_exactly_one_winner(client, session_factory, pending, password):
    login = client.post("/api/auth/login", json={"username": "O70000001", "password": password})
    assert login.status_code == 200
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    barrier = Barrier(2)
    validating, release = Event(), Event()
    original = SQLAlchemyOrderRepository.start_optimization

    def simultaneous(repository, identifier, validate):
        barrier.wait(timeout=10)
        def hold_winner(snapshot):
            validate(snapshot)
            validating.set()
            assert release.wait(timeout=10)
        return original(repository, identifier, hold_winner)

    def request():
        return client.post("/api/optimization/start", json={"id_pedido": pending}, headers=headers)

    with patch.object(SQLAlchemyOrderRepository, "start_optimization", simultaneous):
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(request) for _ in range(2)]
            try:
                assert validating.wait(timeout=10)
                wait_for_real_lock(session_factory)
            finally:
                release.set()
            responses = [f.result(timeout=20) for f in futures]
    assert sorted(r.status_code for r in responses) == [200, 409], [r.text for r in responses]
    winner = next(r for r in responses if r.status_code == 200)
    assert winner.json() == {"id_pedido": pending, "estado": "EN_OPTIMIZACION"}
    with session_factory() as observer:
        assert observer.get(Pedido, pending).estado == "EN_OPTIMIZACION"
        pieces = observer.scalars(select(Pieza).where(Pieza.id_pedido == pending)).all()
        assert len(pieces) == 1 and pieces[0].cantidad == 5
        for model in (Optimizacion, EjecucionOptimizacion, MovimientoInventario):
            assert observer.scalar(select(func.count()).select_from(model)) == 0


@pytest.mark.parametrize("mutation", ["update", "cancel"])
def test_start_winner_prevents_concurrent_order_mutation(session_factory, pending, mutation):
    acquired, release, attempting = Event(), Event(), Event()

    def starting():
        with session_factory() as db:
            repository = SQLAlchemyOrderRepository(db)
            def validate(snapshot):
                acquired.set()
                assert release.wait(timeout=10)
            return repository.start_optimization(pending, validate)

    def mutating():
        assert acquired.wait(timeout=10)
        with session_factory() as db:
            repository = SQLAlchemyOrderRepository(db)
            attempting.set()
            if mutation == "update":
                return repository.update_order(pending, [])
            return repository.cancel_order(pending)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = pool.submit(starting), pool.submit(mutating)
        try:
            assert attempting.wait(timeout=10)
            wait_for_real_lock(session_factory)
        finally:
            release.set()
        assert first.result(timeout=15) is OrderMutationResult.UPDATED
        assert second.result(timeout=15) is OrderMutationResult.STATE_CONFLICT
    with session_factory() as observer:
        assert observer.get(Pedido, pending).estado == "EN_OPTIMIZACION"
        assert observer.scalar(select(func.count()).select_from(Pieza).where(Pieza.id_pedido == pending)) == 1


@pytest.mark.parametrize("mutation", ["update", "cancel"])
def test_order_mutation_winner_is_seen_before_start_validates(session_factory, pending, mutation):
    acquired, attempting, release = Event(), Event(), Event()

    def mutate():
        with session_factory() as db:
            # Mantener el mismo bloqueo de cabecera que update/cancel mientras
            # el start concurrente alcanza su CAS; las primitivas reales siguen
            # ejecutándose en esta misma sesión/transacción.
            db.execute(select(Pedido.estado).where(Pedido.id_pedido == pending).with_for_update())
            acquired.set()
            assert release.wait(timeout=10)
            repo = SQLAlchemyOrderRepository(db)
            if mutation == "update":
                original = repo.get_order(pending)["piezas"][0]
                return repo.update_order(pending, [original | {"cantidad": 7}])
            return repo.cancel_order(pending)

    def starting():
        assert acquired.wait(timeout=10)
        with session_factory() as db:
            attempting.set()
            seen = []
            result = SQLAlchemyOrderRepository(db).start_optimization(pending, lambda order: seen.extend(order["piezas"]))
            return result, seen

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = pool.submit(mutate), pool.submit(starting)
        try:
            assert attempting.wait(timeout=10)
            wait_for_real_lock(session_factory)
        finally:
            release.set()
        assert first.result(timeout=15) is OrderMutationResult.UPDATED
        result, seen = second.result(timeout=15)
    if mutation == "update":
        assert result is OrderMutationResult.UPDATED and seen[0]["cantidad"] == 7
    else:
        assert result is OrderMutationResult.STATE_CONFLICT and seen == []
    with session_factory() as observer:
        assert observer.get(Pedido, pending).estado == ("EN_OPTIMIZACION" if mutation == "update" else "CANCELADO")


def test_validation_failure_rolls_back_and_next_start_can_succeed(session_factory, pending):
    with session_factory() as db:
        def invalid(snapshot):
            assert snapshot["estado"] == "EN_OPTIMIZACION"
            raise InvalidRasterInput("precondición fallida")
        with pytest.raises(InvalidRasterInput):
            SQLAlchemyOrderRepository(db).start_optimization(pending, invalid)
    with session_factory() as observer:
        assert observer.get(Pedido, pending).estado == "PENDIENTE"
        assert use_case(observer).execute(pending)["estado"] == "EN_OPTIMIZACION"


def test_commit_failure_rolls_back_tentative_transition(session_factory, pending):
    with session_factory() as db:
        with patch.object(db, "commit", side_effect=RuntimeError("commit failed")):
            with pytest.raises(RuntimeError):
                use_case(db).execute(pending)
    with session_factory() as observer:
        assert observer.get(Pedido, pending).estado == "PENDIENTE"
