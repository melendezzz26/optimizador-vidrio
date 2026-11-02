"""Proyección comparativa. Autor: Fabricio Melendez Quezada. Revisor: Andro Quispe."""
from collections.abc import Mapping
from decimal import Decimal
from ..application.dto import OptimizationRun, RunStatus
from .comparison_schemas import ComparisonSummary, ExecutionSummary, ExecutionResponse, ComparisonResult
from .run_serialization import config_response, run_response_values


def plain(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, Mapping):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if isinstance(value, Decimal):
        return str(value)
    return value


def metrics_response(result):
    if result is None or result.metrics is None:
        return None
    m = result.metrics
    return dict(aprovechamiento_pct=m.utilization_pct, merma_mm2=m.waste_mm2,
        planchas_nuevas_usadas=m.new_sheets_used, retazo_recuperable_mm2=m.recoverable_remnant_mm2,
        area_material_total_mm2=m.material_area_mm2, area_piezas_colocadas_mm2=m.placed_piece_area_mm2,
        tiempo_computacional_ms=result.computation_time_ms)


def execution_summary(current, execution):
    result = execution.result
    return ExecutionSummary(execution_id=execution.execution_id, method=execution.method, status=execution.status,
        complete=result.complete if result else False,
        eligible=execution.eligible and current.terminal and not current.released and current.confirmation is None,
        placed_units=result.placed_units if result else 0, total_units=len(current.problem.units),
        metrics=metrics_response(result), computation_time_ms=result.computation_time_ms if result else None,
        failure_code=execution.failure_code)


def comparison_response(current):
    editable = current.terminal and not current.released and current.confirmation is None
    selected = next((e for e in current.executions if e.execution_id == current.selected_execution_id), None)
    confirmation = None if current.confirmation is None else {
        k: current.confirmation[k] for k in ("execution_id", "method", "actor_id", "confirmed_at")}
    return ComparisonSummary(comparison_id=current.comparison_id, version=current.version, status=current.status,
        input_sha256=current.input_sha256, order_ids=list(current.problem.order_ids),
        configuration=config_response(current.problem.config), configuration_id=current.configuration_id,
        configuration_version=current.configuration_version, requested_pieces=plain(current.requested_pieces),
        executions=[execution_summary(current, e) for e in current.executions],
        selected_execution_id=current.selected_execution_id, terminal=current.terminal, incomplete=current.incomplete,
        released=current.released, confirmed=current.confirmation is not None,
        selection_allowed=editable and any(e.eligible for e in current.executions),
        confirmable=editable and selected is not None and selected.eligible, confirmation=confirmation)


def execution_response(current, execution):
    result = None
    if execution.result is not None:
        run = OptimizationRun(optimization_id=current.comparison_id,
            status=RunStatus.COMPLETED if execution.result.complete else RunStatus.NO_SOLUTION,
            result=execution.result, residuals=execution.residuals)
        result = ComparisonResult(**run_response_values(run, include_stock_compatibility=True))
    return ExecutionResponse(comparison_id=current.comparison_id, execution=execution_summary(current, execution), result=result)
