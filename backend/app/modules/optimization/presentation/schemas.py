from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

PositiveId = Annotated[int, Field(strict=True, gt=0, le=2147483647)]
PositiveNumber = Annotated[float, Field(strict=True, gt=0, allow_inf_nan=False)]
Coordinate = Annotated[float, Field(strict=True, allow_inf_nan=False)]
StoredPositiveNumber = Annotated[int, Field(strict=True, gt=0)] | PositiveNumber
StoredCoordinate = Annotated[int, Field(strict=True)] | Coordinate


class StartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id_pedido: PositiveId


class RasterizeRequest(StartRequest):
    id_pieza: PositiveId
    resolution_mm: PositiveNumber


class StartResponse(BaseModel):
    id_pedido: PositiveId
    estado: Literal["PENDIENTE"]


class RectangleGeometry(BaseModel):
    type: Literal["RECTANGULO"]
    width_mm: StoredPositiveNumber
    height_mm: StoredPositiveNumber


class CircleGeometry(BaseModel):
    type: Literal["CIRCUNFERENCIA"]
    radius_mm: StoredPositiveNumber


class PolygonGeometry(BaseModel):
    type: Literal["POLIGONO_CONVEXO"]
    vertices_mm: list[Annotated[list[StoredCoordinate], Field(min_length=2, max_length=2)]]


class RowSpans(BaseModel):
    row: int
    runs: list[Annotated[list[int], Field(min_length=2, max_length=2)]]


class RasterizeResponse(BaseModel):
    id_pedido: PositiveId
    id_pieza: PositiveId
    tipo_forma: Literal["RECTANGULO", "CIRCUNFERENCIA", "POLIGONO_CONVEXO"]
    geometria: Annotated[RectangleGeometry | CircleGeometry | PolygonGeometry, Field(discriminator="type")]
    id_tipo_vidrio: PositiveId
    espesor_mm: Decimal
    cantidad: PositiveId
    resolution_mm: PositiveNumber
    row_count: int
    columns: int
    occupied_cells: int
    spans_by_row: list[RowSpans]
