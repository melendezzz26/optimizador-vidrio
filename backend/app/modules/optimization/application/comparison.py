"""TA-021: sequential, read-only comparison of supplied optimizer factories.

Preparation, stock reads and capture of residual limits happen once at the caller.
This service does not enter the durable /runs lifecycle or select a winner.
"""
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from decimal import Decimal
from time import perf_counter_ns
from typing import Any

from ..domain.best_fit import BestFitOptimizer
from ..domain.first_fit import FirstFitOptimizer
from ..domain.metrics import ResidualRectangle, calculate_metrics
from ..domain.problem import OptimizationProblem, OptimizationResult, decimal_value
from ..domain.worst_fit import WorstFitOptimizer


DEFAULT_METHODS = (("FF", FirstFitOptimizer), ("BF", BestFitOptimizer), ("WF", WorstFitOptimizer))


@dataclass(frozen=True, kw_only=True)
class MethodComparisonResult:
    method: str
    result: OptimizationResult
    residuals: tuple[ResidualRectangle, ...]


class ComparisonFailed(RuntimeError):
    """A technical failure, with method/stage and the original exception as cause."""
    def __init__(self, method: str, stage: str):
        self.method, self.stage = method, stage
        super().__init__(f"Comparison failed for {method} during {stage}.")


def _available_methods(method_factories):
    try:
        entries = tuple(method_factories)
    except TypeError as error:
        raise ValueError("Methods must be a collection of (code, factory) pairs.") from error
    if not entries:
        raise ValueError("Comparison requires at least one available method.")
    seen = set()
    # Validate the entire collection before initializing or executing any method.
    for entry in entries:
        if not isinstance(entry, (tuple, list)) or len(entry) != 2:
            raise ValueError("Each method must be a (code, factory) pair.")
        method, factory = entry
        if not isinstance(method, str) or not method or method != method.strip():
            raise ValueError("Each method requires an unambiguous nonempty code.")
        if method in seen:
            raise ValueError(f"Duplicate comparison method: {method}.")
        seen.add(method)
        if not callable(factory):
            raise ValueError(f"Comparison method is unavailable: {method}.")

    optimizers = []
    for method, factory in entries:
        try:
            optimizer = factory()
        except Exception as error:
            raise ComparisonFailed(method, "initialization") from error
        if not callable(getattr(optimizer, "optimize", None)):
            raise ValueError(f"Comparison method has no available optimizer: {method}.")
        optimizers.append((method, optimizer))
    return optimizers


def _identified_result(method, result):
    if not isinstance(result, OptimizationResult):
        raise TypeError("An optimizer must return OptimizationResult.")
    if result.method != method:
        raise ValueError(f"Requested {method}, but the result identifies {result.method}.")


def compare_methods(
    problem: OptimizationProblem,
    method_factories: Iterable[tuple[str, Callable[[], Any]]] = DEFAULT_METHODS,
    *,
    minimum_width_mm: Decimal | int,
    minimum_height_mm: Decimal | int,
    clock: Callable[[], int] = perf_counter_ns,
) -> tuple[MethodComparisonResult, ...]:
    """Run N available methods over one immutable logical input, in request order.

    Factories create optimizers per invocation. Each optimizer owns its execution
    state; no layout or mutable raster cache is passed between methods. Codes are
    supplied with their factories, so extensions do not require a new registry.
    Invalid/unavailable entries fail before any optimize call. Partial/no-fit
    results remain valid; a technical failure never returns a truncated comparison.
    """
    if not isinstance(problem, OptimizationProblem):
        raise ValueError("Comparison requires a prepared OptimizationProblem.")
    width = decimal_value(minimum_width_mm, "minimum_width_mm")
    height = decimal_value(minimum_height_mm, "minimum_height_mm")
    if not callable(clock):
        raise ValueError("Comparison clock must be callable.")
    optimizers = _available_methods(method_factories)
    compared = []
    for method, optimizer in optimizers:
        stage = "optimization"
        try:
            started = clock()
            result = optimizer.optimize(problem)
            stage = "result contract"
            _identified_result(method, result)
            stage = "metrics"
            result, residuals = calculate_metrics(result, width, height)
            stage = "result contract"
            _identified_result(method, result)
            duration = max(0, (clock() - started) // 1_000_000)
            result = replace(result, computation_time_ms=duration)
            compared.append(MethodComparisonResult(
                method=method, result=result, residuals=tuple(residuals),
            ))
        except Exception as error:
            raise ComparisonFailed(method, stage) from error
    return tuple(compared)
