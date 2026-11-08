"""S2-M6 F2: incremental state accounting, shared empty layouts, same results.

The incremental measure must never be below graph_bytes over the same roots
(the T01 accounting), and runs inside the limits must not change.
"""
import importlib.util
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from app.modules.optimization.domain import packing
from app.modules.optimization.domain.beam_memory import (
    BeamStateMemory, _Walk, dimensions, graph_bytes, initial_bound, list_bytes_bound, row_bytes, set_bytes,
)
from app.modules.optimization.domain.beam_search import BeamSearchLimits, BeamSearchOptimizer
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.problem import MaterialSource
from app.modules.optimization.domain.rotation import RasterPreparationError
from tests.unit.optimization.test_beam_memory import large_problem
from tests.unit.optimization.test_first_fit import config, piece, problem, stock

ROOT = Path(__file__).resolve().parents[4]
SPEC = importlib.util.spec_from_file_location("experimental_cases", ROOT / "experiments/optimization/loader.py")
loader = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(loader)
MIB = 1024 * 1024


def real_sizes():
    sheets = [stock(1, width=2140, height=3300, physical=i) for i in (1, 2)]
    remnant = stock(2, width=2440, height=3255, source=MaterialSource.REMNANT)
    return problem([piece(1, width=600, height=800, quantity=2), piece(2, width=1000, height=1200)],
                   [remnant, *sheets], config(margin_mm=3, separation_mm=3))


def with_distinct_sheets(p, count):
    group = p.groups[0]
    sheets = tuple(replace(s, geometry=dict(type="RECTANGULO", width_mm=2140 - i, height_mm=3300),
                           area_mm2=(2140 - i) * 3300)
                   for i, s in enumerate(group.stock_candidates[:count]))
    return replace(p, groups=(replace(group, stock_candidates=sheets),))


def test_set_bytes_is_the_exact_size_of_a_set_grown_one_add_at_a_time():
    grown = set()
    assert set_bytes(0) == sys.getsizeof(grown)
    for value in range(120000):
        grown.add(value)
        assert set_bytes(len(grown)) == sys.getsizeof(grown), len(grown)


def test_list_bound_covers_growth_extend_and_shrink():
    pending, longest = [], 0
    for step in range(4000):
        if step % 7 == 6:
            del pending[-min(len(pending), 300):]
        else:
            pending.extend(range(step % 97 + 1))
        longest = max(longest, len(pending))
        assert sys.getsizeof(pending) <= list_bytes_bound(longest)


@pytest.mark.parametrize("case", ["SMALL", "MEDIUM", "COMPLEX", "REAL"])
def test_incremental_measure_is_a_tight_upper_bound_of_graph_bytes(case, monkeypatch):
    pairs, original = [], BeamStateMemory.search_bytes

    def spy(self, base, children):
        value = original(self, base, children)
        pairs.append((graph_bytes(tuple(base) + (children,)), value))
        return value
    monkeypatch.setattr(BeamStateMemory, "search_bytes", spy)
    if case == "REAL":
        BeamSearchOptimizer(BeamSearchLimits(max_expansions=12)).run(real_sizes())
    else:
        BeamSearchOptimizer().run(loader.load_problem(f"EXP-{case}-001"))

    assert pairs
    for exact, incremental in pairs:
        assert exact <= incremental <= exact + exact // 20 + 512 * 1024


@pytest.mark.parametrize("case_id", loader.CASES)
def test_results_are_identical_to_the_full_graph_walk(case_id, monkeypatch):
    current = BeamSearchOptimizer().run(loader.load_problem(case_id))

    def legacy(self, base, children, scratch=0):
        self.check(tuple(base) + (children,), scratch)
    monkeypatch.setattr(BeamStateMemory, "check_search", legacy)
    walked = BeamSearchOptimizer().run(loader.load_problem(case_id))

    def search_only(statistics):
        return {k: v for k, v in statistics.items() if not k.startswith("state_bytes_")}
    assert current.stop_reason is None and walked.stop_reason is None
    assert current.result == walked.result
    assert current.trace == walked.trace
    assert current.processed == walked.processed
    assert search_only(current.statistics) == search_only(walked.statistics)


def test_identical_sheets_no_longer_exhaust_the_initial_bound():
    stocks = large_problem(23).groups[0].stock_candidates
    assert initial_bound(stocks, large_problem().config) < 32 * MIB
    distinct = with_distinct_sheets(large_problem(23), 23).groups[0].stock_candidates
    assert initial_bound(distinct, large_problem().config) > 32 * MIB

    outcome = BeamSearchOptimizer(BeamSearchLimits(max_expansions=1)).run(
        large_problem(23))
    # The beam really searches: it stops on its expansion limit, not on memory.
    assert outcome.stop_reason == "EXPANSION_LIMIT"
    assert outcome.statistics["expansions"] == 1
    assert outcome.statistics["state_bytes_bound"] < 32 * MIB


@pytest.mark.parametrize("sources", ["identical", "distinct"])
def test_initial_bound_still_covers_the_initial_layouts(sources, monkeypatch):
    p = large_problem(23) if sources == "identical" else with_distinct_sheets(large_problem(3), 3)
    bases, original = [], BeamStateMemory.check_search

    def capture(self, base, children, scratch=0):
        bases.append(tuple(base))
        return original(self, base, children, scratch)
    monkeypatch.setattr(BeamStateMemory, "check_search", capture)
    BeamSearchOptimizer(BeamSearchLimits(max_expansions=1)).run(p)

    stocks, initial = bases[0][1], bases[0][3]
    assert len({id(layout) for layout in initial}) == (1 if sources == "identical" else 3)
    # Owned data of the empty layouts and their rasters (the walk's own scratch
    # is measured by every later check, as in T01), against the bound minus its
    # construction scratch.
    owned = _Walk(None, None)
    owned.path(initial)
    scratch = max(3 * rows * row_bytes(columns) + 65536
                  for columns, rows in (dimensions(s, p.config) for s in stocks))
    assert owned.total <= initial_bound(stocks, p.config) - scratch


def test_native_beam_uses_its_own_state_budget(monkeypatch):
    p = problem([piece(quantity=2, width=2, height=2)], [stock(width=5, height=4)], config())
    monkeypatch.setattr(packing, "RETAINED_LAYOUT_BYTES", 1)
    with pytest.raises(RasterPreparationError, match="128 MiB"):
        FirstFitOptimizer().optimize(p)
    outcome = BeamSearchOptimizer(BeamSearchLimits(max_expansions=1)).run(p)
    assert outcome.stop_reason == "EXPANSION_LIMIT"
    assert outcome.processed == 1
    assert not any(key.startswith("fallback_") for key in outcome.statistics)
