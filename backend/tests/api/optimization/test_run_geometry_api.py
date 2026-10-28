"""HU-017 T02: real PostgreSQL, frozen config and interruption during bases."""
import asyncio
import json
from decimal import Decimal as D
from functools import partial
from threading import Event

import pytest
from sqlalchemy import event, func, select

from app.models import Configuracion, MovimientoInventario, Pedido, Pieza, Plancha
from app.modules.optimization.application.runs import AcceptRun
from app.modules.optimization.domain.placement import SheetLayout
from app.modules.optimization.domain.rotation import RasterCache
from app.modules.optimization.presentation import run_routes
from app.modules.optimization.presentation.run_stream import LiveRunStream
from tests.api.optimization.test_runs_api import BASE, parse, run_api  # noqa: F401
from tests.integration.optimization.test_runs import prepared  # noqa: F401


def test_accepted_config_stays_frozen_and_bases_run_outside_db_transactions(
        run_api, prepared, session_factory, monkeypatch):
    _, ids, _, uow, calculator = run_api
    accepted = AcceptRun(uow).execute(ids, prepared[0])
    with session_factory() as session:
        config = session.scalar(select(Configuracion))
        config.resolucion_raster_mm, config.margen_mm, config.separacion_mm = 5, 7, 9
        session.commit()
    active, observations = set(), []

    def begin(session, transaction, connection):
        active.add(id(session))

    def end(session, transaction):
        if transaction.parent is None:
            active.discard(id(session))

    original = RasterCache._raster

    def raster(self, geometry, resolution, **kwargs):
        assert not active
        assert resolution == D(1)
        observations.append(True)
        return original(self, geometry, resolution, **kwargs)

    event.listen(session_factory.class_, 'after_begin', begin)
    event.listen(session_factory.class_, 'after_transaction_end', end)
    monkeypatch.setattr(RasterCache, '_raster', raster)
    try:
        result = calculator.execute(accepted.optimization_id)
    finally:
        event.remove(session_factory.class_, 'after_begin', begin)
        event.remove(session_factory.class_, 'after_transaction_end', end)
    assert observations and result.result.complete
    assert result.result.problem.config == accepted.result.problem.config
    assert result.result.problem.config.margin_mm == result.result.problem.config.separation_mm == 0
    with session_factory() as session:
        assert session.get(Plancha, 5).cantidad == 2
        assert session.scalar(select(func.count()).select_from(MovimientoInventario)) == 0


@pytest.mark.parametrize('phase', ['base', 'orientation'])
def test_timeout_during_geometric_work_is_failed_not_no_fit(
        run_api, session_factory, monkeypatch, phase):
    client, ids, headers, *_ = run_api
    now, searches = [0.0], []
    original = RasterCache._raster
    if phase == 'orientation':
        with session_factory() as session:
            piece = session.scalar(select(Pieza).where(Pieza.id_pedido == ids[0]))
            piece.geometria, piece.area_mm2 = dict(type='RECTANGULO', width_mm=3, height_mm=2), 6
            sheet = session.get(Plancha, 5)
            sheet.ancho_mm, sheet.alto_mm = 2, 4
            session.commit()

    def raster(self, *args, **kwargs):
        mask = original(self, *args, **kwargs)
        if phase == 'base' or args[0]['type'] == 'POLIGONO_CONVEXO':
            now[0] = 2.0
        return mask

    monkeypatch.setattr(RasterCache, '_raster', raster)
    monkeypatch.setattr(SheetLayout, 'first_position', lambda *args: searches.append(True))
    monkeypatch.setattr(run_routes, 'LiveRunStream', partial(LiveRunStream, time_budget_s=1, clock=lambda: now[0]))
    response = client.post(BASE, json={'order_ids': ids}, headers=headers)
    events = parse(response)
    if phase == 'base':
        assert [entry['event'] for entry in events] == ['optimization_started', 'optimization_failed']
    else:
        assert events[-1]['event'] == 'optimization_failed'
        assert not any(entry['event'] == 'piece_placed' for entry in events)
    assert events[-1]['data']['code'] == 'TIME_BUDGET_EXCEEDED'
    assert searches == []
    final = client.get(response.headers['location'], headers=headers).json()
    assert final['estado'] == 'FALLIDA' and final['placed_units'] == 0 and not final['confirmable']
    with session_factory() as session:
        assert [session.get(Pedido, identifier).estado for identifier in ids] == ['EN_OPTIMIZACION'] * 2
        assert session.get(Plancha, 5).cantidad == 2
        assert session.scalar(select(func.count()).select_from(MovimientoInventario)) == 0


def test_base_memory_failure_is_durable_technical_failure_without_inventory_changes(
        run_api, session_factory, monkeypatch):
    from app.modules.optimization.domain import run_geometry
    client, ids, headers, *_ = run_api
    monkeypatch.setattr(run_geometry, 'RasterCache', lambda: RasterCache(max_cache_bytes=1))
    response = client.post(BASE, json={'order_ids': ids}, headers=headers)
    events = parse(response)
    assert [entry['event'] for entry in events] == ['optimization_started', 'optimization_failed']
    assert events[-1]['data']['code'] == 'CALCULATION_FAILED'
    final = client.get(response.headers['location'], headers=headers).json()
    assert final['estado'] == 'FALLIDA' and final['placed_units'] == 0
    assert not final['confirmable']
    with session_factory() as session:
        assert [session.get(Pedido, identifier).estado for identifier in ids] == ['EN_OPTIMIZACION'] * 2
        assert session.get(Plancha, 5).cantidad == 2
        assert session.scalar(select(func.count()).select_from(MovimientoInventario)) == 0


def test_disconnect_during_first_base_stops_before_search_and_saves_failure(
        run_api, prepared, session_factory, monkeypatch):
    _, ids, _, uow, calculator = run_api
    accepted = AcceptRun(uow).execute(ids, prepared[0])
    entered, resume, worker_done = Event(), Event(), Event()
    original_raster, original_execute = RasterCache._raster, calculator.execute
    searches, rasters = [], []

    def raster(self, *args, **kwargs):
        rasters.append(True)
        mask = original_raster(self, *args, **kwargs)
        if len(rasters) == 1:
            entered.set()
            assert resume.wait(5), 'test must resume its paused base allocation'
        return mask

    def execute(*args, **kwargs):
        try:
            return original_execute(*args, **kwargs)
        finally:
            worker_done.set()

    monkeypatch.setattr(RasterCache, '_raster', raster)
    monkeypatch.setattr(calculator, 'execute', execute)
    monkeypatch.setattr(SheetLayout, 'first_position', lambda *args: searches.append(True))
    owner = LiveRunStream(uow, calculator)

    async def disconnect():
        stream = owner.lines(accepted)
        try:
            assert json.loads(await anext(stream))['event'] == 'optimization_started'
            assert await asyncio.to_thread(entered.wait, 5)
        finally:
            # aclose sets the cooperative stop flag before its bounded join.
            asyncio.get_running_loop().call_later(0.05, resume.set)
            await stream.aclose()

    try:
        asyncio.run(disconnect())
        assert worker_done.wait(5)
    finally:
        resume.set()
    assert rasters == [True] and searches == []
    with uow() as transaction:
        result = transaction.runs.get(accepted.optimization_id)
    assert result.status.value == 'FALLIDA' and result.result.placed_units == 0
    with session_factory() as session:
        assert [session.get(Pedido, identifier).estado for identifier in ids] == ['EN_OPTIMIZACION'] * 2
        assert session.get(Plancha, 5).cantidad == 2
        assert session.scalar(select(func.count()).select_from(MovimientoInventario)) == 0
