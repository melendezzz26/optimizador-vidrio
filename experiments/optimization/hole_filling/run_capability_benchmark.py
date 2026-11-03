"""Comparación definitiva serial del fixture controlado y congelado SP-004."""
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

from experiments.optimization.hole_filling.lab import CAPABILITY_LABEL, CASE_DIR, read_case  # noqa: E402
from experiments.optimization.hole_filling.optimizer import (  # noqa: E402
    placement_signature, run_baseline, run_hole_filling,
)
from experiments.optimization.hole_filling.run_realistic_benchmark import (  # noqa: E402
    _determinism_signature, _run_record,
)
from experiments.optimization.hole_filling.visualize import (  # noqa: E402
    render_capability_comparison, render_pocket_placement,
)


CASE_ID = "HF-CAPABILITY-001"
METHODS = ("FF", "BF", "WF")
HF_REPETITIONS = 3
OUTPUT = ROOT / "docs/evidence/sprint-02/SP-004/hole-filling"
FIGURES = ROOT / "experiments/optimization/hole_filling/figures"


def _freeze_metadata() -> dict:
    case_path = CASE_DIR / f"{CASE_ID}.json"
    actual_hash = hashlib.sha256(case_path.read_bytes()).hexdigest()
    intent = (CASE_DIR / "HF-CAPABILITY-INTENT.md").read_text(encoding="utf-8")
    match = re.search(r"SHA-256 del fixture final.*?([0-9a-f]{64})", intent)
    if not match or match.group(1) != actual_hash:
        raise RuntimeError("El fixture controlado difiere del hash congelado.")
    commit = subprocess.check_output(
        ["git", "log", "-1", "--format=%H", "--", case_path.relative_to(ROOT).as_posix()],
        cwd=ROOT, text=True,
    ).strip()
    if not commit:
        raise RuntimeError("No se encuentra el commit local que congeló el fixture.")
    return {"fixture_sha256": actual_hash, "fixture_freeze_commit": commit}


def _record(run: dict, method: str, is_hf: bool) -> dict:
    result = _run_record(run, method=method, is_hf=is_hf)
    for placement in result["placements"]:
        if run["setup"].roles_by_id[placement["piece_id"]] == "seed":
            placement["decision"] = "seed"
    return result


def _csv_row(record: dict) -> dict:
    return {
        "case_id": CASE_ID,
        "method": record["method"],
        **record["official_metrics"],
        "pockets_detected": record["pockets_detected"],
        "pockets_used": record["pockets_used"],
        "pocket_candidates_checked": record["pocket_candidates_checked"],
        "pieces_placed_in_pockets": record["pieces_placed_in_pockets"],
        "pocket_detection_ms": record["pocket_detection_ms"],
        "pocket_placement_ms": record["pocket_placement_ms"],
        "fallback_count": record["fallback_count"],
        "source_switches": record["source_switches"],
    }


