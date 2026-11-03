"""TA-042: bounded pocket placement, FF fallback and common engine contracts."""
from collections import deque
from dataclasses import replace
from decimal import Decimal as D
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.hole_filling import (
    HoleFillingLimits, HoleFillingOptimizer, HoleFillingSelector, HoleFillingStats, _fallback_reason,
)
from app.modules.optimization.domain.packing import FeasibleCandidate, _empty_layout, pack
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.domain.problem import MaterialSource
from app.modules.optimization.domain.placement import PlacementIssue
from app.modules.optimization.domain.run_geometry import prepare_run_geometry
from experiments.optimization.hole_filling.lab import prepare_case
from tests.unit.optimization.test_first_fit import config, problem, stock
from tests.unit.optimization.test_preparation import piece


def triangle(identifier, width, height):
    return piece(identifier, area=str(width * height / 2)) | {
        "tipo_forma": "POLIGONO_CONVEXO",
        "geometria": {"type": "POLIGONO_CONVEXO", "vertices_mm": [[0, 0], [width, 0], [0, height]]},
    }


def circle(identifier, radius):
    return piece(identifier, area=str(3.14 * radius * radius)) | {
        "tipo_forma": "CIRCUNFERENCIA", "geometria": {"type": "CIRCUNFERENCIA", "radius_mm": radius},
    }


def differentiating_problem():
    rows = [triangle(1, 6, 5), piece(2, width=5, height=5), piece(3, width=3, height=4),
            circle(4, 2), circle(5, 4), triangle(6, 3, 8), piece(7, width=2, height=1),
            triangle(8, 3, 4), circle(9, 3)]
    return problem(rows, [stock(width=18, height=18, physical=i) for i in range(1, 4)])


def product_problem():
    # Deterministically discovered mixed geometry case; units in mm.
    rows = [circle(1, 11), triangle(2, 36, 13), circle(3, 11), circle(4, 5),
            triangle(5, 30, 16), circle(6, 11), piece(7, width=22, height=23)]
    return problem(rows, [stock(width=80, height=80, physical=i) for i in range(1, 4)],
                   config(angular_step_deg=D(5)))


def sheet_problem():
    rows = [piece(1, width=2, height=2), piece(2, width=4, height=7), piece(3, width=1, height=7),
            piece(4, width=4, height=1), piece(5, width=1, height=5), circle(6, 3), triangle(7, 4, 4),
            triangle(8, 5, 5), piece(9, width=4, height=6), triangle(10, 4, 4),
            piece(11, width=1, height=4), triangle(12, 7, 5), piece(13, width=2, height=7)]
    return problem(rows, [stock(9, width=14, height=14, source=MaterialSource.REMNANT)] +
                   [stock(1, width=18, height=18, physical=i) for i in range(1, 4)])


def coverage_problem():
    rows = [triangle(1, 8, 5), piece(2, width=3, height=1), triangle(3, 3, 4),
            piece(4, width=2, height=2), piece(5, width=2, height=5), triangle(6, 5, 5),
            triangle(7, 6, 3), circle(8, 4), piece(9, width=2, height=5), triangle(10, 6, 3),
            circle(11, 4), piece(12, width=1, height=1), circle(13, 4),
            piece(14, width=2, height=2), circle(15, 3), piece(16, width=2, height=2)]
    return problem(rows, [stock(width=18, height=18)])


def diagnostic_candidate(case_id):
    setup = prepare_case(case_id)
    source = setup.problem.groups[0].stock_candidates[0]
    layout = setup.layouts[source.identity]
    orientation = next(iter(setup.prepared.orientations(setup.pending[0]))).orientation
    row, col = layout.first_position(orientation.mask)
    return FeasibleCandidate(stock=source, stock_rank=0, layout=layout, orientation=orientation,
                             orientation_rank=0, row=row, column=col)


