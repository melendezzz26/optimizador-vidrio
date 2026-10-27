"""TA-020: one source-priority contract exercised against all three heuristics."""
from dataclasses import replace
from decimal import Decimal as D
from unittest.mock import patch

import pytest

from app.modules.optimization.application.stock import with_compatible_stock
from app.modules.optimization.domain.best_fit import BestFitOptimizer
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.problem import MaterialSource
from app.modules.optimization.domain.rotation import RasterCache
from app.modules.optimization.domain.worst_fit import WorstFitOptimizer
from app.modules.optimization.infrastructure.stock_adapter import InventoryStockAdapter
from tests.unit.optimization.test_first_fit import config, problem, stock
from tests.unit.optimization.test_preparation import piece
from tests.unit.optimization.test_stock import Inventory, remnant, sheet


@pytest.fixture(params=[FirstFitOptimizer, BestFitOptimizer, WorstFitOptimizer],
                ids=["FF", "BF", "WF"])
def optimizer(request):
    return request.param()


@pytest.mark.parametrize("step", [5, 90])
def test_feasible_remnant_excludes_sheets_from_evaluation(optimizer, step):
    # A tight sheet tempts BF; a large sheet tempts WF; sheet-first tempts FF.
    remnants = [stock(8, width=4, height=4, source=MaterialSource.REMNANT),
                stock(9, width=3, height=3, source=MaterialSource.REMNANT)]
    sources = [stock(1, width=2, height=2), stock(2, width=8, height=8), *remnants]
    with patch.object(RasterCache, "material", wraps=RasterCache().material) as material:
        result = optimizer.optimize(problem([piece(width=2, height=2)], sources,
                                            config(angular_step_deg=D(step))))
    assert result.complete
    assert result.placements[0].stock.source is MaterialSource.REMNANT
    assert result.placements[0].stock.material_id == {"FF": 8, "BF": 9, "WF": 8}[result.method]
    assert material.call_args_list
    assert all(call.args[0].source is MaterialSource.REMNANT for call in material.call_args_list)


@pytest.mark.parametrize("remnants", [[], [stock(8, width=1, height=1, source=MaterialSource.REMNANT)]],
                         ids=["no-remnant", "infeasible-remnant"])
def test_sheet_fallback(optimizer, remnants):
    result = optimizer.optimize(problem([piece(width=2, height=2)],
                                        [stock(1, width=3, height=3), *remnants]))
    assert result.complete
    assert result.placements[0].stock.source is MaterialSource.SHEET


@pytest.mark.parametrize("changes", [{"id_tipo_vidrio": 2}, {"espesor_mm": D(8)}],
                         ids=["different-glass", "different-thickness"])
def test_adapter_excludes_incompatible_remnant_before_optimization(optimizer, changes):
    inventory = Inventory([remnant(8, **changes)], [sheet(1)])
    prepared = with_compatible_stock(problem([piece(width=2, height=2)], []),
                                     InventoryStockAdapter(inventory))
    assert all(c.source is MaterialSource.SHEET for g in prepared.groups for c in g.stock_candidates)
    with patch.object(RasterCache, "material", wraps=RasterCache().material) as material:
        result = optimizer.optimize(prepared)
    assert result.complete
    assert all(call.args[0].source is MaterialSource.SHEET for call in material.call_args_list)
    assert all(p.stock.material_key == p.piece.material_key for p in result.placements)


@pytest.mark.parametrize("changes", [{"glass": 2}, {"thickness": 8}])
def test_domain_rejects_incompatible_candidate_without_filtering_helper(changes):
    group = problem().groups[0]
    with pytest.raises(ValueError, match="must match the material group"):
        replace(group, stock_candidates=(stock(source=MaterialSource.REMNANT, **changes),))


def test_priority_is_rechecked_per_unit_and_repeated_runs_are_identical(optimizer):
    original = problem([piece(width=2, height=2, quantity=3)],
                       [stock(1, width=4, height=4),
                        stock(8, width=2, height=2, source=MaterialSource.REMNANT)])
    before = repr(original)
    runs, events = [], []
    for _ in range(3):
        emitted = []
        runs.append(optimizer.optimize(original, emitted.append))
        events.append(emitted)
    assert runs[0] == runs[1] == runs[2]
    assert events[0] == events[1] == events[2]
    assert runs[0].complete and repr(original) == before
    assert [p.stock.source for p in runs[0].placements] == [
        MaterialSource.REMNANT, MaterialSource.SHEET, MaterialSource.SHEET]
    assert [(p.x_mm, p.y_mm) for p in runs[0].placements] == [(0, 0), (0, 0), (2, 0)]


def test_simulation_leaves_inventory_unchanged(optimizer):
    inventory = Inventory([remnant(8)], [sheet(1, cantidad=2)])
    before = repr((inventory.remnants, inventory.sheets))
    prepared = problem([piece(width=2, height=2, quantity=2)], [])
    provider = InventoryStockAdapter(inventory)
    result = optimizer.optimize(with_compatible_stock(prepared, provider))
    assert result.complete
    assert optimizer.optimize(with_compatible_stock(prepared, provider)) == result
    assert repr((inventory.remnants, inventory.sheets)) == before
