from typing import List, Dict, Any
from decimal import Decimal
from .ports import OrderMutationResult, OrderRepositoryPort
from ..domain.geometry import GeometryValidator
from ..domain.exceptions import (
    InvalidGeometryException,
    InvalidOrderException,
    OrderNotFoundException,
    OrderStateConflictException,
)
from datetime import date

class CreateOrderUseCase:
    def __init__(self, repository: OrderRepositoryPort):
        self.repository = repository

    def execute(self, id_usuario: int, piezas_raw: List[Dict[str, Any]]) -> int:
        if not piezas_raw:
            raise InvalidOrderException("El pedido debe contener al menos una pieza.")
        piezas_validadas = []
        parejas_validadas = set()

        for p in piezas_raw:
            id_tipo_vidrio = p.get("id_tipo_vidrio")
            espesor = p.get("espesor_mm")
            if type(id_tipo_vidrio) is not int or not 0 < id_tipo_vidrio <= 2147483647:
                raise InvalidOrderException("El tipo de vidrio de cada pieza debe ser un identificador válido.")
            if type(espesor) not in (int, float, Decimal):
                raise InvalidOrderException("El espesor de cada pieza debe ser numérico, finito y positivo.")
            espesor_mm = Decimal(str(espesor))
            if not espesor_mm.is_finite() or espesor_mm <= 0:
                raise InvalidOrderException("El espesor de cada pieza debe ser numérico, finito y positivo.")
            pareja = (id_tipo_vidrio, espesor_mm)
            if pareja not in parejas_validadas:
                if not self.repository.validate_catalog(id_tipo_vidrio, espesor_mm):
                    raise InvalidOrderException(f"Combinación inválida de tipo de vidrio ({id_tipo_vidrio}) y espesor ({espesor_mm}).")
                parejas_validadas.add(pareja)
            tipo_forma = p.get("tipo_forma")
            cantidad = p.get("cantidad", 0)
            if type(cantidad) is not int or not 0 < cantidad <= 2147483647:
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

            piezas_validadas[-1].update(id_tipo_vidrio=id_tipo_vidrio, espesor_mm=espesor_mm)

        return self.repository.create_order(id_usuario, piezas_validadas)


class GetOrderUseCase:
    def __init__(self, repository: OrderRepositoryPort):
        self.repository = repository

    def execute(self, id_pedido: int) -> Dict[str, Any]:
        if type(id_pedido) is not int or not 0 < id_pedido <= 2147483647:
            raise InvalidOrderException("El identificador del pedido debe ser un entero positivo válido.")
        order = self.repository.get_order(id_pedido)
        if order is None:
            raise OrderNotFoundException("Pedido no encontrado.")
        return order

class ListOrdersUseCase:
    def __init__(self, repository: OrderRepositoryPort):
        self.repository = repository

    def execute(self, page: int, limit: int, estado: str | None = None, cliente: str | None = None, fecha: date | None = None) -> Dict[str, Any]:
        # Validaciones de paginación
        if page < 1: page = 1
        if limit < 1: limit = 10

        offset = (page - 1) * limit

        result = self.repository.list_orders(
            limit=limit,
            offset=offset,
            estado=estado,
            cliente=cliente,
            fecha=fecha
        )

        return {
            "items": result["items"],
            "total": result["total"],
            "page": page,
            "limit": limit,
            "total_pages": (result["total"] + limit - 1) // limit if limit > 0 else 0
        }

    # Agrega esta nueva clase al final del archivo
