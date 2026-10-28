"""Optional facts about real geometry work; no HTTP, sampling or storage policy."""
from dataclasses import dataclass
from typing import Literal

from .problem import OptimizationConfig, PieceUnit, StockCandidate, Placement
from .raster_mask import RasterMask
from .rotation import Orientation


@dataclass(frozen=True, kw_only=True)
class VisualEvent:
    kind: Literal['preparation_started', 'piece_rasterizing', 'piece_ready',
        'preparation_completed', 'orientation_testing', 'source_selected', 'piece_unplaced']
    unit: PieceUnit | None = None
    stock: StockCandidate | None = None
    orientation: Orientation | None = None
    material_mask: RasterMask | None = None
    placement: Placement | None = None
    config: OptimizationConfig | None = None
    quantity: int = 0
    unique_pieces: int = 0
    material_bases: int = 0
    processed_units: int = 0
    placed_units: int = 0
    total_units: int = 0
    evaluation_index: int = 0
    score: int | None = None
