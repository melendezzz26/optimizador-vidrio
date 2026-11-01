"""Experimento reproducible para el Spike SP-005: Heurística adicional M5 (Best Residual Fit - BRF).

Este script ejecuta de forma determinista la comparación experimental entre las tres
heurísticas del baseline de NewGlass (FF, BF, WF) y la nueva heurística M5 (BRF)
sobre los tres casos congelados TA-027: EXP-SMALL-001, EXP-MEDIUM-001 y EXP-COMPLEX-001.

Condiciones operacionales y experimentales comunes (SP-002 / TA-027):
- Resolución raster: 1 mm / píxel
- Exploración angular: paso de 5° (0° a 355°)
- Margen y separación: exactos por caso (0 mm en small, 1 mm en medium y complex)
- Jerarquía de stock: RETAZO prioritario sobre PLANCHA
- Métricas auditadas: utilización %, desperdicio mm², retazo recuperable mm², planchas usadas, tiempo ms.
"""

import csv
import json
import os
import sys
import time
import tracemalloc
from collections.abc import Iterable
from decimal import Decimal
from pathlib import Path
from typing import Callable, Literal

# Agregar backend y raíz al path de importación
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
from app.modules.optimization.domain.problem import OptimizationProblem, OptimizationResult
from app.modules.optimization.domain.metrics import calculate_metrics, largest_rectangle


# ==============================================================================
# DEFINICIÓN FORMAL DE LA HEURÍSTICA M5: BEST RESIDUAL FIT (BRF)
# ==============================================================================

class BestResidualFitSelector:
    """Selector de candidato para M5 (Best Residual Fit).

    Estrategia de optimización:
    1. Evalúa el estado post-colocación de cada candidato factible en el nivel activo.
    2. Identifica el rectángulo libre máximo inscribible (retazo residual recuperable).
    3. Maximiza el área del retazo recuperable principal (-area_retazo).
    4. En caso de empate, minimiza la merma fragmentada no recuperable (celdas_libres - area_retazo).
    5. Criterios de desempate deterministas idénticos a BF/WF:
       stock_rank ASC, orientation_rank ASC, row ASC, column ASC.
    """

    def __init__(self, min_width_cells: int = 1, min_height_cells: int = 1):
        self.min_width_cells = min_width_cells
        self.min_height_cells = min_height_cells

    def select(self, candidates: Iterable[FeasibleCandidate]) -> FeasibleCandidate | None:
        def score(candidate: FeasibleCandidate):
            layout = candidate.layout_after
            free_rows = tuple(usable & ~blocked for usable, blocked in zip(layout.usable, layout.blocked))
            rect = largest_rectangle(free_rows, layout.material.columns)
            if rect is not None and rect[2] >= self.min_width_cells and rect[3] >= self.min_height_cells:
                remnant_cells = rect[2] * rect[3]
            else:
                remnant_cells = 0

            free_cells = candidate.remaining_free_cells_after_placement
            fragmented_cells = free_cells - remnant_cells

            return (
                -remnant_cells,             # 1. Maximizar retazo recuperable
                fragmented_cells,           # 2. Minimizar fragmentación
                candidate.stock_rank,       # 3. Jerarquía de stock original
                candidate.orientation_rank, # 4. Primera orientación factible
                candidate.row,              # 5. Fila superior
                candidate.column,           # 6. Columna izquierda
            )

        return min(candidates, key=score, default=None)


class M5Result(OptimizationResult):
    """Resultado identificado formalmente como método M5."""
    @property
    def method(self) -> str:
        return "M5"


class BestResidualFitOptimizer:
    """Optimizador M5 basado en Best Residual Fit (BRF)."""

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
            select=BestResidualFitSelector().select,
            checkpoint=checkpoint,
            on_visual=on_visual,
        )
        return M5Result(problem=result.problem, placements=result.placements)


# ==============================================================================
# PROTOCOLO EXPERIMENTAL Y EJECUCIÓN
# ==============================================================================

