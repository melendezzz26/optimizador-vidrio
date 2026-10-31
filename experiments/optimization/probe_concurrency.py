"""T00: sonda reproducible de tres motores con spawn y entrada JSON común.

Autor: Fabricio Melendez Quezada.
Revisor asignado: Andro Quispe.

Desde la raíz, con el Python del backend:
    python experiments/optimization/probe_concurrency.py

Solo usa casos sintéticos congelados, sin DB ni servicios. La barrera dentro
del primer hecho real demuestra solapamiento de las llamadas al optimizador;
los tiempos incluyen esa instrumentación y NO permiten ordenar los motores.
Esta sonda no implementa la API, la supervisión productiva ni sus límites.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import platform
from queue import Empty
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from experiments.optimization.loader import CASES, load_problem, read_case  # noqa: E402
from app.modules.optimization.domain.first_fit import FirstFitOptimizer  # noqa: E402
from app.modules.optimization.domain.best_fit import BestFitOptimizer  # noqa: E402
from app.modules.optimization.domain.worst_fit import WorstFitOptimizer  # noqa: E402
from app.modules.optimization.domain.metrics import calculate_metrics  # noqa: E402
from app.modules.optimization.domain.problem import OptimizationResult  # noqa: E402
from app.modules.optimization.infrastructure.run_snapshot import decode, encode, json_value  # noqa: E402

METHODS = {"FF": FirstFitOptimizer, "BF": BestFitOptimizer, "WF": WorstFitOptimizer}


def digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def peak_rss_bytes():
    try:
        import resource
        maximum = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return maximum if sys.platform == "darwin" else maximum * 1024
    except ImportError:
        return None


def fingerprint(result, residuals):
    # La identidad se incorpora explícitamente. No guardar un resultado BF/WF
    # con el snapshot V1 FF: aquí V1 solo transporta el problema de entrada.
    return digest({"method": result.method, "result": json_value(result),
                   "residuals": json_value(residuals)})


def worker(method, payload, minimums, start, entered, output):
    try:
        problem = decode(json.loads(payload)).problem
        received_hash = digest(json_value(problem))
        start.wait(timeout=30)
        started = time.monotonic_ns()
        cpu_started = time.process_time_ns()
        facts = Counter()

        def observe(fact):
            facts[fact.kind] += 1
            if fact.kind == "preparation_started":
                entered.wait(timeout=30)

        result = METHODS[method]().optimize(problem, on_visual=observe)
        result, residuals = calculate_metrics(result, *minimums)
        ended = time.monotonic_ns()
        assert result.method == method
        output.put({"ok": True, "method": method, "pid": os.getpid(),
            "input_sha256": received_hash, "started_ns": started, "ended_ns": ended,
            "instrumented_elapsed_ms": (ended - started) / 1_000_000,
            "cpu_ms": (time.process_time_ns() - cpu_started) / 1_000_000,
            "peak_rss_bytes": peak_rss_bytes(), "visual_facts": dict(facts),
            "total_units": result.total_units, "placed_units": result.placed_units,
            "functional_sha256": fingerprint(result, residuals)})
    except BaseException as error:
        output.put({"ok": False, "method": method, "error": type(error).__name__})
        traceback.print_exc()


def probe(case_id):
    problem = load_problem(case_id)
    input_hash = digest(json_value(problem))
    frozen = read_case(case_id)
    minimums = (frozen["residual_limits"]["minimum_width_mm"],
                frozen["residual_limits"]["minimum_height_mm"])
    # Sin clases ORM, conexiones ni MappingProxyType en los argumentos spawn.
    payload = json.dumps(encode(OptimizationResult(problem=problem, placements=())), allow_nan=False)
    context = mp.get_context("spawn")
    start, entered, output = context.Barrier(4), context.Barrier(3), context.Queue(maxsize=3)
    processes = [context.Process(target=worker, args=(method, payload, minimums, start, entered, output))
                 for method in METHODS]
    reports = []
    try:
        for process in processes:
            process.start()
        start.wait(timeout=30)
        for _ in processes:
            try:
                reports.append(output.get(timeout=150))
            except Empty as error:
                raise RuntimeError("La sonda excedió el tiempo de espera de sus workers.") from error
        for process in processes:
            process.join(timeout=10)
        assert all(p.exitcode == 0 for p in processes), "Worker sin terminar correctamente"
        assert all(report["ok"] for report in reports), reports
        assert len({report["pid"] for report in reports}) == 3
        assert {report["method"] for report in reports} == set(METHODS)
        assert all(report["input_sha256"] == input_hash for report in reports)
        overlap = min(r["ended_ns"] for r in reports) - max(r["started_ns"] for r in reports)
        assert overlap > 0, "No se demostró solapamiento de las tres llamadas"
        for report in reports:
            result = METHODS[report["method"]]().optimize(load_problem(case_id))
            result, residuals = calculate_metrics(result, *minimums)
            assert report["functional_sha256"] == fingerprint(result, residuals)
        assert digest(json_value(problem)) == input_hash, "La entrada original cambió"
        return {"case_id": case_id, "input_sha256": input_hash,
            "common_overlap_ms": overlap / 1_000_000,
            "all_methods_match_direct_execution": True,
            "sum_worker_peak_rss_bytes": sum(r["peak_rss_bytes"] for r in reports)
                if all(r["peak_rss_bytes"] is not None for r in reports) else None,
            "workers": sorted(reports, key=lambda r: tuple(METHODS).index(r["method"]))}
    finally:
        # No se deja capacidad ni procesos vivos tras un fallo de la sonda.
        for process in processes:
            if process.is_alive():
                process.terminate()
            if process.pid is not None:
                process.join(timeout=10)
        output.close()
        output.join_thread()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", nargs="+", choices=CASES, default=list(CASES))
    args = parser.parse_args()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    result = {"schema_version": 1, "author": "Fabricio Melendez Quezada",
        "assigned_reviewer": "Andro Quispe", "source_commit": commit,
        "python": platform.python_version(), "platform": platform.system(),
        "start_method": "spawn", "probe_only": True,
        "measurement_notes": [
            "Barrera instrumentada dentro del primer hecho real; tiempos no aptos para ranking.",
            "La suma de máximos RSS de workers no es un pico agregado simultáneo medido.",
            "Casos congelados pequeños: no certifica el peor caso ni capacidad de producción.",
            "No implementa streaming/API productivos ni aplica escrituras de inventario."],
        "cases": [probe(case_id) for case_id in args.cases]}
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
