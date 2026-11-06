"""Opt-in B01 HTTP contracts. No comparison-v2 routes are registered."""
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import Field, StrictBool, field_validator, model_validator

from ..application.comparison_catalog import METHODS_V2, MethodV2, validate_methods
from ..application.comparison_v2_contracts import (
    BEAM_REASONS, ExecutionDiagnostic, TerminationReason,
)
from . import comparison_schemas as v1
from .run_schemas import ContractV1, Count, Index, MetricsV1, RunResponseV1, UnitRefV1

PositiveIdV2 = Annotated[int, Field(strict=True, gt=0, le=2147483647)]
DispatchState = Literal["QUEUED", "STARTING", "RUNNING", "TERMINATED"]
Outcome = Literal["COMPLETE", "PARTIAL", "FAILED"]


class DiagnosticV2(ContractV1):
    origin: Literal["ENGINE", "SUPERVISOR"]
    termination_reason: TerminationReason
    statistics: dict[str, Count]

    @model_validator(mode="after")
    def reason_origin(self):
        ExecutionDiagnostic(**self.model_dump())
        return self


class ExecutionReferenceV2(ContractV1):
    execution_id: PositiveIdV2
    method: MethodV2


class ComparisonSelectionV2(ContractV1):
    execution_id: PositiveIdV2
    expected_version: PositiveIdV2


class ComparisonReleaseV2(ContractV1):
    expected_version: PositiveIdV2


class ComparisonHistoryItemV2(ContractV1):
    comparison_id: PositiveIdV2
    profile: Literal["comparison-v1", "comparison-v2"]
    started_at: datetime
    status: Literal["EN_EJECUCION", "COMPLETADA", "FALLIDA", "SIN_SOLUCION"]
    order_ids: list[PositiveIdV2]
    confirmed: StrictBool
    released: StrictBool


class ComparisonHistoryV2(ContractV1):
    items: list[ComparisonHistoryItemV2]
    next_before_id: PositiveIdV2 | None


class ComparisonConfirmationV2(v1.ComparisonConfirmation):
    profile: Literal["comparison-v2"] = "comparison-v2"
    schema_version: Literal[2] = 2
    comparison_id: PositiveIdV2
    execution_id: PositiveIdV2
    version: PositiveIdV2


class ExecutionSummaryV2(ExecutionReferenceV2):
    status: Literal["EN_EJECUCION", "COMPLETADA", "FALLIDA"]
    dispatch_state: DispatchState
    outcome: Outcome | None
    result_available: StrictBool
    complete: StrictBool
    eligible: StrictBool
    placed_units: Count
    total_units: Index
    metrics: MetricsV1 | None
    computation_time_ms: Count | None
    diagnostic: DiagnosticV2 | None

    @model_validator(mode="after")
    def lifecycle(self):
        terminal = self.dispatch_state == "TERMINATED"
        if terminal != (self.status != "EN_EJECUCION") or self.placed_units > self.total_units:
            raise ValueError("Dispatch/cycle state or counters are inconsistent")
        if self.diagnostic and self.diagnostic.termination_reason in BEAM_REASONS and self.method != "M6-BS":
            raise ValueError("Beam resource reasons identify M6-BS")
        if not terminal:
            if (self.outcome is not None or self.diagnostic is not None or self.result_available
                    or self.complete or self.eligible or self.metrics is not None):
                raise ValueError("Unfinished execution cannot claim a terminal result")
        elif self.diagnostic is None:
            raise ValueError("V2 terminal execution requires a diagnostic")
        elif self.status == "FALLIDA":
            if (self.outcome != "FAILED" or self.result_available or self.complete or self.eligible
                    or self.placed_units or self.metrics is not None
                    or self.diagnostic.termination_reason in ("COMPLETED", "NO_FIT")):
                raise ValueError("Failed execution cannot invent a geometric result")
        else:
            if (not self.result_available or self.outcome != ("COMPLETE" if self.complete else "PARTIAL")
                    or self.complete != (self.placed_units == self.total_units)
                    or self.eligible and not self.complete or self.diagnostic.origin != "ENGINE"
                    or (self.diagnostic.termination_reason == "COMPLETED") != self.complete):
                raise ValueError("Result completeness/outcome/diagnostic mismatch")
        if self.metrics is not None and (
            not self.placed_units or self.metrics.tiempo_computacional_ms != self.computation_time_ms
        ):
            raise ValueError("Metrics require real placements and the same calculation time")
        return self