def main() -> None:
    case = read_case(CASE_ID)
    if case["label"] != CAPABILITY_LABEL:
        raise ValueError("La etiqueta del caso controlado no coincide.")
    freeze = _freeze_metadata()
    print(f"{CASE_ID}: fixture congelado en {freeze['fixture_freeze_commit'][:8]}", flush=True)

    live_runs = {}
    baseline_records = []
    for method in METHODS:
        run = run_baseline(CASE_ID, method)
        live_runs[method] = run
        record = _record(run, method, False)
        baseline_records.append(record)
        print(f"{method}: {record['official_metrics']['runtime_ms']:.2f} ms", flush=True)

    hf_runs, hf_records, signatures = [], [], []
    for repetition in range(1, HF_REPETITIONS + 1):
        run = run_hole_filling(CASE_ID)
        record = _record(run, "HF", True)
        hf_runs.append(run)
        hf_records.append(record)
        signatures.append(_determinism_signature(run))
        print(
            f"HF {repetition}/{HF_REPETITIONS}: {record['official_metrics']['runtime_ms']:.2f} ms; "
            f"pockets {record['pockets_detected']}/{record['pockets_used']}",
            flush=True,
        )
    deterministic = len(set(signatures)) == 1
    hf_summary = dict(hf_records[0])
    hf_summary["official_metrics"] = dict(hf_records[0]["official_metrics"])
    hf_summary["official_metrics"]["runtime_ms"] = round(
        statistics.median(item["official_metrics"]["runtime_ms"] for item in hf_records), 4,
    )
    for field in (
        "pocket_detection_ms", "pocket_component_labeling_ms",
        "anchor_map_generation_ms", "pocket_placement_ms", "fallback_search_ms",
    ):
        hf_summary[field] = round(statistics.median(item[field] for item in hf_records), 4)

    hf_run = hf_runs[0]
    live_runs["HF"] = hf_run
    if not hf_run["pocket_placement_contexts"]:
        raise RuntimeError("La corrida definitiva no encontró un pocket usado.")
    FIGURES.mkdir(parents=True, exist_ok=True)
    stage_path = FIGURES / f"{CASE_ID}-pocket-stage.svg"
    layout, anchor_map, selected_anchor, pending_mask = hf_run["pocket_placement_contexts"][0]
    render_pocket_placement(
        layout, anchor_map, selected_anchor, pending_mask,
        stage_path, f"{CASE_ID} | antes y durante el pocket",
    )
    comparison_path = FIGURES / f"{CASE_ID}-comparison.svg"
    render_capability_comparison(live_runs, comparison_path)

    hf_piece = next(item for item in hf_summary["placements"] if item["piece_id"] == 11)
    baseline_piece = next(item for item in baseline_records[0]["placements"] if item["piece_id"] == 11)
    later_by_method = {
        record["method"]: next(item for item in record["placements"] if item["piece_id"] == 12)
        for record in (*baseline_records, hf_summary)
    }
    best_baseline_sheets = min(item["official_metrics"]["sheets_used"] for item in baseline_records)
    if hf_summary["official_metrics"]["sheets_used"] < best_baseline_sheets:
        demonstration_level = 1
    elif hf_summary["official_metrics"]["placed_units"] > max(
        item["official_metrics"]["placed_units"] for item in baseline_records
    ):
        demonstration_level = 2
    elif (
        Decimal(hf_summary["official_metrics"]["utilization_pct"]) > max(
            Decimal(item["official_metrics"]["utilization_pct"]) for item in baseline_records
        )
        or Decimal(hf_summary["official_metrics"]["waste_mm2"]) < min(
            Decimal(item["official_metrics"]["waste_mm2"]) for item in baseline_records
        )
    ):
        demonstration_level = 3
    elif Decimal(hf_summary["official_metrics"]["recoverable_area_mm2"]) > max(
        Decimal(item["official_metrics"]["recoverable_area_mm2"]) for item in baseline_records
    ):
        demonstration_level = 4
    else:
        demonstration_level = 5
    causal_trace = {
        "initial_seed_pieces": [item["piece_id"] for item in case["pieces"] if item["role"] == "seed"],
        "processing_order": [item.piece_id for item in hf_run["setup"].pending],
        "ff_small_piece": baseline_piece,
        "hf_small_piece": hf_piece,
        "later_piece_by_method": later_by_method,
        "hf_pocket_first": hf_piece["decision"] == "pocket",
        "ff_hf_pattern_different": placement_signature(live_runs["FF"], pending_only=True)
        != placement_signature(hf_run, pending_only=True),
    }
    trace = {
        "case_id": CASE_ID,
        "label": CAPABILITY_LABEL,
        "purpose": "controlled capacity demonstration; not a neutral or general benchmark",
        "fixture_freeze": freeze,
        "search_candidates_tried": 20,
        "config": case["config"],
        "material": case["material"],
        "stocks": case["stocks"],
        "pieces": case["pieces"],
        "method_order": ["FF", "BF", "WF", "HF x3"],
        "baselines": baseline_records,
        "hf_repetitions": hf_records,
        "hole_filling": hf_summary,
        "deterministic": deterministic,
        "demonstration_level": demonstration_level,
        "causal_trace": causal_trace,
        "figures": [
            comparison_path.relative_to(ROOT).as_posix(),
            stage_path.relative_to(ROOT).as_posix(),
        ],
        "timing_definition": (
            "Pocket detection includes anchor-map generation plus component labeling; "
            "pocket placement is separate; runtime HF is median of three repetitions."
        ),
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT / "sp004_hf_capability_trace.json"
    csv_path = OUTPUT / "sp004_hf_capability_results.csv"
    json_path.write_text(json.dumps(trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rows = [_csv_row(item) for item in (*baseline_records, hf_summary)]
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Determinismo: {'PASS' if deterministic else 'FAIL'}; nivel {demonstration_level}", flush=True)
    print(f"Resultados: {csv_path}", flush=True)
    print(f"Trazas: {json_path}", flush=True)


if __name__ == "__main__":
    main()