def assert_valid(result):
    prepared = prepare_run_geometry(result.problem)
    layouts = {}
    for placement in result.placements:
        layout = layouts.get(placement.stock.identity)
        if layout is None:
            layout = _empty_layout(prepared.material(placement.stock), result.problem.config)
        orientation = next(item.orientation for item in prepared.orientations(placement.piece)
                           if item.orientation.rotation_deg == placement.rotation_deg)
        row = int(placement.y_mm / result.problem.config.resolution_mm)
        column = int(placement.x_mm / result.problem.config.resolution_mm)
        assert placement.piece.material_key == placement.stock.material_key
        assert layout.check(orientation.mask, row, column).is_valid
        layouts[placement.stock.identity] = layout.place(orientation.mask, row, column)


def assert_pocket_connected_component_is_interior(result, target):
    """Independently traverse the selected component on the pre-placement layout."""
    prepared = prepare_run_geometry(result.problem)
    layout = _empty_layout(prepared.material(target.stock), result.problem.config)
    for placement in result.placements:
        if placement == target:
            break
        if placement.stock.identity != target.stock.identity:
            continue
        orientation = next(item.orientation for item in prepared.orientations(placement.piece)
                           if item.orientation.rotation_deg == placement.rotation_deg)
        layout = layout.place(orientation.mask, int(placement.y_mm), int(placement.x_mm))
    mask = next(item.orientation.mask for item in prepared.orientations(target.piece)
                if item.orientation.rotation_deg == target.rotation_deg)
    start = (int(target.y_mm), int(target.x_mm))
    queue, seen = deque((start,)), {start}
    while queue:
        row, column = queue.popleft()
        for neighbor in ((row - 1, column), (row + 1, column), (row, column - 1), (row, column + 1)):
            if neighbor in seen:
                continue
            check = layout.check(mask, *neighbor)
            assert check.issue not in (PlacementIssue.MARGIN, PlacementIssue.OUT_OF_BOUNDS)
            if check.is_valid:
                seen.add(neighbor)
                queue.append(neighbor)
    assert seen


def test_hf01_no_pocket_is_exact_ff_fallback():
    p = problem([piece(width=2, height=2, quantity=3)], [stock(width=5, height=5)])
    optimizer = HoleFillingOptimizer()
    hf = optimizer.optimize(p)
    ff = FirstFitOptimizer().optimize(p)
    assert hf.placements == ff.placements
    assert optimizer.stats.accepted_pocket == 0 and optimizer.stats.fallback_used


@pytest.mark.parametrize("case_id", ["HF-DIAGNOSTIC-001", "HF-DIAGNOSTIC-002", "HF-DIAGNOSTIC-003"])
def test_hf02_pocket_is_legal_and_differs_from_ff_on_circle_and_polygon(case_id):
    candidate = diagnostic_candidate(case_id)
    selector = HoleFillingSelector()
    winner = selector.select(iter((candidate,)))
    assert (winner.row, winner.column) != (candidate.row, candidate.column)
    assert winner.layout.check(winner.orientation.mask, winner.row, winner.column).is_valid
    assert selector.stats.accepted_pocket == 1
    assert selector.stats.anchors_checked <= 1024


def test_hf03_real_optimizer_uses_pocket_and_differs_from_ff():
    p = product_problem()
    optimizer = HoleFillingOptimizer()
    hf, ff = optimizer.optimize(p), FirstFitOptimizer().optimize(p)
    assert hf.complete and ff.complete and hf.placements != ff.placements
    assert optimizer.stats.accepted_pocket and not optimizer.stats.coverage_fallback
    assert not optimizer.stats.sheet_fallback
    assert len(hf.materials_used) == len(ff.materials_used) == 1
    pocket = next(placement for placement in hf.placements if placement.piece.piece_id == 4)
    assert pocket.piece.geometry["radius_mm"] == 5
    assert (pocket.x_mm, pocket.y_mm) == (47, 24)
    assert_valid(hf)
    assert_pocket_connected_component_is_interior(hf, pocket)


