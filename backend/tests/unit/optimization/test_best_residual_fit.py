"""TA-052 T02: canonical per-source placement and maximum recoverable residual (M5)."""
from dataclasses import replace
from decimal import Decimal as D
from types import SimpleNamespace
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


def candidate(source=None, cfg=None, row=0, column=0, **ranks):
    source, cfg = source or stock(), cfg or config()
    unit = problem([piece(width=1, height=1)], [source], cfg).units[0]
    cache = RasterCache()
    return FeasibleCandidate(
        stock=source,
        layout=_empty_layout(cache.material(source, cfg.resolution_mm), cfg),
        orientation=cache.orientations(unit, cfg.resolution_mm, cfg.angular_step_deg)[0].orientation,
        row=row,
        column=column,
        stock_rank=ranks.get("stock_rank", 0),
        orientation_rank=ranks.get("orientation_rank", 0),
    )


def synthetic_candidate(rows, stock_rank=0, orientation_rank=0, row=0, column=0):
    width = max((bits.bit_length() for bits in rows), default=0)
    layout_after = SimpleNamespace(
        usable=tuple(rows),
        blocked=(0,) * len(rows),
        material=SimpleNamespace(columns=width),
    )
    return SimpleNamespace(
        layout_after=layout_after,
        remaining_free_cells_after_placement=sum(bits.bit_count() for bits in rows),
        stock_rank=stock_rank,
        orientation_rank=orientation_rank,
        row=row,
        column=column,
    )


def test_normal_chooses_largest_residual_source_and_keeps_m5_method():
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


@pytest.mark.parametrize("field", ["stock_rank", "orientation_rank", "row", "column"])
def test_full_stable_tuple(field):
    first = candidate()
    later = replace(first, **{field: 1})
    assert BestResidualFitSelector().select(iter([later, first])) is first
    assert BestResidualFitSelector().select(iter([first, later])) is first


def test_tie_break_minimizes_fragmentation_when_remnant_areas_are_equal():
    fragmented = synthetic_candidate((0b111, 0b011), stock_rank=0)
    clean = synthetic_candidate((0b11, 0b11), stock_rank=1)
    assert BestResidualFitSelector().select((fragmented, clean)) is clean


def test_first_position_is_preserved_and_only_winning_layout_is_committed():
    result = optimize(
        [piece(width=2, height=2, quantity=3)],
        [stock(1, width=4, height=4), stock(2, width=4, height=4)],
    )
    assert [p.stock.material_id for p in result.placements] == [1, 1, 2]
    assert [(p.x_mm, p.y_mm) for p in result.placements] == [(0, 0), (2, 0), (0, 0)]


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
