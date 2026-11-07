"""Contrato comparison-v1. Autor: Fabricio Melendez Quezada. Revisor: Andro Quispe."""
from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, model_validator
from .run_schemas import ContractV1, PositiveId, Index, Count, ConfigV1, MetricsV1, RunResponseV1, ConfirmResponseV1
from .visual_schemas import (MaskDescriptorV2, VisualMaskV2, DATA_TYPES, PreparationStartedV2,
    PieceReadyV2, OrientationTestingV2, SourceSelectedV2)
from .run_schemas import UnitRefV1

Method = Literal["FF", "BF", "WF"]


class ComparisonSelection(ContractV1):
    execution_id: PositiveId
    expected_version: PositiveId


class ComparisonRelease(ContractV1):
    expected_version: PositiveId


class ExecutionSummary(ContractV1):
    execution_id: PositiveId
    method: Method
    status: Literal["EN_EJECUCION", "COMPLETADA", "FALLIDA"]
    complete: bool
    eligible: bool
    placed_units: Count
    total_units: Index
    metrics: MetricsV1 | None
    computation_time_ms: Count | None
    failure_code: str | None


class ComparisonSummary(ContractV1):
    profile: Literal["comparison-v1"] = "comparison-v1"
    schema_version: Literal[1] = 1
    comparison_id: PositiveId
    version: PositiveId
    status: Literal["EN_EJECUCION", "COMPLETADA", "SIN_SOLUCION", "FALLIDA"]
    input_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    order_ids: list[PositiveId]
    configuration: ConfigV1
    configuration_id: PositiveId
    configuration_version: PositiveId
    requested_pieces: list[dict]
    executions: Annotated[list[ExecutionSummary], Field(min_length=3, max_length=3)]
    selected_execution_id: PositiveId | None
    terminal: bool
    incomplete: bool
    released: bool
    confirmed: bool
    selection_allowed: bool
    confirmable: bool
    confirmation: dict | None

    @model_validator(mode="after")
    def identities(self):
        if {e.method for e in self.executions} != {"FF", "BF", "WF"} or len({e.execution_id for e in self.executions}) != 3:
            raise ValueError("Exactly three distinct method identities are required")
        if self.selected_execution_id is not None and self.selected_execution_id not in {e.execution_id for e in self.executions}:
            raise ValueError("Selected execution is outside comparison")
        if self.confirmable and (not self.terminal or self.released or self.confirmed or self.selected_execution_id is None):
            raise ValueError("Invalid confirmation eligibility")
        return self


class ComparisonResult(RunResponseV1):
    # Coherencia geométrica/R4 reutilizada; la confirmabilidad pública es del agregado.
    metodo: Method
    confirmed: bool = Field(default=False, exclude=True)
    confirmable: bool = Field(default=False, exclude=True)

    @model_validator(mode="before")
    @classmethod
    def candidate_state(cls, value):
        data = dict(value)
        data["confirmed"] = False
        data["confirmable"] = data.get("estado") == "COMPLETADA" and data.get("completo") is True
        return data


class ExecutionResponse(ContractV1):
    profile: Literal["comparison-v1"] = "comparison-v1"
    schema_version: Literal[1] = 1
    comparison_id: PositiveId
    execution: ExecutionSummary
    result: ComparisonResult | None

    @model_validator(mode="after")
    def matching_result(self):
        if self.result is not None and (self.result.metodo != self.execution.method or self.result.id_optimizacion != self.comparison_id):
            raise ValueError("Result identity mismatch")
        return self


class ComparisonConfirmation(ContractV1):
    profile: Literal["comparison-v1"] = "comparison-v1"
    schema_version: Literal[1] = 1
    comparison_id: PositiveId
    execution_id: PositiveId
    version: PositiveId
    receipt: ConfirmResponseV1


class ComparisonMask(MaskDescriptorV2):
    comparison_id: PositiveId
    execution_id: PositiveId
    method: Method