def test_hf06_rectangles_fallback_without_pocket():
    p = problem([piece(width=2, height=2, quantity=4)], [stock(width=4, height=4)])
    assert HoleFillingOptimizer().optimize(p).placements == FirstFitOptimizer().optimize(p).placements


def test_hf07_five_degree_grid_allows_non_quarter_turn():
    p = problem([piece(width=6, height=1)], [stock(width=5, height=5)], config(angular_step_deg=D(5)))
    result = HoleFillingOptimizer().optimize(p)
    assert result.complete
    assert result.placements[0].rotation_deg % D(5) == 0
    assert result.placements[0].rotation_deg % D(90) != 0
    assert_valid(result)


def test_hf08_separation_and_hf09_margin():
    p = problem([piece(width=2, height=2, quantity=2)], [stock(width=7, height=4)],
                config(margin_mm=D(1), separation_mm=D(1)))
    result = HoleFillingOptimizer().optimize(p)
    assert result.complete
    assert [(p.x_mm, p.y_mm) for p in result.placements] == [(1, 1), (4, 1)]
    assert_valid(result)


def test_margin_does_not_make_all_interior_anchors_pockets():
    p = problem([piece(width=2, height=2), piece(2, width=1, height=1)],
                [stock(width=10, height=10)], config(margin_mm=D(1)))
    optimizer = HoleFillingOptimizer()
    hf = optimizer.optimize(p)
    assert hf.placements == FirstFitOptimizer().optimize(p).placements
    assert optimizer.stats.accepted_pocket == 0


def test_hf10_hf11_material_and_thickness_remain_grouped():
    rows = [piece(1, glass=2), piece(2, thickness="5.5"), piece(3)]
    sources = [stock(1, glass=2), stock(2, thickness="5.5"), stock(3)]
    result = HoleFillingOptimizer().optimize(problem(rows, sources))
    assert result.complete
    assert {p.piece.material_key for p in result.placements} == {(2, D(6)), (1, D("5.5")), (1, D(6))}
    assert_valid(result)


def test_hf12_remnant_precedes_sheet_and_incompatible_remnant_falls_back():
    p = problem([piece(width=2, height=2, quantity=2)],
                [stock(1, width=2, height=2), stock(2, width=2, height=2, source=MaterialSource.REMNANT)])
    result = HoleFillingOptimizer().optimize(p)
    assert [placement.stock.source for placement in result.placements] == [MaterialSource.REMNANT, MaterialSource.SHEET]
    assert_valid(result)


def test_hf13_deterministic_and_replay_events_describe_selected_result():
    p = product_problem()
    optimizer = HoleFillingOptimizer()
    events, visual = [], []
    first = optimizer.optimize(p, events.append, on_visual=visual.append)
    assert optimizer.stats.accepted_pocket and not optimizer.stats.sheet_fallback
    second = optimizer.optimize(p)
    assert first.placements == second.placements
    assert [event.placement for event in events if event.kind == "piece_placed"] == list(first.placements)
    assert all(event.score is None for event in visual if event.kind == "source_selected")


@pytest.mark.parametrize("limits", [HoleFillingLimits(max_regions=0), HoleFillingLimits(max_anchors=0),
                                   HoleFillingLimits(max_seed_probes=0)])
def test_hf14_budget_falls_back_safely(limits):
    candidate = diagnostic_candidate("HF-DIAGNOSTIC-001")
    selector = HoleFillingSelector(limits)
    assert selector.select(iter((candidate,))) == candidate
    assert selector.stats.budget_exhausted
    assert selector.stats.anchors_checked <= limits.max_anchors
    assert selector.stats.pocket_candidates <= limits.max_regions


