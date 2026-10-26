"""TA-018: canonical per-source placement and least post-placement capacity."""
from dataclasses import replace
from decimal import Decimal as D
from unittest.mock import patch

import pytest

from app.modules.optimization.application.best_fit import calculate_best_fit
from app.modules.optimization.domain.best_fit import BestFitOptimizer, BestFitSelector
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.domain.problem import MaterialSource
from app.modules.optimization.domain.rotation import RasterCache
from app.modules.optimization.domain.worst_fit import WorstFitOptimizer
from app.modules.optimization.infrastructure.stock_adapter import InventoryStockAdapter
from tests.unit.optimization.test_first_fit import config, problem, stock
from tests.unit.optimization.test_preparation import piece
from tests.unit.optimization.test_stock import Inventory, remnant, sheet
from tests.unit.optimization.test_worst_fit import candidate


def optimize(rows=None, candidates=None, cfg=None):
    return BestFitOptimizer().optimize(problem(rows, candidates, cfg))


def test_normal_chooses_smallest_remaining_source_and_keeps_method_with_metrics():
    result = optimize([piece(width=2, height=2)],
                      [stock(1, width=6, height=4), stock(2, width=3, height=3)])
    assert result.complete and result.method == "BF"
    assert result.placements[0].stock.material_id == 2
    measured, _ = calculate_metrics(result, D(1), D(1))
    assert measured.method == "BF" and measured.metrics.material_area_mm2 == 9


@pytest.mark.parametrize("optimizer", [FirstFitOptimizer, BestFitOptimizer, WorstFitOptimizer])
@pytest.mark.parametrize("step", [5, 90])
def test_all_heuristics_use_exact_same_rotation_component(optimizer, step):
    with patch.object(RasterCache, "orientations", wraps=RasterCache().orientations) as orientations:
        result = optimizer().optimize(problem([piece(width=3, height=2)], [stock(width=2, height=3)],
                                             config(angular_step_deg=D(step))))
    assert orientations.call_count == 1
    assert orientations.call_args.args[2] == step
    assert result.complete and result.placements[0].rotation_deg == 90
    assert dict(result.placements[0].geometry) == dict(type="RECTANGULO", width_mm=2, height_mm=3)


@pytest.mark.parametrize("sources", [[], [stock(width=1, height=1)]])
def test_unplaceable(sources):
    result = optimize([piece(width=2, height=2)], sources)
    assert not result.complete and result.placements == ()
    assert result.unplaced_units == result.problem.units


def test_tie_uses_upstream_rank_not_identifier():
    a, b = stock(99), stock(1)
    assert optimize(candidates=[a, b]).placements[0].stock == a
    assert optimize(candidates=[b, a]).placements[0].stock == b


@pytest.mark.parametrize("field", ["stock_rank", "orientation_rank", "row", "column"])
def test_full_stable_tuple(field):
    first = candidate()
    later = replace(first, **{field: 1})
    assert BestFitSelector().select(iter([later, first])) is first


def test_post_placement_capacity_includes_separation_not_only_prior_area():
    a = candidate(stock(1, width=4, height=4), config(separation_mm=D(1)))
    b = candidate(stock(2, width=1, height=15), config(separation_mm=D(1)))
    assert (a.free_cells_before, b.free_cells_before) == (16, 15)
    assert (a.remaining_free_cells_after_placement, b.remaining_free_cells_after_placement) == (12, 13)
    assert BestFitSelector().select(iter([b, a])) is a
    result = optimize([piece(width=1, height=1)], [b.stock, a.stock], config(separation_mm=D(1)))
    assert result.placements[0].stock == a.stock
    assert not any(a.layout.occupied) and not any(b.layout.occupied)


def test_keeps_first_orientation_even_when_later_one_has_better_bf_score():
    # At 0 degrees the 1x2 mask blocks 2x2=4 cells. At 90 it blocks 3x2=6.
    result = optimize([piece(width=1, height=2)], [stock(width=5, height=2)], config(separation_mm=D(1)))
    p = result.placements[0]
    assert (p.rotation_deg, p.x_mm, p.y_mm) == (0, 0, 0)


def test_first_position_is_preserved_and_only_winning_layout_is_committed():
    result = optimize([piece(width=2, height=2, quantity=3)],
                      [stock(1, width=4, height=4), stock(2, width=4, height=4)])
    assert [p.stock.material_id for p in result.placements] == [1, 1, 1]
    assert [(p.x_mm, p.y_mm) for p in result.placements] == [(0, 0), (2, 0), (0, 2)]


def test_remnants_compete_only_with_remnants_and_sheets_are_not_evaluated():
    a = stock(1, width=5, height=5, source=MaterialSource.REMNANT)
    b = stock(2, width=4, height=4, source=MaterialSource.REMNANT)
    with patch.object(RasterCache, "material", wraps=RasterCache().material) as material:
        result = optimize([piece(width=2, height=2)], [stock(3, width=2, height=2), a, b])
    assert result.placements[0].stock == b
    assert all(call.args[0].source is MaterialSource.REMNANT for call in material.call_args_list)


def test_sheet_fallback_and_physical_unit_exhaustion():
    sources = [stock(8, width=1, height=1, source=MaterialSource.REMNANT)]
    sources += [stock(1, width=2, height=2, physical=i) for i in (1, 2)]
    result = optimize([piece(width=2, height=2, quantity=3)], sources)
    assert [p.stock.physical_unit_index for p in result.placements] == [1, 2]
    assert len(result.unplaced_units) == 1


def test_irregular_material_uses_interior_cells_not_bbox_area():
    triangle = stock(1, width=4, height=4, source=MaterialSource.REMNANT,
                     geometry=dict(type="POLIGONO_CONVEXO", vertices_mm=[[0, 0], [4, 0], [0, 4]]))
    square = stock(2, width=3, height=3, source=MaterialSource.REMNANT)
    assert optimize([piece(width=1, height=1)], [square, triangle]).placements[0].stock == triangle


def test_reproducibility_events_and_immutable_input():
    original = problem([piece(quantity=3)], [stock(1), stock(2)])
    before = repr(original)
    optimizer = BestFitOptimizer()
    events_a, events_b = [], []
    assert optimizer.optimize(original, events_a.append) == optimizer.optimize(original, events_b.append)
    assert events_a == events_b and repr(original) == before


def test_application_simulation_does_not_mutate_inventory():
    inventory = Inventory([remnant(8)], [sheet(5, ancho_mm=D(4), alto_mm=D(2), cantidad=2)])
    before = repr((inventory.remnants, inventory.sheets))
    result = calculate_best_fit([1], [piece(quantity=2)], config(), InventoryStockAdapter(inventory))
    assert result.complete and result.method == "BF"
    assert repr((inventory.remnants, inventory.sheets)) == before
    assert inventory.reads == 1 and inventory.calls == 2  # remnants and sheets


def test_empty_selector():
    assert BestFitSelector().select(iter(())) is None
