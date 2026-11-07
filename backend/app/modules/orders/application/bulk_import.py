"""HU-018: caso de uso de previsualización de la importación masiva (SPEC-HU-018 §7).

Recibe filas de texto (de un archivo o del borrador corregido) y devuelve cómo se
interpretó cada una. No usa el repositorio: no escribe en la base de datos.
"""
from dataclasses import asdict

from ..domain.bulk_import import OBSERVADO, interpret_rows

MAX_ROWS = 500
MAX_ROW_LENGTH = 4000  # un polígono de 128 lados con decimales cabe con margen

NO_PIECES = "El archivo no contiene piezas."


class ImportFileError(Exception):
    """El archivo completo no se puede previsualizar (SPEC-HU-018 §6.3)."""

    def __init__(self, message, status_code=422):
        super().__init__(message)
        self.status_code = status_code


class PreviewImportUseCase:
    def execute(self, archivo, rows, skip_header=True):
        # Al revalidar se conservan todas las filas, también las que el usuario vació.
        content = [(fila, texto) for fila, texto in rows if not skip_header or texto.strip().strip(",").strip()]
        if not content:
            raise ImportFileError(NO_PIECES)
        if len(content) > MAX_ROWS:
            raise ImportFileError(f"El archivo supera el máximo de {MAX_ROWS} filas.")
        if any(len(texto) > MAX_ROW_LENGTH for _, texto in content):
            raise ImportFileError(f"Una fila supera el máximo de {MAX_ROW_LENGTH} caracteres.")
        results = interpret_rows(content, skip_header)
        if not results:  # solo había una fila de títulos
            raise ImportFileError(NO_PIECES)
        observed = sum(row.estado == OBSERVADO for row in results)
        return {
            "archivo": archivo,
            "resumen": {"total": len(results), "validas": len(results) - observed, "observadas": observed},
            "filas": [asdict(row) for row in results],
        }