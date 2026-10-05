"""Contrato geométrico puro de retazos TA-003."""

from copy import deepcopy
from decimal import Decimal, Inexact, ROUND_DOWN, localcontext

import pytest

from app.modules.inventory.domain.geometry import calculate_area_mm2
from app.modules.inventory.domain.exceptions import InvalidGeometryError


def assert_area(geometry, expected):
    result = calculate_area_mm2(geometry)
    assert isinstance(result, Decimal)
    assert result > 0
    assert result <= Decimal("9999999999999999.99")
    assert result == Decimal(expected)
    assert result.as_tuple().exponent == -2


@pytest.mark.parametrize("width,height,expected", [
    (1000, 500, "500000.00"),
    (Decimal("12.25"), Decimal("3.50"), "42.88"),
    (1.005, 1, "1.01"),
    (Decimal("1.0049"), 1, "1.00"),
    (Decimal("123456789012345678901234567890.005"), Decimal("0.000000000000001"),
     "123456789012345.68"),
])
def test_rectangle_area(width, height, expected):
    assert_area({"type": "RECTANGULO", "width_mm": width, "height_mm": height}, expected)


@pytest.mark.parametrize("radius,expected", [
    (250, "196349.54"),
    (1, "3.14"),
    (Decimal("0.5"), "0.79"),
    (2.5, "19.63"),
])
def test_circle_area(radius, expected):
    assert_area({"type": "CIRCUNFERENCIA", "radius_mm": radius}, expected)


DIMENSIONS = [
    ({"type": "RECTANGULO", "width_mm": 10, "height_mm": 20}, "width_mm"),
    ({"type": "RECTANGULO", "width_mm": 10, "height_mm": 20}, "height_mm"),
    ({"type": "CIRCUNFERENCIA", "radius_mm": 10}, "radius_mm"),
]
INVALID_NUMBERS = [
    True, False, None, "12.5", "abc", [], {},
    float("nan"), float("inf"), float("-inf"),
    Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"), Decimal("-Infinity"),
]


@pytest.mark.parametrize("geometry,field", DIMENSIONS)
@pytest.mark.parametrize("value", [0, -1, Decimal("-0.01"), *INVALID_NUMBERS])
def test_dimensions_reject_nonpositive_or_invalid_numbers(geometry, field, value):
    with pytest.raises(InvalidGeometryError):
        calculate_area_mm2({**geometry, field: value})


@pytest.mark.parametrize("geometry,field", DIMENSIONS)
def test_missing_dimension(geometry, field):
    incomplete = {key: value for key, value in geometry.items() if key != field}
    with pytest.raises(InvalidGeometryError):
        calculate_area_mm2(incomplete)


@pytest.mark.parametrize("vertices,expected", [
    ([[0, 0], [4, 0], [0, 3]], "6.00"),
    ([[0, 0], [500, 0], [430, 300], [100, 420]], "150300.00"),
    ([[-3, -2], [1, -2], [1, 1], [-3, 1]], "12.00"),
    ([[0, 0], [Decimal("1.005"), 0], [0, 2]], "1.01"),
    ([[0, 0], [0.1, 0], [0, 0.3]], "0.02"),
])
@pytest.mark.parametrize("clockwise", [False, True])
def test_convex_polygon_area_in_both_orientations(vertices, expected, clockwise):
    if clockwise:
        vertices = list(reversed(vertices))
    assert_area({"type": "POLIGONO_CONVEXO", "vertices_mm": vertices}, expected)


@pytest.mark.parametrize("vertices", [
    [], [[0, 0]], [[0, 0], [1, 1]],
    [[0, 0], [1, 1], [2, 2]],
    [[0, 0], [2, 0], [4, 0], [4, 3], [0, 3]],
    [[0, 0], [4, 0], [2, 1], [4, 4], [0, 4]],
    [[0, 0], [4, 4], [0, 4], [4, 0]],
    # Estrella con giros locales del mismo signo y área algebraica no nula.
    [[0, 3], [2, -3], [-3, 1], [3, 1], [-2, -3]],
    [[0, 0], [4, 0], [4, 0], [0, 3]],
    [[0, 0], [4, 0], [0, 3], [0, 0]],
    [[0, 0], [4, 0], [4, 4], [2, 0], [0, 4]],
    [[0, 0], [4, 0], [4, 4], [0, 0], [0, 4]],
])
def test_polygon_rejects_degenerate_concave_or_intersecting_boundaries(vertices):
    with pytest.raises(InvalidGeometryError):
        calculate_area_mm2({"type": "POLIGONO_CONVEXO", "vertices_mm": vertices})


@pytest.mark.parametrize("vertices", [None, True, 3, "triangle", {}, {0, 1, 2}])
def test_invalid_vertices_structure(vertices):
    with pytest.raises(InvalidGeometryError):
        calculate_area_mm2({"type": "POLIGONO_CONVEXO", "vertices_mm": vertices})


@pytest.mark.parametrize("vertex", [None, True, 1, "00", [], [0], [0, 0, 0], {"x": 0, "y": 0}])
def test_invalid_vertex_structure(vertex):
    with pytest.raises(InvalidGeometryError):
        calculate_area_mm2({"type": "POLIGONO_CONVEXO", "vertices_mm": [vertex, [4, 0], [0, 3]]})


@pytest.mark.parametrize("value", INVALID_NUMBERS)
@pytest.mark.parametrize("axis", [0, 1])
def test_invalid_polygon_coordinate(value, axis):
    vertices = [[0, 0], [4, 0], [0, 3]]
    vertices[0][axis] = value
    with pytest.raises(InvalidGeometryError):
        calculate_area_mm2({"type": "POLIGONO_CONVEXO", "vertices_mm": vertices})


