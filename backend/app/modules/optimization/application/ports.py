from dataclasses import dataclass
from typing import Callable, Protocol

from ..domain.raster_mask import RasterMask
from ..domain.problem import StockCandidate
from decimal import Decimal


class CompatibleStockProvider(Protocol):
    """Read-only logical lookup, ordered remnants then sheets; no reservation."""

    def list_compatible(self, group_key: tuple[int, Decimal]) -> tuple[StockCandidate, ...]: ...


class OptimizationOrders(Protocol):
    def get_order(self, id_pedido: int) -> dict | None: ...

    def start_pending(self, id_pedido: int, validate: Callable[[dict], None]) -> None: ...

    def validate_piece(self, piece: dict) -> None: ...


@dataclass(frozen=True)
class RasterizedPiece:
    piece: dict
    mask: RasterMask
