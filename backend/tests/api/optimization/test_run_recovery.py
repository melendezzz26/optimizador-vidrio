"""TA-049: real HTTP/PostgreSQL recovery, without changing engine budgets."""
import asyncio
import pytest
from sqlalchemy import event, func, select

from app.models import (EjecucionOptimizacion, MaterialUtilizado, MetricaEjecucion,
                        MovimientoInventario, Optimizacion, Pedido, Plancha)
from app.modules.optimization.application.errors import ExecutionInterrupted, TimeBudgetExceeded
from app.modules.optimization.application.runs import AcceptRun
from app.modules.optimization.application.run_recovery import RecoverStoppedRun
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.presentation import run_stream
from tests.api.optimization.test_runs_api import BASE, parse, run_api  # noqa: F401
from tests.integration.optimization.test_runs import prepared  # noqa: F401


def assert_released(factory, ids, identifier, code):
    with factory() as db:
        parent = db.get(Optimizacion, identifier)
        execution = db.scalar(select(EjecucionOptimizacion).where(
            EjecucionOptimizacion.id_optimizacion == identifier))
        assert parent.estado == execution.estado == 'FALLIDA'
        assert parent.fecha_fin == execution.fecha_fin
        assert parent.id_ejecucion_seleccionada is None
        assert execution.patron_resultado['failure_code'] == code
        assert [db.get(Pedido, i).estado for i in ids] == ['PENDIENTE'] * len(ids)
        assert db.get(Plancha, 5).cantidad == 2
        for model in (MovimientoInventario, MaterialUtilizado, MetricaEjecucion):
            assert db.scalar(select(func.count()).select_from(model)) == 0


