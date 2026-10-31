"""Fixture compartida de serialización con motores reales, sin DB ni ranking.

Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
La captura secuencial solo fija ejemplos del contrato; no prueba concurrencia.
"""
from dataclasses import replace
from decimal import Decimal
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT)]
from experiments.optimization.loader import load_problem, read_case
from app.modules.optimization.application.comparison_contracts import Comparison, ComparisonExecution, ComparisonSignal
from app.modules.optimization.application.comparison_limits import ComparisonBudget
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.infrastructure.comparison_runner import ENGINES
from app.modules.optimization.infrastructure.comparison_snapshot import problem_fingerprint
from app.modules.optimization.infrastructure.run_snapshot import json_value
from app.modules.optimization.application.visual import mask_window
from app.modules.optimization.presentation.comparison_runtime import ComparisonJob
from app.modules.optimization.presentation.comparison_serialization import comparison_response, execution_response
from app.modules.optimization.presentation.comparison_schemas import ComparisonMaskPayload
from app.modules.optimization.presentation.visual_serialization import describe_record


def main():
    problem = load_problem("EXP-SMALL-001")
    requested = [dict(p, dimensiones=None, area_mm2=str(problem.units[0].area_mm2), material_nombre="Material sintético")
                 for p in read_case("EXP-SMALL-001")["pieces"]]
    initial = Comparison(comparison_id=1, version=1, status="EN_EJECUCION", actor_id=1, input_sha256=problem_fingerprint(problem),
        problem=problem, requested_pieces=tuple(requested), configuration_id=1, configuration_version=1,
        minimum_width_mm=Decimal(1), minimum_height_mm=Decimal(1),
        executions=tuple(ComparisonExecution(execution_id=i, method=m, status="EN_EJECUCION") for i, m in enumerate(ENGINES, 1)))
    job, finished = ComparisonJob(ComparisonBudget()), []
    job.bind(initial)
    for execution in initial.executions:
        def observed(kind, payload):
            job.accept(ComparisonSignal(comparison_id=1, execution_id=execution.execution_id,
                method=execution.method, kind=kind, payload=payload))
        result = ENGINES[execution.method]().optimize(problem, lambda f: observed("milestone", json_value(f)),
            on_visual=lambda f: observed("visual", f))
        result, residuals = calculate_metrics(result, 1, 1)
        done = replace(execution, status="COMPLETADA", result=replace(result, computation_time_ms=17), residuals=residuals)
        finished.append(done)
        observed("result_persisted", done)
    complete = replace(initial, executions=tuple(finished), version=5, status="COMPLETADA", workers_stopped=True)
    job.accept(ComparisonSignal(comparison_id=1, execution_id=None, method=None, kind="comparison_finished", payload=complete))
    job.finish()
    manifests, masks = {}, {}
    for execution in finished:
        manifests[str(execution.execution_id)] = job.manifest(execution.execution_id, 0)
        _, session = job.session(execution.execution_id)
        for record in session.records.values():
            window = mask_window(record)
            spans = window.pop("spans_by_row")
            mask = ComparisonMaskPayload(**job.descriptor(execution.method, describe_record(session, record)),
                geometria_original=dict(record.owner.geometry), geometria=dict(record.orientation.geometry),
                window=window, spans_by_row=spans)
            masks[record.reference] = mask.model_dump(mode="json")
    print(json.dumps(dict(accepted=comparison_response(initial).model_dump(mode="json"),
        completed=comparison_response(complete).model_dump(mode="json"),
        results={str(e.execution_id): execution_response(complete, e).model_dump(mode="json") for e in finished},
        events=[json.loads(raw) for _, raw in job.records], manifests=manifests, masks=masks), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
