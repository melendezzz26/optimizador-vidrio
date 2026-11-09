"""TA-052 T02: canonical per-source placement and maximum recoverable residual (M5)."""
from dataclasses import replace
from decimal import Decimal as D
from unittest.mock import patch

import pytest

from app.modules.optimization.application.best_residual_fit import calculate_best_residual_fit
from app.modules.optimization.domain.best_residual_fit import (
    BestResidualFitOptimizer,
    BestResidualFitResult,
    BestResidualFitSelector,
)
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.domain.packing import FeasibleCandidate, _empty_layout
from app.modules.optimization.domain.problem import MaterialSource, OptimizationResult
from app.modules.optimization.domain.rotation import RasterCache
from app.modules.optimization.domain.run_geometry import PreparedRunGeometry
from app.modules.optimization.infrastructure.stock_adapter import InventoryStockAdapter
from tests.unit.optimization.test_first_fit import config, problem, stock
from tests.unit.optimization.test_preparation import piece
from tests.unit.optimization.test_stock import Inventory, remnant, sheet


def optimize(rows=None, candidates=None, cfg=None):
    return BestResidualFitOptimizer().optimize(problem(rows, candidates, cfg))


def candidate(source=None, cfg=None, row=0, column=0, used_at=None, **ranks):
    source, cfg = source or stock(), cfg or config()
    unit = problem([piece(width=1, height=1)], [source], cfg).units[0]
    cache = RasterCache()
    orientation = cache.orientations(unit, cfg.resolution_mm, cfg.angular_step_deg)[0].orientation
    layout = _empty_layout(cache.material(source, cfg.resolution_mm), cfg)
    if used_at is not None:
        # A real earlier 1x1 placement makes the source "in use" (SPEC-TA-052 v2).
        layout = layout.place(orientation.mask, *used_at)
    return FeasibleCandidate(
        stock=source,
        layout=layout,
        orientation=orientation,
        row=row,
        column=column,
        stock_rank=ranks.get("stock_rank", 0),
        orientation_rank=ranks.get("orientation_rank", 0),
    )


def test_regression_two_pieces_that_fit_one_sheet_use_one_sheet():
    # Defect reported in the 04/11/2026 review: M5 opened a new sheet per piece.
    # Before: empty sheet 2 (2x2 residual) beat sheet 1 in use (no residual) -> [1, 2].
    result = optimize(
        [piece(width=2, height=2, quantity=2)],
        [stock(1, width=4, height=2), stock(2, width=4, height=2)],
    )
    assert result.complete
    assert [p.stock.material_id for p in result.placements] == [1, 1]
    assert [(p.x_mm, p.y_mm) for p in result.placements] == [(0, 0), (2, 0)]
    assert len(result.materials_used) == 1


def test_among_sources_in_use_m5_picks_largest_residual_rectangle():
    # 4x3 fills source 1; 3x3 does not fit there and opens source 2.
    # The 1x1 goes where it leaves the largest free rectangle: source 2 (4x1 = 4)
    # over source 1 (3x1 = 3). FF would keep it in source 1.
    rows = [piece(1, width=4, height=3), piece(2, width=3, height=3), piece(3, width=1, height=1)]
    sources = [stock(1, width=4, height=4), stock(2, width=4, height=4)]
    result = optimize(rows, sources)
    assert result.complete
    assert [p.stock.material_id for p in result.placements] == [1, 2, 2]
    assert (result.placements[2].x_mm, result.placements[2].y_mm) == (3, 0)
    ff = FirstFitOptimizer().optimize(problem(rows, sources))
    assert [p.stock.material_id for p in ff.placements] == [1, 2, 1]


def test_selector_prefers_any_source_in_use_over_an_unused_one():
    # v2: an unused 10x10 leaves a larger residual, but it is not even scored.
    unused = candidate(stock(1, width=10, height=10))
    used = candidate(stock(2), used_at=(3, 5), stock_rank=1)
    assert BestResidualFitSelector().select(iter([unused, used])) is used