@pytest.mark.parametrize('error,code', [
    (TimeBudgetExceeded, 'TIME_BUDGET_EXCEEDED'),
    (ExecutionInterrupted, 'EXECUTION_INTERRUPTED'),
    (RuntimeError, 'CALCULATION_FAILED'),
])
@pytest.mark.parametrize('after_last_piece', [False, True])
def test_stopped_engine_releases_entire_batch_and_can_retry(
        run_api, session_factory, monkeypatch, error, code, after_last_piece):
    client, ids, headers, uow, _ = run_api
    original = FirstFitOptimizer.optimize

    def broken(self, problem, on_event=None, **kwargs):
        def callback(fact):
            on_event(fact)
            if fact.kind == 'piece_placed' and (
                    not after_last_piece or fact.placed_units == fact.total_units):
                raise error('synthetic engine failure')
        return original(self, problem, callback, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(FirstFitOptimizer, 'optimize', broken)
        response = client.post(BASE, json={'order_ids': ids}, headers=headers)
    terminal = parse(response)[-1]
    assert terminal['event'] == 'optimization_failed'
    assert terminal['data']['code'] == code
    identifier = terminal['id_optimizacion']
    assert_released(session_factory, ids, identifier, code)
    assert client.post(f'{BASE}/{identifier}/confirm', headers=headers).status_code == 422
    retried = parse(client.post(BASE, json={'order_ids': ids}, headers=headers))
    assert retried[-1]['data']['estado'] == 'COMPLETADA'
    # A late failure from the old owner must not release the new run's orders.
    with uow() as tx:
        tx.runs.fail(identifier, code)
    with session_factory() as db:
        assert [db.get(Pedido, i).estado for i in ids] == ['OPTIMIZADO'] * len(ids)


def test_failed_result_flush_rolls_back_then_releases_in_separate_transaction(
        run_api, session_factory):
    client, ids, headers, *_ = run_api
    injected = []

    def fail_after_writes(db, context):
        if db.scalar(select(Optimizacion.estado)) == 'COMPLETADA':
            injected.append(True)
            raise RuntimeError('synthetic failure after result SQL')

    event.listen(session_factory.class_, 'after_flush_postexec', fail_after_writes)
    try:
        response = client.post(BASE, json={'order_ids': ids}, headers=headers)
    finally:
        event.remove(session_factory.class_, 'after_flush_postexec', fail_after_writes)
    terminal = parse(response)[-1]
    assert injected == [True]
    assert terminal['data']['code'] == 'RESULT_SAVE_FAILED'
    assert_released(session_factory, ids, terminal['id_optimizacion'], 'RESULT_SAVE_FAILED')


def test_deadline_after_last_engine_checkpoint_cannot_commit_no_solution(
        run_api, session_factory, monkeypatch):
    client, ids, headers, *_ = run_api
    now = [0.0]
    original = FirstFitOptimizer.optimize
    stream = run_stream.LiveRunStream
    monkeypatch.setattr('app.modules.optimization.presentation.run_routes.LiveRunStream',
                        lambda *a, **kw: stream(*a, **kw, clock=lambda: now[0]))

    def overtime(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        now[0] = 121.0
        return result

    monkeypatch.setattr(FirstFitOptimizer, 'optimize', overtime)
    with session_factory() as db:
        db.get(Plancha, 5).ancho_mm = 1  # Valid input with legitimate NO_FIT.
        db.commit()
    response = client.post(BASE, json={'order_ids': ids}, headers=headers)
    terminal = parse(response)[-1]
    assert terminal['event'] == 'optimization_failed'
    assert terminal['data']['code'] == 'TIME_BUDGET_EXCEEDED'
    assert_released(session_factory, ids, terminal['id_optimizacion'], 'TIME_BUDGET_EXCEEDED')


def test_worker_start_failure_recovers_accepted_orders(run_api, session_factory, monkeypatch):
    client, ids, headers, *_ = run_api

    class CannotStart:
        def __init__(self, **kwargs):
            pass

        def start(self):
            raise RuntimeError('synthetic thread start failure')

    monkeypatch.setattr(run_stream, 'Thread', CannotStart)
    client.post(BASE, json={'order_ids': ids}, headers=headers)
    with session_factory() as db:
        identifier = db.scalar(select(Optimizacion.id_optimizacion))
    assert_released(session_factory, ids, identifier, 'EXECUTION_INTERRUPTED')


def test_error_constructing_stream_after_acceptance_is_propagated_and_recovers(
        run_api, session_factory, monkeypatch):
    client, ids, headers, *_ = run_api

    def broken_stream(*args, **kwargs):
        raise RuntimeError('synthetic stream allocation failure')

    monkeypatch.setattr('app.modules.optimization.presentation.run_routes.LiveRunStream', broken_stream)
    response = client.post(BASE, json={'order_ids': ids}, headers=headers)
    assert response.status_code == 500
    with session_factory() as db:
        identifier = db.scalar(select(Optimizacion.id_optimizacion))
    assert_released(session_factory, ids, identifier, 'EXECUTION_INTERRUPTED')


def test_disconnect_before_body_iterator_starts_recovers_accepted_batch(run_api, session_factory, prepared):
    _, ids, _, uow, calculator = run_api
    accepted = AcceptRun(uow).execute(ids, prepared[0])
    stream = run_stream.LiveRunStream(uow, calculator, accepted=accepted)
    response = run_stream.RunStreamingResponse(stream.lines(accepted), stream=stream)

    async def closed_connection(message):
        raise OSError('synthetic disconnect before response body')

    with pytest.raises(OSError):
        asyncio.run(response.stream_response(closed_connection))
    stream.release_if_idle()  # Repeated ASGI cleanup is harmless.
    assert not stream.worker_started
    assert_released(session_factory, ids, accepted.optimization_id, 'EXECUTION_INTERRUPTED')


def test_failure_of_recovery_commit_is_visible_and_requires_reconciliation(
        run_api, session_factory, prepared, monkeypatch, caplog):
    client, ids, headers, uow, _ = run_api

    def broken_engine(*args, **kwargs):
        raise RuntimeError('synthetic calculation failure')

    def broken_recovery(db, context):
        if db.scalar(select(Optimizacion.estado)) == 'FALLIDA':
            raise RuntimeError('synthetic recovery commit failure')

    event.listen(session_factory.class_, 'after_flush_postexec', broken_recovery)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(FirstFitOptimizer, 'optimize', broken_engine)
            response = client.post(BASE, json={'order_ids': ids}, headers=headers)
    finally:
        event.remove(session_factory.class_, 'after_flush_postexec', broken_recovery)
    terminal = parse(response)[-1]
    assert terminal['event'] == 'optimization_failed'
    identifier = terminal['id_optimizacion']
    canonical = client.get(response.headers['location'], headers=headers).json()
    assert canonical['estado'] == 'EN_EJECUCION' and not canonical['confirmable']
    assert 'Cannot record failure' in caplog.text
    with session_factory() as db:
        assert [db.get(Pedido, i).estado for i in ids] == ['EN_OPTIMIZACION'] * len(ids)
    RecoverStoppedRun(uow).execute(identifier, service_stopped=True)
    assert_released(session_factory, ids, identifier, 'EXECUTION_INTERRUPTED')
