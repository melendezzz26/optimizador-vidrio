"""T-01: B01 catalog, schemas/codecs and shared backend/frontend wire examples."""
from copy import deepcopy
from dataclasses import replace
import json
from typing import get_args

import pytest
from pydantic import ValidationError

from app.modules.optimization.application.comparison_catalog import (
    CATALOG_V1, CATALOG_V2, METHODS_V2, MethodV2, validate_methods,
)
from app.modules.optimization.application.comparison_contracts import METHODS
from app.modules.optimization.application.comparison_v2_contracts import ComparisonInputV2, ExecutionDiagnostic, ExecutionPayloadV2
from app.modules.optimization.infrastructure import comparison_snapshot as old_codec
from app.modules.optimization.infrastructure.comparison_v2_snapshot import (
    encode_result_v3, decode_result_v3, decode_compatible_result,
    encode_comparison_input_v2, decode_comparison_input_v2,
)
from app.modules.optimization.infrastructure.run_snapshot import encode as encode_ff
from app.modules.optimization.presentation.comparison_schemas import ComparisonSummary, ExecutionResponse
from app.modules.optimization.presentation.comparison_v2_schemas import (
    ComparisonSummaryV2, ExecutionResponseV2, ComparisonEventV2,
    ComparisonSelectionV2, ComparisonReleaseV2, ComparisonConfirmationV2, ComparisonMaskPayloadV2,
    ComparisonMaskV2,
)
from app.modules.optimization.presentation.run_schemas import RunResponseV1
from tests.unit.optimization.comparison_v2_support import FIXTURE, example, calculated


@pytest.fixture
def wire():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_catalog_is_exact_ordered_immutable_and_identifies_real_engines(wire):
    assert METHODS_V2 == get_args(MethodV2) == ("FF", "BF", "WF", "HF", "M5", "M6-BS")
    assert tuple(m.code for m in CATALOG_V1) == METHODS == ("FF", "BF", "WF")
    assert [m.public() for m in CATALOG_V2] == wire["catalog"]
    assert len({m.optimizer_type for m in CATALOG_V2}) == 6
    for method in CATALOG_V2:
        assert method.result_type(problem=example(), placements=()).method == method.code
    assert CATALOG_V2[-1].optimizer_type().limits.width == CATALOG_V2[-1].beam_width == 2


@pytest.mark.parametrize("codes,profile", [([], "comparison-v2"), (["AUTO"], "comparison-v2"),
    (["BRF"], "comparison-v2"), (["BS-2"], "comparison-v2"), (["FF", "FF"], "comparison-v2"),
    (["HF"], "comparison-v1"), (["FF"], "comparison-v3"), ([True], "comparison-v2")])
def test_catalog_rejects_unknown_duplicate_alias_or_wrong_profile(codes, profile):
    with pytest.raises(ValueError):
        validate_methods(codes, profile=profile)


@pytest.mark.parametrize("definition", CATALOG_V2, ids=lambda m: m.code)
def test_real_results_round_trip_v3_without_widening_historical_codec(definition):
    payload, _ = calculated(definition, example())
    before = encode_result_v3(payload)
    restored = decode_result_v3(deepcopy(before), expected_method=definition.code)
    assert restored == payload and type(restored.result) is definition.result_type
    assert encode_result_v3(restored) == before
    with pytest.raises(old_codec.ComparisonSnapshotError):
        old_codec.decode_result(before)
    if definition.code not in METHODS:
        with pytest.raises(old_codec.ComparisonSnapshotError):
            old_codec.encode_result(payload.result)


@pytest.mark.parametrize("reason", ["EXPANSION_LIMIT", "GEOMETRY_PROBE_LIMIT", "STATE_MEMORY_LIMIT", "TIME_LIMIT"])
def test_partial_result_and_resource_reasons_survive_codec(reason):
    payload, _ = calculated(CATALOG_V2[-1], example(), partial=True)
    payload = replace(payload, diagnostic=ExecutionDiagnostic(origin="ENGINE", termination_reason=reason, statistics={"expansions": 1}))
    restored = decode_result_v3(encode_result_v3(payload))
    assert not restored.result.complete and restored.diagnostic.termination_reason == reason


def test_compatible_reader_does_not_invent_historical_diagnostics_or_methods():
    for definition in CATALOG_V1:
        payload, _ = calculated(definition, example())
        old = old_codec.encode_result(payload.result)
        decoded = decode_compatible_result(old, expected_method=definition.code)
        assert decoded.result == payload.result and decoded.diagnostic is None
        if definition.code == "FF":
            assert decode_compatible_result(encode_ff(payload.result)).result == payload.result
        with pytest.raises(old_codec.ComparisonSnapshotError):
            decode_compatible_result(old, expected_method="HF")


