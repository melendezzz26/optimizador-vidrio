"""Comparación secuencial Pair-Block/FF/BF/WF con evidencia cruda."""
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
from experiments.optimization.block_packing import BlockPackingExperimental
from experiments.optimization.djd.run_benchmark import DISCRIMINANT as DJD_DISCRIMINANT
from experiments.optimization.loader import CASES, build_problem, load_problem, read_case


BLOCK_CASE = "BLOCK-DISCRIMINANT-001"
BLOCK_CASE_PATH = Path(__file__).resolve().parent / "cases" / f"{BLOCK_CASE}.json"
METHODS = (("FF", FirstFitOptimizer), ("BF", BestFitOptimizer),
           ("WF", WorstFitOptimizer), ("Pair-Block", BlockPackingExperimental))
OUTPUT = ROOT / "docs/evidence/sprint-02/SP-004/benchmark-results"


def load_case(case_id):
    """Carga un fixture oficial congelado o el JSON no oficial indicado."""
    if case_id in CASES:
        return read_case(case_id), load_problem(case_id)
    if case_id == BLOCK_CASE:
        data = json.loads(BLOCK_CASE_PATH.read_text(encoding="utf-8"))
        return data, build_problem(data)
    if case_id.startswith("DJD-DIAGNOSTIC-"):
        path = ROOT / "experiments/optimization/djd/cases" / f"{case_id}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return data, build_problem(data)
    raise ValueError(f"Unknown experiment case: {case_id}")


def _placement_rows(result):
    return [{
        "piece_id": placement.piece.piece_id,
        "unit_index": placement.piece.unit_index,
        "source": placement.stock.source.value,
        "material_id": placement.stock.material_id,
        "physical_unit_index": placement.stock.physical_unit_index,
        "x_mm": str(placement.x_mm), "y_mm": str(placement.y_mm),
        "rotation_deg": str(placement.rotation_deg),
        "geometry": dict(placement.geometry),
        "area_mm2": str(placement.piece.area_mm2),
    } for placement in result.placements]


def run_one(case_id, method_name, optimizer_class):
    """Ejecuta un caso de forma aislada y devuelve fila y traza serializables."""
    data, problem = load_case(case_id)
    start = time.perf_counter_ns()
    trace = None
    if method_name == "Pair-Block":
        result, trace = optimizer_class().optimize(problem)
    else:
        result = optimizer_class().optimize(problem)
    result, _ = calculate_metrics(result,
        Decimal(str(data["residual_limits"]["minimum_width_mm"])),
        Decimal(str(data["residual_limits"]["minimum_height_mm"])))
    runtime_ms = (time.perf_counter_ns() - start) / 1_000_000
    metrics = result.metrics
    row = {
        "case": case_id, "method": method_name,
        "requested_units": result.total_units, "placed_units": result.placed_units,
        "unplaced_units": result.total_units - result.placed_units,
        "remnants_used": sum(stock.source.value == "RETAZO" for stock in result.materials_used),
        "sheets_used": sum(stock.source.value == "PLANCHA" for stock in result.materials_used),
        "utilization_pct": str(metrics.utilization_pct) if metrics else "",
        "waste": str(metrics.waste_mm2) if metrics else "",
        "recoverable_area": str(metrics.recoverable_remnant_mm2) if metrics else "",
        "runtime_ms": f"{runtime_ms:.3f}",
        "candidate_pairs": trace.candidate_pairs if trace else "",
        "filtered_pairs": trace.filtered_pairs if trace else "",
        "geometrically_checked_pairs": trace.geometrically_checked_pairs if trace else "",
        "accepted_blocks": trace.accepted_blocks if trace else "",
        "placed_blocks": trace.placed_blocks if trace else "",
        "pieces_in_blocks": trace.pieces_in_blocks if trace else "",
        "standalone_pieces": trace.standalone_pieces if trace else "",
        "block_compaction": f"{trace.block_compaction:.6f}" if trace else "",
        "block_generation_ms": f"{trace.block_generation_ms:.3f}" if trace else "",
        "packing_ms": f"{trace.packing_ms:.3f}" if trace else "",
    }
    detail = {
        "case": case_id, "label": data.get("label", "benchmark oficial TA-027"),
        "diagnostic_intent": data.get("diagnostic_intent"), "method": method_name,
        "configuration": data["config"], "placements": _placement_rows(result),
        "materials_used": [{"source": stock.source.value, "material_id": stock.material_id,
            "physical_unit_index": stock.physical_unit_index,
            "material_key": [stock.glass_type_id, str(stock.thickness_mm)]}
            for stock in result.materials_used],
        "unplaced": [{"piece_id": unit.piece_id, "unit_index": unit.unit_index}
            for unit in result.unplaced_units],
    }
    if trace:
        detail["block_trace"] = {
            "candidate_pairs": trace.candidate_pairs, "filtered_pairs": trace.filtered_pairs,
            "geometrically_checked_pairs": trace.geometrically_checked_pairs,
            "accepted_blocks": trace.accepted_blocks, "placed_blocks": trace.placed_blocks,
            "pieces_in_blocks": trace.pieces_in_blocks, "standalone_pieces": trace.standalone_pieces,
            "block_compaction": trace.block_compaction,
            "block_compaction_values": trace.block_compaction_values,
            "block_generation_ms": trace.block_generation_ms, "packing_ms": trace.packing_ms,
            "selected_blocks": trace.selected_blocks,
            "processing_order": trace.processing_order,
        }
    return row, detail


