"""Observed facts must describe the same lazy geometry decisions as plain runs."""
from decimal import Decimal as D

import pytest

from app.modules.optimization.application.visual import OrientationSampler
from app.modules.optimization.domain.best_fit import BestFitOptimizer
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.rotation import RasterCache
from app.modules.optimization.domain.worst_fit import WorstFitOptimizer
from tests.unit.optimization.test_comparison import representative_cases
from tests.unit.optimization.test_first_fit import config, piece, problem, stock


@pytest.mark.parametrize('optimizer', [FirstFitOptimizer, BestFitOptimizer, WorstFitOptimizer])
@pytest.mark.parametrize('value', list(representative_cases()))
def test_observation_does_not_change_result_or_milestones(optimizer, value):
    milestones, plain_milestones, facts = [], [], []
    before = repr(value)
    plain = optimizer().optimize(value, plain_milestones.append)
    observed = optimizer().optimize(value, milestones.append, on_visual=facts.append)
    assert observed == plain and milestones == plain_milestones and repr(value) == before
    kinds = [fact.kind for fact in facts]
    assert kinds[0] == 'preparation_started'
    if 'orientation_testing' in kinds:
        assert kinds.index('preparation_completed') < kinds.index('orientation_testing')
    terminal = [fact for fact in facts if fact.kind in ('source_selected', 'piece_unplaced')]
    assert len(terminal) == len(value.units)
    assert [fact.processed_units for fact in terminal] == list(range(1, len(value.units) + 1))
    assert len([fact for fact in terminal if fact.kind == 'source_selected']) == plain.placed_units
    evaluations = [fact.evaluation_index for fact in facts if fact.kind == 'orientation_testing']
    assert evaluations == list(range(1, len(evaluations) + 1))
    for fact in facts:
        if fact.kind == 'piece_ready':
            assert fact.orientation == RasterCache().base(fact.unit, value.config.resolution_mm)
        if fact.kind == 'source_selected':
            placement = next(p for p in plain.placements if p.piece == fact.unit)
            assert placement.stock == fact.stock and placement.geometry == fact.orientation.geometry
            assert placement.rotation_deg == fact.orientation.rotation_deg
            assert (fact.score is None) == (plain.method == 'FF')


def test_sampler_preserves_first_per_unit_and_caps_additional_samples():
    now = [0.0]
    sampler = OrientationSampler(clock=lambda: now[0])
    units = problem([piece(quantity=150)]).units
    for unit in units:
        assert sampler.accept(unit)
    assert len(sampler.seen) == 150
    assert sampler.accept(units[0])
    assert not sampler.accept(units[0])
    for _ in range(127):
        now[0] += .1
        assert sampler.accept(units[0])
    now[0] += 10
    assert not sampler.accept(units[0]) and sampler.extra == 128


def test_observation_does_not_generate_unused_rotations(monkeypatch):
    original = RasterCache._orientation
    angles = []
    def orientation(self, unit, resolution, angle):
        angles.append(angle)
        return original(self, unit, resolution, angle)
    monkeypatch.setattr(RasterCache, '_orientation', orientation)
    facts = []
    result = FirstFitOptimizer().optimize(problem([piece(width=2, height=2)], [stock()],
        config(angular_step_deg=D(5))), on_visual=facts.append)
    assert result.complete and set(angles) == {D(0)}
    assert len([fact for fact in facts if fact.kind == 'orientation_testing']) == 1
