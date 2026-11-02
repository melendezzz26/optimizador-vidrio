"""Pruebas aisladas de formación, legalidad y trazabilidad Pair-Block."""
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.best_fit import BestFitOptimizer
from app.modules.optimization.domain.worst_fit import WorstFitOptimizer
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.domain.problem import MaterialSource, OptimizationConfig
from app.modules.optimization.domain.raster_mask import RasterMask
from app.modules.optimization.domain.placement import SheetLayout
from app.modules.optimization.domain.rotation import RasterCache, discrete_angles
from experiments.optimization.block_packing import BlockPackingExperimental
from experiments.optimization.block_packing.block_experimental import _compose, _orientation_options
from experiments.optimization.block_packing.run_benchmark import _classify_case
from experiments.optimization.loader import build_problem, load_problem


ROOT = Path(__file__).resolve().parents[3]
BLOCK_CASE = ROOT / "experiments/optimization/block_packing/cases/BLOCK-DISCRIMINANT-001.json"


def _block_problem():
    return build_problem(json.loads(BLOCK_CASE.read_text(encoding="utf-8")))


def _signature(result, trace):
    placements = tuple((item.piece.identity, item.stock.identity, item.x_mm, item.y_mm,
        item.rotation_deg, tuple(item.geometry.items())) for item in result.placements)
    return placements, trace.selected_blocks


def test_block_discriminant_accepts_complementary_pair_and_preserves_original_units():
    problem = _block_problem()
    result, trace = BlockPackingExperimental().optimize(problem)
    baseline = FirstFitOptimizer().optimize(problem)
    assert result.placed_units == 3
    assert trace.accepted_blocks == trace.placed_blocks == 1
    assert trace.pieces_in_blocks == 2
    assert trace.standalone_pieces == 1
    assert trace.block_compaction == 1.0
    triangles = [placement for placement in result.placements if placement.piece.piece_id in (2, 3)]
    assert {placement.piece.identity for placement in triangles} == {(2, 1), (3, 1)}
    assert {placement.rotation_deg for placement in triangles} == {Decimal(0), Decimal(180)}
    assert all(placement.stock.source is MaterialSource.SHEET for placement in triangles)
    assert len({placement.piece.identity for placement in result.placements}) == 3
    actual_pattern = sorted((item.piece.identity, item.x_mm, item.y_mm, item.rotation_deg)
                            for item in result.placements)
    baseline_pattern = sorted((item.piece.identity, item.x_mm, item.y_mm, item.rotation_deg)
                              for item in baseline.placements)
    assert actual_pattern != baseline_pattern
    block_metrics, _ = calculate_metrics(result, Decimal(1), Decimal(1))
    baseline_metrics, _ = calculate_metrics(baseline, Decimal(1), Decimal(1))
    assert block_metrics.metrics.utilization_pct == baseline_metrics.metrics.utilization_pct
    assert block_metrics.metrics.waste_mm2 == baseline_metrics.metrics.waste_mm2


def test_pair_rejects_noncomplementary_equal_rectangles_and_falls_back_to_singles():
    result, trace = BlockPackingExperimental().optimize(load_problem("EXP-SMALL-001"))
    assert result.placed_units == 3
    assert trace.accepted_blocks == trace.placed_blocks == 0
    assert trace.standalone_pieces == 3
    assert len({placement.piece.identity for placement in result.placements}) == 3


def test_geometrically_accepted_block_that_does_not_fit_falls_back_to_its_two_units():
    result, trace = BlockPackingExperimental().optimize(load_problem("EXP-COMPLEX-001"))
    assert trace.placed_blocks <= trace.accepted_blocks
    assert trace.pieces_in_blocks == 2 * trace.placed_blocks
    assert trace.standalone_pieces == result.total_units - trace.pieces_in_blocks
    assert result.placed_units == 24
    assert len({item.piece.identity for item in result.placements}) == 24


