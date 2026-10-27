"""Worst Fit by exact post-placement free raster capacity, remnants first.

Only the canonical placement of each physical source is compared. No rotation,
geometry, inventory, metrics, HTTP or persistence policy is implemented here.
"""
from collections.abc import Iterable
from typing import Callable, Literal

from .packing import FeasibleCandidate, FirstFitEvent, pack
from .problem import OptimizationProblem, OptimizationResult


class WorstFitSelector:
    def select(self, candidates: Iterable[FeasibleCandidate]) -> FeasibleCandidate | None:
        # min consumes a lazy iterator and retains only the current best candidate.
        return min(candidates, key=lambda candidate: (
            -candidate.remaining_free_cells_after_placement,
            candidate.stock_rank, candidate.orientation_rank, candidate.row, candidate.column,
        ), default=None)


class WorstFitResult(OptimizationResult):
    """Domain result identity only; the current durable/HTTP contracts remain FF."""
    @property
    def method(self) -> Literal["WF"]:
        return "WF"


class WorstFitOptimizer:
    def optimize(self, problem: OptimizationProblem,
                 on_event: Callable[[FirstFitEvent], None] | None = None, *, checkpoint=None) -> OptimizationResult:
        result = pack(problem, on_event, select=WorstFitSelector().select, checkpoint=checkpoint)
        return WorstFitResult(problem=result.problem, placements=result.placements)