def test_total_budget_never_exceeds_configured_limits():
    limits = HoleFillingLimits(max_regions=2, max_anchors=20)
    candidate = diagnostic_candidate("HF-DIAGNOSTIC-001")
    selector = HoleFillingSelector(limits)
    for _ in range(4):
        selector.select(iter((candidate,)))
    assert selector.stats.pocket_candidates <= 2
    assert selector.stats.anchors_checked <= 20
    assert selector.stats.budget_exhausted
    assert selector.stats.placement_checks == selector.stats.anchors_checked


def test_hf15_problem_and_input_stock_are_not_mutated():
    p = differentiating_problem()
    before = repr(p)
    HoleFillingOptimizer().optimize(p)
    assert repr(p) == before


def test_hf16_coverage_guard_rolls_back_real_harmful_pocket_sequence():
    p = coverage_problem()
    selector = HoleFillingSelector()
    trial = pack(p, select=selector.select)
    ff = FirstFitOptimizer().optimize(p)
    assert selector.stats.accepted_pocket > 0
    assert {x.piece.identity for x in ff.placements} - {x.piece.identity for x in trial.placements}
    optimizer = HoleFillingOptimizer()
    hf = optimizer.optimize(p)
    assert optimizer.stats.coverage_fallback
    assert hf.placements == ff.placements
    assert_valid(hf)


def test_coverage_guard_replays_only_committed_ff_events():
    p = coverage_problem()
    optimizer = HoleFillingOptimizer()
    events = []
    result = optimizer.optimize(p, events.append)
    assert optimizer.stats.coverage_fallback
    assert [event.placement for event in events if event.kind == "piece_placed"] == list(result.placements)


@pytest.mark.parametrize("kwargs", [{"max_regions": -1}, {"max_anchors": True}, {"max_bbox_fraction_denominator": 0}])
def test_limits_reject_invalid_values(kwargs):
    with pytest.raises(ValueError):
        HoleFillingLimits(**kwargs)


def test_hf16_coverage_guard_prevents_a_lower_placed_count():
    # Heterogeneous constrained stock, inspired by HF-REALISTIC-003. This is a
    # separate small fixture, not a claim about that experiment's measurements.
    rows = [piece(1, width=1, height=1), triangle(2, 7, 7), triangle(3, 8, 4),
            triangle(4, 3, 5), circle(5, 4), circle(6, 3), circle(7, 3), circle(8, 2),
            circle(9, 4), triangle(10, 3, 4), triangle(11, 5, 7), circle(12, 3),
            circle(13, 4), circle(14, 3), circle(15, 3), piece(16, width=1, height=5),
            piece(17, width=2, height=4), piece(18, width=3, height=2)]
    p = problem(rows, [stock(width=18, height=18)])
    selector = HoleFillingSelector()
    trial = pack(p, select=selector.select)
    ff = FirstFitOptimizer().optimize(p)
    optimizer = HoleFillingOptimizer()
    hf = optimizer.optimize(p)
    assert (trial.placed_units, ff.placed_units, hf.placed_units) == (10, 11, 11)
    assert optimizer.stats.coverage_fallback and hf.placements == ff.placements
    assert_valid(hf)


def test_capability_32mm_uses_certified_local_pocket_without_global_map():
    setup = prepare_case("HF-CAPABILITY-001")
    source = setup.stocks_by_id[8201]
    layout = setup.layouts[source.identity]
    view = setup.prepared.orientations(setup.units_by_id[11])
    orientation = next(iter(view)).orientation
    row, column = layout.first_position(orientation.mask)
    candidate = FeasibleCandidate(stock=source, stock_rank=0, layout=layout, orientation=orientation,
                                  orientation_rank=0, row=row, column=column, orientations=view)
    selector = HoleFillingSelector()
    selected = selector.select(iter((candidate,)))
    assert (selected.row, selected.column, selected.orientation.rotation_deg) == (191, 51, D(0))
    assert layout.check(selected.orientation.mask, selected.row, selected.column).is_valid
    assert selector.stats.accepted_pocket == 1
    assert selector.stats.anchors_checked < 1024 < 60507


