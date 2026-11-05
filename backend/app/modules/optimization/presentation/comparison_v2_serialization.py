"""Pure B01 model-to-wire projection, not a persistence or execution adapter."""
from ..application.dto import OptimizationRun, RunStatus
from ..application.comparison_v2_contracts import ExecutionPayloadV2
from .comparison_v2_schemas import ComparisonResultV2, ComparisonSummaryV2, ExecutionSummaryV2, ExecutionResponseV2
from .run_serialization import run_response_values
from .comparison_serialization import metrics_response, plain
from .run_serialization import config_response


def execution_summary_v2(current, execution):
    result = execution.result
    return ExecutionSummaryV2(execution_id=execution.execution_id, method=execution.method,
        status=execution.status, dispatch_state=execution.dispatch_state, outcome=execution.outcome,
        result_available=result is not None, complete=bool(result and result.complete),
        eligible=execution.eligible and current.terminal and not current.released and current.confirmation is None,
        placed_units=result.placed_units if result else 0, total_units=len(current.problem.units),
        metrics=metrics_response(result), computation_time_ms=result.computation_time_ms if result else None,
        diagnostic=execution.diagnostic.public() if execution.diagnostic else None)


def comparison_response_v2(current):
    executions = [execution_summary_v2(current,e) for e in current.executions]
    selected = next((e for e in executions if e.execution_id==current.selected_execution_id),None)
    return ComparisonSummaryV2(comparison_id=current.comparison_id, version=current.version,status=current.status,
        input_sha256=current.input_sha256,order_ids=list(current.problem.order_ids),
        configuration=config_response(current.problem.config),configuration_id=current.configuration_id,
        configuration_version=current.configuration_version,requested_pieces=plain(current.requested_pieces),
        methods=list(current.methods),executions=executions,selected_execution_id=current.selected_execution_id,
        terminal=current.terminal,incomplete=current.incomplete,released=current.released,
        confirmed=current.confirmation is not None,confirmation=plain(current.confirmation),
        selection_allowed=any(e.eligible for e in executions),confirmable=bool(selected and selected.eligible),
        supervisor_stopped=current.supervisor_stopped)


def execution_response_v2(current, execution):
    payload = ExecutionPayloadV2(method=execution.method,result=execution.result,diagnostic=execution.diagnostic) if execution.result else None
    return ExecutionResponseV2(comparison_id=current.comparison_id,execution=execution_summary_v2(current,execution),
        result=result_response_v2(current.comparison_id,payload,residuals=execution.residuals) if payload else None)


def result_response_v2(comparison_id: int, payload: ExecutionPayloadV2, *, residuals=()):
    if payload.result is None or payload.diagnostic is None:
        raise ValueError("A V2 layout requires a result and captured diagnostic")
    result = payload.result
    run = OptimizationRun(optimization_id=comparison_id,
        status=RunStatus.COMPLETED if result.complete else RunStatus.NO_SOLUTION,
        result=result, residuals=residuals)
    values = run_response_values(run, include_stock_compatibility=True)
    reason = payload.diagnostic.termination_reason
    values.update(schema_version=2, termination_reason=reason)
    for unit in values["unplaced_units"]:
        unit["reason"] = "NO_FIT" if reason == "NO_FIT" else "RESOURCE_LIMIT"
    return ComparisonResultV2.model_validate(values)
