"""Best Residual Fit (M5) selects the source maximizing the largest free rectangular remnant.

Only the canonical placement of each physical source within the active tier is evaluated.
No rotation, geometry, inventory, metrics, HTTP or persistence policy is implemented here.
"""
from collections.abc import Iterable
from typing import Callable, Literal

from .metrics import largest_rectangle
from .packing import FeasibleCandidate, FirstFitEvent, pack
from .problem import OptimizationProblem, OptimizationResult


class BestResidualFitSelector:
    """NewGlass experimental adaptation of Best Residual Fit (BRF / M5).

    Evaluates candidate layouts post-placement and selects the source that maximizes
    the largest contiguous free rectangular residual (retazo útil). In case of ties,
    minimizes non-recoverable fragmented waste, then breaks ties using the standard
    deterministic pipeline (stock_rank, orientation_rank, row, column).
    """

    def __init__(self, min_width_cells: int = 1, min_height_cells: int = 1):
        self.min_width_cells = min_width_cells
        self.min_height_cells = min_height_cells

    def select(self, candidates: Iterable[FeasibleCandidate]) -> FeasibleCandidate | None:
        def score(candidate: FeasibleCandidate):
            layout = candidate.layout_after
            free_rows = tuple(
                usable & ~blocked
                for usable, blocked in zip(layout.usable, layout.blocked)
            )
            rectangle = largest_rectangle(free_rows, layout.material.columns)
            if (
                rectangle is not None
                and rectangle[2] >= self.min_width_cells
                and rectangle[3] >= self.min_height_cells
            ):
                remnant_cells = rectangle[2] * rectangle[3]
            else:
                remnant_cells = 0
            fragmented_cells = candidate.remaining_free_cells_after_placement - remnant_cells
            return (
                -remnant_cells,
                fragmented_cells,
                candidate.stock_rank,
                candidate.orientation_rank,
                candidate.row,
                candidate.column,
            )

        return min(candidates, key=score, default=None)


class BestResidualFitResult(OptimizationResult):
    """Domain result identity for M5."""
    @property
    def method(self) -> Literal["M5"]:
        return "M5"


class BestResidualFitOptimizer:
    """Optimizer applying M5 Best Residual Fit selection over the shared engine."""

    def __init__(self, min_width_cells: int = 1, min_height_cells: int = 1):
        self.selector = BestResidualFitSelector(min_width_cells, min_height_cells)

    def optimize(
        self,
        problem: OptimizationProblem,
        on_event: Callable[[FirstFitEvent], None] | None = None,
        *,
        checkpoint=None,
        on_visual=None,
    ) -> OptimizationResult:
        result = pack(
            problem,
            on_event,
            select=self.selector.select,
            checkpoint=checkpoint,
            on_visual=on_visual,
        )
        return BestResidualFitResult(problem=result.problem, placements=result.placements)
