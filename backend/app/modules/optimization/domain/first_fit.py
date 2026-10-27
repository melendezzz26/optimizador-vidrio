"""Pure First Fit: source -> orientation -> row -> column, first valid wins."""
from typing import Callable

# Keep the existing event/helper imports compatible, including metrics' factory.
from .packing import FirstFitEvent, _coordinate, _distance_cells, _empty_layout, pack
from .problem import OptimizationProblem, OptimizationResult


class FirstFitOptimizer:
    def optimize(self, problem: OptimizationProblem,
                 on_event: Callable[[FirstFitEvent], None] | None = None, *, checkpoint=None, on_visual=None) -> OptimizationResult:
        return pack(problem, on_event, checkpoint=checkpoint, on_visual=on_visual)
