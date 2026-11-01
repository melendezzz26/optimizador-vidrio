"""PostgreSQL aislado: tres identidades, entrada común y elección sin consumo.

Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
"""
from dataclasses import replace
from functools import partial
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import event, func, select

from app.models import (Configuracion, EjecucionOptimizacion, MaterialUtilizado,
    MetricaEjecucion, MovimientoInventario, Optimizacion, Pedido, Pieza, Plancha)
from app.modules.optimization.application.comparisons import AcceptComparison
from app.modules.optimization.application.errors import RunError
from app.modules.optimization.domain.best_fit import BestFitOptimizer
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.worst_fit import WorstFitOptimizer
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.infrastructure.comparison_uow import SqlComparisonUnitOfWork
from .test_runs import prepared  # noqa: F401

ENGINES = {"FF": FirstFitOptimizer, "BF": BestFitOptimizer, "WF": WorstFitOptimizer}


@pytest.fixture
def comparison_setup(session_factory, prepared):
    actor, ids, _ = prepared
    return actor, ids, partial(SqlComparisonUnitOfWork, session_factory)


def accept(setup, key="comparison-test-0001"):
    actor, ids, uow = setup
    return AcceptComparison(uow).execute(ids, actor, key)


def save(uow, current, method):
    execution = next(e for e in current.executions if e.method == method)
    result = ENGINES[method]().optimize(current.problem)
    result, residuals = calculate_metrics(result, current.minimum_width_mm, current.minimum_height_mm)
    result = replace(result, computation_time_ms=17)
    with uow() as tx:
        return tx.comparisons.save_result(current.comparison_id, execution.execution_id, result, residuals)


def finish(uow, current):
    with uow() as tx:
        return tx.comparisons.finish_after_workers_stopped(current.comparison_id)


def test_accept_single_commit_three_identities_original_request_and_one_stock_read(session_factory, comparison_setup):
    actor, ids, uow = comparison_setup
    commits, stock_reads = [], []
    def committed(s): commits.append(True)
    def statement(c, cur, sql, params, context, many):
        if "UNION ALL" in sql and "planchas" in sql and "retazos" in sql:
            stock_reads.append(sql)
    engine = session_factory.kw["bind"]
    event.listen(session_factory.class_, "after_commit", committed)
    event.listen(engine, "before_cursor_execute", statement)
    try:
        current = accept(comparison_setup)
    finally:
        event.remove(session_factory.class_, "after_commit", committed)
        event.remove(engine, "before_cursor_execute", statement)
    assert len(commits) == len(stock_reads) == 1
    assert [e.method for e in current.executions] == ["FF", "BF", "WF"]
    assert len({e.execution_id for e in current.executions}) == 3
    assert current.selected_execution_id is None and not current.terminal
    assert current.problem.order_ids == tuple(ids)
    assert [p["cantidad"] for p in current.requested_pieces] == [2, 2]
    assert dict(current.requested_pieces[0]["dimensiones"]) == {"width_mm": 2, "height_mm": 2}
    with pytest.raises(TypeError):
        current.requested_pieces[0]["dimensiones"]["width_mm"] = 99
    with session_factory() as s:
        assert [s.get(Pedido, i).estado for i in ids] == ["EN_OPTIMIZACION"] * 2
        assert s.get(Plancha, 5).cantidad == 2
        assert s.scalar(select(func.count()).select_from(MovimientoInventario)) == 0


def test_repeated_and_concurrent_acceptance_are_idempotent(session_factory, comparison_setup):
    gate = Barrier(2)
    def submitted():
        gate.wait(timeout=5)
        return accept(comparison_setup)
    with ThreadPoolExecutor(max_workers=2) as pool:
        left, right = [f.result(timeout=15) for f in [pool.submit(submitted), pool.submit(submitted)]]
    assert left == right == accept(comparison_setup)
    with session_factory() as s:
        assert s.scalar(select(func.count()).select_from(Optimizacion)) == 1
        assert s.scalar(select(func.count()).select_from(EjecucionOptimizacion)) == 3
    actor, ids, uow = comparison_setup
    with pytest.raises(RunError, match="otro lote"):
        AcceptComparison(uow).execute(ids[:1], actor, "comparison-test-0001")


def test_original_request_and_inventory_are_not_reloaded_per_engine(session_factory, comparison_setup):
    current = accept(comparison_setup)
    _, ids, uow = comparison_setup
    with session_factory() as s:
        p = s.scalar(select(Pieza).where(Pieza.id_pedido == ids[0]))
        p.dimensiones = {"width_mm": 999, "height_mm": 999}
        s.get(Plancha, 5).cantidad = 1
        s.scalar(select(Configuracion)).margen_mm = 1
        s.commit()
    for method in ("WF", "FF", "BF"):
        current = save(uow, current, method)
        assert current.selected_execution_id is None and current.status == "EN_EJECUCION"
    assert all(e.result.complete and e.result.problem == current.problem for e in current.executions)
    assert all(e.result.method == e.method for e in current.executions)
    assert current.requested_pieces[0]["dimensiones"]["width_mm"] == 2
    with uow() as tx:
        assert tx.comparisons.get(current.comparison_id) == current
    with session_factory() as s:
        assert s.get(Plancha, 5).cantidad == 1