def test_first_piece_opens_lowest_rank_source_and_keeps_m5_method():
    # v2: with no source in use, M5 opens the lowest stock_rank (here also the 6x6).
    result = optimize(
        [piece(width=2, height=2)],
        [stock(1, width=6, height=6), stock(2, width=3, height=3)],
    )
    assert isinstance(result, OptimizationResult)
    assert result.complete and result.method == "M5"
    assert result.placements[0].stock.material_id == 1
    measured, residuals = calculate_metrics(result, D(1), D(1))
    assert measured.method == "M5"
    assert len(residuals) == 1 and residuals[0].material_id == 1


def test_all_heuristics_use_exact_same_rotation_component():
    with patch.object(RasterCache, "iter_orientations", autospec=True, side_effect=RasterCache.iter_orientations) as orientations:
        result = BestResidualFitOptimizer().optimize(
            problem([piece(width=3, height=2)], [stock(width=2, height=3)], config(angular_step_deg=D(5)))
        )
    assert orientations.call_count == 1
    assert orientations.call_args.args[3] == 5
    assert result.complete and result.placements[0].rotation_deg == 90
    assert dict(result.placements[0].geometry) == dict(type="RECTANGULO", width_mm=2, height_mm=3)


@pytest.mark.parametrize("sources", [[], [stock(width=1, height=1)]])
def test_unplaceable(sources):
    result = optimize([piece(width=2, height=2)], sources)
    assert not result.complete and result.placements == ()
    assert result.unplaced_units == result.problem.units


def test_tie_uses_upstream_rank_not_identifier():
    a, b = stock(99, width=4, height=4), stock(1, width=4, height=4)
    assert optimize(candidates=[a, b]).placements[0].stock == a
    assert optimize(candidates=[b, a]).placements[0].stock == b


@pytest.mark.parametrize("used_at", [None, (3, 5)], ids=["unused", "in-use"])
@pytest.mark.parametrize("field", ["stock_rank", "orientation_rank", "row", "column"])
def test_full_stable_tuple(field, used_at):
    first = candidate(used_at=used_at)
    later = replace(first, **{field: 1})
    assert BestResidualFitSelector().select(iter([later, first])) is first
    assert BestResidualFitSelector().select(iter([first, later])) is first


def test_tie_break_minimizes_fragmentation_when_remnant_areas_are_equal():
    # Real geometry, both sources in use (v2): an earlier 1x1 sits in each one.
    # Source 1 (3x2, 1x1 at row 1, column 2): after the new 1x1 at (0, 0), 4 free
    # cells; largest remnant 2, fragmented 2.
    # Source 2 (1x4, 1x1 at row 3): after the new 1x1 at (0, 0), 2 free cells;
    # largest remnant 2, fragmented 0.
    # M5 selects source 2 because fragmented_cells (0) < fragmented_cells (2),
    # despite source 1 having a lower stock_rank.
    fragmented = candidate(stock(1, width=3, height=2), used_at=(1, 2))
    clean = candidate(stock(2, width=1, height=4), used_at=(3, 0), stock_rank=1)
    assert BestResidualFitSelector().select(iter([fragmented, clean])) is clean


@pytest.mark.parametrize("row,column", [(0, 2), (3, 1)])
def test_reused_residual_matches_exact_scan_after_a_new_placement(row, column):
    item = candidate(stock(width=4, height=4), used_at=(3, 0), row=row, column=column)
    selector = BestResidualFitSelector()
    assert selector._largest_after(item) == selector._scan(item.layout_after)


