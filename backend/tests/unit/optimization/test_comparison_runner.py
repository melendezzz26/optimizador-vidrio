"""Spawn real: arranque común, fidelidad, límites y ausencia de procesos huérfanos.

Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
"""
from dataclasses import replace
from decimal import Decimal
from functools import partial
import multiprocessing as mp
import os
import time

import pytest

from app.modules.optimization.application.comparison_limits import ComparisonBudget, MIB
from app.modules.optimization.application.errors import RunError
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.infrastructure import comparison_runner as runner
from app.modules.optimization.infrastructure.comparison_snapshot import decode_result, problem_fingerprint
from app.modules.optimization.infrastructure.comparison_transport import unpack_visual, pack_mask, unpack_mask
from app.modules.optimization.infrastructure.run_snapshot import json_value
from app.modules.optimization.domain.raster_mask import RasterMask
from tests.unit.optimization.test_experimental_cases import loader

CASES, load_problem, read_case = loader.CASES, loader.load_problem, loader.read_case


def synchronized_worker(*args, barrier):
    method = args[0]
    real = runner.ENGINES[method]()
    class ObservedOptimizer:
        def optimize(self, problem, on_event, *, checkpoint, on_visual):
            def observed(fact):
                if fact.kind == "preparation_started":
                    barrier.wait(timeout=10)
                on_visual(fact)
            return real.optimize(problem, on_event, checkpoint=checkpoint, on_visual=observed)
    runner.ENGINES[method] = ObservedOptimizer
    runner.calculation_worker(*args)


def crash_best_fit(*args):
    if args[0] == "BF":
        os._exit(7)
    runner.calculation_worker(*args)


def never_ready(*args):
    time.sleep(30)


def excessive_memory(*args):
    if args[0] == "BF":
        class MemoryOptimizer:
            def optimize(self, *args, **kwargs):
                return bytearray(512 * MIB)
        runner.ENGINES["BF"] = MemoryOptimizer
    runner.calculation_worker(*args)


def input_for(case_id):
    data = read_case(case_id)["residual_limits"]
    return load_problem(case_id), tuple(Decimal(str(v)) for v in data.values())


@pytest.fixture(autouse=True)
def no_leaked_children():
    before = {p.pid for p in mp.active_children()}
    yield
    assert {p.pid for p in mp.active_children()} == before


@pytest.mark.parametrize("case_id", CASES)
def test_three_real_engines_enter_together_and_match_direct_results(case_id):
    problem, minimums = input_for(case_id)
    original = problem_fingerprint(problem)
    barrier = mp.get_context("spawn").Barrier(3)
    service = runner.ComparisonProcessRunner(worker_target=partial(synchronized_worker, barrier=barrier))
    packets = list(service.events(problem, minimums))
    ready = [p for p in packets if p["kind"] == "ready"]
    assert len(ready) == 3 and len({p["payload"]["pid"] for p in ready}) == 3
    assert {p["payload"]["input_sha256"] for p in ready} == {original}
    assert max(packets.index(p) for p in ready) < min(i for i, p in enumerate(packets) if p["kind"] == "started")
    assert not [p for p in packets if p["kind"] == "failed"]
    results = [p for p in packets if p["kind"] == "result"]
    assert {p["method"] for p in results} == {"FF", "BF", "WF"}
    for packet in results:
        restored = decode_result(packet["payload"]["snapshot"], expected_method=packet["method"])
        direct, residuals = calculate_metrics(runner.ENGINES[packet["method"]]().optimize(problem), *minimums)
        assert replace(restored, computation_time_ms=None) == direct
        assert packet["payload"]["residuals"] == json_value(residuals)
        facts = [unpack_visual(p["payload"], problem) for p in packets if p["method"] == packet["method"] and p["kind"] == "visual"]
        kinds = [f.kind for f in facts]
        assert kinds.index("piece_ready") < kinds.index("ordering_ready") < kinds.index("source_selected")
        assert next(f for f in facts if f.kind == "ordering_ready").ordered_units == restored.problem.units
        for fact in facts:
            if fact.kind == "source_selected":
                actual = next(p for p in restored.placements if p.piece.identity == fact.unit.identity)
                assert fact.placement == actual
                assert fact.orientation.rotation_deg == actual.rotation_deg
                assert dict(fact.orientation.geometry) == dict(actual.geometry)
                assert fact.orientation.mask.occupied_cells > 0
    assert problem_fingerprint(problem) == original
    assert service.last_report["all_workers_stopped"]
    assert service.last_report["maximum_queued_packets_per_worker"] <= 1
    assert service.last_report["maximum_packet_bytes"] <= service.budget.packet_bytes