def test_local_partial_region_falls_back_if_cannot_certify_connectivity():
    setup = prepare_case("HF-CAPABILITY-001")
    source = setup.stocks_by_id[8201]
    layout = setup.layouts[source.identity]
    orientation = next(iter(setup.prepared.orientations(setup.units_by_id[11]))).orientation
    row, column = layout.first_position(orientation.mask)
    candidate = FeasibleCandidate(stock=source, stock_rank=0, layout=layout, orientation=orientation,
                                  orientation_rank=0, row=row, column=column)
    selector = HoleFillingSelector(HoleFillingLimits(max_region_checks=5))
    assert selector.select(iter((candidate,))) == candidate
    assert selector.stats.anchors_checked > 0 and selector.stats.budget_exhausted
    assert selector.stats.accepted_pocket == 0


def test_bounded_following_angle_finds_five_degree_pocket():
    setup = prepare_case("HF-DIAGNOSTIC-001")
    source = setup.stocks_by_id[901]
    layout = _empty_layout(setup.prepared.material(source), setup.problem.config)
    for placement in setup.seed_placements:
        if placement.piece.piece_id not in {1, 4, 5, 6}:
            continue
        orientation = next(item.orientation for item in setup.prepared.orientations(placement.piece)
                           if item.orientation.rotation_deg == placement.rotation_deg)
        layout = layout.place(orientation.mask, int(placement.y_mm), int(placement.x_mm))
    view = setup.prepared.orientations(setup.pending[0])
    first = next(iter(view)).orientation
    row, column = layout.first_position(first.mask)
    candidate = FeasibleCandidate(stock=source, stock_rank=0, layout=layout, orientation=first,
                                  orientation_rank=0, row=row, column=column, orientations=view)
    only_ff = HoleFillingSelector(HoleFillingLimits(max_orientations=1))
    assert only_ff.select(iter((candidate,))) == candidate
    selector = HoleFillingSelector()
    selected = selector.select(iter((candidate,)))
    assert selected.orientation.rotation_deg == 5
    assert (selected.row, selected.column) == (13, 7)
    assert layout.check(selected.orientation.mask, selected.row, selected.column).is_valid
    assert selector.stats.orientations_inspected == 2


@pytest.mark.parametrize("resolution", [D("0.5"), D(1), D(2)])
def test_relative_activation_is_not_absolute_64_cell_cutoff(resolution):
    p = problem([piece(width=8, height=8, quantity=2)], [stock(width=24, height=24)],
                config(resolution_mm=resolution))
    optimizer = HoleFillingOptimizer()
    assert optimizer.optimize(p).complete
    assert optimizer.stats.activation_attempts > 0
    assert optimizer.stats.orientations_inspected > 0
    assert optimizer.stats.anchors_checked > 0


def test_equal_coverage_more_sheets_restores_ff_and_callbacks():
    p = sheet_problem()
    assert HoleFillingOptimizer().optimize(p).placements == FirstFitOptimizer().optimize(p).placements
    # The same counterexample needs 19 local regions in this search policy.
    limits = HoleFillingLimits(max_regions=24)
    selector = HoleFillingSelector(limits)
    trial = pack(p, select=selector.select)
    ff_events, events, visuals = [], [], []
    baseline = FirstFitOptimizer().optimize(p, ff_events.append)
    assert trial.complete and baseline.complete
    assert sum(s.source is MaterialSource.SHEET for s in trial.materials_used) == 1
    assert sum(s.source is MaterialSource.SHEET for s in baseline.materials_used) == 0
    before = repr(p)
    optimizer = HoleFillingOptimizer(limits)
    final = optimizer.optimize(p, events.append, on_visual=visuals.append)
    assert optimizer.stats.sheet_fallback and not optimizer.stats.coverage_fallback
    assert final.placements == baseline.placements and repr(p) == before
    assert events == ff_events
    assert [e.placement for e in visuals if e.kind == "source_selected"] == list(baseline.placements)
    assert_valid(final)


