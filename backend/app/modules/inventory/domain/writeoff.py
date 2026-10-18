"""Tipos y validaciones puras para las bajas manuales de inventario."""

from dataclasses import dataclass
from enum import Enum

from .exceptions import InventoryValidationError


class TipoEventoBajaManual(str, Enum):
    """Categorías permitidas para una baja manual de HU-014."""

    BAJA_ROTURA = "BAJA_ROTURA"
    BAJA_MERMA = "BAJA_MERMA"
    BAJA_ERROR_REGISTRO = "BAJA_ERROR_REGISTRO"
    BAJA_RETIRO = "BAJA_RETIRO"


@dataclass(frozen=True, slots=True, kw_only=True)
class BajaManual:
    """Datos validados de una baja manual, sin identidad ni persistencia.

    El usuario y la fecha se asignan en Application a partir de la sesión y
    del reloj del servidor. El cliente aporta categoría, motivo, nota y cantidad
    de plancha. En retazo la cantidad es siempre una unidad.
    """

    tipo_evento: TipoEventoBajaManual
    motivo: str
    observacion: str | None = None
    cantidad_afectada: int | None = None

    def __post_init__(self) -> None:
        if self.cantidad_afectada is not None and (
            type(self.cantidad_afectada) is not int or self.cantidad_afectada <= 0
        ):
            raise InventoryValidationError("cantidad_afectada debe ser un entero positivo.")
        try:
            event = TipoEventoBajaManual(self.tipo_evento)
        except (TypeError, ValueError) as exc:
            raise InventoryValidationError("tipo_evento no es una baja manual admitida.") from exc
        object.__setattr__(self, "tipo_evento", event)

        if not isinstance(self.motivo, str) or not self.motivo.strip():
            raise InventoryValidationError("motivo debe explicar la baja y no puede estar vacío.")
        object.__setattr__(self, "motivo", self.motivo.strip())

        if self.observacion is not None and not isinstance(self.observacion, str):
            raise InventoryValidationError("observacion debe ser texto o None.")
