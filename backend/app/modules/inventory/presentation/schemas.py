from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, field_serializer, field_validator

from app.modules.inventory.domain.writeoff import TipoEventoBajaManual

class BaseSchema(BaseModel):
    model_config = {"extra": "forbid"}


class BajaManualRequest(BaseSchema):
    """Payload público de baja; no permite enviar usuario ni fecha."""

    tipo_evento: TipoEventoBajaManual
    motivo: str = Field(min_length=1)
    observacion: str | None = None

    @field_validator("motivo")
    @classmethod
    def motivo_no_vacio(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("motivo debe explicar la baja y no puede estar vacío")
        return value

# --- Tipos de Vidrio ---

class TipoVidrioCreate(BaseSchema):
    nombre: str = Field(max_length=100)
    descripcion: str | None = None

class TipoVidrioResponse(BaseSchema):
    id_tipo_vidrio: int
    nombre: str
    descripcion: str | None
    estado: bool
    espesores_mm: list[Decimal]

    @field_serializer("espesores_mm", when_used="json")
    def serialize_thicknesses(self, values: list[Decimal]) -> list[int | float]:
        # Conversión exclusiva de transporte: dominio/aplicación conservan Decimal.
        return [int(value) if value == value.to_integral_value() else float(value) for value in values]

# --- Geometría ---

class Rectangulo(BaseSchema):
    type: Literal["RECTANGULO"]
    width_mm: Decimal = Field(gt=0)
    height_mm: Decimal = Field(gt=0)

class Circunferencia(BaseSchema):
    type: Literal["CIRCUNFERENCIA"]
    radius_mm: Decimal = Field(gt=0)

class PoligonoConvexo(BaseSchema):
    type: Literal["POLIGONO_CONVEXO"]
    vertices_mm: list[tuple[Decimal, Decimal]] = Field(min_length=3)

Geometria = Annotated[
    Union[Rectangulo, Circunferencia, PoligonoConvexo],
    Field(discriminator="type")
]

# --- Planchas ---

class PlanchaCreate(BaseSchema):
    ancho_mm: Decimal = Field(gt=0)
    alto_mm: Decimal = Field(gt=0)
    espesor_mm: Decimal = Field(gt=0)
    cantidad: int = Field(gt=0)
    id_tipo_vidrio: int

class PlanchaPatch(BaseSchema):
    ancho_mm: Decimal | None = Field(None, gt=0)
    alto_mm: Decimal | None = Field(None, gt=0)
    espesor_mm: Decimal | None = Field(None, gt=0)
    cantidad: int | None = Field(None, ge=0)
    estado: bool | None = None
    id_tipo_vidrio: int | None = None

class PlanchaResponse(BaseSchema):
    id_plancha: int
    ancho_mm: Decimal
    alto_mm: Decimal
    espesor_mm: Decimal
    cantidad: int
    estado: bool
    fecha_registro: datetime
    id_tipo_vidrio: int

# --- Retazos ---

class RetazoCreate(BaseSchema):
    codigo: str = Field(max_length=40)
    espesor_mm: Decimal = Field(gt=0)
    geometria: Geometria
    id_tipo_vidrio: int

class RetazoPatch(BaseSchema):
    codigo: str | None = Field(None, max_length=40)
    espesor_mm: Decimal | None = Field(None, gt=0)
    geometria: Geometria | None = None
    estado: bool | None = None
    id_tipo_vidrio: int | None = None

class RetazoResponse(BaseSchema):
    id_retazo: int
    codigo: str
    espesor_mm: Decimal
    geometria: Geometria
    area_mm2: Decimal
    estado: bool
    fecha_registro: datetime
    id_tipo_vidrio: int
    id_ejecucion_origen: int | None
