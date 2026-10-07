from typing import List, Dict, Any
from .ports import OrderRepositoryPort
from ..domain.geometry import GeometryValidator
from ..domain.exceptions import InvalidGeometryException, InvalidOrderException

class CreateOrderUseCase:
    def __init__(self, repository: OrderRepositoryPort):
        self.repository = repository

    def execute(self, id_usuario: int, id_tipo_vidrio: int, espesor_mm: float, piezas_raw: List[Dict[str, Any]]) -> int:
        # Validate catalog
        if not self.repository.validate_catalog(id_tipo_vidrio, espesor_mm):
            raise InvalidOrderException(f"Combinación inválida de tipo de vidrio ({id_tipo_vidrio}) y espesor ({espesor_mm}).")

        piezas_validadas = []

        for p in piezas_raw:
            tipo_forma = p.get("tipo_forma")
            cantidad = p.get("cantidad", 0)
            if cantidad <= 0:
                raise InvalidOrderException("La cantidad debe ser mayor a 0.")

            if tipo_forma == "RECTANGULO":
                w = p.get("width_mm", 0.0)
                h = p.get("height_mm", 0.0)
                try:
                    area = GeometryValidator.validate_rectangle(w, h)
                except ValueError as e:
                    raise InvalidGeometryException(str(e))
                
                dimensiones = {"type": "RECTANGULO", "width_mm": w, "height_mm": h}
                geometria = {"type": "RECTANGULO", "width_mm": w, "height_mm": h}
                piezas_validadas.append({
                    "tipo_forma": "RECTANGULO",
                    "cantidad": cantidad,
                    "dimensiones": dimensiones,
                    "geometria": geometria,
                    "area_mm2": area
                })

            elif tipo_forma == "CIRCUNFERENCIA":
                r = p.get("radius_mm", 0.0)
                try:
                    area = GeometryValidator.validate_circle(r)
                except ValueError as e:
                    raise InvalidGeometryException(str(e))
                
                dimensiones = {"type": "CIRCUNFERENCIA", "radius_mm": r}
                geometria = {"type": "CIRCUNFERENCIA", "radius_mm": r}
                piezas_validadas.append({
                    "tipo_forma": "CIRCUNFERENCIA",
                    "cantidad": cantidad,
                    "dimensiones": dimensiones,
                    "geometria": geometria,
                    "area_mm2": area
                })

            elif tipo_forma == "POLIGONO_CONVEXO":
                vertices = p.get("vertices_mm", [])
                try:
                    area = GeometryValidator.validate_convex_polygon(vertices)
                except ValueError as e:
                    raise InvalidGeometryException(str(e))

                dimensiones = None
                geometria = {"type": "POLIGONO_CONVEXO", "vertices_mm": vertices}
                piezas_validadas.append({
                    "tipo_forma": "POLIGONO_CONVEXO",
                    "cantidad": cantidad,
                    "dimensiones": dimensiones,
                    "geometria": geometria,
                    "area_mm2": area
                })
            else:
                raise InvalidOrderException(f"Tipo de forma no soportado: {tipo_forma}")

        return self.repository.create_order(id_usuario, id_tipo_vidrio, espesor_mm, piezas_validadas)
