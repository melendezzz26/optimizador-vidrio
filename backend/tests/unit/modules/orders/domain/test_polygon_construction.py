"""HU-018: lados + ángulos interiores → vértices, sin dibujo (SPEC-HU-018 §4.4)."""
import math

import pytest

from app.modules.orders.domain.geometry import GeometryValidator
from app.modules.orders.domain.polygon_construction import PolygonConstructionError, build_polygon


def sides_and_angles(vertices):
    """Medidas que deberían reconstruir ``vertices`` (ángulo al final de cada lado)."""
    n = len(vertices)
    sides = [math.dist(vertices[i], vertices[(i + 1) % n]) for i in range(n)]
    angles = []
    for i in range(n):
        a, b, c = vertices[i], vertices[(i + 1) % n], vertices[(i + 2) % n]
        u, v = (a[0] - b[0], a[1] - b[1]), (c[0] - b[0], c[1] - b[1])
        angles.append(math.degrees(math.acos((u[0] * v[0] + u[1] * v[1]) / (math.hypot(*u) * math.hypot(*v)))))
    return sides, angles


def assert_same_shape(vertices, sides, angles):
    rebuilt_sides, rebuilt_angles = sides_and_angles(vertices)
    assert rebuilt_sides == pytest.approx(sides, abs=1e-4)
    assert rebuilt_angles == pytest.approx(angles, abs=1e-4)
    GeometryValidator.validate_convex_polygon(vertices)


def test_parallelogram_with_all_angles():
    vertices = build_polygon([120, 160, 120, 160], [60, 120, 60, 120])
    assert vertices == [[0, 0], [120, 0], [40, 138.564065], [-80, 138.564065]]
    assert_same_shape(vertices, [120, 160, 120, 160], [60, 120, 60, 120])


def test_regular_hexagon():
    vertices = build_polygon([100] * 6, [120] * 6)
    assert_same_shape(vertices, [100] * 6, [120] * 6)


@pytest.mark.parametrize("angles", [
    [90, 90, 90, None],          # 1 libre
    [None, 90, 90, None],        # 2 libres
    [None, 90, None, None],      # 3 libres
])
def test_free_angles_are_calculated(angles):
    vertices = build_polygon([300, 200, 300, 200], angles)
    assert_same_shape(vertices, [300, 200, 300, 200], [90, 90, 90, 90])


def test_triangle_without_angles_is_defined_by_its_sides():
    vertices = build_polygon([300, 400, 500], [None, None, None])
    assert_same_shape(vertices, [300, 400, 500], [90, pytest.approx(36.8699, abs=1e-3), pytest.approx(53.1301, abs=1e-3)])


def test_rounded_angles_close_within_tolerance():
    vertices = build_polygon([300, 400, 500], [90, 36.87, 53.13])
    GeometryValidator.validate_convex_polygon(vertices)


@pytest.mark.parametrize("angles", [
    [35, 35, 45, 60],            # suman 175°, deben sumar 360° (ejemplo de la sesión)
    [90, 90, 90, 80],            # suma incorrecta
])
def test_angles_that_do_not_sum_are_rejected(angles):
    with pytest.raises(PolygonConstructionError, match="no forman un polígono cerrado"):
        build_polygon([120, 160, 120, 160], angles)


def test_correct_sum_but_open_shape_is_rejected():
    with pytest.raises(PolygonConstructionError, match="no forman un polígono cerrado"):
        build_polygon([300, 200, 100, 200], [90, 90, 90, 90])


def test_impossible_triangle_is_rejected():
    with pytest.raises(PolygonConstructionError, match="no forman un polígono cerrado"):
        build_polygon([10, 10, 100], [None, None, None])


def test_more_than_three_free_angles_is_rejected():
    with pytest.raises(PolygonConstructionError, match="Faltan ángulos"):
        build_polygon([100, 100, 100, 100], [None, None, None, None])


def test_construction_is_deterministic():
    data = ([120, 90, 140, 70, 110], [100, None, 110, None, None])
    assert build_polygon(*data) == build_polygon(*data)