class ComparisonSummaryV2(v1.ComparisonSummary):
    profile: Literal["comparison-v2"] = "comparison-v2"
    schema_version: Literal[2] = 2
    comparison_id: PositiveIdV2
    version: PositiveIdV2
    order_ids: Annotated[list[PositiveIdV2], Field(min_length=1)]
    configuration_id: PositiveIdV2
    configuration_version: PositiveIdV2
    selected_execution_id: PositiveIdV2 | None
    terminal: StrictBool
    incomplete: StrictBool
    released: StrictBool
    confirmed: StrictBool
    selection_allowed: StrictBool
    confirmable: StrictBool
    methods: list[MethodV2]
    executions: Annotated[list[ExecutionSummaryV2], Field(min_length=6, max_length=6)]
    supervisor_stopped: StrictBool

    @model_validator(mode="after")
    def identities(self):
        if len(set(self.order_ids)) != len(self.order_ids):
            raise ValueError("Duplicate order identity")
        if tuple(self.methods) != METHODS_V2:
            raise ValueError("Catalog order differs from comparison-v2")
        validate_methods([e.method for e in self.executions], require_all=True)
        by_id = {e.execution_id: e for e in self.executions}
        if len(by_id) != len(self.executions):
            raise ValueError("Duplicate execution identity")
        all_terminal = all(e.dispatch_state == "TERMINATED" for e in self.executions)
        if self.terminal != (self.supervisor_stopped and all_terminal):
            raise ValueError("Terminal comparison requires stopped supervisor and executions")
        expected_status = ("EN_EJECUCION" if not self.terminal else
            "COMPLETADA" if any(e.complete for e in self.executions) else
            "FALLIDA" if any(e.status == "FALLIDA" for e in self.executions) else "SIN_SOLUCION")
        if self.status != expected_status:
            raise ValueError("Aggregate status differs from its executions")
        editable = self.terminal and not self.released and not self.confirmed
        for execution in self.executions:
            if execution.eligible != (editable and execution.complete and execution.result_available):
                raise ValueError("Eligibility requires safe aggregate closure")
        selected = by_id.get(self.selected_execution_id)
        if self.selected_execution_id is not None and (
            selected is None or not self.terminal or self.released
            or not selected.complete or not selected.result_available
        ):
            raise ValueError("Invalid manual selection")
        if (self.selection_allowed != (editable and any(e.eligible for e in self.executions))
                or self.confirmable != (editable and selected is not None)
                or self.incomplete != any(e.outcome in ("PARTIAL", "FAILED") for e in self.executions)):
            raise ValueError("Aggregate actions/incomplete flag are inconsistent")
        if self.confirmed != (self.confirmation is not None):
            raise ValueError("Confirmation metadata missing or unexpected")
        if self.confirmed and (selected is None or self.confirmation.get("execution_id") != selected.execution_id
                               or self.confirmation.get("method") != selected.method):
            raise ValueError("Confirmation belongs to another execution")
        return self


class UnplacedUnitV2(UnitRefV1):
    reason: Literal["NO_FIT", "RESOURCE_LIMIT"]


class ComparisonResultV2(v1.ComparisonResult):
    schema_version: Literal[2] = 2
    metodo: MethodV2
    termination_reason: TerminationReason
    unplaced_units: list[UnplacedUnitV2]

    @model_validator(mode="after")
    def coherent_result(self):
        if self.estado.value not in ("COMPLETADA", "SIN_SOLUCION"):
            raise ValueError("A persisted layout is complete or partial, not an active/failed execution")
        # Reuse V1 geometry/identity/R4 invariants, without changing its reason vocabulary.
        geometry_view = self.model_copy(update={"unplaced_units": [
            unit.model_copy(update={"reason": "NO_FIT"}) for unit in self.unplaced_units]})
        RunResponseV1.coherent_result(geometry_view)
        allowed = {"COMPLETED", "NO_FIT"} | (BEAM_REASONS if self.metodo == "M6-BS" else set())
        if self.termination_reason not in allowed or (self.termination_reason == "COMPLETED") != self.completo:
            raise ValueError("Layout completeness/termination mismatch")
        reason = "NO_FIT" if self.termination_reason == "NO_FIT" else "RESOURCE_LIMIT"
        if any(unit.reason != reason for unit in self.unplaced_units):
            raise ValueError("Resource interruption must not be mislabeled NO_FIT")
        return self


class ExecutionResponseV2(ContractV1):
    profile: Literal["comparison-v2"] = "comparison-v2"
    schema_version: Literal[2] = 2
    comparison_id: PositiveIdV2
    execution: ExecutionSummaryV2
    result: ComparisonResultV2 | None

    @model_validator(mode="after")
    def matching_result(self):
        e, r = self.execution, self.result
        if e.result_available != (r is not None):
            raise ValueError("Result availability differs from persisted payload")
        if r is not None and (
            r.metodo != e.method or r.id_optimizacion != self.comparison_id
            or r.completo != e.complete or r.placed_units != e.placed_units or r.total_units != e.total_units
            or r.metrics != e.metrics or r.tiempo_computacional_ms != e.computation_time_ms
            or r.termination_reason != e.diagnostic.termination_reason
        ):
            raise ValueError("Result identity/counters/diagnostic differ from execution")
        return self


class ComparisonMaskV2(v1.ComparisonMask):
    profile: Literal["comparison-v2"] = "comparison-v2"
    schema_version: Literal[2] = 2
    method: MethodV2

    @model_validator(mode="after")
    def identity(self):
        if self.id_optimizacion != self.comparison_id:
            raise ValueError("Mask descriptor belongs to another comparison")
        return self