def test_material_and_thickness_are_pair_compatibility_boundaries():
    data = json.loads(BLOCK_CASE.read_text(encoding="utf-8"))
    data["pieces"][2]["id_tipo_vidrio"] = 2
    data["stock"].append({"material_id": 997, "quantity": 1, "source": "PLANCHA",
        "glass_type_id": 2, "thickness_mm": 6, "geometry": {"type": "RECTANGULO", "width_mm": 18, "height_mm": 10}})
    _, material_trace = BlockPackingExperimental().optimize(build_problem(data))
    assert material_trace.candidate_pairs == 3
    assert material_trace.compatible_pairs == 1
    assert material_trace.filtered_pairs >= 2
    data = json.loads(BLOCK_CASE.read_text(encoding="utf-8"))
    data["pieces"][2]["espesor_mm"] = 8
    data["stock"].append({"material_id": 998, "quantity": 1, "source": "PLANCHA",
        "glass_type_id": 1, "thickness_mm": 8, "geometry": {"type": "RECTANGULO", "width_mm": 18, "height_mm": 10}})
    _, thickness_trace = BlockPackingExperimental().optimize(build_problem(data))
    assert thickness_trace.candidate_pairs == 3
    assert thickness_trace.compatible_pairs == 1
    assert thickness_trace.filtered_pairs >= 2


def test_v2_uses_only_valid_five_degree_angles_and_keeps_distinct_same_bbox_masks():
    problem = _block_problem()
    from app.modules.optimization.domain.run_geometry import prepare_run_geometry
    prepared = prepare_run_geometry(problem)
    triangle = next(unit for unit in problem.units if unit.piece_id == 2)
    options = _orientation_options(prepared, (triangle,), lambda: None)[triangle.identity]
    allowed = {orientation.rotation_deg for orientation in options}
    assert all(angle in set(discrete_angles(Decimal(5))) for angle in allowed)
    assert any(angle not in {Decimal(0), Decimal(90), Decimal(180), Decimal(270)} for angle in allowed)
    orientation_0 = next(value for value in options if value.rotation_deg == 0)
    orientation_180 = next(value for value in options if value.rotation_deg == 180)
    assert (orientation_0.mask.columns, orientation_0.mask.row_count) == (
        orientation_180.mask.columns, orientation_180.mask.row_count)
    assert orientation_0.mask.rows != orientation_180.mask.rows
    result, trace = BlockPackingExperimental().optimize(problem)
    assert all(Decimal(angle) in set(discrete_angles(Decimal(5)))
               for block in trace.selected_blocks for angle in block["rotations_deg"])
    assert trace.orientation_combinations_theoretical == trace.candidate_pairs * 72 * 72
    assert trace.compatible_pairs <= trace.candidate_pairs
    assert trace.orientation_combinations_after_symmetry <= trace.orientation_combinations_theoretical
    assert trace.orientation_combinations_after_phase <= trace.orientation_combinations_after_bounds
    assert trace.orientation_combinations_pruned == (
        trace.orientation_combinations_pruned_by_compatibility
        + trace.orientation_combinations_pruned_by_symmetry
        + trace.orientation_combinations_pruned_by_bounds
        + trace.orientation_combinations_pruned_by_phase
        + trace.orientation_combinations_pruned_by_best_bound)
    assert trace.orientation_combinations_evaluated <= trace.orientation_combinations_after_phase
    assert trace.relative_positions_theoretical == (
        trace.relative_positions_pruned + trace.relative_positions_checked)
    assert trace.relative_positions_checked >= trace.orientation_combinations_evaluated


def test_internal_pair_layout_enforces_separation_and_rejects_overlap():
    problem = _block_problem()
    from app.modules.optimization.domain.run_geometry import prepare_run_geometry
    prepared = prepare_run_geometry(problem)
    first, second = [unit for unit in problem.units if unit.piece_id in (2, 3)]
    options_a = _orientation_options(prepared, (first,), lambda: None)[first.identity]
    options_b = _orientation_options(prepared, (second,), lambda: None)[second.identity]
    orientation_a = next(value for value in options_a if value.rotation_deg == 0)
    orientation_b = next(value for value in options_b if value.rotation_deg == 180)
    assert _compose(first, second, orientation_a, orientation_b, 1, 0,
                    problem.config.resolution_mm, 0) is not None
    assert _compose(first, second, orientation_a, orientation_b, 1, 0,
                    problem.config.resolution_mm, 1) is None
    assert _compose(first, second, orientation_a, orientation_b, 0, 0,
                    problem.config.resolution_mm, 0) is None
    material = RasterMask(1.0, 8, (255,) * 4)
    layout = SheetLayout.empty(material, separation_mm=1)
    solid = RasterMask(1.0, 2, (3, 3))
    layout = layout.place(solid, 0, 0)
    assert not layout.check(solid, 0, 2).is_valid
    assert layout.check(solid, 0, 3).is_valid


