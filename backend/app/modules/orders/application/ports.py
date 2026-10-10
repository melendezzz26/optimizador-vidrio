from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List, Dict, Any
from datetime import date

class OrderRepositoryPort(ABC):
    @abstractmethod
    def validate_catalog(self, id_tipo_vidrio: int, espesor_mm: Decimal) -> bool:
        pass

    @abstractmethod
    def create_order(self, id_usuario: int, piezas: List[Dict[str, Any]]) -> int:
        pass

    @abstractmethod
    def get_order(self, id_pedido: int) -> Dict[str, Any] | None:
        pass

    @abstractmethod
    def list_orders(self, limit: int, offset: int, estado: str | None = None, cliente: str | None = None, fecha: date | None = None) -> dict:
        pass