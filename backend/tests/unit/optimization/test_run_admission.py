"""TA-037 T03: admisión acotada en proceso (L-10, L-11), sin base de datos (CA-08, CA-09)."""
from contextlib import nullcontext
from threading import Barrier, Event, Thread
from types import SimpleNamespace

import pytest

from app.modules.optimization.application.admission import OptimizerBusy
from app.modules.optimization.application.errors import RunError
from app.modules.optimization.infrastructure.in_process_admission import InProcessRunAdmission
from app.modules.optimization.presentation.comparison_supervision_v2 import ComparisonV2Coordinator
from app.modules.optimization.presentation.run_stream import LiveRunStream


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def busy(admission, user_id):
    with pytest.raises(OptimizerBusy) as error:
        admission.acquire(user_id)
    assert error.value.code == "OPTIMIZER_BUSY" and error.value.retry_after == 15
    return error.value.details["limit"]


def test_approved_values_are_two_per_process_and_one_per_user():
    admission = InProcessRunAdmission()
    assert (admission.max_active, admission.max_per_user) == (2, 1)


def test_l10_third_run_is_rejected_and_admitted_after_one_finishes():
    admission = InProcessRunAdmission()
    first, _ = admission.acquire(1), admission.acquire(2)
    assert busy(admission, 3) == dict(name="active_runs", maximum=2, actual=2, scope=None)
    first.release()
    admission.acquire(3)
    assert admission.active() == 2


def test_l11_same_user_cannot_hold_two_runs_even_with_free_capacity():
    admission = InProcessRunAdmission()
    admission.acquire(7)
    assert busy(admission, 7) == dict(name="active_runs_per_user", maximum=1, actual=1, scope=None)
    admission.acquire(8)  # otro usuario sí entra


def test_release_is_idempotent_and_frees_exactly_one_slot():
    admission = InProcessRunAdmission()
    lease = admission.acquire(1)
    admission.acquire(2)
    lease.release()
    lease.release()
    assert admission.active() == 1


@pytest.mark.parametrize("elapsed", [300, 301, 3600])
def test_unreleased_slots_keep_global_and_user_limits_after_long_delivery(elapsed):
    clock = FakeClock()
    admission = InProcessRunAdmission(clock=clock)
    first, second = admission.acquire(1), admission.acquire(2)
    clock.now = elapsed
    assert admission.active() == 2
    assert busy(admission, 3)["name"] == "active_runs"
    assert busy(admission, 1)["name"] == "active_runs_per_user"
    first.release()
    third = admission.acquire(3)
    assert admission.active() == 2
    second.release()
    third.release()
    assert admission.active() == 0


def test_no_slot_leaks_after_100_admission_and_rejection_cycles():
    admission = InProcessRunAdmission()
    for cycle in range(100):
        leases = [admission.acquire(cycle * 10 + 1), admission.acquire(cycle * 10 + 2)]
        busy(admission, cycle * 10 + 3)
        for lease in leases:
            lease.release()
    assert admission.active() == 0


def test_concurrent_requests_never_exceed_the_limit():
    admission, barrier, admitted, rejected = InProcessRunAdmission(), Barrier(20), [], []

    def request(user_id):
        barrier.wait(timeout=5)
        try:
            admitted.append(admission.acquire(user_id))
        except OptimizerBusy:
            rejected.append(user_id)

    threads = [Thread(target=request, args=(i,)) for i in range(1, 21)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)
    assert (len(admitted), len(rejected), admission.active()) == (2, 18, 2)


class Lease:
    def __init__(self):
        self.releases = 0

    def release(self):
        self.releases += 1


def test_a_stream_whose_worker_never_started_frees_its_slot():
    lease = Lease()
    stream = LiveRunStream(None, None, lease=lease)
    stream.release_if_idle()
    assert lease.releases == 1


def test_a_running_worker_keeps_its_slot_until_it_ends():
    lease = Lease()
    stream = LiveRunStream(None, None, lease=lease)
    stream.worker_started = True
    stream.release_if_idle()
    assert lease.releases == 0


def test_comparison_reserves_all_capacity_until_idempotent_release():
    admission = InProcessRunAdmission()
    lease = admission.acquire_comparison(1)
    busy(admission, 2)
    with pytest.raises(OptimizerBusy):
        admission.acquire_comparison(3)
    lease.release()
    admission.acquire(2)
    lease.release()
    assert admission.active() == 1


def test_legacy_and_comparison_requests_never_overlap():
    admission = InProcessRunAdmission()
    legacy = admission.acquire(1)
    with pytest.raises(OptimizerBusy):
        admission.acquire_comparison(2)
    legacy.release()
    comparison = admission.acquire_comparison(2)
    assert admission.active() == 1
    comparison.release()
    assert admission.active() == 0


@pytest.mark.parametrize("owner", ["local", "startup"])
def test_new_request_retries_safe_recovery_before_reserving_capacity(monkeypatch, owner):
    tx = SimpleNamespace(comparisons_v2=SimpleNamespace(find_by_key=lambda *_: None))
    admission = InProcessRunAdmission()
    lease = admission.acquire_comparison(1)
    coordinator = ComparisonV2Coordinator(lambda: nullcontext(tx), admission, authorize=lambda *_: None)
    if owner == "local":
        coordinator.job = SimpleNamespace(closed=Event(), thread=None)
        monkeypatch.setattr(coordinator, "_close", lambda job: False)
    else:
        coordinator.recovery_lease = lease
        monkeypatch.setattr(coordinator, "recover_pending", lambda: False)

    with pytest.raises(RunError) as blocked:
        coordinator.start([2], 1, "retry-recovery")
    assert blocked.value.code == "RECOVERY_BLOCKED"
    assert blocked.value.details == {"request_accepted": False}
    assert admission.active() == 1

    def recovered(*_):
        lease.release()
        if owner == "local":
            coordinator.job.closed.set()
        else:
            coordinator.recovery_lease = None
        return True

    def reached_preflight():
        assert admission.active() == 1  # The new request owns the reservation.
        raise RunError("RESOURCE_UNAVAILABLE", "Controlled preflight failure")

    monkeypatch.setattr(coordinator, "_close" if owner == "local" else "recover_pending", recovered)
    if coordinator.job is not None:
        coordinator.job.lease = lease
    coordinator.runner_factory = lambda: SimpleNamespace(preflight=reached_preflight)
    with pytest.raises(RunError) as resumed:
        coordinator.start([2], 1, "retry-recovery")
    assert resumed.value.code == "RESOURCE_UNAVAILABLE"
    assert admission.active() == 0
