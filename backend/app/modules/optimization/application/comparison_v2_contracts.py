"""Pure B01 result/diagnostic DTOs, independent of HTTP and persistence."""
from dataclasses import dataclass
from types import MappingProxyType
from collections.abc import Mapping
from decimal import Decimal
from typing import Literal

from .comparison_catalog import BY_METHOD, METHODS_V2, validate_methods
from .comparison_contracts import immutable_json
from ..domain.problem import OptimizationProblem, OptimizationResult, decimal_value

TerminationReason = Literal[
    "COMPLETED", "NO_FIT", "EXPANSION_LIMIT", "GEOMETRY_PROBE_LIMIT",
    "STATE_MEMORY_LIMIT", "TIME_LIMIT", "GLOBAL_TIME_LIMIT", "TIME_BUDGET_EXCEEDED",
    "MEMORY_BUDGET_EXCEEDED", "EXECUTION_FAILED", "RESULT_SAVE_FAILED",
    "WORKER_STOPPED", "PROCESS_START_FAILED", "CANCELLED",
]
ENGINE_REASONS = frozenset(("COMPLETED", "NO_FIT", "EXPANSION_LIMIT",
                            "GEOMETRY_PROBE_LIMIT", "STATE_MEMORY_LIMIT", "TIME_LIMIT"))
SUPERVISOR_REASONS = frozenset(("GLOBAL_TIME_LIMIT", "TIME_BUDGET_EXCEEDED",
    "MEMORY_BUDGET_EXCEEDED", "EXECUTION_FAILED", "RESULT_SAVE_FAILED",
    "WORKER_STOPPED", "PROCESS_START_FAILED", "CANCELLED"))
BEAM_REASONS = ENGINE_REASONS - {"COMPLETED", "NO_FIT"}


@dataclass(frozen=True, kw_only=True)
class ExecutionDiagnostic:
    origin: str
    termination_reason: str
    statistics: Mapping[str, int]

    def __post_init__(self):
        allowed = {"ENGINE": ENGINE_REASONS, "SUPERVISOR": SUPERVISOR_REASONS}
        if self.origin not in allowed or self.termination_reason not in allowed[self.origin]:
            raise ValueError("Invalid termination reason/origin")
        if not isinstance(self.statistics, Mapping) or any(
            type(key) is not str or not key or type(value) is not int or value < 0
            for key, value in self.statistics.items()
        ):
            raise ValueError("Diagnostic statistics require named nonnegative integer counters")
        object.__setattr__(self, "statistics", MappingProxyType(dict(self.statistics)))

    def public(self):
        return dict(origin=self.origin, termination_reason=self.termination_reason,
                    statistics=dict(self.statistics))


@dataclass(frozen=True, kw_only=True)
class ExecutionPayloadV2:
    method: str
    result: OptimizationResult | None
    diagnostic: ExecutionDiagnostic | None

    def __post_init__(self):
        validate_methods((self.method,))
        if self.result is not None and (
            not isinstance(self.result, OptimizationResult)
            or self.result.method != self.method
            or type(self.result) is not BY_METHOD[self.method].result_type
        ):
            raise ValueError("Result type/method does not identify its execution")
        # None is reserved for historical diagnostics which were never captured.
        if self.diagnostic is not None:
            reason = self.diagnostic.termination_reason
            if reason in BEAM_REASONS and self.method != "M6-BS":
                raise ValueError("Beam Search resource reason belongs to M6-BS")
            if self.result is None and reason in {"COMPLETED", "NO_FIT"}:
                raise ValueError("Geometric termination requires an actual result")
            if self.result is not None and (
                self.diagnostic.origin != "ENGINE"
                or (reason == "COMPLETED") != self.result.complete
            ):
                raise ValueError("Result completeness differs from termination diagnostic")


@dataclass(frozen=True, kw_only=True)
class ComparisonInputV2:
    """Frozen input metadata; B02/B05 will persist and supervise it, not B01."""
    problem: OptimizationProblem
    configuration_id: int
    configuration_version: int
    requested_pieces: tuple[Mapping, ...]
    minimum_width_mm: Decimal
    minimum_height_mm: Decimal
    methods: tuple[str, ...] = METHODS_V2

    def __post_init__(self):
        if not isinstance(self.problem, OptimizationProblem) or any(
            type(value) is not int or not 0 < value <= 2147483647
            for value in (self.configuration_id, self.configuration_version)
        ):
            raise ValueError("Input requires a prepared problem and configuration identity")
        if tuple(self.methods) != METHODS_V2:
            raise ValueError("Input requires the ordered comparison-v2 catalog")
        if not isinstance(self.requested_pieces, (list, tuple)) or not self.requested_pieces or any(
            not isinstance(piece, Mapping) for piece in self.requested_pieces
        ):
            raise ValueError("Original requested pieces must be captured")
        for name in ("minimum_width_mm", "minimum_height_mm"):
            value = decimal_value(getattr(self, name), name)
            if value < 0:
                raise ValueError("Residual thresholds cannot be negative")
            object.__setattr__(self, name, value)
        object.__setattr__(self, "methods", tuple(self.methods))
        object.__setattr__(self, "requested_pieces", immutable_json(self.requested_pieces))
