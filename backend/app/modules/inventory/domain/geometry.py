"""Validación y cálculo de áreas de retazos, sin dependencias de infraestructura."""

from collections.abc import Mapping
from decimal import Context, Decimal, DecimalException, ROUND_HALF_UP, localcontext

from .exceptions import InvalidGeometryError


PI = Decimal("3.14159265358979323846264338327950288419716939937510")
AREA_QUANTUM = Decimal("0.01")
# Rango aprobado para el área de NewGlass v1.1 (NUMERIC(18,2)).
MAX_AREA_MM2 = Decimal("9999999999999999.99")
GEOMETRY_FIELDS = {
    "RECTANGULO": frozenset({"type", "width_mm", "height_mm"}),
    "CIRCUNFERENCIA": frozenset({"type", "radius_mm"}),
    "POLIGONO_CONVEXO": frozenset({"type", "vertices_mm"}),
}
SUPPORTED_TYPES = tuple(GEOMETRY_FIELDS)
Point = tuple[Decimal, Decimal]


def _number(value: object, field: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise InvalidGeometryError(f"{field} debe ser un número finito.")
    # str evita incorporar los artefactos binarios de un float recibido del JSON.
    number = value if isinstance(value, Decimal) else Decimal(str(value))
    if not number.is_finite():
        raise InvalidGeometryError(f"{field} debe ser un número finito.")
    return number


def _positive_dimension(geometry: Mapping, field: str) -> Decimal:
    number = _number(geometry.get(field), field)
    if number <= 0:
        raise InvalidGeometryError(f"{field} debe ser mayor que cero.")
    return number


def _vertices(value: object) -> list[Point]:
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        raise InvalidGeometryError("vertices_mm debe contener al menos tres vértices.")
    points = []
    for index, vertex in enumerate(value):
        if not isinstance(vertex, (list, tuple)) or len(vertex) != 2:
            raise InvalidGeometryError(f"El vértice {index} debe contener dos coordenadas.")
        points.append((
            _number(vertex[0], f"vertices_mm[{index}][0]"),
            _number(vertex[1], f"vertices_mm[{index}][1]"),
        ))
    if len(set(points)) != len(points):
        raise InvalidGeometryError("Los vértices no deben repetirse.")
    return points


def _precision(numbers: list[Decimal]) -> int:
    # Reserva dígitos para diferencias, productos, PI y suma de las aristas.
    # La amplitud decimal preserva áreas pequeñas aun con coordenadas grandes.
    highest = max(1, max(number.adjusted() + 1 for number in numbers))
    lowest = min(-2, min(number.as_tuple().exponent for number in numbers))
    return 2 * (highest - lowest) + len(PI.as_tuple().digits) + len(str(len(numbers))) + 4


def _cross(a: Point, b: Point, c: Point) -> Decimal:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _polygon_area(points: list[Point]) -> Decimal:
    orientation = _cross(points[0], points[1], points[2])
    if orientation == 0:
        raise InvalidGeometryError("El polígono no puede contener vértices colineales.")
    counterclockwise = orientation > 0
    count = len(points)
    for index, a in enumerate(points):
        next_index = (index + 1) % count
        b = points[next_index]
        # En un polígono estrictamente convexo cada arista deja TODOS los demás
        # vértices en el mismo semiplano abierto. También descarta cruces y toques.
        for other_index, c in enumerate(points):
            if other_index in (index, next_index):
                continue
            cross = _cross(a, b, c)
            if cross == 0 or (cross > 0) != counterclockwise:
                raise InvalidGeometryError(
                    "El polígono debe ser convexo, sin colinealidad ni auto-intersecciones."
                )
    # Fórmula del cordón, independiente del sentido de recorrido.
    twice_area = sum(
        (a[0] * points[(index + 1) % count][1]
         - a[1] * points[(index + 1) % count][0])
        for index, a in enumerate(points)
    )
    area = abs(twice_area) / 2
    if area <= 0:
        raise InvalidGeometryError("El área del polígono debe ser mayor que cero.")
    return area


def calculate_area_mm2(geometry: Mapping[str, object]) -> Decimal:
    """Valida una geometría y devuelve su área en mm² con dos decimales.

    Acepta int, float finitos y Decimal; rechaza bool y cadenas numéricas.
    Los polígonos usan vértices ordenados, sin repetir el primero al final,
    en cualquiera de los dos sentidos y con convexidad estricta.
    Cada tipo exige sus claves exactas; se rechazan campos adicionales,
    incluido area_mm2, que solo pertenece al resultado calculado por backend.
    El área debe ser positiva antes y después de cuantizar a dos decimales:
    si redondea a Decimal('0.00'), la geometría es inválida.
    El resultado cuantizado no puede superar MAX_AREA_MM2.
    No modifica la entrada ni el contexto decimal.
    """
    if not isinstance(geometry, Mapping):
        raise InvalidGeometryError("La geometría debe ser un objeto con un tipo admitido.")
    kind = geometry.get("type")
    if not isinstance(kind, str) or kind not in SUPPORTED_TYPES:
        raise InvalidGeometryError("Tipo de geometría no soportado.")
    if set(geometry) != GEOMETRY_FIELDS[kind]:
        raise InvalidGeometryError(
            "La geometría debe contener exactamente las propiedades de su tipo, sin campos adicionales."
        )

    if kind == "RECTANGULO":
        numbers = [_positive_dimension(geometry, field) for field in ("width_mm", "height_mm")]
    elif kind == "CIRCUNFERENCIA":
        numbers = [_positive_dimension(geometry, "radius_mm")]
    else:
        points = _vertices(geometry.get("vertices_mm"))
        numbers = [coordinate for point in points for coordinate in point]

    try:
        # Context nuevo: precisión, redondeo y traps no dependen del llamador.
        with localcontext(Context(prec=_precision(numbers), rounding=ROUND_HALF_UP)):
            if kind == "RECTANGULO":
                area = numbers[0] * numbers[1]
            elif kind == "CIRCUNFERENCIA":
                area = PI * numbers[0] * numbers[0]
            else:
                area = _polygon_area(points)
            if area <= 0:
                raise InvalidGeometryError("El área debe ser mayor que cero.")
            quantized_area = area.quantize(AREA_QUANTUM, rounding=ROUND_HALF_UP)
            if quantized_area <= 0:
                raise InvalidGeometryError(
                    "El área debe seguir siendo mayor que cero después de cuantizar a dos decimales."
                )
            if quantized_area > MAX_AREA_MM2:
                raise InvalidGeometryError(
                    f"El área cuantizada no debe superar {MAX_AREA_MM2} mm²."
                )
            return quantized_area
    except DecimalException as exc:
        raise InvalidGeometryError("La geometría excede el rango decimal de cálculo.") from exc
