"""Supervisor con PostgreSQL real y tres workers spawn; sin HTTP ni red externa.

Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Thread
from dataclasses import replace
import logging

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import TimeoutError as PoolTimeout

from app.models import MetricaEjecucion, MovimientoInventario, Optimizacion, Pedido, Plancha
from app.modules.optimization.application.comparison_confirmation import ConfirmComparison
from app.modules.optimization.application.comparison_calculation import CalculateComparison
from app.modules.optimization.application.errors import WorkersNotStopped
from app.modules.optimization.infrastructure.comparison_runner import ComparisonProcessRunner
from app.modules.optimization.infrastructure import comparison_runner
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.infrastructure.in_process_admission import InProcessRunAdmission
from tests.unit.optimization.test_comparison_runner import crash_best_fit
from .test_comparison_persistence import comparison_setup, accept  # noqa: F401
from .test_runs import prepared  # noqa: F401


def test_real_pipeline_persists_three_results_before_notifying_and_releases_after_join(session_factory, comparison_setup):
    current = accept(comparison_setup)
    actor, ids, uow = comparison_setup
    admission, signals, observed_commits = InProcessRunAdmission(), [], []
    lease = admission.acquire_comparison(actor)
    def observed(signal):
        signals.append(signal)
        if signal.kind == "result_persisted":
            with uow() as tx:
                loaded = tx.comparisons.get(current.comparison_id)
            observed_commits.append((signal.execution_id,
                next(e.status for e in loaded.executions if e.execution_id == signal.execution_id), admission.active()))
    finished = CalculateComparison(uow, ComparisonProcessRunner()).execute(current.comparison_id, observed, lease=lease)
    assert finished.terminal and finished.status == "COMPLETADA" and finished.selected_execution_id is None
    assert all(e.eligible and e.result.method == e.method for e in finished.executions)
    assert len(observed_commits) == 3 and all(status == "COMPLETADA" and active == 1 for _, status, active in observed_commits)
    assert signals[-1].kind == "comparison_finished" and signals[-1].method is None
    assert admission.active() == 0
    for method in ("FF", "BF", "WF"):
        facts = [s.payload for s in signals if s.method == method and s.kind == "visual"]
        assert next(f for f in facts if f.kind == "ordering_ready").ordered_units == current.problem.units
    with session_factory() as s:
        snapshot = s.get(Optimizacion, current.comparison_id).comparison_snapshot
        assert len(snapshot["worker_processes"]) == 3
        assert snapshot["supervisor_identity"]["pid"] > 0
        assert s.get(Plancha, 5).cantidad == 2
        assert [s.get(Pedido, i).estado for i in ids] == ["OPTIMIZADO"] * 2
    assert CalculateComparison(uow, ComparisonProcessRunner()).execute(current.comparison_id) == finished


def test_lost_observer_does_not_cancel_or_restart_calculations(comparison_setup):
    current = accept(comparison_setup)
    _, _, uow = comparison_setup
    calls = []
    def disconnected(signal):
        calls.append(signal)
        raise ConnectionError("synthetic disconnected viewer")
    finished = CalculateComparison(uow, ComparisonProcessRunner()).execute(current.comparison_id, disconnected)
    assert len(calls) == 1 and all(e.eligible for e in finished.executions)


def test_failed_engine_keeps_successful_persisted_results(comparison_setup):
    current = accept(comparison_setup)
    _, _, uow = comparison_setup
    finished = CalculateComparison(uow, ComparisonProcessRunner(worker_target=crash_best_fit)).execute(current.comparison_id)
    assert finished.terminal and finished.incomplete
    assert [e.eligible for e in finished.executions] == [True, False, True]
    assert finished.selected_execution_id is None


def test_result_commit_failure_is_isolated_to_its_engine(session_factory, comparison_setup):
    current = accept(comparison_setup)
    _, _, uow = comparison_setup
    bf_id = next(e.execution_id for e in current.executions if e.method == "BF")
    def fail(session, flush_context, instances):
        if any(isinstance(o, MetricaEjecucion) and o.id_ejecucion == bf_id for o in session.new):
            raise RuntimeError("synthetic metric write failure")
    event.listen(session_factory.class_, "before_flush", fail)
    try:
        finished = CalculateComparison(uow, ComparisonProcessRunner()).execute(current.comparison_id)
    finally:
        event.remove(session_factory.class_, "before_flush", fail)
    assert finished.incomplete and [e.eligible for e in finished.executions] == [True, False, True]
    assert finished.executions[1].failure_code == "RESULT_SAVE_FAILED"


def test_pool_timeout_after_valid_ff_calculation_preserves_bf_wf_and_inventory(session_factory, comparison_setup, caplog):
    current = accept(comparison_setup)
    _, _, uow = comparison_setup
    original = session_factory.kw["bind"]
    assert original.url.host == "127.0.0.1" and original.url.username == "r1_test"
    engine = create_engine(original.url, pool_size=1, max_overflow=0, pool_timeout=.2)
    acquired, release = Event(), Event()
    results, holders = [], []
    real = ComparisonProcessRunner()
    def occupy():
        with engine.connect():
            acquired.set()
            release.wait(timeout=5)
    class ReleaseOnFailure(logging.Handler):
        def emit(self, record):
            if record.exc_info and isinstance(record.exc_info[1], PoolTimeout):
                release.set()
    logger = logging.getLogger("app.modules.optimization.application.comparison_calculation")
    handler = ReleaseOnFailure()
    logger.addHandler(handler)
    class BlockedFirstFit:
        supervisor_identity = real.supervisor_identity
        def calculate(self, *args, **kwargs):
            stream = real.calculate(*args, **kwargs)
            try:
                for packet in stream:
                    if packet["method"] == "FF" and packet["kind"] == "result":
                        results.append(packet["payload"].result)
                        holder = Thread(target=occupy)
                        holders.append(holder)
                        holder.start()
                        assert acquired.wait(timeout=5)
                    yield packet
            finally:
                stream.close()
    session_factory.configure(bind=engine)
    try:
        finished = CalculateComparison(uow, BlockedFirstFit()).execute(current.comparison_id)
        assert len(results) == 1
        direct, _ = calculate_metrics(FirstFitOptimizer().optimize(current.problem), current.minimum_width_mm, current.minimum_height_mm)
        assert replace(results[0], computation_time_ms=None) == direct
        assert finished.executions[0].failure_code == "RESULT_SAVE_FAILED"
        assert [execution.eligible for execution in finished.executions] == [False, True, True]
        assert any(record.exc_info and isinstance(record.exc_info[1], PoolTimeout) for record in caplog.records)
        assert real.last_report["all_workers_stopped"]
        with session_factory() as session:
            assert session.get(Plancha, 5).cantidad == 2
        bf = next(execution for execution in finished.executions if execution.method == 'BF')
        with uow() as tx:
            selected = tx.comparisons.select(finished.comparison_id, bf.execution_id, finished.version)
        command = ConfirmComparison(uow)
        receipt = command.execute(finished.comparison_id, bf.execution_id, selected.version, 'partial-bf-confirmation', comparison_setup[0])
        assert command.execute(finished.comparison_id, bf.execution_id, selected.version, 'partial-bf-confirmation', comparison_setup[0]) == receipt
        with session_factory() as session:
            movements = list(session.scalars(select(MovimientoInventario).where(
                MovimientoInventario.id_optimizacion == finished.comparison_id,
                MovimientoInventario.tipo_evento == 'CONSUMO_OPTIMIZACION')))
            assert len(movements) == 1 and movements[0].cantidad_afectada == 2
            assert session.get(Plancha, 5).cantidad == 0
        with uow() as tx:
            recovered = tx.comparisons.get(finished.comparison_id)
        assert recovered.confirmation['method'] == 'BF' and recovered.executions[0].status == 'FALLIDA'
    finally:
        release.set()
        for holder in holders:
            holder.join(timeout=5)
        logger.removeHandler(handler)
        session_factory.configure(bind=original)
        engine.dispose()


def test_preflight_failure_safely_reconciles_accepted_orders_and_releases_admission(session_factory, comparison_setup, monkeypatch):
    current = accept(comparison_setup)
    actor, ids, uow = comparison_setup
    admission = InProcessRunAdmission()
    monkeypatch.setattr(comparison_runner, "available_memory", lambda: 0)
    finished = CalculateComparison(uow, ComparisonProcessRunner()).execute(current.comparison_id,
        lease=admission.acquire_comparison(actor))
    assert finished.terminal and finished.status == "FALLIDA" and admission.active() == 0
    assert all(e.failure_code == "MEMORY_BUDGET_EXCEEDED" for e in finished.executions)
    with session_factory() as s:
        assert [s.get(Pedido, i).estado for i in ids] == ["PENDIENTE"] * 2


def test_unproven_worker_termination_keeps_admission_and_orders(session_factory, comparison_setup):
    class UnsafeRunner:
        def calculate(self, *args, **kwargs):
            raise WorkersNotStopped("synthetic unproven termination")
            yield
    current = accept(comparison_setup)
    actor, ids, uow = comparison_setup
    admission = InProcessRunAdmission()
    lease = admission.acquire_comparison(actor)
    try:
        with pytest.raises(WorkersNotStopped):
            CalculateComparison(uow, UnsafeRunner()).execute(current.comparison_id, lease=lease)
        assert admission.active() == 1
        with session_factory() as s:
            assert [s.get(Pedido, i).estado for i in ids] == ["EN_OPTIMIZACION"] * 2
    finally:
        # La simulación no creó procesos reales; se limpia su lease de prueba.
        lease.release()


def test_concurrent_supervisor_claim_cannot_start_another_calculation(comparison_setup):
    current = accept(comparison_setup)
    _, _, uow = comparison_setup
    entered, proceed = Event(), Event()
    def hold(signal):
        if signal.kind == "started" and not entered.is_set():
            entered.set()
            proceed.wait(timeout=5)
    with ThreadPoolExecutor(max_workers=1) as pool:
        running = pool.submit(CalculateComparison(uow, ComparisonProcessRunner()).execute,
                              current.comparison_id, hold)
        try:
            assert entered.wait(timeout=5)
            observed = CalculateComparison(uow, ComparisonProcessRunner()).execute(current.comparison_id)
            assert not observed.terminal
        finally:
            proceed.set()
        assert running.result(timeout=15).terminal
