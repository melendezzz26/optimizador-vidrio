"""Validación pública tipo–espesor, reutilizable por Pedidos sin otra lista."""

from decimal import Decimal

from ..domain.exceptions import InventoryNotFoundError, InventoryValidationError
from .ports import GlassCatalog


def validate_tipo_espesor(
    catalog: GlassCatalog, id_tipo_vidrio: int, espesor_mm: Decimal | int,
    *, require_active: bool = True,
) -> Decimal:
    """Valida contra el catálogo persistido dentro de la transacción del llamador."""
    if isinstance(id_tipo_vidrio, bool) or not isinstance(id_tipo_vidrio, int) or id_tipo_vidrio <= 0:
        raise InventoryValidationError("id_tipo_vidrio debe ser un entero positivo.")
    if isinstance(espesor_mm, bool) or not isinstance(espesor_mm, (Decimal, int)):
        raise InventoryValidationError("espesor_mm debe ser Decimal o entero, no booleano.")
    thickness = Decimal(espesor_mm)
    if not thickness.is_finite() or thickness <= 0:
        raise InventoryValidationError("espesor_mm debe ser finito y mayor que cero.")
    tipo = catalog.get_tipo_vidrio(id_tipo_vidrio)
    if tipo is None:
        raise InventoryNotFoundError("Tipo de vidrio inexistente.")
    if require_active and not tipo.estado:
        raise InventoryValidationError("El tipo de vidrio debe estar activo.")
    if thickness not in tipo.espesores_mm:
        raise InventoryValidationError("La combinación de tipo de vidrio y espesor no está admitida.")
    return thickness
