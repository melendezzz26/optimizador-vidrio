"""SP-005 M5 selector checks on shared engine contracts and TA-027 fixtures."""

import importlib.util
import sys
from decimal import Decimal
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[4]
M5_SCRIPT = PROJECT_ROOT / "docs" / "spikes" / "sp-005-heuristica-m5" / "experimento_m5.py"
sys.path.insert(0, str(PROJECT_ROOT))
M5_SPEC = importlib.util.spec_from_file_location("sp005_experimento_m5", M5_SCRIPT)
M5_MODULE = importlib.util.module_from_spec(M5_SPEC)
sys.modules[M5_SPEC.name] = M5_MODULE
M5_SPEC.loader.exec_module(M5_MODULE)

from experiments.optimization.loader import CASES, load_problem  # noqa: E402
from app.modules.optimization.domain.best_fit import BestFitOptimizer  # noqa: E402
from app.modules.optimization.domain.metrics import calculate_metrics  # noqa: E402
from app.modules.optimization.domain.placement import SheetLayout  # noqa: E402
from app.modules.optimization.domain.problem import (  # noqa: E402
    MaterialGroup,
    MaterialSource,
    OptimizationConfig,
    OptimizationProblem,
    PieceUnit,
    StockCandidate,
)
from app.modules.optimization.domain.rasterizer import rasterize_geometry, rasterize_material  # noqa: E402
from app.modules.optimization.domain.rotation import RasterCache  # noqa: E402
from app.modules.optimization.domain.worst_fit import WorstFitOptimizer  # noqa: E402

BestResidualFitOptimizer = M5_MODULE.BestResidualFitOptimizer
BestResidualFitSelector = M5_MODULE.BestResidualFitSelector


def _problem(*, piece_geometry=None, stocks=(), glass_type_id=7, thickness_mm=6):
    piece_geometry = piece_geometry or {"type": "RECTANGULO", "width_mm": 2, "height_mm": 2}
    unit = PieceUnit(
        order_id=1,
        piece_id=1,
        unit_index=1,
        glass_type_id=glass_type_id,
        thickness_mm=Decimal(str(thickness_mm)),
        geometry=piece_geometry,
        area_mm2=Decimal("4"),
    )
    group = MaterialGroup(
        glass_type_id=glass_type_id,
        thickness_mm=Decimal(str(thickness_mm)),
        units=(unit,),
        stock_candidates=tuple(stocks),
    )
    return OptimizationProblem(
        order_ids=(1,),
        config=OptimizationConfig(
            resolution_mm=Decimal("1"),
            margin_mm=Decimal("0"),
            separation_mm=Decimal("0"),
            angular_step_deg=Decimal("5"),
        ),
        groups=(group,),
    )


def _stock(source, material_id, width, height, *, glass_type_id=7, thickness_mm=6):
    return StockCandidate(
        source=source,
        material_id=material_id,
        physical_unit_index=1,
        glass_type_id=glass_type_id,
        thickness_mm=Decimal(str(thickness_mm)),
        geometry={"type": "RECTANGULO", "width_mm": width, "height_mm": height},
        area_mm2=Decimal(str(width * height)),
    )


def _plain(value):
    if hasattr(value, "items"):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def _assert_valid_placements(result):
    config = result.problem.config
    assert config.resolution_mm == Decimal("1")
    assert config.angular_step_deg == Decimal("5")
    layouts = {}
    cache = RasterCache()
    for placement in result.placements:
        assert placement.rotation_deg % config.angular_step_deg == 0
        possible_angles = {
            candidate.orientation.rotation_deg
            for candidate in cache.orientations(
                placement.piece, config.resolution_mm, config.angular_step_deg
            )
        }
        assert placement.rotation_deg in possible_angles
        assert placement.piece.material_key == placement.stock.material_key

        identity = placement.stock.identity
        layout = layouts.get(identity)
        if layout is None:
            material = rasterize_material(_plain(placement.stock.geometry), float(config.resolution_mm))
            layout = SheetLayout.empty(
                material,
                margin_mm=float(config.margin_mm),
                separation_mm=float(config.separation_mm),
            )
        row, column = placement.y_mm / config.resolution_mm, placement.x_mm / config.resolution_mm
        assert row == row.to_integral_value()
        assert column == column.to_integral_value()
        mask = rasterize_geometry(_plain(placement.geometry), float(config.resolution_mm))
        layouts[identity] = layout.place(mask, int(row), int(column))


def test_m5_prefers_larger_recoverable_rectangle_over_lower_total_free_area():
    # BF selects source with fewer total free cells; M5 selects the larger
    # continuous residual rectangle even though that source has more total free area.
    # Stock A (5x5, area 25): placing 2x2 leaves 21 free cells, largest rectangle is 3x5 = 15.
    # Stock B (3x4, area 12): placing 2x2 leaves 8 free cells, largest rectangle is 3x2 = 6.
    broad_stock = _stock(MaterialSource.SHEET, 1, 5, 5)
    tight_stock = _stock(MaterialSource.SHEET, 2, 3, 4)
    prob = _problem(stocks=(broad_stock, tight_stock))

    bf_result = BestFitOptimizer().optimize(prob)
    m5_result = BestResidualFitOptimizer().optimize(prob)

    assert bf_result.placements[0].stock.material_id == 2
    assert m5_result.placements[0].stock.material_id == 1


