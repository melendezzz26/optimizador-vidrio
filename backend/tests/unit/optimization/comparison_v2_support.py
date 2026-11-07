"""Reproduce the B01 shared contract example using six direct production engines.

Run from backend: python -m tests.unit.optimization.comparison_v2_support
Events/lifecycle are contract examples, not traces of a six-worker supervisor.
"""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from time import perf_counter_ns

from app.modules.optimization.application.comparison_catalog import CATALOG_V2, METHODS_V2
from app.modules.optimization.application.comparison_v2_contracts import ComparisonInputV2, ExecutionDiagnostic, ExecutionPayloadV2
from app.modules.optimization.infrastructure.comparison_v2_snapshot import encode_comparison_input_v2
from app.modules.optimization.domain.beam_search import BeamSearchLimits, BeamSearchOptimizer
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.infrastructure.comparison_snapshot import problem_fingerprint
from app.modules.optimization.infrastructure.run_snapshot import json_value
from app.modules.optimization.presentation.comparison_serialization import metrics_response
from app.modules.optimization.presentation.comparison_v2_serialization import result_response_v2
from app.modules.optimization.presentation.comparison_v2_schemas import (
    ComparisonSummaryV2, ComparisonEventV2, ExecutionResponseV2,
)
from app.modules.optimization.presentation.run_serialization import config_response
from tests.unit.optimization.test_comparison_snapshot import example

FIXTURE = Path(__file__).resolve().parents[4] / "docs/contracts/optimization/comparison-v2.json"


