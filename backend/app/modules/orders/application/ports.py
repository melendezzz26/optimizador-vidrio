from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List, Dict, Any, Callable, Protocol
from datetime import date
from enum import Enum


class OrderMutationResult(Enum):
    UPDATED = "updated"
    NOT_FOUND = "not_found"
    STATE_CONFLICT = "state_conflict"


class OrderOptimizationPort(Protocol):
    def get_order(self, id_pedido: int) -> Dict[str, Any] | None: ...

    def start_optimization(
        self, id_pedido: int, validate: Callable[[dict], None]
    ) -> OrderMutationResult:
        """Transición atómica; valida el snapshot vigente antes del commit.

        Ausencia/conflicto no escriben. Error de validación/commit revierte todo.
        El callback no escribe ni rasteriza; SQL queda encapsulado en Orders.
        """
        ...

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
