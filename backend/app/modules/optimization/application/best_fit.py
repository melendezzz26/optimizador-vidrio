"""Read-only Best Fit simulation over the existing snapshots and stock port."""
from .preparation import prepare_persisted_problem
from .stock import with_compatible_stock
from ..domain.best_fit import BestFitOptimizer


def calculate_best_fit(order_ids, persisted_pieces, config, stock_provider, on_event=None):
    problem = prepare_persisted_problem(order_ids, persisted_pieces, config)
    problem = with_compatible_stock(problem, stock_provider)
    return BestFitOptimizer().optimize(problem, on_event=on_event)
