"""Pruebas de validación de colocaciones (TA-007 T01 y T02, SPEC-TA-007)."""
import dataclasses

import pytest

from app.modules.optimization.domain.placement import (
    PlacementCheck,
    PlacementError,
    PlacementIssue,
    SheetLayout,
    distance_in_cells,
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
    
    
# --- T02: margen y separación ---------------------------------------------------

CELL = rasterize_rectangle(10, 10, 10)  # 1 x 1 celda


def configured(margin_mm=0, separation_mm=0, geometry=SHEET, resolution=10):
    material = rasterize_material(geometry, resolution)
    return SheetLayout.empty(material, margin_mm=margin_mm, separation_mm=separation_mm)


@pytest.mark.parametrize("row, column", [(0, 0), (0, 3), (3, 1), (1, 7), (1, 0)])
def test_placement_closer_to_the_border_than_the_margin_is_rejected(row, column):
    # CA-07: con 10 mm de margen la fila 0, la fila 4, la columna 0 y la columna 9 quedan fuera.
    result = configured(margin_mm=10).check(PIECE, row, column)

    assert result == PlacementCheck(False, PlacementIssue.MARGIN)


@pytest.mark.parametrize("row, column", [(1, 1), (2, 6), (1, 6), (2, 1)])
def test_placement_that_respects_the_margin_is_valid(row, column):
    # CA-07: el área usable queda en filas 1 a 3 y columnas 1 a 8.
    assert configured(margin_mm=10).check(PIECE, row, column).is_valid


def test_margin_follows_the_edge_of_a_scrap():
    # CA-07 en un retazo triangular: el margen también se mide desde la hipotenusa.
    scrap = {"type": "POLIGONO_CONVEXO", "vertices_mm": [[0, 0], [100, 0], [0, 100]]}
    square = rasterize_rectangle(20, 20, 10)

    assert configured(geometry=scrap).check(square, 1, 4).is_valid
    assert configured(margin_mm=10, geometry=scrap).check(square, 1, 4).issue == PlacementIssue.MARGIN
    assert configured(margin_mm=10, geometry=scrap).check(square, 1, 3).is_valid


def test_placement_closer_to_another_piece_than_the_separation_is_rejected():
    # CA-08: con 10 mm de separación debe quedar al menos una celda libre entre piezas.
    layout = configured(separation_mm=10).place(PIECE, 0, 0)

    assert layout.check(PIECE, 0, 3) == PlacementCheck(False, PlacementIssue.SEPARATION)
    assert layout.check(PIECE, 2, 0) == PlacementCheck(False, PlacementIssue.SEPARATION)


def test_placement_that_respects_the_separation_is_valid():
    # CA-08.
    layout = configured(separation_mm=10).place(PIECE, 0, 0)

    assert layout.check(PIECE, 0, 4).is_valid
    assert layout.check(PIECE, 3, 0).is_valid


def test_separation_is_also_required_in_diagonal():
    # RN-07: la vecindad es cuadrada, así que la esquina vecina en diagonal también cuenta.
    layout = configured(separation_mm=10).place(PIECE, 0, 0)

    assert layout.check(PIECE, 2, 3).issue == PlacementIssue.SEPARATION
    assert layout.check(PIECE, 3, 4).is_valid


def test_issues_are_reported_in_the_specified_order():
    # RN-08: límite, margen, superposición y separación, en ese orden.
    layout = configured(margin_mm=10, separation_mm=10).place(PIECE, 1, 1)

    assert layout.check(PIECE, 0, 8).issue == PlacementIssue.OUT_OF_BOUNDS
    assert layout.check(PIECE, 0, 1).issue == PlacementIssue.MARGIN
    assert layout.check(PIECE, 1, 2).issue == PlacementIssue.OVERLAP
    assert layout.check(PIECE, 1, 4).issue == PlacementIssue.SEPARATION
    assert layout.check(PIECE, 1, 5).is_valid


@pytest.mark.parametrize(
    "distance_mm, resolution, expected",
    [(0, 10, 0), (1, 10, 1), (10, 10, 1), (11, 10, 2), (12.5, 5, 3), (15, 5, 3), (3, 2, 2)],
)
def test_distances_are_rounded_up_to_whole_cells(distance_mm, resolution, expected):
    # CA-09 / RN-06: nunca se aplica menos distancia que la configurada.
    assert distance_in_cells(distance_mm, resolution, "La distancia") == expected


def test_rounding_up_is_applied_to_the_layout():
    # CA-09: 1 mm ya ocupa una celda completa y 11 mm ocupan dos.
    assert configured(margin_mm=1).check(CELL, 0, 0).issue == PlacementIssue.MARGIN
    assert configured(margin_mm=10).check(CELL, 1, 1).is_valid
    assert configured(margin_mm=11).check(CELL, 1, 2).issue == PlacementIssue.MARGIN
    assert configured(margin_mm=11).check(CELL, 2, 2).is_valid

    layout = configured(separation_mm=11).place(CELL, 0, 0)
    assert layout.check(CELL, 0, 2).issue == PlacementIssue.SEPARATION
    assert layout.check(CELL, 0, 3).is_valid


def test_zero_margin_and_separation_behave_like_t01():
    # CA-09: con 0 el resultado coincide con la validación de T01 en todas las posiciones.
    plain = sheet().place(PIECE, 1, 2)
    zeros = configured(margin_mm=0, separation_mm=0).place(PIECE, 1, 2)

    for row in range(-1, 6):
        for column in range(-1, 11):
            assert zeros.check(PIECE, row, column) == plain.check(PIECE, row, column)
    assert zeros.blocked == zeros.occupied


@pytest.mark.parametrize("value", [-1, -0.5, float("nan"), float("inf"), "10", None, True])
@pytest.mark.parametrize("field", ["margin_mm", "separation_mm"])
def test_invalid_margin_or_separation_raises(field, value):
    # CA-10.
    with pytest.raises(PlacementError, match="mayor o igual a cero"):
        configured(**{field: value})


def test_place_keeps_margin_and_separation_and_does_not_change_the_previous_layout():
    # RN-09 con T02.
    empty = configured(margin_mm=10, separation_mm=10)
    layout = empty.place(PIECE, 1, 1)

    assert layout.usable == empty.usable
    assert layout.separation_cells == empty.separation_cells == 1
    assert empty.blocked == empty.occupied == (0, 0, 0, 0, 0)
    assert layout.check(PIECE, 1, 4).issue == PlacementIssue.SEPARATION


def test_real_sheet_with_margin_and_separation():
    # Plancha 2440 x 1830 a 5 mm con 10 mm de margen (2 celdas) y 5 mm de separación (1 celda).
    layout = configured(10, 5, {"type": "RECTANGULO", "width_mm": 2440, "height_mm": 1830}, 5)
    piece = rasterize_rectangle(600, 400, 5)  # 80 x 120 celdas

    assert layout.check(piece, 1, 2).issue == PlacementIssue.MARGIN
    layout = layout.place(piece, 2, 2)
    assert layout.check(piece, 2, 122).issue == PlacementIssue.SEPARATION
    assert layout.check(piece, 2, 123).is_valid