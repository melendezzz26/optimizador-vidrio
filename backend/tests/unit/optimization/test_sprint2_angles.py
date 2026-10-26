"""Operational five-degree contract, preserving explicit research configurations."""
from decimal import Decimal as D
from unittest.mock import MagicMock

import pytest

from app.modules.optimization.application.errors import RunError
from app.modules.optimization.application.runs import AcceptRun
from app.modules.optimization.domain.best_fit import BestFitOptimizer
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.problem import MaterialSource, OptimizationConfig
from app.modules.optimization.domain.rotation import RasterCache, discrete_angles
from app.modules.optimization.domain.worst_fit import WorstFitOptimizer
from app.modules.optimization.infrastructure.configuration_seed import DEMO_PARAMETERS
from tests.unit.optimization.test_first_fit import problem, stock
from tests.unit.optimization.test_preparation import piece
from tests.unit.optimization.test_rotation import unit


def test_operational_default_seed_and_exact_sequence():
    cfg = OptimizationConfig(resolution_mm=1, margin_mm=0, separation_mm=0)
    assert cfg.angular_step_deg == DEMO_PARAMETERS['paso_angular_grados'] == 5
    angles = discrete_angles(cfg.angular_step_deg)
    assert angles == tuple(D(i) for i in range(0, 360, 5))
    assert len(angles) == 72 and angles[-1] == 355


def test_five_degree_dedup_keeps_first_mask_angle_and_circle_once():
    cache = RasterCache()
    orientations = cache.orientations(unit(), D(1), D(5))
    angles = [entry.orientation.rotation_deg for entry in orientations]
    masks = [(entry.orientation.mask.columns, entry.orientation.mask.rows) for entry in orientations]
    assert len(masks) == len(set(masks)) < 72
    assert angles == sorted(angles) and angles[0] == 0 and all(0 <= a < 360 for a in angles)
    assert D(180) not in angles  # same rectangular mask as 0 degrees
    circle = cache.orientations(unit(dict(type='CIRCUNFERENCIA', radius_mm=2)), D(1), D(5))
    assert [entry.orientation.rotation_deg for entry in circle] == [0]


@pytest.mark.parametrize('optimizer', [FirstFitOptimizer, BestFitOptimizer, WorstFitOptimizer])
def test_default_five_degree_run_is_deterministic_remnants_first_and_input_unchanged(optimizer):
    cfg = OptimizationConfig(resolution_mm=1, margin_mm=0, separation_mm=0)
    rem = stock(9, width=4, height=4, source=MaterialSource.REMNANT)
    original = problem([piece(width=2, height=2, quantity=2)], [stock(1), rem], cfg)
    before = repr(original)
    first_events, second_events = [], []
    first = optimizer().optimize(original, first_events.append)
    second = optimizer().optimize(original, second_events.append)
    assert first == second and first_events == second_events and repr(original) == before
    assert all(p.stock == rem and p.rotation_deg == 0 for p in first.placements)


@pytest.mark.parametrize('step', [90, 45, 15])
def test_new_operational_runs_reject_old_step_before_locking_or_writing(step):
    uow = MagicMock()
    uow.configuration.return_value = (1, OptimizationConfig(
        resolution_mm=1, margin_mm=0, separation_mm=0, angular_step_deg=step))
    uow.__enter__.return_value = uow
    with pytest.raises(RunError, match='5°'):
        AcceptRun(lambda: uow).execute([1], 1)
    uow.orders.lock_pending.assert_not_called()
    uow.orders.transition.assert_not_called()
    uow.runs.create.assert_not_called()


def test_five_degree_operational_configuration_reaches_preparation():
    uow = MagicMock()
    uow.__enter__.return_value = uow
    uow.configuration.return_value = (1, OptimizationConfig(resolution_mm=1, margin_mm=0, separation_mm=0))
    uow.orders.lock_pending.return_value = [piece()]
    AcceptRun(lambda: uow).execute([1], 1)
    assert uow.runs.create.call_args.args[0].config.angular_step_deg == 5
