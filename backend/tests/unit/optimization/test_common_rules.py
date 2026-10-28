"""SP-002: cross-method contracts missing from the existing shared suites."""
from decimal import Decimal as D

import pytest

from app.modules.optimization.domain.best_fit import BestFitOptimizer
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.worst_fit import WorstFitOptimizer
from tests.unit.optimization.test_first_fit import config, problem, stock
from tests.unit.optimization.test_preparation import piece

METHODS = [FirstFitOptimizer, BestFitOptimizer, WorstFitOptimizer]


@pytest.mark.parametrize("optimizer", METHODS)
@pytest.mark.parametrize("resolution,margin,separation", [(1, 1, 1), (2, 1, 1)])
def test_nonzero_distances_use_same_conservative_cells_and_first_position(
    optimizer, resolution, margin, separation,
):
    cfg = config(resolution_mm=D(resolution), margin_mm=D(margin),
                 separation_mm=D(separation), angular_step_deg=D(5))
    original = problem([piece(width=2, height=2, quantity=2)],
                       [stock(width=12, height=8)], cfg)
    before = repr(original)
    result = optimizer().optimize(original)
    # Ceil to one raster cell: first usable origin, then first separated origin.
    assert [(p.x_mm, p.y_mm, p.rotation_deg) for p in result.placements] == [
        (resolution, resolution, 0), (2 * resolution + 2, resolution, 0)]
    assert result.problem.config == cfg
    assert repr(original) == before
    assert optimizer().optimize(original) == result


@pytest.mark.parametrize("optimizer", METHODS)
def test_unplaceable_unit_does_not_skip_smaller_units_or_invent_physical_stock(optimizer):
    original = problem([piece(1, width=9, height=9),
                        piece(2, width=2, height=2, quantity=3)],
                       [stock(width=2, height=2, physical=i) for i in (1, 2)],
                       config(angular_step_deg=D(5)))
    before = repr(original)
    result = optimizer().optimize(original)
    assert result.total_units == 4 and result.placed_units == 2 and not result.complete
    assert [(p.piece.identity, p.stock.physical_unit_index) for p in result.placements] == [
        ((2, 1), 1), ((2, 2), 2)]
    assert [u.identity for u in result.unplaced_units] == [(1, 1), (2, 3)]
    assert repr(original) == before
    assert optimizer().optimize(original) == result
