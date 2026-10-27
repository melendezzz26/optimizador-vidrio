"""TA-037 T02: AcceptRun rechaza antes de expandir y sin escribir (CA-02, CA-03, CA-06, CA-07)."""
from unittest.mock import MagicMock

import pytest

from app.modules.optimization.application import runs
from app.modules.optimization.application.errors import RunError
from app.modules.optimization.application.preparation import prepare_persisted_problem
from app.modules.optimization.application.runs import AcceptRun
from app.modules.optimization.domain.problem import OptimizationConfig
from tests.unit.optimization.test_load_budget import polygon, row

CONFIG = OptimizationConfig(resolution_mm=1, margin_mm=0, separation_mm=0)


class Counter:
    def __init__(self, units):
        self.units, self.calls = units, []

    def count_compatible(self, key):
        self.calls.append(key)
        return self.units


def unit_of_work(rows):
    uow = MagicMock()
    uow.__enter__.return_value = uow
    uow.configuration.return_value = (1, CONFIG)
    uow.orders.lock_pending.return_value = rows
    return uow


@pytest.fixture
def no_expansion(monkeypatch):
    """Falla si AcceptRun llega a expandir cantidades tras un rechazo."""
    def forbidden(*args, **kwargs):
        pytest.fail("prepare_persisted_problem no debe ejecutarse cuando se excede el presupuesto.")
    monkeypatch.setattr(runs, "prepare_persisted_problem", forbidden)


def assert_nothing_written(uow):
    uow.runs.create.assert_not_called()
    uow.orders.transition.assert_not_called()


def test_l01_is_rejected_before_opening_the_transaction():
    uow = unit_of_work([row()])
    with pytest.raises(RunError) as error:
        AcceptRun(lambda: uow).execute(list(range(1, 22)), 1)
    assert error.value.code == "LOAD_LIMIT_EXCEEDED"
    uow.__enter__.assert_not_called()
    uow.orders.lock_pending.assert_not_called()


@pytest.mark.parametrize("rows,name", [
    ([row(quantity=151)], "units_per_run"),
    ([row(quantity=2147483647)], "units_per_run"),
    ([row(geometry=polygon(129))], "vertices_per_piece"),
    ([row(identifier=i + 1, width=1300, height=1000 + i) for i in range(3)], "raster_memory"),
])
def test_p3_rejections_never_expand_or_write(no_expansion, rows, name):
    uow, counter = unit_of_work(rows), Counter(1)
    with pytest.raises(RunError) as error:
        AcceptRun(lambda: uow, counter).execute([1], 1)
    assert error.value.code == "LOAD_LIMIT_EXCEEDED"
    assert error.value.details["limit"]["name"] == name
    assert counter.calls == []  # P3 falla antes de consultar stock
    assert_nothing_written(uow)


def test_p4_stock_rejection_never_expands_or_writes(no_expansion):
    uow, counter = unit_of_work([row(glass=7, thickness="6.00")]), Counter(51)
    with pytest.raises(RunError) as error:
        AcceptRun(lambda: uow, counter).execute([1], 1)
    limit = error.value.details["limit"]
    assert (limit["name"], limit["actual"], limit["scope"]["id_tipo_vidrio"]) == ("stock_units_per_material", 51, 7)
    assert_nothing_written(uow)


def test_exact_limits_are_accepted_with_the_same_problem_as_before():
    """RN-03: dentro del presupuesto, el problema preparado es idéntico al de antes de TA-037."""
    rows = [row(identifier=1, quantity=100), row(identifier=2, quantity=50, geometry=polygon(128))]
    uow, counter = unit_of_work(rows), Counter(50)
    AcceptRun(lambda: uow, counter).execute([1], 1)
    accepted = uow.runs.create.call_args.args[0]
    assert accepted == prepare_persisted_problem((1,), rows, CONFIG)
    assert len(accepted.units) == 150
    assert counter.calls == [(1, rows[0]["espesor_mm"])]
    uow.orders.transition.assert_called_once()


def test_two_large_distinct_shapes_are_still_accepted():
    rows = [row(identifier=i + 1, width=1300, height=1000 + i) for i in range(2)]
    uow = unit_of_work(rows)
    AcceptRun(lambda: uow, Counter(2)).execute([1], 1)
    uow.runs.create.assert_called_once()


def test_without_stock_counter_p4_is_skipped_for_direct_callers():
    uow = unit_of_work([row()])
    AcceptRun(lambda: uow).execute([1], 1)
    uow.runs.create.assert_called_once()


@pytest.mark.parametrize("bad", [
    dict(geometria=dict(type="RECTANGULO", width_mm=-2, height_mm=2)),
    dict(geometria=dict(type="RECTANGULO", width_mm=4001, height_mm=10)),
    dict(cantidad="2"),
])
def test_existing_invalid_input_response_is_unchanged(bad):
    uow = unit_of_work([{**row(), **bad}])
    with pytest.raises(RunError) as error:
        AcceptRun(lambda: uow, Counter(1)).execute([1], 1)
    assert error.value.code == "INVALID_INPUT"
    assert error.value.message == "Las piezas o parámetros exceden las condiciones válidas de cálculo."
    assert error.value.details is None
    assert_nothing_written(uow)