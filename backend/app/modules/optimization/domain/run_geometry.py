"""HU-017: bounded run-local bases before search; no layouts or candidate scan."""
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from .problem import OptimizationConfig, OptimizationProblem, PieceUnit, StockCandidate
from .raster_mask import RasterMask
from .rasterizer import COORDINATE_DECIMALS
from .rotation import Orientation, RasterCache, discrete_angles, oriented_geometry, raster_number


@dataclass(frozen=True, kw_only=True)
class PreparedRunGeometry:
    """Bases reference the immutable problem/config, never live Orders or UI state.

    Only the private, run-local cache grows on demand within its original budget.
    No mutable cache/layout is shared between methods or invocations. External
    mask descriptors and their retention are a separate visual-stream contract.
    """
    problem: OptimizationProblem
    piece_bases: Mapping[tuple[int, int], Orientation]
    material_bases: Mapping[tuple, RasterMask]
    _cache: RasterCache
    _checkpoint: Callable[[], None]
    coordinate_decimals: int = COORDINATE_DECIMALS

    @property
    def config(self) -> OptimizationConfig:
        return self.problem.config

    def orientations(self, unit: PieceUnit):
        return self._cache.iter_orientations(unit, self.config.resolution_mm,
            self.config.angular_step_deg, checkpoint=self._checkpoint)

    def material(self, stock: StockCandidate) -> RasterMask:
        return self.material_bases[stock.identity]


def prepare_run_geometry(problem: OptimizationProblem, *, cache=None, checkpoint=None) -> PreparedRunGeometry:
    """Validate all geometries, then allocate only bases, with bounded checkpoints.

    Reuses TA-005/006 normalization and TA-016 caches; does not enumerate layouts,
    positions or rotated masks. Preparing available sources is not evaluating
    their candidates. Quantities/identical figures share the existing mask keys.
    """
    cache = cache if cache is not None else RasterCache()
    checkpoint = checkpoint if checkpoint is not None else lambda: None
    resolution = problem.config.resolution_mm
    raster_number(resolution)
    discrete_angles(problem.config.angular_step_deg)
    pieces = {(unit.order_id, unit.piece_id): unit for unit in problem.units}
    stocks = {stock.identity: stock for group in problem.groups for stock in group.stock_candidates}
    for item in (*pieces.values(), *stocks.values()):
        checkpoint()
        cache.check_geometry(item.geometry, resolution)
        cache.check_geometry(oriented_geometry(item.geometry, 0), resolution)
    piece_bases, material_bases = {}, {}
    for key, unit in pieces.items():
        checkpoint()
        piece_bases[key] = cache.base(unit, resolution)
        checkpoint()
    for key, stock in stocks.items():
        checkpoint()
        material_bases[key] = cache.material(stock, resolution)
        checkpoint()
    return PreparedRunGeometry(problem=problem, piece_bases=MappingProxyType(piece_bases),
        material_bases=MappingProxyType(material_bases), _cache=cache, _checkpoint=checkpoint)