@pytest.mark.parametrize("geometry", [
    None, True, 10, "RECTANGULO", [], {},
    {"type": None}, {"type": []}, {"type": {}}, {"type": 1},
    {"type": "TRIANGULO"}, {"type": "rectangulo"},
    {"width_mm": 10, "height_mm": 20},
    {"type": "POLIGONO_CONVEXO"},
])
def test_missing_invalid_or_unsupported_geometry(geometry):
    with pytest.raises(InvalidGeometryError):
        calculate_area_mm2(geometry)


@pytest.mark.parametrize("geometry,expected", [
    ({"type": "RECTANGULO", "width_mm": Decimal("1.005"), "height_mm": 1}, "1.01"),
    ({"type": "CIRCUNFERENCIA", "radius_mm": 250}, "196349.54"),
    ({"type": "POLIGONO_CONVEXO", "vertices_mm": [[0, 0], [Decimal("1.005"), 0], [0, 2]]}, "1.01"),
])
def test_area_is_independent_of_callers_decimal_context(geometry, expected):
    with localcontext() as context:
        context.prec = 3
        context.rounding = ROUND_DOWN
        context.traps[Inexact] = True
        assert_area(geometry, expected)
        assert context.prec == 3
        assert context.rounding == ROUND_DOWN
        assert context.traps[Inexact]


def test_polygon_with_large_coordinates_keeps_small_area():
    vertices = [
        [Decimal("1000000000000000000000000000000"), 0],
        [Decimal("1000000000000000000000000000004"), 0],
        [Decimal("1000000000000000000000000000004"), 3],
        [Decimal("1000000000000000000000000000000"), 3],
    ]
    assert_area({"type": "POLIGONO_CONVEXO", "vertices_mm": vertices}, "12.00")


def test_area_is_computed_without_mutating_or_trusting_client_area():
    geometry = {
        "type": "POLIGONO_CONVEXO",
        "vertices_mm": [[0, 0], [4, 0], [0, 3]],
        "area_mm2": 999999,
    }
    original = deepcopy(geometry)
    assert_area(geometry, "6.00")
    assert geometry == original


@pytest.mark.parametrize("geometry", [
    {"type": "RECTANGULO", "width_mm": Decimal("0.01"), "height_mm": Decimal("0.01")},
    {"type": "CIRCUNFERENCIA", "radius_mm": Decimal("0.01")},
    {"type": "POLIGONO_CONVEXO",
     "vertices_mm": [[0, 0], [Decimal("0.01"), 0], [0, Decimal("0.01")]]},
    {"type": "RECTANGULO", "width_mm": Decimal("0.004999999"), "height_mm": 1},
    {"type": "CIRCUNFERENCIA", "radius_mm": Decimal("0.03989")},
    {"type": "POLIGONO_CONVEXO",
     "vertices_mm": [[0, 0], [Decimal("0.004999999"), 0], [0, 2]]},
], ids=["tiny-rectangle", "tiny-circle", "tiny-polygon",
        "rectangle-below-threshold", "circle-below-threshold", "polygon-below-threshold"])
def test_positive_area_rounding_to_zero_is_rejected(geometry):
    with pytest.raises(InvalidGeometryError):
        calculate_area_mm2(geometry)


@pytest.mark.parametrize("geometry", [
    # Área exactamente 0.005: ROUND_HALF_UP debe producir 0.01.
    {"type": "RECTANGULO", "width_mm": Decimal("0.005"), "height_mm": 1},
    {"type": "POLIGONO_CONVEXO",
     "vertices_mm": [[0, 0], [Decimal("0.005"), 0], [0, 2]]},
    # El radio umbral sqrt(0.005 / PI) está entre 0.03989 y 0.03990.
    {"type": "CIRCUNFERENCIA", "radius_mm": Decimal("0.03990")},
], ids=["rectangle-at-threshold", "polygon-at-threshold", "circle-above-threshold"])
def test_smallest_positive_quantized_area_is_accepted(geometry):
    assert_area(geometry, "0.01")


@pytest.mark.parametrize("geometry", [
    {"type": "RECTANGULO", "width_mm": Decimal("9999999999999999.99"), "height_mm": 1},
    # El límite se aplica después de cuantizar, no al área sin redondear.
    {"type": "RECTANGULO", "width_mm": Decimal("9999999999999999.9949"), "height_mm": 1},
    {"type": "POLIGONO_CONVEXO", "vertices_mm": [
        [0, 0], [Decimal("9999999999999999.99"), 0],
        [Decimal("9999999999999999.99"), 1], [0, 1],
    ]},
], ids=["rectangle-at-maximum", "rectangle-rounding-to-maximum", "polygon-at-maximum"])
def test_maximum_quantized_area_is_accepted(geometry):
    assert_area(geometry, "9999999999999999.99")


@pytest.mark.parametrize("geometry", [
    {"type": "RECTANGULO", "width_mm": Decimal("9999999999999999.995"), "height_mm": 1},
    {"type": "RECTANGULO", "width_mm": 10000000000000000, "height_mm": 1},
    {"type": "RECTANGULO", "width_mm": Decimal("123456789012345678901234567890.005"),
     "height_mm": 1},
    {"type": "CIRCUNFERENCIA", "radius_mm": 100000000},
    {"type": "POLIGONO_CONVEXO", "vertices_mm": [
        [0, 0], [100000000, 0], [100000000, 100000000], [0, 100000000],
    ]},
], ids=["rectangle-rounding-over-maximum", "rectangle-over-maximum",
        "very-large-rectangle", "circle-over-maximum", "polygon-over-maximum"])
def test_quantized_area_above_maximum_is_rejected(geometry):
    with pytest.raises(InvalidGeometryError):
        calculate_area_mm2(geometry)
