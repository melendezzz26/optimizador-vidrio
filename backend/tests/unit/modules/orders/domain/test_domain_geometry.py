import pytest
from app.modules.orders.domain.geometry import GeometryValidator

def test_validate_rectangle_valid():
    area = GeometryValidator.validate_rectangle(100, 200)
    assert area == 20000

def test_validate_rectangle_invalid():
    with pytest.raises(ValueError):
        GeometryValidator.validate_rectangle(-10, 20)

def test_validate_circle_valid():
    area = GeometryValidator.validate_circle(10)
    assert area > 314 and area < 315

def test_validate_circle_invalid():
    with pytest.raises(ValueError):
        GeometryValidator.validate_circle(0)

def test_validate_convex_polygon_triangle():
    area = GeometryValidator.validate_convex_polygon([[0,0], [10,0], [0,10]])
    assert area == 50

def test_validate_convex_polygon_cw():
    area = GeometryValidator.validate_convex_polygon([[0,0], [0,10], [10,10], [10,0]])
    assert area == 100

def test_validate_convex_polygon_ccw():
    area = GeometryValidator.validate_convex_polygon([[0,0], [10,0], [10,10], [0,10]])
    assert area == 100

def test_validate_convex_polygon_concave():
    with pytest.raises(ValueError, match="no es convexo"):
        GeometryValidator.validate_convex_polygon([[0,0], [10,0], [5,5], [10,10], [0,10]])

def test_validate_convex_polygon_self_intersect():
    with pytest.raises(ValueError, match="intersecta a sí mismo"):
        # bow-tie
        GeometryValidator.validate_convex_polygon([[0,0], [10,10], [10,0], [0,10]])

def test_validate_convex_polygon_degenerate():
    with pytest.raises(ValueError, match="área del polígono debe ser mayor a cero"):
        GeometryValidator.validate_convex_polygon([[0,0], [10,0], [20,0]])

def test_validate_convex_polygon_repeated_vertex():
    with pytest.raises(ValueError, match="consecutivos iguales"):
        GeometryValidator.validate_convex_polygon([[0,0], [10,0], [10,0], [0,10]])

def test_validate_convex_polygon_invalid_coords():
    with pytest.raises(ValueError, match="números finitos"):
        GeometryValidator.validate_convex_polygon([[0,0], [10,0], [float('inf'),10]])


@pytest.mark.parametrize("value", [True, "10", None, float("nan"), float("inf")])
def test_all_shapes_reject_non_numeric_or_non_finite_values(value):
    for call in (
        lambda: GeometryValidator.validate_rectangle(value, 10),
        lambda: GeometryValidator.validate_circle(value),
        lambda: GeometryValidator.validate_convex_polygon([[0, 0], [10, 0], [value, 10]]),
    ):
        with pytest.raises(ValueError):
            call()


@pytest.mark.parametrize("width,height", [(1e200, 1e200), (1e-5, 1e-5), (1e16, 1)])
def test_area_must_fit_canonical_storage(width, height):
    with pytest.raises(ValueError):
        GeometryValidator.validate_rectangle(width, height)


def test_nonadjacent_duplicate_vertex_is_rejected():
    with pytest.raises(ValueError):
        GeometryValidator.validate_convex_polygon([[0, 0], [10, 0], [10, 10], [0, 0], [0, 10]])