def test_first_position_is_preserved_and_only_winning_layout_is_committed():
    # v2: the third 2x2 still fits sheet 1 in use, so sheet 2 is never opened
    # (before: [1, 1, 2] with the third piece at (0, 0) of sheet 2).
    result = optimize(
        [piece(width=2, height=2, quantity=3)],
        [stock(1, width=4, height=4), stock(2, width=4, height=4)],
    )
    assert [p.stock.material_id for p in result.placements] == [1, 1, 1]
    assert [(p.x_mm, p.y_mm) for p in result.placements] == [(0, 0), (2, 0), (0, 2)]


def test_remnants_compete_only_with_remnants_and_sheets_are_not_evaluated():
    a = stock(1, width=5, height=5, source=MaterialSource.REMNANT)
    b = stock(2, width=4, height=4, source=MaterialSource.REMNANT)
    sheet_cand = stock(3, width=10, height=10, source=MaterialSource.SHEET)
    with patch.object(PreparedRunGeometry, "material", autospec=True, side_effect=PreparedRunGeometry.material) as material:
        result = optimize([piece(width=2, height=2)], [sheet_cand, a, b])
    assert result.placements[0].stock.source == MaterialSource.REMNANT
    assert all(call.args[1].source is MaterialSource.REMNANT for call in material.call_args_list)


def test_sheet_fallback_and_physical_unit_exhaustion():
    sources = [stock(8, width=1, height=1, source=MaterialSource.REMNANT)]
    sources += [stock(1, width=2, height=2, physical=i) for i in (1, 2)]
    result = optimize([piece(width=2, height=2, quantity=3)], sources)
    assert [p.stock.physical_unit_index for p in result.placements] == [1, 2]
    assert len(result.unplaced_units) == 1


def test_reproducibility_events_and_immutable_input():
    original = problem([piece(quantity=3)], [stock(1), stock(2)])
    before = repr(original)
    optimizer = BestResidualFitOptimizer()
    events_a, events_b = [], []
    assert optimizer.optimize(original, events_a.append) == optimizer.optimize(original, events_b.append)
    assert events_a == events_b and repr(original) == before


def test_application_simulation_does_not_mutate_inventory():
    inventory = Inventory([remnant(8)], [sheet(5, ancho_mm=D(4), alto_mm=D(2), cantidad=2)])
    before = repr((inventory.remnants, inventory.sheets))
    result = calculate_best_residual_fit([1], [piece(quantity=2)], config(), InventoryStockAdapter(inventory))
    assert result.complete and result.method == "M5"
    assert repr((inventory.remnants, inventory.sheets)) == before
    assert inventory.reads == 1 and inventory.calls == 2


def test_empty_selector():
    assert BestResidualFitSelector().select(iter(())) is None


def test_m5_places_real_circle_and_convex_polygon():
    circle = piece(1) | dict(
        tipo_forma="CIRCUNFERENCIA",
        geometria=dict(type="CIRCUNFERENCIA", radius_mm=2),
        area_mm2=D("12.57"),
    )
    poly = piece(2) | dict(
        tipo_forma="POLIGONO_CONVEXO",
        geometria=dict(type="POLIGONO_CONVEXO", vertices_mm=[[0, 0], [4, 0], [4, 3], [0, 3]]),
        area_mm2=D("12"),
    )
    result = optimize([circle, poly], [stock(1, width=15, height=15)])
    assert result.complete and len(result.placements) == 2
    assert {p.piece.shape_type for p in result.placements} == {"CIRCUNFERENCIA", "POLIGONO_CONVEXO"}


def test_m5_never_mixes_incompatible_materials():
    p1 = piece(1, glass=1, thickness=6, width=2, height=2)
    p2 = piece(2, glass=2, thickness=8, width=2, height=2)
    s1 = stock(1, glass=1, thickness=6, width=10, height=10)
    s2 = stock(2, glass=2, thickness=8, width=10, height=10)
    result = optimize([p1, p2], [s1, s2])
    assert result.complete and len(result.placements) == 2
    assert {p.stock.glass_type_id for p in result.placements} == {1, 2}
    assert all(p.piece.material_key == p.stock.material_key for p in result.placements)
