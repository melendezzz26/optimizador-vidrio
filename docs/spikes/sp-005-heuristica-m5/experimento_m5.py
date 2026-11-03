"""Reproducible SP-005 comparison using the canonical TA-027 loader and engine.

M5 is an experimental NewGlass selector adaptation. This file supplies only
the selection policy; geometry, candidate generation, placement validation and
metrics are imported from the backend so all four methods share one engine.
"""

import argparse
import csv
import hashlib
import json
import platform
import statistics
import sys
import time
import tracemalloc
from collections.abc import Iterable, Mapping
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Callable

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parents[2]
BACKEND_DIR = PROJECT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(PROJECT_DIR))

from experiments.optimization.loader import CASES, load_problem, read_case
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.best_fit import BestFitOptimizer
from app.modules.optimization.domain.worst_fit import WorstFitOptimizer
from app.modules.optimization.domain.packing import FeasibleCandidate, FirstFitEvent, pack
from app.modules.optimization.domain.problem import (
    MaterialSource,
    OptimizationProblem,
    OptimizationResult,
)
from app.modules.optimization.domain.metrics import calculate_metrics, largest_rectangle


class BestResidualFitSelector:
    """NewGlass experimental adaptation of Best Residual Fit (BRF).

    Minimize this lexicographic score for each canonical feasible source:
    (-recoverable_rectangle_area, fragmented_free_cells, stock_rank,
    orientation_rank, row, column). The first term maximizes the largest
    post-placement free rectangle; the second minimizes remaining free cells
    outside it. The final terms keep deterministic baseline tie ordering.
    """

    def __init__(self, min_width_cells: int = 1, min_height_cells: int = 1):
        self.min_width_cells = min_width_cells
        self.min_height_cells = min_height_cells

    def select(self, candidates: Iterable[FeasibleCandidate]) -> FeasibleCandidate | None:
        def score(candidate: FeasibleCandidate):
            layout = candidate.layout_after
            free_rows = tuple(
                usable & ~blocked
                for usable, blocked in zip(layout.usable, layout.blocked)
            )
            rectangle = largest_rectangle(free_rows, layout.material.columns)
            if (
                rectangle is not None
                and rectangle[2] >= self.min_width_cells
                and rectangle[3] >= self.min_height_cells
            ):
                remnant_cells = rectangle[2] * rectangle[3]
            else:
                remnant_cells = 0

            fragmented_cells = candidate.remaining_free_cells_after_placement - remnant_cells
            return (
                -remnant_cells,
                fragmented_cells,
                candidate.stock_rank,
                candidate.orientation_rank,
                candidate.row,
                candidate.column,
            )

        return min(candidates, key=score, default=None)


class M5Result(OptimizationResult):
    @property
    def method(self) -> str:
        return "M5"


class BestResidualFitOptimizer:
    """M5 selector on the shared backend packing traversal."""

    def __init__(self, min_width_cells: int = 1, min_height_cells: int = 1):
        self.selector = BestResidualFitSelector(min_width_cells, min_height_cells)

    def optimize(
        self,
        problem: OptimizationProblem,
        on_event: Callable[[FirstFitEvent], None] | None = None,
        *,
        checkpoint=None,
        on_visual=None,
    ) -> OptimizationResult:
        result = pack(
            problem,
            on_event,
            select=self.selector.select,
            checkpoint=checkpoint,
            on_visual=on_visual,
        )
        return M5Result(problem=result.problem, placements=result.placements)


METHODS = (
    ("FF", "First Fit", FirstFitOptimizer),
    ("BF", "Best Fit", BestFitOptimizer),
    ("WF", "Worst Fit", WorstFitOptimizer),
    ("M5", "Best Residual Fit (adaptación experimental NewGlass)", BestResidualFitOptimizer),
)