def test_strict_coverage_superset_may_use_additional_sheet():
    def fake(ids, sheet_count):
        placements = [SimpleNamespace(piece=SimpleNamespace(identity=(i, 1))) for i in ids]
        stocks = [SimpleNamespace(source=MaterialSource.SHEET) for _ in range(sheet_count)]
        return SimpleNamespace(placements=placements, materials_used=stocks)
    baseline = fake([1], 0)
    assert _fallback_reason(fake([1, 2], 1), baseline) is None
    assert _fallback_reason(fake([1], 1), baseline) == "sheets"
    assert _fallback_reason(fake([2], 0), baseline) == "coverage"


def test_operation_limits_hold_for_local_search():
    p = product_problem()
    limits = HoleFillingLimits(max_regions=2, max_region_checks=20, max_anchors=100,
                               max_check_rows=2000, max_seed_probes=30,
                               max_seeds_per_orientation=15, max_boundary_rows=32,
                               max_edges_per_row=8, max_orientations=2,
                               max_orientation_evaluations=4)
    optimizer = HoleFillingOptimizer(limits)
    result = optimizer.optimize(p)
    stats = optimizer.stats
    assert_valid(result)
    assert stats.pocket_candidates <= limits.max_regions
    assert stats.max_region_checks_observed <= limits.max_region_checks
    assert stats.max_region_anchors_observed <= limits.max_region_anchors
    assert stats.anchors_checked <= limits.max_anchors
    assert stats.placement_checks == stats.anchors_checked
    assert stats.check_rows <= limits.max_check_rows
    assert stats.seed_probes <= limits.max_seed_probes
    assert stats.orientations_inspected <= limits.max_orientation_evaluations
    assert stats.boundary_rows <= limits.max_boundary_rows * stats.orientations_inspected



def test_equivalent_masks_are_not_reexamined_as_distinct_orientations():
    p = problem([piece(width=2, height=2, quantity=2)], [stock(width=12, height=12)])
    prepared = prepare_run_geometry(p)
    source = p.groups[0].stock_candidates[0]
    view = prepared.orientations(p.units[0])
    orientation = next(iter(view)).orientation
    layout = _empty_layout(prepared.material(source), p.config)
    layout = layout.place(orientation.mask, 0, 0)
    row, column = layout.first_position(orientation.mask)
    candidate = FeasibleCandidate(stock=source, stock_rank=0, layout=layout, orientation=orientation,
                                  orientation_rank=0, row=row, column=column, orientations=view)
    selector = HoleFillingSelector()
    selector.select(iter((candidate,)))
    assert selector.stats.orientations_inspected == 1



def test_exact_global_and_seed_limits_do_not_overrun():
    setup = prepare_case("HF-CAPABILITY-001")
    source = setup.stocks_by_id[8201]
    layout = setup.layouts[source.identity]
    orientation = next(iter(setup.prepared.orientations(setup.units_by_id[11]))).orientation
    row, column = layout.first_position(orientation.mask)
    candidate = FeasibleCandidate(stock=source, stock_rank=0, layout=layout, orientation=orientation,
                                  orientation_rank=0, row=row, column=column)
    exact = HoleFillingSelector(HoleFillingLimits(max_anchors=121, max_check_rows=3872,
                                                   max_seed_probes=25))
    selected = exact.select(iter((candidate,)))
    assert (selected.row, selected.column) == (191, 51)
    assert (exact.stats.anchors_checked, exact.stats.check_rows, exact.stats.seed_probes) == (121, 3872, 25)
    limited = HoleFillingSelector(HoleFillingLimits(max_anchors=120, max_check_rows=3872))
    assert limited.select(iter((candidate,))) == candidate
    assert limited.stats.anchors_checked == 120 and limited.stats.budget_exhausted


