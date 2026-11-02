"""Benchmark serial de pedidos HF realistas congelados antes de las heuristicas."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import statistics
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from experiments.optimization.hole_filling.lab import CASE_DIR, REALISTIC_LABEL, read_case  # noqa: E402
from experiments.optimization.hole_filling.optimizer import (  # noqa: E402
    metric_values,
    placement_signature,
    run_baseline,
    run_hole_filling,
)
from experiments.optimization.hole_filling.visualize import render_pocket_placement  # noqa: E402


CASE_IDS = tuple(f"HF-REALISTIC-{index:03d}" for index in range(1, 4))
METHODS = ("FF", "BF", "WF")
HF_REPETITIONS = 3
RUNTIME_LIMIT_RATIO = Decimal(10)
OUTPUT = ROOT / "docs/evidence/sprint-02/SP-004/hole-filling"
FIGURES = Path(__file__).resolve().parent / "figures"


def _official_metrics(run: dict) -> dict:
    values = metric_values(run)
    materials = values.get("materials_used", [])
    remnants = {
        (item["source"], item["material_id"], item["physical_unit_index"])
        for item in materials if item["source"] == "RETAZO"
    }
    return {
        "requested_units": int(values["requested"]),
        "placed_units": int(values["placed"]),
        "unplaced_units": int(values["unplaced"]),
        "remnants_used": len(remnants),
        "sheets_used": int(values["new_sheets_used"]),
        "utilization_pct": str(values["utilization_pct"]),
        "waste_mm2": str(values["waste_mm2"]),
        "recoverable_area_mm2": str(values["recoverable_remnant_mm2"]),
        "runtime_ms": round(run["total_ms"], 4),
    }


def _metric_tuple(record: dict) -> tuple:
    values = record["official_metrics"]
    return (
        values["placed_units"],
        -values["sheets_used"],
        Decimal(values["utilization_pct"]),
        -Decimal(values["waste_mm2"]),
        Decimal(values["recoverable_area_mm2"]),
    )


def _source_switches(placements: list[dict]) -> int:
    sources = [item["source"] for item in placements]
    return sum(left != right for left, right in zip(sources, sources[1:]))


def _run_record(run: dict, *, method: str, is_hf: bool) -> dict:
    diagnostics = run["diagnostics"]
    selected_by_piece = {
        (int(item["piece_id"]), int(item["unit_index"])): item
        for item in diagnostics.get("selected_pockets", [])
    }
    placements = []
    for placement in run["result"].placements:
        key = placement.piece.piece_id, placement.piece.unit_index
        pocket = selected_by_piece.get(key) if is_hf else None
        row = {
            "piece_id": placement.piece.piece_id,
            "unit_index": placement.piece.unit_index,
            "source": placement.stock.source.value,
            "material_id": placement.stock.material_id,
            "physical_unit_index": placement.stock.physical_unit_index,
            "rotation_deg": str(placement.rotation_deg),
            "x_mm": str(placement.x_mm),
            "y_mm": str(placement.y_mm),
            "geometry": dict(placement.geometry),
            "decision": "pocket" if pocket else ("fallback" if is_hf else "baseline"),
            "pocket": pocket,
        }
        placements.append(row)

    options_by_decision = diagnostics.get("pocket_options_by_decision", [])
    pocket_candidates_checked = sum(int(value) for value in options_by_decision)
    fallback_count = int(diagnostics.get("fallback_placements", 0)) + int(diagnostics.get("fallback_unplaced", 0))
    component_labeling_ms = float(diagnostics.get("pocket_detection_ms", 0))
    anchor_map_generation_ms = float(diagnostics.get("anchor_map_generation_ms", 0))
    return {
        "method": method,
        "official_metrics": _official_metrics(run),
        "placements": placements,
        "source_switches": _source_switches(placements),
        "pockets_detected": int(diagnostics.get("pocket_components_detected", 0)),
        "pockets_used": int(diagnostics.get("pockets_used", 0)),
        "pocket_candidates_checked": pocket_candidates_checked,
        "pieces_placed_in_pockets": int(diagnostics.get("pockets_used", 0)),
        "pocket_detection_ms": round(component_labeling_ms + anchor_map_generation_ms, 4),
        "pocket_component_labeling_ms": round(component_labeling_ms, 4),
        "pocket_placement_ms": round(float(diagnostics.get("pocket_placement_ms", 0)), 4),
        "anchor_map_generation_ms": round(anchor_map_generation_ms, 4),
        "fallback_search_ms": round(float(diagnostics.get("fallback_search_ms", 0)), 4),
        "fallback_count": fallback_count,
        "fallback_placements": int(diagnostics.get("fallback_placements", 0)),
        "fallback_unplaced": int(diagnostics.get("fallback_unplaced", 0)),
        "candidate_orientations_scanned": int(diagnostics.get("candidate_orientations_scanned", 0)),
        "geometric_positions_evaluated": int(diagnostics.get("geometric_positions_evaluated", 0)),
        "exact_geometry_checks": int(diagnostics.get("exact_geometry_checks", 0)),
        "pocket_options_by_decision": list(options_by_decision),
        "selected_pockets": list(diagnostics.get("selected_pockets", [])),
    }


def _functional_changes(actual: dict, baseline: dict) -> tuple[list[str], list[str]]:
    higher = ("placed_units", "utilization_pct", "recoverable_area_mm2")
    lower = ("sheets_used", "waste_mm2")
    improved, worsened = [], []
    for name in higher:
        left, right = Decimal(str(actual[name])), Decimal(str(baseline[name]))
        if left > right:
            improved.append(name)
        elif left < right:
            worsened.append(name)
    for name in lower:
        left, right = Decimal(str(actual[name])), Decimal(str(baseline[name]))
        if left < right:
            improved.append(name)
        elif left > right:
            worsened.append(name)
    return improved, worsened


def _classify(hf: dict, baselines: list[dict], fastest_ms: float) -> dict:
    best = max(baselines, key=_metric_tuple)
    actual = hf["official_metrics"]
    reference = best["official_metrics"]
    improved, worsened = _functional_changes(actual, reference)
    hf_signature = hf["functional_signature"]
    changed_from_all = all(hf_signature != item["functional_signature"] for item in baselines)
    ratio = actual["runtime_ms"] / fastest_ms if fastest_ms else float("inf")
    used = hf["pockets_used"] > 0

    if ratio > float(RUNTIME_LIMIT_RATIO):
        category = "E"
    elif worsened:
        category = "D"
    elif used and changed_from_all and improved:
        category = "C"
    elif used and changed_from_all:
        category = "B"
    else:
        category = "A"
    return {
        "category": category,
        "best_baseline": best["method"],
        "fastest_baseline_ms": round(fastest_ms, 4),
        "runtime_ratio_vs_fastest_baseline": round(ratio, 4),
        "pattern_changed_from_all_baselines": changed_from_all,
        "improved_fields": improved,
        "worsened_fields": worsened,
        "pocket_used": used,
    }


def _freeze_metadata(case_id: str) -> dict:
    case_path = CASE_DIR / f"{case_id}.json"
    actual_hash = hashlib.sha256(case_path.read_bytes()).hexdigest()
    intent = (CASE_DIR / "HF-REALISTIC-INTENT.md").read_text(encoding="utf-8")
    match = re.search(rf"{case_id}.*?([0-9a-f]{{64}})", intent)
    if not match or match.group(1) != actual_hash:
        raise RuntimeError(f"El hash congelado no coincide con {case_id}.")
    commit = subprocess.check_output(
        ["git", "log", "-1", "--format=%H", "--", case_path.relative_to(ROOT).as_posix()],
        cwd=ROOT, text=True,
    ).strip()
    return {"fixture_sha256": actual_hash, "fixture_freeze_commit": commit}


def _determinism_signature(run: dict) -> str:
    payload = {
        "placements": placement_signature(run, pending_only=True),
        "metrics": _official_metrics(run),
        "selected_pockets": run["diagnostics"].get("selected_pockets", []),
        "pocket_options_by_decision": run["diagnostics"].get("pocket_options_by_decision", []),
    }
    payload["metrics"].pop("runtime_ms", None)
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)


def _case_run(case_id: str) -> tuple[dict, list[dict]]:
    case = read_case(case_id)
    if case["label"] != REALISTIC_LABEL:
        raise ValueError(f"La etiqueta no corresponde al pedido realista {case_id}.")
    freeze = _freeze_metadata(case_id)
    print(f"{case_id}: fixture congelado; inicio de FF, BF, WF y HF secuenciales", flush=True)

    baseline_records = []
    for method in METHODS:
        run = run_baseline(case_id, method)
        record = _run_record(run, method=method, is_hf=False)
        record["functional_signature"] = placement_signature(run, pending_only=True)
        baseline_records.append(record)
        print(f"  {method}: {record['official_metrics']['runtime_ms']:.2f} ms", flush=True)
        del run

    hf_records, hf_signatures = [], []
    figure_paths = []
    for repetition in range(1, HF_REPETITIONS + 1):
        print(f"  HF repeticion {repetition}/{HF_REPETITIONS}", flush=True)
        run = run_hole_filling(case_id)
        record = _run_record(run, method="HF", is_hf=True)
        signature = _determinism_signature(run)
        record["functional_signature"] = placement_signature(run, pending_only=True)
        hf_signatures.append(signature)
        hf_records.append(record)
        if repetition == 1 and run["diagnostics"]["pockets_used"]:
            for index, context in enumerate(run["pocket_placement_contexts"], start=1):
                layout, anchor_map, selected_anchor, pending_mask = context
                path = FIGURES / f"{case_id}-pocket-{index:02d}.svg"
                render_pocket_placement(
                    layout, anchor_map, selected_anchor, pending_mask,
                    path, f"{case_id} | pocket {index}",
                )
                figure_paths.append(path.relative_to(ROOT).as_posix())
        print(f"    HF: {record['official_metrics']['runtime_ms']:.2f} ms; "
              f"pockets {record['pockets_detected']}/{record['pockets_used']}", flush=True)
        del run

    hf_deterministic = len(set(hf_signatures)) == 1
    hf_median_ms = statistics.median(item["official_metrics"]["runtime_ms"] for item in hf_records)
    fastest_baseline_ms = min(item["official_metrics"]["runtime_ms"] for item in baseline_records)
    hf_summary = dict(hf_records[0])
    hf_summary["official_metrics"] = dict(hf_records[0]["official_metrics"])
    hf_summary["official_metrics"]["runtime_ms"] = round(hf_median_ms, 4)
    classification = _classify(hf_summary, baseline_records, fastest_baseline_ms)
    baseline_comparison = [
        {key: value for key, value in record.items() if key != "functional_signature"}
        for record in baseline_records
    ]
    clean_hf_repetitions = [
        {key: value for key, value in record.items() if key != "functional_signature"}
        for record in hf_records
    ]
    clean_hf_summary = {
        key: value for key, value in hf_summary.items() if key != "functional_signature"
    }
    trace = {
        "case_id": case_id,
        "label": case["label"],
        "fixture_freeze": freeze,
        "requested_units": len(case["pieces"]),
        "config": case["config"],
        "material": case["material"],
        "stocks": case["stocks"],
        "pieces": case["pieces"],
        "methods_order": [*METHODS, "HF x3"],
        "classification": classification,
        "deterministic": hf_deterministic,
        "hf_repetitions": clean_hf_repetitions,
        "baselines": baseline_comparison,
        "hole_filling": clean_hf_summary,
        "figures": figure_paths,
    }
    rows = []
    for record in baseline_comparison:
        rows.append(_csv_row(case_id, record, ""))
    rows.append(_csv_row(case_id, clean_hf_summary, classification["category"]))
    return trace, rows


def _csv_row(case_id: str, record: dict, classification: str) -> dict:
    metrics = record["official_metrics"]
    return {
        "case_id": case_id,
        "method": record["method"],
        "classification": classification,
        **metrics,
        "pockets_detected": record["pockets_detected"],
        "pockets_used": record["pockets_used"],
        "pocket_candidates_checked": record["pocket_candidates_checked"],
        "pieces_placed_in_pockets": record["pieces_placed_in_pockets"],
        "pocket_detection_ms": record["pocket_detection_ms"],
        "pocket_component_labeling_ms": record["pocket_component_labeling_ms"],
        "anchor_map_generation_ms": record["anchor_map_generation_ms"],
        "pocket_placement_ms": record["pocket_placement_ms"],
        "fallback_count": record["fallback_count"],
        "source_switches": record["source_switches"],
    }


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    cases, rows = [], []
    for case_id in CASE_IDS:
        trace, case_rows = _case_run(case_id)
        cases.append(trace)
        rows.extend(case_rows)

    summary = {
        "label": REALISTIC_LABEL,
        "execution": "sequential; no multiprocessing",
        "hf_repetitions_per_case": HF_REPETITIONS,
        "classification_rule": "HF-REALISTIC-INTENT.md; E if HF > 10x fastest baseline",
        "cases": cases,
    }
    (OUTPUT / "sp004_hf_realistic_trace.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    columns = list(rows[0])
    with (OUTPUT / "sp004_hf_realistic_results.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Resultados: {OUTPUT / 'sp004_hf_realistic_results.csv'}", flush=True)
    print(f"Trazas: {OUTPUT / 'sp004_hf_realistic_trace.json'}", flush=True)


if __name__ == "__main__":
    main()
