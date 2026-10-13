"""Orders adapter that delegates candidate rules and reads to Inventory."""

from collections.abc import Callable, Sequence
from typing import Any

from sqlalchemy.orm import Session

from app.modules.inventory.application.stock_compatibility import StockCompatibilityService
from app.modules.inventory.infrastructure.repository import SqlAlchemyInventoryRepository


class InventoryStockCandidateChecker:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        repository = SqlAlchemyInventoryRepository(session_factory)
        self._service = StockCompatibilityService(repository)

    def find_missing_candidate_indexes(self, pieces: Sequence[dict[str, Any]]) -> list[int]:
        return self._service.find_missing_candidate_indexes(pieces)
