"""Frontera de validación canónica de piezas ya persistidas, sin consultar stock."""
from decimal import Decimal

from ..domain.geometry import GeometryValidator


def validate_persisted_piece(piece: dict) -> None:
    for key in ("id_pedido", "id_pieza", "id_tipo_vidrio", "cantidad"):
        value = piece.get(key)
        if type(value) is not int or not 0 < value <= 2147483647:
            raise ValueError("La pieza persistida contiene identificadores o cantidad inválidos.")
    thickness = piece.get("espesor_mm")
    if type(thickness) not in (int, float, Decimal):
        raise ValueError("El espesor persistido no es válido.")
    thickness = Decimal(str(thickness))
    if not thickness.is_finite() or thickness <= 0:
        raise ValueError("El espesor persistido debe ser finito y positivo.")
    geometry = piece.get("geometria")
    if not isinstance(geometry, dict) or geometry.get("type") != piece.get("tipo_forma"):
        raise ValueError("La forma y geometría persistidas no coinciden.")
    shape = geometry["type"]
    if shape == "RECTANGULO" and set(geometry) == {"type", "width_mm", "height_mm"}:
        GeometryValidator.validate_rectangle(geometry["width_mm"], geometry["height_mm"])
    elif shape == "CIRCUNFERENCIA" and set(geometry) == {"type", "radius_mm"}:
        GeometryValidator.validate_circle(geometry["radius_mm"])
    elif shape == "POLIGONO_CONVEXO" and set(geometry) == {"type", "vertices_mm"}:
        GeometryValidator.validate_convex_polygon(geometry["vertices_mm"])
    else:
        raise ValueError("La geometría persistida no corresponde al formato canónico soportado.")
