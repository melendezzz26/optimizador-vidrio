from typing import Annotated, Literal
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

PositiveNumber = Annotated[float, Field(strict=True, gt=0, allow_inf_nan=False)]
Coordinate = Annotated[float, Field(strict=True, allow_inf_nan=False)]
PositiveId = Annotated[int, Field(strict=True, gt=0, le=2147483647)]


class InputSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PieceInput(InputSchema):
    id_tipo_vidrio: PositiveId
    espesor_mm: PositiveNumber


class RectanguloSchema(PieceInput):
    tipo_forma: Literal["RECTANGULO"]
    cantidad: PositiveId
    width_mm: PositiveNumber
    height_mm: PositiveNumber


class CircunferenciaSchema(PieceInput):
    tipo_forma: Literal["CIRCUNFERENCIA"]
    cantidad: PositiveId
    radius_mm: PositiveNumber


class PoligonoConvexoSchema(PieceInput):
    tipo_forma: Literal["POLIGONO_CONVEXO"]
    cantidad: PositiveId
    vertices_mm: list[Annotated[list[Coordinate], Field(min_length=2, max_length=2)]] = Field(min_length=3)


PiezaSchema = Annotated[
    RectanguloSchema | CircunferenciaSchema | PoligonoConvexoSchema,
    Field(discriminator="tipo_forma"),
]


class CreateOrderRequest(InputSchema):
    piezas: list[PiezaSchema] = Field(min_length=1)


class CreateOrderResponse(BaseModel):
    id_pedido: int
    estado: Literal["PENDIENTE"]


class PieceResponse(BaseModel):
    id_pieza: int
    id_pedido: int
    id_tipo_vidrio: int
    espesor_mm: Decimal
    tipo_forma: Literal["RECTANGULO", "CIRCUNFERENCIA", "POLIGONO_CONVEXO"]
    cantidad: int
    dimensiones: dict | None
    geometria: dict
    area_mm2: Decimal


class OrderResponse(BaseModel):
    id_pedido: int
    fecha_registro: datetime
    estado: Literal["PENDIENTE", "EN_OPTIMIZACION", "OPTIMIZADO", "CONFIRMADO", "CANCELADO"]
    id_usuario_registro: int
    piezas: list[PieceResponse]
