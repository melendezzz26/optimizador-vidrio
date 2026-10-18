from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List, Dict, Any

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