def _jsonable(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def placement_records(result: OptimizationResult) -> list[dict]:
    """Stable, inspectable placement representation used for determinism checks."""
    return [
        {
            "piece_id": placement.piece.piece_id,
            "unit_index": placement.piece.unit_index,
            "material_key": _jsonable(placement.piece.material_key),
            "stock_source": placement.stock.source.value,
            "material_id": placement.stock.material_id,
            "stock_unit_index": placement.stock.physical_unit_index,
            "x_mm": str(placement.x_mm),
            "y_mm": str(placement.y_mm),
            "rotation_deg": str(placement.rotation_deg),
            "geometry": _jsonable(placement.geometry),
        }
        for placement in result.placements
    ]


def _functional_payload(result: OptimizationResult, calculated_result: OptimizationResult) -> dict:
    metrics = calculated_result.metrics
    return {
        "placed_units": calculated_result.placed_units,
        "total_units": calculated_result.total_units,
        "complete": calculated_result.complete,
        "metrics": {
            "utilization_pct": str(metrics.utilization_pct),
            "waste_mm2": str(metrics.waste_mm2),
            "new_sheets_used": metrics.new_sheets_used,
            "recoverable_remnant_mm2": str(metrics.recoverable_remnant_mm2),
            "material_area_mm2": str(metrics.material_area_mm2),
            "placed_piece_area_mm2": str(metrics.placed_piece_area_mm2),
        },
        "placements": placement_records(result),
    }


def _signature(payload: dict) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _git_commit() -> str | None:
    import subprocess

    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_DIR,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def run_experiment(repetitions: int = 3, output_dir: Path | None = None) -> bool:
    if repetitions < 3:
        raise ValueError("SP-005 requiere al menos tres repeticiones por método y caso.")

    results_dir = Path(output_dir) if output_dir else BASE_DIR / "resultados"
    results_dir.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict] = []
    summary_by_case: dict[str, dict] = {}
    all_deterministic = True

    print("SP-005 — FF/BF/WF/M5 en backend canónico y fixtures TA-027")
    print(f"Python: {sys.version.splitlines()[0]} ({platform.platform()})")
    print(f"Commit base del runner: {_git_commit() or 'no disponible'}")
    print(f"Repeticiones por método/caso: {repetitions}")
    print(f"Directorio de resultados: {results_dir}")

    for case_id in CASES:
        case_data = read_case(case_id)
        residual_limits = {
            key: Decimal(str(value))
            for key, value in case_data["residual_limits"].items()
        }
        summary_by_case[case_id] = {}
        print(f"\n=== {case_id} ===")

        for code, name, optimizer_factory in METHODS:
            samples = []
            payloads = []
            for repetition in range(1, repetitions + 1):
                problem = load_problem(case_id)
                optimizer = optimizer_factory()
                tracemalloc.start()
                started_ns = time.perf_counter_ns()
                try:
                    raw_result = optimizer.optimize(problem)
                    calculated_result, _ = calculate_metrics(raw_result, **residual_limits)
                    elapsed_ms = (time.perf_counter_ns() - started_ns) / 1_000_000
                    _, peak_bytes = tracemalloc.get_traced_memory()
                finally:
                    tracemalloc.stop()

                payload = _functional_payload(raw_result, calculated_result)
                payloads.append(payload)
                metrics = calculated_result.metrics
                row = {
                    "caso": case_id,
                    "repeticion": repetition,
                    "metodo_codigo": code,
                    "metodo_nombre": name,
                    "piezas_colocadas": calculated_result.placed_units,
                    "piezas_totales": calculated_result.total_units,
                    "retazos_usados": sum(
                        stock.source is MaterialSource.REMNANT
                        for stock in calculated_result.materials_used
                    ),
                    "planchas_nuevas": metrics.new_sheets_used,
                    "utilizacion_pct": float(metrics.utilization_pct),
                    "desperdicio_mm2": float(metrics.waste_mm2),
                    "retazo_recuperable_mm2": float(metrics.recoverable_remnant_mm2),
                    "area_material_usado_mm2": float(metrics.material_area_mm2),
                    "area_piezas_colocadas_mm2": float(metrics.placed_piece_area_mm2),
                    "tiempo_ms": round(elapsed_ms, 2),
                    "memoria_pico_kb": round(peak_bytes / 1024, 2),
                    "completo": calculated_result.complete,
                    "firma_funcional_sha256": _signature(payload),
                }
                samples.append(row)
                print(
                    f"[{code}] rep {repetition}/{repetitions}: "
                    f"{row['piezas_colocadas']}/{row['piezas_totales']} colocadas, "
                    f"retazos={row['retazos_usados']}, planchas={row['planchas_nuevas']}, "
                    f"uso={row['utilizacion_pct']:.3f}%, merma={row['desperdicio_mm2']:.2f} mm², "
                    f"recuperable={row['retazo_recuperable_mm2']:.2f} mm², "
                    f"tiempo={row['tiempo_ms']:.2f} ms"
                )

            deterministic = all(payload == payloads[0] for payload in payloads[1:])
            all_deterministic &= deterministic
            median_time = round(statistics.median(row["tiempo_ms"] for row in samples), 2)
            median_memory = round(statistics.median(row["memoria_pico_kb"] for row in samples), 2)
            for row in samples:
                row["tiempo_ms_mediana"] = median_time
                row["memoria_pico_kb_mediana"] = median_memory
                row["determinista"] = deterministic
                all_rows.append(row)

            summary_by_case[case_id][code] = {
                "metodo_nombre": name,
                "repeticiones": repetitions,
                "determinista": deterministic,
                "firma_funcional_sha256": _signature(payloads[0]) if deterministic else None,
                "resultados_funcionales": payloads[0] if deterministic else payloads,
                "tiempo_ms_muestras": [row["tiempo_ms"] for row in samples],
                "tiempo_ms_mediana": median_time,
                "memoria_pico_kb_muestras": [row["memoria_pico_kb"] for row in samples],
                "memoria_pico_kb_mediana": median_memory,
            }
            print(
                f"  determinista={deterministic}; mediana tiempo={median_time:.2f} ms; "
                f"mediana memoria={median_memory:.2f} KB"
            )

        case_path = results_dir / f"{case_id.lower().replace('-', '_')}_detalles.json"
        case_path.write_text(
            json.dumps(summary_by_case[case_id], indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    csv_path = results_dir / "resultados_baseline_vs_m5.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(all_rows[0]))
        writer.writeheader()
        writer.writerows(all_rows)

    summary = {
        "schema_version": 2,
        "fuente": "backend versionado + loader TA-027; sin motor duplicado en notebook",
        "commit_base_runner": _git_commit(),
        "python": sys.version.splitlines()[0],
        "plataforma": platform.platform(),
        "repeticiones_por_metodo_y_caso": repetitions,
        "determinismo_funcional_completo": all_deterministic,
        "definicion_m5": {
            "denominacion": "Best Residual Fit (adaptación experimental de NewGlass)",
            "score_lexicografico": "(-area_rectangulo_recuperable, celdas_libres_fragmentadas, stock_rank, orientation_rank, row, column)",
            "fuente_motor": "backend/app/modules/optimization/domain/packing.py",
            "fuente_metricas": "backend/app/modules/optimization/domain/metrics.py",
        },
        "casos": summary_by_case,
    }
    json_path = results_dir / "resumen_comparativo.json"
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"\nCSV: {csv_path}")
    print(f"JSON: {json_path}")
    print(f"Determinismo funcional en todas las celdas método/caso: {all_deterministic}")
    return all_deterministic


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, default=3, help="Repeticiones por método/caso (mínimo 3).")
    parser.add_argument("--output-dir", type=Path, help="Destino de CSV/JSON; por defecto, resultados/ del spike.")
    args = parser.parse_args()
    try:
        return 0 if run_experiment(args.repetitions, args.output_dir) else 1
    except ValueError as error:
        parser.error(str(error))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
