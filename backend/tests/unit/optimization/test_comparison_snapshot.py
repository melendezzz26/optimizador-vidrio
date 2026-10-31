"""Identidad multimétodo, transporte spawn y regresión del formato FF V1.

Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
"""
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import json

import pytest

from app.modules.optimization.domain.best_fit import BestFitOptimizer
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.worst_fit import WorstFitOptimizer
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.infrastructure import comparison_snapshot as codec
from app.modules.optimization.infrastructure.run_snapshot import encode as encode_v1, decode as decode_v1
from tests.unit.optimization.test_first_fit import problem, piece, stock, config


def example():
    return problem([piece(quantity=2)], [stock(width=12, height=8)],
                   config(angular_step_deg=Decimal(5)))


@pytest.mark.parametrize("optimizer", [FirstFitOptimizer, BestFitOptimizer, WorstFitOptimizer])
def test_round_trip_preserves_real_method_geometry_metrics_and_time(optimizer):
    result, residuals = calculate_metrics(optimizer().optimize(example()), 1, 1)
    result = replace(result, computation_time_ms=17)
    snapshot = codec.encode_result(result)
    before = deepcopy(snapshot)
    restored = codec.decode_result(json.loads(json.dumps(snapshot)), expected_method=result.method)
    assert restored == result and type(restored) is type(result)
    assert restored.method == result.method and restored.computation_time_ms == 17
    assert calculate_metrics(restored, 1, 1)[1] == residuals
    assert snapshot == before
    assert snapshot["snapshot_version"] == 2 and snapshot["method"] == result.method


@pytest.mark.parametrize("optimizer", [FirstFitOptimizer, BestFitOptimizer, WorstFitOptimizer])
def test_partial_results_keep_identity_and_missing_units(optimizer):
    result = optimizer().optimize(problem([piece(width=20, height=20)], [stock(width=4, height=4)]))
    restored = codec.decode_result(codec.encode_result(result))
    assert restored.method == result.method and not restored.complete
    assert restored.placements == () and restored.unplaced_units == result.unplaced_units


def test_input_transport_is_json_only_detached_immutable_and_complete():
    original = example()
    payload = codec.encode_problem(original)
    restored = codec.decode_problem(payload)
    assert restored == original and restored is not original
    assert restored.units[0].geometry is not original.units[0].geometry
    assert codec.problem_fingerprint(original) == codec.problem_fingerprint(restored)
    payload["problem"]["groups"][0]["units"][0]["geometry"]["width_mm"] = 999
    assert restored.units[0].geometry["width_mm"] != 999
    with pytest.raises(TypeError):
        restored.units[0].geometry["width_mm"] = 1
    assert isinstance(codec.encode_problem(original)["problem"]["config"]["resolution_mm"], str)


def test_fingerprint_changes_with_configuration_quantities_and_stock_order():
    original = example()
    changed_config = replace(original, config=replace(original.config, separation_mm=Decimal(2)))
    changed_quantity = problem([piece(quantity=3)], [stock(width=12, height=8)], config(angular_step_deg=Decimal(5)))
    different_stock = problem([piece(quantity=2)], [stock(width=13, height=8)], config(angular_step_deg=Decimal(5)))
    hashes = {codec.problem_fingerprint(p) for p in (original, changed_config, changed_quantity, different_stock)}
    assert len(hashes) == 4
    ranked = problem(candidates=[stock(1), stock(2)])
    reversed_rank = replace(ranked, groups=(replace(ranked.groups[0],
                            stock_candidates=tuple(reversed(ranked.groups[0].stock_candidates))),))
    assert codec.problem_fingerprint(ranked) != codec.problem_fingerprint(reversed_rank)


def test_historical_ff_codec_and_snapshot_remain_unchanged():
    result = FirstFitOptimizer().optimize(example())
    old = encode_v1(result)
    assert old["snapshot_version"] == 1 and "method" not in old
    assert decode_v1(old) == codec.decode_result(old, expected_method="FF") == result
    for method in ("BF", "WF"):
        with pytest.raises(codec.ComparisonSnapshotError):
            codec.decode_result(old, expected_method=method)


def test_historical_envelope_cannot_claim_another_method():
    old = encode_v1(FirstFitOptimizer().optimize(example()))
    old["method"] = "BF"
    with pytest.raises(codec.ComparisonSnapshotError):
        codec.decode_result(old)


@pytest.mark.parametrize("mutation", [
    {"snapshot_version": True}, {"snapshot_version": 3}, {"snapshot_version": "2"},
    {"method": "AUTO"}, {"method": []}, {"result": None}, {"extra": "no"},
])
def test_bad_result_envelopes_are_rejected(mutation):
    value = codec.encode_result(BestFitOptimizer().optimize(example()))
    value.update(mutation)
    with pytest.raises(codec.ComparisonSnapshotError):
        codec.decode_result(value)


def test_result_cannot_be_reassigned_to_another_execution_method():
    value = codec.encode_result(WorstFitOptimizer().optimize(example()))
    with pytest.raises(codec.ComparisonSnapshotError):
        codec.decode_result(value, expected_method="BF")


@pytest.mark.parametrize("version", [False, 2, "1", None])
def test_unsupported_input_versions_are_rejected(version):
    value = codec.encode_problem(example()); value["input_version"] = version
    with pytest.raises(codec.ComparisonSnapshotError):
        codec.decode_problem(value)


def test_no_pickle_or_nonfinite_values_and_explicit_byte_limits():
    for value in ({"bad": float("nan")}, {"bad": float("inf")}, {"bad": object()}):
        with pytest.raises(codec.ComparisonSnapshotError):
            codec.canonical_json(value)
    assert codec.canonical_json("á", maximum_bytes=4) == '"á"'
    with pytest.raises(codec.ComparisonSnapshotError):
        codec.canonical_json("á", maximum_bytes=3)
    with pytest.raises(codec.ComparisonSnapshotError):
        codec.decode_problem({"input_version": 1, "problem": {}})


def test_decode_never_calls_an_optimizer(monkeypatch):
    encoded = codec.encode_result(BestFitOptimizer().optimize(example()))
    def forbidden(*args, **kwargs):
        pytest.fail("Decodificar no debe recalcular")
    for optimizer in (FirstFitOptimizer, BestFitOptimizer, WorstFitOptimizer):
        monkeypatch.setattr(optimizer, "optimize", forbidden)
    assert codec.decode_result(encoded).method == "BF"
