from decimal import Decimal as D
import random

import pytest

from app.modules.optimization.domain.rotation import RasterCache, RasterPreparationError
from app.modules.optimization.domain.placement import SheetLayout
from app.modules.optimization.domain.raster_mask import RasterMask
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.application.resource_policy import DEFAULT_RASTER_BUDGET
from tests.unit.optimization.test_first_fit import stock, optimize, config
from tests.unit.optimization.test_preparation import piece


@pytest.mark.parametrize('width,height', [(2140, 3300), (4000, 4000)])
def test_commercial_mask_keeps_one_mm_and_bit_rows(width, height):
    mask = RasterCache().material(stock(width=width, height=height), D(1))
    assert (mask.columns, mask.row_count, mask.resolution_mm) == (width, height, 1)
    assert mask.occupied_cells == width * height
    assert len(mask.rows) == height and all(type(row) is int for row in mask.rows)
    with pytest.raises(ValueError):
        DEFAULT_RASTER_BUDGET.check(dict(type='RECTANGULO', width_mm=width, height_mm=height), 1)


def test_above_maximum_and_aggregate_cache_reject_before_allocation():
    with pytest.raises(RasterPreparationError, match='internal cutting budget'):
        RasterCache().material(stock(width=4001, height=4000), D(1))
    with pytest.raises(RasterPreparationError, match='cache'):
        RasterCache(max_cache_bytes=1024).material(stock(width=4000, height=4000), D(1))


def test_order_64_equivalent_eight_units_and_deterministic_result():
    rows = [piece(order=64, quantity=8, width=600, height=800)]
    candidates = [stock(width=2140, height=3300)]
    first, second = optimize(rows, candidates), optimize(rows, candidates)
    assert first == second and first.complete and first.placed_units == 8
    final, residuals = calculate_metrics(first, D(10), D(10))
    assert final.metrics.material_area_mm2 == 7062000
    assert final.metrics.placed_piece_area_mm2 == 3840000
    assert residuals and final.metrics.waste_mm2 >= 0


def test_unusable_diagonal_orientation_does_not_hide_valid_maximum_square():
    result = optimize([piece(width=4000, height=4000)], [stock(width=4000, height=4000)], config(angular_step_deg=D(45)))
    assert result.complete and result.placements[0].rotation_deg == 0


def test_bit_parallel_search_matches_exhaustive_first_fit_for_irregular_rows():
    rng = random.Random(64)
    for _ in range(200):
        material = RasterMask(1, 12, tuple(rng.getrandbits(12) for _ in range(10)))
        layout = SheetLayout.empty(material, separation_mm=rng.randrange(2), margin_mm=rng.randrange(2))
        mask = RasterMask(1, 4, tuple(rng.randrange(1, 16) for _ in range(3)))
        expected = next(((row, column) for row in range(8) for column in range(9)
                         if layout.check(mask, row, column).is_valid), None)
        assert layout.first_position(mask) == expected
        if expected:
            placed = layout.place(mask, *expected)
            expected_next = next(((row, column) for row in range(8) for column in range(9)
                                  if placed.check(mask, row, column).is_valid), None)
            assert placed.first_position(mask) == expected_next
