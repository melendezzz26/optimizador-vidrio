"""Immutable contracts for S1 First Fit; no preparation or search is performed here.

Canonical geometry retains the numeric representation accepted by TA-005/006.
Snapshots are detached and deeply immutable. Orders/Inventory remain responsible
for validating persisted shapes; these contracts do not replace their validators.
"""
import math
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from typing import Literal


class MaterialSource(str, Enum):
    REMNANT = "RETAZO"
    SHEET = "PLANCHA"


def positive_int(value: int, label: str) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{label} must be a positive integer.")


def decimal_value(value: Decimal | int, label: str, *, positive=False) -> Decimal:
    # No implicit binary-float conversion for thickness, area or configuration.
    if type(value) not in (Decimal, int):
        raise ValueError(f"{label} must be Decimal or int.")
    number = Decimal(value)
    if not number.is_finite() or (number <= 0 if positive else number < 0):
        raise ValueError(f"{label} is outside its finite valid range.")
    return number


def geometry_snapshot(geometry: Mapping) -> Mapping:
    """Copy canonical shape fields without normalizing, rotating or rasterizing."""
    if not isinstance(geometry, Mapping):
        raise ValueError("geometry must be a canonical mapping.")
    shape = geometry.get("type")
    fields = {
        "RECTANGULO": ("width_mm", "height_mm"),
        "CIRCUNFERENCIA": ("radius_mm",),
        "POLIGONO_CONVEXO": ("vertices_mm",),
    }
    if not isinstance(shape, str) or shape not in fields or set(geometry) != {"type", *fields[shape]}:
        raise ValueError("geometry must contain exactly the supported canonical shape fields.")

    def coordinate(value):
        try:
            valid = type(value) in (int, float) and math.isfinite(value)
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError("geometry coordinates must be finite canonical numbers.")
        return value

    if shape == "POLIGONO_CONVEXO":
        vertices = geometry["vertices_mm"]
        if not isinstance(vertices, (list, tuple)) or len(vertices) < 3:
            raise ValueError("geometry requires at least three vertices.")
        if any(not isinstance(p, (list, tuple)) or len(p) != 2 for p in vertices):
            raise ValueError("geometry vertices must be coordinate pairs.")
        values = {"vertices_mm": tuple(tuple(coordinate(v) for v in p) for p in vertices)}
    else:
        values = {field: coordinate(geometry[field]) for field in fields[shape]}
        if any(value <= 0 for value in values.values()):
            raise ValueError("geometry dimensions must be positive.")
    return MappingProxyType({"type": shape, **values})


@dataclass(frozen=True, kw_only=True)
class OptimizationConfig:
    resolution_mm: Decimal
    margin_mm: Decimal
    separation_mm: Decimal
    angular_step_deg: Decimal

    def __post_init__(self):
        for name in ("resolution_mm", "margin_mm", "separation_mm", "angular_step_deg"):
            object.__setattr__(self, name, decimal_value(
                getattr(self, name), name, positive=name in ("resolution_mm", "angular_step_deg"),
            ))
        if self.angular_step_deg > 360:
            raise ValueError("angular_step_deg must be at most 360.")


@dataclass(frozen=True, kw_only=True)
class PieceUnit:
    order_id: int
    piece_id: int
    unit_index: int
    glass_type_id: int
    thickness_mm: Decimal
    geometry: Mapping
    area_mm2: Decimal

    def __post_init__(self):
        for name in ("order_id", "piece_id", "unit_index", "glass_type_id"):
            positive_int(getattr(self, name), name)
        for name in ("thickness_mm", "area_mm2"):
            object.__setattr__(self, name, decimal_value(getattr(self, name), name, positive=True))
        object.__setattr__(self, "geometry", geometry_snapshot(self.geometry))

    @property
    def identity(self) -> tuple[int, int]:
        return self.piece_id, self.unit_index

    @property
    def material_key(self) -> tuple[int, Decimal]:
        return self.glass_type_id, self.thickness_mm

    @property
    def shape_type(self) -> str:
        return self.geometry["type"]