def run_experiment():
    results_dir = BASE_DIR / "resultados"
    results_dir.mkdir(parents=True, exist_ok=True)

    methods = [
        ("FF", "First Fit", FirstFitOptimizer),
        ("BF", "Best Fit", BestFitOptimizer),
        ("WF", "Worst Fit", WorstFitOptimizer),
        ("M5", "Best Residual Fit", BestResidualFitOptimizer),
    ]

    all_rows = []
    summary_data = {}

    print("================================================================================")
    print("NEWGLASS - EXPERIMENTACIÓN FORMAL SP-005 (T01): BASELINE VS HEURÍSTICA M5")
    print("================================================================================")
    print(f"Directorio de resultados: {results_dir}")
    print(f"Casos a evaluar: {', '.join(CASES)}")
    print("Condiciones: Resolución 1 mm, Rotación 5°, Margen/Separación congelados.")
    print("--------------------------------------------------------------------------------\n")

    for case_id in CASES:
        case_data = read_case(case_id)
        residual_limits = {k: Decimal(str(v)) for k, v in case_data["residual_limits"].items()}
        summary_data[case_id] = {}

        print(f"Ejecutando caso: {case_id} ({len(case_data['pieces'])} piezas def, "
              f"{sum(p['cantidad'] for p in case_data['pieces'])} unidades, "
              f"{len(case_data['stock'])} tipos de stock)...")

        for code, name, optimizer_factory in methods:
            tracemalloc.start()
            start_ns = time.perf_counter_ns()

            problem = load_problem(case_id)
            optimizer = optimizer_factory()
            raw_result = optimizer.optimize(problem)

            calc_result, residuals = calculate_metrics(raw_result, **residual_limits)
            duration_ms = (time.perf_counter_ns() - start_ns) / 1_000_000
            _, peak_mem_bytes = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            metrics = calc_result.metrics

            row = {
                "caso": case_id,
                "metodo_codigo": code,
                "metodo_nombre": name,
                "piezas_colocadas": calc_result.placed_units,
                "piezas_totales": calc_result.total_units,
                "planchas_nuevas": metrics.new_sheets_used,
                "utilizacion_pct": float(metrics.utilization_pct),
                "desperdicio_mm2": float(metrics.waste_mm2),
                "retazo_recuperable_mm2": float(metrics.recoverable_remnant_mm2),
                "area_material_usado_mm2": float(metrics.material_area_mm2),
                "area_piezas_colocadas_mm2": float(metrics.placed_piece_area_mm2),
                "tiempo_ms": round(duration_ms, 2),
                "memoria_pico_kb": round(peak_mem_bytes / 1024, 2),
                "completo": calc_result.complete,
            }
            all_rows.append(row)
            summary_data[case_id][code] = row

            print(f"  [{code:<2}] {name:<18} | Colocadas: {calc_result.placed_units}/{calc_result.total_units} "
                  f"| Planchas: {metrics.new_sheets_used} | Utilización: {metrics.utilization_pct:>6}% "
                  f"| Merma: {metrics.waste_mm2:>7} mm² | Retazo: {metrics.recoverable_remnant_mm2:>5} mm² "
                  f"| Tiempo: {duration_ms:>6.2f} ms | Memoria: {peak_mem_bytes/1024:>6.1f} KB")

        # Guardar detalle de caso en JSON
        case_json_path = results_dir / f"{case_id.lower().replace('-', '_')}_detalles.json"
        with open(case_json_path, "w", encoding="utf-8") as f:
            json.dump(summary_data[case_id], f, indent=2, ensure_ascii=False)
        print()

    # Guardar CSV consolidado
    csv_path = results_dir / "resultados_baseline_vs_m5.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        writer.writeheader()
        writer.writerows(all_rows)

    # Guardar JSON consolidado
    json_path = results_dir / "resumen_comparativo.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)

    print("================================================================================")
    print("EXPERIMENTO COMPLETADO EXITOSAMENTE")
    print(f"1. Resumen CSV generado en: {csv_path}")
    print(f"2. Resumen JSON generado en: {json_path}")
    print("================================================================================")


if __name__ == "__main__":
    run_experiment()
