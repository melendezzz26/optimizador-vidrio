import math
from typing import List
from decimal import Decimal, ROUND_HALF_UP


def finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def storable_area(area):
    # Pieza.area_mm2 is NUMERIC(18, 2): reject rounding to zero or overflow.
    if not math.isfinite(area) or area <= 0:
        raise ValueError("El área debe ser positiva y finita.")
    rounded = Decimal(str(area)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if area < 1e16 else None
    if rounded is None or not 0 < rounded < Decimal("10000000000000000"):
        raise ValueError("El área está fuera del rango de almacenamiento en mm².")
    return area


class GeometryValidator:
    @staticmethod
    def validate_rectangle(width_mm: float, height_mm: float) -> float:
        if not finite_number(width_mm) or not finite_number(height_mm) or width_mm <= 0 or height_mm <= 0:
            raise ValueError("Las dimensiones del rectángulo deben ser positivas.")
        return storable_area(width_mm * height_mm)

    @staticmethod
    def validate_circle(radius_mm: float) -> float:
        if not finite_number(radius_mm) or radius_mm <= 0:
            raise ValueError("El radio de la circunferencia debe ser positivo.")
        return storable_area(math.pi * radius_mm * radius_mm)

    @staticmethod
    def validate_convex_polygon(vertices: List[List[float]]) -> float:
        if not isinstance(vertices, list) or len(vertices) < 3:
            raise ValueError("El polígono debe tener al menos 3 vértices.")

        # Check types and finite numbers
        for v in vertices:
            if not isinstance(v, list) or len(v) != 2:
                raise ValueError("Cada vértice debe ser una lista de 2 coordenadas [x, y].")
            if not finite_number(v[0]) or not finite_number(v[1]):
                raise ValueError("Las coordenadas deben ser números finitos.")

        n = len(vertices)

        # Check repeated consecutive vertices and zero length sides
        for i in range(n):
            v1 = vertices[i]
            v2 = vertices[(i + 1) % n]
            dx = v2[0] - v1[0]
            dy = v2[1] - v1[1]
            if abs(dx) < 1e-6 and abs(dy) < 1e-6:
                raise ValueError("No se permiten vértices consecutivos iguales o lados de longitud cero.")

        # Calculate area using shoelace
        area = 0.0
        for i in range(n):
            v1 = vertices[i]
            v2 = vertices[(i + 1) % n]
            area += (v1[0] * v2[1]) - (v2[0] * v1[1])
        area = abs(area) / 2.0

        # Convexity and simple polygon
        def cross_product(p1, p2, p3):
            return (p2[0] - p1[0]) * (p3[1] - p2[1]) - (p2[1] - p1[1]) * (p3[0] - p2[0])

        def on_segment(p, q, r):
            if q[0] <= max(p[0], r[0]) and q[0] >= min(p[0], r[0]) and \
               q[1] <= max(p[1], r[1]) and q[1] >= min(p[1], r[1]):
               return True
            return False

        def do_intersect(p1, q1, p2, q2):
            def orientation(p, q, r):
                val = cross_product(p, q, r)
                if abs(val) < 1e-6:
                    return 0
                return 1 if val > 0 else -1

            o1 = orientation(p1, q1, p2)
            o2 = orientation(p1, q1, q2)
            o3 = orientation(p2, q2, p1)
            o4 = orientation(p2, q2, q1)

            if o1 != o2 and o3 != o4:
                return True

            if o1 == 0 and on_segment(p1, p2, q1): return True
            if o2 == 0 and on_segment(p1, q2, q1): return True
            if o3 == 0 and on_segment(p2, p1, q2): return True
            if o4 == 0 and on_segment(p2, q1, q2): return True

            return False

        # Self-intersection check (only non-adjacent segments)
        for i in range(n):
            for j in range(i + 2, n):
                if i == 0 and j == n - 1:
                    continue # adjacent
                if do_intersect(vertices[i], vertices[(i + 1) % n], vertices[j], vertices[(j + 1) % n]):
                    raise ValueError("El polígono se intersecta a sí mismo.")

        if not math.isfinite(area) or area < 1e-6:
            raise ValueError("El área del polígono debe ser mayor a cero y no ser degenerado.")

        # Convexity check
        sign = 0
        for i in range(n):
            p1 = vertices[i]
            p2 = vertices[(i + 1) % n]
            p3 = vertices[(i + 2) % n]
            cp = cross_product(p1, p2, p3)

            # Allow collinear consecutive segments if they don't reverse
            if abs(cp) > 1e-6:
                current_sign = 1 if cp > 0 else -1
                if sign == 0:
                    sign = current_sign
                elif sign != current_sign:
                    raise ValueError("El polígono no es convexo.")

        # Degenerate completely collinear is handled by area > 0

        return storable_area(area)