def main():
    """Corre benchmarks y determinismo en serie, liberando resultados entre corridas."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    case_ids = (*CASES, BLOCK_CASE)
    rows, details = [], []
    for case_id in case_ids:
        for method_name, optimizer_class in METHODS:
            row, detail = run_one(case_id, method_name, optimizer_class)
            rows.append(row)
            details.append(detail)
            print(f"{case_id} {method_name}: {row['placed_units']}/{row['requested_units']} colocadas; "
                  f"aprovechamiento={row['utilization_pct']}%; merma={row['waste']} mm²; "
                  f"retazos={row['remnants_used']}; planchas={row['sheets_used']}; ms={row['runtime_ms']}; "
                  f"bloques={row['placed_blocks']}")
            del row, detail
            gc.collect()
    determinism = {}
    for case_id in case_ids:
        signatures, runtimes = [], []
        for _ in range(3):
            row, detail = run_one(case_id, "Pair-Block", BlockPackingExperimental)
            functional = tuple(row[key] for key in (
                "placed_units", "unplaced_units", "remnants_used", "sheets_used",
                "utilization_pct", "waste", "recoverable_area"))
            placements = json.dumps(detail["placements"], ensure_ascii=False, sort_keys=True)
            blocks = json.dumps(detail["block_trace"]["selected_blocks"], ensure_ascii=False, sort_keys=True)
            signatures.append((functional, placements, blocks))
            runtimes.append(row["runtime_ms"])
            del row, detail
            gc.collect()
        determinism[case_id] = {"runs": 3, "pass": signatures[0] == signatures[1] == signatures[2],
            "runtime_ms": runtimes}
        print(f"Determinismo {case_id} ×3: {'PASS' if determinism[case_id]['pass'] else 'FAIL'}")
    csv_path = OUTPUT / "sp004_block_results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    payload = {
        "spike": "SP-004", "candidate": "Pair-Block experimental adaptation",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime": {"python": sys.version, "platform": sys.platform},
        "official_fixtures": list(CASES), "non_official_case": BLOCK_CASE,
        "method_order": [name for name, _ in METHODS], "results": details,
        "determinism": determinism,
    }
    json_path = OUTPUT / "sp004_block_trace.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(csv_path)
    print(json_path)


if __name__ == "__main__":
    main()