def test_region_limit_rejects_next_region_without_scanning_it():
    candidate = diagnostic_candidate("HF-DIAGNOSTIC-001")
    selector = HoleFillingSelector(HoleFillingLimits(max_regions=2))
    selector.select(iter((candidate,)))
    selector.select(iter((candidate,)))
    before = selector.stats.anchors_checked
    assert selector.stats.pocket_candidates == 2
    assert selector.select(iter((candidate,))) == candidate
    assert selector.stats.anchors_checked == before and selector.stats.budget_exhausted



def test_equal_sheets_and_coverage_do_not_force_a_waste_comparison():
    # Deterministically discovered case: worse residual is documented, not a new guard.
    rows = [piece(1, width=20, height=8), piece(2, width=9, height=30), triangle(3, 13, 19),
            triangle(4, 17, 11), circle(5, 14), piece(6, width=29, height=31), circle(7, 6),
            piece(8, width=17, height=18), triangle(9, 15, 18), piece(10, width=19, height=10),
            circle(11, 14), triangle(12, 16, 11), triangle(13, 23, 23), triangle(14, 32, 31),
            piece(15, width=21, height=29)]
    p = problem(rows, [stock(width=80, height=80, physical=i) for i in range(1, 4)],
                config(angular_step_deg=D(5)))
    optimizer = HoleFillingOptimizer()
    hf = optimizer.optimize(p)
    ff = FirstFitOptimizer().optimize(p)
    hf_metrics = calculate_metrics(hf, D(1), D(1))[0].metrics
    ff_metrics = calculate_metrics(ff, D(1), D(1))[0].metrics
    assert hf.complete and ff.complete and hf.placed_units == ff.placed_units == 15
    assert hf_metrics.new_sheets_used == ff_metrics.new_sheets_used == 2
    assert hf_metrics.waste_mm2 - ff_metrics.waste_mm2 == 62
    assert ff_metrics.recoverable_remnant_mm2 - hf_metrics.recoverable_remnant_mm2 == 62
    assert optimizer.stats.accepted_pocket and not optimizer.stats.sheet_fallback
    assert_valid(hf)



@pytest.mark.parametrize("denominator,expected", [(4, True), (8, True), (16, True),
                                                   (32, True), (64, True), (128, False)])
def test_relative_threshold_sensitivity_on_capability(denominator, expected):
    setup = prepare_case("HF-CAPABILITY-001")
    source = setup.stocks_by_id[8201]
    layout = setup.layouts[source.identity]
    orientation = next(iter(setup.prepared.orientations(setup.units_by_id[11]))).orientation
    row, column = layout.first_position(orientation.mask)
    candidate = FeasibleCandidate(stock=source, stock_rank=0, layout=layout, orientation=orientation,
                                  orientation_rank=0, row=row, column=column)
    selector = HoleFillingSelector(HoleFillingLimits(max_bbox_fraction_denominator=denominator))
    selector.select(iter((candidate,)))
    assert bool(selector.stats.accepted_pocket) is expected



def test_exact_local_component_anchor_limit():
    setup = prepare_case("HF-CAPABILITY-001")
    source = setup.stocks_by_id[8201]
    layout = setup.layouts[source.identity]
    orientation = next(iter(setup.prepared.orientations(setup.units_by_id[11]))).orientation
    row, column = layout.first_position(orientation.mask)
    candidate = FeasibleCandidate(stock=source, stock_rank=0, layout=layout, orientation=orientation,
                                  orientation_rank=0, row=row, column=column)
    exact = HoleFillingSelector(HoleFillingLimits(max_region_anchors=60))
    selected = exact.select(iter((candidate,)))
    assert (selected.row, selected.column) == (191, 51)
    assert exact.stats.max_region_anchors_observed == 60
    limited = HoleFillingSelector(HoleFillingLimits(max_region_anchors=59))
    assert limited.select(iter((candidate,))) == candidate
    assert limited.stats.max_region_anchors_observed == 59
    assert limited.stats.budget_exhausted
