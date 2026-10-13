"""Máscara raster binaria de una pieza (TA-005 / TA-006).

Ver SPEC-TA-005-TA-006. Cada fila se guarda como un entero usado como mapa de
bits: el bit ``c`` vale 1 si la columna ``c`` está ocupada. Es la estructura más
liviana medida en el spike de rasterización y permite comparar filas completas
con operaciones de bits (por ejemplo, ``fila_a & fila_b`` para detectar
superposición en TA-007).
"""
import math
from dataclasses import dataclass


class RasterizationError(ValueError):
    """La entrada no se puede rasterizar. El mensaje se puede mostrar al usuario."""


def is_real_number(value) -> bool:
    """True si es int o float finito. bool se excluye aunque sea subclase de int."""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


@dataclass(frozen=True)
class RasterMask:
    """Máscara inmutable: resolución en mm por celda, columnas y filas como bits."""

    resolution_mm: float
    columns: int
    rows: tuple[int, ...]

    def __post_init__(self):
        # Se convierte a tupla para que la máscara no se pueda modificar desde fuera.
        object.__setattr__(self, "rows", tuple(self.rows))

        if not is_real_number(self.resolution_mm) or self.resolution_mm <= 0:
            raise RasterizationError("La resolución debe ser un número positivo.")
        if not isinstance(self.columns, int) or isinstance(self.columns, bool) or self.columns <= 0:
            raise RasterizationError("La máscara debe tener al menos una columna.")
        if not self.rows:
            raise RasterizationError("La máscara debe tener al menos una fila.")

        limit = 1 << self.columns
        for bits in self.rows:
            if not isinstance(bits, int) or isinstance(bits, bool) or not 0 <= bits < limit:
                raise RasterizationError("Una fila tiene celdas fuera de la máscara.")

    @classmethod
    def from_spans(cls, resolution_mm, columns, spans):
        """Crea la máscara a partir de un tramo [inicio, fin) de columnas por fila."""
        rows = []
        for start, end in spans:
            if not 0 <= start <= end <= columns:
                raise RasterizationError("Un tramo de columnas está fuera de la máscara.")
            # (1 << n) - 1 deja n bits en 1; el desplazamiento los mueve a la columna inicial.
            rows.append(((1 << (end - start)) - 1) << start)
        return cls(resolution_mm, columns, tuple(rows))

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def width_mm(self) -> float:
        return self.columns * self.resolution_mm

    @property
    def height_mm(self) -> float:
        return self.row_count * self.resolution_mm

    @property
    def occupied_cells(self) -> int:
        return sum(bits.bit_count() for bits in self.rows)

    @property
    def area_mm2(self) -> float:
        """Área que representa la máscara: celdas ocupadas por el área de una celda."""
        return self.occupied_cells * self.resolution_mm * self.resolution_mm

    def is_occupied(self, row: int, column: int) -> bool:
        if not (0 <= row < self.row_count and 0 <= column < self.columns):
            raise IndexError("La celda está fuera de la máscara.")
        return bool((self.rows[row] >> column) & 1)

    def to_text(self, occupied: str = "#", free: str = ".") -> str:
        """Dibujo de la máscara en texto, una línea por fila (fila 0 arriba)."""
        return "\n".join(
            "".join(occupied if (bits >> column) & 1 else free for column in range(self.columns))
            for bits in self.rows
        )