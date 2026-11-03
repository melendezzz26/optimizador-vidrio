"""Characterization of review findings; these cases are not acceptance criteria.
Update the documented counterexamples when the implementation is corrected.
"""
from decimal import Decimal as D
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / 'backend'), str(ROOT)]
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.hole_filling import HoleFillingLimits, HoleFillingOptimizer, HoleFillingSelector
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.domain.packing import FeasibleCandidate, _empty_layout
from app.modules.optimization.domain.problem import MaterialSource
from app.modules.optimization.domain.run_geometry import prepare_run_geometry
from experiments.optimization.hole_filling.lab import prepare_case
from tests.unit.optimization.test_first_fit import problem, stock, config
from tests.unit.optimization.test_hole_filling import triangle, circle, assert_valid, differentiating_problem, coverage_problem
from tests.unit.optimization.test_preparation import piece


def candidate_with_used_layout(width=32, height=32, geometry=None):
    src = stock(width=width, height=height, source=MaterialSource.REMNANT, geometry=geometry)
    p = problem([piece(width=1, height=1)], [src], config(margin_mm=D(0), separation_mm=D(0)))
    prepared = prepare_run_geometry(p)
    mask_orientation = next(iter(prepared.orientations(p.units[0]))).orientation
    layout = _empty_layout(prepared.material(src), p.config)
    seed = layout.first_position(mask_orientation.mask)
    layout = layout.place(mask_orientation.mask, *seed)
    pos = layout.first_position(mask_orientation.mask)
    return FeasibleCandidate(stock=src, stock_rank=0, layout=layout, orientation=mask_orientation,
                             orientation_rank=0, row=pos[0], column=pos[1])


def sheet_case():
    rows = [piece(1,width=2,height=2),piece(2,width=4,height=7),piece(3,width=1,height=7),
            piece(4,width=4,height=1),piece(5,width=1,height=5),circle(6,3),triangle(7,4,4),
            triangle(8,5,5),piece(9,width=4,height=6),triangle(10,4,4),piece(11,width=1,height=4),
            triangle(12,7,5),piece(13,width=2,height=7)]
    return problem(rows,[stock(9,width=14,height=14,source=MaterialSource.REMNANT)] +
                        [stock(1,width=18,height=18,physical=n) for n in range(1,4)])


def test_capability32mm_blocked_by_absolute_size_and_even_if_size_raised_by_map_limit():
    s=prepare_case('HF-CAPABILITY-001'); u=s.units_by_id[11]; st=s.stocks_by_id[8201]; layout=s.layouts[st.identity]
    orientation=next(iter(s.prepared.orientations(u))).orientation
    pos=layout.first_position(orientation.mask)
    candidate=FeasibleCandidate(stock=st,stock_rank=0,layout=layout,orientation=orientation,orientation_rank=0,row=pos[0],column=pos[1])
    assert sum(bits.bit_count() for bits in orientation.mask.rows)==1024
    assert (layout.material.columns-31)*(layout.material.row_count-31)==60507
    default=HoleFillingSelector(); assert default.select(iter([candidate]))==candidate
    assert default.stats.activation_attempts==0
    larger=HoleFillingSelector(HoleFillingLimits(max_piece_cells=1024,max_piece_rows=32))
    assert larger.select(iter([candidate]))==candidate
    assert larger.stats.budget_exhausted and larger.stats.anchors_checked==0


@pytest.mark.parametrize('resolution,expected_attempts', [('0.5',0),('1',1),('2',1)])
def test_same_physical_piece_changes_activation_with_resolution(resolution,expected_attempts):
    p=problem([piece(width=8,height=8,quantity=2)],[stock(width=24,height=24)],config(resolution_mm=D(resolution)))
    optimizer=HoleFillingOptimizer(); result=optimizer.optimize(p)
    assert result.complete and optimizer.stats.activation_attempts==expected_attempts


