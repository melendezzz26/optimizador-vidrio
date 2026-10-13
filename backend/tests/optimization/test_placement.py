"""Pruebas de validación de colocaciones: límites y superposición (TA-007 T01, SPEC-TA-007)."""
import dataclasses

import pytest

from app.modules.optimization.domain.placement import (
    PlacementCheck,
    PlacementError,
    PlacementIssue,
    SheetLayout,
)
from app.modules.optimization.domain.rasterizer import (
    rasterize_circle,
    rasterize_material,
    rasterize_rectangle,
)

# Plancha de 100 x 50 mm con celdas de 10 mm: 5 filas x 10 columnas usables.
SHEET = {"type": "RECTANGULO", "width_mm": 100, "height_mm": 50}
PIECE = rasterize_rectangle(30, 20, 10)  # 2 filas x 3 columnas


def sheet(geometry=SHEET, resolution=10):
    return SheetLayout.empty(rasterize_material(geometry, resolution))


def test_placement_fully_inside_an_empty_sheet_is_valid():
    # CA-03.
    result = sheet().check(PIECE, 0, 0)

    assert result == PlacementCheck(True)
    assert result.issue is None


@pytest.mark.parametrize("row, column", [(0, 7), (3, 0), (3, 7)])
def test_placement_touching_the_sheet_border_from_inside_is_valid(row, column):
    # Las esquinas del área usable: la pieza llega justo al borde sin salir.
    assert sheet().check(PIECE, row, column).is_valid


@pytest.mark.parametrize("row, column", [(0, 8), (4, 0), (-1, 0), (0, -1), (10, 10)])
def test_placement_outside_the_sheet_is_out_of_bounds(row, column):
    # CA-04: se sale por la derecha, por abajo, por arriba, por la izquierda o del todo.
    assert sheet().check(PIECE, row, column) == PlacementCheck(False, PlacementIssue.OUT_OF_BOUNDS)


def test_placement_on_a_non_usable_cell_of_a_scrap_is_out_of_bounds():
    # CA-04 en un retazo triangular: la caja cabe, pero una celda cae fuera del vidrio.
    scrap = sheet({"type": "POLIGONO_CONVEXO", "vertices_mm": [[0, 0], [100, 0], [0, 100]]})
    square = rasterize_rectangle(20, 20, 10)

    assert scrap.check(square, 0, 6).is_valid
    assert scrap.check(square, 0, 7) == PlacementCheck(False, PlacementIssue.OUT_OF_BOUNDS)


def test_placement_over_another_piece_is_an_overlap():
    # CA-05.
    layout = sheet().place(PIECE, 0, 0)

    assert layout.check(PIECE, 0, 2) == PlacementCheck(False, PlacementIssue.OVERLAP)
    assert layout.check(PIECE, 1, 1) == PlacementCheck(False, PlacementIssue.OVERLAP)


def test_pieces_side_by_side_do_not_overlap():
    # Las celdas son exclusivas: una pieza puede empezar en la columna siguiente.
    layout = sheet().place(PIECE, 0, 0)

    assert layout.check(PIECE, 0, 3).is_valid
    assert layout.check(PIECE, 2, 0).is_valid


def test_out_of_bounds_is_reported_before_overlap():
    layout = sheet().place(PIECE, 3, 7)

    assert layout.check(PIECE, 4, 7).issue == PlacementIssue.OUT_OF_BOUNDS


def test_circle_fits_where_its_corners_are_free():
    # La máscara del círculo tiene las esquinas libres; solo cuentan sus celdas ocupadas.
    layout = sheet({"type": "RECTANGULO", "width_mm": 40, "height_mm": 20}, 2)
    circle = rasterize_circle(10, 2)  # 10 x 10 celdas con esquinas libres

    assert layout.place(circle, 0, 0).check(circle, 0, 10).is_valid


def test_place_returns_a_new_layout_and_keeps_the_previous_one():
    # CA-06.
    empty = sheet()
    layout = empty.place(PIECE, 0, 0)

    assert empty.check(PIECE, 0, 0).is_valid
    assert not layout.check(PIECE, 0, 0).is_valid
    assert layout.occupied[0] == 0b111
    with pytest.raises(dataclasses.FrozenInstanceError):
        layout.occupied = ()


def test_placing_in_an_invalid_position_fails():
    # CA-06.
    with pytest.raises(PlacementError, match="FUERA_DE_LIMITE"):
        sheet().place(PIECE, 0, 8)


def test_piece_and_material_must_share_the_resolution():
    # CA-10.
    with pytest.raises(PlacementError):
        sheet().check(rasterize_rectangle(30, 20, 5), 0, 0)


def test_large_sheet_accepts_many_pieces_without_overlap():
    # Plancha real 2440 x 1830 a 5 mm: una cuadrícula de piezas de 600 x 400 mm.
    layout = sheet({"type": "RECTANGULO", "width_mm": 2440, "height_mm": 1830}, 5)
    piece = rasterize_rectangle(600, 400, 5)  # 80 x 120 celdas
    for row in range(0, 4 * 80, 80):
        for column in range(0, 4 * 120, 120):
            layout = layout.place(piece, row, column)

    assert sum(bits.bit_count() for bits in layout.occupied) == 16 * piece.occupied_cells
    assert layout.check(piece, 0, 0).issue == PlacementIssue.OVERLAP