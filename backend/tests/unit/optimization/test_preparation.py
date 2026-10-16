from copy import deepcopy
from decimal import Decimal as D
from itertools import permutations

import pytest

from app.modules.optimization.application.preparation import prepare_persisted_problem
from app.modules.optimization.domain.preparation import bbox_dimensions
from app.modules.optimization.domain.problem import OptimizationConfig


CONFIG = OptimizationConfig(resolution_mm=1, margin_mm=0, separation_mm=0, angular_step_deg=90)


def piece(identifier=1, order=1, quantity=1, glass=1, thickness="6", width=4, height=2, area=None):
    return dict(id_pedido=order, id_pieza=identifier, cantidad=quantity,
                id_tipo_vidrio=glass, espesor_mm=D(thickness), tipo_forma="RECTANGULO",
                geometria=dict(type="RECTANGULO", width_mm=width, height_mm=height),
                area_mm2=D(str(area if area is not None else width * height)))


@pytest.mark.parametrize("quantity", [1, 2, 5])
def test_quantity_identity_and_immutable_snapshot(quantity):
    row = piece(quantity=quantity)
    original = deepcopy(row)
    result = prepare_persisted_problem([1], [row], CONFIG)
    assert [(u.order_id, u.piece_id, u.unit_index) for u in result.units] == [
        (1, 1, i) for i in range(1, quantity + 1)]
    assert row == original
    row["geometria"]["width_mm"] = 99
    assert all(u.geometry["width_mm"] == 4 for u in result.units)
    assert all(isinstance(u.area_mm2, D) and isinstance(u.thickness_mm, D) for u in result.units)


def test_two_orders_materials_and_thickness_sorted_and_permutation_independent():
    rows = [piece(1, 2, glass=2), piece(2, 1, thickness="5.5"), piece(3, 2, thickness="6")]
    expected = prepare_persisted_problem([2, 1], rows, CONFIG)
    assert expected.order_ids == (1, 2)
    assert [g.key for g in expected.groups] == [(1, D("5.5")), (1, D(6)), (2, D(6))]
    for rows_permuted in permutations(rows):
        assert prepare_persisted_problem([1, 2], rows_permuted, CONFIG) == expected


def test_area_then_bbox_then_order_piece_and_unit_indices():
    rows = [piece(6, 2, quantity=2), piece(5, 1, quantity=2), piece(4, 1),
            piece(3, 1, width=8, height=1), piece(2, 1, width=3, height=3)]
    result = prepare_persisted_problem([2, 1], rows[::-1], CONFIG)
    assert [(u.piece_id, u.unit_index) for u in result.units] == [
        (2, 1), (3, 1), (4, 1), (5, 1), (5, 2), (6, 1), (6, 2)]
    assert result == prepare_persisted_problem([2, 1], rows, CONFIG)


@pytest.mark.parametrize("geometry,expected", [
    ({"type": "RECTANGULO", "width_mm": 0.1, "height_mm": 2}, (D("0.1"), D(2))),
    ({"type": "CIRCUNFERENCIA", "radius_mm": 1.1}, (D("2.2"), D("2.2"))),
    ({"type": "POLIGONO_CONVEXO", "vertices_mm": [[-2, -1], [4, 0], [0, 3]]}, (D(6), D(4))),
])
def test_decimal_bbox_for_supported_shapes(geometry, expected):
    assert bbox_dimensions(geometry) == expected


@pytest.mark.parametrize("change", [
    {"cantidad": 0}, {"cantidad": -1}, {"cantidad": True}, {"cantidad": 1.5},
    {"espesor_mm": D(0)}, {"area_mm2": D(0)}, {"id_pieza": 0},
    {"geometria": {"type": "RECTANGULO", "width_mm": -1, "height_mm": 2}},
])
def test_invalid_persisted_metadata_or_geometry_rejected(change):
    with pytest.raises(ValueError):
        prepare_persisted_problem([1], [piece() | change], CONFIG)


@pytest.mark.parametrize("orders,rows", [([], []), ([1], []), ([1, 1], [piece()]),
                                         ([1, 2], [piece()]), ([2], [piece()]),
                                         ([1], [piece(), piece()])])
def test_invalid_selection_or_duplicate_piece_rejected(orders, rows):
    with pytest.raises(ValueError):
        prepare_persisted_problem(orders, rows, CONFIG)
