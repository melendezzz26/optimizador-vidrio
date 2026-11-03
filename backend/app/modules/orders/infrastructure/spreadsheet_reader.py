"""HU-018: lee un archivo CSV o XLSX y entrega sus filas como texto (SPEC-HU-018 §4.6).

Cada fila sale como (número de fila, texto). En XLSX se unen las celdas con
comas, así una fila de Excel se interpreta exactamente igual que una línea del CSV,
aunque Excel haya partido un polígono en varias celdas.
"""
from io import BytesIO
from pathlib import PurePath

from openpyxl import load_workbook

from ..application.bulk_import import MAX_ROWS, ImportFileError

UNREADABLE = "No se pudo leer el archivo. Verifica el formato."
# Límites de recorrido: cuentan también las filas y celdas vacías, para que un archivo
# pequeño (XLSX está comprimido) no obligue a recorrer cientos de miles de filas.
MAX_SCANNED_ROWS = 2000
MAX_COLUMNS = 300  # un polígono de 128 lados partido en celdas (256) + tipo y cantidad
TOO_MANY_ROWS = f"El archivo supera el máximo de {MAX_SCANNED_ROWS} filas, contando las vacías. Elimina las filas vacías."
TOO_MANY_COLUMNS = f"Una fila del archivo supera el máximo de {MAX_COLUMNS} columnas."

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
    lines = text.splitlines()
    if len(lines) > MAX_SCANNED_ROWS:
        raise ImportFileError(TOO_MANY_ROWS)
    return list(enumerate(lines, start=1))


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
        sheet_rows = workbook.worksheets[0].iter_rows(max_col=MAX_COLUMNS + 1, values_only=True)
        for number, cells in enumerate(sheet_rows, start=1):
            if number > MAX_SCANNED_ROWS:
                raise ImportFileError(TOO_MANY_ROWS)
            if len(cells) > MAX_COLUMNS and cells[MAX_COLUMNS] is not None:
                raise ImportFileError(TOO_MANY_COLUMNS)
            values = [_cell_text(cell) if cell is not None else "" for cell in cells]
            while values and not values[-1]:
                values.pop()  # solo se descartan celdas vacías al final de la fila
            text = ",".join(values)
            rows.append((number, text))
            with_content += bool(text)
            if with_content > MAX_ROWS:  # deja de leer: el caso de uso rechazará el archivo
                break
        return rows
    except ImportFileError:
        raise
    except Exception as error:
        raise ImportFileError(UNREADABLE) from error
    finally:
        workbook.close()
