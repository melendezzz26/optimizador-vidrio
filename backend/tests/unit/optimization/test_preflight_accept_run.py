from unittest.mock import patch
from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from app.modules.optimization.application.errors import RunError
from app.modules.optimization.application.runs import AcceptRun
from app.modules.optimization.application.calculation import CalculateRun
from app.modules.optimization.application.dto import OptimizationRun, RunStatus
from app.modules.optimization.application.preparation import prepare_persisted_problem
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.problem import OptimizationResult
from tests.unit.optimization.test_accept_run_load_limits import CONFIG, unit_of_work
from tests.unit.optimization.test_first_fit import stock
from tests.unit.optimization.test_load_budget import row


class Provider:
    def __init__(self, candidates):
        self.candidates = candidates

    def count_compatible(self, key):
        return len(self.list_compatible(key))

    def list_compatible(self, key):
        return tuple(item for item in self.candidates if item.material_key == key)


def test_failure_does_not_create_or_invoke_optimizer():
    uow = unit_of_work([row()])
    with patch.object(FirstFitOptimizer, "optimize") as optimize, pytest.raises(RunError) as error:
        AcceptRun(lambda: uow, Provider([])).execute([1], 1)
    assert error.value.details["preflight_errors"] == [{"code": "NO_COMPATIBLE_STOCK", "piece_id": 1}]
    uow.runs.create.assert_not_called()
    uow.orders.transition.assert_not_called()
    optimize.assert_not_called()


def test_pass_creates_same_prepared_problem():
    rows = [row()]
    uow = unit_of_work(rows)
    AcceptRun(lambda: uow, Provider([stock(width=10, height=10)])).execute([1], 1)
    assert uow.runs.create.call_args.args[0] == prepare_persisted_problem((1,), rows, CONFIG)
    uow.orders.transition.assert_called_once()


def test_pass_reaches_optimizer_once_with_unchanged_result():
    rows = [row()]
    uow, provider = unit_of_work(rows), Provider([stock(width=10, height=10)])
    AcceptRun(lambda: uow, provider).execute([1], 1)
    accepted = uow.runs.create.call_args.args[0]
    run = OptimizationRun(optimization_id=1, status=RunStatus.RUNNING,
                          result=OptimizationResult(problem=accepted, placements=()))
    runs = SimpleNamespace(get=lambda _: run, residual_limits=lambda _: (1, 1),
                           save_result=lambda _, result, residuals: result)
    calculator = CalculateRun(lambda: nullcontext(SimpleNamespace(runs=runs)), provider)
    original = FirstFitOptimizer.optimize
    calls = []
    def spy(self, problem, *args, **kwargs):
        calls.append(problem)
        return original(self, problem, *args, **kwargs)
    with patch.object(FirstFitOptimizer, "optimize", spy):
        result = calculator.execute(1)
    assert len(calls) == 1
    expected = original(FirstFitOptimizer(), calls[0])
    assert result.placements == expected.placements


def test_empty_order_is_structured_and_never_created():
    uow = unit_of_work([])
    with pytest.raises(RunError) as error:
        AcceptRun(lambda: uow, Provider([])).execute([1], 1)
    assert error.value.details["preflight_errors"] == [{"code": "EMPTY_ORDER"}]
    uow.runs.create.assert_not_called()
