"""Best Residual Fit (M5) selects the source maximizing the largest free rectangular remnant.

Only the canonical placement of each physical source within the active tier is evaluated.
No rotation, geometry, inventory, metrics, HTTP or persistence policy is implemented here.

SPEC-TA-052 v2 (observación del profesor, revisión del 04/11/2026), same source
rule as WF v2: within the permitted level, M5 scores only sources ALREADY IN USE
(with at least one placed piece). A new source is opened only when the piece fits
in none of them, and then it is the unused source with the lowest upstream rank.
"""
from collections.abc import Iterable
from typing import Callable, Literal

from .metrics import largest_rectangle
from .packing import FeasibleCandidate, FirstFitEvent, pack
from .placement import LayoutQueryMemo
from .problem import OptimizationProblem, OptimizationResult


def _in_use(candidate: FeasibleCandidate) -> bool:
    # A source enters the calculation's layouts only after its first placement,
    # so any occupied raster cell means "already used in this calculation".
    return any(candidate.layout.occupied)


def _tie_key(candidate: FeasibleCandidate) -> tuple[int, int, int, int]:
    return candidate.stock_rank, candidate.orientation_rank, candidate.row, candidate.column


class BestResidualFitSelector:
    """NewGlass experimental adaptation of Best Residual Fit (BRF / M5).

    Among the sources already in use, evaluates candidate layouts post-placement and
    selects the source that maximizes the largest contiguous free rectangular residual
    (retazo útil). In case of ties, minimizes non-recoverable fragmented waste, then
    breaks ties using the standard deterministic pipeline (stock_rank, orientation_rank,
    row, column). If no source in use is feasible, opens the unused source with the
    lowest (stock_rank, orientation_rank, row, column), without scoring it.
    """

    def __init__(self, min_width_cells: int = 1, min_height_cells: int = 1):
        self.min_width_cells = min_width_cells
        self.min_height_cells = min_height_cells
        self._scores = LayoutQueryMemo()

    def _score(self, candidate: FeasibleCandidate):
        score = self._scores.get(candidate.layout, candidate.orientation.mask,
                                 lambda: self._residual_score(candidate),
                                 parameters=(candidate.row, candidate.column,
                                             self.min_width_cells, self.min_height_cells))
        return (*score, *_tie_key(candidate))

    @staticmethod
    def _scan(layout):
        free_rows = tuple(
            usable & ~blocked
            for usable, blocked in zip(layout.usable, layout.blocked)
        )
        return largest_rectangle(free_rows, layout.material.columns)

    def _largest_after(self, candidate):
        before, after = candidate.layout, candidate.layout_after
        rectangle = self._scores.get(before, before, lambda: self._scan(before))
        if rectangle is None:
            return None
        row, column, width, height = rectangle
        span = ((1 << width) - 1) << column
        # Placement can only remove free cells. If the previous winner
        # survives, no new rectangle or better tie can have appeared.
        if not any(bits & span for bits in after.blocked[row:row + height]):
            return rectangle
        return self._scan(after)

    def _residual_score(self, candidate):
        layout = candidate.layout_after
        rectangle = self._scores.get(layout, layout, lambda: self._largest_after(candidate))
        if (
            rectangle is not None
            and rectangle[2] >= self.min_width_cells
            and rectangle[3] >= self.min_height_cells
        ):
            remnant_cells = rectangle[2] * rectangle[3]
        else:
            remnant_cells = 0
        fragmented_cells = candidate.remaining_free_cells_after_placement - remnant_cells
        return -remnant_cells, fragmented_cells

    def select(self, candidates: Iterable[FeasibleCandidate]) -> FeasibleCandidate | None:
        # One lazy pass that retains only two candidates: the best source in use
        # and the first unused one. Unused sources are never scored.
        best_in_use, best_key, first_unused = None, None, None
        for candidate in candidates:
            if _in_use(candidate):
                if best_in_use is None:
                    best_in_use = candidate
                    continue
                # A score cannot affect selection when there is one feasible
                # source in use. Compute it only once a second one competes.
                if best_key is None:
                    best_key = self._score(best_in_use)
                key = self._score(candidate)
                if key < best_key:
                    best_in_use, best_key = candidate, key
            elif first_unused is None or _tie_key(candidate) < _tie_key(first_unused):
                first_unused = candidate
        return best_in_use if best_in_use is not None else first_unused


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