@pytest.mark.parametrize("mutation", [{"snapshot_version": True}, {"snapshot_version": "3"},
    {"method": "AUTO"}, {"profile": "comparison-v1"}, {"diagnostic": None}, {"extra": 1}])
def test_bad_v3_envelopes_rejected(mutation):
    payload, _ = calculated(CATALOG_V2[0], example())
    snapshot = encode_result_v3(payload)
    snapshot.update(mutation)
    with pytest.raises(old_codec.ComparisonSnapshotError):
        decode_result_v3(snapshot)


def test_codec_rejects_cross_method_and_never_runs_a_motor(monkeypatch):
    payload, _ = calculated(CATALOG_V2[-1], example())
    snapshot = encode_result_v3(payload)
    with pytest.raises(old_codec.ComparisonSnapshotError):
        decode_result_v3(snapshot, expected_method="HF")
    def forbidden(*args, **kwargs):
        pytest.fail("Decoding cannot execute heuristics")
    for method in CATALOG_V2:
        monkeypatch.setattr(method.optimizer_type, "optimize", forbidden)
    monkeypatch.setattr(CATALOG_V2[-1].optimizer_type, "run", forbidden)
    assert decode_result_v3(snapshot).result == payload.result


def test_diagnostic_is_immutable_and_cannot_fabricate_a_success():
    counters = {"expansions": 1}
    diagnostic = ExecutionDiagnostic(origin="ENGINE", termination_reason="EXPANSION_LIMIT", statistics=counters)
    counters["expansions"] = 9
    assert diagnostic.statistics["expansions"] == 1
    with pytest.raises(TypeError):
        diagnostic.statistics["expansions"] = 2
    with pytest.raises(ValueError):
        ExecutionPayloadV2(method="M6-BS", result=None,
            diagnostic=ExecutionDiagnostic(origin="ENGINE", termination_reason="COMPLETED", statistics={}))


def test_shared_wire_examples_and_historical_rejection(wire):
    for key in ("accepted", "completed", "mixed"):
        assert ComparisonSummaryV2.model_validate(wire[key]).model_dump(mode="json") == wire[key]
        with pytest.raises(ValidationError):
            ComparisonSummary.model_validate(wire[key])
    for result in (*wire["results"].values(), wire["partial_result"], wire["failed_result"]):
        assert ExecutionResponseV2.model_validate(result).model_dump(mode="json") == result
        with pytest.raises(ValidationError):
            ExecutionResponse.model_validate(result)
    for event in wire["events"]:
        ComparisonEventV2.model_validate(event)
    assert [e["sequence"] for e in wire["events"]] == list(range(1, len(wire["events"]) + 1))
    for method in METHODS_V2:
        sequences = [e["execution_sequence"] for e in wire["events"] if e["method"] == method]
        assert sequences == list(range(1, len(sequences) + 1))
    with pytest.raises(ValidationError):
        RunResponseV1.model_validate(wire["results"]["4301"]["result"])


@pytest.mark.parametrize("mutation", ["method", "duplicate", "id", "early_selection", "early_stop", "outcome", "diagnostic"])
def test_inconsistent_comparison_identity_and_lifecycle_rejected(wire, mutation):
    data = deepcopy(wire["completed"])
    if mutation == "method": data["executions"][0]["method"] = "AUTO"
    if mutation == "duplicate": data["executions"][0]["method"] = "BF"
    if mutation == "id": data["executions"][0]["execution_id"] = data["executions"][1]["execution_id"]
    if mutation == "early_selection": data["selected_execution_id"] = 999
    if mutation == "early_stop": data["supervisor_stopped"] = False
    if mutation == "outcome": data["executions"][0]["outcome"] = "PARTIAL"
    if mutation == "diagnostic": data["executions"][0]["diagnostic"]["termination_reason"] = "TIME_LIMIT"
    with pytest.raises(ValidationError):
        ComparisonSummaryV2.model_validate(data)


def test_execution_order_does_not_define_identity(wire):
    data = deepcopy(wire["completed"])
    data["executions"].reverse()
    assert ComparisonSummaryV2.model_validate(data).executions[0].method == "M6-BS"


