from dataclasses import replace
from decimal import Decimal as D
from unittest.mock import patch

import pytest

from app.modules.optimization.domain.problem import MaterialSource, PieceUnit, StockCandidate
from app.modules.optimization.domain.rasterizer import rasterize_geometry, rasterize_material
from app.modules.optimization.domain.rotation import (
    RasterCache, RasterPreparationError, discrete_angles, normalized_angle, oriented_geometry, raster_number,
)


def unit(geometry=None):
    return PieceUnit(order_id=1, piece_id=1, unit_index=1, glass_type_id=1,
                     thickness_mm=D(6), area_mm2=D(8),
                     geometry=geometry or dict(type="RECTANGULO", width_mm=4, height_mm=2))


@pytest.mark.parametrize("step,count,last", [(90, 4, 270), (45, 8, 315), (5, 72, 355),
                                            (360, 1, 0), (100, 4, 300), (D("22.5"), 16, D("337.5"))])
def test_decimal_sequence_and_no_360(step, count, last):
    angles = discrete_angles(step)
    assert len(angles) == count and angles[-1] == last
    assert all(type(a) is D and 0 <= a < 360 for a in angles)
    assert angles == tuple(D(step) * i for i in range(count))


@pytest.mark.parametrize("step", [0, -1, 361, None, True, 5.0, D("NaN"), D("Infinity")])
def test_invalid_step_is_never_defaulted(step):
    with pytest.raises(ValueError):
        discrete_angles(step)


@pytest.mark.parametrize("angle,expected", [(-90, 270), (360, 0), (450, 90)])
def test_normalized_angle(angle, expected):
    assert normalized_angle(angle) == expected


def test_rectangle_quarter_turns_deduplicate_only_equal_full_masks():
    prepared = RasterCache().orientations(unit(), D(1), D(90))
    assert [p.orientation.rotation_deg for p in prepared] == [0, 90]
    assert [(p.orientation.mask.columns, p.orientation.mask.row_count) for p in prepared] == [(4, 2), (2, 4)]
    assert all(p.unit == unit() for p in prepared)
    assert prepared[1].orientation.geometry == dict(type="RECTANGULO", width_mm=2, height_mm=4)


def test_square_mask_symmetry_and_circle_only_once_even_with_different_steps():
    cache = RasterCache()
    square = unit(dict(type="RECTANGULO", width_mm=4, height_mm=4))
    assert len(cache.orientations(square, D(1), D(90))) == 1
    circle = unit(dict(type="CIRCUNFERENCIA", radius_mm=2))
    with patch("app.modules.optimization.domain.rotation.rasterize_geometry", wraps=rasterize_geometry) as raster:
        a = cache.orientations(circle, D(1), D(5))
        b = cache.orientations(replace(circle, unit_index=2), D(1), D(45))
        assert raster.call_count == 1
    assert a[0].orientation is b[0].orientation
    assert a[0].unit.unit_index == 1 and b[0].unit.unit_index == 2


def test_polygon_angles_local_contour_legacy_compatibility_and_original_untouched():
    geometry = dict(type="POLIGONO_CONVEXO", vertices_mm=[[-3, -1], [4, -1], [-2, 3]])
    piece = unit(geometry)
    prepared = RasterCache().orientations(piece, D("0.5"), D(45))
    assert prepared and prepared[0].orientation.rotation_deg == 0
    for oriented in prepared:
        value = oriented.orientation
        vertices = value.geometry["vertices_mm"]
        assert min(x for x, _ in vertices) == 0 and min(y for _, y in vertices) == 0
        assert value.mask == rasterize_geometry(dict(value.geometry), 0.5)
    assert piece.geometry["vertices_mm"][0] == (-3, -1)


def test_five_degree_rotation_contains_sampled_interior_points():
    from tests.optimization.test_rasterize_polygon import inside_convex
    prepared = RasterCache().orientations(unit(), D("0.5"), D(5))
    assert len(prepared) > 2
    for entry in prepared:
        geometry, mask = entry.orientation.geometry, entry.orientation.mask
        if geometry["type"] != "POLIGONO_CONVEXO":
            continue
        vertices = geometry["vertices_mm"]
        for row in range(mask.row_count):
            for column in range(mask.columns):
                for dx, dy in [(0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8)]:
                    if inside_convex(vertices, (column + dx) * .5, (row + dy) * .5):
                        assert mask.is_occupied(row, column)


def test_cache_hits_and_separation_by_geometry_resolution_and_angle():
    cache = RasterCache()
    with patch("app.modules.optimization.domain.rotation.rasterize_geometry", wraps=rasterize_geometry) as raster:
        first = cache.orientations(unit(), D(1), D(90))
        assert raster.call_count == 4  # equality dedup happens after rasterization
        again = cache.orientations(replace(unit(), piece_id=2), D(1), D(90))
        assert raster.call_count == 4 and first[0].orientation is again[0].orientation
        cache.orientations(unit(), D("0.5"), D(90))
        assert raster.call_count == 8
        cache.orientations(unit(), D(1), D(45))
        assert raster.call_count == 12  # 4 existing angles, 4 new
        cache.orientations(unit(dict(type="RECTANGULO", width_mm=5, height_mm=2)), D(1), D(90))
        assert raster.call_count == 16


def test_material_is_interior_mask_and_cache_does_not_fill_irregular_bbox():
    stock = StockCandidate(source=MaterialSource.REMNANT, material_id=1, physical_unit_index=1,
                           glass_type_id=1, thickness_mm=D(6), area_mm2=D(8),
                           geometry=dict(type="POLIGONO_CONVEXO", vertices_mm=[[0, 0], [4, 0], [0, 4]]))
    cache = RasterCache()
    with patch("app.modules.optimization.domain.rotation.rasterize_material", wraps=rasterize_material) as raster:
        mask = cache.material(stock, D(1))
        assert cache.material(stock, D(1)) is mask and raster.call_count == 1
    assert not mask.is_occupied(3, 3)
    assert mask.occupied_cells < mask.columns * mask.row_count


def test_explicit_decimal_bridge_and_safe_budget_failures():
    assert raster_number(D("0.1")) == 0.1
    with pytest.raises(RasterPreparationError):
        raster_number(D("0.10000000000000000000001"))
    with pytest.raises(RasterPreparationError):
        RasterCache(max_cells=1).orientations(unit(), D(1), D(90))
    with pytest.raises(RasterPreparationError):
        discrete_angles(D("0.000001"))


def test_rn04_rounding_is_explicit_and_same_contour_is_returned():
    geometry = oriented_geometry(unit().geometry, D(45))
    for point in geometry["vertices_mm"]:
        assert all(round(value, 6) == value for value in point)
    assert oriented_geometry(unit().geometry, D(-90)) == oriented_geometry(unit().geometry, D(270))
