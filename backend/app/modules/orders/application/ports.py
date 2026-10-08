from abc import ABC, abstractmethod
from typing import List, Dict, Any

class OrderRepositoryPort(ABC):
    @abstractmethod
    def validate_catalog(self, id_tipo_vidrio: int, espesor_mm: float) -> bool:
        pass

    @abstractmethod
    def create_order(self, id_usuario: int, id_tipo_vidrio: int, espesor_mm: float, piezas: List[Dict[str, Any]]) -> int:
        pass
