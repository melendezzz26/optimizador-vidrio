"""TA-045: shared geometry first, then the six integrated productive engines.

Distances are fixtures, not commercial defaults. The independent cell oracle
checks boundaries, margin and separation without calling layout conversion.
"""
from copy import deepcopy
from decimal import Decimal as D, localcontext
from fractions import Fraction
from itertools import combinations
import math

import pytest

from app.modules.optimization.application.comparison_catalog import CATALOG_V2
from app.modules.optimization.application.engine_execution import EngineExecutionAdapter, ExecutionScope
from app.modules.optimization.domain.packing import _empty_layout
from app.modules.optimization.domain.placement import PlacementIssue, SheetLayout
from app.modules.optimization.domain.problem import MaterialSource
from app.modules.optimization.domain.rasterizer import rasterize_material, rasterize_rectangle
from app.modules.optimization.domain.rotation import RasterCache
from app.modules.optimization.domain.run_geometry import prepare_run_geometry
from app.modules.optimization.infrastructure.comparison_v2_snapshot import decode_result_v3, encode_result_v3
from tests.unit.optimization.test_first_fit import config, problem, stock
from tests.unit.optimization.test_preparation import piece


def cells(mask, row=0, column=0):
    return {(row + y, column + x) for y, bits in enumerate(mask.rows)
            for x in range(mask.columns) if bits & (1 << x)}


def assert_geometry(result):
    """Replay official placement and independently inspect the raster cell sets."""
    prepared = prepare_run_geometry(result.problem)
    cfg = result.problem.config
    margin = math.ceil(Fraction(cfg.margin_mm) / Fraction(cfg.resolution_mm))
    separation = math.ceil(Fraction(cfg.separation_mm) / Fraction(cfg.resolution_mm))
    layouts, groups = {}, {}
    for placed in result.placements:
        identity = placed.stock.identity
        material = prepared.material(placed.stock)
        layout = layouts.get(identity) or _empty_layout(material, cfg)
        orientation = next(o.orientation for o in prepared.orientations(placed.piece)
                           if o.orientation.rotation_deg == placed.rotation_deg)
        row = Fraction(placed.y_mm) / Fraction(cfg.resolution_mm)
        column = Fraction(placed.x_mm) / Fraction(cfg.resolution_mm)
        assert row.denominator == column.denominator == 1
        row, column = int(row), int(column)
        assert placed.geometry == orientation.geometry
        occupied, inside = cells(orientation.mask, row, column), cells(material)
        assert occupied <= inside
        assert all((y + dy, x + dx) in inside for y, x in occupied
                   for dy in range(-margin, margin + 1)
                   for dx in range(-margin, margin + 1))
        assert layout.check(orientation.mask, row, column).is_valid
        layouts[identity] = layout.place(orientation.mask, row, column)
        groups.setdefault(identity, []).append(occupied)
    for group in groups.values():
        for left, right in combinations(group, 2):
            assert left.isdisjoint(right)
            assert all(max(abs(y - v), abs(x - u)) > separation
                       for y, x in left for v, u in right)


# Shared placement / packing logic, independent of the source selector.
@pytest.mark.parametrize("distance, expected", [(0, 0), (1e-10, 1), (1, 1), (1.0000000001, 2)])
def test_shared_margin_and_separation_use_exact_counts(distance, expected):
    material, unit = rasterize_rectangle(9, 9, 1), rasterize_rectangle(1, 1, 1)
    layout = SheetLayout.empty(material, margin_mm=distance, separation_mm=distance)
    assert layout.separation_cells == expected
    assert layout.check(unit, expected, expected).is_valid
    if expected:
        assert layout.check(unit, expected - 1, expected).issue is PlacementIssue.MARGIN
    placed = layout.place(unit, expected, expected)
    assert placed.check(unit, expected, 2 * expected + 1).is_valid
    if expected:
        assert placed.check(unit, expected, 2 * expected).issue is PlacementIssue.SEPARATION


@pytest.mark.parametrize("precision", [6, 28])
def test_engine_keeps_exact_decimal_counts_without_float_round_trip(precision):
    material = rasterize_rectangle(1, 1, 0.1)
    with localcontext() as context:
        context.prec = precision
        layout = _empty_layout(material, config(resolution_mm=D('0.1'),
                                               margin_mm=D('0.3'), separation_mm=D('0.3')))
    # 3 * float(0.1) is 0.30000000000000004; re-ceiling would incorrectly yield 4.
    assert layout.separation_cells == 3
    unit = rasterize_rectangle(0.1, 0.1, 0.1)
    assert layout.check(unit, 3, 3).is_valid
    assert layout.check(unit, 2, 3).issue is PlacementIssue.MARGIN


@pytest.mark.parametrize("geometry", [
    dict(type='RECTANGULO', width_mm=12, height_mm=12),
    dict(type='CIRCUNFERENCIA', radius_mm=6),
    dict(type='POLIGONO_CONVEXO', vertices_mm=[[0, 0], [12, 0], [0, 12]]),
], ids=['rectangle', 'circle', 'triangle'])
def test_margin_matches_material_boundary_for_every_origin(geometry):
    material, unit = rasterize_material(geometry, 1), rasterize_rectangle(1, 1, 1)
    inside = cells(material)
    layout = SheetLayout.empty(material, margin_mm=1.0000000001)
    for row in range(material.row_count):
        for column in range(material.columns):
            expected = all((row + dy, column + dx) in inside
                           for dy in range(-2, 3) for dx in range(-2, 3))
            assert layout.check(unit, row, column).is_valid == expected
    assert layout.check(unit, -1, 0).issue is PlacementIssue.OUT_OF_BOUNDS
    assert layout.check(unit, 0, material.columns).issue is PlacementIssue.OUT_OF_BOUNDS


