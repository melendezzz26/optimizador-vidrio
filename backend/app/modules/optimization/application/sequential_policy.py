"""TA-043/B04 resource policy. No admission, database or aggregate orchestration."""
from collections import deque
from dataclasses import dataclass, replace

from .comparison_catalog import METHODS_V2
from .comparison_limits import (
    ComparisonBudget, DEFAULT_COMPARISON_BUDGET, LARGE_COMPARISON_MIN_UNITS,
    MAX_LARGE_CALCULATION_SECONDS,
)


@dataclass(frozen=True)
class SequentialPolicy:
    budget: ComparisonBudget = DEFAULT_COMPARISON_BUDGET
    max_active_workers: int = 1
    methods: tuple[str, ...] = METHODS_V2
    memory_ceiling: ComparisonBudget = DEFAULT_COMPARISON_BUDGET
    large_calculation_seconds: int | None = None

    def __post_init__(self):
        if type(self.max_active_workers) is not int or self.max_active_workers != 1 or self.methods != METHODS_V2:
            raise ValueError("Initial v2 policy requires one worker and the frozen ordered six-method catalog")
        if not isinstance(self.budget, ComparisonBudget) or not isinstance(self.memory_ceiling, ComparisonBudget):
            raise ValueError('Comparison budgets must be typed')
        if self.large_calculation_seconds is not None and (
            type(self.large_calculation_seconds) is not int
            or not DEFAULT_COMPARISON_BUDGET.calculation_seconds < self.large_calculation_seconds
            <= MAX_LARGE_CALCULATION_SECONDS
        ):
            raise ValueError("Invalid large-order deadline")
        memory_names = {'supervisor_rss_bytes', 'worker_address_bytes', 'aggregate_rss_bytes'}
        if any(
            getattr(self.budget, name) > (getattr(self.memory_ceiling, name) if name in memory_names else value)
            for name, value in vars(DEFAULT_COMPARISON_BUDGET).items()
        ):
            raise ValueError("Cannot increase budgets without an explicit memory ceiling")

    def for_problem(self, problem):
        if self.large_calculation_seconds is None or len(problem.units) < LARGE_COMPARISON_MIN_UNITS:
            return self.budget
        seconds = self.large_calculation_seconds
        # Budget each engine's startup, calculation and bounded process cleanup.
        return replace(self.budget, calculation_seconds=seconds,
                       global_seconds=len(self.methods) * (self.budget.startup_seconds + seconds + 5))

    def expired(self, now, began, launched, engine_started, *, budget=None):
        budget = self.budget if budget is None else budget
        deadlines = [(began + budget.global_seconds, "GLOBAL_TIME_LIMIT")]
        deadlines.append((engine_started + budget.calculation_seconds, "TIME_BUDGET_EXCEEDED")
                         if engine_started else (launched + budget.startup_seconds, "PROCESS_START_FAILED"))
        reached = [(deadline, code) for deadline, code in deadlines if now >= deadline]
        return min(reached)[1] if reached else None


class ObservationRetention:
    """Byte-bounded internal observations across all six methods, never per-engine budgets.

    These raw IPC observations are not HTTP replay/mask sessions. B05/B06 must
    integrate the same global limits with their existing visual projection.
    """
    def __init__(self, budget=DEFAULT_COMPARISON_BUDGET):
        self.maximum = dict(visual=budget.retained_visual_bytes, event=budget.retained_event_bytes)
        self.records = {name: deque() for name in self.maximum}
        self.bytes = dict(visual=0, event=0)
        self.evicted = dict(visual=0, event=0)

    def append(self, category, scope, raw):
        if category not in self.maximum or not isinstance(raw, bytes):
            raise ValueError("Invalid observation retention input")
        if len(raw) > self.maximum[category]:
            self.evicted[category] += 1
            return False
        values = self.records[category]
        # Keep the existing event window count as well as its byte budget.
        while values and (self.bytes[category] + len(raw) > self.maximum[category] or len(values) >= 4096):
            _, previous = values.popleft()
            self.bytes[category] -= len(previous)
            self.evicted[category] += 1
        values.append((scope, raw))
        self.bytes[category] += len(raw)
        return True

    def get(self, category, scope):
        return tuple(raw for owner, raw in self.records[category] if owner == scope)
