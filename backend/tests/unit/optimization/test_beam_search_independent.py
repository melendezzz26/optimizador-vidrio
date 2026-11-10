"""Academic M6: no cross-engine completion, bounded native candidates."""
import pytest

from app.modules.optimization.application.engine_execution import EngineExecutionAdapter, ExecutionScope
from app.modules.optimization.domain.beam_search import BeamSearchLimits, BeamSearchOptimizer
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from tests.unit.optimization.test_first_fit import config, piece, problem, stock


def sample():
    return problem([piece(quantity=6, width=2, height=2)],
                   [stock(width=10, height=10)], config(angular_step_deg=5))


@pytest.mark.parametrize('overrides,reason', [
    ({'max_expansions': 1}, 'EXPANSION_LIMIT'),
    ({'seconds': .000000001}, 'TIME_LIMIT'),
    ({'max_state_bytes': 1}, 'STATE_MEMORY_LIMIT'),
    ({'max_geometry_probes': 1}, 'GEOMETRY_PROBE_LIMIT'),
])
def test_resource_exhaustion_never_calls_another_engine(monkeypatch, overrides, reason):
    def forbidden(*args, **kwargs):
        pytest.fail('M6 must never complete with First Fit')
    monkeypatch.setattr(FirstFitOptimizer, 'optimize', forbidden)
    result = EngineExecutionAdapter('M6-BS', beam_limits=BeamSearchLimits(**overrides)).execute(
        ExecutionScope(comparison_id=1, execution_id=6, method='M6-BS'), sample(),
        minimum_width_mm=1, minimum_height_mm=1)
    assert result.error_type is None
    assert result.payload.diagnostic.termination_reason == reason
    assert not result.payload.result.complete
    assert not any(key.startswith('fallback_') for key in result.payload.diagnostic.statistics)


def test_bounded_policy_closes_every_level_and_revalidates_geometry():
    from app.modules.optimization.domain.metrics import calculate_metrics
    p = sample()
    first = BeamSearchOptimizer().run(p)
    second = BeamSearchOptimizer().run(p)
    # Memory diagnostics measure live Python objects and can vary with allocator
    # state; determinism applies to the solution, trace and search decisions.
    assert (first.result, first.processed, first.stop_reason, first.trace) == (
        second.result, second.processed, second.stop_reason, second.trace)
    memory_fields = {'state_bytes_bound', 'state_bytes_peak'}
    assert {k: v for k, v in first.statistics.items() if k not in memory_fields} == {
        k: v for k, v in second.statistics.items() if k not in memory_fields}
    for outcome in (first, second):
        assert 0 < outcome.statistics['state_bytes_peak'] <= outcome.statistics['state_bytes_bound'] <= BeamSearchLimits().max_state_bytes
    assert first.result.complete and first.processed == 6
    assert first.statistics['expansions'] <= first.statistics['parents'] * 12
    assert first.statistics['max_frontier'] == 2
    assert first.statistics['bounded_candidates'] == 1
    calculated, _ = calculate_metrics(first.result, 1, 1)
    assert calculated.metrics is not None
    assert first.result.problem == p


@pytest.mark.parametrize('value', [0, -1, 129, True, 1.5])
def test_candidate_budget_is_finite_and_validated(value):
    with pytest.raises(ValueError, match='candidate_limit'):
        BeamSearchLimits(candidate_limit=value)


def test_historical_policy_is_explicit_and_still_independent():
    result = BeamSearchOptimizer(BeamSearchLimits(candidate_limit=None)).run(sample())
    assert result.result.complete
    assert result.statistics['bounded_candidates'] == 0
    assert not any(key.startswith('fallback_') for key in result.statistics)


def test_identical_empty_physical_sheets_are_symmetric_without_losing_identity():
    single = problem([piece(width=3, height=2)], [stock(width=8, height=8)], config(angular_step_deg=90))
    many = problem([piece(width=3, height=2)],
                   [stock(width=8, height=8, physical=i) for i in (1, 2, 3, 4)],
                   config(angular_step_deg=90))
    one = BeamSearchOptimizer().run(single)
    four = BeamSearchOptimizer().run(many)
    assert one.result.complete and four.result.complete
    assert one.statistics['expansions'] == four.statistics['expansions']
    assert four.result.placements[0].stock.physical_unit_index == 1
    assert len(many.groups[0].stock_candidates) == 4
