"""Pruebas de la rasterización del material con regla interior (TA-007 T01, SPEC-TA-007)."""
import math

import pytest

from app.modules.optimization.domain.raster_mask import RasterizationError
from app.modules.optimization.domain.rasterizer import (
    rasterize_geometry,
    rasterize_material,
    rasterize_material_circle,
    rasterize_material_polygon,
)

HEXAGON = [[250, 0], [750, 0], [1000, 433], [750, 866], [250, 866], [0, 433]]
TRIANGLE_HU007 = [[0, 0], [600, 0], [300, -450]]


def inside_convex(vertices, x, y, tolerance=1e-6):
    """True si (x, y) está dentro o sobre el borde del polígono convexo."""
    signs = set()
    for (ax, ay), (bx, by) in zip(vertices, vertices[1:] + vertices[:1]):
        cross = (bx - ax) * (y - ay) - (by - ay) * (x - ax)
        if abs(cross) > tolerance:
            signs.add(cross > 0)
    return len(signs) <= 1


def cell_corners(mask, row, column):
    size = mask.resolution_mm
    return [
        (column * size, row * size),
        ((column + 1) * size, row * size),
        (column * size, (row + 1) * size),
        ((column + 1) * size, (row + 1) * size),
    ]


def usable_cells(mask):
    for row in range(mask.row_count):
        for start, end in mask.row_runs(row):
            for column in range(start, end):
                yield row, column


def test_sheet_aligned_with_the_grid_is_exact():
    # CA-01: plancha de 2440 x 1830 mm a 5 mm.
    mask = rasterize_material({"type": "RECTANGULO", "width_mm": 2440, "height_mm": 1830}, 5)

    assert (mask.row_count, mask.columns) == (366, 488)
    assert mask.occupied_cells == 488 * 366
    assert mask.area_mm2 == 2440 * 1830


def test_partial_edge_cells_of_a_sheet_are_not_usable():
    # 802 x 603 mm: la columna 161 y la fila 121 tienen vidrio solo en parte.
    mask = rasterize_material({"type": "RECTANGULO", "width_mm": 802, "height_mm": 603}, 5)

    assert (mask.row_count, mask.columns) == (121, 161)
    assert mask.occupied_cells == 160 * 120
    assert mask.row_runs(120) == ()


def test_right_triangle_keeps_only_cells_fully_inside():
    # Cada fila de 10 mm deja 9, 8, ..., 0 celdas completas: 45 (la pieza ocupaba 55).
    mask = rasterize_material_polygon([[0, 0], [100, 0], [0, 100]], 10)
    lines = mask.to_text().splitlines()

    assert mask.occupied_cells == 45
    assert lines[0] == "#" * 9 + "."
    assert lines[-1] == "." * 10


def test_small_circle_is_drawn_as_expected():
    # Radio 10 mm a 2 mm: las filas 0 y 9 solo tocan el círculo en un punto.
    expected = [
        "..........",
        "..######..",
        *[".########."] * 6,
        "..######..",
        "..........",
    ]

    assert rasterize_material_circle(10, 2).to_text().splitlines() == expected


@pytest.mark.parametrize("vertices", [HEXAGON, TRIANGLE_HU007])
def test_no_usable_polygon_cell_leaves_the_material(vertices):
    # CA-02: las cuatro esquinas de cada celda usable están dentro del polígono real.
    mask = rasterize_material_polygon(vertices, 5)
    min_x = min(x for x, _ in vertices)
    min_y = min(y for _, y in vertices)
    moved = [[x - min_x, y - min_y] for x, y in vertices]

    for row, column in usable_cells(mask):
        for x, y in cell_corners(mask, row, column):
            assert inside_convex(moved, x, y), (row, column)


def test_no_usable_circle_cell_leaves_the_material():
    radius = 500
    mask = rasterize_material_circle(radius, 5)

    for row, column in usable_cells(mask):
        for x, y in cell_corners(mask, row, column):
            assert math.hypot(x - radius, y - radius) <= radius + 1e-6, (row, column)


@pytest.mark.parametrize(
    "geometry, real_area",
    [
        ({"type": "CIRCUNFERENCIA", "radius_mm": 500}, math.pi * 500**2),
        ({"type": "POLIGONO_CONVEXO", "vertices_mm": HEXAGON}, 0.75 * 1000 * 866),
    ],
)
def test_usable_area_never_exceeds_the_real_area(geometry, real_area):
    # CA-02: la regla interior pierde un poco de borde, nunca agrega.
    error = rasterize_material(geometry, 5).area_mm2 / real_area - 1

    assert -0.015 <= error <= 0


@pytest.mark.parametrize(
    "geometry",
    [
        {"type": "RECTANGULO", "width_mm": 802, "height_mm": 603},
        {"type": "CIRCUNFERENCIA", "radius_mm": 500},
        {"type": "POLIGONO_CONVEXO", "vertices_mm": HEXAGON},
    ],
)
def test_material_cells_are_a_subset_of_the_piece_cells(geometry):
    # Misma figura: interior ⊆ conservadora, y ambas usan la misma cuadrícula.
    interior = rasterize_material(geometry, 5)
    conservative = rasterize_geometry(geometry, 5)

    assert (interior.row_count, interior.columns) == (conservative.row_count, conservative.columns)
    for inner_bits, outer_bits in zip(interior.rows, conservative.rows):
        assert inner_bits & ~outer_bits == 0


@pytest.mark.parametrize(
    "geometry",
    [None, {"type": "OVALO"}, {"type": "RECTANGULO", "width_mm": 10}, {"type": "CIRCUNFERENCIA", "radius_mm": 0}],
)
def test_rejects_invalid_material_geometries(geometry):
    with pytest.raises(RasterizationError):
        rasterize_material(geometry, 5)