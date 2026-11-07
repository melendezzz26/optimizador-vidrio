"""HU-018: lectura de CSV y XLSX como filas de texto (SPEC-HU-018 §4.6)."""
from io import BytesIO

import pytest
from openpyxl import Workbook

from app.modules.orders.application.bulk_import import ImportFileError, PreviewImportUseCase
from app.modules.orders.infrastructure.spreadsheet_reader import file_name, read_rows

POLYGON = "{{120,60},{160,120},{120,60},{160,120}}"


def xlsx(*rows):
    workbook = Workbook()
    for row in rows:
        workbook.active.append(list(row))
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_csv_lines_keep_their_numbers_with_or_without_bom():
    content = "tipo,cantidad,medidas\r\nR,3,800,600\n\nC,2,150".encode("utf-8")
    expected = [(1, "tipo,cantidad,medidas"), (2, "R,3,800,600"), (3, ""), (4, "C,2,150")]
    assert read_rows("piezas.csv", content) == expected
    assert read_rows("PIEZAS.CSV", b"\xef\xbb\xbf" + content) == expected


def test_xlsx_with_three_columns_reads_like_the_csv():
    rows = read_rows("piezas.xlsx", xlsx(("R", 3, "800,600"), ("C", 2, 150), ("P", 1, POLYGON)))
    assert rows == [(1, "R,3,800,600"), (2, "C,2,150"), (3, f"P,1,{POLYGON}")]


def test_xlsx_with_the_row_in_one_cell_or_split_polygon():
    rows = read_rows("piezas.xlsx", xlsx(("R,3,800,600",), ("P", 1, "{{120", "60}", "{160", "120}}"),
                                         ("R", 1, 12.5, 7.0)))
    assert rows == [(1, "R,3,800,600"), (2, "P,1,{{120,60},{160,120}}"), (3, "R,1,12.5,7")]


def test_xlsx_empty_rows_stay_empty():
    rows = read_rows("piezas.xlsx", xlsx(("R", 1, 10, 10), (), ("C", 1, 5)))
    assert [text for _, text in rows] == ["R,1,10,10", "", "C,1,5"]


@pytest.mark.parametrize("cells,expected", [
    (("R", None, 2, 800, 600), "R,,2,800,600"),
    (("C", 1, None, 150), "C,1,,150"),
    (("R", 1, None, 800, 600), "R,1,,800,600"),
    (("R", 1, 800, None, 600), "R,1,800,,600"),
    (("P", None, 1, "{{300,},{400,},{500,}}"), "P,,1,{{300,},{400,},{500,}}"),
    (("P", 1, "{{300,}", None, "{400,},{500,}}"), "P,1,{{300,},,{400,},{500,}}"),
])
def test_xlsx_preserves_missing_intermediate_cells_and_observes_row(cells, expected):
    rows = read_rows("piezas.xlsx", xlsx(cells))
    assert rows == [(1, expected)]
    row = PreviewImportUseCase().execute("piezas.xlsx", rows)["filas"][0]
    assert row["estado"] == "OBSERVADO"
    assert row["cantidad"] is None and row["medidas"] is None


def test_csv_keeps_missing_intermediate_quantity():
    rows = read_rows("piezas.csv", b"R,,2,800,600")
    assert rows == [(1, "R,,2,800,600")]
    assert PreviewImportUseCase().execute("piezas.csv", rows)["filas"][0]["estado"] == "OBSERVADO"


@pytest.mark.parametrize("name", ["piezas.txt", "piezas.xls", "piezas", "", None])
def test_other_extensions_are_rejected(name):
    with pytest.raises(ImportFileError, match=r"\.csv o \.xlsx"):
        read_rows(name, b"R,1,10,10")


@pytest.mark.parametrize("name, content", [
    ("piezas.csv", "R,1,10,10".encode("utf-16")),
    ("piezas.xlsx", b"esto no es un xlsx"),
])
def test_unreadable_files_are_rejected_without_details(name, content):
    with pytest.raises(ImportFileError) as error:
        read_rows(name, content)
    assert str(error.value) == "No se pudo leer el archivo. Verifica el formato."


def test_file_name_never_keeps_paths():
    assert file_name("C:\\Users\\Ana\\piezas.csv") == "piezas.csv"
    assert file_name("../../piezas.xlsx") == "piezas.xlsx"
    assert file_name(None) == ""


def test_csv_with_too_many_lines_is_rejected_even_if_they_are_empty():
    assert len(read_rows("piezas.csv", b"\n" * 1999 + b"C,1,10")) == 2000
    with pytest.raises(ImportFileError, match="2000 filas, contando las vacías"):
        read_rows("piezas.csv", b"\n" * 2000 + b"C,1,10")


def test_xlsx_stops_reading_after_2000_rows_even_if_they_are_empty():
    assert len(read_rows("piezas.xlsx", xlsx(*[("",)] * 1999, ("C", 1, 10)))) == 2000
    with pytest.raises(ImportFileError, match="2000 filas, contando las vacías"):
        read_rows("piezas.xlsx", xlsx(*[("",)] * 2000, ("C", 1, 10)))


def test_xlsx_row_with_too_many_columns_is_rejected():
    assert read_rows("piezas.xlsx", xlsx(("C", 1, 10) + ("",) * 297)) == [(1, "C,1,10")]
    with pytest.raises(ImportFileError, match="300 columnas"):
        read_rows("piezas.xlsx", xlsx(("C", 1, 10) + ("",) * 297 + ("x",)))
    with pytest.raises(ImportFileError, match="300 columnas"):
        read_rows("piezas.xlsx", xlsx(("C", 1, 10) + ("",) * 298 + ("x",)))
