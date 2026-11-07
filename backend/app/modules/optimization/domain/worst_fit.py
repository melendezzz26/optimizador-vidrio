"""Worst Fit by exact post-placement free raster capacity, remnants first.

Only the canonical placement of each physical source is compared. No rotation,
geometry, inventory, metrics, HTTP or persistence policy is implemented here.

SPEC-TA-019 v2 (observación del profesor, revisión del 04/11/2026): within the
permitted level, WF compares only sources ALREADY IN USE (with at least one
placed piece). A new source is opened only when the piece fits in none of them,
and then it is the unused source with the lowest upstream rank, as in FF.
"""
from collections.abc import Iterable
from typing import Callable, Literal

from .packing import FeasibleCandidate, FirstFitEvent, pack
from .problem import OptimizationProblem, OptimizationResult


def _in_use(candidate: FeasibleCandidate) -> bool:
    # A source enters the calculation's layouts only after its first placement,
    # so any occupied raster cell means "already used in this calculation".
    return any(candidate.layout.occupied)


def _tie_key(candidate: FeasibleCandidate) -> tuple[int, int, int, int]:
    return candidate.stock_rank, candidate.orientation_rank, candidate.row, candidate.column


class WorstFitSelector:
    def select(self, candidates: Iterable[FeasibleCandidate]) -> FeasibleCandidate | None:
        # One lazy pass that retains only two candidates: the best source in use
        # and the first unused one. Unused sources are never scored.
        best_in_use, best_key, first_unused = None, None, None
        for candidate in candidates:
            if _in_use(candidate):
                key = (-candidate.remaining_free_cells_after_placement, *_tie_key(candidate))
                if best_key is None or key < best_key:
                    best_in_use, best_key = candidate, key
            elif first_unused is None or _tie_key(candidate) < _tie_key(first_unused):
                first_unused = candidate
        return best_in_use if best_in_use is not None else first_unused


class WorstFitResult(OptimizationResult):
    """Domain result identity only; the current durable/HTTP contracts remain FF."""
    @property
    def method(self) -> Literal["WF"]:
        return "WF"


class WorstFitOptimizer:
    def optimize(self, problem: OptimizationProblem,
                 on_event: Callable[[FirstFitEvent], None] | None = None, *, checkpoint=None, on_visual=None) -> OptimizationResult:
        result = pack(problem, on_event, select=WorstFitSelector().select, checkpoint=checkpoint, on_visual=on_visual)
        return WorstFitResult(problem=result.problem, placements=result.placements)
