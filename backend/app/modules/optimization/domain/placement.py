"""Validación geométrica de colocaciones (TA-007).

Una pieza (máscara conservadora) se coloca sobre un material
(máscara interior) con su esquina superior izquierda en la celda (fila, columna).
La colocación es válida si todas las celdas de la pieza caen en celdas usables
del material (límites) y ninguna toca una celda ya ocupada (superposición).
Todo se comprueba fila por fila con operaciones de bits.
"""
from dataclasses import dataclass
from enum import Enum

from .raster_mask import RasterMask


class PlacementError(ValueError):
    """Uso incorrecto del validador (resoluciones distintas o colocar donde no se puede)."""


class PlacementIssue(str, Enum):
    OUT_OF_BOUNDS = "FUERA_DE_LIMITE"
    OVERLAP = "SUPERPOSICION"


@dataclass(frozen=True)
class PlacementCheck:
    is_valid: bool
    issue: PlacementIssue | None = None


VALID = PlacementCheck(True)


@dataclass(frozen=True)
class SheetLayout:
    """Estado inmutable de un material con las piezas ya colocadas.

    - material: celdas completamente dentro del material (regla interior).
    - occupied: celdas de las piezas colocadas, una fila de bits por fila del material.
    """

    material: RasterMask
    occupied: tuple[int, ...]

    @classmethod
    def empty(cls, material: RasterMask) -> "SheetLayout":
        return cls(material, tuple(0 for _ in material.rows))

    def check(self, piece: RasterMask, row: int, column: int) -> PlacementCheck:
        """Indica si la pieza cabe en (fila, columna) y, si no, el primer motivo encontrado."""
        if piece.resolution_mm != self.material.resolution_mm:
            raise PlacementError("La pieza y el material deben tener la misma resolución.")

        # La caja de la pieza debe caer dentro de la cuadrícula del material.
        if (
            row < 0
            or column < 0
            or row + piece.row_count > self.material.row_count
            or column + piece.columns > self.material.columns
        ):
            return PlacementCheck(False, PlacementIssue.OUT_OF_BOUNDS)

        # Cada fila de la pieza se desplaza a su columna y se compara con la fila del material.
        placed_rows = [(row + offset, bits << column) for offset, bits in enumerate(piece.rows)]

        # Primero se descarta salir del material; luego, chocar con otra pieza.
        if any(placed & ~self.material.rows[target] for target, placed in placed_rows):
            return PlacementCheck(False, PlacementIssue.OUT_OF_BOUNDS)
        if any(placed & self.occupied[target] for target, placed in placed_rows):
            return PlacementCheck(False, PlacementIssue.OVERLAP)
        return VALID

    def place(self, piece: RasterMask, row: int, column: int) -> "SheetLayout":
        """Devuelve un nuevo estado con la pieza colocada; falla si la colocación no es válida."""
        result = self.check(piece, row, column)
        if not result.is_valid:
            raise PlacementError(f"No se puede colocar la pieza: {result.issue.value}.")

        occupied = list(self.occupied)
        for offset, bits in enumerate(piece.rows):
            occupied[row + offset] |= bits << column
        return SheetLayout(self.material, tuple(occupied))