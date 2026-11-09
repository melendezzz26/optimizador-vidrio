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
from itertools import groupby
from weakref import ref

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


class LayoutQueryMemo:
    """Reuse exact queries without retaining old layouts or masks."""

    def __init__(self):
        self._entries = {}

    @property
    def bytes_bound(self):
        # Entries hold identity integers, weak references and coordinates.
        return 512 * (len(self._entries) + 1)

    def find(self, layout, mask, *, empty=False):
        # Within one run every empty layout of the same material has the same
        # margin and separation. Occupied layouts require object identity.
        source = layout.material if empty else layout
        return self.get(source, mask, lambda: self._search(source, layout, mask))

    def _search(self, source, layout, mask):
        if mask.resolution_mm != layout.material.resolution_mm:
            return layout.first_position(mask)
        if mask.columns > layout.material.columns or mask.row_count > layout.material.row_count:
            return None
        free = self.get(source, source,
                        lambda: sum((usable & ~blocked).bit_count()
                                    for usable, blocked in zip(layout.usable, layout.blocked)),
                        parameters=('free_cells',))
        # A translation preserves the number of occupied cells. Use the
        # bounding box as a cheap shortcut before counting the piece bits.
        if free < mask.columns * mask.row_count:
            occupied = self.get(mask, mask, lambda: mask.occupied_cells,
                                parameters=('occupied_cells',))
            if free < occupied:
                return None
        return layout.first_position(mask)

    def get(self, source, mask, calculate, *, parameters=()):
        key = (id(source), id(mask), parameters)
        cached = self._entries.get(key)
        if cached is not None and cached[0]() is source and cached[1]() is mask:
            return cached[2]
        value = calculate()
        if len(self._entries) >= 2048:
            self._entries.clear()
        self._entries[key] = (ref(source), ref(mask), value)
        return value


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
        return self._position(piece)

    def last_position(self, piece: RasterMask, *, checkpoint=None, on_scan=None):
        """Exact reverse row/column order; charge every logically scanned origin."""
        return self._position(piece, reverse=True, checkpoint=checkpoint, on_scan=on_scan)

    def _position(self, piece: RasterMask, *, reverse=False, checkpoint=None, on_scan=None):
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

        band_ends = []
        if not reverse and on_scan is None:
            end = 0
            for _, band in groupby(free):
                height = sum(1 for _ in band)
                end += height
                band_ends.extend([end] * height)

        shape = piece.rows[0]
        if band_ends and checkpoint is None and piece.rows.count(shape) == piece.row_count:
            # For a constant piece row, every free band touched by the
            # vertical window remains a constraint until the top band leaves.
            row = 0
            while row < rows:
                candidates, target = all_origins, row
                while candidates and target < row + piece.row_count:
                    candidates &= origins(free[target], shape)
                    target = band_ends[target]
                if candidates:
                    return row, (candidates & -candidates).bit_length() - 1
                row = band_ends[row]
            return None

        # Intersections commute: test the densest constraints first, while the
        # candidate origins still follow the exact row/leftmost-column order.
        # For equal free material rows, masks already tested imply every subset
        # of their union. Retain only one union, local to this candidate row.
        occupied_rows = [(offset, bits) for offset, bits in enumerate(piece.rows) if bits]
        first = occupied_rows[0] if occupied_rows else None
        occupied_rows.sort(key=lambda item: item[1].bit_count(), reverse=True)
        direction = -1 if reverse else 1
        row = rows - 1 if reverse else 0
        while 0 <= row < rows:
            if checkpoint is not None:
                checkpoint()
            candidates = all_origins
            next_row = rows if band_ends else row + direction
            previous_free, covered_shape = None, 0
            if first is not None:
                # Keep the cheap original top-row rejection before dense rows.
                offset, covered_shape = first
                previous_free = free[row + offset]
                candidates &= origins(previous_free, covered_shape)
                if band_ends:
                    next_row = band_ends[row + offset] - offset
                if not candidates:
                    if on_scan is not None:
                        on_scan(columns)
                    row = next_row
                    continue
            for constraint_index, (offset, bits) in enumerate(occupied_rows):
                if checkpoint is not None and constraint_index % 64 == 0:
                    checkpoint()
                available = free[row + offset]
                if available != previous_free:
                    previous_free, covered_shape = available, 0
                if bits & ~covered_shape == 0:
                    continue
                covered_shape |= bits
                candidates &= origins(available, bits)
                if band_ends:
                    next_row = min(next_row, band_ends[row + offset] - offset)
                if not candidates:
                    break
            if candidates:
                column = (candidates.bit_length() - 1 if reverse else
                          (candidates & -candidates).bit_length() - 1)
                if on_scan is not None:
                    on_scan(columns - column)
                return row, column
            if on_scan is not None:
                on_scan(columns)
            # The failed intersection stays empty while every tested constraint
            # reads the same free bits. Resume at the first possible change.
            row = next_row
        return None

    def place(self, piece: RasterMask, row: int, column: int) -> "SheetLayout":
        """Devuelve un nuevo estado con la pieza colocada; falla si la colocación no es válida."""
        result = self.check(piece, row, column)
        if not result.is_valid:
            raise PlacementError(f"No se puede colocar la pieza: {result.issue.value}.")

        occupied = list(self.occupied)
        previous_shape = previous_occupied = -1
        for offset, bits in enumerate(piece.rows):
            current = occupied[row + offset]
            if bits != previous_shape or current != previous_occupied:
                combined = current | (bits << column)
                previous_shape, previous_occupied = bits, current
            occupied[row + offset] = combined
        occupied = tuple(occupied)
        return SheetLayout(
            material=self.material,
            usable=self.usable,
            occupied=occupied,
            blocked=_dilate(occupied, self.material.columns, self.separation_cells),
            separation_cells=self.separation_cells,
        )
