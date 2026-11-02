"""Benchmark formal gated tras VIABLE: EXP-SMALL/MEDIUM/COMPLEX in series."""
import csv
import json
import statistics
import sys
from pathlib import Path
from time import perf_counter_ns

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from app.modules.optimization.domain.best_fit import BestFitOptimizer  # noqa: E402
from app.modules.optimization.domain.first_fit import FirstFitOptimizer  # noqa: E402
from app.modules.optimization.domain.metrics import calculate_metrics  # noqa: E402
from app.modules.optimization.domain.worst_fit import WorstFitOptimizer  # noqa: E402
from experiments.optimization.hole_filling.optimizer import (  # noqa: E402
    metric_values,
    placement_signature,
    run_hole_filling_problem,
)
from experiments.optimization.hole_filling.run_benchmark import (  # noqa: E402
    _classification,
    _trace_run,
    _validate_placements,
)
from experiments.optimization.hole_filling.visualize import render_anchor_map  # noqa: E402
from experiments.optimization.loader import load_problem  # noqa: E402
from experiments.optimization.hole_filling.lab import DIAGNOSTIC_LABEL, setup_from_problem  # noqa: E402


CASE_IDS = ("EXP-SMALL-001", "EXP-MEDIUM-001", "EXP-COMPLEX-001")
BASELINES = (("FF", FirstFitOptimizer), ("BF", BestFitOptimizer), ("WF", WorstFitOptimizer))
REPETITIONS = 3
OUTPUT = ROOT / "docs/evidence/sprint-02/SP-004/hole-filling"
FIGURES = Path(__file__).resolve().parent / "figures"


def _run_official_baseline(case_id, method, factory):
    problem = load_problem(case_id)
    started = perf_counter_ns()
    result = factory().optimize(problem)
    result, residuals = calculate_metrics(result, 1, 1)
    total_ms = (perf_counter_ns() - started) / 1_000_000
    setup = setup_from_problem(problem, case_id)
    return {
        "case_id": case_id,
        "method": method,
        "setup": setup,
        "result": result,
        "residuals": residuals,
        "total_ms": total_ms,
        "diagnostics": {},
        "anchor_maps_used": (),
    }


def _csv_row(case_id, method, run, category=None):
    values = metric_values(run)
    diag = run["diagnostics"]
    placements = run["result"].placements
    return {
        "case_id": case_id,
        "method": method,
        "classification": category or "",
        "requested": values["requested"],
        "placed": values["placed"],
        "unplaced": values["unplaced"],
        "new_sheets_used": values["new_sheets_used"],
        "utilization_pct": values["utilization_pct"],
        "waste_mm2": values["waste_mm2"],
        "recoverable_remnant_mm2": values["recoverable_remnant_mm2"],
        "materials_used": json.dumps(values.get("materials_used", []), ensure_ascii=False),
        "total_ms": round(run["total_ms"], 4),
        "setup_ms": round(diag.get("setup_ms", 0), 4),
        "pocket_detection_ms": round(diag.get("pocket_detection_ms", 0), 4),
        "placement_search_ms": round(diag.get("placement_search_ms", 0), 4),
        "candidate_orientations_scanned": diag.get("candidate_orientations_scanned", 0),
        "geometric_positions_evaluated": diag.get("geometric_positions_evaluated", 0),
        "exact_geometry_checks": diag.get("exact_geometry_checks", 0),
        "pocket_components_detected": diag.get("pocket_components_detected", 0),
        "pockets_used": diag.get("pockets_used", 0),
        "fallback_placements": diag.get("fallback_placements", 0),
        "fallback_unplaced": diag.get("fallback_unplaced", 0),
        "placements_json": json.dumps([
            {"piece_id": p.piece.piece_id, "unit_index": p.piece.unit_index,
             "source": p.stock.source.value, "material_id": p.stock.material_id,
             "x_mm": str(p.x_mm), "y_mm": str(p.y_mm),
             "rotation_deg": str(p.rotation_deg)} for p in placements
        ], ensure_ascii=False),
    }


def run_case(case_id):
    baselines = [_run_official_baseline(case_id, method, factory) for method, factory in BASELINES]
    hf_runs = [run_hole_filling_problem(load_problem(case_id), case_id) for _ in range(REPETITIONS)]
    signatures = [placement_signature(run, pending_only=True) for run in hf_runs]
    decisions = [json.dumps(run["diagnostics"]["selected_pockets"], sort_keys=True)
                 for run in hf_runs]
    deterministic = len(set(signatures)) == 1 and len(set(decisions)) == 1
    hf = hf_runs[0]
    hf["total_ms"] = statistics.median(run["total_ms"] for run in hf_runs)
    hf["diagnostics"]["total_ms"] = hf["total_ms"]
    fastest = min(run["total_ms"] for run in baselines)
    classification = _classification(hf, baselines, fastest)
    placement_checks = sum(_validate_placements(run) for run in [*baselines, *hf_runs])
    for index, (anchor_map, selected_anchor) in enumerate(hf["anchor_maps_used"], start=1):
        render_anchor_map(anchor_map, FIGURES / f"{case_id}-used-{index:02d}-anchors.svg",
                          f"{case_id} — {DIAGNOSTIC_LABEL}", selected_anchor=selected_anchor)
    return {
        "case_id": case_id,
        "classification": classification,
        "deterministic": deterministic,
        "placement_rule_checks": placement_checks,
        "baselines": [_trace_run(run) for run in baselines],
        "hf_repetitions": [_trace_run(run) for run in hf_runs],
        "hole_filling": _trace_run(hf),
    }, [*(_csv_row(case_id, run["method"], run) for run in baselines),
        _csv_row(case_id, "Hole-Filling", hf, classification["category"])]


def main():
    cases, rows = [], []
    for case_id in CASE_IDS:
        trace, csv_rows = run_case(case_id)
        cases.append(trace)
        rows.extend(csv_rows)
    functional_go = any(case["classification"]["category"] == "C" for case in cases)
    no_cost_e = all(case["classification"]["category"] != "E" for case in cases)
    deterministic = all(case["deterministic"] for case in cases)
    decision = "GO CANDIDATO PARA SIGUIENTE REVISIÓN" if functional_go and no_cost_e and deterministic else "NO-GO TA-042"
    payload = {
        "scope": "EXP-SMALL-001 / EXP-MEDIUM-001 / EXP-COMPLEX-001, solo después de VIABLE diagnóstico",
        "methods": ["FF", "BF", "WF", "Hole-Filling"],
        "hf_repetitions_per_case": REPETITIONS,
        "decision_ta042": decision,
        "cases": cases,
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "sp004_hole_filling_official_trace.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if rows:
        with (OUTPUT / "sp004_hole_filling_official_results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps({
        "decision_ta042": decision,
        "cases": [{"case_id": case["case_id"],
                   "classification": case["classification"]["category"],
                   "deterministic": case["deterministic"],
                   "pockets_detected": case["hole_filling"]["diagnostics"].get("pocket_components_detected", 0),
                   "pockets_used": case["hole_filling"]["diagnostics"].get("pockets_used", 0),
                   "runtime_ratio": round(case["classification"]["runtime_ratio_vs_fastest_baseline"], 3)}
                  for case in cases],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
