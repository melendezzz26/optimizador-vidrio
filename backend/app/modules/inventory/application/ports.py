"""Puerto implementado posteriormente por Infrastructure."""

from contextlib import AbstractContextManager
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from .dto import PlanchaData, RetazoData, TipoVidrioData


class GlassCatalog(Protocol):
    """Lectura pública del catálogo para Inventory y futuros consumidores.

    El caso de uso llamador controla la transacción. El DTO incluye únicamente
    los espesores persistidos; un tipo sin combinaciones devuelve una tupla vacía.
    """

    def get_tipo_vidrio(self, id_tipo_vidrio: int) -> TipoVidrioData | None: ...


class InventoryRepository(GlassCatalog, Protocol):
    """Cada caso de uso se ejecuta dentro de transaction(), sin anidación.

    El adaptador abre/cierra la unidad transaccional: confirma al salir con éxito
    y revierte si falla el cuerpo O la confirmación, propagando el error. Las
    escrituras individuales pueden hacer flush, pero nunca commit independiente.
    También se cierra la transacción en consultas. No hay commit en Application.

    Los métodos devuelven snapshots DTO desconectados (incluida geometria), nunca
    entidades ORM. Las altas asignan el ID y retornan el registro completo.
    Listar incluye activos e inactivos, sin orden garantizado.

    Las comprobaciones previas no reemplazan las garantías de concurrencia:
    el adaptador debe mantener unicidad y referencias válidas en la transacción,
    traducir duplicados a InventoryConflictError y actualizaciones de registros
    desaparecidos a InventoryNotFoundError. save_* solo actualiza existentes.
    Las búsquedas por nombre/código son exactas y distinguen mayúsculas.
    """

    def transaction(self) -> AbstractContextManager[None]: ...

    def tipo_nombre_exists(self, nombre: str) -> bool: ...

    def create_tipo_vidrio(self, *, nombre: str, descripcion: str | None,
                          estado: bool) -> TipoVidrioData: ...

    def list_tipos_vidrio(self) -> list[TipoVidrioData]: ...

    def get_plancha(self, id_plancha: int) -> PlanchaData | None: ...

    def create_plancha(self, *, ancho_mm: Decimal, alto_mm: Decimal,
                       espesor_mm: Decimal, cantidad: int, estado: bool,
                       fecha_registro: datetime, id_tipo_vidrio: int) -> PlanchaData: ...

    def list_planchas(self) -> list[PlanchaData]: ...

    def save_plancha(self, data: PlanchaData) -> PlanchaData: ...

    def get_retazo(self, id_retazo: int) -> RetazoData | None: ...

    def retazo_codigo_exists(self, codigo: str, exclude_id: int | None = None) -> bool: ...

    def create_retazo(self, *, codigo: str, espesor_mm: Decimal,
                      geometria: dict[str, object], area_mm2: Decimal, estado: bool,
                      fecha_registro: datetime, id_tipo_vidrio: int,
                      id_ejecucion_origen: int | None) -> RetazoData: ...

    def list_retazos(self) -> list[RetazoData]: ...

    def save_retazo(self, data: RetazoData) -> RetazoData: ...
