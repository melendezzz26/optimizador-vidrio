"""TA-037 T02: límites operativos previos a la expansión (SPEC-TA-037 §5-§7).

Funciones puras sobre filas persistidas y conteos de stock. Nunca expanden
cantidades, no crean StockCandidate y no rasterizan: el motor (FF/BF/WF) no se
modifica. Un rechazo es un RunError, así que la unidad de trabajo hace rollback.
"""
from dataclasses import dataclass
from decimal import Decimal

from .errors import RunError
from ..domain.problem import geometry_snapshot
from ..domain.rotation import INTERNAL_CACHE_BYTES, RasterCache

MAX_PERSISTED_INT = 2147483647


@dataclass(frozen=True)
class RunLoadBudget:
    """SPEC-TA-037 v1.1 + SPEC-ACADEMIC-800 (paso operativo de 5°)."""
    max_orders: int = 20                                # L-01
    max_units: int = 800                                # ACADEMIC-800: physical piece units
    max_vertices: int = 128                             # L-04
    max_stock_units_per_material: int = 50              # L-07
    max_raster_bytes: int = INTERNAL_CACHE_BYTES        # L-13, mismo valor que RasterCache
    max_active_runs: int = 2                            # L-10, por proceso
    max_active_runs_per_user: int = 1                   # L-11
    max_calculation_seconds: int = 120                  # L-12


DEFAULT_RUN_LOAD_BUDGET = RunLoadBudget()

_MESSAGES = {
    "orders_per_run": "Seleccionaste {actual} pedidos y el máximo por cálculo es {maximum}. "
                      "Quita algunos e inténtalo de nuevo.",
    "units_per_run": "Los pedidos seleccionados suman {actual} unidades y el máximo por cálculo es {maximum}. "
                     "Divide la selección en lotes más pequeños.",
    "vertices_per_piece": "La pieza {id_pieza} tiene {actual} vértices y el máximo admitido es {maximum}. "
                          "Edita la pieza en su pedido.",
    "raster_memory": "Las máscaras base de las piezas y los materiales superan el límite de un solo cálculo. "
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

    snapshots, cache = [], RasterCache()
    for row in rows:
        snapshot = geometry_snapshot(row.get("geometria"))                  # ValueError -> INVALID_INPUT
        vertices = len(snapshot.get("vertices_mm", ()))
        if vertices > budget.max_vertices:                                  # L-04
            raise LoadLimitExceeded("vertices_per_piece", budget.max_vertices, vertices,
                                    {"id_pieza": row.get("id_pieza")})
        cache.check_geometry(snapshot, config.resolution_mm)                # L-05
        snapshots.append(snapshot)

    check_raster_bases(snapshots, config, budget)
    return units_by_material


def check_stock(units_by_material: dict, stock_units: dict,
                budget: RunLoadBudget = DEFAULT_RUN_LOAD_BUDGET) -> None:
    """P4 / L-07: conteo de unidades físicas compatibles, sin crear candidatos."""
    for key in sorted(units_by_material):
        count = stock_units[key]
        if count > budget.max_stock_units_per_material:
            raise LoadLimitExceeded("stock_units_per_material", budget.max_stock_units_per_material, count,
                                    {"id_tipo_vidrio": key[0], "espesor_mm": str(key[1])})


def check_raster_bases(pieces, config, budget, *, stock=()) -> None:
    """L-13: charge the resident bases; the cache bounds requested rotations."""
    cache = RasterCache()
    resolution = config.resolution_mm
    estimate = cache.base_bytes(pieces, resolution) + cache.base_bytes(stock, resolution, material=True)
    if estimate > budget.max_raster_bytes:
        raise LoadLimitExceeded("raster_memory", budget.max_raster_bytes, estimate)