class UpdateOrderUseCase:
    def __init__(self, repository: OrderRepositoryPort):
        self.repository = repository

    def execute(self, id_pedido: int, piezas_raw: List[Dict[str, Any]]) -> None:
        if type(id_pedido) is not int or not 0 < id_pedido <= 2147483647:
            raise InvalidOrderException("El identificador del pedido debe ser un entero positivo válido.")

        # Validate the command before entering the repository transaction.
        if not piezas_raw:
            raise InvalidOrderException("El pedido debe contener al menos una pieza.")
        piezas_validadas = []
        parejas_validadas = set()

        for p in piezas_raw:
            id_tipo_vidrio = p.get("id_tipo_vidrio")
            espesor = p.get("espesor_mm")
            if type(id_tipo_vidrio) is not int or not 0 < id_tipo_vidrio <= 2147483647:
                raise InvalidOrderException("El tipo de vidrio de cada pieza debe ser un identificador válido.")
            if type(espesor) not in (int, float, Decimal):
                raise InvalidOrderException("El espesor de cada pieza debe ser numérico, finito y positivo.")
            espesor_mm = Decimal(str(espesor))
            if not espesor_mm.is_finite() or espesor_mm <= 0:
                raise InvalidOrderException("El espesor de cada pieza debe ser numérico, finito y positivo.")
            pareja = (id_tipo_vidrio, espesor_mm)
            if pareja not in parejas_validadas:
                if not self.repository.validate_catalog(id_tipo_vidrio, espesor_mm):
                    raise InvalidOrderException(f"Combinación inválida de tipo de vidrio ({id_tipo_vidrio}) y espesor ({espesor_mm}).")
                parejas_validadas.add(pareja)
            tipo_forma = p.get("tipo_forma")
            cantidad = p.get("cantidad", 0)
            if type(cantidad) is not int or not 0 < cantidad <= 2147483647:
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
                piezas_validadas.append({"tipo_forma": "RECTANGULO", "cantidad": cantidad, "dimensiones": dimensiones, "geometria": geometria, "area_mm2": area})

            elif tipo_forma == "CIRCUNFERENCIA":
                r = p.get("radius_mm", 0.0)
                try:
                    area = GeometryValidator.validate_circle(r)
                except ValueError as e:
                    raise InvalidGeometryException(str(e))

                dimensiones = {"type": "CIRCUNFERENCIA", "radius_mm": r}
                geometria = {"type": "CIRCUNFERENCIA", "radius_mm": r}
                piezas_validadas.append({"tipo_forma": "CIRCUNFERENCIA", "cantidad": cantidad, "dimensiones": dimensiones, "geometria": geometria, "area_mm2": area})

            elif tipo_forma == "POLIGONO_CONVEXO":
                vertices = p.get("vertices_mm", [])
                try:
                    area = GeometryValidator.validate_convex_polygon(vertices)
                except ValueError as e:
                    raise InvalidGeometryException(str(e))

                dimensiones = None
                geometria = {"type": "POLIGONO_CONVEXO", "vertices_mm": vertices}
                piezas_validadas.append({"tipo_forma": "POLIGONO_CONVEXO", "cantidad": cantidad, "dimensiones": dimensiones, "geometria": geometria, "area_mm2": area})
            else:
                raise InvalidOrderException(f"Tipo de forma no soportado: {tipo_forma}")

            piezas_validadas[-1].update(id_tipo_vidrio=id_tipo_vidrio, espesor_mm=espesor_mm)

        # The repository's locked result is authoritative for existence/state.
        result = self.repository.update_order(id_pedido, piezas_validadas)
        if result is OrderMutationResult.NOT_FOUND:
            raise OrderNotFoundException("Pedido no encontrado.")
        if result is OrderMutationResult.STATE_CONFLICT:
            raise OrderStateConflictException(
                "El pedido cambió de estado y ya no se puede editar."
            )

class CancelOrderUseCase:
    def __init__(self, repository: OrderRepositoryPort):
        self.repository = repository

    def execute(self, id_pedido: int) -> None:
        result = self.repository.cancel_order(id_pedido)
        if result is OrderMutationResult.NOT_FOUND:
            raise OrderNotFoundException("Pedido no encontrado.")
        if result is OrderMutationResult.STATE_CONFLICT:
            raise OrderStateConflictException(
                "El pedido cambió de estado y ya no se puede cancelar."
            )
