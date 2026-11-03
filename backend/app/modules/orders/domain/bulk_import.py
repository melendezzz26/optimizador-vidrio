"""HU-018: interpretación de una fila del archivo de importación (SPEC-HU-018 §4 y §5).

Cada fila es ``TIPO,CANTIDAD,MEDIDAS``. Las comas separan valores, pero las de dentro
de las llaves de un polígono no: por eso no se usa un lector CSV estándar. Una fila
inválida nunca se descarta ni se completa con valores por defecto: queda OBSERVADO
con todas las causas que se puedan detectar.
"""
import math
import re
from dataclasses import dataclass, field

from .geometry import GeometryValidator
from .polygon_construction import MAX_FREE_ANGLES, MISSING_ANGLES, build_polygon

VALIDO = "VALIDO"
OBSERVADO = "OBSERVADO"
MAX_QUANTITY = 2147483647
MAX_POLYGON_SIDES = 128  # TA-037 L-04

SHAPES = {"R": "RECTANGULO", "C": "CIRCUNFERENCIA", "P": "POLIGONO_CONVEXO"}
EMPTY_ROW = "Fila vacía: escribe la pieza o vuelve a cargar el archivo sin esta fila"
_NUMBER = re.compile(r"[+-]?(\d+(\.\d*)?|\.\d+)")
_INTEGER = re.compile(r"\d+")
_GROUPS = re.compile(r"\{[^{}]*\}(,\{[^{}]*\})*")


@dataclass
class RowResult:
    fila: int
    texto: str
    estado: str = VALIDO
    tipo_forma: str | None = None
    cantidad: int | None = None
    medidas: dict | None = None
    causas: list = field(default_factory=list)


def split_values(text):
    """Separa por comas que no están dentro de llaves. ``None`` si las llaves no cierran."""
    values, current, depth = [], [], 0
    for char in text:
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                return None
        if char == "," and depth == 0:
            values.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    if depth != 0:
        return None
    values.append("".join(current).strip())
    return values


def _number(text):
    text = text.strip()
    if not _NUMBER.fullmatch(text):
        return None
    value = float(text)
    return value if math.isfinite(value) else None


def _positive(text):
    value = _number(text)
    return value if value is not None and value > 0 else None


def _quantity(text, causes):
    text = (text or "").strip()
    if not text:
        causes.append("Falta la cantidad")
        return None
    if _NUMBER.fullmatch(text) is None:
        causes.append("Cantidad inválida")
        return None
    if not _INTEGER.fullmatch(text) or not 0 < int(text) <= MAX_QUANTITY:
        causes.append("Cantidad debe ser un entero mayor a 0")
        return None
    return int(text)


def _count_measures(values, expected, causes):
    if len(values) < expected or not all(values[:expected]):
        causes.append("Faltan dimensiones")
        return False
    if len(values) > expected:
        causes.append("Sobran valores en la fila")
        return False
    return True


def _circle(values, causes):
    if not _count_measures(values, 1, causes):
        return None
    radius = _positive(values[0])
    if radius is None:
        causes.append("Radio inválido")
        return None
    try:
        GeometryValidator.validate_circle(radius)
    except ValueError as error:
        causes.append(str(error))
        return None
    return {"radius_mm": radius}


def _rectangle(values, causes):
    if not _count_measures(values, 2, causes):
        return None
    length, width = _positive(values[0]), _positive(values[1])
    if length is None:
        causes.append("Largo inválido")
    if width is None:
        causes.append("Ancho inválido")
    if length is None or width is None:
        return None
    try:
        GeometryValidator.validate_rectangle(length, width)
    except ValueError as error:
        causes.append(str(error))
        return None
    return {"width_mm": length, "height_mm": width}


def _polygon_pairs(values):
    """``{{l,a},{l,a}}`` o ``{l,a},{l,a}`` → lista de (lado, ángulo) en texto, o ``None``."""
    text = re.sub(r"\s+", "", ",".join(values))
    if text.startswith("{{") and text.endswith("}}"):
        text = text[1:-1]
    if not _GROUPS.fullmatch(text):
        return None
    pairs = []
    for group in re.findall(r"\{([^{}]*)\}", text):
        parts = group.split(",")
        if len(parts) > 2 or not parts[0]:
            return None
        pairs.append((parts[0], parts[1] if len(parts) == 2 else ""))
    return pairs


