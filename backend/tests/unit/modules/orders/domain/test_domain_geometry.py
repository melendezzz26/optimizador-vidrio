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
