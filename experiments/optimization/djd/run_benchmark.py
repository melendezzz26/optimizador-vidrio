"""Ejecuta DJD-1/3 y los baselines en serie sobre TA-027 y la demo discriminante."""
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
from experiments.optimization.djd import DJDExperimental
from experiments.optimization.loader import CASES, build_problem, load_problem, read_case

CASE_DIR = Path(__file__).resolve().parent / "cases"
DISCRIMINANT = "DJD-DISCRIMINANT-001"
OUTPUT = ROOT / "docs/evidence/sprint-02/SP-004/benchmark-results"
METHODS = (("FF", FirstFitOptimizer), ("BF", BestFitOptimizer),
           ("WF", WorstFitOptimizer), ("DJD-1/3", DJDExperimental))


def load_experimental_case(case_id):
    """Carga TA-027 con el loader oficial o el JSON didáctico por separado."""
    if case_id == DISCRIMINANT:
        data = json.loads((CASE_DIR / f"{case_id}.json").read_text(encoding="utf-8"))
        return data, build_problem(data)
    data = read_case(case_id)
    return data, load_problem(case_id)


def run_one(case_id, method_name, optimizer_class):
    """Mide una ejecución completa y serializa placements y diagnósticos."""
    data, problem = load_experimental_case(case_id)
    start = time.perf_counter_ns()
    trace = None
    if method_name == "DJD-1/3":
        result, trace = optimizer_class().optimize(
            problem,
            minimum_width_mm=Decimal(str(data["residual_limits"]["minimum_width_mm"])),
            minimum_height_mm=Decimal(str(data["residual_limits"]["minimum_height_mm"])),
        )
    else:
        result = optimizer_class().optimize(problem)
        result, _ = calculate_metrics(
            result,
            Decimal(str(data["residual_limits"]["minimum_width_mm"])),
            Decimal(str(data["residual_limits"]["minimum_height_mm"])),
        )
    runtime_ms = (time.perf_counter_ns() - start) / 1_000_000
    metrics = result.metrics
    remnants = sum(stock.source.value == "RETAZO" for stock in result.materials_used)
    sheets = sum(stock.source.value == "PLANCHA" for stock in result.materials_used)
    row = {
        "case": case_id, "method": method_name,
        "requested_units": result.total_units, "placed_units": result.placed_units,
        "unplaced_units": result.total_units - result.placed_units,
        "remnants_used": remnants, "sheets_used": sheets,
        "utilization_pct": str(metrics.utilization_pct) if metrics else "",
        "waste": str(metrics.waste_mm2) if metrics else "",
        "recoverable_area": str(metrics.recoverable_remnant_mm2) if metrics else "",
        "runtime_ms": f"{runtime_ms:.3f}",
        "initial_fill_ratio": json.dumps(trace.initial_fill_ratio, ensure_ascii=False) if trace else "",
        "combinations_size_1": trace.combinations_size_1 if trace else "",
        "combinations_size_2": trace.combinations_size_2 if trace else "",
        "combinations_size_3": trace.combinations_size_3 if trace else "",
        "combinations_pruned": trace.combinations_pruned if trace else "",
        "geometric_sequence_checks": trace.geometric_sequence_checks if trace else "",
        "cached_sequences_skipped": trace.cached_sequences_skipped if trace else "",
        "geometric_checks": trace.geometric_checks if trace else "",
        "feasible_combinations": trace.feasible_combinations if trace else "",
        "waste_tolerance_steps": trace.waste_tolerance_steps if trace else "",
        "selected_combination_sizes": ";".join(map(str, trace.selected_combination_sizes)) if trace else "",
        "source_switches": trace.source_switches if trace else "",
    }
    detail = {
        "case": case_id, "label": data.get("label", "benchmark oficial TA-027"),
        "method": method_name,
        "placements": [{
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
    if trace:
        detail["djd_trace"] = {
            "initial_fill_ratio": trace.initial_fill_ratio,
            "combinations_size_1": trace.combinations_size_1,
            "combinations_size_2": trace.combinations_size_2,
            "combinations_size_3": trace.combinations_size_3,
            "combinations_pruned": trace.combinations_pruned,
            "pruned_by_size": trace.pruned_by_size,
            "geometric_sequence_checks": trace.geometric_sequence_checks,
            "cached_sequences_skipped": trace.cached_sequences_skipped,
            "geometric_checks": trace.geometric_checks,
            "feasible_combinations": trace.feasible_combinations,
            "waste_tolerance_steps": trace.waste_tolerance_steps,
            "selected_combination_sizes": trace.selected_combination_sizes,
            "selected_groups": trace.selected_groups,
            "source_switches": trace.source_switches,
            "processing_order": trace.processing_order,
            "source_decisions": trace.source_decisions,
        }
    return row, detail


def main():
    """Corre cada caso y método en serie y escribe las salidas crudas."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    cases = (*CASES, DISCRIMINANT)
    rows, details = [], []
    for case_id in cases:
        for method_name, optimizer_class in METHODS:
            row, detail = run_one(case_id, method_name, optimizer_class)
            rows.append(row)
            details.append(detail)
            print(f"{case_id} {method_name}: {row['placed_units']}/{row['requested_units']} unidades; "
                  f"utilización={row['utilization_pct']}%; merma={row['waste']} mm²; "
                  f"retazos={row['remnants_used']}; planchas={row['sheets_used']}; "
                  f"ms={row['runtime_ms']}; grupos DJD={row['selected_combination_sizes']}")
            del row, detail
            gc.collect()
    csv_path = OUTPUT / "sp004_djd_results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    config = {case_id: load_experimental_case(case_id)[0]["config"] for case_id in cases}
    payload = {
        "spike": "SP-004", "candidate": "DJD-1/3",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime": {"python": sys.version, "platform": sys.platform},
        "configuration": config, "official_fixtures": list(CASES),
        "non_official_case": DISCRIMINANT, "results": details,
    }
    json_path = OUTPUT / "sp004_djd_trace.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(csv_path)
    print(json_path)


if __name__ == "__main__":
    main()
