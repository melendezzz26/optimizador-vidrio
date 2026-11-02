"""HU-018: reglas de cada fila del archivo de importación (SPEC-HU-018 §4 y §5)."""
import pytest

from app.modules.orders.domain.bulk_import import OBSERVADO, VALIDO, interpret_row, interpret_rows, split_values

PARALLELOGRAM = [[0, 0], [120, 0], [40, 138.564065], [-80, 138.564065]]


def rows(*texts):
    return list(enumerate(texts, start=1))


# --- Filas válidas ---------------------------------------------------------------

@pytest.mark.parametrize("texto, tipo, cantidad, medidas", [
    ("R,3,800,600", "RECTANGULO", 3, {"width_mm": 800, "height_mm": 600}),
    ("r, 2, 1200.5, 450", "RECTANGULO", 2, {"width_mm": 1200.5, "height_mm": 450}),
    ("C,2,150", "CIRCUNFERENCIA", 2, {"radius_mm": 150}),
    (" c , 7 , 25 ", "CIRCUNFERENCIA", 7, {"radius_mm": 25}),
    ("P,1,{{120,60},{160,120},{120,60},{160,120}}", "POLIGONO_CONVEXO", 1, {"vertices_mm": PARALLELOGRAM}),
    ("P,4,{120,60},{160,120},{120,60},{160,120}", "POLIGONO_CONVEXO", 4, {"vertices_mm": PARALLELOGRAM}),
    ("P,1,{{ 120 , 60 }, {160,120}, {120,60}, {160,120}}", "POLIGONO_CONVEXO", 1, {"vertices_mm": PARALLELOGRAM}),
])
def test_valid_rows_use_the_manual_registration_fields(texto, tipo, cantidad, medidas):
    row = interpret_row(5, texto)
    assert (row.fila, row.estado, row.tipo_forma, row.cantidad, row.medidas, row.causas) == (
        5, VALIDO, tipo, cantidad, medidas, [])


@pytest.mark.parametrize("texto", [
    "P,1,{{300,90},{200,90},{300,90},{200,}}",   # ángulo vacío con coma
    "P,1,{{300,90},{200,90},{300,90},{200}}",    # ángulo vacío sin coma
])
def test_empty_angle_is_calculated(texto):
    row = interpret_row(1, texto)
    assert row.estado == VALIDO
    assert row.medidas == {"vertices_mm": [[0, 0], [300, 0], [300, 200], [0, 200]]}


def test_triangle_without_angles():
    assert interpret_row(1, "P,1,{{300,},{400,},{500,}}").medidas == {"vertices_mm": [[0, 0], [300, 0], [300, 400]]}


def test_the_same_row_always_gives_the_same_vertices():
    texto = "P,2,{{120,100},{90,},{140,110},{70,},{110,}}"
    assert interpret_row(1, texto) == interpret_row(1, texto)


# --- Filas observadas: nunca se descartan ni se completan -------------------------

@pytest.mark.parametrize("texto, causas", [
    ("X,1,100", ["Tipo de pieza desconocido"]),
    ("C", ["Falta la cantidad", "Faltan dimensiones"]),
    ("C,abc,5", ["Cantidad inválida"]),
    ("C,0,150", ["Cantidad debe ser un entero mayor a 0"]),
    ("C,-3,150", ["Cantidad debe ser un entero mayor a 0"]),
    ("R,2.5,10,10", ["Cantidad debe ser un entero mayor a 0"]),
    ("C,2", ["Faltan dimensiones"]),
    ("C,2,-5", ["Radio inválido"]),
    ("C,2,0", ["Radio inválido"]),
    ("C,2,inf", ["Radio inválido"]),
    ("R,3,800", ["Faltan dimensiones"]),
    ("R,3,800,", ["Faltan dimensiones"]),
    ("R,3,800,600,5", ["Sobran valores en la fila"]),
    ("R,3,0,600", ["Largo inválido"]),
    ("R,3,800,-1", ["Ancho inválido"]),
    ("R,0,-1,0", ["Cantidad debe ser un entero mayor a 0", "Largo inválido", "Ancho inválido"]),
    ("P,1,", ["Faltan dimensiones"]),
    ("P,1,{{120,60},{160", ["Formato de polígono inválido"]),
    ("P,1,{{100,90}{100,90}{100,90}}", ["Formato de polígono inválido"]),
    ("P,1,{{100,90,3},{100,90},{100,90}}", ["Formato de polígono inválido"]),
    ("P,1,{{100,60},{100,60}}", ["Un polígono necesita al menos 3 lados"]),
    ("P,1,{{-1,90},{100,90},{100,90}}", ["Lado 1 inválido"]),
    ("P,1,{{100,90},{100,180},{100,90}}", ["Ángulo 2 inválido: debe estar entre 0 y 180"]),
    ("P,1,{{100,90},{100,abc},{100,90}}", ["Ángulo 2 inválido: debe estar entre 0 y 180"]),
    ("P,1,{{100,},{100,},{100,},{100,}}", ["Faltan ángulos para definir el polígono"]),
    ("P,1,{{120,35},{160,35},{120,45},{160,60}}", ["Los lados y ángulos no forman un polígono cerrado"]),
    ("P,1,{{10,},{10,},{100,}}", ["Los lados y ángulos no forman un polígono cerrado"]),
])
def test_invalid_rows_are_observed_with_their_cause(texto, causas):
    row = interpret_row(9, texto)
    assert (row.fila, row.texto, row.estado, row.causas) == (9, texto, OBSERVADO, causas)
    assert row.cantidad is None and row.medidas is None


def test_polygon_with_more_than_128_sides_is_observed():
    texto = "P,1,{" + ",".join("{10,178}" for _ in range(129)) + "}"
    assert interpret_row(1, texto).causas == ["El polígono supera el máximo de 128 lados"]


def test_observed_row_keeps_its_original_text_and_type():
    row = interpret_row(3, "  R,3,800  ")
    assert (row.texto, row.tipo_forma) == ("R,3,800", "RECTANGULO")


# --- Varias filas -----------------------------------------------------------------

def test_header_and_empty_rows_are_ignored_but_numbered_rows_are_kept():
    result = interpret_rows(rows("tipo,cantidad,medidas", "", "R,3,800,600", ",,", "C,2,150"))
    assert [(r.fila, r.estado) for r in result] == [(3, VALIDO), (5, VALIDO)]


def test_a_first_row_with_numbers_is_not_a_header():
    result = interpret_rows(rows("X,1,100", "R,3,800,600"))
    assert [(r.fila, r.estado, r.causas) for r in result] == [
        (1, OBSERVADO, ["Tipo de pieza desconocido"]), (2, VALIDO, [])]


def test_only_the_first_content_row_can_be_a_header():
    result = interpret_rows(rows("tipo,cantidad,medidas", "R,1,10,10", "otra cosa"))
    assert [(r.fila, r.estado) for r in result] == [(2, VALIDO), (3, OBSERVADO)]


def test_mixed_file_keeps_every_row_in_order():
    result = interpret_rows(rows("R,3,800,600", "C,0,150", "P,1,{{120,60},{160,120},{120,60},{160,120}}", "X,1,1"))
    assert [r.estado for r in result] == [VALIDO, OBSERVADO, VALIDO, OBSERVADO]


def test_commas_inside_braces_do_not_split_values():
    assert split_values("P,1,{{120,60},{160,120}}") == ["P", "1", "{{120,60},{160,120}}"]
    assert split_values("P,1,{{120,60}") is None