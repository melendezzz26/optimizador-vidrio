"""Validación geométrica de colocaciones (TA-007).

Ver SPEC-TA-007. Una pieza (máscara conservadora) se coloca sobre un material
(máscara interior) con su esquina superior izquierda en la celda (fila, columna).
La colocación es válida si todas las celdas de la pieza caen en celdas usables
del material (límites) y ninguna toca una celda ya ocupada (superposición).
Con margen y separación (T02), además debe quedar a esa distancia del borde
del material y de las demás piezas. Todo se comprueba fila por fila con bits.
"""
import math
from dataclasses import dataclass
from enum import Enum

from .raster_mask import RasterMask, is_real_number

_EPSILON = 1e-9


class PlacementError(ValueError):
    """Uso incorrecto del validador (resoluciones distintas, valores inválidos o colocar donde no se puede)."""


class PlacementIssue(str, Enum):
    OUT_OF_BOUNDS = "FUERA_DE_LIMITE"
    MARGIN = "MARGEN_INSUFICIENTE"
    OVERLAP = "SUPERPOSICION"
    SEPARATION = "SEPARACION_INSUFICIENTE"


@dataclass(frozen=True)
class PlacementCheck:
    is_valid: bool
    issue: PlacementIssue | None = None


VALID = PlacementCheck(True)


def distance_in_cells(distance_mm, resolution_mm: float, label: str) -> int:
    """Celdas que cubren una distancia, redondeando hacia arriba (nunca menos de lo pedido)."""
    if not is_real_number(distance_mm) or distance_mm < 0:
        raise PlacementError(f"{label} debe ser un número mayor o igual a cero.")
    return math.ceil(distance_mm / resolution_mm - _EPSILON) if distance_mm > 0 else 0


def _erode(rows: tuple[int, ...], columns: int, cells: int) -> tuple[int, ...]:
    """Deja una celda solo si todas las celdas a `cells` o menos (en filas y columnas) también lo están."""
    if cells == 0:
        return rows
    full = (1 << columns) - 1
    horizontal = []
    for bits in rows:
        kept = bits
        for k in range(1, cells + 1):
            kept &= (bits >> k) & (bits << k) & full
        horizontal.append(kept)
    count = len(rows)
    result = []
    for index in range(count):
        kept = full
        for neighbor in range(index - cells, index + cells + 1):
            kept &= horizontal[neighbor] if 0 <= neighbor < count else 0
        result.append(kept)
    return tuple(result)


def _dilate(rows: tuple[int, ...], columns: int, cells: int) -> tuple[int, ...]:
    """Agrega las celdas a `cells` o menos (en filas y columnas) de una celda marcada, sin salir de la máscara."""
    if cells == 0:
        return rows
    full = (1 << columns) - 1
    horizontal = []
    for bits in rows:
        grown = bits
        for k in range(1, cells + 1):
            grown |= (bits >> k) | (bits << k)
        horizontal.append(grown & full)
    count = len(rows)
    result = []
    for index in range(count):
        grown = 0
        for neighbor in range(max(0, index - cells), min(count, index + cells + 1)):
            grown |= horizontal[neighbor]
        result.append(grown)
    return tuple(result)


@dataclass(frozen=True)
class SheetLayout:
    """Estado inmutable de un material con las piezas ya colocadas.

    - material: celdas completamente dentro del material (regla interior).
    - usable: material encogido por el margen; ahí deben caer todas las celdas de una pieza.
    - occupied: celdas de las piezas colocadas.
    - blocked: occupied agrandado por la separación; una pieza nueva no puede tocarlo.
    """

    material: RasterMask
    usable: tuple[int, ...]
    occupied: tuple[int, ...]
    blocked: tuple[int, ...]
    separation_cells: int

    @classmethod
    def empty(cls, material: RasterMask, margin_mm=0.0, separation_mm=0.0) -> "SheetLayout":
        resolution = material.resolution_mm
        margin_cells = distance_in_cells(margin_mm, resolution, "El margen")
        separation_cells = distance_in_cells(separation_mm, resolution, "La separación")
        empty_rows = tuple(0 for _ in material.rows)
        return cls(
            material=material,
            usable=_erode(material.rows, material.columns, margin_cells),
            occupied=empty_rows,
            blocked=empty_rows,
            separation_cells=separation_cells,
        )

    def check(self, piece: RasterMask, row: int, column: int) -> PlacementCheck:
        """Indica si la pieza cabe en (fila, columna) y, si no, el primer motivo encontrado."""
        if piece.resolution_mm != self.material.resolution_mm:
            raise PlacementError("La pieza y el material deben tener la misma resolución.")

        if (
            row < 0
            or column < 0
            or row + piece.row_count > self.material.row_count
            or column + piece.columns > self.material.columns
        ):
            return PlacementCheck(False, PlacementIssue.OUT_OF_BOUNDS)

        placed_rows = [(row + offset, bits << column) for offset, bits in enumerate(piece.rows)]

        # Se informa el motivo más grave primero: salir del material, luego invadir el
        # margen, luego chocar con otra pieza y, al final, quedar demasiado cerca de ella.
        if any(placed & ~self.material.rows[target] for target, placed in placed_rows):
            return PlacementCheck(False, PlacementIssue.OUT_OF_BOUNDS)
        if any(placed & ~self.usable[target] for target, placed in placed_rows):
            return PlacementCheck(False, PlacementIssue.MARGIN)
        if any(placed & self.occupied[target] for target, placed in placed_rows):
            return PlacementCheck(False, PlacementIssue.OVERLAP)
        if any(placed & self.blocked[target] for target, placed in placed_rows):
            return PlacementCheck(False, PlacementIssue.SEPARATION)
        return VALID

    def place(self, piece: RasterMask, row: int, column: int) -> "SheetLayout":
        """Devuelve un nuevo estado con la pieza colocada; falla si la colocación no es válida."""
        result = self.check(piece, row, column)
        if not result.is_valid:
            raise PlacementError(f"No se puede colocar la pieza: {result.issue.value}.")

        occupied = list(self.occupied)
        for offset, bits in enumerate(piece.rows):
            occupied[row + offset] |= bits << column
        occupied = tuple(occupied)
        return SheetLayout(
            material=self.material,
            usable=self.usable,
            occupied=occupied,
            blocked=_dilate(occupied, self.material.columns, self.separation_cells),
            separation_cells=self.separation_cells,
        )