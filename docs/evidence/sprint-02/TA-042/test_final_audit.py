"""Supplemental checks for TA-042 after the bounded local-search adjustment.

The earlier characterization of the old behavior remains in git at commit
1cff0aa2; these tests no longer assert that the old limitations are acceptable.
"""
from decimal import Decimal as D
import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT)]
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.hole_filling import HoleFillingLimits, HoleFillingOptimizer, HoleFillingSelector
from app.modules.optimization.domain.packing import FeasibleCandidate, _empty_layout
from app.modules.optimization.domain.problem import MaterialSource
from app.modules.optimization.domain.run_geometry import prepare_run_geometry
from tests.unit.optimization.test_first_fit import config, problem, stock
from tests.unit.optimization.test_hole_filling import assert_valid, coverage_problem, product_problem
from tests.unit.optimization.test_preparation import piece


def candidate_with_used_layout(geometry):
    source = stock(width=20, height=20, source=MaterialSource.REMNANT, geometry=geometry)
    p = problem([piece(width=1, height=1)], [source], config(margin_mm=D(0), separation_mm=D(0)))
    prepared = prepare_run_geometry(p)
    orientation = next(iter(prepared.orientations(p.units[0]))).orientation
    layout = _empty_layout(prepared.material(source), p.config)
    layout = layout.place(orientation.mask, *layout.first_position(orientation.mask))
    row, column = layout.first_position(orientation.mask)
    return FeasibleCandidate(stock=source, stock_rank=0, layout=layout, orientation=orientation,
                             orientation_rank=0, row=row, column=column)


@pytest.mark.parametrize("geometry", [
    {"type": "CIRCUNFERENCIA", "radius_mm": 10},
    {"type": "POLIGONO_CONVEXO", "vertices_mm": [[0, 0], [20, 0], [0, 20]]},
])
def test_irregular_usable_boundary_does_not_create_false_pocket(geometry):
    candidate = candidate_with_used_layout(geometry)
    selector = HoleFillingSelector()
    assert selector.select(iter((candidate,))) == candidate
    assert selector.stats.accepted_pocket == 0


@pytest.mark.parametrize("name", ["fallback", "pocket", "budget"])
def test_three_runs_are_deterministic_in_each_path(name):
    p = (problem([piece(width=2, height=2, quantity=3)], [stock(width=5, height=5)])
         if name == "fallback" else product_problem())
    limits = HoleFillingLimits(max_regions=0) if name == "budget" else None
    records = []
    for _ in range(3):
        optimizer = HoleFillingOptimizer(limits)
        result = optimizer.optimize(p)
        records.append((result.placements, optimizer.stats))
    assert records[0] == records[1] == records[2]
    assert (records[0][1].accepted_pocket > 0) == (name == "pocket")
    if name == "budget":
        assert records[0][1].budget_exhausted


def test_coverage_fallback_callbacks_match_only_committed_ff():
    p = coverage_problem()
    initial = repr(p)
    events, visual, baseline_events = [], [], []
    optimizer = HoleFillingOptimizer()
    result = optimizer.optimize(p, events.append, on_visual=visual.append)
    baseline = FirstFitOptimizer().optimize(p, baseline_events.append)
    assert optimizer.stats.coverage_fallback
    assert result.placements == baseline.placements and repr(p) == initial
    assert events == baseline_events
    assert [event.placement for event in visual if event.kind == "source_selected"] == list(baseline.placements)



def test_seeded_capability_complete_and_saves_one_new_sheet():
    path = ROOT / "docs/evidence/sprint-02/TA-042/measure_adjustment.py"
    spec = importlib.util.spec_from_file_location("ta042_adjustment_measurement", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    setup = module.prepare_case("HF-CAPABILITY-001")
    before = repr(setup.problem), repr(setup.layouts)
    hf, stats = module.capability_hf(setup)
    ff = module.seeded_run(setup)
    assert hf.complete and ff.complete and hf.placed_units == ff.placed_units == 18
    assert sum(s.source is MaterialSource.SHEET for s in hf.materials_used) == 0
    assert sum(s.source is MaterialSource.SHEET for s in ff.materials_used) == 1
    placement = next(p for p in hf.placements if p.piece.piece_id == 11)
    assert (placement.x_mm, placement.y_mm, placement.rotation_deg) == (D(51), D(191), D(0))
    assert stats.accepted_pocket and stats.anchors_checked < 1024
    assert (repr(setup.problem), repr(setup.layouts)) == before
    assert_valid(hf)
    assert_valid(ff)
