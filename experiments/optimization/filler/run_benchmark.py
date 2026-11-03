"""Corre los tres fixtures congelados en secuencia y guarda evidencia cruda."""
import csv
import gc
import json
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from app.modules.optimization.domain.best_fit import BestFitOptimizer
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.domain.worst_fit import WorstFitOptimizer
from experiments.optimization.filler import FillerExperimental
from experiments.optimization.loader import CASES, load_problem, read_case

OUTPUT = ROOT / "docs/evidence/sprint-02/SP-004/benchmark-results"
METHODS = (("FF", FirstFitOptimizer), ("BF", BestFitOptimizer),
           ("WF", WorstFitOptimizer), ("Filler", FillerExperimental))


def run_one(case_id, method_name, optimizer_class):
    """Mide una ejecución completa con carga, colocación y métricas."""
    frozen = read_case(case_id)
    problem = load_problem(case_id)
    start = time.perf_counter_ns()
    trace = None
    if method_name == "Filler":
        result, trace = optimizer_class().optimize(
            problem,
            minimum_width_mm=Decimal(str(frozen["residual_limits"]["minimum_width_mm"])),
            minimum_height_mm=Decimal(str(frozen["residual_limits"]["minimum_height_mm"])),
        )
    else:
        result = optimizer_class().optimize(problem)
        result, _ = calculate_metrics(
            result,
            Decimal(str(frozen["residual_limits"]["minimum_width_mm"])),
            Decimal(str(frozen["residual_limits"]["minimum_height_mm"])),
        )
    runtime_ms = (time.perf_counter_ns() - start) / 1_000_000
    remnants = sum(stock.source.value == "RETAZO" for stock in result.materials_used)
    sheets = sum(stock.source.value == "PLANCHA" for stock in result.materials_used)
    metrics = result.metrics
    row = {
        "case": case_id, "method": method_name, "requested_units": result.total_units,
        "placed_units": result.placed_units,
        "unplaced_units": result.total_units - result.placed_units,
        "remnants_used": remnants, "sheets_used": sheets,
        "utilization_pct": str(metrics.utilization_pct) if metrics else "",
        "waste": str(metrics.waste_mm2) if metrics else "",
        "recoverable_area": str(metrics.recoverable_remnant_mm2) if metrics else "",
        "runtime_ms": f"{runtime_ms:.3f}",
        "material_area_mm2": str(metrics.material_area_mm2) if metrics else "",
        "placed_piece_area_mm2": str(metrics.placed_piece_area_mm2) if metrics else "",
    }
    detail = {
        "case": case_id, "method": method_name, "placements": [{
            "piece_id": p.piece.piece_id, "unit_index": p.piece.unit_index,
            "source": p.stock.source.value, "material_id": p.stock.material_id,
            "physical_unit_index": p.stock.physical_unit_index,
            "x_mm": str(p.x_mm), "y_mm": str(p.y_mm),
            "rotation_deg": str(p.rotation_deg), "area_mm2": str(p.piece.area_mm2),
        } for p in result.placements],
        "materials_used": [{"source": s.source.value, "material_id": s.material_id,
                            "physical_unit_index": s.physical_unit_index,
                            "material_key": [s.glass_type_id, str(s.thickness_mm)]}
                           for s in result.materials_used],
        "unplaced": [{"piece_id": u.piece_id, "unit_index": u.unit_index}
                     for u in result.unplaced_units],
    }
    if trace is not None:
        detail["filler_trace"] = {
            "attempts": trace.attempts, "placements": trace.placements,
            "source_switches": trace.source_switches,
            "skipped_piece_attempts": trace.skipped_piece_attempts,
            "successful_fill_after_skip": trace.successful_fill_after_skip,
            "processing_order": trace.processing_order,
            "pieces_per_source": trace.pieces_per_source,
        }
    return row, detail


def main():
    """Ejecuta FF, BF, WF y Filler en orden, con liberación entre métodos."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rows, details = [], []
    for case_id in CASES:
        for method_name, optimizer_class in METHODS:
            row, detail = run_one(case_id, method_name, optimizer_class)
            rows.append(row)
            details.append(detail)
            print(f"{case_id} {method_name}: {row['placed_units']}/{row['requested_units']} unidades, "
                  f"utilización={row['utilization_pct']}%, merma={row['waste']} mm², "
                  f"retazos={row['remnants_used']}, planchas={row['sheets_used']}, "
                  f"tiempo={row['runtime_ms']} ms")
            del row, detail
            gc.collect()
    csv_path = OUTPUT / "sp004_filler_descartado_results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    payload = {
        "spike": "SP-004", "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime": {"python": sys.version, "platform": sys.platform},
        "configuration": {case: read_case(case)["config"] for case in CASES},
        "fixtures": list(CASES), "results": details,
    }
    json_path = OUTPUT / "sp004_filler_descartado_trace.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(csv_path)
    print(json_path)


if __name__ == "__main__":
    main()