def test_pocket_at_five_degrees_is_not_seen_when_first_ff_orientation_is_zero():
    s=prepare_case('HF-DIAGNOSTIC-001'); st=s.stocks_by_id[901]; unit=s.pending[0]
    layout=_empty_layout(s.prepared.material(st),s.problem.config)
    for pl in s.seed_placements:
        if pl.piece.piece_id not in {1,4,5,6}: continue
        o=next(x.orientation for x in s.prepared.orientations(pl.piece) if x.orientation.rotation_deg==pl.rotation_deg)
        layout=layout.place(o.mask,int(pl.y_mm),int(pl.x_mm))
    selected=[]
    for angle in (0,5):
        o=next(x.orientation for x in s.prepared.orientations(unit) if x.orientation.rotation_deg==angle)
        pos=layout.first_position(o.mask)
        c=FeasibleCandidate(stock=st,stock_rank=0,layout=layout,orientation=o,orientation_rank=0,row=pos[0],column=pos[1])
        selector=HoleFillingSelector(); out=selector.select(iter([c])); selected.append((selector.stats.accepted_pocket,out.row,out.column))
        assert layout.check(o.mask,out.row,out.column).is_valid
    assert selected==[(0,0,0),(1,13,7)]


def test_same_coverage_can_consume_an_extra_sheet_and_worsen_waste():
    p=sheet_case(); before=repr(p); optimizer=HoleFillingOptimizer(); events=[]; visuals=[]
    hf=optimizer.optimize(p,events.append,on_visual=visuals.append); ff=FirstFitOptimizer().optimize(p)
    assert_valid(hf); assert_valid(ff); assert repr(p)==before
    hm,_=calculate_metrics(hf,D(1),D(1)); fm,_=calculate_metrics(ff,D(1),D(1))
    assert hf.complete and ff.complete and hf.placed_units==ff.placed_units==13
    assert (hm.metrics.new_sheets_used,fm.metrics.new_sheets_used)==(1,0)
    assert hm.metrics.waste_mm2 > fm.metrics.waste_mm2
    assert optimizer.stats.accepted_pocket and not optimizer.stats.coverage_fallback
    assert [e.placement for e in events if e.kind=='piece_placed']==list(hf.placements)
    assert len([e for e in visuals if e.kind=='source_selected'])==13
    assert all(e.score is None for e in visuals if e.kind=='source_selected')


def test_exact_map_and_total_budgets_then_rejection_without_extra_checks():
    c=candidate_with_used_layout(); selector=HoleFillingSelector()
    for _ in range(8): selector.select(iter([c]))
    assert selector.stats.pocket_candidates==8 and selector.stats.anchors_checked==8192
    assert selector.stats.placement_checks==16384 and not selector.stats.budget_exhausted
    assert selector.select(iter([c]))==c
    assert selector.stats.budget_exhausted and selector.stats.anchors_checked==8192


def test_map_over_1024_is_never_partially_evaluated():
    c=candidate_with_used_layout(33,32); selector=HoleFillingSelector()
    assert selector.select(iter([c]))==c
    assert selector.stats.budget_exhausted and selector.stats.anchors_checked==0


@pytest.mark.parametrize('geometry', [
    {'type':'CIRCUNFERENCIA','radius_mm':10},
    {'type':'POLIGONO_CONVEXO','vertices_mm':[[0,0],[20,0],[0,20]]},
])
def test_irregular_usable_boundary_does_not_create_false_pocket(geometry):
    c=candidate_with_used_layout(20,20,geometry); selector=HoleFillingSelector()
    assert selector.select(iter([c]))==c
    assert selector.stats.pocket_candidates==1 and selector.stats.accepted_pocket==0


@pytest.mark.parametrize('name', ['fallback','pocket','budget'])
def test_three_runs_are_deterministic_in_each_path(name):
    p=problem([piece(width=2,height=2,quantity=3)],[stock(width=5,height=5)]) if name=='fallback' else differentiating_problem()
    limits=HoleFillingLimits(max_maps=0) if name=='budget' else None
    records=[]
    for _ in range(3):
        opt=HoleFillingOptimizer(limits); result=opt.optimize(p); records.append((result.placements,opt.stats))
    assert records[0]==records[1]==records[2]
    assert (records[0][1].accepted_pocket>0)==(name=='pocket')
    assert records[0][1].budget_exhausted==(name=='budget')


def test_coverage_fallback_callbacks_match_only_committed_ff():
    p=coverage_problem(); initial=repr(p); ev=[]; vis=[]; baseline_ev=[]
    opt=HoleFillingOptimizer(); out=opt.optimize(p,ev.append,on_visual=vis.append)
    ff=FirstFitOptimizer().optimize(p,baseline_ev.append)
    assert opt.stats.coverage_fallback and out.placements==ff.placements and repr(p)==initial
    assert ev==baseline_ev
    assert [e.placement for e in vis if e.kind=='source_selected']==list(ff.placements)
