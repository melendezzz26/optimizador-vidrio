"""T-02: v2 durable ownership and compatibility on real isolated PostgreSQL."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from functools import partial
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models import (Configuracion, EjecucionOptimizacion, MaterialUtilizado, MetricaEjecucion,
                        MovimientoInventario, Optimizacion, Pedido, Plancha)
from app.modules.optimization.application.comparison_catalog import CATALOG_V2, METHODS_V2
from app.modules.optimization.application.comparison_persistence_contracts import VisualReferenceV2
from app.modules.optimization.application.comparison_v2_contracts import (
    ComparisonInputV2, ExecutionDiagnostic, ExecutionPayloadV2,
)
from app.modules.optimization.application.comparisons import AcceptComparison
from app.modules.optimization.application.errors import RunError
from app.modules.optimization.application.load_budget import check_pieces, DEFAULT_RUN_LOAD_BUDGET
from app.modules.optimization.application.preparation import prepare_persisted_problem
from app.modules.optimization.infrastructure.comparison_v2_uow import SqlComparisonPersistenceUnitOfWork
from tests.unit.optimization.comparison_v2_support import calculated
from .test_runs import prepared  # noqa: F401


@pytest.fixture
def setup_v2(session_factory, prepared):
    assert session_factory.kw["bind"].url.host == "127.0.0.1"
    actor, ids, _ = prepared
    return actor, ids, partial(SqlComparisonPersistenceUnitOfWork, session_factory)


def frozen_input(setup, ids=None):
    _, all_ids, factory = setup
    ids = all_ids if ids is None else ids
    with factory() as tx:
        config_id, config = tx.configuration()
        pieces = tx.orders.lock_pending(ids)
        stock = tx.stock.capture(check_pieces(pieces, config, DEFAULT_RUN_LOAD_BUDGET))
        problem = prepare_persisted_problem(ids, pieces, config)
        problem = replace(problem, groups=tuple(replace(g, stock_candidates=stock[g.key]) for g in problem.groups))
        row = tx.session.get(Configuracion, config_id)
        return ComparisonInputV2(problem=problem, configuration_id=config_id, configuration_version=row.version,
            requested_pieces=pieces, minimum_width_mm=row.ancho_min_retazo_mm, minimum_height_mm=row.alto_min_retazo_mm)


def create(setup, key="b02-v2-request", ids=None):
    actor, _, factory = setup
    with factory() as tx:
        return tx.comparisons_v2.create(frozen_input(setup, ids), actor, key)


def save(setup, current, method, *, failed=False, partial_result=False, reason=None):
    factory = setup[2]
    execution = next(e for e in current.executions if e.method == method)
    if failed:
        payload = ExecutionPayloadV2(method=method, result=None, diagnostic=ExecutionDiagnostic(
            origin="SUPERVISOR", termination_reason="PROCESS_START_FAILED", statistics={}))
        residuals = ()
    else:
        for state in ("STARTING", "RUNNING"):
            with factory() as tx:
                current = tx.comparisons_v2.set_dispatch_state(current.comparison_id,
                    execution.execution_id, state, current.version)
        payload, residuals = calculated(next(d for d in CATALOG_V2 if d.code == method),
                                       current.problem, partial=partial_result)
        if reason is not None:
            payload = replace(payload, diagnostic=replace(payload.diagnostic, termination_reason=reason))
    with factory() as tx:
        return tx.comparisons_v2.save_execution(current.comparison_id, execution.execution_id,
                                               payload, residuals, current.version)


def test_create_six_owned_records_is_idempotent_read_only_for_inventory_and_orders(session_factory, setup_v2):
    actor, ids, factory = setup_v2
    current = create(setup_v2)
    assert current.methods == METHODS_V2 and tuple(e.method for e in current.executions) == METHODS_V2
    assert len({e.execution_id for e in current.executions}) == 6
    assert all(e.dispatch_state == "QUEUED" and e.result is None and e.diagnostic is None for e in current.executions)
    assert current.version == 1 and current.profile == "comparison-v2" and current.selected_execution_id is None
    assert create(setup_v2) == current
    with factory() as tx:
        assert tx.comparisons_v2.get_compatible(current.comparison_id) == current
        with pytest.raises(TypeError):
            current.requested_pieces[0]["cantidad"] = 99
    with session_factory() as s:
        assert s.scalar(select(func.count()).select_from(EjecucionOptimizacion)) == 6
        assert s.scalar(select(func.count()).select_from(MovimientoInventario)) == 0
        assert s.get(Plancha, 5).cantidad == 2
        assert [s.get(Pedido, i).estado for i in ids] == ["PENDIENTE", "PENDIENTE"]
        snapshot = s.get(Optimizacion, current.comparison_id).comparison_snapshot
        assert snapshot["comparison_snapshot_version"] == 2 and snapshot["methods"] == list(METHODS_V2)
        assert snapshot["input"]["input_version"] == 1
    with pytest.raises(RunError), factory() as tx:
        tx.comparisons.get(current.comparison_id)


def test_six_results_metrics_and_source_identities_survive_round_trip_without_consumption(session_factory, setup_v2):
    current = create(setup_v2)
    for method in reversed(METHODS_V2):
        current = save(setup_v2, current, method)
    assert all(e.result.complete and e.dispatch_state == "TERMINATED" for e in current.executions)
    assert not current.terminal  # Storage does not infer supervisor death from execution states.
    with setup_v2[2]() as tx:
        restored = tx.comparisons_v2.get(current.comparison_id)
        assert restored == current
        closed = tx.comparisons_v2.record_supervisor_stopped(current.comparison_id,
            datetime.now(timezone.utc), current.version)
    assert closed.supervisor_stopped and closed.terminal and closed.status == "COMPLETADA"
    with session_factory() as s:
        assert s.scalar(select(func.count()).select_from(MetricaEjecucion)) == 6
        assert s.scalar(select(func.count()).select_from(MaterialUtilizado)) == 6
        assert s.scalar(select(func.count()).select_from(MovimientoInventario)) == 0
        assert s.get(Plancha, 5).cantidad == 2
        for execution in s.scalars(select(EjecucionOptimizacion)):
            assert execution.patron_resultado["snapshot"]["snapshot_version"] == 3


@pytest.mark.parametrize("reason", ["EXPANSION_LIMIT", "GEOMETRY_PROBE_LIMIT", "STATE_MEMORY_LIMIT", "TIME_LIMIT"])
def test_partial_and_failed_diagnostics_persist_independently(setup_v2, reason):
    current = create(setup_v2)
    current = save(setup_v2, current, "M6-BS", partial_result=True, reason=reason)
    current = save(setup_v2, current, "HF", failed=True)
    with setup_v2[2]() as tx:
        restored = tx.comparisons_v2.get(current.comparison_id)
    beam = next(e for e in restored.executions if e.method == "M6-BS")
    hole = next(e for e in restored.executions if e.method == "HF")
    assert beam.outcome == "PARTIAL" and not beam.eligible and beam.diagnostic.termination_reason == reason
    assert hole.outcome == "FAILED" and hole.result is None and hole.failure_code == "PROCESS_START_FAILED"
    assert all(e.dispatch_state == "QUEUED" for e in restored.executions if e.method not in ("M6-BS", "HF"))


def test_visual_references_are_owned_metadata_not_shared_masks(setup_v2):
    current = create(setup_v2)
    left, right = current.executions[:2]
    ref = VisualReferenceV2(comparison_id=current.comparison_id, execution_id=left.execution_id,
                            method=left.method, mask_ref="a" * 32)
    with setup_v2[2]() as tx:
        current = tx.comparisons_v2.save_visual_references(current.comparison_id, left.execution_id, (ref,), current.version)
    with setup_v2[2]() as tx:
        assert tx.comparisons_v2.get_visual_reference(current.comparison_id, left.execution_id, ref.mask_ref) == ref
    with pytest.raises(RunError), setup_v2[2]() as tx:
        tx.comparisons_v2.save_visual_references(current.comparison_id, right.execution_id, (ref,), current.version)
    with pytest.raises(RunError), setup_v2[2]() as tx:
        tx.comparisons_v2.get_visual_reference(current.comparison_id, right.execution_id, ref.mask_ref)


@pytest.mark.parametrize("alteration", ["method", "snapshot_owner", "visual_owner", "completeness", "catalog", "input_hash"])
def test_corrupted_persistent_identities_are_rejected_not_reinterpreted(session_factory, setup_v2, alteration):
    current = create(setup_v2)
    if alteration == "completeness":
        current = save(setup_v2, current, "FF")
    with session_factory() as s:
        execution = s.get(EjecucionOptimizacion, current.executions[0].execution_id)
        data = deepcopy(execution.patron_resultado)
        if alteration == "method": data["method"] = "M5"
        if alteration == "snapshot_owner": data["comparison_id"] += 1
        if alteration == "visual_owner":
            data["visual_references"] = [VisualReferenceV2(comparison_id=current.comparison_id,
                execution_id=current.executions[1].execution_id, method="BF", mask_ref="b" * 32).record()]
        if alteration == "completeness": execution.completo = False
        if alteration in ("catalog", "input_hash"):
            row = s.get(Optimizacion, current.comparison_id)
            stored = deepcopy(row.comparison_snapshot)
            if alteration == "catalog": stored["methods"][0] = "BF"
            else: stored["input_sha256"] = "0" * 64
            row.comparison_snapshot = stored
        execution.patron_resultado = data
        s.commit()
    with pytest.raises(RunError, match="trazabilidad"), setup_v2[2]() as tx:
        tx.comparisons_v2.get(current.comparison_id)


def test_missing_execution_is_rejected(session_factory, setup_v2):
    current = create(setup_v2)
    with session_factory() as s:
        s.delete(s.get(EjecucionOptimizacion, current.executions[0].execution_id))
        s.commit()
    with pytest.raises(RunError), setup_v2[2]() as tx:
        tx.comparisons_v2.get(current.comparison_id)


def test_foreign_selection_and_early_stop_are_rejected(session_factory, setup_v2):
    left = create(setup_v2, "b02-select-left", setup_v2[1][:1])
    right = create(setup_v2, "b02-select-right", setup_v2[1][1:])
    with pytest.raises(RunError), setup_v2[2]() as tx:
        tx.comparisons_v2.record_supervisor_stopped(left.comparison_id, datetime.now(timezone.utc), left.version)
    with session_factory() as s:
        s.get(Optimizacion, left.comparison_id).id_ejecucion_seleccionada = right.executions[0].execution_id
        s.commit()  # FK alone permits this; the durable reader must enforce ownership.
    with pytest.raises(RunError, match="trazabilidad"), setup_v2[2]() as tx:
        tx.comparisons_v2.get(left.comparison_id)
    with setup_v2[2]() as tx:
        assert tx.comparisons_v2.get(right.comparison_id) == right


def test_mismatched_result_and_duplicate_visual_reference_roll_back(setup_v2):
    current = create(setup_v2)
    first = current.executions[0]
    payload, residuals = calculated(CATALOG_V2[1], current.problem)
    with pytest.raises(RunError), setup_v2[2]() as tx:
        tx.comparisons_v2.save_execution(current.comparison_id, first.execution_id, payload, residuals, current.version)
    reference = VisualReferenceV2(comparison_id=current.comparison_id, execution_id=first.execution_id,
        method=first.method, mask_ref="c" * 32)
    with pytest.raises(RunError), setup_v2[2]() as tx:
        tx.comparisons_v2.save_visual_references(current.comparison_id, first.execution_id,
            (reference, reference), current.version)
    with setup_v2[2]() as tx:
        assert tx.comparisons_v2.get(current.comparison_id) == current


@pytest.mark.parametrize("violation", ["unknown_method", "duplicate_method", "foreign_aggregate"])
def test_real_check_unique_and_foreign_key_constraints(session_factory, setup_v2, violation):
    current = create(setup_v2)
    with pytest.raises(IntegrityError), session_factory() as s:
        s.add(EjecucionOptimizacion(id_optimizacion=999999 if violation == "foreign_aggregate" else current.comparison_id,
            metodo="AUTO" if violation == "unknown_method" else "FF", estado="EN_EJECUCION",
            completo=False, fecha_inicio=datetime.now(timezone.utc)))
        s.commit()
    with setup_v2[2]() as tx:
        assert tx.comparisons_v2.get(current.comparison_id) == current


def test_cross_comparison_execution_and_stale_versions_do_not_mutate(setup_v2):
    left = create(setup_v2, "b02-left-key", setup_v2[1][:1])
    right = create(setup_v2, "b02-right-key", setup_v2[1][1:])
    with pytest.raises(RunError), setup_v2[2]() as tx:
        tx.comparisons_v2.set_dispatch_state(left.comparison_id, right.executions[0].execution_id, "STARTING", left.version)
    with setup_v2[2]() as tx:
        changed = tx.comparisons_v2.set_dispatch_state(left.comparison_id, left.executions[0].execution_id, "STARTING", left.version)
    with pytest.raises(RunError), setup_v2[2]() as tx:
        tx.comparisons_v2.set_dispatch_state(left.comparison_id, left.executions[1].execution_id, "STARTING", left.version)
    with setup_v2[2]() as tx:
        assert tx.comparisons_v2.get(left.comparison_id) == changed
        assert tx.comparisons_v2.get(right.comparison_id) == right


def test_input_and_key_are_frozen_without_reloading_stock(session_factory, setup_v2):
    current = create(setup_v2)
    with session_factory() as s:
        s.get(Plancha, 5).cantidad = 1
        s.scalar(select(Configuracion)).margen_mm = 1
        s.commit()
    with setup_v2[2]() as tx:
        assert tx.comparisons_v2.get(current.comparison_id).problem == current.problem
    with pytest.raises(RunError), setup_v2[2]() as tx:
        tx.comparisons_v2.create(frozen_input(setup_v2), setup_v2[0], "b02-v2-request")


def test_concurrent_creation_uses_one_owned_six_execution_set(setup_v2):
    value = frozen_input(setup_v2)
    gate = Barrier(2)
    def create_one():
        gate.wait(timeout=5)
        with setup_v2[2]() as tx:
            return tx.comparisons_v2.create(value, setup_v2[0], "b02-concurrent-key")
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(create_one) for _ in range(2)]
        left, right = [f.result(timeout=20) for f in futures]
    assert left == right and len(left.executions) == 6


def test_v1_key_and_reader_keep_original_three_execution_contract(setup_v2):
    actor, ids, factory = setup_v2
    historical = AcceptComparison(factory).execute(ids, actor, "b02-history-key")
    with factory() as tx:
        assert tx.comparisons_v2.get_compatible(historical.comparison_id) == historical
    with pytest.raises(RunError), factory() as tx:
        tx.comparisons_v2.get(historical.comparison_id)
    assert len(historical.executions) == 3