class ComparisonMaskPayloadV2(v1.ComparisonMaskPayload):
    profile: Literal["comparison-v2"] = "comparison-v2"
    schema_version: Literal[2] = 2
    method: MethodV2

    @model_validator(mode="after")
    def identity(self):
        if self.id_optimizacion != self.comparison_id:
            raise ValueError("Mask belongs to another comparison")
        return self


class AcceptedV2(ContractV1):
    version: PositiveIdV2
    methods: list[MethodV2]
    executions: Annotated[list[ExecutionReferenceV2], Field(min_length=6, max_length=6)]

    @model_validator(mode="after")
    def identities(self):
        if tuple(self.methods) != METHODS_V2 or len({e.execution_id for e in self.executions}) != 6:
            raise ValueError("Invalid accepted comparison identities")
        validate_methods([e.method for e in self.executions], require_all=True)
        return self


class SearchProgressV2(ContractV1):
    completed_levels: Count
    processed_units: Count
    total_units: Index
    expansions: Count
    geometry_probes: Count
    frontier_size: Index

    @model_validator(mode="after")
    def processed(self):
        if self.processed_units > self.total_units:
            raise ValueError("Search progress exceeds requested units")
        return self


class PreparationStartedV2(v1.PreparationStarted):
    metodo: MethodV2


class PieceReadyV2(v1.PieceReady):
    mask: ComparisonMaskV2


class OrientationTestingV2(v1.OrientationTesting):
    mask: ComparisonMaskV2


class SourceSelectedV2(v1.SourceSelected):
    mask: ComparisonMaskV2
    material_mask: ComparisonMaskV2


class FinishedV2(v1.Finished):
    supervisor_stopped: Literal[True]


EVENT_DATA_V2 = {**v1.EVENT_DATA, "comparison_accepted": AcceptedV2,
    "comparison_finished": FinishedV2, "execution_state": ExecutionSummaryV2,
    "result_persisted": ExecutionSummaryV2, "execution_failed": ExecutionSummaryV2,
    "search_progress": SearchProgressV2, "preparation_started": PreparationStartedV2,
    "piece_ready": PieceReadyV2, "orientation_testing": OrientationTestingV2,
    "source_selected": SourceSelectedV2}


class ComparisonEventV2(ContractV1):
    profile: Literal["comparison-v2"] = "comparison-v2"
    schema_version: Literal[2] = 2
    comparison_id: PositiveIdV2
    sequence: Index
    timestamp: datetime
    execution_id: PositiveIdV2 | None
    method: MethodV2 | None
    execution_sequence: Index | None
    presentation: Literal["OBSERVED", "PROVISIONAL", "FINAL_REPLAY"] | None
    event: str
    data: dict

    @field_validator("timestamp")
    @classmethod
    def utc_timestamp(cls, value):
        if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
            raise ValueError("Events require UTC timestamps")
        return value

    @model_validator(mode="after")
    def scope(self):
        if self.event not in EVENT_DATA_V2:
            raise ValueError("Unknown comparison-v2 event")
        global_event = self.event in {"comparison_accepted", "comparison_finished", "heartbeat", "snapshot_required"}
        if global_event:
            if any(v is not None for v in (self.method, self.execution_id, self.execution_sequence, self.presentation)):
                raise ValueError("Global event cannot identify an execution")
        elif any(v is None for v in (self.method, self.execution_id, self.execution_sequence, self.presentation)):
            raise ValueError("Execution event requires explicit scope/presentation")
        if self.event == "search_progress":
            if self.method != "M6-BS" or self.presentation != "PROVISIONAL":
                raise ValueError("Provisional search progress belongs to M6-BS")
        elif self.presentation == "PROVISIONAL":
            raise ValueError("Provisional branches are not definitive placement facts")
        if self.method == "M6-BS" and self.event in (
            "piece_started", "piece_placed", "piece_unplaced", "source_selected", "orientation_testing"
        ) and self.presentation != "FINAL_REPLAY":
            raise ValueError("Beam placements can only describe the chosen final replay")
        payload = EVENT_DATA_V2[self.event].model_validate(self.data)
        if isinstance(payload, ExecutionSummaryV2):
            if (payload.execution_id, payload.method) != (self.execution_id, self.method):
                raise ValueError("Event payload identifies another execution")
            if self.event == "result_persisted" and not payload.result_available:
                raise ValueError("Persisted event requires a real result")
            if self.event == "execution_failed" and payload.outcome != "FAILED":
                raise ValueError("Failure event requires failed execution")
        if self.event == "preparation_started" and payload.metodo != self.method:
            raise ValueError("Preparation method differs from execution")
        for name in ("mask", "material_mask"):
            if name in self.data:
                mask = ComparisonMaskV2.model_validate(self.data[name])
                if (mask.comparison_id, mask.id_optimizacion, mask.execution_id, mask.method) != (
                    self.comparison_id, self.comparison_id, self.execution_id, self.method
                ):
                    raise ValueError("Cross-execution mask reference")
        return self
