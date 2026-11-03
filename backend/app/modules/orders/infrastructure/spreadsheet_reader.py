"""HU-018: lee un archivo CSV o XLSX y entrega sus filas como texto (SPEC-HU-018 §4.6).

Cada fila sale como (número de fila, texto). En XLSX se unen las celdas no vacías con
comas, así una fila de Excel se interpreta exactamente igual que una línea del CSV,
aunque Excel haya partido un polígono en varias celdas.
"""
from io import BytesIO
from pathlib import PurePath

from openpyxl import load_workbook

from ..application.bulk_import import MAX_ROWS, ImportFileError

UNREADABLE = "No se pudo leer el archivo. Verifica el formato."


def file_name(filename):
    """Solo el nombre, sin rutas, para mostrarlo como fuente de las filas."""
    return PurePath((filename or "").replace("\\", "/")).name[:255]


def read_rows(filename, content):
    extension = PurePath(file_name(filename)).suffix.lower()
    if extension == ".csv":
        return _csv_rows(content)
    if extension == ".xlsx":
        return _xlsx_rows(content)
    raise ImportFileError("Selecciona un archivo .csv o .xlsx.")


def _csv_rows(content):
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ImportFileError(UNREADABLE) from error
    return list(enumerate(text.splitlines(), start=1))


def _cell_text(value):
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _xlsx_rows(content):
    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    except Exception as error:  # archivo dañado o que no es XLSX: nunca se expone el detalle
        raise ImportFileError(UNREADABLE) from error
    try:
        rows, with_content = [], 0
        for number, cells in enumerate(workbook.worksheets[0].iter_rows(values_only=True), start=1):
            values = [_cell_text(cell) for cell in cells if cell is not None]
            text = ",".join(value for value in values if value)
            rows.append((number, text))
            with_content += bool(text)
            if with_content > MAX_ROWS:  # deja de leer: el caso de uso rechazará el archivo
                break
        return rows
    except Exception as error:
        raise ImportFileError(UNREADABLE) from error
    finally:
        workbook.close()