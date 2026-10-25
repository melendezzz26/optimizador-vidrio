"""TA-019 T02: exact post-placement source selection over the common geometry."""
import gc
import weakref
from dataclasses import replace
from decimal import Decimal as D
from itertools import permutations
from unittest.mock import patch

import pytest

from app.modules.optimization.application.dto import OptimizationRun, RunStatus
from app.modules.optimization.application.stock import with_compatible_stock
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.domain.packing import FeasibleCandidate, _empty_layout
from app.modules.optimization.domain.placement import SheetLayout
from app.modules.optimization.domain.problem import MaterialSource, OptimizationResult
from app.modules.optimization.domain.rotation import RasterCache, RasterPreparationError
from app.modules.optimization.domain.worst_fit import WorstFitOptimizer, WorstFitSelector
from app.modules.optimization.infrastructure.stock_adapter import InventoryStockAdapter
from tests.unit.optimization.test_first_fit import config, problem, stock
from tests.unit.optimization.test_preparation import piece, prepare_persisted_problem
from tests.unit.optimization.test_stock import Inventory, remnant, sheet


def optimize(rows=None, candidates=None, cfg=None, callback=None):
    return WorstFitOptimizer().optimize(problem(rows, candidates, cfg), callback)


def candidate(source=None, cfg=None, row=0, column=0, **ranks):
    source, cfg = source or stock(), cfg or config()
    unit = problem([piece(width=1, height=1)], [source], cfg).units[0]
    cache = RasterCache()
    return FeasibleCandidate(
        stock=source, layout=_empty_layout(cache.material(source, cfg.resolution_mm), cfg),
        orientation=cache.orientations(unit, cfg.resolution_mm, cfg.angular_step_deg)[0].orientation,
        row=row, column=column, stock_rank=ranks.get("stock_rank", 0),
        orientation_rank=ranks.get("orientation_rank", 0),
    )


def test_clearly_worst_source_and_domain_method_identity():
    result = optimize([piece(width=2, height=2)],
                      [stock(1, width=4, height=4), stock(2, width=6, height=4), stock(3, width=3, height=3)])
    assert isinstance(result, OptimizationResult) and result.method == "WF"
    assert result.complete and result.placements[0].stock.material_id == 2
    assert (result.placements[0].x_mm, result.placements[0].y_mm) == (0, 0)


def test_tie_preserves_upstream_stock_rank_not_id_order():
    first, second = stock(2), stock(99)
    assert optimize(candidates=[first, second]).placements[0].stock == first
    assert optimize(candidates=[second, first]).placements[0].stock == second


@pytest.mark.parametrize("field", ["stock_rank", "orientation_rank", "row", "column"])
def test_selector_uses_all_approved_tiebreaks(field):
    earlier = candidate()
    later = replace(earlier, **{field: 1})
    assert WorstFitSelector().select(iter([later, earlier])) is earlier
    assert WorstFitSelector().select(iter([earlier, later])) is earlier


def test_score_uses_real_post_placement_separation_and_does_not_mutate_layout():
    square = candidate(stock(1, width=4, height=4), config(separation_mm=D(1)))
    narrow = candidate(stock(2, width=1, height=15), config(separation_mm=D(1)), stock_rank=1)
    before = (square.layout, narrow.layout)
    # Prior capacity would select the square, but its 2x2 halo leaves less room.
    assert (square.free_cells_before, narrow.free_cells_before) == (16, 15)
    assert (square.remaining_free_cells_after_placement, narrow.remaining_free_cells_after_placement) == (12, 13)
    assert WorstFitSelector().select(iter([square, narrow])) is narrow
    assert (square.layout, narrow.layout) == before
    assert all(not any(layout.occupied) and not any(layout.blocked) for layout in before)
    assert square.layout_after is square.layout_after  # one immutable trial per candidate
    result = optimize([piece(width=1, height=1)], [square.stock, narrow.stock], config(separation_mm=D(1)))
    assert result.placements[0].stock == narrow.stock


def test_multiple_pieces_change_source_and_losing_trials_are_not_applied():
    result = optimize([piece(width=2, height=2, quantity=3)],
                      [stock(1, width=4, height=4), stock(2, width=4, height=4)])
    assert [p.stock.material_id for p in result.placements] == [1, 2, 1]
    assert [(p.x_mm, p.y_mm) for p in result.placements] == [(0, 0), (0, 0), (2, 0)]


def test_rotation_uses_common_component_and_first_feasible_angle():
    with patch.object(RasterCache, "orientations", wraps=RasterCache().orientations) as orientations:
        result = optimize([piece(width=3, height=2)], [stock(width=2, height=3)])
    assert orientations.call_count == 1
    assert result.complete and result.placements[0].rotation_deg == 90
    assert dict(result.placements[0].geometry) == dict(type="RECTANGULO", width_mm=2, height_mm=3)


def test_does_not_search_for_a_better_angle_or_position_within_source():
    # 90 degrees would leave 6 free cells, but canonical 0 degrees leaves 4.
    result = optimize([piece(width=2, height=1)], [stock(width=5, height=2)], config(separation_mm=D(1)))
    p = result.placements[0]
    assert (p.rotation_deg, p.x_mm, p.y_mm) == (0, 0, 0)


