"""HU-018: construye los vértices de un polígono a partir de lados y ángulos interiores.

El editor de piezas calcula los vértices con el dibujo como guía. Un archivo no tiene
dibujo, así que aquí la forma se obtiene solo con números (SPEC-HU-018 §4.4, §8.1):

- ``angles[k]`` es el ángulo interior al final del lado ``k`` (entre el lado ``k`` y el
  siguiente); ``None`` significa "libre, calcúlalo".
- Se recorren los lados en sentido antihorario: un ángulo interior A es un giro de 180 - A.
- Con hasta 3 ángulos libres la forma queda definida; con más, no.

El resultado es determinístico: los mismos lados y ángulos dan siempre los mismos vértices.
"""
import math

CLOSURE_TOLERANCE_MM = 0.5      # mitad de la resolución raster de 1 mm
ANGLE_SUM_TOLERANCE_DEG = 0.1
MAX_FREE_ANGLES = 3

MISSING_ANGLES = "Faltan ángulos para definir el polígono"
NOT_CLOSED = "Los lados y ángulos no forman un polígono cerrado"


class PolygonConstructionError(ValueError):
    """Los lados y ángulos indicados no definen un polígono."""


def _chain(sides, turns):
    """Recorre lados con giros fijos desde (0, 0) y rumbo 0; devuelve los puntos."""
    points = [(0.0, 0.0)]
    heading = 0.0
    for index, side in enumerate(sides):
        x, y = points[-1]
        points.append((x + side * math.cos(heading), y + side * math.sin(heading)))
        if index < len(turns):
            heading += turns[index]
    return points


def _place(points, start, target):
    """Rota un tramo para que empiece en ``start`` y su extremo apunte a ``target``."""
    end_x, end_y = points[-1]
    rotation = math.atan2(target[1] - start[1], target[0] - start[0]) - math.atan2(end_y, end_x)
    cos, sin = math.cos(rotation), math.sin(rotation)
    return [(start[0] + x * cos - y * sin, start[1] + x * sin + y * cos) for x, y in points]


def _clean(points):
    # Redondeo fijo: evita ruido de coma flotante (y -0.0) en la respuesta.
    return [[round(x, 6) + 0.0, round(y, 6) + 0.0] for x, y in points]


def _turn(angle):
    return math.radians(180.0 - angle)


def build_polygon(sides, angles):
    """Devuelve los vértices ``[[x, y], ...]`` o lanza ``PolygonConstructionError``."""
    n = len(sides)
    if n != len(angles) or n < 3:
        raise PolygonConstructionError("Un polígono necesita al menos 3 lados")
    free = [(k + 1) % n for k, angle in enumerate(angles) if angle is None]
    if len(free) > MAX_FREE_ANGLES:
        raise PolygonConstructionError(MISSING_ANGLES)
    angle_at = {(k + 1) % n: angle for k, angle in enumerate(angles)}  # ángulo de cada vértice

    if not free:
        if abs(sum(angles) - (n - 2) * 180.0) > ANGLE_SUM_TOLERANCE_DEG:
            raise PolygonConstructionError(NOT_CLOSED)
        points = _chain(sides, [_turn(angle_at[(k + 1) % n]) for k in range(n - 1)])
        if math.dist(points[-1], points[0]) > CLOSURE_TOLERANCE_MM:
            raise PolygonConstructionError(NOT_CLOSED)
        return _clean(points[:-1])

    # Tramos rígidos entre vértices libres consecutivos (en orden de recorrido).
    free.sort()
    chains = []
    for index, first in enumerate(free):
        last = free[(index + 1) % len(free)]
        count = (last - first) % n or n
        side_indices = [(first + j) % n for j in range(count)]
        inner_turns = [_turn(angle_at[(first + j) % n]) for j in range(1, count)]
        chains.append(_chain([sides[i] for i in side_indices], inner_turns))
    chords = [math.hypot(*chain[-1]) for chain in chains]

    if len(chains) == 1:
        if chords[0] > CLOSURE_TOLERANCE_MM:
            raise PolygonConstructionError(NOT_CLOSED)
        return _clean(chains[0][:-1])

    if min(chords) <= CLOSURE_TOLERANCE_MM:
        raise PolygonConstructionError(NOT_CLOSED)
    if len(chains) == 2:
        if abs(chords[0] - chords[1]) > CLOSURE_TOLERANCE_MM:
            raise PolygonConstructionError(NOT_CLOSED)
        corners = [(0.0, 0.0), (chords[0], 0.0)]
    else:
        a, b, c = chords  # triángulo con lados conocidos, en sentido antihorario
        if a >= b + c or b >= a + c or c >= a + b:
            raise PolygonConstructionError(NOT_CLOSED)
        x = (a * a + c * c - b * b) / (2 * a)
        corners = [(0.0, 0.0), (a, 0.0), (x, math.sqrt(max(c * c - x * x, 0.0)))]

    vertices = []
    for index, chain in enumerate(chains):
        start, target = corners[index], corners[(index + 1) % len(corners)]
        vertices.extend(_place(chain, start, target)[:-1])
    return _clean(vertices)