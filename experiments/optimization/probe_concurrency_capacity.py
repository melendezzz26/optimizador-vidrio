"""Sonda de determinismo y concurrencia multi-proceso del optimizador (TA-044 - T03).

Autor: Luis Anthony Ibáñez Herrera.
Revisor esperado: Andro Joseph Quispe Cesias.

1. Determinismo:
   - Ejecuta N=5 repeticiones independientes sobre cada caso y método determinista.
   - Genera huella digital SHA-256 de las colocaciones exactas (pieza, lámina, x, y, rotación).
   - Compara igualdad de las colocaciones observadas.

2. Concurrencia:
   - Ejecuta optimizaciones concurrentes con 2, 4 y 8 procesos simultáneos.
   - Evalúa aislamiento de memoria, tasa de éxito, contención de CPU y factor de degradación.
   - Compara huellas con una ejecución secuencial; no prueba el servicio ni fugas.
"""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.optimization.capacity_scenarios import CAPACITY_SCENARIOS, load_capacity_problem
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.best_fit import BestFitOptimizer
from app.modules.optimization.domain.worst_fit import WorstFitOptimizer
from app.modules.optimization.domain.hole_filling import HoleFillingOptimizer
from app.modules.optimization.domain.best_residual_fit import BestResidualFitOptimizer
from app.modules.optimization.domain.beam_search import BeamSearchOptimizer

EVIDENCE_DIR = ROOT / "docs" / "evidence" / "sprint-02" / "TA-044"