def calculated(definition, problem, *, partial=False):
    started = perf_counter_ns()
    optimizer = (BeamSearchOptimizer(BeamSearchLimits(max_expansions=1))
                 if partial else definition.optimizer_type())
    if definition.code == "M6-BS":
        outcome = optimizer.run(problem)
        result, reason, stats = outcome.result, outcome.stop_reason, outcome.statistics
    else:
        result, reason, stats = optimizer.optimize(problem), None, {}
    result, residuals = calculate_metrics(result, 1, 1)
    result = replace(result, computation_time_ms=max(0, (perf_counter_ns() - started) // 1_000_000))
    reason = reason or ("COMPLETED" if result.complete else "NO_FIT")
    return ExecutionPayloadV2(method=definition.code, result=result,
        diagnostic=ExecutionDiagnostic(origin="ENGINE", termination_reason=reason, statistics=stats)), residuals


def summary(payload, identifier, *, eligible):
    result = payload.result
    return dict(execution_id=identifier, method=payload.method, status="COMPLETADA",
        dispatch_state="TERMINATED", outcome="COMPLETE" if result.complete else "PARTIAL",
        result_available=True, complete=result.complete, eligible=eligible,
        placed_units=result.placed_units, total_units=result.total_units,
        metrics=metrics_response(result), computation_time_ms=result.computation_time_ms,
        diagnostic=payload.diagnostic.public())


def build_fixture():
    problem = example()
    completed = dict(profile="comparison-v2", schema_version=2, comparison_id=43, version=7,
        methods=list(METHODS_V2), input_sha256=problem_fingerprint(problem), order_ids=list(problem.order_ids),
        configuration=config_response(problem.config).model_dump(mode="json"),
        configuration_id=1, configuration_version=1,
        requested_pieces=[dict(id_pedido=problem.units[0].order_id, id_pieza=problem.units[0].piece_id,
            cantidad=len(problem.units), tipo_forma=problem.units[0].shape_type)], executions=[],
        selected_execution_id=None, terminal=True, supervisor_stopped=True, incomplete=False,
        released=False, confirmed=False, selection_allowed=True, confirmable=False, confirmation=None)
    results = {}
    for identifier, definition in enumerate(CATALOG_V2, 4301):
        payload, residuals = calculated(definition, problem)
        execution = summary(payload, identifier, eligible=True)
        completed["executions"].append(execution)
        results[str(identifier)] = dict(profile="comparison-v2", schema_version=2, comparison_id=43,
            execution=execution, result=result_response_v2(43, payload, residuals=residuals).model_dump(mode="json"))
    accepted = deepcopy(completed)
    accepted.update(version=1, status="EN_EJECUCION", terminal=False, supervisor_stopped=False, selection_allowed=False)
    completed["status"] = "COMPLETADA"
    for execution in accepted["executions"]:
        execution.update(status="EN_EJECUCION", dispatch_state="QUEUED", outcome=None, result_available=False,
                         complete=False, eligible=False, placed_units=0, metrics=None, computation_time_ms=None, diagnostic=None)
    mixed = deepcopy(completed)
    mixed["incomplete"] = True
    partial, residuals = calculated(CATALOG_V2[-1], problem, partial=True)
    mixed["executions"][-1] = summary(partial, 4306, eligible=False)
    failed = mixed["executions"][3]
    failed.update(status="FALLIDA", outcome="FAILED", result_available=False, complete=False, eligible=False,
        placed_units=0, metrics=None, computation_time_ms=None,
        diagnostic=dict(origin="SUPERVISOR", termination_reason="WORKER_STOPPED", statistics={}))
    partial_response = dict(profile="comparison-v2", schema_version=2, comparison_id=43,
        execution=mixed["executions"][-1], result=result_response_v2(43, partial, residuals=residuals).model_dump(mode="json"))
    failed_response = dict(profile="comparison-v2", schema_version=2, comparison_id=43, execution=failed, result=None)
    events = []
    execution_sequences = {}

    def event(kind, data, execution=None, presentation="OBSERVED"):
        if execution:
            code = execution["method"]
            execution_sequences[code] = execution_sequences.get(code, 0) + 1
        events.append(dict(profile="comparison-v2", schema_version=2, comparison_id=43,
            sequence=len(events) + 1, timestamp="2026-11-03T00:00:00Z", event=kind, data=data,
            execution_id=execution["execution_id"] if execution else None,
            method=execution["method"] if execution else None,
            execution_sequence=execution_sequences[execution["method"]] if execution else None,
            presentation=presentation if execution else None))

    event("comparison_accepted", dict(version=1, methods=list(METHODS_V2), executions=[
        {key: e[key] for key in ("execution_id", "method")} for e in accepted["executions"]]))
    event("search_progress", dict(completed_levels=0, processed_units=0, total_units=len(problem.units),
          expansions=0, geometry_probes=0, frontier_size=1), accepted["executions"][-1], "PROVISIONAL")
    for execution in completed["executions"]:
        event("result_persisted", execution, execution)
    event("comparison_finished", dict(version=7, status="COMPLETADA", incomplete=False, supervisor_stopped=True))
    for value in (accepted, completed, mixed):
        ComparisonSummaryV2.model_validate(value)
    for value in (*results.values(), partial_response, failed_response):
        ExecutionResponseV2.model_validate(value)
    for value in events:
        ComparisonEventV2.model_validate(value)
    return dict(provenance=dict(scope="B01 contract example; not public six-engine integration",
        results="six direct production engines; common immutable input; real calculation times",
        events="constructed examples, not a recorded supervisor stream",
        partial="real M6-BS with max_expansions=1; other Beam defaults preserved",
        failure="constructed contract example; no process was killed to create this fixture"),
        catalog=[m.public() for m in CATALOG_V2],
        input_snapshot=encode_comparison_input_v2(ComparisonInputV2(problem=problem,
            configuration_id=1, configuration_version=1, requested_pieces=completed["requested_pieces"],
            minimum_width_mm=1, minimum_height_mm=1)),
        accepted=accepted, completed=completed, mixed=mixed,
        results=results, partial_result=partial_response, failed_result=failed_response, events=events)


if __name__ == "__main__":
    FIXTURE.write_text(json.dumps(json_value(build_fixture()), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(FIXTURE.name + ": generated and validated")
