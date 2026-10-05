"""Contratos puros de Inventory; no son schemas HTTP ni modelos de persistencia.

Los PATCH usan None exclusivamente como omisión (ningún campo editable admite
NULL). Presentation deberá rechazar NULL explícito; False y 0 sí son cambios.
Las medidas se normalizan a Decimal en el servicio; también se admiten int.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateTipoVidrio:
    nombre: str
    descripcion: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class TipoVidrioData:
    id_tipo_vidrio: int
    nombre: str
    descripcion: str | None
    estado: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class CreatePlancha:
    ancho_mm: Decimal | int
    alto_mm: Decimal | int
    espesor_mm: Decimal | int
    cantidad: int
    id_tipo_vidrio: int


@dataclass(frozen=True, slots=True, kw_only=True)
class UpdatePlancha:
    ancho_mm: Decimal | int | None = None
    alto_mm: Decimal | int | None = None
    espesor_mm: Decimal | int | None = None
    cantidad: int | None = None
    estado: bool | None = None
    id_tipo_vidrio: int | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class PlanchaData:
    id_plancha: int
    ancho_mm: Decimal
    alto_mm: Decimal
    espesor_mm: Decimal
    cantidad: int
    estado: bool
    fecha_registro: datetime
    id_tipo_vidrio: int


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateRetazo:
    codigo: str
    espesor_mm: Decimal | int
    geometria: dict[str, object]
    id_tipo_vidrio: int


@dataclass(frozen=True, slots=True, kw_only=True)
class UpdateRetazo:
    codigo: str | None = None
    espesor_mm: Decimal | int | None = None
    geometria: dict[str, object] | None = None
    estado: bool | None = None
    id_tipo_vidrio: int | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class RetazoData:
    id_retazo: int
    codigo: str
    espesor_mm: Decimal
    geometria: dict[str, object]
    area_mm2: Decimal
    estado: bool
    fecha_registro: datetime
    id_tipo_vidrio: int
    id_ejecucion_origen: int | None
