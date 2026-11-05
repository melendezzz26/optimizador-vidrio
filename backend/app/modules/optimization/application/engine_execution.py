"""TA-043/B03: opt-in execution adapters; no process, admission or HTTP policy."""
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from decimal import Decimal
from time import perf_counter_ns
from typing import Literal

from .comparison_catalog import BY_METHOD, validate_methods
from .comparison_v2_contracts import ExecutionDiagnostic, ExecutionPayloadV2
from .errors import ExecutionInterrupted, TimeBudgetExceeded
from ..domain.beam_search import BeamSearchLimits, BeamSearchOutcome, BeamSearchProgress
from ..domain.hole_filling import HoleFillingLimits
from ..domain.metrics import ResidualRectangle, calculate_metrics
from ..domain.packing import FirstFitEvent
from ..domain.problem import OptimizationProblem, OptimizationResult, decimal_value
from ..domain.visual_events import VisualEvent


@dataclass(frozen=True, kw_only=True)
class ExecutionScope:
    comparison_id: int
    execution_id: int
    method: str

    def __post_init__(self):
        validate_methods((self.method,))
        if any(type(value) is not int or not 0 < value <= 2147483647
               for value in (self.comparison_id, self.execution_id)):
            raise ValueError("Execution scope requires positive owner identities")


@dataclass(frozen=True, kw_only=True)
class EngineObservation:
    """Internal facts, scoped at source; HTTP sequencing/retention belongs to B05/B06."""
    scope: ExecutionScope
    kind: Literal["milestone", "visual", "search_progress", "final_layout"]
    presentation: Literal["OBSERVED", "PROVISIONAL", "FINAL_REPLAY"]
    fact: FirstFitEvent | VisualEvent | BeamSearchProgress | OptimizationResult


@dataclass(frozen=True, kw_only=True)
class AdaptedExecution:
    scope: ExecutionScope
    payload: ExecutionPayloadV2
    residuals: tuple[ResidualRectangle, ...] = ()
    beam_outcome: BeamSearchOutcome | None = None
    observer_error_type: str | None = None
    error_type: str | None = None


class EngineExecutionAdapter:
    """Create a fresh productive engine per invocation, preserving native decisions.

    The optional limits are the engines' existing objects (e.g. focused resource
    tests). Production defaults remain untouched. BS-2 always requires width 2.
    An observer exception disconnects that observer and is reported explicitly;
    checkpoints remain independent. Process kills cannot be rescued by this layer.
    """
    def __init__(self, method, *, beam_limits: BeamSearchLimits | None = None,
                 hole_limits: HoleFillingLimits | None = None):
        validate_methods((method,))
        if beam_limits is not None and (method != "M6-BS" or not isinstance(beam_limits, BeamSearchLimits)
                                        or beam_limits.width != 2):
            raise ValueError("BS-2 limits require M6-BS with width 2")
        if hole_limits is not None and (method != "HF" or not isinstance(hole_limits, HoleFillingLimits)):
            raise ValueError("Hole Filling limits belong to HF")
        self.method, self.beam_limits, self.hole_limits = method, beam_limits, hole_limits

    def execute(self, scope: ExecutionScope, problem: OptimizationProblem, *,
                minimum_width_mm: Decimal, minimum_height_mm: Decimal,
                checkpoint: Callable[[], None] | None = None,
                on_observation: Callable[[EngineObservation], None] | None = None) -> AdaptedExecution:
        if not isinstance(scope, ExecutionScope) or scope.method != self.method:
            raise ValueError("Adapter and execution scope identify different engines")
        if not isinstance(problem, OptimizationProblem):
            raise ValueError("A canonical optimization problem is required")
        minimums = tuple(decimal_value(v, "residual threshold") for v in (minimum_width_mm, minimum_height_mm))
        if any(v < 0 for v in minimums):
            raise ValueError("Residual thresholds cannot be negative")
        if checkpoint is not None and not callable(checkpoint) or on_observation is not None and not callable(on_observation):
            raise ValueError("Callbacks must be callable")
        definition = BY_METHOD[self.method]
        check = checkpoint if checkpoint is not None else lambda: None
        observer, observer_error, observation_ns = on_observation, None, 0
        outcome = None
        started = perf_counter_ns()

        def observe(kind, fact, presentation="OBSERVED"):
            nonlocal observer, observer_error, observation_ns
            if observer is None:
                return
            before = perf_counter_ns()
            try:
                observer(EngineObservation(scope=scope, kind=kind, presentation=presentation, fact=fact))
            except Exception as error:
                observer_error = type(error).__name__
                observer = None
            finally:
                observation_ns += perf_counter_ns() - before

        try:
            check()
            if self.method == "M6-BS":
                optimizer = definition.optimizer_type(self.beam_limits)
                outcome = optimizer.run(problem, checkpoint=check, on_progress=(
                    lambda fact: observe("search_progress", fact, "PROVISIONAL")) if observer is not None else None)
                result, reason, statistics = outcome.result, outcome.stop_reason, outcome.statistics
            else:
                optimizer = (definition.optimizer_type(self.hole_limits) if self.method == "HF"
                             else definition.optimizer_type())
                presentation = "FINAL_REPLAY" if self.method == "HF" else "OBSERVED"
                result = optimizer.optimize(problem,
                    (lambda fact: observe("milestone", fact, presentation)) if observer is not None else None,
                    checkpoint=check,
                    on_visual=(lambda fact: observe("visual", fact, presentation)) if observer is not None else None)
                reason = None
                statistics = {key: int(value) for key, value in asdict(optimizer.stats).items()} if self.method == "HF" else {}
            if type(result) is not definition.result_type or result.method != self.method or result.problem != problem:
                raise ValueError("Engine result does not belong to its canonical execution")
            # Validate the native cause before metrics; never reinterpret resource exhaustion as NO_FIT.
            diagnostic = ExecutionDiagnostic(origin="ENGINE", termination_reason=reason or (
                "COMPLETED" if result.complete else "NO_FIT"), statistics=statistics)
            ExecutionPayloadV2(method=self.method, result=result, diagnostic=diagnostic)
            check()
            result, residuals = calculate_metrics(result, *minimums)
            check()
            elapsed = max(0, (perf_counter_ns() - started - observation_ns) // 1_000_000)
            result = replace(result, computation_time_ms=elapsed)
            payload = ExecutionPayloadV2(method=self.method, result=result, diagnostic=diagnostic)
            observe("final_layout", result, "FINAL_REPLAY")
            return AdaptedExecution(scope=scope, payload=payload, residuals=tuple(residuals),
                                    beam_outcome=outcome, observer_error_type=observer_error)
        except Exception as error:
            reason = ("CANCELLED" if isinstance(error, ExecutionInterrupted) else
                      "TIME_BUDGET_EXCEEDED" if isinstance(error, TimeBudgetExceeded) else
                      "MEMORY_BUDGET_EXCEEDED" if isinstance(error, MemoryError) else "EXECUTION_FAILED")
            return AdaptedExecution(scope=scope, payload=ExecutionPayloadV2(method=self.method, result=None,
                diagnostic=ExecutionDiagnostic(origin="SUPERVISOR", termination_reason=reason, statistics={})),
                beam_outcome=outcome, observer_error_type=observer_error, error_type=type(error).__name__)
