"""Pruebas de rasterización de formas estándar y del punto de entrada (TA-005, SPEC-TA-005-TA-006)."""
import math

import pytest

from app.modules.optimization.domain.raster_mask import RasterizationError
from app.modules.optimization.domain.rasterizer import (
    DEFAULT_RESOLUTION_MM,
    rasterize_circle,
    rasterize_convex_polygon,
    rasterize_geometry,
    rasterize_rectangle,
)


def test_rectangle_aligned_with_the_grid_has_exact_cells():
    # CA-01: tocar el borde de una celda no la ocupa, así que no sobra ninguna fila ni columna.
    mask = rasterize_rectangle(800, 600, 5)

    assert (mask.row_count, mask.columns) == (120, 160)
    assert mask.occupied_cells == 19_200
    assert mask.area_mm2 == 800 * 600


def test_rectangle_not_multiple_of_resolution_is_covered_by_excess():
    # CA-02: 802 mm necesita 161 columnas de 5 mm; la última queda ocupada.
    mask = rasterize_rectangle(802, 600, 5)

    assert mask.columns == 161
    assert mask.occupied_cells == 161 * 120
    assert mask.area_mm2 > 802 * 600


def test_rectangle_reuses_the_polygon_rasterizer():
    assert rasterize_rectangle(300, 200, 5) == rasterize_convex_polygon(
        [[0, 0], [300, 0], [300, 200], [0, 200]], 5
    )


def test_circle_area_error_is_small_and_never_negative():
    # CA-03: radio 500 mm a 5 mm.
    mask = rasterize_circle(500, 5)
    error = mask.area_mm2 / (math.pi * 500**2) - 1

    assert (mask.row_count, mask.columns) == (200, 200)
    assert 0 <= error <= 0.015


def test_no_point_inside_the_circle_falls_in_a_free_cell():
    # CA-05: regla conservadora con una malla de puntos.
    radius, resolution, step = 120, 10, 1.3
    mask = rasterize_circle(radius, resolution)
    for i in range(int(2 * radius / step)):
        for j in range(int(2 * radius / step)):
            x, y = i * step + 0.05, j * step + 0.05
            if (x - radius) ** 2 + (y - radius) ** 2 < radius**2:
                assert mask.is_occupied(int(y // resolution), int(x // resolution)), (x, y)


def test_circle_is_symmetric():
    rows = rasterize_circle(500, 5).to_text().splitlines()

    assert rows == rows[::-1]
    assert all(row == row[::-1] for row in rows)


def test_small_circle_is_drawn_as_expected():
    # Radio 10 mm a 2 mm: 10 x 10 celdas. En la fila 0 (y de 0 a 2) el círculo
    # va de x = 4 a x = 16, así que ocupa las columnas 2 a 7.
    expected = [
        "..######..",
        ".########.",
        *["##########"] * 6,
        ".########.",
        "..######..",
    ]

    assert rasterize_circle(10, 2).to_text().splitlines() == expected


def test_default_resolution_is_five_millimeters():
    # SP-001: resolución inicial seleccionada.
    assert DEFAULT_RESOLUTION_MM == 5.0
    assert rasterize_rectangle(100, 50).resolution_mm == 5.0


@pytest.mark.parametrize(
    "geometry, expected",
    [
        ({"type": "RECTANGULO", "width_mm": 800, "height_mm": 600}, rasterize_rectangle(800, 600)),
        ({"type": "CIRCUNFERENCIA", "radius_mm": 500}, rasterize_circle(500)),
        (
            {"type": "POLIGONO_CONVEXO", "vertices_mm": [[0, 0], [100, 0], [0, -100]]},
            rasterize_convex_polygon([[0, 0], [100, 0], [0, -100]]),
        ),
    ],
)
def test_geometry_entry_point_accepts_the_three_order_shapes(geometry, expected):
    # CA-07: mismo formato que persiste el módulo de pedidos en Pieza.geometria.
    assert rasterize_geometry(geometry) == expected


@pytest.mark.parametrize(
    "geometry",
    [
        None,
        [],
        {},
        {"type": "OVALO", "width_mm": 10, "height_mm": 5},
        {"type": "RECTANGULO", "width_mm": 10},
        {"type": "CIRCUNFERENCIA"},
        {"type": "POLIGONO_CONVEXO"},
        {"type": "RECTANGULO", "width_mm": 0, "height_mm": 5},
        {"type": "CIRCUNFERENCIA", "radius_mm": -1},
        {"type": "CIRCUNFERENCIA", "radius_mm": "500"},
    ],
)
def test_geometry_entry_point_rejects_invalid_geometries(geometry):
    # CA-08.
    with pytest.raises(RasterizationError):
        rasterize_geometry(geometry)


@pytest.mark.parametrize("resolution", [0, -5, float("nan")])
def test_standard_shapes_reject_invalid_resolution(resolution):
    with pytest.raises(RasterizationError):
        rasterize_rectangle(100, 100, resolution)
    with pytest.raises(RasterizationError):
        rasterize_circle(100, resolution)