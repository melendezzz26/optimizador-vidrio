"""Vertical slice over existing persisted DTOs; no batch transaction or new API."""
from .preparation import prepare_persisted_problem
from .stock import with_compatible_stock
from ..domain.first_fit import FirstFitOptimizer


def calculate_first_fit(order_ids, persisted_pieces, config, stock_provider, on_event=None):
    problem = prepare_persisted_problem(order_ids, persisted_pieces, config)
    problem = with_compatible_stock(problem, stock_provider)
    return FirstFitOptimizer().optimize(problem, on_event=on_event)
