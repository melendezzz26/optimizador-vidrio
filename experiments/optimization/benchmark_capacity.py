"""Runner formal de pruebas de capacidad, estrés y límites del optimizador (TA-044 - T02).

Autor: Luis Anthony Ibáñez Herrera.
Revisión: Andro Joseph Quispe Cesias / Wilder Fabricio Melendez Quezada.

Ejecuta la matriz progresiva de capacidad (10, 25, 50, 75, 100 piezas) sobre los
métodos disponibles (FF, BF, WF, M4, M5, M6), midiendo de forma reproducible:
- Tiempo de ejecución monotónico (ms)
- Memoria pico utilizada (KB y MB)
- Piezas solicitadas vs. colocadas
- Planchas nuevas consumidas y retazos aprovechados
- Porcentaje de utilización y área de merma
- Diagnóstico de degradación y límites operativos
"""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from decimal import Decimal
import json
from pathlib import Path
import sys
import time
import tracemalloc

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
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.domain.problem import MaterialSource

EVIDENCE_DIR = ROOT / "docs" / "evidence" / "sprint-02" / "TA-044"

METHOD_FACTORIES = [
    ("FF", FirstFitOptimizer),
    ("BF", BestFitOptimizer),
    ("WF", WorstFitOptimizer),
    ("M4", HoleFillingOptimizer),
    ("M5", BestResidualFitOptimizer),
    ("M6", BeamSearchOptimizer),
]


@dataclass
class BenchmarkRecord:
    scale_n: int
    case_id: str
    method: str
    status: str  # SUCCESS, PARTIAL, FAILED
    execution_time_ms: float
    peak_memory_kb: float
    peak_memory_mb: float
    total_units: int
    placed_units: int
    unplaced_units: int
    completion_rate_pct: float
    sheets_used: int
    remnants_used: int
    utilization_pct: float | None
    waste_mm2: float | None
    recoverable_remnant_mm2: float | None
    error_message: str | None = None


def run_single_benchmark(scale_n: int, method_code: str, factory) -> BenchmarkRecord:
    problem = load_capacity_problem(scale_n)

    tracemalloc.start()
    t0 = time.perf_counter_ns()
    error_msg = None
    res = None

    try:
        optimizer = factory()
        res = optimizer.optimize(problem)
    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {exc}"
    finally:
        t1 = time.perf_counter_ns()
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    execution_time_ms = round((t1 - t0) / 1_000_000, 2)
    peak_memory_kb = round(peak_mem / 1024, 2)
    peak_memory_mb = round(peak_mem / (1024 * 1024), 3)

    if res is None:
        return BenchmarkRecord(
            scale_n=scale_n,
            case_id=f"CAP-{scale_n}",
            method=method_code,
            status="FAILED",
            execution_time_ms=execution_time_ms,
            peak_memory_kb=peak_memory_kb,
            peak_memory_mb=peak_memory_mb,
            total_units=scale_n,
            placed_units=0,
            unplaced_units=scale_n,
            completion_rate_pct=0.0,
            sheets_used=0,
            remnants_used=0,
            utilization_pct=None,
            waste_mm2=None,
            recoverable_remnant_mm2=None,
            error_message=error_msg,
        )

    # Contar stock utilizado
    sheets_used = sum(1 for s in res.materials_used if s.source is MaterialSource.SHEET)
    remnants_used = sum(1 for s in res.materials_used if s.source is MaterialSource.REMNANT)

    # Calcular métricas canónicas si hubo colocaciones
    util_pct = None
    waste = None
    rec_rem = None
    if res.placements:
        try:
            res_metrics, _ = calculate_metrics(res, minimum_width_mm=1, minimum_height_mm=1)
            if res_metrics.metrics:
                util_pct = float(res_metrics.metrics.utilization_pct)
                waste = float(res_metrics.metrics.waste_mm2)
                rec_rem = float(res_metrics.metrics.recoverable_remnant_mm2)
        except Exception as m_exc:
            error_msg = f"Metrics calculation warning: {m_exc}"

    status = "SUCCESS" if res.placed_units == res.total_units else "PARTIAL"

    return BenchmarkRecord(
        scale_n=scale_n,
        case_id=f"CAP-{scale_n}",
        method=method_code,
        status=status,
        execution_time_ms=execution_time_ms,
        peak_memory_kb=peak_memory_kb,
        peak_memory_mb=peak_memory_mb,
        total_units=res.total_units,
        placed_units=res.placed_units,
        unplaced_units=len(res.unplaced_units),
        completion_rate_pct=round(res.placed_units / res.total_units * 100, 1),
        sheets_used=sheets_used,
        remnants_used=remnants_used,
        utilization_pct=util_pct,
        waste_mm2=waste,
        recoverable_remnant_mm2=rec_rem,
        error_message=error_msg,
    )


def run_full_capacity_benchmark(output_dir: Path | None = None) -> list[BenchmarkRecord]:
    target_dir = output_dir or EVIDENCE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    records: list[BenchmarkRecord] = []
    print("=" * 78)
    print("INICIANDO PRUEBAS DE CAPACIDAD Y ESTRÉS TA-044")
    print(f"Escalas: {CAPACITY_SCENARIOS} | Métodos: {[m[0] for m in METHOD_FACTORIES]}")
    print("=" * 78)

    for scale in CAPACITY_SCENARIOS:
        print(f"\n>>> Evaluando Escenario CAP-{scale} ({scale} piezas)...")
        for code, factory in METHOD_FACTORIES:
            print(f"  Ejecutando método {code}...", end="", flush=True)
            rec = run_single_benchmark(scale, code, factory)
            records.append(rec)
            print(f" {rec.status} en {rec.execution_time_ms} ms | Colocadas: {rec.placed_units}/{rec.total_units} | RAM: {rec.peak_memory_mb} MB")

    # Guardar JSON
    json_path = target_dir / "capacity_benchmark_results.json"
    json_data = [asdict(r) for r in records]
    json_path.write_text(json.dumps(json_data, indent=2), encoding="utf-8")

    # Guardar CSV
    csv_path = target_dir / "capacity_benchmark_results.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(json_data[0].keys()))
        writer.writeheader()
        writer.writerows(json_data)

    print("\n" + "=" * 78)
    print(f"BENCHMARK COMPLETADO EXITOSAMENTE")
    print(f"Resultados crudos guardados en:")
    print(f" - {json_path}")
    print(f" - {csv_path}")
    print("=" * 78)

    return records


if __name__ == "__main__":
    run_full_capacity_benchmark()
