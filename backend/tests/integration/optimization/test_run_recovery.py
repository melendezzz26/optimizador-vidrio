"""TA-049: fences, atomic rollback, concurrency and explicit crash recovery."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import subprocess
import sys

import pytest
from sqlalchemy import event, select

from app.models import EjecucionOptimizacion, MovimientoInventario, Optimizacion, Pedido
from app.modules.optimization.application.errors import RunError
from app.modules.optimization.application.confirmation import ConfirmRun
from app.modules.optimization.application.run_recovery import RecoverStoppedRun
from app.modules.optimization.application.runs import AcceptRun
from tests.integration.optimization.test_runs import prepared  # noqa: F401
from tests.integration.optimization.test_run_states import calculator, inventory


def states(factory, ids):
    with factory() as db:
        return [db.get(Pedido, i).estado for i in ids]


def test_failure_and_order_release_have_one_commit_or_total_rollback(session_factory, prepared):
    actor, ids, uow = prepared
    accepted = AcceptRun(uow).execute(ids, actor)
    before = inventory(session_factory)

    def reject(db, context):
        if db.scalar(select(Optimizacion.estado)) == 'FALLIDA':
            assert list(db.scalars(select(Pedido.estado))) == ['PENDIENTE'] * 2
            raise RuntimeError('synthetic recovery SQL failure')

    event.listen(session_factory.class_, 'after_flush_postexec', reject)
    try:
        with pytest.raises(RuntimeError, match='recovery SQL'):
            with uow() as tx:
                tx.runs.fail(accepted.optimization_id, 'TIME_BUDGET_EXCEEDED')
    finally:
        event.remove(session_factory.class_, 'after_flush_postexec', reject)
    with uow() as tx:
        assert tx.runs.get(accepted.optimization_id) == accepted
    assert states(session_factory, ids) == ['EN_OPTIMIZACION'] * 2
    commits = []

    def committed(db):
        commits.append(True)

    event.listen(session_factory.class_, 'after_commit', committed)
    try:
        with uow() as tx:
            tx.runs.fail(accepted.optimization_id, 'TIME_BUDGET_EXCEEDED')
    finally:
        event.remove(session_factory.class_, 'after_commit', committed)
    assert commits == [True]
    assert states(session_factory, ids) == ['PENDIENTE'] * 2
    assert inventory(session_factory) == before


@pytest.mark.parametrize('corruption', ['mixed_orders', 'consumption'])
def test_inconsistent_batch_blocks_failure_without_partial_reset(session_factory, prepared, corruption):
    actor, ids, uow = prepared
    accepted = AcceptRun(uow).execute(ids, actor)
    with session_factory() as db:
        if corruption == 'mixed_orders':
            db.get(Pedido, ids[-1]).estado = 'CANCELADO'
        else:
            db.add(MovimientoInventario(id_plancha=5, tipo_evento='CONSUMO_OPTIMIZACION',
                motivo='Synthetic inconsistency', id_usuario=actor, id_optimizacion=accepted.optimization_id,
                cantidad_afectada=1, fecha=datetime.now(timezone.utc)))
        db.commit()
    before = states(session_factory, ids)
    with pytest.raises(RunError, match='requiere revisión|estado del lote'):
        with uow() as tx:
            tx.runs.fail(accepted.optimization_id, 'CALCULATION_FAILED')
    with uow() as tx:
        assert tx.runs.get(accepted.optimization_id) == accepted
    assert states(session_factory, ids) == before


def test_two_failures_and_new_acceptance_never_release_another_owner(session_factory, prepared):
    actor, ids, uow = prepared
    first, unrelated = [AcceptRun(uow).execute([i], actor) for i in ids]

    def fail():
        with uow() as tx:
            return tx.runs.fail(first.optimization_id, 'TIME_BUDGET_EXCEEDED')

    with ThreadPoolExecutor(2) as pool:
        futures = [pool.submit(fail) for _ in range(2)]
        results = [f.result(timeout=10) for f in futures]
    assert results[0] == results[1]
    assert states(session_factory, ids) == ['PENDIENTE', 'EN_OPTIMIZACION']
    successor = AcceptRun(uow).execute(ids[:1], actor)
    fail()
    RecoverStoppedRun(uow).execute(first.optimization_id, service_stopped=True)
    assert states(session_factory, ids) == ['EN_OPTIMIZACION'] * 2
    with uow() as tx:
        assert tx.runs.get(successor.optimization_id) == successor
        assert tx.runs.get(unrelated.optimization_id) == unrelated


def test_late_failure_refreshes_previously_loaded_terminal_state(session_factory, prepared):
    actor, ids, uow = prepared
    accepted = AcceptRun(uow).execute(ids, actor)
    with uow() as stale:
        # Keep strong ORM references to exercise SQLAlchemy's identity map.
        parent = stale.session.get(Optimizacion, accepted.optimization_id)
        execution = stale.session.scalar(select(EjecucionOptimizacion))
        stale.runs.get(accepted.optimization_id)
        final = calculator(session_factory, uow).execute(accepted.optimization_id)
        assert stale.runs.fail(accepted.optimization_id, 'EXECUTION_INTERRUPTED') == final
        assert parent.estado == execution.estado == 'COMPLETADA'
    assert states(session_factory, ids) == ['OPTIMIZADO'] * 2


def test_abrupt_process_exit_requires_explicit_offline_reconciliation(session_factory, prepared):
    actor, ids, uow = prepared
    before = inventory(session_factory)
    script = '''
from functools import partial
import os, sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.modules.optimization.application.runs import AcceptRun
from app.modules.optimization.infrastructure.run_uow import SqlRunUnitOfWork
factory = sessionmaker(bind=create_engine(sys.argv[1]))
AcceptRun(partial(SqlRunUnitOfWork, factory)).execute([int(i) for i in sys.argv[3:]], int(sys.argv[2]))
os._exit(23)  # No finally, disconnect callback, shutdown or worker cleanup.
'''
    process = subprocess.run([sys.executable, '-c', script,
        session_factory.kw['bind'].url.render_as_string(hide_password=False), str(actor), *map(str, ids)],
        capture_output=True, text=True, timeout=30)
    assert process.returncode == 23, process.stderr
    with session_factory() as db:
        identifier = db.scalar(select(Optimizacion.id_optimizacion))
    assert states(session_factory, ids) == ['EN_OPTIMIZACION'] * 2
    with pytest.raises(RunError) as blocked:
        RecoverStoppedRun(uow).execute(identifier)
    assert blocked.value.code == 'RECOVERY_BLOCKED'
    recovered = RecoverStoppedRun(uow).execute(identifier, service_stopped=True)
    assert recovered.status.value == 'FALLIDA'
    assert states(session_factory, ids) == ['PENDIENTE'] * 2
    assert RecoverStoppedRun(uow).execute(identifier, service_stopped=True) == recovered
    assert inventory(session_factory) == before
    assert calculator(session_factory, uow).execute(AcceptRun(uow).execute(ids, actor).optimization_id).confirmable


def test_historical_failed_run_can_be_reconciled_without_rewriting_diagnostic(session_factory, prepared):
    actor, ids, uow = prepared
    accepted = AcceptRun(uow).execute(ids, actor)
    with uow() as tx:
        failed = tx.runs.fail(accepted.optimization_id, 'RESULT_SAVE_FAILED')
    # Reproduce the pre-TA049 durable state (FALLIDA + retained orders).
    with session_factory() as db:
        for i in ids:
            db.get(Pedido, i).estado = 'EN_OPTIMIZACION'
        db.commit()
    assert RecoverStoppedRun(uow).execute(accepted.optimization_id, service_stopped=True) == failed
    assert states(session_factory, ids) == ['PENDIENTE'] * 2


@pytest.mark.parametrize('terminal', ['complete', 'no_solution', 'confirmed'])
def test_reconciliation_and_late_failure_preserve_terminal_outcomes(session_factory, prepared, terminal):
    from app.models import Plancha
    actor, ids, uow = prepared
    if terminal == 'no_solution':
        with session_factory() as db:
            db.get(Plancha, 5).cantidad = 0
            db.commit()
    accepted = AcceptRun(uow).execute(ids, actor)
    final = calculator(session_factory, uow).execute(accepted.optimization_id)
    if terminal == 'confirmed':
        ConfirmRun(uow).execute(accepted.optimization_id, actor)
        with uow() as tx:
            final = tx.runs.get(accepted.optimization_id)
    before = inventory(session_factory)
    expected_orders = states(session_factory, ids)
    with uow() as tx:
        assert tx.runs.fail(accepted.optimization_id, 'TIME_BUDGET_EXCEEDED') == final
    assert RecoverStoppedRun(uow).execute(accepted.optimization_id, service_stopped=True) == final
    assert states(session_factory, ids) == expected_orders
    assert inventory(session_factory) == before
