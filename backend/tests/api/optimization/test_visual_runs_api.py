"""HU-017 T03: opt-in live geometry, strict V1 compatibility and owned PostgreSQL."""
import json
import asyncio
from decimal import Decimal

import pytest
from sqlalchemy import delete, func, select
from pydantic import TypeAdapter

from app.models import MovimientoInventario, Optimizacion, Pedido, Plancha, Permiso, RolPermiso
from tests.api.optimization.test_runs_api import BASE, parse, run_api  # noqa: F401
from tests.integration.optimization.test_runs import prepared  # noqa: F401
from app.modules.optimization.application.runs import AcceptRun
from app.modules.optimization.presentation.run_stream import LiveRunStream
from app.modules.optimization.presentation.visual_schemas import OptimizationEventV2


def visual(response):
    assert response.status_code == 201, response.text
    parser = TypeAdapter(OptimizationEventV2)
    values = [parser.validate_json(line).model_dump(mode='json') for line in response.iter_lines()]
    assert all(value['schema_version'] == 2 for value in values)
    assert [value['sequence'] for value in values] == list(range(1, len(values) + 1))
    return values


@pytest.mark.parametrize('query', ['?stream_profile=unknown', '?stream_profile=', '?stream_profile=v1&stream_profile=visual-v2'])
def test_invalid_profile_does_not_accept_or_reserve(run_api, run_admission, session_factory, query):
    client, ids, headers, *_ = run_api
    response = client.post(BASE + query, json={'order_ids': ids}, headers=headers)
    assert response.status_code == 422
    assert run_admission.active() == 0
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Optimizacion)) == 0
        assert [session.get(Pedido, identifier).estado for identifier in ids] == ['PENDIENTE'] * 2


def test_visual_order_real_masks_and_canonical_v1_result(run_api, session_factory):
    client, ids, headers, *_ = run_api
    response = client.post(BASE + '?stream_profile=visual-v2', json={'order_ids': ids}, headers=headers)
    events = visual(response)
    names = [entry['event'] for entry in events]
    assert names[0] == 'optimization_started' and names[-1] == 'optimization_completed'
    assert names.index('preparation_completed') < names.index('group_started') < names.index('orientation_testing')
    assert names.index('source_selected') < names.index('piece_placed')
    ready = [entry['data'] for entry in events if entry['event'] == 'piece_ready']
    assert len(ready) == 2 and all(entry['cantidad'] == 2 for entry in ready)
    mask = ready[0]['mask']
    assert mask['available'] and mask['rotation_deg'] == '0'
    result = client.get(response.headers['location'], headers=headers).json()
    assert result['schema_version'] == 1 and result['completo']
    assert result['placed_units'] == events[-1]['data']['processed_units'] == 4
    assert [entry['data']['processed_units'] for entry in events if entry['event'] == 'piece_placed'] == [1, 2, 3, 4]
    page = client.get(response.headers['location'] + '/visual', headers=headers)
    assert page.status_code == 200 and page.json()['items']
    window = client.get(response.headers['location'] + '/visual/masks/' + mask['mask_ref'], headers=headers)
    assert window.status_code == 200, window.text
    data = window.json()
    assert data['resolution_mm'] == result['configuracion']['resolucion_raster_mm']
    assert data['spans_by_row'] == [{'row': 0, 'runs': [[0, 2]]}, {'row': 1, 'runs': [[0, 2]]}]
    assert data['geometria'] == {'type': 'RECTANGULO', 'width_mm': 2.0, 'height_mm': 2.0}
    assert client.get(response.headers['location'] + '/visual/masks/' + mask['mask_ref'] + '?row_count=257', headers=headers).status_code == 422
    assert len(window.content) <= 256 * 1024
    assert all(len(line.encode()) + 1 <= 64 * 1024 for line in response.iter_lines())
    with session_factory() as session:
        assert session.get(Plancha, 5).cantidad == 2
        assert session.scalar(select(func.count()).select_from(MovimientoInventario)) == 0


def test_no_fit_processed_progress_and_legacy_profile(run_api, session_factory):
    client, ids, headers, *_ = run_api
    with session_factory() as session:
        session.get(Plancha, 5).cantidad = 1
        session.commit()
    response = client.post(BASE + '?stream_profile=visual-v2', json={'order_ids': ids}, headers=headers)
    events = visual(response)
    missing = [entry for entry in events if entry['event'] == 'piece_unplaced']
    assert len(missing) == 2 and all(entry['data']['reason'] == 'NO_FIT' for entry in missing)
    terminal = events[-1]['data']
    assert terminal['estado'] == 'SIN_SOLUCION' and terminal['processed_units'] == 4
    assert terminal['placed_units'] == 2 and Decimal(terminal['progress_pct']) == 50


def test_v1_remains_default_and_visual_absence_is_explicit(run_api):
    client, ids, headers, *_ = run_api
    response = client.post(BASE, json={'order_ids': ids}, headers=headers)
    assert parse(response)[-1]['event'] == 'optimization_completed'
    assert client.get(response.headers['location'] + '/visual', headers=headers).status_code == 410


