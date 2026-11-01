"""Fixture pública compartida. Autor: Fabricio Melendez Quezada. Revisor: Andro Quispe."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from app.modules.optimization.presentation.comparison_schemas import ComparisonSummary, ComparisonEvent, ComparisonMaskPayload, ExecutionResponse
from app.modules.optimization.presentation.run_schemas import RunResponseV1

FIXTURE = Path(__file__).resolve().parents[4] / "docs/contracts/optimization/comparison-v1.json"


def test_real_engine_fixture_has_three_results_and_typed_visual_facts():
    data = json.loads(FIXTURE.read_text())
    accepted = ComparisonSummary.model_validate(data["accepted"])
    complete = ComparisonSummary.model_validate(data["completed"])
    assert accepted.selected_execution_id is complete.selected_execution_id is None
    assert {ExecutionResponse.model_validate(r).result.metodo for r in data["results"].values()} == {"FF", "BF", "WF"}
    events = [ComparisonEvent.model_validate(e) for e in data["events"]]
    assert [e.sequence for e in events] == list(range(1, len(events) + 1))
    for mask in data["masks"].values():
        ComparisonMaskPayload.model_validate(mask)
    with pytest.raises(ValidationError):
        RunResponseV1.model_validate(data["results"]["2"]["result"])


def test_cross_engine_mask_and_untyped_payload_are_rejected():
    data = json.loads(FIXTURE.read_text())
    original = next(e for e in data["events"] if "mask" in e["data"])
    wrong = deepcopy(original)
    wrong["data"]["mask"]["execution_id"] += 1
    with pytest.raises(ValidationError):
        ComparisonEvent.model_validate(wrong)
    wrong = deepcopy(original)
    wrong["data"] = {}
    with pytest.raises(ValidationError):
        ComparisonEvent.model_validate(wrong)
