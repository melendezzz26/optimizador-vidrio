"""Preflight de rejilla; no construye máscaras ni depende de helpers privados."""
import math
from dataclasses import dataclass

from .errors import InvalidRasterInput, RasterBudgetExceeded


def finite_number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def positive_resolution(value):
    if not finite_number(value) or value <= 0:
        raise InvalidRasterInput("La resolución debe ser numérica, finita y mayor a cero.")


def geometry_bounds(geometry):
    if not isinstance(geometry, dict):
        raise InvalidRasterInput("La geometría persistida no es compatible.")
    shape = geometry.get("type")
    if shape == "RECTANGULO":
        values = [geometry.get("width_mm"), geometry.get("height_mm")]
        if not all(finite_number(v) and v > 0 for v in values):
            raise InvalidRasterInput("Las dimensiones persistidas deben ser finitas y positivas.")
        return tuple(round(v, 6) for v in values)
    if shape == "CIRCUNFERENCIA":
        radius = geometry.get("radius_mm")
        if not finite_number(radius) or radius <= 0:
            raise InvalidRasterInput("El radio persistido debe ser finito y positivo.")
        return (round(2 * radius, 6),) * 2
    if shape == "POLIGONO_CONVEXO":
        vertices = geometry.get("vertices_mm")
        if (not isinstance(vertices, list) or len(vertices) < 3
                or any(not isinstance(p, list) or len(p) != 2
                       or not all(finite_number(v) for v in p) for p in vertices)):
            raise InvalidRasterInput("Los vértices persistidos deben ser pares finitos válidos.")
        return tuple(round(max(p[i] for p in vertices) - min(p[i] for p in vertices), 6)
                     for i in (0, 1))
    raise InvalidRasterInput("Tipo de geometría persistida no soportado.")


def estimate_grid(geometry, resolution_mm):
    positive_resolution(resolution_mm)
    width, height = geometry_bounds(geometry)
    if not all(finite_number(v) and v > 0 for v in (width, height)):
        raise RasterBudgetExceeded("La geometría/resolución excede el rango seguro de rasterización.")
    ratios = (width / resolution_mm, height / resolution_mm)
    if not all(finite_number(v) and v > 0 for v in ratios):
        raise RasterBudgetExceeded("La geometría/resolución excede el rango seguro de rasterización.")
    columns, rows = (max(1, math.ceil(v - 1e-9)) for v in ratios)
    return rows, columns


@dataclass(frozen=True)
class RasterBudget:
    max_cells: int
    max_axis: int
    max_vertices: int
    max_payload_bytes: int

    def check(self, geometry, resolution_mm):
        if isinstance(geometry, dict):
            vertices = geometry.get("vertices_mm")
            if isinstance(vertices, list) and len(vertices) > self.max_vertices:
                raise RasterBudgetExceeded("La geometría excede el máximo seguro de vértices.")
        rows, columns = estimate_grid(geometry, resolution_mm)
        if rows * columns > self.max_cells or max(rows, columns) > self.max_axis:
            raise RasterBudgetExceeded(
                "La rejilla excede el límite seguro de rasterización. Aumenta la resolución en mm/celda."
            )
        # Formas convexas: máximo un tramo por fila. Con ejes <= 2440, 96
        # bytes/fila es una cota holgada. Un par de enteros finitos originales
        # puede ocupar hasta ~620 bytes: no convertirlo a float para acortarlo.
        vertices = geometry["vertices_mm"] if geometry["type"] == "POLIGONO_CONVEXO" else []
        estimated_bytes = rows * 96 + len(vertices) * 640 + 2048
        if estimated_bytes > self.max_payload_bytes:
            raise RasterBudgetExceeded("La respuesta raster excedería el tamaño seguro.")
        return rows, columns


# Benchmark HU-015: docs/evidence/sprint-01/HU-015/benchmark-limite.md.
# Celdas no acotan por sí solas filas/JSON ni convexidad O(vertices²).
MAX_RASTER_CELLS = 1_000_000
MAX_RASTER_AXIS = 2440
MAX_RASTER_VERTICES = 128
MAX_RASTER_PAYLOAD_BYTES = 262_144
HU015_RASTER_BUDGET = RasterBudget(
    MAX_RASTER_CELLS, MAX_RASTER_AXIS, MAX_RASTER_VERTICES, MAX_RASTER_PAYLOAD_BYTES,
)
# Backwards-compatible preview alias. First Fit uses domain.rotation's INTERNAL_*
# budgets and never this JSON/preview response limit.
DEFAULT_RASTER_BUDGET = HU015_RASTER_BUDGET
