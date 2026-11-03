"""Comparación secuencial de diagnósticos FF/BF/WF/HF y evidencia local."""
import csv
import json
import statistics
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from app.modules.optimization.domain.packing import _empty_layout  # noqa: E402
from experiments.optimization.hole_filling.lab import DIAGNOSTIC_LABEL  # noqa: E402
from experiments.optimization.hole_filling.optimizer import (  # noqa: E402
    metric_values,
    placement_signature,
    run_baseline,
    run_hole_filling,
)
from experiments.optimization.hole_filling.visualize import render_anchor_map  # noqa: E402


CASE_IDS = tuple(f"HF-DIAGNOSTIC-{index:03d}" for index in range(1, 5))
METHODS = ("FF", "BF", "WF")
REPETITIONS = 3
FIGURES = Path(__file__).resolve().parent / "figures"
OUTPUT = ROOT / "docs/evidence/sprint-02/SP-004/hole-filling"


def _metric_tuple(run):
    values = metric_values(run)
    return (
        int(values["placed"]),
        -int(values["new_sheets_used"]),
        Decimal(values["utilization_pct"]),
        -Decimal(values["waste_mm2"]),
        Decimal(values["recoverable_remnant_mm2"]),
    )


def _metric_changes(actual, reference):
    comparisons = {
        "placed": (int(actual["placed"]), int(reference["placed"]), "higher"),
        "new_sheets_used": (int(actual["new_sheets_used"]), int(reference["new_sheets_used"]), "lower"),
        "utilization_pct": (Decimal(actual["utilization_pct"]), Decimal(reference["utilization_pct"]), "higher"),
        "waste_mm2": (Decimal(actual["waste_mm2"]), Decimal(reference["waste_mm2"]), "lower"),
        "recoverable_remnant_mm2": (
            Decimal(actual["recoverable_remnant_mm2"]),
            Decimal(reference["recoverable_remnant_mm2"]),
            "higher",
        ),
    }
    improved, worsened = [], []
    for name, (value, baseline, direction) in comparisons.items():
        is_better = value > baseline if direction == "higher" else value < baseline
        is_worse = value < baseline if direction == "higher" else value > baseline
        if is_better:
            improved.append(name)
        if is_worse:
            worsened.append(name)
    return improved, worsened


def _functional_equal(left, right):
    fields = ("placed", "unplaced", "new_sheets_used", "utilization_pct", "waste_mm2", "recoverable_remnant_mm2")
    a, b = metric_values(left), metric_values(right)
    return all(a[field] == b[field] for field in fields)


def _validate_placements(run):
    setup = run["setup"]
    layouts = {}
    checks = 0
    for placement in run["result"].placements:
        stock = placement.stock
        layout = layouts.get(stock.identity)
        if layout is None:
            layout = _empty_layout(setup.prepared.material(stock), setup.problem.config)
        oriented = next((item for item in setup.prepared.orientations(placement.piece)
                         if item.orientation.rotation_deg == placement.rotation_deg), None)
        if oriented is None:
            raise AssertionError(f"Orientación inválida para la pieza {placement.piece.piece_id}.")
        row_value = placement.y_mm / setup.problem.config.resolution_mm
        column_value = placement.x_mm / setup.problem.config.resolution_mm
        if row_value != row_value.to_integral_value() or column_value != column_value.to_integral_value():
            raise AssertionError("El placement no está alineado al raster existente.")
        row, column = int(row_value), int(column_value)
        check = layout.check(oriented.orientation.mask, row, column)
        checks += 1
        if not check.is_valid:
            raise AssertionError(
                f"Placement inválido de {placement.piece.piece_id}: {check.issue.value}."
            )
        layouts[stock.identity] = layout.place(oriented.orientation.mask, row, column)
    return checks


def _classification(hf, baselines, fastest_baseline_ms):
    metrics = metric_values(hf)
    best_baseline = max(baselines, key=_metric_tuple)
    best_metrics = metric_values(best_baseline)
    improved, worsened = _metric_changes(metrics, best_metrics)
    hf_signature = placement_signature(hf, pending_only=True)
    pattern_changed = all(hf_signature != placement_signature(base, pending_only=True) for base in baselines)
    used = hf["diagnostics"]["pockets_used"] > 0
    ratio = hf["total_ms"] / fastest_baseline_ms if fastest_baseline_ms else float("inf")
    if ratio > 10:
        category = "E"
    elif worsened:
        category = "D"
    elif used and pattern_changed and improved:
        category = "C"
    elif used and pattern_changed and not improved:
        category = "B"
    elif not pattern_changed and any(_functional_equal(hf, base) for base in baselines):
        category = "A"
    elif pattern_changed and not used and not worsened:
        category = "A"
    else:
        category = "D"
    return {
        "category": category,
        "best_baseline": best_baseline["method"],
        "improved_fields": improved,
        "worsened_fields": worsened,
        "pattern_changed_from_all_baselines": pattern_changed,
        "pocket_used": used,
        "runtime_ratio_vs_fastest_baseline": ratio,
    }


def _placement_rows(run):
    roles = run["setup"].roles_by_id
    return [
        {
            "piece_id": placement.piece.piece_id,
            "unit_index": placement.piece.unit_index,
            "role": roles[placement.piece.piece_id],
            "source": placement.stock.source.value,
            "material_id": placement.stock.material_id,
            "physical_unit_index": placement.stock.physical_unit_index,
            "x_mm": str(placement.x_mm),
            "y_mm": str(placement.y_mm),
            "rotation_deg": str(placement.rotation_deg),
            "geometry": dict(placement.geometry),
        }
        for placement in run["result"].placements
    ]


