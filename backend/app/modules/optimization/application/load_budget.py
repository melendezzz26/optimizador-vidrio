"""TA-037 T02: límites operativos previos a la expansión (SPEC-TA-037 §5-§7).

Funciones puras sobre filas persistidas y conteos de stock. Nunca expanden
cantidades, no crean StockCandidate y no rasterizan: el motor (FF/BF/WF) no se
modifica. Un rechazo es un RunError, así que la unidad de trabajo hace rollback.
"""
import math
from dataclasses import dataclass
from decimal import Decimal

from .errors import RunError
from ..domain.preparation import bbox_dimensions
from ..domain.problem import geometry_snapshot
from ..domain.rotation import (
    INTERNAL_CACHE_BYTES, INTERNAL_MAX_AXIS, INTERNAL_MAX_CELLS, INTERNAL_MAX_DIMENSION_MM,
    RasterCache, discrete_angles,
)

MAX_PERSISTED_INT = 2147483647


@dataclass(frozen=True)
class RunLoadBudget:
    """Valores aprobados en SPEC-TA-037 v1.1 (paso operativo de 5°)."""
    max_orders: int = 20                                # L-01
    max_units: int = 150                                # L-03
    max_vertices: int = 128                             # L-04
    max_stock_units_per_material: int = 50              # L-07
    max_raster_bytes: int = INTERNAL_CACHE_BYTES        # L-13, mismo valor que RasterCache


DEFAULT_RUN_LOAD_BUDGET = RunLoadBudget()

_MESSAGES = {
    "orders_per_run": "Seleccionaste {actual} pedidos y el máximo por cálculo es {maximum}. "
                      "Quita algunos e inténtalo de nuevo.",
    "units_per_run": "Los pedidos seleccionados suman {actual} unidades y el máximo por cálculo es {maximum}. "
                     "Divide la selección en lotes más pequeños.",
    "vertices_per_piece": "La pieza {id_pieza} tiene {actual} vértices y el máximo admitido es {maximum}. "
                          "Edita la pieza en su pedido.",
    "raster_memory": "Las piezas seleccionadas tienen demasiadas formas grandes distintas para un solo cálculo. "
                     "Divide la selección en lotes más pequeños.",
    "stock_units_per_material": "Hay {actual} unidades de stock compatibles para un mismo material y un cálculo "
                                "admite {maximum}. Solicita al almacenero revisar el inventario activo.",
}


class LoadLimitExceeded(RunError):
    """422 LOAD_LIMIT_EXCEEDED: la solicitud es válida pero excede el presupuesto."""

    def __init__(self, name: str, maximum: int, actual: int, scope: dict | None = None):
        self.limit = dict(name=name, maximum=maximum, actual=actual, scope=scope)
        message = _MESSAGES[name].format(maximum=maximum, actual=actual, **(scope or {}))
        super().__init__("LOAD_LIMIT_EXCEEDED", message, details={"limit": self.limit})


def material_key(row) -> tuple[int, Decimal] | None:
    """Misma clave que PieceUnit.material_key y que los grupos de stock.

    None si el material persistido es inválido: lo rechaza la validación de negocio.
    """
    glass, thickness = row.get("id_tipo_vidrio"), row.get("espesor_mm")
    if type(glass) is not int or type(thickness) not in (int, float, Decimal):
        return None
    try:
        thickness = Decimal(str(thickness))
    except ArithmeticError:
        return None
    return (glass, thickness) if thickness.is_finite() and thickness > 0 else None


def check_selection(order_ids, budget: RunLoadBudget = DEFAULT_RUN_LOAD_BUDGET) -> None:
    """P1 / L-01: antes de abrir la transacción."""
    if len(order_ids) > budget.max_orders:
        raise LoadLimitExceeded("orders_per_run", budget.max_orders, len(order_ids))


def _valid_quantity(value) -> bool:
    return type(value) is int and 0 < value <= MAX_PERSISTED_INT


