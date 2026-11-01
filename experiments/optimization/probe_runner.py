"""T00/T02: medir el runner incorporado, sin API, DB ni retención visual web.

Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
No ranking: el tiempo global incluye IPC, supervisión y cierre de procesos.
"""
from collections import Counter
from dataclasses import replace
from decimal import Decimal
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from experiments.optimization.loader import CASES, build_problem, read_case  # noqa: E402
from experiments.optimization.resource_cases import RESOURCE_CASES, read_resource_case  # noqa: E402
from app.modules.optimization.domain.metrics import calculate_metrics  # noqa: E402
from app.modules.optimization.infrastructure.comparison_runner import ComparisonProcessRunner, ENGINES  # noqa: E402
from app.modules.optimization.infrastructure.comparison_snapshot import problem_fingerprint  # noqa: E402
from app.modules.optimization.infrastructure.run_snapshot import json_value  # noqa: E402


def probe(case_id):
    data = read_resource_case(case_id) if case_id in RESOURCE_CASES else read_case(case_id)
    problem = build_problem(data)
    minimums = tuple(Decimal(str(data["residual_limits"][k])) for k in ("minimum_width_mm", "minimum_height_mm"))
    service, counts, results, ready, ordering = ComparisonProcessRunner(), Counter(), {}, [], set()
    for packet in service.calculate(problem, minimums):
        method, kind, payload = packet["method"], packet["kind"], packet["payload"]
        counts[(method, kind)] += 1
        if kind == "failed":
            raise RuntimeError(f"{case_id}/{method}: {payload['code']}")
        if kind == "ready":
            ready.append(payload)
        elif kind == "visual" and payload.kind == "ordering_ready":
            assert payload.ordered_units == problem.units
            ordering.add(method)
        elif kind == "result":
            results[method] = payload
    assert set(results) == ordering == set(ENGINES)
    assert len(ready) == len({r["pid"] for r in ready}) == 3
    assert {r["input_sha256"] for r in ready} == {problem_fingerprint(problem)}
    for method, actual in results.items():
        direct, residuals = calculate_metrics(ENGINES[method]().optimize(problem), *minimums)
        assert replace(actual.result, computation_time_ms=None) == direct
        assert actual.residuals == residuals
    return dict(case_id=case_id, total_units=len(problem.units), input_sha256=problem_fingerprint(problem),
        all_methods_match_direct_execution=True, all_ordering_facts_match=True,
        runner_measurements=service.last_report,
        packet_counts={method: {kind: number for (m, kind), number in counts.items() if m == method} for method in ENGINES})


def main():
    report = dict(schema_version=1, author="Fabricio Melendez Quezada", assigned_reviewer="Andro Quispe",
        source_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        source_tree_dirty=bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()),
        python=platform.python_version(), platform=platform.system(),
        budget=json_value(ComparisonProcessRunner().budget),
        limitations=["No incluye servidor web ni retención visual de producto.",
            "RSS muestreado con reserva auxiliar; puede omitir picos y duplicar páginas compartidas.",
            "Límites ejercitados por separado; no se certifica el peor caso ni el despliegue.",
            "La barrera de entrada común es operativa; la prueba de solapamiento interno tiene instrumentación adicional."],
        cases=[probe(case_id) for case_id in (*CASES, *RESOURCE_CASES)])
    print(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