def test_partial_reason_and_execution_scope_cannot_be_reassigned(wire):
    data = deepcopy(wire["partial_result"])
    data["result"]["unplaced_units"][0]["reason"] = "NO_FIT"
    with pytest.raises(ValidationError):
        ExecutionResponseV2.model_validate(data)
    data = deepcopy(wire["results"]["4301"])
    data["execution"]["method"] = "BF"
    with pytest.raises(ValidationError):
        ExecutionResponseV2.model_validate(data)


def test_search_progress_is_provisional_and_never_a_definitive_placement(wire):
    event = deepcopy(wire["events"][1])
    event["data"]["placements"] = []
    with pytest.raises(ValidationError):
        ComparisonEventV2.model_validate(event)
    event = deepcopy(wire["events"][1]); event["presentation"] = "OBSERVED"
    with pytest.raises(ValidationError):
        ComparisonEventV2.model_validate(event)


def frozen_input(wire):
    return ComparisonInputV2(problem=example(), configuration_id=1, configuration_version=1,
        requested_pieces=wire["completed"]["requested_pieces"], minimum_width_mm=1, minimum_height_mm=1)


def test_frozen_input_envelope_has_independent_version_hash_and_immutable_metadata(wire):
    value = frozen_input(wire)
    encoded = encode_comparison_input_v2(value)
    assert encoded["comparison_snapshot_version"] == 2 and encoded["input"]["input_version"] == 1
    assert encoded["engine_parameters"] == {"M6-BS": {"width": 2}}
    assert decode_comparison_input_v2(encoded) == value
    with pytest.raises(TypeError):
        value.requested_pieces[0]["cantidad"] = 99


@pytest.mark.parametrize("mutation", ["version", "hash", "width", "methods", "configuration", "threshold"])
def test_inconsistent_frozen_input_rejected(wire, mutation):
    encoded = encode_comparison_input_v2(frozen_input(wire))
    if mutation == "version": encoded["comparison_snapshot_version"] = True
    if mutation == "hash": encoded["input_sha256"] = "0" * 64
    if mutation == "width": encoded["engine_parameters"]["M6-BS"]["width"] = 3
    if mutation == "methods": encoded["methods"][0] = "BF"
    if mutation == "configuration": encoded["configuration_id"] = True
    if mutation == "threshold": encoded["minimum_height_mm"] = "-1"
    with pytest.raises(old_codec.ComparisonSnapshotError):
        decode_comparison_input_v2(encoded)


def test_failure_codec_preserves_absence_of_result_and_public_diagnostic():
    payload = ExecutionPayloadV2(method="HF", result=None,
        diagnostic=ExecutionDiagnostic(origin="SUPERVISOR", termination_reason="WORKER_STOPPED", statistics={}))
    assert decode_result_v3(encode_result_v3(payload)) == payload


def test_control_bodies_and_confirmation_envelope_are_explicitly_versioned():
    assert ComparisonSelectionV2(execution_id=4306, expected_version=7).execution_id == 4306
    assert ComparisonReleaseV2(expected_version=7).expected_version == 7
    with pytest.raises(ValidationError):
        ComparisonSelectionV2(execution_id=True, expected_version=7)
    old_file = FIXTURE.with_name("comparison-v1.json")
    old = json.loads(old_file.read_text(encoding="utf-8"))
    mask = next(iter(old["masks"].values()))
    mask.update(profile="comparison-v2", schema_version=2, method="M5")
    assert ComparisonMaskPayloadV2.model_validate(mask).method == "M5"
    mask["comparison_id"] += 1
    with pytest.raises(ValidationError):
        ComparisonMaskPayloadV2.model_validate(mask)
    schema = ComparisonConfirmationV2.model_json_schema()
    assert schema["properties"]["profile"]["const"] == "comparison-v2"


def test_masks_and_event_payload_cannot_cross_execution_boundaries(wire):
    old = json.loads(FIXTURE.with_name("comparison-v1.json").read_text(encoding="utf-8"))
    event = deepcopy(next(e for e in old["events"] if e["event"] == "piece_ready"))
    event.update(profile="comparison-v2", schema_version=2, presentation="OBSERVED", comparison_id=43,
                 execution_id=4305, method="M5")
    event["data"]["mask"].update(profile="comparison-v2", schema_version=2, comparison_id=43,
        id_optimizacion=43, execution_id=4305, method="M5")
    ComparisonEventV2.model_validate(event)
    standalone = deepcopy(event["data"]["mask"])
    standalone["id_optimizacion"] = 99
    with pytest.raises(ValidationError):
        ComparisonMaskV2.model_validate(standalone)
    event["data"]["mask"]["execution_id"] = 4306
    with pytest.raises(ValidationError):
        ComparisonEventV2.model_validate(event)
