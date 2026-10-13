"""Servicio de dominio para validar la compatibilidad geométrica pre-raster."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class BoundingBox:
    """Caja envolvente mínima alineada a los ejes."""
    width_mm: Decimal
    height_mm: Decimal


class StockCompatibilityValidator:
    """
    Servicio de Dominio puro para SP-005 y HU-008.
    Evalúa la viabilidad geométrica pre-raster individual de cada pieza frente al stock.
    No consume inventario.
    """

    @staticmethod
    def calculate_bounding_box(piece: dict[str, Any]) -> BoundingBox:
        """
        Calcula las dimensiones envolventes mínimas (ancho x alto) en Decimal.
        Soporta RECTANGULO, CIRCUNFERENCIA y POLIGONO_CONVEXO según SP-005.
        """
        shape_type = piece.get("tipo_forma")
        dimensions = piece.get("dimensiones") or {}

        if shape_type == "RECTANGULO":
            w = Decimal(str(dimensions.get("width_mm", piece.get("ancho_mm", "0.0"))))
            h = Decimal(str(dimensions.get("height_mm", piece.get("alto_mm", "0.0"))))
            return BoundingBox(width_mm=w, height_mm=h)

        elif shape_type == "CIRCUNFERENCIA":
            radius = Decimal(str(dimensions.get("radius_mm", piece.get("radio_mm", "0.0"))))
            diameter = radius * Decimal("2.0")
            return BoundingBox(width_mm=diameter, height_mm=diameter)

        elif shape_type == "POLIGONO_CONVEXO":
            vertices: list[list[float]] = (
                dimensions.get("vertices_mm")
                or piece.get("geometria", {}).get("vertices_mm", [])
            )
            if not vertices or len(vertices) < 3:
                raise ValueError("Un POLIGONO_CONVEXO debe contener al menos 3 vértices.")

            xs = [Decimal(str(v[0])) for v in vertices]
            ys = [Decimal(str(v[1])) for v in vertices]
            w = max(xs) - min(xs)
            h = max(ys) - min(ys)
            return BoundingBox(width_mm=w, height_mm=h)

        # Fallback para estructuras genéricas
        w = Decimal(str(piece.get("width_mm", "0.0")))
        h = Decimal(str(piece.get("height_mm", "0.0")))
        return BoundingBox(width_mm=w, height_mm=h)

    @staticmethod
    def fits_geometrically(
        box: BoundingBox,
        stock_width_mm: Decimal,
        stock_height_mm: Decimal,
    ) -> bool:
        """
        SP-005: Evalúa si la Bounding Box cabe en el stock permitiendo rotación ortogonal (90°).
        """
        # Orientación original
        if box.width_mm <= stock_width_mm and box.height_mm <= stock_height_mm:
            return True

        # Orientación rotada 90°
        if box.width_mm <= stock_height_mm and box.height_mm <= stock_width_mm:
            return True

        return False