def test_m5_breaks_equal_residual_ties_by_less_fragmentation_then_canonical_rank():
    # Real geometry: piece 2x2.
    # Candidate 1 (4x3): largest remnant is 2x3 = 6, but leaves 2 fragmented cells (8 - 6 = 2).
    # Candidate 2 (2x5): largest remnant is 2x3 = 6, and leaves 0 fragmented cells (6 - 6 = 0).
    fragmented_stock = _stock(MaterialSource.SHEET, 1, 4, 3)
    clean_stock = _stock(MaterialSource.SHEET, 2, 2, 5)

    prob = _problem(stocks=(fragmented_stock, clean_stock))
    result = BestResidualFitOptimizer().optimize(prob)
    assert result.placements[0].stock.material_id == 2

    # When largest remnant and fragmentation are identical, upstream stock rank breaks the tie.
    identical_a = _stock(MaterialSource.SHEET, 10, 2, 5)
    identical_b = _stock(MaterialSource.SHEET, 20, 2, 5)
    prob_rank = _problem(stocks=(identical_a, identical_b))
    result_rank = BestResidualFitOptimizer().optimize(prob_rank)
    assert result_rank.placements[0].stock.material_id == 10
    assert BestResidualFitSelector().select(()) is None


def test_m5_falls_back_to_fragmented_free_area_when_residual_is_below_minimum():
    # Real geometry: piece 1x1.
    # Stock 1 (3x1): 2 free cells remaining.
    # Stock 2 (2x1): 1 free cell remaining.
    # With min_width_cells=4, neither remnant qualifies (both get 0 remnant cells).
    # M5 falls back to minimizing fragmented cells, selecting Stock 2 (1 < 2).
    piece_1x1 = {"type": "RECTANGULO", "width_mm": 1, "height_mm": 1}
    larger_stock = _stock(MaterialSource.SHEET, 1, 3, 1)
    smaller_stock = _stock(MaterialSource.SHEET, 2, 2, 1)
    prob = _problem(piece_geometry=piece_1x1, stocks=(larger_stock, smaller_stock))

    selector_fallback = BestResidualFitOptimizer(min_width_cells=4, min_height_cells=1)
    result = selector_fallback.optimize(prob)
    assert result.placements[0].stock.material_id == 2


@pytest.mark.parametrize("case_id", CASES)
def test_m5_ta027_results_are_complete_deterministic_and_respect_geometry(case_id):
    signatures = []
    for _ in range(3):
        problem = load_problem(case_id)
        result = BestResidualFitOptimizer().optimize(problem)
        calculated, _ = calculate_metrics(result, Decimal("1"), Decimal("1"))
        assert calculated.complete
        assert calculated.placed_units == calculated.total_units
        assert all(p.stock.material_key == p.piece.material_key for p in result.placements)
        _assert_valid_placements(result)
        signatures.append(M5_MODULE._signature(M5_MODULE._functional_payload(result, calculated)))
    assert signatures[0] == signatures[1] == signatures[2]


def test_m5_uses_remnant_first_and_falls_through_to_sheet_when_remnant_cannot_fit():
    sheet = _stock(MaterialSource.SHEET, 2, 4, 4)
    fitting_remnant = _stock(MaterialSource.REMNANT, 1, 4, 4)
    remnant_first = BestResidualFitOptimizer().optimize(_problem(stocks=(sheet, fitting_remnant)))
    assert remnant_first.placements[0].stock.source is MaterialSource.REMNANT

    too_small_remnant = _stock(MaterialSource.REMNANT, 3, 1, 1)
    fallback = BestResidualFitOptimizer().optimize(_problem(stocks=(too_small_remnant, sheet)))
    assert fallback.placements[0].stock.source is MaterialSource.SHEET


def test_m5_without_any_feasible_candidate_returns_incomplete_result():
    result = BestResidualFitOptimizer().optimize(_problem(stocks=()))
    assert result.placements == ()
    assert not result.complete
    assert BestResidualFitSelector().select(()) is None


def test_m5_decisions_differ_from_bf_and_wf_on_official_complex_fixture():
    problem = load_problem("EXP-COMPLEX-001")
    m5 = BestResidualFitOptimizer().optimize(problem)
    bf = BestFitOptimizer().optimize(load_problem("EXP-COMPLEX-001"))
    wf = WorstFitOptimizer().optimize(load_problem("EXP-COMPLEX-001"))

    m5_signature = M5_MODULE.placement_records(m5)
    assert m5_signature != M5_MODULE.placement_records(bf)
    assert m5_signature != M5_MODULE.placement_records(wf)


def test_m5_respects_ta027_five_degree_rotation_margin_separation_and_non_overlap():
    for case_id in ("EXP-MEDIUM-001", "EXP-COMPLEX-001"):
        result = BestResidualFitOptimizer().optimize(load_problem(case_id))
        assert result.problem.config.margin_mm == Decimal("1")
        assert result.problem.config.separation_mm == Decimal("1")
        _assert_valid_placements(result)


def test_ta027_orientation_cache_enumerates_five_degree_candidates():
    problem = load_problem("EXP-COMPLEX-001")
    polygon = next(unit for unit in problem.units if unit.geometry["type"] == "POLIGONO_CONVEXO")
    angles = {
        candidate.orientation.rotation_deg
        for candidate in RasterCache().orientations(
            polygon, problem.config.resolution_mm, problem.config.angular_step_deg
        )
    }
    assert Decimal("5") in angles
    assert Decimal("355") in angles
