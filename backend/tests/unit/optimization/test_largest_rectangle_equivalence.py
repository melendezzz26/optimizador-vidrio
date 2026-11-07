"""S2-M6 F4b: the segment-compressed largest_rectangle equals the original one.

_reference_largest_rectangle is a verbatim copy of metrics.largest_rectangle
before F4b (column-by-column scan). Every comparison is exact equality of
(top, left, width, height), including the documented tie order, plus the same
number of checkpoint calls (one per run of identical rows).
"""
import importlib.util
import random
from itertools import groupby
from pathlib import Path

import pytest

from app.modules.optimization.domain import beam_search, best_residual_fit, metrics
from app.modules.optimization.domain.beam_search import BeamSearchLimits, BeamSearchOptimizer
from app.modules.optimization.domain.best_residual_fit import BestResidualFitOptimizer
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.metrics import calculate_metrics, largest_rectangle
from scripts.benchmark_load_engines import build_problem

ROOT = Path(__file__).resolve().parents[4]
SPEC = importlib.util.spec_from_file_location("experimental_cases", ROOT / "experiments/optimization/loader.py")
loader = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(loader)


def _reference_largest_rectangle(free_rows, columns, *, checkpoint=None):
    heights = [0] * columns
    best, best_key = None, None
    row = -1
    for bits, repeated in groupby(free_rows):
        if checkpoint is not None:
            checkpoint()
        count = sum(1 for _ in repeated)
        row += count
        heights = [heights[c] + count if (bits >> c) & 1 else 0 for c in range(columns)]
        stack = []
        for column in range(columns + 1):
            height = heights[column] if column < columns else 0
            start = column
            while stack and stack[-1][1] > height:
                left, h = stack.pop()
                width, top = column - left, row - h + 1
                key = (-width * h, top, left, -width, -h)
                if best_key is None or key < best_key:
                    best_key, best = key, (top, left, width, h)
                start = left
            if height and (not stack or stack[-1][1] < height):
                stack.append((start, height))
    return best


def assert_same(rows, columns):
    rows = tuple(rows)
    expected_calls, actual_calls = [], []
    expected = _reference_largest_rectangle(rows, columns, checkpoint=lambda: expected_calls.append(1))
    actual = largest_rectangle(rows, columns, checkpoint=lambda: actual_calls.append(1))
    assert actual == expected, (columns, rows)
    assert len(actual_calls) == len(expected_calls)


def _density_rows(rng, width, height):
    p = rng.choice((0.0, 0.05, 0.3, 0.5, 0.7, 0.95, 1.0))
    rows = [sum(1 << c for c in range(width) if rng.random() < p) for _ in range(height)]
    # Repeat some rows so groupby forms runs of different lengths.
    return [rows[i] if rng.random() < 0.6 or i == 0 else rows[i - 1] for i in range(height)]


def _block_rows(rng, width, height):
    rows = [(1 << width) - 1] * height
    for _ in range(rng.randint(0, 12)):
        top, left = rng.randrange(height), rng.randrange(width)
        bottom, right = rng.randint(top + 1, height), rng.randint(left + 1, width)
        hole = ((1 << (right - left)) - 1) << left
        for r in range(top, bottom):
            rows[r] &= ~hole
    return rows


def _stripe_rows(rng, width, height):
    patterns = [rng.getrandbits(width) for _ in range(rng.randint(1, 4))]
    rows = []
    while len(rows) < height:
        rows.extend([rng.choice(patterns)] * rng.randint(1, 30))
    return rows[:height]


def _tie_rows(rng, width, height):
    # Equal free cells separated by occupied lines: many maximal ties.
    cell_w, cell_h = rng.randint(1, max(1, width // 2)), rng.randint(1, max(1, height // 2))
    line = sum(1 << c for c in range(width) if (c + 1) % (cell_w + 1))
    return [0 if (r + 1) % (cell_h + 1) == 0 else line for r in range(height)]


GENERATORS = (_density_rows, _block_rows, _stripe_rows, _tie_rows)


@pytest.mark.parametrize("seed", range(4))
def test_pseudorandom_layouts_are_identical(seed):
    rng = random.Random(20261107 + seed)
    for _ in range(500):
        small = rng.random() < 0.7
        width = rng.randint(1, 40) if small else rng.randint(41, 300)
        height = rng.randint(1, 60) if small else rng.randint(61, 200)
        rows = rng.choice(GENERATORS)(rng, width, height)
        if rng.random() < 0.1:
            # Bits beyond the material columns are ignored by both versions.
            rows = [bits | (rng.getrandbits(5) << width) for bits in rows]
        assert_same(rows, width)


@pytest.mark.parametrize("width,height", [(1, 1), (1, 7), (9, 1), (17, 13), (300, 200)])
def test_all_free_and_all_occupied(width, height):
    assert_same([(1 << width) - 1] * height, width)
    assert_same([0] * height, width)


def test_single_column_single_row_and_degenerate_inputs():
    rng = random.Random(7)
    for _ in range(200):
        assert_same([rng.getrandbits(1) for _ in range(rng.randint(1, 60))], 1)
        width = rng.randint(1, 300)
        assert_same([rng.getrandbits(width)], width)
    assert_same([], 5)
    assert_same([0, 3, 1], 0)
    assert_same([-1, -6, ~0b1010, -1], 8)
    # A one-pass iterable is accepted, as before.
    assert largest_rectangle(iter([0b111, 0b111]), 3) == _reference_largest_rectangle([0b111, 0b111], 3)


@pytest.mark.parametrize("width,height", [(2, 4), (4, 2), (3, 3)])
def test_exhaustive_small_grids(width, height):
    for value in range(1 << (width * height)):
        rows = [(value >> (r * width)) & ((1 << width) - 1) for r in range(height)]
        assert_same(rows, width)


def _record_real_inputs(monkeypatch):
    recorded = []

    def spy(free_rows, columns, *, checkpoint=None):
        recorded.append((tuple(free_rows), columns))
        return largest_rectangle(free_rows, columns, checkpoint=checkpoint)
    for module in (metrics, beam_search, best_residual_fit):
        monkeypatch.setattr(module, "largest_rectangle", spy)
    return recorded


@pytest.mark.parametrize("case_id", loader.CASES)
def test_real_layouts_from_sp005_and_sp006_fixtures(case_id, monkeypatch):
    recorded = _record_real_inputs(monkeypatch)
    problem = loader.load_problem(case_id)
    calculate_metrics(FirstFitOptimizer().optimize(problem), 1, 1)
    BestResidualFitOptimizer().optimize(problem)  # SP-005 (M5) scoring
    BeamSearchOptimizer(BeamSearchLimits(max_expansions=40, complete_on_stop=False)).run(problem)  # SP-006 (M6)
    assert recorded
    for rows, columns in recorded:
        assert_same(rows, columns)


def test_real_2140_by_3300_sheets_from_the_load_script(monkeypatch):
    recorded = _record_real_inputs(monkeypatch)
    problem = build_problem(6)
    calculate_metrics(FirstFitOptimizer().optimize(problem), 1, 1)
    BeamSearchOptimizer(BeamSearchLimits(max_expansions=4, complete_on_stop=False)).run(problem)
    assert any(columns == 2140 for _, columns in recorded)
    for rows, columns in recorded:
        assert_same(rows, columns)
