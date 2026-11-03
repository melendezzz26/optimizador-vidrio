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
           ("WF", WorstFitOptimizer), ("Pair-Block-v2", BlockPackingExperimental))
OUTPUT = ROOT / "docs/evidence/sprint-02/SP-004/benchmark-results"
DIAGNOSTIC_CASES = (
    "BLOCK-V2-OBLIQUE-TRIANGLES-001",
    "BLOCK-V2-MIXED-TRIANGLE-CIRCLE-001",
)


def load_case(case_id):
    """Carga un fixture oficial congelado o el JSON no oficial indicado."""
    if case_id in CASES:
        return read_case(case_id), load_problem(case_id)
    if case_id.startswith("BLOCK-"):
        path = (BLOCK_CASE_PATH if case_id == BLOCK_CASE else
                Path(__file__).resolve().parent / "cases" / f"{case_id}.json")
        data = json.loads(path.read_text(encoding="utf-8"))
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


def _pattern_signature(detail):
    """Identidad, fuente, coordenadas y orientación, en orden estable."""
    return tuple(sorted((
        item["piece_id"], item["unit_index"], item["source"], item["material_id"],
        item["physical_unit_index"], item["x_mm"], item["y_mm"], item["rotation_deg"],
    ) for item in detail["placements"]))


def _functional_score(row):
    sources = int(row["remnants_used"]) + int(row["sheets_used"])
    return (int(row["placed_units"]), -sources, -int(row["sheets_used"]),
            Decimal(row["utilization_pct"]),
            -Decimal(row["waste"]), Decimal(row["recoverable_area"]))


def _classify_case(case_rows, case_details):
    """Apply the predeclared exclusive A-E precedence to one benchmark case."""
    by_method = {row["method"]: row for row in case_rows}
    baselines = [by_method[name] for name in ("FF", "BF", "WF")]
    best = max(baselines, key=_functional_score)
    pair = by_method["Pair-Block-v2"]
    fastest = min(float(row["runtime_ms"]) for row in baselines)
    ratio = float(pair["runtime_ms"]) / fastest if fastest else float("inf")
    pair_sources = int(pair["remnants_used"]) + int(pair["sheets_used"])
    best_sources = int(best["remnants_used"]) + int(best["sheets_used"])
    worse = (
        int(pair["placed_units"]) < int(best["placed_units"])
        or pair_sources > best_sources
        or (pair_sources == best_sources
            and int(pair["sheets_used"]) > int(best["sheets_used"]))
        or Decimal(pair["utilization_pct"]) < Decimal(best["utilization_pct"])
        or Decimal(pair["waste"]) > Decimal(best["waste"])
        or Decimal(pair["recoverable_area"]) < Decimal(best["recoverable_area"])
    )
    improved = (
        pair_sources < best_sources
        or (pair_sources == best_sources
            and int(pair["sheets_used"]) < int(best["sheets_used"]))
        or
        Decimal(pair["utilization_pct"]) > Decimal(best["utilization_pct"])
        or Decimal(pair["waste"]) < Decimal(best["waste"])
        or Decimal(pair["recoverable_area"]) > Decimal(best["recoverable_area"])
    )
    if worse or ratio > 10:
        code = "E"
        reason = ("empeora al menos una métrica funcional" if worse else
                  "runtime total supera 10× al baseline más rápido")
    elif improved and int(pair["placed_units"]) >= int(best["placed_units"]) and pair_sources <= best_sources:
        code, reason = "C", "mejora una métrica funcional sin perder cobertura ni abrir más fuentes"
    else:
        metrics_tie = tuple(pair[key] for key in (
            "placed_units", "remnants_used", "sheets_used", "utilization_pct",
            "waste", "recoverable_area")) == tuple(best[key] for key in (
            "placed_units", "remnants_used", "sheets_used", "utilization_pct",
            "waste", "recoverable_area"))
        detail_by_method = {item["method"]: item for item in case_details}
        baseline_pattern = _pattern_signature(detail_by_method[best["method"]])
        changed = _pattern_signature(detail_by_method["Pair-Block-v2"]) != baseline_pattern
        block_trace = detail_by_method["Pair-Block-v2"].get("block_trace", {})
        if not metrics_tie:
            code, reason = "E", "métricas funcionales cambiaron sin mejora neta"
        elif not block_trace.get("placed_blocks"):
            code, reason = "D", "no se colocó ningún bloque y no aplica E"
        elif changed:
            code, reason = "B", "bloque colocado; cambió el patrón y las métricas funcionales empataron"
        else:
            code, reason = "A", "bloque colocado; patrón y métricas funcionales empataron"
    return {"classification": code, "reason": reason,
            "best_baseline": best["method"], "fastest_baseline_ms": fastest,
            "runtime_ratio_fastest_baseline": ratio}


