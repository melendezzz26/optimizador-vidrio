from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List, Dict, Any
from datetime import date
from enum import Enum
from typing import Protocol, Sequence


class OrderMutationResult(Enum):
    UPDATED = "updated"
    NOT_FOUND = "not_found"
    STATE_CONFLICT = "state_conflict"


class StockCandidateChecker(Protocol):
    """Read-only boundary used by Orders to ask Inventory about stock candidates."""

    def find_missing_candidate_indexes(self, pieces: Sequence[Dict[str, Any]]) -> list[int]: ...

class OrderRepositoryPort(ABC):
    @abstractmethod
    def validate_catalog(self, id_tipo_vidrio: int, espesor_mm: Decimal) -> bool:
        pass

    @abstractmethod
    def create_order(self, id_usuario: int, piezas: List[Dict[str, Any]], *, id_cliente: int) -> int:
        pass

    @abstractmethod
    def get_order(self, id_pedido: int) -> Dict[str, Any] | None:
        pass

    @abstractmethod
    def list_orders(self, limit: int, offset: int, estado: str | None = None, cliente: str | None = None, fecha: date | None = None) -> dict:
        pass

    @abstractmethod
    def update_order(self, id_pedido: int, piezas: List[Dict[str, Any]]) -> OrderMutationResult:
        pass

    @abstractmethod
    def cancel_order(self, id_pedido: int) -> OrderMutationResult:
        pass