def test_select_only_after_terminal_and_never_consumes_stock(session_factory, comparison_setup):
    current = accept(comparison_setup)
    _, ids, uow = comparison_setup
    current = save(uow, current, "BF")
    execution = next(e for e in current.executions if e.method == "BF")
    with pytest.raises(RunError), uow() as tx:
        tx.comparisons.select(current.comparison_id, execution.execution_id, current.version)
    for method in ("FF", "WF"):
        current = save(uow, current, method)
    with pytest.raises(RunError), uow() as tx:
        tx.comparisons.select(current.comparison_id, execution.execution_id, current.version)
    current = finish(uow, current)
    assert current.selected_execution_id is None
    with uow() as tx:
        selected = tx.comparisons.select(current.comparison_id, execution.execution_id, current.version)
    assert selected.version == current.version + 1
    assert selected.selected_execution_id == execution.execution_id
    with pytest.raises(RunError), uow() as tx:
        tx.comparisons.select(current.comparison_id, execution.execution_id, current.version)
    with session_factory() as s:
        assert s.get(Plancha, 5).cantidad == 2
        assert [s.get(Pedido, i).estado for i in ids] == ["OPTIMIZADO"] * 2
        assert s.scalar(select(func.count()).select_from(MovimientoInventario)) == 0
        assert s.scalar(select(func.count()).select_from(MetricaEjecucion)) == 3
        assert s.scalar(select(func.count()).select_from(MaterialUtilizado)) == 3


def test_failed_method_keeps_other_results_and_becomes_incomplete(comparison_setup):
    current = accept(comparison_setup)
    _, _, uow = comparison_setup
    current = save(uow, current, "WF")
    current = save(uow, current, "FF")
    execution = next(e for e in current.executions if e.method == "BF")
    with uow() as tx:
        current = tx.comparisons.fail_execution(current.comparison_id, execution.execution_id, "MEMORY_BUDGET_EXCEEDED")
    current = finish(uow, current)
    assert current.terminal and current.incomplete and current.status == "COMPLETADA"
    assert [e.eligible for e in current.executions] == [True, False, True]
    with pytest.raises(RunError), uow() as tx:
        tx.comparisons.select(current.comparison_id, execution.execution_id, current.version)
    with uow() as tx:
        wf = next(e for e in current.executions if e.method == "WF")
        assert tx.comparisons.select(current.comparison_id, wf.execution_id, current.version).selected_execution_id == wf.execution_id


@pytest.mark.parametrize("failure", [False, True])
def test_no_eligible_result_returns_orders_after_safe_finish(session_factory, comparison_setup, failure):
    actor, ids, uow = comparison_setup
    with session_factory() as s:
        s.get(Plancha, 5).cantidad = 0
        s.commit()
    current = accept(comparison_setup)
    for execution in current.executions:
        if failure:
            with uow() as tx:
                current = tx.comparisons.fail_execution(current.comparison_id, execution.execution_id, "EXECUTION_FAILED")
        else:
            current = save(uow, current, execution.method)
    with session_factory() as s:
        assert [s.get(Pedido, i).estado for i in ids] == ["EN_OPTIMIZACION"] * 2
    current = finish(uow, current)
    assert current.status == ("FALLIDA" if failure else "SIN_SOLUCION")
    with session_factory() as s:
        assert [s.get(Pedido, i).estado for i in ids] == ["PENDIENTE"] * 2


@pytest.mark.parametrize("alteration", ["method", "stock", "config", "quantity"])
def test_result_must_match_exact_method_and_frozen_input(comparison_setup, alteration):
    current = accept(comparison_setup)
    _, _, uow = comparison_setup
    original = current.problem
    if alteration == "stock":
        original = replace(original, groups=(replace(original.groups[0], stock_candidates=()),))
    elif alteration == "config":
        original = replace(original, config=replace(original.config, margin_mm=1))
    elif alteration == "quantity":
        original = replace(original, groups=(replace(original.groups[0], units=original.groups[0].units[:-1]),))
    result = (BestFitOptimizer if alteration == "method" else FirstFitOptimizer)().optimize(original)
    with pytest.raises(RunError), uow() as tx:
        tx.comparisons.save_result(current.comparison_id, current.executions[0].execution_id, result, ())
    with uow() as tx:
        assert tx.comparisons.get(current.comparison_id) == current