@pytest.mark.parametrize("candidates", [[], [stock(width=4, height=4)]])
def test_unplaceable_piece_has_no_fake_placement_and_is_not_confirmable(candidates):
    result = optimize([piece(width=5, height=5)], candidates)
    assert not result.complete and not result.placements
    assert result.unplaced_units == result.problem.units and result.metrics is None
    assert not OptimizationRun(optimization_id=1, status=RunStatus.NO_SOLUTION, result=result).confirmable


def test_failed_large_piece_does_not_suppress_smaller_units():
    result = optimize([piece(1, width=5, height=5), piece(2, width=2, height=2)], [stock(width=4, height=4)])
    assert [p.piece.piece_id for p in result.placements] == [2]
    assert [u.piece_id for u in result.unplaced_units] == [1]


def test_remnant_priority_prevents_even_evaluating_sheets():
    rem = stock(2, width=3, height=3, source=MaterialSource.REMNANT)
    unused_sheet = stock(3, width=10, height=10)
    with patch.object(RasterCache, "material", wraps=RasterCache().material) as material:
        result = optimize([piece(width=2, height=2)], [unused_sheet, rem])
    assert result.placements[0].stock == rem
    assert material.call_count == 1 and material.call_args.args[0] == rem


def test_worst_fit_between_remnants():
    small = stock(1, width=3, height=3, source=MaterialSource.REMNANT)
    large = stock(2, width=4, height=4, source=MaterialSource.REMNANT)
    assert optimize([piece(width=2, height=2)], [small, stock(3), large]).placements[0].stock == large


def test_sheet_fallback_only_when_no_remnant_is_feasible():
    remnants = [stock(i, width=1, height=1, source=MaterialSource.REMNANT) for i in (1, 2)]
    larger_sheet = stock(4, width=5, height=4)
    result = optimize([piece(width=2, height=2)], remnants + [stock(3, width=3, height=3), larger_sheet])
    assert result.placements[0].stock == larger_sheet


def test_physical_units_have_independent_layouts_and_no_new_stock_is_invented():
    result = optimize([piece(width=2, height=2, quantity=3)],
                      [stock(5, width=2, height=2, physical=i) for i in (1, 2)])
    assert [p.stock.physical_unit_index for p in result.placements] == [1, 2]
    assert result.placed_units == 2 and len(result.unplaced_units) == 1


def test_margin_changes_score_and_is_respected_at_canonical_position():
    cfg = config(margin_mm=D(1), separation_mm=D(1))
    square = candidate(stock(1, width=6, height=6), cfg, row=1, column=1)
    narrow = candidate(stock(2, width=3, height=17), cfg, row=1, column=1)
    assert (square.free_cells_before, narrow.free_cells_before) == (16, 15)
    assert (square.remaining_free_cells_after_placement, narrow.remaining_free_cells_after_placement) == (12, 13)
    result = optimize([piece(width=1, height=1)], [square.stock, narrow.stock], cfg)
    assert result.placements[0].stock == narrow.stock
    assert (result.placements[0].x_mm, result.placements[0].y_mm) == (1, 1)
    assert not optimize([piece(width=2, height=2)], [narrow.stock], cfg).complete


def test_separation_blocks_the_required_empty_cell():
    cfg = config(separation_mm=D(1))
    result = optimize([piece(width=2, height=2, quantity=2)], [stock(width=5, height=2)], cfg)
    assert [(p.x_mm, p.y_mm) for p in result.placements] == [(0, 0), (3, 0)]
    assert not optimize([piece(width=2, height=2, quantity=2)], [stock(width=4, height=2)], cfg).complete


def test_irregular_material_score_counts_interior_not_bbox():
    triangle = stock(1, width=4, height=4, source=MaterialSource.REMNANT,
                     geometry=dict(type="POLIGONO_CONVEXO", vertices_mm=[[0, 0], [4, 0], [0, 4]]))
    rectangle = stock(2, width=3, height=3, source=MaterialSource.REMNANT)
    # Triangle bbox area is 16 but its interior raster has only 6 usable cells.
    a, b = candidate(triangle), candidate(rectangle)
    assert (a.remaining_free_cells_after_placement, b.remaining_free_cells_after_placement) == (5, 8)
    assert optimize([piece(width=1, height=1)], [triangle, rectangle]).placements[0].stock == rectangle
    assert not optimize([piece(width=3, height=3)], [triangle]).complete


def test_multimaterial_multiorder_and_existing_piece_order_are_deterministic():
    rows = [piece(1, order=2, glass=2), piece(2, order=1, thickness="5.5"),
            piece(3, order=2, quantity=2), piece(4, order=1, width=2, height=2)]
    candidates = [stock(1, glass=2), stock(2, thickness="5.5"), stock(3), stock(4)]
    expected = optimize(rows, candidates)
    ff = FirstFitOptimizer().optimize(problem(rows, candidates))
    assert expected.problem == ff.problem and expected.complete
    assert expected.problem.order_ids == (1, 2)
    assert all(p.piece.material_key == p.stock.material_key for p in expected.placements)
    for permuted in permutations(rows):
        assert optimize(list(permuted), candidates) == expected


