"""Run calculation outside database transactions; timer excludes event delivery."""
from dataclasses import replace
from time import perf_counter_ns

from .errors import RunError, ResultSaveFailed
from .stock import with_compatible_stock
from .dto import RunStatus
from ..domain.first_fit import FirstFitOptimizer
from ..domain.metrics import calculate_metrics


class CalculateRun:
    def __init__(self, unit_of_work, stock_provider, *, clock=perf_counter_ns):
        self.unit_of_work, self.stock_provider, self.clock = unit_of_work, stock_provider, clock

    def execute(self, optimization_id, on_event=None, *, checkpoint=None, on_visual=None):
        with self.unit_of_work() as uow:
            run = uow.runs.get(optimization_id)
            minimum_width, minimum_height = uow.runs.residual_limits(optimization_id)
        if run.status is not RunStatus.RUNNING:
            raise RunError("STATE_CONFLICT", "La corrida ya ha finalizado.")
        # Stock I/O and all DB sessions end before starting the computation clock.
        problem = with_compatible_stock(run.result.problem, self.stock_provider)
        paused = 0
        def timed(callback):
            def emit(event):
                nonlocal paused
                if callback is not None:
                    before = self.clock()
                    try:
                        callback(event)
                    finally:
                        paused += self.clock() - before
            return emit
        started = self.clock()
        visual = {'on_visual': timed(on_visual)} if on_visual is not None else {}
        result = FirstFitOptimizer().optimize(problem, on_event=timed(on_event), checkpoint=checkpoint, **visual)
        result, residuals = calculate_metrics(result, minimum_width, minimum_height)
        duration = max(0, (self.clock() - started - paused) // 1_000_000)
        result = replace(result, computation_time_ms=duration)
        try:
            with self.unit_of_work() as uow:
                return uow.runs.save_result(optimization_id, result, residuals)
        except Exception as exc:
            raise ResultSaveFailed("No se pudo guardar el resultado.") from exc
