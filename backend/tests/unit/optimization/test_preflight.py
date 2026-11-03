from decimal import Decimal as D

from app.modules.optimization.domain.preflight import preflight
from app.modules.optimization.domain.problem import MaterialSource
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
    p = problem([piece(1, width=2, height=2), piece(3, width=9, height=9)])
    original = repr(p)
    first = check(p)
    assert [(e.code, e.piece_id) for e in first.errors] == [("PIECE_DOES_NOT_FIT", 3)]
    assert first.affected_piece_ids == (3,) and first == check(p)
    assert repr(p) == original