def test_repeated_same_problem_has_fresh_layouts_and_identical_events():
    original = problem([piece(width=2, height=2, quantity=3)], [stock(1), stock(2)])
    before = repr(original)
    optimizer, events_a, events_b = WorstFitOptimizer(), [], []
    a = optimizer.optimize(original, events_a.append)
    b = optimizer.optimize(original, events_b.append)
    assert a == b and events_a == events_b and repr(original) == before
    assert [e.placement for e in events_a if e.kind == "piece_placed"] == list(a.placements)
    assert [e.placed_units for e in events_a if e.kind == "piece_placed"] == [1, 2, 3]


def test_preparation_stock_slice_does_not_consume_or_mutate_inventory():
    inventory = Inventory([remnant(8)], [sheet(5, ancho_mm=D(4), alto_mm=D(2), cantidad=2)])
    before = repr((inventory.remnants, inventory.sheets))
    prepared = prepare_persisted_problem([2, 1], [piece(1, order=1, quantity=2), piece(2, order=2)], config())
    result = WorstFitOptimizer().optimize(with_compatible_stock(prepared, InventoryStockAdapter(inventory)))
    assert result.complete and result.total_units == 3
    assert inventory.reads == 1 and inventory.calls == 2
    assert repr((inventory.remnants, inventory.sheets)) == before


def test_common_metrics_preserve_wf_identity_and_revalidate_geometry():
    result = optimize([piece(width=2, height=2, quantity=2)], [stock(width=5, height=2)], config(separation_mm=D(1)))
    measured, residuals = calculate_metrics(result, D(1), D(1))
    assert measured.method == "WF" and measured.metrics.placed_piece_area_mm2 == 8
    assert measured.metrics.material_area_mm2 == 10 and residuals == ()


def test_raster_errors_are_not_silently_reported_as_no_fit():
    with pytest.raises(RasterPreparationError):
        optimize(cfg=config(resolution_mm=D("0.10000000000000000001")))


def test_selector_empty_input():
    assert WorstFitSelector().select(iter(())) is None


def test_candidate_selection_is_incremental_and_releases_discarded_layouts(monkeypatch):
    """Ten times more feasible sources must not retain ten times more trials."""
    original_init, original_place = FeasibleCandidate.__init__, SheetLayout.place

    def measure(source_count):
        candidate_refs, layout_refs = [], []
        counts = {"generated": 0, "scored": 0}
        peaks = {"candidates": 0, "layouts_after": 0}

        def sample():
            peaks["candidates"] = max(peaks["candidates"], sum(ref() is not None for ref in candidate_refs))
            peaks["layouts_after"] = max(peaks["layouts_after"], sum(ref() is not None for ref in layout_refs))

        def track_candidate(self, *args, **kwargs):
            # An eager list/tuple would generate another candidate before scoring
            # the previous one. Plain functions avoid Mock retaining arguments.
            assert counts["generated"] == counts["scored"], "Candidates were generated ahead of scoring"
            original_init(self, *args, **kwargs)
            counts["generated"] += 1
            candidate_refs.append(weakref.ref(self))
            sample()

        def track_place(self, *args, **kwargs):
            after = original_place(self, *args, **kwargs)
            counts["scored"] += 1
            layout_refs.append(weakref.ref(after))
            sample()
            return after

        with monkeypatch.context() as instrumentation:
            instrumentation.setattr(FeasibleCandidate, "__init__", track_candidate)
            instrumentation.setattr(SheetLayout, "place", track_place)
            result = optimize([piece(width=1, height=1, quantity=2)],
                              [stock(i, width=4, height=4) for i in range(1, source_count + 1)])

        assert result.complete and [p.stock.material_id for p in result.placements] == [1, 2]
        assert counts["generated"] == counts["scored"] == source_count * 2
        # Discarded trials must disappear while selection is still in progress,
        # rather than merely being released together when the optimizer returns.
        assert peaks["candidates"] < source_count
        assert peaks["layouts_after"] < source_count
        gc.collect()
        assert all(ref() is None for ref in candidate_refs)
        assert all(ref() is None for ref in layout_refs)
        return peaks

    small, large = measure(8), measure(80)
    # Compare scaling, not an implementation-specific exact object count. Allow
    # headroom for bounded references while rejecting per-source accumulation.
    for kind in small:
        assert small[kind] > 0
        assert large[kind] <= small[kind] * 2


def test_first_fit_does_not_score_or_evaluate_later_sources():
    with patch.object(FeasibleCandidate, "remaining_free_cells_after_placement",
                      new=property(lambda _: pytest.fail("FF must not score candidates"))):
        with patch.object(RasterCache, "material", wraps=RasterCache().material) as material:
            result = FirstFitOptimizer().optimize(problem(candidates=[stock(1), stock(2)]))
    assert result.placements[0].stock.material_id == 1 and result.method == "FF"
    assert material.call_count == 1
