"""Validación geométrica de colocaciones (TA-007).

Ver SPEC-TA-007. Una pieza (máscara conservadora) se coloca sobre un material
(máscara interior) con su esquina superior izquierda en la celda (fila, columna).
La colocación es válida si todas las celdas de la pieza caen en celdas usables
del material (límites) y ninguna toca una celda ya ocupada (superposición).
Con margen y separación (T02), además debe quedar a esa distancia del borde
del material y de las demás piezas. Todo se comprueba fila por fila con bits.
"""
from decimal import Decimal
from functools import lru_cache
from dataclasses import dataclass
from enum import Enum

from .raster_mask import RasterMask, is_real_number


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
    """Techo exacto sobre los valores decimales aceptados, sin reducir distancias."""
    if not is_real_number(distance_mm) or distance_mm < 0:
        raise PlacementError(f"{label} debe ser un número mayor o igual a cero.")
    if not is_real_number(resolution_mm) or resolution_mm <= 0:
        raise PlacementError("La resolución debe ser un número positivo.")
    dn, dd = Decimal(str(distance_mm)).as_integer_ratio()
    rn, rd = Decimal(str(resolution_mm)).as_integer_ratio()
    return (dn * rd + dd * rn - 1) // (dd * rn)


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
        return cls._from_cells(material, margin_cells, separation_cells)

    @classmethod
    def _from_cells(cls, material: RasterMask, margin_cells: int, separation_cells: int) -> "SheetLayout":
        """Construye desde conteos internos ya validados, sin reconvertir a floats."""
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

    def first_position(self, piece: RasterMask):
        """Exact row/column First Fit, testing candidate columns in parallel bits.

        Intersect usable, unblocked origins for every occupied piece-row run.
        There is no heuristic skip, geometric relaxation or change of scan order.
        Bounded memoization avoids per-cell objects and repeated row erosion.
        """
        if piece.resolution_mm != self.material.resolution_mm:
            raise PlacementError("La pieza y el material deben tener la misma resolución.")
        columns = self.material.columns - piece.columns + 1
        rows = self.material.row_count - piece.row_count + 1
        if columns <= 0 or rows <= 0:
            return None
        free = tuple(usable & ~blocked for usable, blocked in zip(self.usable, self.blocked))
        all_origins = (1 << columns) - 1

        @lru_cache(maxsize=256)
        def origins(available, shape):
            candidates = all_origins
            # All windows of length n, computed with doubling intersections.
            remaining = shape
            offset = 0
            while remaining:
                zeros = (remaining & -remaining).bit_length() - 1
                remaining >>= zeros
                offset += zeros
                length = (remaining ^ (remaining + 1)).bit_length() - 1
                windows, covered = available, 1
                while covered * 2 <= length:
                    windows &= windows >> covered
                    covered *= 2
                if length > covered:
                    windows &= windows >> (length - covered)
                candidates &= windows >> offset
                if not candidates:
                    return 0
                remaining >>= length
                offset += length
            return candidates

        # Intersections commute: test the densest constraints first, while the
        # candidate origins still follow the exact row/leftmost-column order.
        # For equal free material rows, masks already tested imply every subset
        # of their union. Avoid repeating those constraints (notably circles and
        # polygons over long rectangular free strips). Retain only one such
        # union, local to this candidate row; no layout/global cache is added.
        occupied_rows = [(offset, bits) for offset, bits in enumerate(piece.rows) if bits]
        first = occupied_rows[0] if occupied_rows else None
        occupied_rows.sort(key=lambda item: item[1].bit_count(), reverse=True)
        for row in range(rows):
            candidates = all_origins
            previous_free, covered_shape = None, 0
            if first is not None:
                # Keep the cheap original top-row rejection before dense rows.
                offset, covered_shape = first
                previous_free = free[row + offset]
                candidates &= origins(previous_free, covered_shape)
                if not candidates:
                    continue
            for offset, bits in occupied_rows:
                available = free[row + offset]
                if available != previous_free:
                    previous_free, covered_shape = available, 0
                if bits & ~covered_shape == 0:
                    continue
                covered_shape |= bits
                candidates &= origins(available, bits)
                if not candidates:
                    break
            if candidates:
                return row, (candidates & -candidates).bit_length() - 1
        return None

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
