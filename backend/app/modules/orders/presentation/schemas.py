from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field

PositiveNumber = Annotated[float, Field(strict=True, gt=0, allow_inf_nan=False)]
Coordinate = Annotated[float, Field(strict=True, allow_inf_nan=False)]
PositiveId = Annotated[int, Field(strict=True, gt=0, le=2147483647)]


class InputSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RectanguloSchema(InputSchema):
    tipo_forma: Literal["RECTANGULO"]
    cantidad: PositiveId
    width_mm: PositiveNumber
    height_mm: PositiveNumber


class CircunferenciaSchema(InputSchema):
    tipo_forma: Literal["CIRCUNFERENCIA"]
    cantidad: PositiveId
    radius_mm: PositiveNumber


class PoligonoConvexoSchema(InputSchema):
    tipo_forma: Literal["POLIGONO_CONVEXO"]
    cantidad: PositiveId
    vertices_mm: list[Annotated[list[Coordinate], Field(min_length=2, max_length=2)]] = Field(min_length=3)


PiezaSchema = Annotated[
    RectanguloSchema | CircunferenciaSchema | PoligonoConvexoSchema,
    Field(discriminator="tipo_forma"),
]


class CreateOrderRequest(InputSchema):
    id_tipo_vidrio: PositiveId
    espesor_mm: PositiveNumber
    piezas: list[PiezaSchema] = Field(min_length=1)


class CreateOrderResponse(BaseModel):
    id_pedido: int
    estado: Literal["PENDIENTE"]