def test_mask_reads_require_view_and_expiration_preserves_canonical_result(run_api, visual_store, session_factory):
    client, ids, headers, *_ = run_api
    now = [0.0]
    visual_store.clock = lambda: now[0]
    response = client.post(BASE + '?stream_profile=visual-v2', json={'order_ids': ids}, headers=headers)
    events = visual(response)
    reference = next(entry['data']['mask']['mask_ref'] for entry in events if entry['event'] == 'piece_ready')
    path = response.headers['location'] + '/visual/masks/' + reference
    assert client.get(path).status_code == 401
    assert client.get(path, headers=headers).status_code == 200
    assert client.get(response.headers['location'] + '/visual/masks/' + 'f' * 32, headers=headers).status_code == 404
    now[0] = 300.0
    assert client.get(path, headers=headers).status_code == 410
    assert client.get(response.headers['location'], headers=headers).json()['completo']
    with session_factory() as session:
        permission = session.scalar(select(Permiso.id_permiso).where(Permiso.codigo == 'optimization.view'))
        session.execute(delete(RolPermiso).where(RolPermiso.id_rol == 3, RolPermiso.id_permiso == permission))
        session.commit()
    assert client.get(path, headers=headers).status_code == 403


def test_visual_reservation_is_released_when_acceptance_fails(run_api, visual_store, run_admission):
    client, ids, headers, *_ = run_api
    response = client.post(BASE + '?stream_profile=visual-v2', json={'order_ids': [999999]}, headers=headers)
    assert response.status_code == 404
    assert visual_store.contexts == [] and run_admission.active() == 0


def test_full_visual_budget_reports_unavailable_without_changing_placements(run_api, visual_store):
    client, ids, headers, *_ = run_api
    visual_store.max_bytes = 1
    response = client.post(BASE + '?stream_profile=visual-v2', json={'order_ids': ids}, headers=headers)
    events = visual(response)
    assert events[-1]['data']['completo']
    masks = [entry['data']['mask'] for entry in events if 'mask' in entry['data']]
    assert masks and all(not mask['available'] and mask['reason'] == 'VISUAL_BUDGET_EXCEEDED' for mask in masks)
    result = client.get(response.headers['location'], headers=headers).json()
    assert result['placed_units'] == 4 and result['confirmable']


def test_visual_overhead_is_excluded_from_both_clocks(run_api, visual_store, monkeypatch):
    from app.modules.optimization.infrastructure.visual_store import VisualSession
    from app.modules.optimization.presentation import run_routes
    from functools import partial
    client, ids, headers, _, calculator = run_api
    now = [0]
    calculator.clock = lambda: now[0]
    original = VisualSession.register
    def register(self, *args):
        now[0] += 60_000_000_000
        return original(self, *args)
    monkeypatch.setattr(VisualSession, 'register', register)
    monkeypatch.setattr(run_routes, 'LiveRunStream', partial(LiveRunStream, clock=lambda: now[0] / 1e9, time_budget_s=1))
    response = client.post(BASE + '?stream_profile=visual-v2', json={'order_ids': ids}, headers=headers)
    events = visual(response)
    assert events[-1]['event'] == 'optimization_completed'
    result = client.get(response.headers['location'], headers=headers).json()
    assert result['tiempo_computacional_ms'] == 0 and now[0] > 120_000_000_000


def test_disconnect_after_selection_preserves_the_actual_diagnostic_placement(run_api, visual_store, prepared):
    _, ids, _, uow, calculator = run_api
    session = visual_store.reserve()
    accepted = AcceptRun(uow).execute(ids, prepared[0])
    session.bind(accepted.optimization_id, accepted.result.problem.config.resolution_mm)
    owner = LiveRunStream(uow, calculator, visual_session=session)
    async def consume():
        stream = owner.lines(accepted)
        try:
            while json.loads(await anext(stream))['event'] != 'source_selected':
                pass
        finally:
            await stream.aclose()
    asyncio.run(consume())
    with uow() as transaction:
        result = transaction.runs.get(accepted.optimization_id)
    assert result.status.value == 'FALLIDA' and result.result.placed_units == 1
    assert session.finished_at is not None


def test_slow_visual_consumer_does_not_spend_compute_budget_or_expire_active_masks(
        run_api, visual_store, run_admission, prepared, session_factory):
    _, ids, _, uow, calculator = run_api
    now = [0.0]
    visual_store.clock = lambda: now[0]
    session = visual_store.reserve()
    lease = run_admission.acquire(prepared[0])
    accepted = AcceptRun(uow).execute(ids, prepared[0])
    session.bind(accepted.optimization_id, accepted.result.problem.config.resolution_mm)
    owner = LiveRunStream(uow, calculator, visual_session=session, lease=lease,
        clock=lambda: now[0], time_budget_s=1)
    async def consume():
        stream = owner.lines(accepted)
        try:
            assert json.loads(await anext(stream))['event'] == 'optimization_started'
            assert json.loads(await anext(stream))['event'] == 'preparation_started'
            now[0] = 301.0  # Consumer is suspended at the acknowledged bounded bridge.
            assert run_admission.active() == 1
            assert visual_store.get(accepted.optimization_id) is session
            assert session.records == {}  # Producer cannot run ahead of this event.
            events = [json.loads(raw) async for raw in stream]
            assert events[-1]['event'] == 'optimization_completed'
            assert events[-1]['data']['processed_units'] == 4
        finally:
            await stream.aclose()
    asyncio.run(consume())
    assert run_admission.active() == 0 and session.finished_at == 301.0
    with session_factory() as db:
        assert db.get(Plancha, 5).cantidad == 2
        assert db.scalar(select(func.count()).select_from(MovimientoInventario)) == 0