def test_crashed_worker_does_not_erase_the_other_two():
    packets = list(runner.ComparisonProcessRunner(worker_target=crash_best_fit).events(*input_for(CASES[0])))
    assert {p["method"] for p in packets if p["kind"] == "result"} == {"FF", "WF"}
    failed, = [p for p in packets if p["kind"] == "failed"]
    assert failed["method"] == "BF" and failed["payload"]["code"] == "WORKER_STOPPED"


def test_address_space_limit_rejects_worker_allocation_and_preserves_others():
    packets = list(runner.ComparisonProcessRunner(worker_target=excessive_memory).events(*input_for(CASES[0])))
    assert {p["method"] for p in packets if p["kind"] == "result"} == {"FF", "WF"}
    failed, = [p for p in packets if p["kind"] == "failed"]
    assert failed["method"] == "BF" and failed["payload"]["code"] == "MEMORY_BUDGET_EXCEEDED"


def test_unresponsive_startup_is_terminated_and_joined():
    budget = replace(ComparisonBudget(), startup_seconds=.15, global_seconds=3)
    began = time.monotonic()
    packets = list(runner.ComparisonProcessRunner(budget, worker_target=never_ready).events(*input_for(CASES[0])))
    assert time.monotonic() - began < 8
    assert len(packets) == 3 and all(p["kind"] == "failed" and p["payload"]["code"] == "PROCESS_START_FAILED" for p in packets)


def test_calculation_timeout_is_not_reported_as_no_fit():
    budget = replace(ComparisonBudget(), calculation_seconds=1e-9)
    packets = list(runner.ComparisonProcessRunner(budget).events(*input_for(CASES[0])))
    assert not any(p["kind"] == "result" for p in packets)
    assert len([p for p in packets if p["kind"] == "failed" and p["payload"]["code"] == "TIME_BUDGET_EXCEEDED"]) == 3


def test_closing_consumer_terminates_owned_workers():
    stream = runner.ComparisonProcessRunner().events(*input_for(CASES[0]))
    assert next(stream)["kind"] == "ready"
    stream.close()


def test_preflight_rejects_unavailable_memory_before_spawning(monkeypatch):
    monkeypatch.setattr(runner, "available_memory", lambda: 0)
    with pytest.raises(RunError) as error:
        list(runner.ComparisonProcessRunner().events(*input_for(CASES[0])))
    assert error.value.code == "RESOURCE_UNAVAILABLE"


@pytest.mark.parametrize("platform", ["win32", "darwin"])
def test_unsupported_platform_explains_safe_environment_before_resource_access(monkeypatch, platform):
    monkeypatch.setattr(runner.sys, "platform", platform)
    def unexpected_read(*args):
        pytest.fail("Unsupported platforms must be rejected before reading Linux resources")
    monkeypatch.setattr(runner, "resident_bytes", unexpected_read)
    with pytest.raises(RunError) as error:
        runner.ComparisonProcessRunner().preflight()
    assert error.value.code == "RESOURCE_UNAVAILABLE"
    assert "WSL2" in error.value.message and "RLIMIT_AS" in error.value.message
    assert isinstance(error.value.__cause__, ValueError)
    assert str(error.value.__cause__) == "Linux procfs required"


def test_global_deadline_terminates_workers_even_before_startup_deadline():
    budget = replace(ComparisonBudget(), startup_seconds=10, global_seconds=.15)
    service = runner.ComparisonProcessRunner(budget, worker_target=never_ready)
    packets = list(service.events(*input_for(CASES[0])))
    assert len(packets) == 3
    assert all(p["kind"] == "failed" and p["payload"]["code"] == "TIME_BUDGET_EXCEEDED" for p in packets)
    assert service.last_report["all_workers_stopped"]


def test_aggregate_memory_budget_stops_all_workers_and_joins_them():
    budget = replace(ComparisonBudget(), aggregate_rss_bytes=(
        runner.resident_bytes(os.getpid()) + ComparisonBudget().helper_reserve_bytes + MIB))
    service = runner.ComparisonProcessRunner(budget, worker_target=never_ready)
    packets = list(service.events(*input_for(CASES[0])))
    assert len(packets) == 3
    assert all(p["kind"] == "failed" and p["payload"]["code"] == "MEMORY_BUDGET_EXCEEDED" for p in packets)
    assert service.last_report["maximum_rss_sum_bytes"] > budget.aggregate_rss_bytes
    assert service.last_report["all_workers_stopped"]


def test_lossless_mask_transport_preserves_wide_rows_and_holes():
    mask = RasterMask(0.25, 200, (1 | (1 << 199), 0, (1 << 200) - 1))
    # Simula JSON: las tuplas de tramos se convierten en listas.
    import json
    assert unpack_mask(json.loads(json.dumps(pack_mask(mask)))) == mask
    with pytest.raises(ValueError):
        unpack_mask(dict(columns=4001, spans=[[]], resolution_mm="1"))