@dataclass(frozen=True, kw_only=True)
class StockCandidate:
    source: MaterialSource
    material_id: int
    physical_unit_index: int
    glass_type_id: int
    thickness_mm: Decimal
    geometry: Mapping
    area_mm2: Decimal

    def __post_init__(self):
        if not isinstance(self.source, MaterialSource):
            raise ValueError("source must be a MaterialSource.")
        for name in ("material_id", "physical_unit_index", "glass_type_id"):
            positive_int(getattr(self, name), name)
        if self.source is MaterialSource.REMNANT and self.physical_unit_index != 1:
            raise ValueError("A remnant represents exactly one physical unit.")
        for name in ("thickness_mm", "area_mm2"):
            object.__setattr__(self, name, decimal_value(getattr(self, name), name, positive=True))
        object.__setattr__(self, "geometry", geometry_snapshot(self.geometry))
        if self.source is MaterialSource.SHEET and self.geometry["type"] != "RECTANGULO":
            raise ValueError("A sheet must retain its rectangular geometry.")

    @property
    def identity(self) -> tuple[MaterialSource, int, int]:
        return self.source, self.material_id, self.physical_unit_index

    @property
    def material_key(self) -> tuple[int, Decimal]:
        return self.glass_type_id, self.thickness_mm


@dataclass(frozen=True, kw_only=True)
class MaterialGroup:
    glass_type_id: int
    thickness_mm: Decimal
    units: tuple[PieceUnit, ...]
    stock_candidates: tuple[StockCandidate, ...] = ()

    def __post_init__(self):
        positive_int(self.glass_type_id, "glass_type_id")
        object.__setattr__(self, "thickness_mm", decimal_value(self.thickness_mm, "thickness_mm", positive=True))
        object.__setattr__(self, "units", tuple(self.units))
        object.__setattr__(self, "stock_candidates", tuple(self.stock_candidates))
        if not self.units:
            raise ValueError("A material group must contain requested units.")
        for items in (self.units, self.stock_candidates):
            if any(item.material_key != self.key for item in items):
                raise ValueError("Every unit and stock candidate must match the material group.")
            if len({item.identity for item in items}) != len(items):
                raise ValueError("Duplicate physical units in material group.")

    @property
    def key(self) -> tuple[int, Decimal]:
        return self.glass_type_id, self.thickness_mm


@dataclass(frozen=True, kw_only=True)
class OptimizationProblem:
    order_ids: tuple[int, ...]
    config: OptimizationConfig
    groups: tuple[MaterialGroup, ...]

    def __post_init__(self):
        object.__setattr__(self, "order_ids", tuple(self.order_ids))
        object.__setattr__(self, "groups", tuple(self.groups))
        if not self.order_ids or not self.groups:
            raise ValueError("A problem requires explicit orders and material groups.")
        for identifier in self.order_ids:
            positive_int(identifier, "order_id")
        if len(set(self.order_ids)) != len(self.order_ids):
            raise ValueError("Duplicate order IDs.")
        if len({group.key for group in self.groups}) != len(self.groups):
            raise ValueError("Duplicate material groups.")
        units = self.units
        if {unit.order_id for unit in units} != set(self.order_ids):
            raise ValueError("Units must cover exactly the selected orders.")
        if len({unit.identity for unit in units}) != len(units):
            raise ValueError("A piece unit may only occur once in the problem.")
        pieces = {}
        for unit in units:
            previous = pieces.setdefault(unit.piece_id, unit)
            if (previous.order_id, previous.material_key, previous.geometry, previous.area_mm2) != (
                unit.order_id, unit.material_key, unit.geometry, unit.area_mm2,
            ):
                raise ValueError("All units of a persisted piece must share its snapshot.")

    @property
    def units(self) -> tuple[PieceUnit, ...]:
        return tuple(unit for group in self.groups for unit in group.units)


