"""Read-only application service for per-piece pre-raster stock checks."""

from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from app.modules.inventory.application.dto import PlanchaData, RetazoData
from app.modules.inventory.application.ports import InventoryRepository
from app.modules.inventory.domain.services.stock_compatibility_validator import (
    StockCompatibilityValidator,
)


class StockCompatibilityService:
    """Checks each requested piece independently against compatible inventory."""

    def __init__(self, repository: InventoryRepository) -> None:
        self._repository = repository

    def find_missing_candidate_indexes(self, pieces: Sequence[dict[str, Any]]) -> list[int]:
        """Return zero-based indexes for pieces without an individual candidate."""
        missing: list[int] = []
        stock_by_material: dict[
            tuple[int, Decimal], tuple[list[PlanchaData], list[RetazoData]],
        ] = {}

        with self._repository.read_transaction():
            for index, piece in enumerate(pieces):
                material = (int(piece["id_tipo_vidrio"]), Decimal(str(piece["espesor_mm"])))
                stock = stock_by_material.get(material)
                if stock is None:
                    stock = self._repository.get_compatible_stock(*material)
                    stock_by_material[material] = stock

                if not self._piece_has_candidate(piece, *stock):
                    missing.append(index)

        return missing

    @staticmethod
    def _piece_has_candidate(
        piece: dict[str, Any], planchas: list[PlanchaData], retazos: list[RetazoData],
    ) -> bool:
        piece_box = StockCompatibilityValidator.calculate_bounding_box(piece)
        for plancha in planchas:
            if StockCompatibilityValidator.fits_geometrically(
                piece_box, plancha.ancho_mm, plancha.alto_mm,
            ):
                return True

        for retazo in retazos:
            retazo_box = StockCompatibilityValidator.calculate_bounding_box(retazo.geometria)
            if StockCompatibilityValidator.fits_geometrically(
                piece_box, retazo_box.width_mm, retazo_box.height_mm,
            ):
                return True

        return False
