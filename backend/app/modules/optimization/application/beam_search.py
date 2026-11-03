"""Application entry point for the independent M6 Beam Search simulation."""
from .preparation import prepare_persisted_problem
from .stock import with_compatible_stock
from ..domain.beam_search import BeamSearchLimits, BeamSearchOptimizer


def calculate_beam_search(order_ids, persisted_pieces, config, stock_provider,
                          on_event=None, *, limits=None, checkpoint=None):
    problem = prepare_persisted_problem(order_ids, persisted_pieces, config)
    problem = with_compatible_stock(problem, stock_provider)
    return BeamSearchOptimizer(limits).optimize(
        problem, on_event=on_event, checkpoint=checkpoint,
    )
