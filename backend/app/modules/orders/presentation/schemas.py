from typing import List, Union, Literal
from pydantic import BaseModel, Field, conint, conlist

class RectanguloSchema(BaseModel):
    tipo_forma: Literal["RECTANGULO"]
    cantidad: conint(gt=0)
    width_mm: float = Field(gt=0)
    height_mm: float = Field(gt=0)

class CircunferenciaSchema(BaseModel):
    tipo_forma: Literal["CIRCUNFERENCIA"]
    cantidad: conint(gt=0)
    radius_mm: float = Field(gt=0)

class PoligonoConvexoSchema(BaseModel):
    tipo_forma: Literal["POLIGONO_CONVEXO"]
    cantidad: conint(gt=0)
    vertices_mm: conlist(conlist(float, min_length=2, max_length=2), min_length=3)

PiezaSchema = Union[RectanguloSchema, CircunferenciaSchema, PoligonoConvexoSchema]

class CreateOrderRequest(BaseModel):
    id_tipo_vidrio: conint(gt=0)
    espesor_mm: float = Field(gt=0)
    piezas: conlist(PiezaSchema, min_length=1)

class CreateOrderResponse(BaseModel):
    id_pedido: int
    estado: str