def test_release_is_versioned_keeps_history_and_allows_new_request(session_factory, comparison_setup):
    current = accept(comparison_setup)
    actor, ids, uow = comparison_setup
    with pytest.raises(RunError), uow() as tx:
        tx.comparisons.release(current.comparison_id, current.version, actor)
    for method in ENGINES:
        current = save(uow, current, method)
    current = finish(uow, current)
    with uow() as tx:
        released = tx.comparisons.release(current.comparison_id, current.version, actor)
    assert released.released and released.executions == current.executions
    assert accept(comparison_setup).comparison_id == current.comparison_id
    assert accept(comparison_setup, "comparison-test-0002").comparison_id != current.comparison_id
    with session_factory() as s:
        assert s.get(Plancha, 5).cantidad == 2


def test_invalid_and_commit_failure_leave_no_mutations(session_factory, comparison_setup):
    actor, ids, uow = comparison_setup
    def fail(session, flush_context, instances):
        if any(isinstance(o, Pedido) and o.estado == "EN_OPTIMIZACION" for o in session.dirty):
            raise RuntimeError("synthetic commit failure")
    event.listen(session_factory.class_, "before_flush", fail)
    try:
        with pytest.raises(RuntimeError):
            accept(comparison_setup)
    finally:
        event.remove(session_factory.class_, "before_flush", fail)
    with session_factory() as s:
        assert s.scalar(select(func.count()).select_from(Optimizacion)) == 0
        assert [s.get(Pedido, i).estado for i in ids] == ["PENDIENTE"] * 2


def test_large_stock_rejected_before_expansion_and_no_child_rows(session_factory, comparison_setup):
    with session_factory() as s:
        s.get(Plancha, 5).cantidad = 100000
        s.commit()
    with pytest.raises(RunError) as error:
        accept(comparison_setup)
    assert error.value.code == "LOAD_LIMIT_EXCEEDED"
    with session_factory() as s:
        assert s.scalar(select(func.count()).select_from(Optimizacion)) == 0


def test_save_failure_rolls_back_child_metrics_and_keeps_input(session_factory, comparison_setup):
    current = accept(comparison_setup)
    _, _, uow = comparison_setup
    def fail(session, flush_context, instances):
        if any(isinstance(o, MetricaEjecucion) for o in session.new):
            raise RuntimeError("synthetic metric failure")
    event.listen(session_factory.class_, "before_flush", fail)
    try:
        with pytest.raises(RuntimeError):
            save(uow, current, "BF")
    finally:
        event.remove(session_factory.class_, "before_flush", fail)
    with uow() as tx:
        assert tx.comparisons.get(current.comparison_id) == current


def test_concurrent_selections_use_compare_and_set(comparison_setup):
    current = accept(comparison_setup)
    _, _, uow = comparison_setup
    for method in ENGINES:
        current = save(uow, current, method)
    current = finish(uow, current)
    gate = Barrier(2)
    def choose(execution_id):
        gate.wait(timeout=5)
        try:
            with uow() as tx:
                return tx.comparisons.select(current.comparison_id, execution_id, current.version)
        except RunError as error:
            return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        choices = [pool.submit(choose, e.execution_id) for e in current.executions[1:]]
        results = [f.result(timeout=15) for f in choices]
    assert sum(r == "STATE_CONFLICT" for r in results if isinstance(r, str)) == 1
    selected = next(r for r in results if not isinstance(r, str))
    with uow() as tx:
        assert tx.comparisons.get(current.comparison_id) == selected


def test_foreign_execution_and_unmeasured_result_are_rejected(comparison_setup):
    actor, ids, uow = comparison_setup
    left = AcceptComparison(uow).execute(ids[:1], actor, "comparison-left-key")
    right = AcceptComparison(uow).execute(ids[1:], actor, "comparison-right-key")
    raw = FirstFitOptimizer().optimize(left.problem)
    with pytest.raises(RunError), uow() as tx:
        tx.comparisons.save_result(left.comparison_id, left.executions[0].execution_id, raw, ())
    for method in ENGINES:
        left = save(uow, left, method)
    left = finish(uow, left)
    with pytest.raises(RunError), uow() as tx:
        tx.comparisons.select(left.comparison_id, right.executions[0].execution_id, left.version)


def test_early_finish_cannot_release_orders(session_factory, comparison_setup):
    current = accept(comparison_setup)
    _, ids, uow = comparison_setup
    with pytest.raises(RunError):
        finish(uow, current)
    with session_factory() as s:
        assert [s.get(Pedido, i).estado for i in ids] == ["EN_OPTIMIZACION"] * 2


def test_released_run_cannot_modify_a_new_batch(comparison_setup):
    actor, _, uow = comparison_setup
    current = accept(comparison_setup)
    for method in ENGINES:
        current = save(uow, current, method)
    current = finish(uow, current)
    with uow() as tx:
        current = tx.comparisons.release(current.comparison_id, current.version, actor)
    new = accept(comparison_setup, "comparison-test-0002")
    with pytest.raises(RunError), uow() as tx:
        tx.comparisons.release(current.comparison_id, current.version, actor)
    with uow() as tx:
        assert tx.comparisons.get(new.comparison_id) == new