def compute_placement_fingerprint(result) -> str:
    """Calcula un hash SHA-256 canónico de las asignaciones de piezas."""
    items = []
    for p in result.placements:
        items.append({
            "piece_id": p.piece.piece_id,
            "unit_index": p.piece.unit_index,
            "stock_source": p.stock.source.value,
            "stock_id": p.stock.material_id,
            "physical_unit": p.stock.physical_unit_index,
            "x_mm": str(p.x_mm),
            "y_mm": str(p.y_mm),
            "rotation_deg": str(p.rotation_deg),
        })
    # Ordenar por identidad de pieza para invariante de orden
    items.sort(key=lambda x: (x["piece_id"], x["unit_index"]))
    serialized = json.dumps(items, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


# --- 1. EVALUACIÓN DE DETERMINISMO ---

def run_determinism_test(repetitions: int = 5, scales=(10,)) -> list[dict]:
    print("\n" + "=" * 78)
    print(f"1. INICIANDO VERIFICACIÓN DE DETERMINISMO FUNCIONAL (N={repetitions} repeticiones)")
    print("=" * 78)

    methods = [
        ("FF", FirstFitOptimizer),
        ("BF", BestFitOptimizer),
        ("WF", WorstFitOptimizer),
        ("M4", HoleFillingOptimizer),
        ("M5", BestResidualFitOptimizer),
        ("M6", BeamSearchOptimizer),
    ]

    results = []
    for scale in scales:
        problem = load_capacity_problem(scale)
        for code, factory in methods:
            hashes = []
            times = []
            for rep in range(repetitions):
                t0 = time.perf_counter_ns()
                opt = factory()
                res = opt.optimize(problem)
                dt_ms = (time.perf_counter_ns() - t0) / 1_000_000
                times.append(dt_ms)
                hashes.append(compute_placement_fingerprint(res))

            unique_hashes = set(hashes)
            is_deterministic = len(unique_hashes) == 1
            avg_time = round(sum(times) / len(times), 2)
            time_std = round((sum((t - avg_time) ** 2 for t in times) / len(times)) ** 0.5, 2)

            rec = {
                "scale_n": scale,
                "case_id": f"CAP-{scale}",
                "method": code,
                "repetitions": repetitions,
                "is_deterministic": is_deterministic,
                "unique_hashes_count": len(unique_hashes),
                "fingerprint": hashes[0],
                "avg_time_ms": avg_time,
                "time_std_ms": time_std,
            }
            results.append(rec)
            status_txt = "DETERMINISTA (PASS)" if is_deterministic else "NO DETERMINISTA (FAIL)"
            print(f"  CAP-{scale:3d} | {code:2s} -> {status_txt} | Hash: {hashes[0][:16]}... | Tiempo: {avg_time} ± {time_std} ms")

    return results


# --- 2. EVALUACIÓN DE CONCURRENCIA ---

def _worker_optimize(args):
    """Tarea ejecutada en proceso worker aislado."""
    worker_id, scale_n, method_code = args
    t0 = time.perf_counter_ns()
    try:
        problem = load_capacity_problem(scale_n)
        if method_code == "FF":
            opt = FirstFitOptimizer()
        elif method_code == "M5":
            opt = BestResidualFitOptimizer()
        else:
            opt = FirstFitOptimizer()
        res = opt.optimize(problem)
        dt_ms = (time.perf_counter_ns() - t0) / 1_000_000
        fp = compute_placement_fingerprint(res)
        return {
            "worker_id": worker_id,
            "success": True,
            "execution_time_ms": round(dt_ms, 2),
            "placed_units": res.placed_units,
            "total_units": res.total_units,
            "fingerprint": fp,
            "error": None,
        }
    except Exception as exc:
        dt_ms = (time.perf_counter_ns() - t0) / 1_000_000
        return {
            "worker_id": worker_id,
            "success": False,
            "execution_time_ms": round(dt_ms, 2),
            "placed_units": 0,
            "total_units": scale_n,
            "fingerprint": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def run_concurrency_test() -> list[dict]:
    print("\n" + "=" * 78)
    print("2. INICIANDO PRUEBAS DE CONCURRENCIA Y SATURACIÓN MULTI-PROCESO")
    print(f"CPUs lógicos disponibles en host: {mp.cpu_count()}")
    print("=" * 78)

    concurrency_levels = [2, 4, 8]
    test_cases = [
        (25, "FF"),
        (25, "M5"),
        (50, "FF"),
        (50, "M5"),
    ]

    concurrency_results = []

    for scale, method in test_cases:
        # Primero medir línea base secuencial (1 worker aislado)
        seq_res = _worker_optimize((0, scale, method))
        baseline_time = seq_res["execution_time_ms"]
        baseline_fp = seq_res["fingerprint"]

        for workers in concurrency_levels:
            tasks = [(i, scale, method) for i in range(workers)]
            t_start = time.perf_counter_ns()

            with mp.Pool(processes=workers) as pool:
                task_outputs = pool.map(_worker_optimize, tasks)

            t_end = time.perf_counter_ns()
            total_wall_ms = round((t_end - t_start) / 1_000_000, 2)

            all_success = all(t["success"] for t in task_outputs)
            all_match_fp = all(t["fingerprint"] == baseline_fp for t in task_outputs)
            avg_worker_ms = round(sum(t["execution_time_ms"] for t in task_outputs) / len(task_outputs), 2)
            slowdown_factor = round(avg_worker_ms / baseline_time, 2) if baseline_time > 0 else 1.0
            throughput_ops_sec = round(workers / (total_wall_ms / 1000), 2) if total_wall_ms > 0 else 0.0

            record = {
                "scale_n": scale,
                "case_id": f"CAP-{scale}",
                "method": method,
                "concurrency_workers": workers,
                "all_success": all_success,
                "fingerprints_match_baseline": all_match_fp,
                "total_wall_time_ms": total_wall_ms,
                "baseline_single_ms": baseline_time,
                "avg_worker_time_ms": avg_worker_ms,
                "slowdown_factor": slowdown_factor,
                "throughput_ops_sec": throughput_ops_sec,
                "worker_outputs": task_outputs,
            }
            concurrency_results.append(record)

            status_str = "SUCCESS" if (all_success and all_match_fp) else "FAIL/MISMATCH"
            print(f"  CAP-{scale} | {method} | Concurrencia={workers} -> {status_str} | Wall: {total_wall_ms} ms | Avg/worker: {avg_worker_ms} ms (Slowdown: {slowdown_factor}x) | {throughput_ops_sec} ops/s")

    return concurrency_results


def run_full_determinism_and_concurrency(output_dir: Path | None = None):
    target_dir = output_dir or EVIDENCE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    det_results = run_determinism_test(repetitions=5)
    conc_results = run_concurrency_test()

    consolidated = {
        "metadata": {
            "date": "04/11/2026",
            "cpu_count": mp.cpu_count(),
            "python_version": sys.version,
            "platform": sys.platform,
        },
        "determinism_results": det_results,
        "concurrency_results": conc_results,
    }

    out_file = target_dir / "concurrency_results.json"
    out_file.write_text(json.dumps(consolidated, indent=2), encoding="utf-8")
    print("\n" + "=" * 78)
    print("Sondas de determinismo y paralelismo terminadas; revisar resultados")
    print(f"Resultados guardados en: {out_file}")
    print("=" * 78)


if __name__ == "__main__":
    mp.freeze_support()
    run_full_determinism_and_concurrency()