class ComparisonMaskPayload(VisualMaskV2):
    schema_version: Literal[1] = 1
    profile: Literal["comparison-v1"] = "comparison-v1"
    comparison_id: PositiveId
    execution_id: PositiveId
    method: Method


class ComparisonEvent(ContractV1):
    profile: Literal["comparison-v1"] = "comparison-v1"
    schema_version: Literal[1] = 1
    comparison_id: PositiveId
    sequence: Index
    execution_id: PositiveId | None
    method: Method | None
    execution_sequence: Index | None
    timestamp: datetime
    event: Literal["comparison_accepted", "engine_ready", "engine_started", "group_started", "piece_started",
        "piece_placed", "group_completed", "preparation_started", "piece_rasterizing", "piece_ready",
        "preparation_completed", "ordering_ready", "orientation_testing", "source_selected", "piece_unplaced",
        "result_persisted", "execution_failed", "comparison_finished", "heartbeat", "snapshot_required"]
    data: dict

    @model_validator(mode="after")
    def scope(self):
        global_event = self.event in {"comparison_accepted", "comparison_finished", "heartbeat", "snapshot_required"}
        if global_event:
            if any(v is not None for v in (self.method, self.execution_id, self.execution_sequence)):
                raise ValueError("Global event cannot name an execution")
        elif any(v is None for v in (self.method, self.execution_id, self.execution_sequence)):
            raise ValueError("Execution event requires identity and sequence")
        for name in ("mask", "material_mask"):
            if name in self.data:
                mask = ComparisonMask.model_validate(self.data[name])
                if (mask.comparison_id, mask.id_optimizacion, mask.execution_id, mask.method) != (
                        self.comparison_id, self.comparison_id, self.execution_id, self.method):
                    raise ValueError("Cross-execution mask reference")
        if self.event == "ordering_ready" and (self.data.get("criterion") != "area_desc_max_side_desc_order_piece_unit_asc"
                or not isinstance(self.data.get("units"), list)):
            raise ValueError("Ordering requires real ordered references")
        if self.event == "preparation_started" and self.data.get("metodo") != self.method:
            raise ValueError("Preparation method differs from execution")
        EVENT_DATA[self.event].model_validate(self.data)
        return self


class PreparationStarted(PreparationStartedV2):
    metodo: Method


class PieceReady(PieceReadyV2):
    mask: ComparisonMask


class OrientationTesting(OrientationTestingV2):
    mask: ComparisonMask


class SourceSelected(SourceSelectedV2):
    mask: ComparisonMask
    material_mask: ComparisonMask


class Ordering(ContractV1):
    criterion: Literal["area_desc_max_side_desc_order_piece_unit_asc"]
    # Acompaña a L-03 (300 unidades); 300 referencias (~30 KB) < 64 KB por evento.
    units: Annotated[list[UnitRefV1], Field(min_length=1, max_length=300)]


class ExecutionReference(ContractV1):
    execution_id: PositiveId
    method: Method


class Accepted(ContractV1):
    version: PositiveId
    executions: Annotated[list[ExecutionReference], Field(min_length=3, max_length=3)]


class Finished(ContractV1):
    version: PositiveId
    status: Literal["COMPLETADA", "SIN_SOLUCION", "FALLIDA"]
    incomplete: bool


class Failure(ContractV1):
    code: Literal["EXECUTION_FAILED", "TIME_BUDGET_EXCEEDED", "MEMORY_BUDGET_EXCEEDED",
                  "RESULT_SAVE_FAILED", "WORKER_STOPPED", "PROCESS_START_FAILED"]


class Cursor(ContractV1):
    latest_sequence: Index


EVENT_DATA = {**DATA_TYPES, "preparation_started": PreparationStarted, "piece_ready": PieceReady,
    "orientation_testing": OrientationTesting, "source_selected": SourceSelected,
    "comparison_accepted": Accepted, "comparison_finished": Finished, "ordering_ready": Ordering,
    "engine_ready": ContractV1, "engine_started": ContractV1, "heartbeat": ContractV1,
    "snapshot_required": Cursor, "execution_failed": Failure, "result_persisted": ExecutionSummary}
