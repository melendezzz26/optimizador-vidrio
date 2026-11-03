"""Pure B01 model-to-wire projection, not a persistence or execution adapter."""
from ..application.dto import OptimizationRun, RunStatus
from ..application.comparison_v2_contracts import ExecutionPayloadV2
from .comparison_v2_schemas import ComparisonResultV2
from .run_serialization import run_response_values


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
