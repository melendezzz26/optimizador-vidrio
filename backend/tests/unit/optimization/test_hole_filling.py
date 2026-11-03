"""TA-042: bounded pocket placement, FF fallback and common engine contracts."""
from dataclasses import replace
from decimal import Decimal as D
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.hole_filling import (
    HoleFillingLimits, HoleFillingOptimizer, HoleFillingSelector, HoleFillingStats,
)
from app.modules.optimization.domain.packing import FeasibleCandidate, _empty_layout, pack
from app.modules.optimization.domain.problem import MaterialSource
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
    p = differentiating_problem()
    optimizer = HoleFillingOptimizer()
    hf, ff = optimizer.optimize(p), FirstFitOptimizer().optimize(p)
    assert hf.complete and ff.complete and hf.placements != ff.placements
    assert optimizer.stats.accepted_pocket and not optimizer.stats.coverage_fallback
    assert_valid(hf)


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
    p = differentiating_problem()
    optimizer = HoleFillingOptimizer()
    events, visual = [], []
    first = optimizer.optimize(p, events.append, on_visual=visual.append)
    second = optimizer.optimize(p)
    assert first.placements == second.placements
    assert [event.placement for event in events if event.kind == "piece_placed"] == list(first.placements)
    assert all(event.score is None for event in visual if event.kind == "source_selected")


@pytest.mark.parametrize("limits", [HoleFillingLimits(max_maps=0), HoleFillingLimits(max_anchors=5),
                                   HoleFillingLimits(max_map_anchors=5)])
def test_hf14_budget_falls_back_before_partial_map(limits):
    candidate = diagnostic_candidate("HF-DIAGNOSTIC-001")
    selector = HoleFillingSelector(limits)
    assert selector.select(iter((candidate,))) == candidate
    assert selector.stats.budget_exhausted and selector.stats.anchors_checked == 0


def test_total_budget_never_exceeds_configured_limits():
    limits = HoleFillingLimits(max_maps=2, max_anchors=880)
    candidate = diagnostic_candidate("HF-DIAGNOSTIC-001")
    selector = HoleFillingSelector(limits)
    for _ in range(4):
        selector.select(iter((candidate,)))
    assert selector.stats.pocket_candidates == 2
    assert selector.stats.anchors_checked == 880
    assert selector.stats.budget_exhausted
    assert selector.stats.placement_checks <= 2 * limits.max_anchors


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


@pytest.mark.parametrize("kwargs", [{"max_maps": -1}, {"max_anchors": True}, {"max_bbox_fraction_denominator": 0}])
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