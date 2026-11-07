"""B03 -> B01 codecs/B02 repository, real isolated PostgreSQL; no v2 coordinator."""
from sqlalchemy import func, select
import pytest

from app.models import MovimientoInventario, Plancha
from app.modules.optimization.application.engine_execution import EngineExecutionAdapter, ExecutionScope
from app.modules.optimization.application.errors import ExecutionInterrupted
from app.modules.optimization.domain.beam_search import BeamSearchLimits
from .test_comparison_v2_persistence import setup_v2, create  # noqa: F401
from .test_runs import prepared  # noqa: F401


def persist(factory, current, execution, adapted):
    with factory() as tx:
        return tx.comparisons_v2.save_execution(current.comparison_id, execution.execution_id,
            adapted.payload, adapted.residuals, current.version)


def test_six_adapters_persist_owned_results_without_inventory_effects(session_factory, setup_v2):
    current = create(setup_v2, "b03-six-direct")
    for execution in current.executions:
        for state in ("STARTING", "RUNNING"):
            with setup_v2[2]() as tx:
                current = tx.comparisons_v2.set_dispatch_state(current.comparison_id,
                    execution.execution_id, state, current.version)
        adapted = EngineExecutionAdapter(execution.method).execute(ExecutionScope(
            comparison_id=current.comparison_id, execution_id=execution.execution_id, method=execution.method),
            current.problem, minimum_width_mm=current.minimum_width_mm, minimum_height_mm=current.minimum_height_mm)
        assert adapted.error_type is None
        current = persist(setup_v2[2], current, execution, adapted)
        restored = next(e for e in current.executions if e.execution_id == execution.execution_id)
        assert restored.result == adapted.payload.result and restored.diagnostic == adapted.payload.diagnostic
        assert restored.residuals == adapted.residuals and restored.outcome == "COMPLETE"
    assert not current.supervisor_stopped  # B03 cannot certify process shutdown or enable selection.
    with session_factory() as session:
        assert session.get(Plancha, 5).cantidad == 2
        assert session.scalar(select(func.count()).select_from(MovimientoInventario)) == 0


@pytest.mark.parametrize("limits,reason", [(BeamSearchLimits(max_expansions=1, complete_on_stop=False), "EXPANSION_LIMIT"),
    (BeamSearchLimits(max_geometry_probes=1, complete_on_stop=False), "GEOMETRY_PROBE_LIMIT"),
    (BeamSearchLimits(max_state_bytes=1, complete_on_stop=False), "STATE_MEMORY_LIMIT"),
    (BeamSearchLimits(seconds=0.000000001, complete_on_stop=False), "TIME_LIMIT")])
def test_actual_m6_exhaustion_is_durable_and_distinct_from_no_fit(setup_v2, limits, reason):
    current = create(setup_v2, "b03-beam-partial")
    execution = current.executions[-1]
    for state in ("STARTING", "RUNNING"):
        with setup_v2[2]() as tx:
            current = tx.comparisons_v2.set_dispatch_state(current.comparison_id,
                execution.execution_id, state, current.version)
    adapted = EngineExecutionAdapter("M6-BS", beam_limits=limits).execute(ExecutionScope(
        comparison_id=current.comparison_id, execution_id=execution.execution_id, method="M6-BS"), current.problem, minimum_width_mm=current.minimum_width_mm, minimum_height_mm=current.minimum_height_mm)
    restored = persist(setup_v2[2], current, execution, adapted).executions[-1]
    assert restored.outcome == "PARTIAL" and restored.diagnostic.termination_reason == reason
    assert restored.result == adapted.payload.result and restored.diagnostic == adapted.payload.diagnostic


def test_cancelled_adapter_does_not_invent_a_durable_result(setup_v2):
    current = create(setup_v2, "b03-interrupted")
    execution = current.executions[0]
    def cancel():
        raise ExecutionInterrupted()
    adapted = EngineExecutionAdapter("FF").execute(ExecutionScope(comparison_id=current.comparison_id,
        execution_id=execution.execution_id, method="FF"), current.problem, minimum_width_mm=current.minimum_width_mm, minimum_height_mm=current.minimum_height_mm, checkpoint=cancel)
    restored = persist(setup_v2[2], current, execution, adapted).executions[0]
    assert restored.outcome == "FAILED" and restored.result is None
    assert restored.diagnostic.termination_reason == "CANCELLED"