def test_five_degree_rotation_respects_mask_separation_with_overlapping_boxes():
    triangle = piece(area='128') | dict(tipo_forma='POLIGONO_CONVEXO',
        geometria=dict(type='POLIGONO_CONVEXO', vertices_mm=[[0, 0], [16, 0], [0, 16]]))
    p = problem([triangle], [stock(width=40, height=40)], config(angular_step_deg=D(5)))
    oriented = next(o.orientation for o in RasterCache().orientations(p.units[0], D(1), D(5))
                    if o.orientation.rotation_deg == 5)
    mask = oriented.mask
    layout = SheetLayout.empty(rasterize_rectangle(40, 40, 1), separation_mm=1.0000000001)
    layout = layout.place(mask, 0, 0)
    positions = [(r, c) for r in range(mask.row_count) for c in range(mask.columns)
                 if layout.check(mask, r, c).is_valid]
    assert positions  # The bounding boxes overlap; acceptance uses occupied cells.
    first, second = cells(mask), cells(mask, *positions[0])
    assert all(max(abs(y - v), abs(x - u)) > 2 for y, x in first for v, u in second)


# Engine regressions: use the integrated catalog and its public identities.
@pytest.mark.parametrize("definition", CATALOG_V2, ids=lambda d: d.code)
@pytest.mark.parametrize("source", list(MaterialSource), ids=['retazo', 'plancha'])
@pytest.mark.parametrize("separation, width, expected", [
    ('0', 4, 2), ('0.0000000001', 4, 1), ('1', 5, 2),
    ('1.0000000001', 5, 1), ('1.0000000001', 6, 2),
])
def test_adjacent_pieces_physical_feasibility(definition, source, separation, width, expected):
    p = problem([piece(width=2, height=2, quantity=2)],
                [stock(width=width, height=2, source=source)],
                config(separation_mm=D(separation)))
    result = definition.optimizer_type().optimize(p)
    assert result.placed_units == expected
    assert result.complete == (expected == 2)
    assert_geometry(result)


@pytest.mark.parametrize("definition", CATALOG_V2, ids=lambda d: d.code)
@pytest.mark.parametrize("source", list(MaterialSource), ids=['retazo', 'plancha'])
def test_fractional_exact_fit_has_no_double_clearance_or_exterior_separation(definition, source):
    # 0.1 margin + 0.2 piece + 0.3 gap + 0.2 piece + 0.1 margin = 0.9 mm.
    rows = [piece(width=0.2, height=0.2, quantity=2)]
    original = deepcopy(rows)
    p = problem(rows, [stock(width=0.9, height=0.4, source=source)],
                config(resolution_mm=D('0.1'), margin_mm=D('0.1'), separation_mm=D('0.3')))
    result = definition.optimizer_type().optimize(p)
    assert result.complete
    assert sorted((p.x_mm, p.y_mm) for p in result.placements) == [(D('0.1'), D('0.1')), (D('0.6'), D('0.1'))]
    assert rows == original
    assert all(p.piece.geometry['width_mm'] == 0.2 and p.piece.geometry['height_mm'] == 0.2
               for p in result.placements)
    assert_geometry(result)


@pytest.mark.parametrize("definition", CATALOG_V2, ids=lambda d: d.code)
@pytest.mark.parametrize("shape", ['rectangle', 'circle', 'triangle'])
def test_rotated_piece_keeps_dimensions_inside_remnant_with_margin(definition, shape):
    geometry = dict(
        rectangle=dict(type='RECTANGULO', width_mm=4, height_mm=6),
        circle=dict(type='CIRCUNFERENCIA', radius_mm=6),
        triangle=dict(type='POLIGONO_CONVEXO', vertices_mm=[[0, 0], [14, 0], [0, 14]]),
    )[shape]
    rows = [piece(width=3, height=1)]
    extent = 12 if shape == 'circle' else 14
    p = problem(rows, [stock(width=extent, height=extent, source=MaterialSource.REMNANT, geometry=geometry)],
                config(margin_mm=D('1.0000000001'), separation_mm=D('1.0000000001')))
    # Use one-cell margins for a forced quarter turn in the narrow rectangle.
    if shape == 'rectangle':
        p = problem(rows, [stock(width=4, height=6, source=MaterialSource.REMNANT, geometry=geometry)],
                    config(margin_mm=D(1), separation_mm=D('1.0000000001')))
    result = definition.optimizer_type().optimize(p)
    assert result.complete
    if shape == 'rectangle':
        placed, = result.placements
        assert placed.rotation_deg == 90
        assert dict(placed.geometry) == dict(type='RECTANGULO', width_mm=1, height_mm=3)
    assert dict(result.placements[0].piece.geometry) == rows[0]['geometria']
    assert_geometry(result)


@pytest.mark.parametrize("definition", CATALOG_V2, ids=lambda d: d.code)
def test_integrated_adapter_and_result_snapshot_keep_fractional_geometry(definition):
    p = problem([piece(width=0.2, height=0.2, quantity=2)], [stock(width=0.9, height=0.4)],
                config(resolution_mm=D('0.1'), margin_mm=D('0.1'), separation_mm=D('0.3')))
    scope = ExecutionScope(comparison_id=45, execution_id=4501, method=definition.code)
    adapted = EngineExecutionAdapter(definition.code).execute(scope, p, minimum_width_mm=D(0), minimum_height_mm=D(0))
    assert adapted.error_type is None
    result = adapted.payload.result
    assert result is not None and result.complete
    assert adapted.payload.diagnostic.termination_reason == 'COMPLETED'
    restored = decode_result_v3(encode_result_v3(adapted.payload))
    assert restored == adapted.payload
    assert_geometry(restored.result)
