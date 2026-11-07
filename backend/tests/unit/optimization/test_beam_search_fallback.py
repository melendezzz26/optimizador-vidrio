"""S2-M6 F1: a stopped Beam Search is completed with First Fit's own decision.

Regression: with real sheet/remnant sizes M6 stopped by a limit before closing
its first level and returned 0 placed units, while the other five engines
placed the same piece in milliseconds.
"""
from dataclasses import replace

import pytest

from app.modules.optimization.application.engine_execution import EngineExecutionAdapter, ExecutionScope
from app.modules.optimization.domain.beam_search import BeamSearchLimits, BeamSearchOptimizer
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.problem import MaterialSource
from tests.unit.optimization.test_first_fit import config, piece, problem, stock


def real_size_problem():
    # Heroku case: one 1000x2500 piece over a 2440x3255 remnant, at 1 mm.
    return problem([piece(width=1000, height=2500)],
                   [stock(width=2440, height=3255, source=MaterialSource.REMNANT)])


def small_problem(*rows):
    rows = rows or (piece(quantity=3, width=2, height=2),)
    return problem(list(rows), [stock(width=5, height=4)], config(angular_step_deg=5))


@pytest.mark.parametrize("limits,counter", [
    (BeamSearchLimits(max_expansions=1), "fallback_from_expansion_limit"),
    (BeamSearchLimits(seconds=0.000001), "fallback_from_time_limit"),
    (BeamSearchLimits(max_state_bytes=1), "fallback_from_state_memory_limit"),
    (BeamSearchLimits(max_geometry_probes=1), "fallback_from_geometry_probe_limit"),
])
def test_real_size_stop_before_first_level_is_completed_like_first_fit(limits, counter):
    p = real_size_problem()
    outcome = BeamSearchOptimizer(limits).run(p)

    assert outcome.result.complete and outcome.result.placed_units == 1
    assert outcome.stop_reason is None
    assert outcome.processed == outcome.result.total_units == 1
    # Nothing was decided by the beam, so the layout is exactly First Fit's.
    assert outcome.result.placements == FirstFitOptimizer().optimize(p).placements
    assert outcome.statistics["fallback_used"] == 1
    assert outcome.statistics[counter] == 1
    assert outcome.statistics["fallback_beam_units"] == 0
    assert outcome.statistics["fallback_units"] == 1


def test_fallback_continues_from_the_last_completed_frontier():
    p = small_problem()
    progress = []
    BeamSearchOptimizer().run(p, on_progress=progress.append)
    limits = BeamSearchLimits(max_expansions=progress[1].expansions + 1)
    partial = BeamSearchOptimizer(replace(limits, complete_on_stop=False)).run(p)
    assert partial.stop_reason == "EXPANSION_LIMIT" and partial.processed > 0

    completed = BeamSearchOptimizer(limits).run(p)

    decided = partial.processed
    assert completed.result.placements[:len(partial.result.placements)] == partial.result.placements
    assert completed.trace == partial.trace
    assert completed.processed == completed.result.total_units
    assert completed.statistics["fallback_beam_units"] == decided
    assert completed.statistics["fallback_units"] == completed.result.total_units - decided
    # Search counters are the same ones the partial run reported.
    assert {k: v for k, v in completed.statistics.items() if not k.startswith("fallback_")} == partial.statistics


def test_runs_inside_the_limits_are_identical_and_carry_no_fallback_counters():
    p = small_problem()
    default = BeamSearchOptimizer().run(p)
    without = BeamSearchOptimizer(BeamSearchLimits(complete_on_stop=False)).run(p)

    assert default.stop_reason is None
    assert default == without
    assert not any(key.startswith("fallback_") for key in default.statistics)


def test_complete_on_stop_requires_a_boolean():
    with pytest.raises(ValueError, match="complete_on_stop"):
        BeamSearchLimits(complete_on_stop=1)


@pytest.mark.parametrize("rows,reason", [
    ((piece(quantity=3, width=2, height=2),), "COMPLETED"),
    ((piece(1, width=2, height=2), piece(2, width=9, height=9)), "NO_FIT"),
])
def test_adapter_reports_a_geometric_termination_with_fallback_counters(rows, reason):
    p = small_problem(*rows)
    limits = BeamSearchLimits(max_expansions=1)
    adapted = EngineExecutionAdapter("M6-BS", beam_limits=limits).execute(
        ExecutionScope(comparison_id=43, execution_id=4306, method="M6-BS"), p,
        minimum_width_mm=1, minimum_height_mm=1)

    assert adapted.error_type is None
    assert adapted.payload.diagnostic.origin == "ENGINE"
    assert adapted.payload.diagnostic.termination_reason == reason
    assert adapted.payload.result.complete is (reason == "COMPLETED")
    assert adapted.payload.diagnostic.statistics["fallback_used"] == 1
    assert adapted.payload.diagnostic.statistics["fallback_from_expansion_limit"] == 1