def _trace_run(run):
    return {
        "method": run["method"],
        "total_ms": run["total_ms"],
        "metrics": metric_values(run),
        "placements": _placement_rows(run),
        "pending_signature": placement_signature(run, pending_only=True),
        "diagnostics": run["diagnostics"],
    }


def _csv_row(case_id, method, run, classification=None):
    metrics = metric_values(run)
    diagnostics = run["diagnostics"]
    seeds = sum(role == "seed" for role in run["setup"].roles_by_id.values())
    return {
        "case_id": case_id,
        "label": DIAGNOSTIC_LABEL,
        "method": method,
        "classification": classification or "",
        "requested": metrics["requested"],
        "placed": metrics["placed"],
        "unplaced": metrics["unplaced"],
        "seed_pieces": seeds,
        "new_sheets_used": metrics["new_sheets_used"],
        "materials_used": json.dumps(metrics.get("materials_used", []), ensure_ascii=False),
        "utilization_pct": metrics["utilization_pct"],
        "waste_mm2": metrics["waste_mm2"],
        "recoverable_remnant_mm2": metrics["recoverable_remnant_mm2"],
        "total_ms": round(run["total_ms"], 4),
        "setup_ms": round(diagnostics.get("setup_ms", 0), 4),
        "pocket_detection_ms": round(diagnostics.get("pocket_detection_ms", 0), 4),
        "placement_search_ms": round(diagnostics.get("placement_search_ms", 0), 4),
        "candidate_orientations_scanned": diagnostics.get("candidate_orientations_scanned", 0),
        "geometric_positions_evaluated": diagnostics.get("geometric_positions_evaluated", 0),
        "exact_geometry_checks": diagnostics.get("exact_geometry_checks", 0),
        "pocket_components_detected": diagnostics.get("pocket_components_detected", 0),
        "pockets_used": diagnostics.get("pockets_used", 0),
        "fallback_placements": diagnostics.get("fallback_placements", 0),
        "fallback_unplaced": diagnostics.get("fallback_unplaced", 0),
        "placements_json": json.dumps(_placement_rows(run), ensure_ascii=False),
    }


def run_case(case_id):
    baselines = [run_baseline(case_id, method) for method in METHODS]
    hf_repetitions = [run_hole_filling(case_id) for _ in range(REPETITIONS)]
    signatures = [placement_signature(run, pending_only=True) for run in hf_repetitions]
    decision_signatures = [
        (run["diagnostics"]["candidate_orientations_scanned"],
         run["diagnostics"]["geometric_positions_evaluated"],
         run["diagnostics"]["pocket_components_detected"],
         run["diagnostics"]["pockets_used"],
         tuple(json.dumps(item, sort_keys=True, ensure_ascii=False)
               for item in run["diagnostics"]["selected_pockets"]))
        for run in hf_repetitions
    ]
    deterministic = len(set(signatures)) == 1 and len(set(decision_signatures)) == 1
    hf = hf_repetitions[0]
    hf["total_ms"] = statistics.median(run["total_ms"] for run in hf_repetitions)
    hf["diagnostics"]["total_ms"] = hf["total_ms"]
    fastest = min(run["total_ms"] for run in baselines)
    classification = _classification(hf, baselines, fastest)
    placement_checks = sum(_validate_placements(run) for run in [*baselines, *hf_repetitions])
    for index, (anchor_map, selected_anchor) in enumerate(hf["anchor_maps_used"], start=1):
        render_anchor_map(
            anchor_map,
            FIGURES / f"{case_id}-used-{index:02d}-anchors.svg",
            DIAGNOSTIC_LABEL,
            selected_anchor=selected_anchor,
        )
    return {
        "case_id": case_id,
        "label": DIAGNOSTIC_LABEL,
        "classification": classification,
        "deterministic": deterministic,
        "hf_repetitions": [_trace_run(run) for run in hf_repetitions],
        "baselines": [_trace_run(run) for run in baselines],
        "hole_filling": _trace_run(hf),
        "placement_rule_checks": placement_checks,
    }, [(_csv_row(case_id, run["method"], run) for run in baselines),
        _csv_row(case_id, "Hole-Filling", hf, classification["category"])]


def main():
    traces, rows = [], []
    for case_id in CASE_IDS:
        trace, row_groups = run_case(case_id)
        traces.append(trace)
        for group in row_groups:
            rows.extend(list(group) if not isinstance(group, dict) else [group])

    viable = (
        any(case["classification"]["category"] in ("B", "C") for case in traces)
        and all(case["classification"]["category"] != "E" for case in traces)
        and all(case["deterministic"] for case in traces)
    )
    result = {
        "label": DIAGNOSTIC_LABEL,
        "methods": [*METHODS, "Hole-Filling"],
        "hf_repetitions_per_case": REPETITIONS,
        "classification_rules": "HF-DIAGNOSTIC-INTENT.md",
        "mini_spike_decision": "VIABLE" if viable else "NO VIABLE",
        "official_benchmark_authorized_by_gate": viable,
        "cases": traces,
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "sp004_hole_filling_trace.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if rows:
        with (OUTPUT / "sp004_hole_filling_results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    summary = [{
        "case_id": case["case_id"],
        "classification": case["classification"]["category"],
        "best_baseline": case["classification"]["best_baseline"],
        "deterministic": case["deterministic"],
        "pockets_detected": case["hole_filling"]["diagnostics"].get("pocket_components_detected", 0),
        "pockets_used": case["hole_filling"]["diagnostics"].get("pockets_used", 0),
        "runtime_ratio": round(case["classification"]["runtime_ratio_vs_fastest_baseline"], 3),
    } for case in traces]
    print(json.dumps({"decision": result["mini_spike_decision"], "cases": summary}, indent=2))


if __name__ == "__main__":
    main()
