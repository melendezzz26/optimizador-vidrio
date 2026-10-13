"""Rasterización conservadora de piezas (TA-005 / TA-006).

Ver SPEC-TA-005-TA-006. Una celda se ocupa si la figura cubre un área positiva
de ella (RN-01): ninguna parte de la pieza queda fuera de la máscara, a cambio
de sobreestimar un poco su área. La figura se recorre fila por fila; como las
figuras son convexas, cada fila ocupa un único tramo continuo de columnas.
"""
import math

from .raster_mask import RasterMask, RasterizationError, is_real_number

DEFAULT_RESOLUTION_MM = 5.0  # SP-001
COORDINATE_DECIMALS = 6  # RN-04: se redondea a 0.000001 mm
_EPSILON = 1e-9  # Tolerancia en unidades de celda para absorber residuos de coma flotante


def _positive(value, label: str) -> float:
    if not is_real_number(value) or value <= 0:
        raise RasterizationError(f"{label} debe ser un número positivo.")
    return float(value)


def _cell_count(length_mm: float, resolution_mm: float) -> int:
    """Celdas necesarias para cubrir una longitud (RN-03), al menos una."""
    return max(1, math.ceil(length_mm / resolution_mm - _EPSILON))


def _column_span(low_mm: float, high_mm: float, resolution_mm: float) -> tuple[int, int]:
    """Tramo [inicio, fin) de columnas que tocan con área positiva el intervalo [low, high]."""
    start = math.floor(low_mm / resolution_mm + _EPSILON)
    end = math.ceil(high_mm / resolution_mm - _EPSILON)
    return start, max(end, start + 1)


def _normalized_vertices(vertices_mm) -> list[tuple[float, float]]:
    """Valida los vértices y traslada la caja envolvente al origen (RN-02, RN-04)."""
    if not isinstance(vertices_mm, (list, tuple)) or len(vertices_mm) < 3:
        raise RasterizationError("El polígono debe tener al menos 3 vértices.")
    for vertex in vertices_mm:
        if (
            not isinstance(vertex, (list, tuple))
            or len(vertex) != 2
            or not all(is_real_number(coordinate) for coordinate in vertex)
        ):
            raise RasterizationError("Cada vértice debe ser un par [x, y] de números finitos.")

    min_x = min(x for x, _ in vertices_mm)
    min_y = min(y for _, y in vertices_mm)
    return [
        (round(x - min_x, COORDINATE_DECIMALS), round(y - min_y, COORDINATE_DECIMALS))
        for x, y in vertices_mm
    ]


def _horizontal_extent(points, top_mm: float, bottom_mm: float) -> tuple[float, float]:
    """Mínima y máxima X del polígono dentro de la franja horizontal [top, bottom]."""
    xs = []
    count = len(points)
    for index in range(count):
        (ax, ay), (bx, by) = points[index], points[(index + 1) % count]
        if top_mm <= ay <= bottom_mm:
            xs.append(ax)
        if ay != by:
            # Puntos donde el lado cruza los bordes superior e inferior de la franja.
            for edge_y in (top_mm, bottom_mm):
                t = (edge_y - ay) / (by - ay)
                if 0 <= t <= 1:
                    xs.append(ax + t * (bx - ax))
    return min(xs), max(xs)


def rasterize_convex_polygon(vertices_mm, resolution_mm=DEFAULT_RESOLUTION_MM) -> RasterMask:
    """Rasteriza un polígono convexo (TA-006).

    Los vértices llegan como en ``geometria.vertices_mm`` de un pedido: el primero
    puede estar en (0, 0), puede haber coordenadas negativas y la Y crece hacia
    abajo. La convexidad ya la validó el módulo de pedidos (HU-007 T03); si llegara
    un polígono no convexo, cada fila se cubriría completa entre sus extremos, así
    que el resultado seguiría siendo conservador.
    """
    resolution = _positive(resolution_mm, "La resolución")
    points = _normalized_vertices(vertices_mm)
    width = max(x for x, _ in points)
    height = max(y for _, y in points)
    if width <= 0 or height <= 0:
        raise RasterizationError("El polígono debe tener ancho y alto mayores que cero.")

    spans = []
    for row in range(_cell_count(height, resolution)):
        top = row * resolution
        bottom = min(top + resolution, height)
        low, high = _horizontal_extent(points, top, bottom)
        spans.append(_column_span(low, high, resolution))

    return RasterMask.from_spans(resolution, _cell_count(width, resolution), spans)