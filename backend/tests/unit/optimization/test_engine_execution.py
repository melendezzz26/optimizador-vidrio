"""T-03: production engines through B03, without processes, DB or HTTP mocks."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace

import pytest

from app.modules.optimization.application.comparison_catalog import BY_METHOD, CATALOG_V2, METHODS_V2
from app.modules.optimization.application.engine_execution import EngineExecutionAdapter as ProductiveAdapter, ExecutionScope
from app.modules.optimization.application.errors import ExecutionInterrupted, TimeBudgetExceeded
from app.modules.optimization.domain.beam_search import BeamSearchLimits, BeamSearchOptimizer
from app.modules.optimization.domain.hole_filling import HoleFillingLimits, HoleFillingOptimizer
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.domain.preparation import prepare_group_units
from app.modules.optimization.domain.problem import MaterialSource
from app.modules.optimization.infrastructure.comparison_v2_snapshot import encode_result_v3, decode_result_v3
from app.modules.optimization.presentation.comparison_v2_schemas import SearchProgressV2
from tests.unit.optimization.test_comparison import representative_cases
from tests.unit.optimization.test_comparison_snapshot import example
from tests.unit.optimization.test_hole_filling import coverage_problem, sheet_problem, product_problem, circle, triangle


class EngineExecutionAdapter(ProductiveAdapter):
    """Test fixtures freeze the same explicit 1 mm minima in both executions."""
    def execute(self, scope, problem, **kwargs):
        return super().execute(scope, problem, minimum_width_mm=1, minimum_height_mm=1, **kwargs)


def scope(method, execution=4301, comparison=43):
    return ExecutionScope(comparison_id=comparison, execution_id=execution, method=method)


def functional(result):
    return replace(result, computation_time_ms=None)


def canonical(problem):
    # Existing mixed-tier fixtures may list sheets before remnants. B01/B02's
    # frozen input uses canonical tier order, preserving rank within each tier.
    return replace(problem, order_ids=tuple(sorted(problem.order_ids)), groups=tuple(
        replace(g, units=prepare_group_units(g.units), stock_candidates=tuple(sorted(
            g.stock_candidates, key=lambda s: s.source is MaterialSource.SHEET)))
        for g in sorted(problem.groups, key=lambda g: g.key)))


def parity_cases():
    yield from (canonical(p) for p in representative_cases())
    from tests.unit.optimization.test_first_fit import piece, problem, stock, config
    yield canonical(problem([circle(1, 1), triangle(2, 3, 2), piece(3, width=2, height=1)],
                            [stock(width=8, height=6)], config(angular_step_deg=5)))


@pytest.mark.parametrize("definition", CATALOG_V2, ids=lambda d: d.code)
@pytest.mark.parametrize("problem", list(parity_cases()))
def test_direct_and_adapted_parity_including_native_observation(definition, problem):
    before = repr(problem)
    native_events, observed = [], []
    optimizer = definition.optimizer_type()
    if definition.code == "M6-BS":
        outcome = optimizer.run(problem, on_progress=lambda f: native_events.append(("search_progress", f)))
        raw = outcome.result
    else:
        raw = optimizer.optimize(problem, lambda f: native_events.append(("milestone", f)),
                                 on_visual=lambda f: native_events.append(("visual", f)))
    expected, residuals = calculate_metrics(raw, 1, 1)
    adapted = EngineExecutionAdapter(definition.code).execute(scope(definition.code), problem,
                                                           on_observation=observed.append)
    assert adapted.error_type is None and adapted.payload.result is not None
    assert functional(adapted.payload.result) == expected
    assert adapted.residuals == tuple(residuals) and repr(problem) == before
    assert [(f.kind, f.fact) for f in observed[:-1]] == native_events
    assert observed[-1].kind == "final_layout" and observed[-1].fact is adapted.payload.result
    assert observed[-1].presentation == "FINAL_REPLAY"
    assert all(f.scope == adapted.scope for f in observed)
    if definition.code == "M6-BS":
        assert adapted.beam_outcome == outcome
        assert all(f.presentation == "PROVISIONAL" for f in observed[:-1])
        assert all(not hasattr(f.fact, "placement") for f in observed[:-1])
        for f in observed[:-1]:
            SearchProgressV2.model_validate(asdict(f.fact))
    else:
        assert adapted.beam_outcome is None
        assert all(f.presentation == ("FINAL_REPLAY" if definition.code == "HF" else "OBSERVED") for f in observed[:-1])
    assert decode_result_v3(encode_result_v3(adapted.payload), expected_method=definition.code) == adapted.payload


@pytest.mark.parametrize("method", METHODS_V2)
def test_callbacks_off_and_broken_observer_preserve_results_and_checkpoints(method):
    adapter = EngineExecutionAdapter(method)
    plain = adapter.execute(scope(method), example())
    calls = []
    def broken(fact):
        calls.append(fact)
        raise RuntimeError("observer disconnected")
    checks = []
    observed = adapter.execute(scope(method), example(), checkpoint=lambda: checks.append(True), on_observation=broken)
    assert functional(plain.payload.result) == functional(observed.payload.result)
    assert len(calls) == 1 and len(checks) > 3
    assert observed.observer_error_type == "RuntimeError" and observed.error_type is None


@pytest.mark.parametrize("method", METHODS_V2)
def test_new_productive_instance_for_each_execution_and_no_cross_scope_observations(method, monkeypatch):
    cls = BY_METHOD[method].optimizer_type
    native = cls.__init__
    instances = []
    def create(self, *args, **kwargs):
        instances.append(self)
        native(self, *args, **kwargs)
    monkeypatch.setattr(cls, "__init__", create)
    adapter, observations = EngineExecutionAdapter(method), []
    left = adapter.execute(scope(method), example(), on_observation=observations.append)
    right_facts = []
    right = adapter.execute(scope(method, 5301, 53), example(), on_observation=right_facts.append)
    assert len(instances) == 2 and instances[0] is not instances[1]
    assert functional(left.payload.result) == functional(right.payload.result)
    assert all(f.scope == left.scope for f in observations)
    assert all(f.scope == right.scope for f in right_facts)


@pytest.mark.parametrize("method", ["BRF", "BS-2", "DJD", "AUTO", "", None, True])
def test_unknown_or_ambiguous_method_is_rejected(method):
    with pytest.raises(ValueError):
        EngineExecutionAdapter(method)


def test_inconsistent_scope_and_wrong_engine_configuration_rejected():
    with pytest.raises(ValueError):
        EngineExecutionAdapter("FF").execute(scope("BF"), example())
    for identifier in (True, 0, -1):
        with pytest.raises(ValueError):
            scope("FF", identifier)
    with pytest.raises(ValueError):
        EngineExecutionAdapter("M6-BS", beam_limits=BeamSearchLimits(width=3))
    with pytest.raises(ValueError):
        EngineExecutionAdapter("FF", beam_limits=BeamSearchLimits())
    with pytest.raises(ValueError):
        EngineExecutionAdapter("M5", hole_limits=HoleFillingLimits())


def test_captured_residual_minima_are_required_and_preserve_configured_metrics():
    with pytest.raises(TypeError):
        ProductiveAdapter("FF").execute(scope("FF"), example())
    measured, residuals = calculate_metrics(BY_METHOD["FF"].optimizer_type().optimize(example()), 20, 20)
    adapted = ProductiveAdapter("FF").execute(scope("FF"), example(), minimum_width_mm=20, minimum_height_mm=20)
    assert functional(adapted.payload.result) == measured and adapted.residuals == tuple(residuals)
    assert not adapted.residuals


@pytest.mark.parametrize("method", METHODS_V2)
@pytest.mark.parametrize("error,reason", [(ExecutionInterrupted, "CANCELLED"),
    (TimeBudgetExceeded, "TIME_BUDGET_EXCEEDED"), (MemoryError, "MEMORY_BUDGET_EXCEEDED"),
    (RuntimeError, "EXECUTION_FAILED")])
def test_checkpoint_failure_without_observer_returns_no_invented_partial(method, error, reason):
    checks = []
    def checkpoint():
        checks.append(True)
        if len(checks) == 3:
            raise error("internal detail must not become a public diagnostic")
    result = EngineExecutionAdapter(method).execute(scope(method), example(), checkpoint=checkpoint)
    assert len(checks) == 3 and result.payload.result is None and not result.residuals
    assert result.payload.diagnostic.origin == "SUPERVISOR"
    assert result.payload.diagnostic.termination_reason == reason and result.error_type == error.__name__
    assert result.beam_outcome is None


@pytest.mark.parametrize("limits,reason", [
    (BeamSearchLimits(max_expansions=1, complete_on_stop=False), "EXPANSION_LIMIT"),
    (BeamSearchLimits(max_geometry_probes=1, complete_on_stop=False), "GEOMETRY_PROBE_LIMIT"),
    (BeamSearchLimits(max_state_bytes=1, complete_on_stop=False), "STATE_MEMORY_LIMIT"),
    (BeamSearchLimits(seconds=0.000000001, complete_on_stop=False), "TIME_LIMIT"),
])
@pytest.mark.parametrize("observed", [False, True])
def test_original_m6_resource_outcome_and_empty_partial_survive(limits, reason, observed):
    facts = []
    original = BeamSearchOptimizer(limits).run(example())
    result = EngineExecutionAdapter("M6-BS", beam_limits=limits).execute(scope("M6-BS"), example(),
        on_observation=facts.append if observed else None)
    assert result.error_type is None and result.beam_outcome == original
    assert not result.payload.result.complete
    assert result.payload.diagnostic.termination_reason == reason
    assert dict(result.payload.diagnostic.statistics) == original.statistics
    assert result.payload.result.method == "M6-BS"
    assert all(f.kind in ("search_progress", "final_layout") for f in facts)
    assert decode_result_v3(encode_result_v3(result.payload), expected_method="M6-BS") == result.payload


def test_m6_partial_nonempty_is_last_completed_frontier_and_no_search_replay(monkeypatch):
    from tests.unit.optimization.test_first_fit import piece, problem, stock, config
    p = problem([piece(quantity=3, width=2, height=2)], [stock(width=5, height=4)], config(angular_step_deg=5))
    progress = []
    BeamSearchOptimizer().run(p, on_progress=progress.append)
    limits = BeamSearchLimits(max_expansions=progress[1].expansions + 1, complete_on_stop=False)
    original = BeamSearchOptimizer(limits).run(p)
    assert 0 < original.result.placed_units < original.result.total_units
    native, calls = BeamSearchOptimizer.run, []
    def run(self, *args, **kwargs):
        calls.append(self)
        return native(self, *args, **kwargs)
    monkeypatch.setattr(BeamSearchOptimizer, "run", run)
    facts = []
    result = EngineExecutionAdapter("M6-BS", beam_limits=limits).execute(scope("M6-BS"), p, on_observation=facts.append)
    assert len(calls) == 1 and result.beam_outcome == original
    assert functional(result.payload.result).placements == original.result.placements
    assert facts[-1].fact.placements == original.result.placements
    assert all(not hasattr(f.fact, "placements") for f in facts[:-1])
    assert result.payload.diagnostic.termination_reason == "EXPANSION_LIMIT"


@pytest.mark.parametrize("factory,flag,limits", [(product_problem, "accepted_pocket", None),
    (coverage_problem, "coverage_fallback", None),
    (sheet_problem, "sheet_fallback", HoleFillingLimits(max_regions=24))])
def test_hf_chosen_solution_and_protection_flags_match_direct(factory, flag, limits):
    p = factory()
    direct = HoleFillingOptimizer(limits)
    expected = direct.optimize(p)
    facts = []
    result = EngineExecutionAdapter("HF", hole_limits=limits).execute(scope("HF"), p, on_observation=facts.append)
    assert result.payload.result.placements == expected.placements
    assert dict(result.payload.diagnostic.statistics) == {k: int(v) for k, v in asdict(direct.stats).items()}
    assert result.payload.diagnostic.statistics[flag] > 0
    placed = [f.fact.placement for f in facts if f.kind == "milestone" and f.fact.kind == "piece_placed"]
    assert tuple(placed) == expected.placements
    assert all(f.presentation == "FINAL_REPLAY" for f in facts)


def test_hf_existing_bounded_fallback_and_brf_source_policy():
    from tests.unit.optimization.test_first_fit import piece, problem, stock
    p = problem([piece(width=2, height=2)], [stock(1, width=3, height=3), stock(2, width=6, height=4)])
    result = EngineExecutionAdapter("HF", hole_limits=HoleFillingLimits(max_orientations=0)).execute(scope("HF"), p)
    expected = HoleFillingOptimizer(HoleFillingLimits(max_orientations=0)).optimize(p)
    assert result.payload.result.placements == expected.placements
    brf = EngineExecutionAdapter("M5").execute(scope("M5"), p)
    # SPEC-TA-052 v2: with no source in use, M5 opens the lowest stock_rank (before: 2).
    assert brf.payload.result.placements[0].stock.material_id == 1
    assert brf.payload.method == "M5" and BY_METHOD["M5"].label == "BRF"


def test_same_adapter_isolated_under_concurrent_calls_and_mismatched_result_is_failed(monkeypatch):
    adapter = EngineExecutionAdapter("FF")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda i: adapter.execute(scope("FF", i), example()), (1, 2)))
    assert functional(results[0].payload.result) == functional(results[1].payload.result)
    assert results[0].scope != results[1].scope
    wrong = BY_METHOD["BF"].optimizer_type().optimize(example())
    monkeypatch.setattr(BY_METHOD["FF"].optimizer_type, "optimize", lambda *args, **kwargs: wrong)
    failure = adapter.execute(scope("FF"), example())
    assert failure.payload.result is None and failure.error_type == "ValueError"
    assert failure.payload.diagnostic.termination_reason == "EXECUTION_FAILED"