def test_rectangle_remains_standalone_and_block_keeps_original_identities():
    result, trace = BlockPackingExperimental().optimize(_block_problem())
    rectangle = next(placement for placement in result.placements if placement.piece.piece_id == 1)
    assert rectangle.piece.geometry["type"] == "RECTANGULO"
    assert trace.standalone_pieces == result.total_units - trace.pieces_in_blocks
    assert trace.placed_blocks == 1
    assert all(placement.piece.piece_id in {1, 2, 3} for placement in result.placements)
    assert len({placement.piece.identity for placement in result.placements}) == 3


def test_pair_respects_remnant_before_sheet_source_priority():
    data = json.loads(BLOCK_CASE.read_text(encoding="utf-8"))
    data["pieces"][0]["id_tipo_vidrio"] = 2
    data["stock"].append({"material_id": 988, "quantity": 1, "source": "PLANCHA",
        "glass_type_id": 2, "thickness_mm": 6,
        "geometry": {"type": "RECTANGULO", "width_mm": 18, "height_mm": 10}})
    data["stock"].insert(0, {"material_id": 989, "quantity": 1, "source": "RETAZO",
        "glass_type_id": 1, "thickness_mm": 6,
        "geometry": {"type": "RECTANGULO", "width_mm": 11, "height_mm": 10}})
    result, trace = BlockPackingExperimental().optimize(build_problem(data))
    triangle_placements = [item for item in result.placements if item.piece.piece_id in (2, 3)]
    assert trace.placed_blocks == 1
    assert {item.stock.source for item in triangle_placements} == {MaterialSource.REMNANT}


def test_block_matching_is_deterministic_across_three_runs():
    problem = _block_problem()
    signatures = [_signature(*BlockPackingExperimental().optimize(problem)) for _ in range(3)]
    assert signatures[0] == signatures[1] == signatures[2]


def test_pair_experiment_does_not_mutate_official_fixture_bytes():
    path = ROOT / "experiments/optimization/cases/EXP-COMPLEX-001.json"
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    BlockPackingExperimental().optimize(load_problem("EXP-COMPLEX-001"))
    after = hashlib.sha256(path.read_bytes()).hexdigest()
    assert before == after


def test_ff_and_bf_regression_outputs_remain_well_formed_after_pair_run():
    problem = load_problem("EXP-SMALL-001")
    BlockPackingExperimental().optimize(problem)
    for optimizer in (FirstFitOptimizer, BestFitOptimizer, WorstFitOptimizer):
        result = optimizer().optimize(problem)
        measured, _ = calculate_metrics(result, Decimal(1), Decimal(1))
        assert measured.placed_units == 3
        assert measured.unplaced_units == ()


def test_predeclared_case_classification_precedence_a_through_e():
    def row(method, *, runtime=10, utilization="50", waste="50", recoverable="20"):
        return {"method": method, "placed_units": "2", "remnants_used": "0",
            "sheets_used": "1", "utilization_pct": utilization, "waste": waste,
            "recoverable_area": recoverable, "runtime_ms": str(runtime)}

    def detail(method, *, x="0", blocks=0):
        placement = {"piece_id": 1, "unit_index": 1, "source": "PLANCHA",
            "material_id": 1, "physical_unit_index": 1, "x_mm": x, "y_mm": "0",
            "rotation_deg": "0"}
        return {"method": method, "placements": [placement],
            "block_trace": {"placed_blocks": blocks}}

    def classify(pair, *, x="0", blocks=0):
        rows = [row("FF"), row("BF", runtime=11), row("WF", runtime=12), pair]
        details = [detail("FF"), detail("BF"), detail("WF"), detail("Pair-Block-v2", x=x, blocks=blocks)]
        return _classify_case(rows, details)["classification"]

    assert classify(row("Pair-Block-v2", runtime=20)) == "D"
    assert classify(row("Pair-Block-v2", runtime=101), blocks=1) == "E"
    assert classify(row("Pair-Block-v2", runtime=20, utilization="51", waste="49", recoverable="21")) == "C"
    assert classify(row("Pair-Block-v2", runtime=20), x="1", blocks=1) == "B"
    assert classify(row("Pair-Block-v2", runtime=20), blocks=1) == "A"
    assert classify(row("Pair-Block-v2", runtime=20, waste="51", recoverable="19"), blocks=1) == "E"
