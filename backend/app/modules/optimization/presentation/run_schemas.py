"""Frozen S1 v1 wire contracts. No routes or streaming transport are registered.

Decimal measures serialize as JSON strings, as in the existing HU-015 contract.
Spanish wire fields follow the Approved PLAN; internal model names are English.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator, model_validator

from ..application.dto import Progress, RunStatus
from ..domain.problem import MaterialSource
from .schemas import CircleGeometry, PolygonGeometry, PositiveId, RectangleGeometry


def decimal_input(value):
    if type(value) not in (Decimal, int, str):
        raise ValueError("Decimal measures require a decimal string, Decimal or integer.")
    return value


NonnegativeDecimal = Annotated[Decimal, BeforeValidator(decimal_input), Field(ge=0, allow_inf_nan=False)]
PositiveDecimal = Annotated[Decimal, BeforeValidator(decimal_input), Field(gt=0, allow_inf_nan=False)]
Count = Annotated[int, Field(strict=True, ge=0)]
Index = Annotated[int, Field(strict=True, gt=0)]
Geometry = Annotated[RectangleGeometry | CircleGeometry | PolygonGeometry, Field(discriminator="type")]


class ContractV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RunRequestV1(ContractV1):
    order_ids: Annotated[list[PositiveId], Field(min_length=1)]

    @field_validator("order_ids")
    @classmethod
    def distinct_orders(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("order_ids must be distinct.")
        return value


class ConfigV1(ContractV1):
    resolucion_raster_mm: PositiveDecimal
    margen_mm: NonnegativeDecimal
    separacion_mm: NonnegativeDecimal
    paso_angular_grados: Annotated[PositiveDecimal, Field(le=360)]


class MaterialKeyV1(ContractV1):
    id_tipo_vidrio: PositiveId
    espesor_mm: PositiveDecimal


class UnitRefV1(MaterialKeyV1):
    id_pedido: PositiveId
    id_pieza: PositiveId
    unit_index: Index


class PieceUnitV1(UnitRefV1):
    tipo_forma: Literal["RECTANGULO", "CIRCUNFERENCIA", "POLIGONO_CONVEXO"]
    geometria: Geometry
    area_mm2: PositiveDecimal

    @model_validator(mode="after")
    def matching_shape(self):
        if self.tipo_forma != self.geometria.type:
            raise ValueError("tipo_forma must match geometria.type.")
        return self


class StockRefV1(ContractV1):
    material_source: MaterialSource
    material_id: PositiveId
    stock_unit_index: Index

    @model_validator(mode="after")
    def remnant_unit(self):
        if self.material_source is MaterialSource.REMNANT and self.stock_unit_index != 1:
            raise ValueError("RETAZO has stock_unit_index=1.")
        return self


class StockV1(StockRefV1, MaterialKeyV1):
    geometria: Geometry
    area_mm2: PositiveDecimal

    @model_validator(mode="after")
    def rectangular_sheet(self):
        if self.material_source is MaterialSource.SHEET and self.geometria.type != "RECTANGULO":
            raise ValueError("PLANCHA requires rectangular geometry.")
        return self


class PlacementV1(UnitRefV1, StockRefV1):
    x_mm: NonnegativeDecimal
    y_mm: NonnegativeDecimal
    rotation_deg: Annotated[NonnegativeDecimal, Field(lt=360)]
    resolution_mm: PositiveDecimal
    geometria: Geometry  # Already oriented and normalized to its local bounding box.

    @model_validator(mode="after")
    def local_contour(self):
        if isinstance(self.geometria, PolygonGeometry):
            if any(min(p[axis] for p in self.geometria.vertices_mm) != 0 for axis in (0, 1)):
                raise ValueError("Placement contour must be local to its bounding-box origin.")
        return self


class ProgressV1(ContractV1):
    placed_units: Count
    total_units: Index
    progress_pct: Annotated[NonnegativeDecimal, Field(le=100)]

    @model_validator(mode="after")
    def truthful_progress(self):
        if self.progress_pct != Progress(placed_units=self.placed_units, total_units=self.total_units).progress_pct:
            raise ValueError("progress_pct must derive from accepted placements / total units.")
        return self


class MetricsV1(ContractV1):
    aprovechamiento_pct: Annotated[NonnegativeDecimal, Field(le=100)]
    merma_mm2: NonnegativeDecimal
    planchas_nuevas_usadas: Count
    retazo_recuperable_mm2: NonnegativeDecimal
    area_material_total_mm2: PositiveDecimal
    area_piezas_colocadas_mm2: NonnegativeDecimal
    tiempo_computacional_ms: Count


class GroupV1(MaterialKeyV1):
    units: Annotated[list[PieceUnitV1], Field(min_length=1)]

    @model_validator(mode="after")
    def compatible_units(self):
        if any((unit.id_tipo_vidrio, unit.espesor_mm) != (self.id_tipo_vidrio, self.espesor_mm)
               for unit in self.units):
            raise ValueError("Units must belong to the material group.")
        return self


class UnplacedUnitV1(UnitRefV1):
    reason: Literal["PENDING", "NO_FIT", "INTERRUPTED"]


class RunResponseV1(ProgressV1):
    schema_version: Literal[1]
    id_optimizacion: PositiveId
    estado: RunStatus
    metodo: Literal["FF"]
    order_ids: Annotated[list[PositiveId], Field(min_length=1)]
    configuracion: ConfigV1
    groups: Annotated[list[GroupV1], Field(min_length=1)]
    placements: list[PlacementV1]
    materials_used: list[StockV1]
    unplaced_units: list[UnplacedUnitV1]
    completo: bool
    metrics_available: bool
    metrics: MetricsV1 | None
    tiempo_computacional_ms: Count | None
    confirmed: bool
    confirmable: bool

    @model_validator(mode="after")
    def coherent_result(self):
        RunRequestV1(order_ids=self.order_ids)
        units = [unit for group in self.groups for unit in group.units]
        unit_map = {(u.id_pieza, u.unit_index): u for u in units}
        group_keys = {(g.id_tipo_vidrio, g.espesor_mm) for g in self.groups}
        if len(group_keys) != len(self.groups) or len(unit_map) != len(units) or len(units) != self.total_units:
            raise ValueError("Groups must represent every requested unit exactly once.")
        if {u.id_pedido for u in units} != set(self.order_ids):
            raise ValueError("Units must cover the selected orders.")
        stock_map = {(s.material_source, s.material_id, s.stock_unit_index): s for s in self.materials_used}
        if len(stock_map) != len(self.materials_used):
            raise ValueError("Duplicate physical stock resources.")
        placed = set()
        used = set()
        for placement in self.placements:
            key = placement.id_pieza, placement.unit_index
            unit = unit_map.get(key)
            stock_key = placement.material_source, placement.material_id, placement.stock_unit_index
            stock = stock_map.get(stock_key)
            if key in placed or unit is None or stock is None:
                raise ValueError("Placements require unique requested units and referenced stock.")
            if (placement.id_pedido, placement.id_tipo_vidrio, placement.espesor_mm) != (
                unit.id_pedido, unit.id_tipo_vidrio, unit.espesor_mm,
            ) or (stock.id_tipo_vidrio, stock.espesor_mm) != (unit.id_tipo_vidrio, unit.espesor_mm):
                raise ValueError("Placement traceability and material must match the snapshots.")
            if placement.resolution_mm != self.configuracion.resolucion_raster_mm:
                raise ValueError("Placement resolution must match the effective configuration.")
            placed.add(key)
            used.add(stock_key)
        missing = {(u.id_pieza, u.unit_index) for u in self.unplaced_units}
        if len(missing) != len(self.unplaced_units) or missing != set(unit_map) - placed or used != set(stock_map):
            raise ValueError("Unplaced units and used materials must match placements.")
        for unit in self.unplaced_units:
            original = unit_map[(unit.id_pieza, unit.unit_index)]
            if (unit.id_pedido, unit.id_tipo_vidrio, unit.espesor_mm) != (
                original.id_pedido, original.id_tipo_vidrio, original.espesor_mm,
            ):
                raise ValueError("Unplaced unit traceability must match the requested snapshot.")
        if self.placed_units != len(placed) or self.completo != (self.placed_units == self.total_units):
            raise ValueError("Completeness and counters must match placements.")
        if self.estado is RunStatus.COMPLETED and not self.completo:
            raise ValueError("COMPLETADA requires a complete result.")
        if self.estado is RunStatus.NO_SOLUTION and self.completo:
            raise ValueError("SIN_SOLUCION requires missing units.")
        if self.confirmed and self.estado is not RunStatus.COMPLETED:
            raise ValueError("Only COMPLETADA may have been confirmed.")
        if self.confirmable != (self.estado is RunStatus.COMPLETED and self.completo and not self.confirmed):
            raise ValueError("Invalid confirmation eligibility.")
        if self.metrics_available != (self.metrics is not None):
            raise ValueError("metrics_available must describe metrics nullability.")
        if self.metrics_available and not self.materials_used:
            raise ValueError("Metrics require used material.")
        if self.metrics is not None and self.metrics.tiempo_computacional_ms != self.tiempo_computacional_ms:
            raise ValueError("Computation time must be consistent with metrics.")
        expected_reason = {RunStatus.RUNNING: "PENDING", RunStatus.FAILED: "INTERRUPTED",
                           RunStatus.NO_SOLUTION: "NO_FIT", RunStatus.COMPLETED: "NO_FIT"}[self.estado]
        if any(unit.reason != expected_reason for unit in self.unplaced_units):
            raise ValueError("Unplaced unit reason must reflect the run state.")
        return self


class StartedDataV1(ContractV1):
    metodo: Literal["FF"]
    order_ids: Annotated[list[PositiveId], Field(min_length=1)]
    total_units: Index
    groups: Annotated[list[MaterialKeyV1], Field(min_length=1)]
    configuracion: ConfigV1

    @field_validator("order_ids")
    @classmethod
    def distinct_orders(cls, value):
        return RunRequestV1(order_ids=value).order_ids


class GroupStartedDataV1(MaterialKeyV1):
    total_units: Index  # Group-scoped; piece events use run-scoped counters.


class PieceStartedDataV1(UnitRefV1, ProgressV1):
    pass


class PiecePlacedDataV1(PlacementV1, ProgressV1):
    material: StockV1  # Allows first live placement to draw its material without another request.

    @model_validator(mode="after")
    def matching_material(self):
        if self.placed_units == 0:
            raise ValueError("piece_placed must include the accepted unit in its counter.")
        if (self.material_source, self.material_id, self.stock_unit_index, self.id_tipo_vidrio, self.espesor_mm) != (
            self.material.material_source, self.material.material_id, self.material.stock_unit_index,
            self.material.id_tipo_vidrio, self.material.espesor_mm,
        ):
            raise ValueError("Live material snapshot must match the placement.")
        return self


class GroupCompletedDataV1(MaterialKeyV1, ProgressV1):
    result_url: str  # Durable GET; counters here are group-scoped.


class MetricsDataV1(ContractV1):
    metrics_available: bool
    metrics: MetricsV1 | None

    @model_validator(mode="after")
    def available_metrics(self):
        if self.metrics_available != (self.metrics is not None):
            raise ValueError("metrics_available must describe metrics nullability.")
        return self


class CompletedDataV1(ProgressV1):
    estado: Literal["COMPLETADA", "SIN_SOLUCION"]
    completo: bool
    result_url: str

    @model_validator(mode="after")
    def terminal_state(self):
        if self.completo != (self.placed_units == self.total_units) or self.completo != (self.estado == "COMPLETADA"):
            raise ValueError("Terminal state must agree with accepted placements.")
        return self


class FailedDataV1(ContractV1):
    code: Literal["CALCULATION_FAILED", "EXECUTION_INTERRUPTED", "RESULT_SAVE_FAILED"]
    message: str
    estado: Literal["FALLIDA"]
    result_url: str


class EventV1(ContractV1):
    schema_version: Literal[1]
    sequence: Index
    id_optimizacion: PositiveId
    occurred_at: datetime

    @field_validator("occurred_at")
    @classmethod
    def utc_timestamp(cls, value):
        if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
            raise ValueError("occurred_at must be an ISO 8601 UTC timestamp.")
        return value


class OptimizationStartedV1(EventV1):
    event: Literal["optimization_started"]
    data: StartedDataV1


class GroupStartedV1(EventV1):
    event: Literal["group_started"]
    data: GroupStartedDataV1


class PieceStartedV1(EventV1):
    event: Literal["piece_started"]
    data: PieceStartedDataV1


class PiecePlacedV1(EventV1):
    event: Literal["piece_placed"]
    data: PiecePlacedDataV1


class GroupCompletedV1(EventV1):
    event: Literal["group_completed"]
    data: GroupCompletedDataV1


class MetricsCalculatedV1(EventV1):
    event: Literal["metrics_calculated"]
    data: MetricsDataV1


class OptimizationCompletedV1(EventV1):
    event: Literal["optimization_completed"]
    data: CompletedDataV1


class OptimizationFailedV1(EventV1):
    event: Literal["optimization_failed"]
    data: FailedDataV1


OptimizationEventV1 = Annotated[
    OptimizationStartedV1 | GroupStartedV1 | PieceStartedV1 | PiecePlacedV1
    | GroupCompletedV1 | MetricsCalculatedV1 | OptimizationCompletedV1 | OptimizationFailedV1,
    Field(discriminator="event"),
]


class ConfirmedOrderV1(ContractV1):
    id_pedido: PositiveId
    estado: Literal["CONFIRMADO"]


class CreatedRemnantV1(ContractV1):
    id_retazo: PositiveId
    source: StockRefV1
    x_mm: NonnegativeDecimal
    y_mm: NonnegativeDecimal
    geometria: RectangleGeometry
    area_mm2: PositiveDecimal


class ConfirmResponseV1(ContractV1):
    schema_version: Literal[1]
    id_optimizacion: PositiveId
    confirmed: Literal[True]
    orders: Annotated[list[ConfirmedOrderV1], Field(min_length=1)]
    materials_consumed: Annotated[list[StockRefV1], Field(min_length=1)]
    remnants_created: list[CreatedRemnantV1]

    @model_validator(mode="after")
    def distinct_consumption(self):
        orders = [order.id_pedido for order in self.orders]
        resources = [(s.material_source, s.material_id, s.stock_unit_index) for s in self.materials_consumed]
        if len(set(orders)) != len(orders) or len(set(resources)) != len(resources):
            raise ValueError("Confirmation must not duplicate orders or physical consumption.")
        return self


class ErrorDetailV1(ContractV1):
    code: Literal["UNAUTHENTICATED", "FORBIDDEN", "NOT_FOUND", "STATE_CONFLICT", "CONFIG_CONFLICT",
                  "STOCK_CONFLICT", "ALREADY_CONFIRMED", "INVALID_INPUT", "NOT_CONFIRMABLE", "INTERNAL_ERROR"]
    message: str


class ErrorResponseV1(ContractV1):
    detail: ErrorDetailV1
