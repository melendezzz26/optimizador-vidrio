"""Reproduce B03 parity/callback/resource evidence with productive engines.

From backend: python -m tests.unit.optimization.engine_execution_support
This is direct adapter evidence, never a substitute for service smoke.
"""
from collections import Counter
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path

from app.modules.optimization.application.comparison_catalog import CATALOG_V2
from app.modules.optimization.application.comparison_v2_contracts import ExecutionDiagnostic, ExecutionPayloadV2
from app.modules.optimization.application.engine_execution import EngineExecutionAdapter, ExecutionScope
from app.modules.optimization.domain.beam_search import BeamSearchLimits
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.infrastructure.comparison_snapshot import canonical_json, encode_problem, problem_fingerprint
from app.modules.optimization.infrastructure.comparison_v2_snapshot import encode_result_v3
from tests.unit.optimization.test_engine_execution import parity_cases

ROOT = Path(__file__).resolve().parents[4]


def digest(value):
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def main():
    problem = list(parity_cases())[-1]  # All three official shapes, real 5 degree configuration.
    records = []
    for identifier, definition in enumerate(CATALOG_V2, 4301):
        scope = ExecutionScope(comparison_id=43, execution_id=identifier, method=definition.code)
        engine = definition.optimizer_type()
        raw_events = []
        if definition.code == "M6-BS":
            original = engine.run(problem, on_event=raw_events.append)
            raw, reason, stats = original.result, original.stop_reason, original.statistics
        else:
            raw = engine.optimize(problem, on_event=raw_events.append)
            reason, stats = None, ({k: int(v) for k, v in asdict(engine.stats).items()} if definition.code == "HF" else {})
        measured, residuals = calculate_metrics(raw, 1, 1)
        native_payload = ExecutionPayloadV2(method=definition.code, result=replace(measured, computation_time_ms=0),
            diagnostic=ExecutionDiagnostic(origin="ENGINE", termination_reason=reason or (
                "COMPLETED" if raw.complete else "NO_FIT"), statistics=stats))
        facts, checks = [], []
        adapted = EngineExecutionAdapter(definition.code).execute(scope, problem,
            minimum_width_mm=1, minimum_height_mm=1, checkpoint=lambda: checks.append(True), on_observation=facts.append)
        assert adapted.error_type is None
        normalized = replace(adapted.payload, result=replace(adapted.payload.result, computation_time_ms=0))
        assert encode_result_v3(native_payload) == encode_result_v3(normalized)
        assert tuple(residuals) == adapted.residuals
        records.append(dict(method=definition.code, label=definition.label, optimizer=definition.optimizer_type.__name__,
            scope=asdict(scope), input_sha256=problem_fingerprint(problem), result_type=type(raw).__name__,
            direct_sha256=digest(encode_result_v3(native_payload)), adapted_sha256=digest(encode_result_v3(normalized)),
            equality_excludes_only_elapsed_time=True, residuals_equal=True, result_snapshot=encode_result_v3(adapted.payload),
            checkpoint_calls=len(checks), native_milestone_count=len(raw_events),
            observations=dict(Counter(f"{f.kind}/{f.presentation}" for f in facts)),
            search_progress=[asdict(f.fact) for f in facts if f.kind == "search_progress"],
            beam_trace=adapted.beam_outcome.trace if adapted.beam_outcome else None,
            result="PASS"))
    reasons = []
    for limits in (BeamSearchLimits(max_expansions=1, complete_on_stop=False),
                   BeamSearchLimits(max_geometry_probes=1, complete_on_stop=False),
                   BeamSearchLimits(max_state_bytes=1, complete_on_stop=False),
                   BeamSearchLimits(seconds=0.000000001, complete_on_stop=False)):
        scope = ExecutionScope(comparison_id=44, execution_id=4406, method="M6-BS")
        adapted = EngineExecutionAdapter("M6-BS", beam_limits=limits).execute(scope, problem, minimum_width_mm=1, minimum_height_mm=1)
        assert adapted.payload.result is not None and not adapted.payload.result.complete and adapted.error_type is None
        reasons.append(dict(test_limits=asdict(limits), diagnostic=adapted.payload.diagnostic.public(),
            placed_units=adapted.payload.result.placed_units, complete=adapted.payload.result.complete,
            original_stop_reason=adapted.beam_outcome.stop_reason, result="PASS"))
    target = ROOT / "docs/evidence/sprint-02/TA-043/B03/adapter-validation.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(dict(result="PASS", scope="direct adapters only; not HTTP integration",
        production_beam_limits=asdict(BeamSearchLimits()), problem=encode_problem(problem),
        records=records, actual_m6_resource_terminations=reasons), indent=2) + "\n", encoding="utf-8")
    print(f"PASS: six direct/adapted results, checkpoints and four actual M6 terminations; {target}")


if __name__ == "__main__":
    main()
