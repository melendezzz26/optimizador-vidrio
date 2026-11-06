"""M6-02: reverse bit search versus the original exhaustive scan."""
from dataclasses import replace
import random

import pytest

from app.modules.optimization.domain.placement import SheetLayout
from app.modules.optimization.domain.raster_mask import RasterMask
from app.modules.optimization.domain.beam_search import BeamSearchOptimizer, BeamSearchLimits
from app.modules.optimization.domain.metrics import calculate_metrics
from .test_beam_search import loader


def exhaustive(layout, mask, checkpoint=None, on_scan=None):
    for row in range(layout.material.row_count-mask.row_count, -1, -1):
        for column in range(layout.material.columns-mask.columns, -1, -1):
            if checkpoint:
                checkpoint()
            if on_scan:
                on_scan(1)
            if layout.check(mask, row, column).is_valid:
                return row, column
    return None


def test_disconnected_empty_edge_and_random_masks_match_exhaustive():
    rng = random.Random(20261106)
    for _ in range(1920):
        cols, rows = rng.randrange(1, 12), rng.randrange(1, 12)
        material = RasterMask(1, cols, tuple(rng.randrange(1 << cols) for _ in range(rows)))
        layout = SheetLayout.empty(material, margin_mm=rng.randrange(3),
                                   separation_mm=rng.randrange(3))
        blocked = tuple(rng.randrange(1 << cols) for _ in range(rows))
        layout = replace(layout, occupied=blocked, blocked=blocked)
        width, height = rng.randrange(1, 13), rng.randrange(1, 13)
        mask = RasterMask(1, width, tuple(rng.randrange(1 << width) for _ in range(height)))
        expected_probes, actual_probes = [], []
        expected = exhaustive(layout, mask, on_scan=expected_probes.append)
        actual = layout.last_position(mask, on_scan=actual_probes.append)
        assert actual == expected
        assert sum(actual_probes) == sum(expected_probes)


@pytest.mark.parametrize("case_id", loader.CASES)
def test_rotations_irregular_remnants_traces_geometry_and_metrics_match_old_scan(case_id, monkeypatch):
    problem = loader.load_problem(case_id)
    actual = BeamSearchOptimizer().run(problem)
    monkeypatch.setattr(SheetLayout, "last_position", exhaustive)
    expected = BeamSearchOptimizer().run(problem)
    assert actual.result == expected.result
    assert actual.trace == expected.trace
    assert actual.statistics["geometry_probes"] == expected.statistics["geometry_probes"]
    from decimal import Decimal
    assert calculate_metrics(actual.result, Decimal(1), Decimal(1)) == calculate_metrics(
        expected.result, Decimal(1), Decimal(1))


@pytest.mark.parametrize("limit", (1, 7, 30, 100, 500))
def test_logical_probe_limit_preserves_the_same_completed_frontier(limit, monkeypatch):
    problem = loader.load_problem("EXP-MEDIUM-001")
    optimizer = BeamSearchOptimizer(BeamSearchLimits(max_geometry_probes=limit))
    actual = optimizer.run(problem)
    monkeypatch.setattr(SheetLayout, "last_position", exhaustive)
    expected = optimizer.run(problem)
    assert actual.stop_reason == expected.stop_reason
    assert actual.trace == expected.trace
    assert actual.result == expected.result
    assert actual.statistics["geometry_probes"] == expected.statistics["geometry_probes"]


def test_checkpoint_interrupts_dense_scan():
    layout = SheetLayout.empty(RasterMask(1, 100, (0,) * 100))
    def stop():
        raise RuntimeError("cancelled")
    with pytest.raises(RuntimeError, match="cancelled"):
        layout.last_position(RasterMask(1, 2, (3, 3)), checkpoint=stop)
