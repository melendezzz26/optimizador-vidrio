"""Validación de placement pocket-first y fallback sobre casos congelados."""
from decimal import Decimal
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from app.modules.optimization.domain.placement import PlacementIssue
from experiments.optimization.hole_filling.lab import prepare_case
from experiments.optimization.hole_filling.optimizer import (
    placement_signature,
    run_hole_filling,
)
from experiments.optimization.hole_filling.run_benchmark import _validate_placements


def test_circle_triangle_and_convex_polygon_cases_place_inside_detected_pockets():
    for case_id in (
        "HF-DIAGNOSTIC-001", "HF-DIAGNOSTIC-002", "HF-DIAGNOSTIC-003",
    ):
        run = run_hole_filling(case_id)
        assert run["diagnostics"]["pockets_used"] >= 1
        assert run["diagnostics"]["exact_geometry_checks"] >= 1
        assert run["diagnostics"]["fallback_unplaced"] == 0
        assert _validate_placements(run) == len(run["result"].placements)
        assert run["setup"].data["label"] == "DIAGNÓSTICO HOLE FILLING — NO PERTENECE A TA-027"


def test_negative_case_uses_ff_fallback_and_sheet_after_remnant_does_not_fit():
    run = run_hole_filling("HF-DIAGNOSTIC-004")
    pending = next(p for p in run["result"].placements if p.piece.piece_id == 2)

    assert run["diagnostics"]["pocket_components_detected"] == 0
    assert run["diagnostics"]["pockets_used"] == 0
    assert run["diagnostics"]["fallback_placements"] == 1
    assert pending.stock.source.value == "PLANCHA"
    assert _validate_placements(run) == len(run["result"].placements)


def test_material_thickness_margin_separation_and_non_overlap_are_preserved():
    setup = prepare_case("HF-DIAGNOSTIC-001")
    assert all(unit.material_key == (1, Decimal(6)) for unit in setup.problem.units)
    assert all(stock.material_key == (1, Decimal(6)) for stock in setup.problem.groups[0].stock_candidates)
    unit, stock = setup.pending[0], setup.stocks_by_id[901]
    layout = setup.layouts[stock.identity]
    oriented = next(item for item in setup.prepared.orientations(unit)
                    if item.orientation.rotation_deg == Decimal(0))
    occupied = next((row, column) for row, bits in enumerate(layout.occupied)
                    for column in range(layout.material.columns) if bits & (1 << column))
    assert layout.check(oriented.orientation.mask, *occupied).issue is PlacementIssue.OVERLAP
    separation_only = [
        layout.check(oriented.orientation.mask, row, column).issue
        for row in range(layout.material.row_count)
        for column in range(layout.material.columns)
    ]
    assert PlacementIssue.SEPARATION in separation_only


def test_three_runs_have_identical_functional_placements_and_pocket_decisions():
    runs = [run_hole_filling("HF-DIAGNOSTIC-002") for _ in range(3)]
    signatures = [placement_signature(run, pending_only=True) for run in runs]
    decisions = [run["diagnostics"]["selected_pockets"] for run in runs]
    assert signatures[0] == signatures[1] == signatures[2]
    assert decisions[0] == decisions[1] == decisions[2]
