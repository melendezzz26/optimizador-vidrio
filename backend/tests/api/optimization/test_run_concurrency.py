"""TA-037 T03: admisión, liberación y tiempo máximo por HTTP real -> PostgreSQL (CA-08 a CA-10)."""
import time
from functools import partial

import pytest
from sqlalchemy import func, select

from app.models import MovimientoInventario, Optimizacion, Pedido, Plancha
from app.modules.optimization.presentation import run_routes
from app.modules.optimization.presentation.run_schemas import ErrorResponseV1, RunResponseV1
from app.modules.optimization.presentation.run_stream import LiveRunStream
from tests.api.optimization.test_runs_api import BASE, parse, run_api  # noqa: F401
from tests.integration.optimization.test_runs import prepared  # noqa: F401


def wait_until_free(admission, seconds=5):
    deadline = time.monotonic() + seconds
    while admission.active() and time.monotonic() < deadline:
        time.sleep(0.05)
    return admission.active()


def assert_busy(response, name, maximum, actual):
    assert response.status_code == 503, response.text
    assert response.headers["retry-after"] == "15"
    assert "location" not in response.headers
    detail = ErrorResponseV1.model_validate(response.json()).detail
    assert detail.code == "OPTIMIZER_BUSY"
    assert (detail.limit.name, detail.limit.maximum, detail.limit.actual) == (name, maximum, actual)
    return detail


def test_completed_run_frees_its_slot(run_api, run_admission):
    client, ids, headers, *_ = run_api
    assert parse(client.post(BASE, json={"order_ids": ids}, headers=headers))[-1]["event"] == "optimization_completed"
    assert wait_until_free(run_admission) == 0


def test_third_concurrent_run_gets_503_without_side_effects_and_is_admitted_later(
        run_api, run_admission, session_factory):
    client, ids, headers, *_ = run_api
    others = [run_admission.acquire(900001), run_admission.acquire(900002)]  # dos cálculos en curso
    assert_busy(client.post(BASE, json={"order_ids": ids}, headers=headers), "active_runs", 2, 2)
    with session_factory() as s:
        assert [s.get(Pedido, i).estado for i in ids] == ["PENDIENTE"] * 2
        assert s.scalar(select(func.count()).select_from(Optimizacion)) == 0
    others[0].release()
    assert parse(client.post(BASE, json={"order_ids": ids}, headers=headers))[-1]["event"] == "optimization_completed"
    others[1].release()
    assert wait_until_free(run_admission) == 0


def test_same_user_cannot_start_a_second_run(run_api, run_admission, prepared):
    client, ids, headers, *_ = run_api
    actor = prepared[0]
    lease = run_admission.acquire(actor)
    detail = assert_busy(client.post(BASE, json={"order_ids": ids}, headers=headers), "active_runs_per_user", 1, 1)
    assert detail.message.startswith("Ya tienes un cálculo en curso")
    lease.release()


@pytest.mark.parametrize("reject", ["load_limit", "not_found"])
def test_a_rejected_request_frees_its_slot(run_api, run_admission, reject):
    client, ids, headers, *_ = run_api
    body = {"order_ids": list(range(1, 22))} if reject == "load_limit" else {"order_ids": [999999]}
    assert client.post(BASE, json=body, headers=headers).status_code in (404, 422)
    assert run_admission.active() == 0


def test_a_failed_calculation_frees_its_slot(run_api, run_admission, monkeypatch):
    from app.modules.optimization.domain.first_fit import FirstFitOptimizer
    client, ids, headers, *_ = run_api
    monkeypatch.setattr(FirstFitOptimizer, "optimize", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    events = parse(client.post(BASE, json={"order_ids": ids}, headers=headers))
    assert events[-1]["data"]["code"] == "CALCULATION_FAILED"
    assert wait_until_free(run_admission) == 0


def test_client_disconnect_frees_the_slot_when_the_worker_stops(run_api, run_admission):
    client, ids, headers, *_ = run_api
    with client.stream("POST", BASE, json={"order_ids": ids}, headers=headers) as response:
        assert response.status_code == 201
        next(response.iter_lines())  # solo optimization_started; luego se corta la conexión
    assert wait_until_free(run_admission) == 0


def test_time_budget_stops_the_run_as_failed_and_frees_the_slot(run_api, run_admission, session_factory, monkeypatch):
    client, ids, headers, *_ = run_api
    monkeypatch.setattr(run_routes, "LiveRunStream", partial(LiveRunStream, time_budget_s=-1))
    response = client.post(BASE, json={"order_ids": ids}, headers=headers)
    events = parse(response)
    failed = events[-1]
    assert failed["event"] == "optimization_failed"
    assert failed["data"]["code"] == "TIME_BUDGET_EXCEEDED"
    assert failed["data"]["message"].startswith("El cálculo superó el tiempo máximo")
    canonical = RunResponseV1.model_validate(client.get(response.headers["location"], headers=headers).json())
    assert canonical.estado.value == "FALLIDA" and not canonical.confirmable
    with session_factory() as s:
        assert s.get(Plancha, 5).cantidad == 2  # nada se consumió
        assert s.scalar(select(func.count()).select_from(MovimientoInventario)) == 0
    assert wait_until_free(run_admission) == 0


def test_normal_run_is_not_affected_by_the_time_budget(run_api):
    client, ids, headers, *_ = run_api
    events = parse(client.post(BASE, json={"order_ids": ids}, headers=headers))
    assert events[-1]["event"] == "optimization_completed" and events[-1]["data"]["estado"] == "COMPLETADA"


def test_confirmation_is_not_subject_to_admission(run_api, run_admission):
    client, ids, headers, *_ = run_api
    response = client.post(BASE, json={"order_ids": ids}, headers=headers)
    parse(response)
    wait_until_free(run_admission)
    others = [run_admission.acquire(900001), run_admission.acquire(900002)]  # optimizador lleno
    confirm = client.post(response.headers["location"] + "/confirm", headers=headers)
    assert confirm.status_code == 200, confirm.text
    for lease in others:
        lease.release()