def run_one(case_id, method_name, optimizer_class):
    """Ejecuta un caso de forma aislada y devuelve fila y traza serializables."""
    data, problem = load_case(case_id)
    start = time.perf_counter_ns()
    trace = None
    if method_name.startswith("Pair-Block"):
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
        "classification": "", "classification_reason": "", "best_baseline": "",
        "runtime_ratio_fastest_baseline": "",
        "candidate_pairs": trace.candidate_pairs if trace else "",
        "compatible_pairs": trace.compatible_pairs if trace else "",
        "filtered_pairs": trace.filtered_pairs if trace else "",
        "geometrically_checked_pairs": trace.geometrically_checked_pairs if trace else "",
        "orientation_combinations_theoretical": trace.orientation_combinations_theoretical if trace else "",
        "orientation_combinations_after_symmetry": trace.orientation_combinations_after_symmetry if trace else "",
        "orientation_combinations_after_bounds": trace.orientation_combinations_after_bounds if trace else "",
        "orientation_combinations_after_phase": trace.orientation_combinations_after_phase if trace else "",
        "orientation_combinations_pruned": trace.orientation_combinations_pruned if trace else "",
        "orientation_combinations_pruned_by_compatibility": trace.orientation_combinations_pruned_by_compatibility if trace else "",
        "orientation_combinations_pruned_by_symmetry": trace.orientation_combinations_pruned_by_symmetry if trace else "",
        "orientation_combinations_pruned_by_bounds": trace.orientation_combinations_pruned_by_bounds if trace else "",
        "orientation_combinations_pruned_by_phase": trace.orientation_combinations_pruned_by_phase if trace else "",
        "orientation_combinations_pruned_by_best_bound": trace.orientation_combinations_pruned_by_best_bound if trace else "",
        "orientation_combinations_evaluated": trace.orientation_combinations_evaluated if trace else "",
        "relative_positions_theoretical": trace.relative_positions_theoretical if trace else "",
        "relative_positions_pruned": trace.relative_positions_pruned if trace else "",
        "relative_positions_checked": trace.relative_positions_checked if trace else "",
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
            "compatible_pairs": trace.compatible_pairs,
            "geometrically_checked_pairs": trace.geometrically_checked_pairs,
            "orientation_combinations_theoretical": trace.orientation_combinations_theoretical,
            "orientation_combinations_after_symmetry": trace.orientation_combinations_after_symmetry,
            "orientation_combinations_after_bounds": trace.orientation_combinations_after_bounds,
            "orientation_combinations_after_phase": trace.orientation_combinations_after_phase,
            "orientation_combinations_pruned": trace.orientation_combinations_pruned,
            "orientation_combinations_pruned_by_compatibility": trace.orientation_combinations_pruned_by_compatibility,
            "orientation_combinations_pruned_by_symmetry": trace.orientation_combinations_pruned_by_symmetry,
            "orientation_combinations_pruned_by_bounds": trace.orientation_combinations_pruned_by_bounds,
            "orientation_combinations_pruned_by_phase": trace.orientation_combinations_pruned_by_phase,
            "orientation_combinations_pruned_by_best_bound": trace.orientation_combinations_pruned_by_best_bound,
            "orientation_combinations_evaluated": trace.orientation_combinations_evaluated,
            "relative_positions_theoretical": trace.relative_positions_theoretical,
            "relative_positions_pruned": trace.relative_positions_pruned,
            "relative_positions_checked": trace.relative_positions_checked,
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
    case_ids = (*CASES, BLOCK_CASE, *DIAGNOSTIC_CASES)
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
    classifications = {}
    for case_id in case_ids:
        case_rows = [row for row in rows if row["case"] == case_id]
        case_details = [item for item in details if item["case"] == case_id]
        classification = _classify_case(case_rows, case_details)
        classifications[case_id] = classification
        for row in case_rows:
            if row["method"] == "Pair-Block-v2":
                row.update(classification=classification["classification"],
                           classification_reason=classification["reason"],
                           best_baseline=classification["best_baseline"],
                           runtime_ratio_fastest_baseline=round(
                               classification["runtime_ratio_fastest_baseline"], 3))
        for item in case_details:
            if item["method"] == "Pair-Block-v2":
                item["classification"] = classification
    determinism = {}
    for case_id in case_ids:
        signatures, runtimes = [], []
        for _ in range(3):
            row, detail = run_one(case_id, "Pair-Block-v2", BlockPackingExperimental)
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
    csv_path = OUTPUT / "sp004_block_v2_results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    payload = {
        "spike": "SP-004", "candidate": "Pair-Block v2 experimental adaptation",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime": {"python": sys.version, "platform": sys.platform},
        "official_fixtures": list(CASES), "non_official_cases": [BLOCK_CASE, *DIAGNOSTIC_CASES],
        "method_order": [name for name, _ in METHODS], "results": details,
        "classifications": classifications, "determinism": determinism,
    }
    json_path = OUTPUT / "sp004_block_v2_trace.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(csv_path)
    print(json_path)


if __name__ == "__main__":
    main()
