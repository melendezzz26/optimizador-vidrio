"""TA-045: independent raster-cell separation checks across all six methods.

The values 1 and 2 mm below are test fixtures, not commercial settings.
"""
from decimal import Decimal as D
from itertools import combinations

import pytest

from app.modules.optimization.domain.beam_search import BeamSearchOptimizer
from app.modules.optimization.domain.best_fit import BestFitOptimizer
from app.modules.optimization.domain.best_residual_fit import BestResidualFitOptimizer
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.hole_filling import HoleFillingOptimizer
from app.modules.optimization.domain.packing import _distance_cells, _empty_layout
from app.modules.optimization.domain.placement import PlacementIssue, distance_in_cells
from app.modules.optimization.domain.problem import MaterialSource
from app.modules.optimization.domain.rasterizer import rasterize_rectangle
from app.modules.optimization.domain.rotation import RasterCache
from app.modules.optimization.domain.run_geometry import prepare_run_geometry
from app.modules.optimization.domain.worst_fit import WorstFitOptimizer
from tests.unit.optimization.test_first_fit import config, problem, stock
from tests.unit.optimization.test_preparation import piece


METHODS = [FirstFitOptimizer, BestFitOptimizer, WorstFitOptimizer,
           HoleFillingOptimizer, BestResidualFitOptimizer, BeamSearchOptimizer]


def cells(mask, row, col):
    return {(row + y, col + x) for y, bits in enumerate(mask.rows)
            for x in range(mask.columns) if bits & (1 << x)}


def assert_valid_placements(result):
    """Replay official placement AND independently compare occupied raster cells."""
    prepared = prepare_run_geometry(result.problem)
    layouts, cell_sets = {}, {}
    cfg = result.problem.config
    clearance = _distance_cells(cfg.separation_mm, cfg.resolution_mm)
    for placed in result.placements:
        key = placed.stock.identity
        layout = layouts.get(key) or _empty_layout(prepared.material(placed.stock), cfg)
        orientation = next(o.orientation for o in prepared.orientations(placed.piece)
                           if o.orientation.rotation_deg == placed.rotation_deg)
        row, col = int(placed.y_mm / cfg.resolution_mm), int(placed.x_mm / cfg.resolution_mm)
        assert layout.check(orientation.mask, row, col).is_valid
        layouts[key] = layout.place(orientation.mask, row, col)
        cell_sets.setdefault(key, []).append(cells(orientation.mask, row, col))
    for groups in cell_sets.values():
        for left, right in combinations(groups, 2):
            assert all(max(abs(a - c), abs(b - d)) > clearance
                       for a, b in left for c, d in right)


@pytest.mark.parametrize('method', METHODS, ids=['FF', 'BF', 'WF', 'M4', 'M5', 'M6'])
@pytest.mark.parametrize('source', [MaterialSource.SHEET, MaterialSource.REMNANT], ids=['plancha', 'retazo'])
def test_adjacent_rectangles_fit_at_zero_but_not_with_separation(method, source):
    rows = [piece(width=2, height=2, quantity=2)]
    candidate = stock(width=4, height=2, source=source)
    zero = method().optimize(problem(rows, [candidate], config()))
    spaced = method().optimize(problem(rows, [candidate], config(separation_mm=D(1))))
    assert zero.placed_units == 2 and zero.complete
    assert spaced.placed_units == 1 and not spaced.complete
    assert_valid_placements(zero)
    assert_valid_placements(spaced)


@pytest.mark.parametrize('method', METHODS, ids=['FF', 'BF', 'WF', 'M4', 'M5', 'M6'])
def test_mixed_shapes_margin_separation_and_determinism(method):
    circle = piece(2, area='12.56') | {'tipo_forma': 'CIRCUNFERENCIA',
        'geometria': {'type': 'CIRCUNFERENCIA', 'radius_mm': 2}}
    triangle = piece(3, area='6') | {'tipo_forma': 'POLIGONO_CONVEXO',
        'geometria': {'type': 'POLIGONO_CONVEXO', 'vertices_mm': [[0, 0], [4, 0], [0, 3]]}}
    p = problem([piece(1, width=3, height=2), circle, triangle],
                [stock(width=20, height=15)],
                config(margin_mm=D(1), separation_mm=D(1), angular_step_deg=D(5)))
    result = method().optimize(p)
    assert result.complete and len(result.placements) == 3
    assert_valid_placements(result)
    assert all(p.x_mm >= 1 and p.y_mm >= 1 for p in result.placements)
    assert method().optimize(p) == result


def test_non_orthogonal_rotation_uses_occupied_cells_not_bounding_box():
    triangle = piece(1, area='128') | {'tipo_forma': 'POLIGONO_CONVEXO',
        'geometria': {'type': 'POLIGONO_CONVEXO', 'vertices_mm': [[0, 0], [16, 0], [0, 16]]}}
    p = problem([triangle], [stock(width=40, height=40)],
                config(separation_mm=D(1), angular_step_deg=D(5)))
    oriented = next(o.orientation for o in RasterCache().orientations(p.units[0], D(1), D(5))
                    if o.orientation.rotation_deg == D(5))
    assert oriented.rotation_deg == 5
    assert len(cells(oriented.mask, 0, 0)) < oriented.mask.columns * oriented.mask.row_count
    layout = _empty_layout(rasterize_rectangle(40, 40, 1), p.config)
    layout = layout.place(oriented.mask, 0, 0)
    # At least one legal origin exists whose bounding boxes overlap; full mask is decisive.
    candidates = [(r, c) for r in range(oriented.mask.row_count)
                  for c in range(oriented.mask.columns)
                  if layout.check(oriented.mask, r, c).is_valid]
    assert candidates
    row, col = candidates[0]
    first, second = cells(oriented.mask, 0, 0), cells(oriented.mask, row, col)
    assert all(max(abs(a-c), abs(b-d)) > 1 for a, b in first for c, d in second)


def test_exact_ceil_and_independent_margin_vs_separation():
    assert _distance_cells(D('0.00000000001'), D(1)) == 1
    assert _distance_cells(D('2.01'), D(2)) == 2
    assert distance_in_cells(1e-12, 1, 'Separación') == 1
    assert distance_in_cells(1.0000000001, 1, 'Separación') == 2
    assert distance_in_cells(0.07, 0.01, 'Separación') == 7
    fractional = _empty_layout(rasterize_rectangle(1, 1, 0.1),
                               config(resolution_mm=D('0.1'), separation_mm=D('0.3')))
    assert fractional.separation_cells == 3
    material, square = rasterize_rectangle(7, 5, 1), rasterize_rectangle(2, 2, 1)
    layout = _empty_layout(material, config(margin_mm=D(1), separation_mm=D(1)))
    assert layout.check(square, 0, 0).issue is PlacementIssue.MARGIN
    layout = layout.place(square, 1, 1)
    assert layout.check(square, 1, 3).issue is PlacementIssue.SEPARATION
    assert layout.check(square, 1, 4).is_valid
