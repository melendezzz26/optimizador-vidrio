from decimal import Decimal as D
from dataclasses import replace
from unittest.mock import patch

import pytest

from app.modules.optimization.domain.preflight import preflight
from app.modules.optimization.domain.problem import MaterialSource
from app.modules.optimization.domain.rotation import RasterCache
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from tests.unit.optimization.test_first_fit import config, piece, problem, stock


def check(p):
    return preflight(p.groups, p.config)


def test_empty_and_missing_stock():
    assert preflight((), config()).errors[0].code == "EMPTY_ORDER"
    result = check(problem(candidates=[]))
    assert [(e.code, e.piece_id) for e in result.errors] == [("NO_COMPATIBLE_STOCK", 1)]


def test_rotation_margin_and_fallback():
    p = problem([piece(width=4, height=2)], [stock(width=2, height=4)])
    assert check(p).can_optimize
    assert not check(problem([piece(width=4, height=2)], [stock(width=2, height=4)],
                             config(margin_mm=D(1)))).can_optimize
    p = problem([piece(width=4, height=2)], [stock(1, width=1, height=1, source=MaterialSource.REMNANT),
                                               stock(2, width=4, height=2)])
    assert check(p).can_optimize


def test_impossible_piece_is_identified_and_inputs_unchanged():
    p = problem([piece(1, width=2, height=2), piece(2, width=1, height=1), piece(3, width=9, height=9)])
    original = repr(p)
    first = check(p)
    assert [(e.code, e.piece_id) for e in first.errors] == [("PIECE_DOES_NOT_FIT", 3)]
    assert first.affected_piece_ids == (3,) and first == check(p)
    assert repr(p) == original


@pytest.mark.parametrize("candidate", [stock(glass=2), stock(thickness=8)])
def test_material_and_thickness_are_both_required(candidate):
    result = check(problem(candidates=[candidate]))
    assert [(e.code, e.piece_id) for e in result.errors] == [("NO_COMPATIBLE_STOCK", 1)]


def shaped_problem(geometry, width, height):
    p = problem(candidates=[stock(width=width, height=height)], cfg=config(angular_step_deg=D(5)))
    group = p.groups[0]
    unit = replace(group.units[0], geometry=geometry)
    return replace(p, groups=(replace(group, units=(unit,)),))


def test_circle_compatible_and_too_large_has_only_one_orientation():
    circle = dict(type="CIRCUNFERENCIA", radius_mm=2)
    with patch.object(RasterCache, "_orientation", autospec=True, side_effect=RasterCache._orientation) as orient:
        assert check(shaped_problem(circle, 4, 4)).can_optimize
        assert not check(shaped_problem(circle, 3, 3)).can_optimize
        assert orient.call_count == 2


def test_polygon_compatible_too_large_and_rotation():
    triangle = dict(type="POLIGONO_CONVEXO", vertices_mm=[[0, 0], [4, 0], [0, 2]])
    assert check(shaped_problem(triangle, 4, 2)).can_optimize
    assert not check(shaped_problem(triangle, 1, 1)).can_optimize
    assert check(shaped_problem(triangle, 2, 4)).can_optimize


def test_separation_is_not_an_edge_margin():
    p = problem([piece(width=4, height=2)], [stock(width=4, height=2)],
                config(separation_mm=D(10), angular_step_deg=D(5)))
    assert check(p).can_optimize


def test_non_orthogonal_five_degree_orientation():
    p = shaped_problem(dict(type="RECTANGULO", width_mm=9, height_mm=2), 8, 8)
    assert check(p).can_optimize
    assert not check(replace(p, config=replace(p.config, angular_step_deg=D(90)))).can_optimize


def test_preflight_does_not_change_optimizer_result():
    p = problem([piece(width=2, height=2, quantity=2)], [stock(width=6, height=4)])
    before = FirstFitOptimizer().optimize(p)
    assert check(p).can_optimize
    after = FirstFitOptimizer().optimize(p)
    assert after == before