def _polygon(values, causes):
    if not values or not any(values):
        causes.append("Faltan dimensiones")
        return None
    pairs = _polygon_pairs(values)
    if pairs is None:
        causes.append("Formato de polígono inválido")
        return None
    if len(pairs) < 3:
        causes.append("Un polígono necesita al menos 3 lados")
        return None
    if len(pairs) > MAX_POLYGON_SIDES:
        causes.append(f"El polígono supera el máximo de {MAX_POLYGON_SIDES} lados")
        return None
    sides, angles = [], []
    for number, (side_text, angle_text) in enumerate(pairs, start=1):
        side = _positive(side_text)
        if side is None:
            causes.append(f"Lado {number} inválido")
        sides.append(side)
        if angle_text == "":
            angles.append(None)
            continue
        angle = _number(angle_text)
        if angle is None or not 0 < angle < 180:
            causes.append(f"Ángulo {number} inválido: debe estar entre 0 y 180")
        angles.append(angle)
    if causes:
        return None
    if sum(angle is None for angle in angles) > MAX_FREE_ANGLES:
        causes.append(MISSING_ANGLES)
        return None
    try:
        vertices = build_polygon(sides, angles)
        GeometryValidator.validate_convex_polygon(vertices)
    except ValueError as error:  # PolygonConstructionError o reglas de GeometryValidator
        causes.append(str(error))
        return None
    return {"vertices_mm": vertices}


def interpret_row(fila, texto):
    """Interpreta una fila con contenido. Nunca lanza: los errores quedan como causas."""
    row = RowResult(fila=fila, texto=texto.strip())
    causes = row.causas
    if not _has_content(row.texto):  # solo llega aquí al revalidar: nunca se descarta en silencio
        causes.append(EMPTY_ROW)
        row.estado = OBSERVADO
        return row
    values = split_values(row.texto)
    letter = (values or row.texto.split(","))[0].strip().upper()
    row.tipo_forma = SHAPES.get(letter)
    if row.tipo_forma is None:
        causes.append("Tipo de pieza desconocido")
    if values is None:
        if row.tipo_forma == "POLIGONO_CONVEXO":
            causes.append("Formato de polígono inválido")
        else:
            causes.append("Formato de fila inválido")
        row.estado = OBSERVADO
        return row
    row.cantidad = _quantity(values[1] if len(values) > 1 else "", causes)
    measures = values[2:]
    if row.tipo_forma == "CIRCUNFERENCIA":
        row.medidas = _circle(measures, causes)
    elif row.tipo_forma == "RECTANGULO":
        row.medidas = _rectangle(measures, causes)
    elif row.tipo_forma == "POLIGONO_CONVEXO":
        row.medidas = _polygon(measures, causes)
    if causes:
        row.estado, row.cantidad, row.medidas = OBSERVADO, None, None
    return row


def is_header(texto):
    """La primera fila con contenido es de títulos si no es una pieza y no tiene números."""
    first = (split_values(texto) or [texto])[0].strip().upper()
    return first not in SHAPES and not re.search(r"\d", texto)


def _has_content(texto):
    return bool(texto.strip().strip(",").strip())


def interpret_rows(rows, skip_header=True):
    """``rows``: lista de (número de fila, texto).

    Desde un archivo (``skip_header=True``) se ignoran las filas vacías y la de títulos.
    Al revalidar (``skip_header=False``) no se descarta ninguna: una fila que el usuario
    vació queda OBSERVADO, porque quitar piezas debe ser una decisión explícita.
    """
    if not skip_header:
        return [interpret_row(fila, texto) for fila, texto in rows]
    content = [(fila, texto) for fila, texto in rows if _has_content(texto)]
    if content and is_header(content[0][1]):
        content = content[1:]
    return [interpret_row(fila, texto) for fila, texto in content]