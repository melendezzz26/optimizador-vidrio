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

def rasterize_rectangle(width_mm, height_mm, resolution_mm=DEFAULT_RESOLUTION_MM) -> RasterMask:
    """Rasteriza un rectángulo (TA-005) como polígono convexo de 4 vértices."""
    width = _positive(width_mm, "El ancho")
    height = _positive(height_mm, "El alto")
    return rasterize_convex_polygon(
        [[0, 0], [width, 0], [width, height], [0, height]], resolution_mm
    )

def rasterize_circle(radius_mm, resolution_mm=DEFAULT_RESOLUTION_MM) -> RasterMask:
    """Rasteriza una circunferencia (TA-005) con la regla conservadora.

    El centro queda en (radio, radio). En cada franja horizontal, el círculo es
    más ancho en la altura más cercana al centro; esa es la que define el tramo.
    """
    resolution = _positive(resolution_mm, "La resolución")
    radius = _positive(radius_mm, "El radio")
    diameter = round(2 * radius, COORDINATE_DECIMALS)

    spans = []
    for row in range(_cell_count(diameter, resolution)):
        top = row * resolution
        bottom = min(top + resolution, diameter)
        if top <= radius <= bottom:
            nearest = 0.0  # La franja contiene la altura del centro.
        else:
            nearest = min(abs(top - radius), abs(bottom - radius))
        half_width = math.sqrt(max(radius * radius - nearest * nearest, 0.0))
        spans.append(_column_span(radius - half_width, radius + half_width, resolution))

    return RasterMask.from_spans(resolution, _cell_count(diameter, resolution), spans)


def _field(geometry: dict, name: str):
    if name not in geometry:
        raise RasterizationError(f"A la geometría le falta el campo {name}.")
    return geometry[name]


def rasterize_geometry(geometry, resolution_mm=DEFAULT_RESOLUTION_MM) -> RasterMask:
    """Punto de entrada: recibe la ``geometria`` tal como la guarda el módulo de pedidos."""
    if not isinstance(geometry, dict):
        raise RasterizationError("La geometría debe ser un objeto con el campo type.")

    shape = geometry.get("type")
    if shape == "RECTANGULO":
        return rasterize_rectangle(
            _field(geometry, "width_mm"), _field(geometry, "height_mm"), resolution_mm
        )
    if shape == "CIRCUNFERENCIA":
        return rasterize_circle(_field(geometry, "radius_mm"), resolution_mm)
    if shape == "POLIGONO_CONVEXO":
        return rasterize_convex_polygon(_field(geometry, "vertices_mm"), resolution_mm)
    raise RasterizationError("Tipo de geometría no soportado.")

# Una celda del material es usable solo si está completamente dentro de él, para
# que una pieza colocada ahí nunca quede sobre una zona sin vidrio.


def _interior_span(low_mm: float, high_mm: float, resolution_mm: float) -> tuple[int, int]:
    """Tramo [inicio, fin) de columnas contenidas por completo en [low, high]; puede ser vacío."""
    start = math.ceil(low_mm / resolution_mm - _EPSILON)
    end = math.floor(high_mm / resolution_mm + _EPSILON)
    return (start, end) if end > start else (0, 0)


def _cross_section(points, y_mm: float):
    """Intervalo [x mínima, x máxima] del polígono sobre la recta horizontal y; None si no la corta."""
    xs = []
    count = len(points)
    for index in range(count):
        (ax, ay), (bx, by) = points[index], points[(index + 1) % count]
        if ay == by:
            if ay == y_mm:
                xs.extend((ax, bx))
        elif min(ay, by) <= y_mm <= max(ay, by):
            xs.append(ax + (y_mm - ay) / (by - ay) * (bx - ax))
    return (min(xs), max(xs)) if xs else None


def rasterize_material_polygon(vertices_mm, resolution_mm=DEFAULT_RESOLUTION_MM) -> RasterMask:
    """Celdas usables de un retazo poligonal convexo (regla interior).

    En una franja horizontal, la parte del polígono convexo que la cruza entera
    está limitada por sus cortes en el borde superior y en el inferior: se toma
    la intersección de ambos intervalos.
    """
    resolution = _positive(resolution_mm, "La resolución")
    points = _normalized_vertices(vertices_mm)
    width = max(x for x, _ in points)
    height = max(y for _, y in points)
    if width <= 0 or height <= 0:
        raise RasterizationError("El polígono debe tener ancho y alto mayores que cero.")

    row_count = _cell_count(height, resolution)
    columns = _cell_count(width, resolution)

    spans = []
    for row in range(row_count):
        top = row * resolution
        bottom = top + resolution
        upper = _cross_section(points, top)
        lower = _cross_section(points, bottom) if bottom <= height + _EPSILON * resolution else None
        if upper is None or lower is None:
            spans.append((0, 0))
            continue
        spans.append(_interior_span(max(upper[0], lower[0]), min(upper[1], lower[1]), resolution))

    return RasterMask.from_spans(resolution, columns, spans)


def rasterize_material_circle(radius_mm, resolution_mm=DEFAULT_RESOLUTION_MM) -> RasterMask:
    """Celdas usables de un retazo circular (regla interior)."""
    resolution = _positive(resolution_mm, "La resolución")
    radius = _positive(radius_mm, "El radio")
    diameter = round(2 * radius, COORDINATE_DECIMALS)
    cells = _cell_count(diameter, resolution)

    spans = []
    for row in range(cells):
        top = row * resolution
        bottom = top + resolution
        if bottom > diameter + _EPSILON * resolution:
            spans.append((0, 0))
            continue
        # El borde de la franja más alejado del centro es el que limita el ancho.
        farthest = max(abs(top - radius), abs(bottom - radius))
        half_width = math.sqrt(max(radius * radius - farthest * farthest, 0.0))
        spans.append(_interior_span(radius - half_width, radius + half_width, resolution))

    return RasterMask.from_spans(resolution, cells, spans)


def rasterize_material(geometry, resolution_mm=DEFAULT_RESOLUTION_MM) -> RasterMask:
    """Celdas usables de una plancha (RECTANGULO) o de un retazo (las tres formas)."""
    if not isinstance(geometry, dict):
        raise RasterizationError("La geometría debe ser un objeto con el campo type.")

    shape = geometry.get("type")
    if shape == "RECTANGULO":
        width = _positive(_field(geometry, "width_mm"), "El ancho")
        height = _positive(_field(geometry, "height_mm"), "El alto")
        return rasterize_material_polygon(
            [[0, 0], [width, 0], [width, height], [0, height]], resolution_mm
        )
    if shape == "CIRCUNFERENCIA":
        return rasterize_material_circle(_field(geometry, "radius_mm"), resolution_mm)
    if shape == "POLIGONO_CONVEXO":
        return rasterize_material_polygon(_field(geometry, "vertices_mm"), resolution_mm)
    raise RasterizationError("Tipo de geometría no soportado.")