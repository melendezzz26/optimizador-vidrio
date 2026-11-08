"""M6-01: shared objects, reservation before allocation and durable frontiers."""
from dataclasses import replace

import pytest

from app.modules.optimization.domain.beam_memory import (
    BeamStateMemory, StateMemoryLimit, graph_bytes, initial_bound,
)
from app.modules.optimization.domain.beam_search import BeamSearchLimits, BeamSearchOptimizer
from app.modules.optimization.domain.problem import (
    MaterialGroup, MaterialSource, OptimizationConfig, OptimizationProblem,
    PieceUnit, StockCandidate,
)


def large_problem(sources=1, count=1):
    piece = PieceUnit(order_id=1, piece_id=1, unit_index=1, glass_type_id=1,
                      thickness_mm=6, geometry=dict(type="RECTANGULO", width_mm=600,
                      height_mm=800), area_mm2=480000)
    stock = StockCandidate(source=MaterialSource.SHEET, material_id=1,
                           physical_unit_index=1, glass_type_id=1, thickness_mm=6,
                           geometry=dict(type="RECTANGULO", width_mm=2140,
                                         height_mm=3300), area_mm2=7062000)
    return OptimizationProblem(order_ids=(1,), config=OptimizationConfig(
        resolution_mm=1, margin_mm=3, separation_mm=3, angular_step_deg=5),
        groups=(MaterialGroup(glass_type_id=1, thickness_mm=6,
            units=tuple(replace(piece, unit_index=i+1) for i in range(count)),
            stock_candidates=tuple(replace(stock, physical_unit_index=i+1)
                                   for i in range(sources))),))


def test_shared_graph_is_charged_once_including_nested_integer_rows():
    rows = tuple((1 << 2000) + i for i in range(1000))
    assert graph_bytes((rows,) * 20) < graph_bytes((rows,)) + 1000
    separate = tuple(tuple((1 << 2000) + i for i in range(1000)) for _ in range(2))
    assert graph_bytes(separate) > 1.8 * graph_bytes((rows,))


@pytest.mark.parametrize("sources", (1, 8))
def test_large_sources_are_admitted_without_raising_defaults(sources):
    outcome = BeamSearchOptimizer(BeamSearchLimits(max_expansions=1)).run(
        large_problem(sources))
    assert outcome.stop_reason == "EXPANSION_LIMIT"
    assert outcome.statistics["expansions"] == 1
    assert 0 < outcome.statistics["state_bytes_peak"] <= 32 * 1024 * 1024


def test_genuinely_oversized_initial_sources_stop_before_raster_allocation(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("oversized state must be rejected before preparing rasters")
    monkeypatch.setattr("app.modules.optimization.domain.beam_search.prepare_run_geometry", forbidden)
    # S2-M6: identical sources share one empty layout, so the 50 sources need
    # 50 distinct rasters to remain genuinely oversized.
    problem = large_problem(50)
    group = problem.groups[0]
    distinct = tuple(replace(stock, geometry=dict(type="RECTANGULO", width_mm=2140 - i, height_mm=3300),
                             area_mm2=(2140 - i) * 3300)
                     for i, stock in enumerate(group.stock_candidates))
    problem = replace(problem, groups=(replace(group, stock_candidates=distinct),))
    outcome = BeamSearchOptimizer(BeamSearchLimits()).run(problem)
    assert outcome.stop_reason == "STATE_MEMORY_LIMIT"
    assert outcome.processed == outcome.result.placed_units == 0
    assert outcome.statistics["state_bytes_bound"] > 32 * 1024 * 1024
    assert outcome.statistics["state_bytes_peak"] == 0


def test_memory_limit_does_not_replace_last_completed_frontier(monkeypatch):
    problem = large_problem(count=2)
    # One orientation keeps this focused on reservation, rather than timing.
    problem = replace(problem, config=replace(problem.config, angular_step_deg=360))
    # S2-M6: search-time checks use check_search; both paths end in reserve().
    original = BeamStateMemory.reserve
    completed = []
    def stop_after_first_level(self, amount):
        if completed:
            raise StateMemoryLimit()
        return original(self, amount)
    monkeypatch.setattr(BeamStateMemory, "reserve", stop_after_first_level)
    outcome = BeamSearchOptimizer(BeamSearchLimits()).run(problem, on_progress=lambda p:
        completed.append(p.completed_levels) if p.completed_levels == 1 else None)
    assert outcome.stop_reason == "STATE_MEMORY_LIMIT"
    assert outcome.processed == outcome.result.placed_units == 1
    assert len(outcome.trace) == 1


def test_accounting_rejects_actual_graph_larger_than_32_mib():
    rows = tuple(tuple((1 << 4000) + i for i in range(4000)) for _ in range(16))
    memory = BeamStateMemory(32 * 1024 * 1024)
    assert graph_bytes(rows) > memory.maximum
    with pytest.raises(StateMemoryLimit):
        memory.check(rows)
    assert memory.peak == 0


def test_material_and_thickness_incompatibility_is_still_rejected():
    group = large_problem().groups[0]
    for incompatible in (replace(group.stock_candidates[0], glass_type_id=2),
                         replace(group.stock_candidates[0], thickness_mm=8)):
        with pytest.raises(ValueError, match="match the material group"):
            replace(group, stock_candidates=(incompatible,))


def test_initial_bound_uses_the_raster_cache_key_for_translated_polygons():
    problem = large_problem(16)
    original = problem.groups[0].stock_candidates
    stocks = tuple(replace(s, source=MaterialSource.REMNANT, material_id=i+1,
        physical_unit_index=1, geometry=dict(type="POLIGONO_CONVEXO",
            vertices_mm=((i,0),(2140+i,0),(2140+i,3300),(i,3300)))) for i,s in enumerate(original))
    normalized = tuple(replace(s, geometry=stocks[0].geometry) for s in stocks)
    assert initial_bound(stocks, problem.config) == initial_bound(normalized, problem.config)
    assert initial_bound(stocks, problem.config) < 32 * 1024 * 1024


def test_accounting_walk_keeps_cancellation_checkpoints():
    def cancelled():
        raise RuntimeError("cancelled")
    with pytest.raises(RuntimeError, match="cancelled"):
        BeamStateMemory(32 * 1024 * 1024, checkpoint=cancelled).check(((0,) * 4000,))
