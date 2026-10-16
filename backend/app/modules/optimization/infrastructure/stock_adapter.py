"""Inventory's public read-only DTO boundary, without importing its Infrastructure.

One logical lookup uses two catalogue reads in one read_transaction. Inventory
does not yet expose filtered batch reads; filtering here avoids inventing a new
cross-module SQL API. Application caches this result per material key per run.
"""
from decimal import Decimal

from app.modules.inventory.application.ports import InventoryRepository

from ..domain.problem import MaterialSource, StockCandidate


def _canonical_measure(value):
    """T1 geometry accepts JSON numbers. Fail rather than silently round NUMERIC."""
    decimal = Decimal(value)
    number = int(decimal) if decimal == decimal.to_integral_value() else float(decimal)
    if Decimal(str(number)) != decimal:
        raise ValueError("Inventory dimension cannot cross the canonical JSON boundary exactly.")
    return number


class InventoryStockAdapter:
    def __init__(self, inventory: InventoryRepository):
        self.inventory = inventory

    def list_compatible(self, group_key):
        glass, thickness = group_key
        with self.inventory.read_transaction():
            remnants = [r for r in self.inventory.list_retazos()
                        if r.estado and (r.id_tipo_vidrio, r.espesor_mm) == (glass, thickness)]
            sheets = [s for s in self.inventory.list_planchas()
                      if s.estado and s.cantidad > 0 and (s.id_tipo_vidrio, s.espesor_mm) == (glass, thickness)]
        # PLAN §7: date DESC, persisted ID DESC, physical unit ASC.
        remnants.sort(key=lambda r: (r.fecha_registro, r.id_retazo), reverse=True)
        sheets.sort(key=lambda s: (s.fecha_registro, s.id_plancha), reverse=True)
        result = [StockCandidate(
            source=MaterialSource.REMNANT, material_id=r.id_retazo, physical_unit_index=1,
            glass_type_id=glass, thickness_mm=thickness, geometry=r.geometria, area_mm2=r.area_mm2,
        ) for r in remnants]
        for sheet in sheets:
            geometry = dict(type="RECTANGULO", width_mm=_canonical_measure(sheet.ancho_mm),
                            height_mm=_canonical_measure(sheet.alto_mm))
            for index in range(1, sheet.cantidad + 1):
                result.append(StockCandidate(
                    source=MaterialSource.SHEET, material_id=sheet.id_plancha, physical_unit_index=index,
                    glass_type_id=glass, thickness_mm=thickness, geometry=geometry,
                    area_mm2=sheet.ancho_mm * sheet.alto_mm,
                ))
        return tuple(result)
