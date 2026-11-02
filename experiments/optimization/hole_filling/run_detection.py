"""Corre la fase de detección solamente sobre los cuatro layouts congelados."""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from experiments.optimization.hole_filling.lab import (  # noqa: E402
    DIAGNOSTIC_LABEL,
    feasible_anchor_map,
    physical_free_regions,
    prepare_case,
)
from experiments.optimization.hole_filling.visualize import (  # noqa: E402
    render_anchor_map,
    render_physical_map,
)


FIGURES = Path(__file__).resolve().parent / "figures"
OUTPUT = ROOT / "docs/evidence/sprint-02/SP-004/hole-filling"


def inspect_case(case_id):
    setup = prepare_case(case_id)
    stats = {
        "case_id": case_id,
        "label": DIAGNOSTIC_LABEL,
        "stocks": [],
        "candidate_orientations": 0,
        "anchor_positions_examined": 0,
        "pocket_components": 0,
        "internal_holes": 0,
        "physical_detection_ms": 0.0,
        "anchor_component_detection_ms": 0.0,
        "anchor_generation_ms": 0.0,
    }
    first_layout = next(iter(setup.layouts.values()))
    started = time.perf_counter_ns()
    regions = physical_free_regions(first_layout)
    stats["physical_detection_ms"] += (time.perf_counter_ns() - started) / 1_000_000
    stats["internal_holes"] = sum(region.region_type == "internal_hole" for region in regions)
    render_physical_map(first_layout, regions, FIGURES / f"{case_id}-physical.svg", DIAGNOSTIC_LABEL)

    snapshots = []
    for unit in setup.pending:
        for stock in setup.problem.groups[0].stock_candidates:
            layout = setup.layouts.get(stock.identity)
            if layout is None:
                continue
            for oriented in setup.prepared.orientations(unit):
                stats["candidate_orientations"] += 1
                anchor = feasible_anchor_map(layout, unit, stock, oriented)
                stats["anchor_positions_examined"] += anchor.positions_examined
                stats["pocket_components"] += len(anchor.pockets)
                stats["anchor_generation_ms"] += anchor.origin_generation_ns / 1_000_000
                stats["anchor_component_detection_ms"] += anchor.component_detection_ns / 1_000_000
                if len(snapshots) < 1 or (anchor.pockets and not snapshots[0].pockets):
                    snapshots.append(anchor)
    if snapshots:
        chosen = next((item for item in snapshots if item.pockets), snapshots[0])
        render_anchor_map(chosen, FIGURES / f"{case_id}-anchors.svg", DIAGNOSTIC_LABEL)
        stats["anchor_map_piece_id"] = chosen.unit.piece_id
        stats["anchor_map_rotation_deg"] = str(chosen.rotation_deg)
        stats["anchor_pocket_cells"] = [len(region.cells) for region in chosen.pockets]
        stats["anchor_pocket_bbox"] = [
            [region.min_row, region.min_column, region.max_row, region.max_column]
            for region in chosen.pockets
        ]
    stats["seed_count"] = len(setup.seed_placements)
    stats["pending_count"] = len(setup.pending)
    stats["used_seed_sources"] = sorted({placement.stock.source.value for placement in setup.seed_placements})
    stats["physical_regions"] = [
        {"type": region.region_type, "cells": region.area_cells,
         "bbox": [region.min_row, region.min_column, region.max_row, region.max_column]}
        for region in regions
    ]
    return stats


def main():
    summaries = [inspect_case(f"HF-DIAGNOSTIC-{index:03d}") for index in range(1, 5)]
    OUTPUT.mkdir(parents=True, exist_ok=True)
    target = OUTPUT / "sp004_hole_filling_detection.json"
    target.write_text(json.dumps(summaries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(target)
    print(json.dumps(summaries, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