@dataclass(frozen=True, kw_only=True)
class Placement:
    """Accepted unit/stock assignment; SheetLayout still owns geometric checks.

    geometry is the oriented, bounding-box-local contour produced later by T3.
    x/y translate that local contour on the material; clients never rerun FF.
    """
    piece: PieceUnit
    stock: StockCandidate
    x_mm: Decimal
    y_mm: Decimal
    rotation_deg: Decimal
    geometry: Mapping

    def __post_init__(self):
        if self.piece.material_key != self.stock.material_key:
            raise ValueError("A placement cannot mix incompatible materials.")
        for name in ("x_mm", "y_mm", "rotation_deg"):
            object.__setattr__(self, name, decimal_value(getattr(self, name), name))
        if self.rotation_deg >= 360:
            raise ValueError("rotation_deg must be in [0, 360).")
        object.__setattr__(self, "geometry", geometry_snapshot(self.geometry))
        if self.geometry["type"] == "POLIGONO_CONVEXO":
            vertices = self.geometry["vertices_mm"]
            if any(min(p[axis] for p in vertices) != 0 for axis in (0, 1)):
                raise ValueError("Placement geometry must be local to its bounding-box origin.")


@dataclass(frozen=True, kw_only=True)
class OptimizationMetrics:
    """Future calculated values, with R4 units; no formulas run in T1."""
    utilization_pct: Decimal
    waste_mm2: Decimal
    new_sheets_used: int
    recoverable_remnant_mm2: Decimal
    material_area_mm2: Decimal
    placed_piece_area_mm2: Decimal

    def __post_init__(self):
        for name in ("utilization_pct", "waste_mm2", "recoverable_remnant_mm2",
                     "material_area_mm2", "placed_piece_area_mm2"):
            object.__setattr__(self, name, decimal_value(
                getattr(self, name), name, positive=name == "material_area_mm2",
            ))
        if self.utilization_pct > 100:
            raise ValueError("utilization_pct must be at most 100.")
        if type(self.new_sheets_used) is not int or self.new_sheets_used < 0:
            raise ValueError("new_sheets_used must be a nonnegative integer.")


@dataclass(frozen=True, kw_only=True)
class OptimizationResult:
    problem: OptimizationProblem
    placements: tuple[Placement, ...]
    metrics: OptimizationMetrics | None = None
    computation_time_ms: int | None = None

    def __post_init__(self):
        object.__setattr__(self, "placements", tuple(self.placements))
        units = {unit.identity: unit for unit in self.problem.units}
        stocks = {stock.identity: stock for group in self.problem.groups for stock in group.stock_candidates}
        seen = set()
        for placement in self.placements:
            identity = placement.piece.identity
            if identity in seen or units.get(identity) != placement.piece:
                raise ValueError("Placements must identify distinct requested piece snapshots.")
            if stocks.get(placement.stock.identity) != placement.stock:
                raise ValueError("Placement stock must belong to the problem snapshot.")
            seen.add(identity)
        if self.computation_time_ms is not None and (
            type(self.computation_time_ms) is not int or self.computation_time_ms < 0
        ):
            raise ValueError("computation_time_ms must be a nonnegative integer or None.")
        if self.metrics is not None and not self.placements:
            raise ValueError("Metrics require used material from accepted placements.")

    @property
    def method(self) -> Literal["FF", "BF", "WF"]:
        return "FF"

    @property
    def total_units(self) -> int:
        return len(self.problem.units)

    @property
    def placed_units(self) -> int:
        return len(self.placements)

    @property
    def complete(self) -> bool:
        return self.placed_units == self.total_units

    @property
    def materials_used(self) -> tuple[StockCandidate, ...]:
        return tuple({p.stock.identity: p.stock for p in self.placements}.values())

    @property
    def unplaced_units(self) -> tuple[PieceUnit, ...]:
        placed = {p.piece.identity for p in self.placements}
        return tuple(unit for unit in self.problem.units if unit.identity not in placed)
