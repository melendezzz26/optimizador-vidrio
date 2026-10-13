"""Pruebas de rasterización de polígonos convexos (TA-006, SPEC-TA-005-TA-006)."""
import math

import pytest

from app.modules.optimization.domain.raster_mask import RasterizationError
from app.modules.optimization.domain.rasterizer import rasterize_convex_polygon

HEXAGON = [[250, 0], [750, 0], [1000, 433], [750, 866], [250, 866], [0, 433]]


def polygon_area(vertices):
    """Fórmula del cordón (shoelace)."""
    total = 0.0
    for (ax, ay), (bx, by) in zip(vertices, vertices[1:] + vertices[:1]):
        total += ax * by - bx * ay
    return abs(total) / 2


def inside_convex(vertices, x, y):
    """True si (x, y) está estrictamente dentro del polígono convexo."""
    signs = set()
    for (ax, ay), (bx, by) in zip(vertices, vertices[1:] + vertices[:1]):
        cross = (bx - ax) * (y - ay) - (by - ay) * (x - ax)
        if abs(cross) < 1e-9:
            return False
        signs.add(cross > 0)
    return len(signs) == 1


def test_right_triangle_covers_every_touched_cell():
    # Cada fila de 10 mm toca 10, 9, ..., 1 celdas: 55 en total (área real 5000 mm²).
    mask = rasterize_convex_polygon([[0, 0], [100, 0], [0, 100]], 10)

    assert (mask.row_count, mask.columns) == (10, 10)
    assert mask.occupied_cells == 55
    assert mask.to_text().splitlines()[0] == "#" * 10
    assert mask.to_text().splitlines()[-1] == "#" + "." * 9


def test_hexagon_area_error_is_small_and_never_negative():
    # CA-04: a 5 mm el error de la regla conservadora está entre 0 % y 1.5 %.
    mask = rasterize_convex_polygon(HEXAGON, 5)
    error = mask.area_mm2 / polygon_area(HEXAGON) - 1

    assert (mask.row_count, mask.columns) == (174, 200)
    assert 0 <= error <= 0.015


def test_no_interior_point_falls_in_a_free_cell():
    # CA-05: regla conservadora comprobada con una malla de puntos interiores.
    resolution = 5
    mask = rasterize_convex_polygon(HEXAGON, resolution)
    step = 3.7
    for i in range(int(1000 / step)):
        for j in range(int(866 / step)):
            x, y = i * step + 0.1, j * step + 0.1
            if inside_convex(HEXAGON, x, y):
                assert mask.is_occupied(int(y // resolution), int(x // resolution)), (x, y)


def test_translation_and_vertex_order_do_not_change_the_mask():
    # CA-06 y formato de HU-007: origen en el primer vértice, coordenadas negativas.
    reference = rasterize_convex_polygon(HEXAGON, 5)
    moved = [[x - 250.5, y - 433.25] for x, y in HEXAGON]

    assert rasterize_convex_polygon(moved, 5) == reference
    assert rasterize_convex_polygon(HEXAGON[::-1], 5) == reference


def test_rectangle_rotated_with_cos_and_sin_keeps_exact_cells():
    # RN-04: sin redondeo, el residuo de cos(90°) agregaría una fila de más.
    angle = math.radians(90)
    rotated = [
        [x * math.cos(angle) - y * math.sin(angle), x * math.sin(angle) + y * math.cos(angle)]
        for x, y in [[0, 0], [800, 0], [800, 600], [0, 600]]
    ]
    mask = rasterize_convex_polygon(rotated, 5)

    assert (mask.row_count, mask.columns) == (160, 120)
    assert mask.occupied_cells == 19_200


def test_piece_thinner_than_a_cell_still_occupies_whole_cells():
    # RN-07: una tira de 30 mm a 20 mm ocupa 2 filas (40 mm).
    mask = rasterize_convex_polygon([[0, 0], [1500, 0], [1500, 30], [0, 30]], 20)

    assert (mask.row_count, mask.columns) == (2, 75)
    assert mask.occupied_cells == 150


def test_same_input_gives_same_mask():
    assert rasterize_convex_polygon(HEXAGON, 5) == rasterize_convex_polygon(HEXAGON, 5)


def test_does_not_modify_the_input():
    vertices = [list(vertex) for vertex in HEXAGON]
    rasterize_convex_polygon(vertices, 5)

    assert vertices == HEXAGON


@pytest.mark.parametrize(
    "vertices",
    [
        [[0, 0], [10, 0]],
        [[0, 0], [10, 0], [10]],
        [[0, 0], [10, 0], ["10", 10]],
        [[0, 0], [10, 0], [float("nan"), 10]],
        [[0, 0], [10, 0], [True, 10]],
        [[0, 0], [10, 0], [20, 0]],
        "no es una lista",
    ],
)
def test_rejects_invalid_vertices(vertices):
    with pytest.raises(RasterizationError):
        rasterize_convex_polygon(vertices, 5)


@pytest.mark.parametrize("resolution", [0, -1, float("nan"), None])
def test_rejects_invalid_resolution(resolution):
    with pytest.raises(RasterizationError):
        rasterize_convex_polygon(HEXAGON, resolution)