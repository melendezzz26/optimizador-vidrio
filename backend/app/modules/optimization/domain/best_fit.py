"""Best Fit selects the least remaining raster capacity within each source tier."""
from collections.abc import Iterable
from typing import Callable, Literal

from .packing import FeasibleCandidate, FirstFitEvent, pack
from .problem import OptimizationProblem, OptimizationResult


class BestFitSelector:
    def select(self, candidates: Iterable[FeasibleCandidate]) -> FeasibleCandidate | None:
        # Same capacity and stable ranks as WF; retain only the current winner.
        return min(candidates, key=lambda candidate: (
            candidate.remaining_free_cells_after_placement,
            candidate.stock_rank, candidate.orientation_rank, candidate.row, candidate.column,
        ), default=None)


class BestFitResult(OptimizationResult):
    @property
    def method(self) -> Literal["BF"]:
        return "BF"


class BestFitOptimizer:
    def optimize(self, problem: OptimizationProblem,
                 on_event: Callable[[FirstFitEvent], None] | None = None, *, checkpoint=None) -> OptimizationResult:
        result = pack(problem, on_event, select=BestFitSelector().select, checkpoint=checkpoint)
        return BestFitResult(problem=result.problem, placements=result.placements)
