"""Common functional contracts for the six optimization engines."""
from decimal import Decimal as D

import pytest

from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.best_fit import BestFitOptimizer
from app.modules.optimization.domain.worst_fit import WorstFitOptimizer
from app.modules.optimization.domain.hole_filling import HoleFillingOptimizer
from app.modules.optimization.domain.best_residual_fit import BestResidualFitOptimizer
from app.modules.optimization.domain.beam_search import BeamSearchOptimizer
from tests.unit.optimization.test_first_fit import config, problem, stock
from tests.unit.optimization.test_preparation import piece
from tests.unit.optimization.test_hole_filling import circle, triangle

ENGINES = [FirstFitOptimizer, BestFitOptimizer, WorstFitOptimizer,
           HoleFillingOptimizer, BestResidualFitOptimizer, BeamSearchOptimizer]


def assert_rectangles(result, width, height, margin, separation):
    """Independent bounds and axis-gap oracle for rectangular placements."""
    boxes = []
    for p in result.placements:
        geometry = dict(p.geometry)
        assert geometry['type'] == 'RECTANGULO'
        x, y = D(p.x_mm), D(p.y_mm)
        w, h = D(str(geometry['width_mm'])), D(str(geometry['height_mm']))
        assert x >= margin and y >= margin
        assert x + w <= width - margin and y + h <= height - margin
        assert p.rotation_deg in (D(0), D(90), D(180), D(270))
        for a, b, c, d, source in boxes:
            if source == p.stock.identity:
                assert (x >= c + separation or a >= x + w + separation
                        or y >= d + separation or b >= y + h + separation)
        boxes.append((x, y, x + w, y + h, p.stock.identity))


@pytest.mark.parametrize('engine', ENGINES, ids=['FF', 'BF', 'WF', 'HF', 'M5', 'M6-BS'])
@pytest.mark.parametrize('separation', [D(0), D(1)], ids=['zero-gap', 'one-mm-gap'])
def test_common_geometry_with_margin(engine, separation):
    case = problem([piece(width=2, height=2, quantity=2)], [stock(width=8, height=8)],
                   config(margin_mm=D(1), separation_mm=separation))
    result = engine().optimize(case)
    assert result.complete and result.placed_units == 2
    assert_rectangles(result, D(8), D(8), D(1), separation)


@pytest.mark.parametrize('engine', ENGINES, ids=['FF', 'BF', 'WF', 'HF', 'M5', 'M6-BS'])
def test_required_quarter_turn(engine):
    result = engine().optimize(problem([piece(width=3, height=2)], [stock(width=2, height=3)]))
    assert result.complete and result.placed_units == 1
    assert result.placements[0].rotation_deg in (D(90), D(270))
    assert_rectangles(result, D(2), D(3), D(0), D(0))


@pytest.mark.parametrize('engine', ENGINES, ids=['FF', 'BF', 'WF', 'HF', 'M5', 'M6-BS'])
def test_impossible_piece_is_not_placed(engine):
    result = engine().optimize(problem([piece(width=7, height=7)], [stock(width=6, height=4)]))
    assert not result.complete and result.placed_units == 0 and len(result.unplaced_units) == 1


def test_first_fit_and_best_fit_differ_on_same_sources():
    case = problem([piece(width=2, height=2)],
                   [stock(1, width=6, height=4), stock(2, width=3, height=3)])
    ff = FirstFitOptimizer().optimize(case)
    bf = BestFitOptimizer().optimize(case)
    assert ff.complete and bf.complete
    assert ff.placements[0].stock.material_id == 1
    assert bf.placements[0].stock.material_id == 2


@pytest.mark.parametrize('engine', ENGINES, ids=['FF', 'BF', 'WF', 'HF', 'M5', 'M6-BS'])
def test_mixed_shapes_have_disjoint_bounding_boxes(engine):
    # Conservative independent oracle: disjoint bounding boxes imply no overlap.
    case = problem([piece(1, width=2, height=2), circle(2, 1), triangle(3, 2, 2)],
                   [stock(width=20, height=20)])
    result = engine().optimize(case)
    assert result.complete and result.placed_units == 3
    boxes = []
    for p in result.placements:
        g = dict(p.geometry)
        if g['type'] == 'RECTANGULO':
            w, h = D(str(g['width_mm'])), D(str(g['height_mm']))
        elif g['type'] == 'CIRCUNFERENCIA':
            w = h = 2 * D(str(g['radius_mm']))
        else:
            assert g['type'] == 'POLIGONO_CONVEXO'
            xs, ys = zip(*g['vertices_mm'])
            assert min(xs) == min(ys) == 0
            w, h = D(str(max(xs))), D(str(max(ys)))
        x, y = D(p.x_mm), D(p.y_mm)
        assert x >= 0 and y >= 0 and x + w <= 20 and y + h <= 20
        assert p.rotation_deg in (D(0), D(90), D(180), D(270))
        for a, b, c, d in boxes:
            assert x >= c or a >= x + w or y >= d or b >= y + h
        boxes.append((x, y, x + w, y + h))


def test_beam_finds_a_different_valid_deterministic_layout_than_first_fit():
    # Exploratory fixture discovered with Random(13); this checks reproduction,
    # not an independently predicted optimal packing.
    dimensions = [(3, 2), (2, 4), (2, 1), (1, 3)]
    case = problem([piece(i + 1, width=w, height=h)
                    for i, (w, h) in enumerate(dimensions)], [stock(width=6, height=6)])
    ff = FirstFitOptimizer().optimize(case)
    beam = BeamSearchOptimizer().optimize(case)
    assert ff.complete and beam.complete
    assert beam.placements != ff.placements
    assert beam == BeamSearchOptimizer().optimize(case)
    assert_rectangles(ff, D(6), D(6), D(0), D(0))
    assert_rectangles(beam, D(6), D(6), D(0), D(0))