def check_pieces(rows, config, budget: RunLoadBudget = DEFAULT_RUN_LOAD_BUDGET) -> dict:
    """P3 / L-03, L-04, L-05 y L-13, sobre filas persistidas y sin expandir.

    Devuelve las unidades por material para P4. Las filas con datos de negocio
    inválidos no se cuentan aquí: la validación existente las rechaza después
    como INVALID_INPUT. Los ValueError de geometría (L-05) se propagan para que
    AcceptRun conserve la respuesta INVALID_INPUT de siempre.
    """
    units_by_material, total = {}, 0
    for row in rows:
        quantity = row.get("cantidad")
        if _valid_quantity(quantity):
            total += quantity
            key = material_key(row)
            if key is not None:
                units_by_material[key] = units_by_material.get(key, 0) + quantity
    if total > budget.max_units:                                            # L-03
        raise LoadLimitExceeded("units_per_run", budget.max_units, total)

    snapshots = []
    for row in rows:
        snapshot = geometry_snapshot(row.get("geometria"))                  # ValueError -> INVALID_INPUT
        vertices = len(snapshot.get("vertices_mm", ()))
        if vertices > budget.max_vertices:                                  # L-04
            raise LoadLimitExceeded("vertices_per_piece", budget.max_vertices, vertices,
                                    {"id_pieza": row.get("id_pieza")})
        geometry = dict(snapshot)
        if snapshot["type"] == "POLIGONO_CONVEXO":
            geometry["vertices_mm"] = [list(p) for p in snapshot["vertices_mm"]]
        RasterCache().check_geometry(geometry, config.resolution_mm)        # L-05, misma función que antes
        snapshots.append(snapshot)

    estimate = estimate_raster_bytes(snapshots, config)                     # L-13
    if estimate > budget.max_raster_bytes:
        raise LoadLimitExceeded("raster_memory", budget.max_raster_bytes, estimate)
    return units_by_material


def check_stock(units_by_material: dict, stock_units: dict,
                budget: RunLoadBudget = DEFAULT_RUN_LOAD_BUDGET) -> None:
    """P4 / L-07: conteo de unidades físicas compatibles, sin crear candidatos."""
    for key in sorted(units_by_material):
        count = stock_units[key]
        if count > budget.max_stock_units_per_material:
            raise LoadLimitExceeded("stock_units_per_material", budget.max_stock_units_per_material, count,
                                    {"id_tipo_vidrio": key[0], "espesor_mm": str(key[1])})


# --- L-13: cota inferior de la caché raster ----------------------------------

def _fingerprint(snapshot):
    """Misma identidad con la que RasterCache comparte máscaras entre piezas."""
    if snapshot["type"] == "CIRCUNFERENCIA":
        return ("CIRCUNFERENCIA", Decimal(str(snapshot["radius_mm"])))
    return tuple(_local_vertices(snapshot))


def _local_vertices(snapshot):
    if snapshot["type"] == "RECTANGULO":
        width, height = bbox_dimensions(snapshot)
        return [(Decimal(0), Decimal(0)), (width, Decimal(0)), (width, height), (Decimal(0), height)]
    vertices = [tuple(Decimal(str(v)) for v in point) for point in snapshot["vertices_mm"]]
    minimum = tuple(min(p[i] for p in vertices) for i in (0, 1))
    return [(x - minimum[0], y - minimum[1]) for x, y in vertices]


def _orientation_lower_bound(points, vertex_count, angle, resolution):
    """Bytes que RasterCache reservaría para una orientación, redondeando hacia abajo.

    Rejilla con floor en vez de ceil y bbox en float: nunca supera la estimación
    real. Si la orientación podría ser descartada por extensión, aporta 0.
    """
    radians = math.radians(float(angle))
    cosine, sine = math.cos(radians), math.sin(radians)
    xs = [x * cosine - y * sine for x, y in points]
    ys = [x * sine + y * cosine for x, y in points]
    width, height = max(xs) - min(xs), max(ys) - min(ys)
    columns, rows = math.floor(width / resolution), math.floor(height / resolution)
    if (max(width, height) >= INTERNAL_MAX_DIMENSION_MM - 1 or max(columns, rows) + 1 > INTERNAL_MAX_AXIS
            or (columns + 1) * (rows + 1) > INTERNAL_MAX_CELLS):
        return 0
    columns, rows = max(1, columns), max(1, rows)
    return rows * (32 + 4 * ((columns + 29) // 30) + 8) + 4096 + vertex_count * 512


def estimate_raster_bytes(snapshots, config) -> int:
    """Cota inferior de la memoria raster de las piezas (sin el stock), SPEC §5.1."""
    resolution = float(config.resolution_mm)
    angles = discrete_angles(config.angular_step_deg)
    total, seen = 0, set()
    for snapshot in snapshots:
        fingerprint = _fingerprint(snapshot)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        if snapshot["type"] == "CIRCUNFERENCIA":
            diameter = 2 * float(snapshot["radius_mm"])
            square = [(0.0, 0.0), (diameter, 0.0), (diameter, diameter), (0.0, diameter)]
            total += _orientation_lower_bound(square, 0, 0, resolution)
            continue
        points = [(float(x), float(y)) for x, y in fingerprint]
        rectangle = snapshot["type"] == "RECTANGULO"
        for angle in angles:
            # Un rectángulo en un cuarto de vuelta sigue siendo RECTANGULO (sin vértices).
            vertex_count = 0 if rectangle and angle % 90 == 0 else len(points)
            total += _orientation_lower_bound(points, vertex_count, angle, resolution)
    return total