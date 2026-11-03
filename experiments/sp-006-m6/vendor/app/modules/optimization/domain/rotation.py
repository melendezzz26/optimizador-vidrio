"""Discrete geometry rotations and run-local raster cache (TA-005/006 compatible).

Coordinates follow the existing RN-04 six-decimal mm convention. Original unit
snapshots are retained unchanged; placement contours are the oriented, normalized
coordinates actually rasterized. Quarter turns are exact before RN-04 rounding.
"""
import math
from dataclasses import dataclass
from decimal import Decimal, localcontext
from types import MappingProxyType
from collections.abc import Callable, Iterable, Iterator

from .preparation import bbox_dimensions
from .problem import PieceUnit, decimal_value, geometry_snapshot
from .raster_mask import RasterMask, RasterizationError
from .rasterizer import COORDINATE_DECIMALS, rasterize_geometry, rasterize_material

INTERNAL_MAX_CELLS = 16_000_000
INTERNAL_MAX_AXIS = 4000
INTERNAL_MAX_DIMENSION_MM = 4000
INTERNAL_CACHE_BYTES = 64 * 1024 * 1024


class RasterPreparationError(ValueError):
    """Unsafe precision/range/budget: reject, never report a geometric NO_FIT."""


class RasterExtentExceeded(RasterPreparationError):
    """An oriented bounding box cannot fit any supported stock grid."""


def raster_number(value: Decimal) -> float:
    """Explicit Decimal -> legacy float bridge; reject underflow or digit loss."""
    result = float(value)
    if not math.isfinite(result) or Decimal(str(result)) != value:
        raise RasterPreparationError("Value cannot cross the raster float boundary without digit loss.")
    return result


def _coordinate(value: Decimal) -> float:
    """Arithmetic coordinates tolerate <=1e-12 mm conversion error before RN-04."""
    result = float(value)
    if not math.isfinite(result) or abs(Decimal(str(result)) - value) > Decimal("1e-12"):
        raise RasterPreparationError("Coordinate float error exceeds the explicit 1e-12 mm budget.")
    return result


def normalized_angle(angle: Decimal) -> Decimal:
    if type(angle) not in (Decimal, int) or not Decimal(angle).is_finite():
        raise ValueError("Angle must be a finite Decimal or integer.")
    return (Decimal(angle) % 360 + 360) % 360


def discrete_angles(step):
    step = decimal_value(step, "angular_step_deg", positive=True)
    if step > 360:
        raise ValueError("angular_step_deg must be at most 360.")
    # Exact multiples, even when the caller uses a lower Decimal context precision.
    with localcontext() as context:
        context.prec = max(28, len(step.as_tuple().digits) + abs(step.as_tuple().exponent) + 5)
        count = int((Decimal(360) / step).to_integral_value(rounding="ROUND_CEILING"))
    if count > 10_000:
        raise RasterPreparationError("Angular enumeration exceeds the 10000-orientation resource budget.")
    with localcontext() as context:
        context.prec = max(28, len(step.as_tuple().digits) + abs(step.as_tuple().exponent) + 5)
        return tuple(step * index for index in range(count))


def _local_vertices(geometry):
    if geometry["type"] == "RECTANGULO":
        w, h = bbox_dimensions(geometry)
        return [(Decimal(0), Decimal(0)), (w, Decimal(0)), (w, h), (Decimal(0), h)]
    vertices = [tuple(Decimal(str(v)) for v in point) for point in geometry["vertices_mm"]]
    minimum = tuple(min(p[i] for p in vertices) for i in (0, 1))
    return [(x - minimum[0], y - minimum[1]) for x, y in vertices]


def oriented_geometry(geometry, angle: Decimal):
    """Rotate about vertex centroid, then normalize bbox; positive Y points down."""
    angle = normalized_angle(angle)
    geometry = geometry_snapshot(geometry)
    if geometry["type"] == "CIRCUNFERENCIA":
        return geometry
    points = _local_vertices(geometry)
    if angle % 90 == 0:
        quarter = int(angle / 90) % 4
        rotated = [[(x, y), (-y, x), (-x, -y), (y, -x)][quarter] for x, y in points]
    else:
        # A different pivot only adds translation, removed by bbox normalization.
        # Use the vertex centroid to keep intermediate coordinates small.
        cx, cy = (sum(p[i] for p in points) / len(points) for i in (0, 1))
        radians = math.radians(raster_number(angle))
        cosine, sine = math.cos(radians), math.sin(radians)
        rotated = []
        for x, y in points:
            x, y = _coordinate(x - cx), _coordinate(y - cy)
            rotated.append((Decimal(str(x * cosine - y * sine)), Decimal(str(x * sine + y * cosine))))
    low_x, low_y = (min(p[i] for p in rotated) for i in (0, 1))
    vertices = tuple((round(_coordinate(x - low_x), COORDINATE_DECIMALS),
                      round(_coordinate(y - low_y), COORDINATE_DECIMALS)) for x, y in rotated)
    # Retain rectangular shape for exact quarter turns, with swapped dimensions.
    if geometry["type"] == "RECTANGULO" and angle % 90 == 0:
        return geometry_snapshot(dict(type="RECTANGULO", width_mm=max(x for x, _ in vertices),
                                      height_mm=max(y for _, y in vertices)))
    return geometry_snapshot(dict(type="POLIGONO_CONVEXO", vertices_mm=vertices))


def _fingerprint(geometry):
    if geometry["type"] == "CIRCUNFERENCIA":
        return ("CIRCUNFERENCIA", Decimal(str(geometry["radius_mm"])))
    return tuple(_local_vertices(geometry))


@dataclass(frozen=True)
class Orientation:
    rotation_deg: Decimal
    geometry: MappingProxyType
    mask: RasterMask


@dataclass(frozen=True)
class OrientedUnit:
    unit: PieceUnit
    orientation: Orientation


@dataclass(frozen=True)
class _OrientationView:
    """Restart at angle zero for each source; cache only actually requested masks."""
    cache: 'RasterCache'
    unit: PieceUnit
    resolution: Decimal
    angles: tuple[Decimal, ...]
    checkpoint: Callable[[], None]

    def __iter__(self) -> Iterator[OrientedUnit]:
        masks_seen = set()
        for angle in self.angles:
            self.checkpoint()
            try:
                prepared = self.cache._orientation(self.unit, self.resolution, angle)
            except RasterExtentExceeded:
                # This angle cannot fit ANY supported stock, as in TA-016.
                continue
            self.checkpoint()
            signature = (prepared.mask.columns, prepared.mask.rows)
            if signature not in masks_seen:
                masks_seen.add(signature)
                yield OrientedUnit(self.unit, prepared)


class RasterCache:
    """One instance per calculation. Immutable masks may be shared across units."""
    # Internal bit rows, independent of HU-015's JSON preview budget. A maximum
    # 4000x4000 mask occupies ~2.3 MB, not 16 million Python cell objects.
    def __init__(self, *, max_cells=INTERNAL_MAX_CELLS, max_axis=INTERNAL_MAX_AXIS, max_vertices=128,
                 max_cache_bytes=INTERNAL_CACHE_BYTES):
        self.max_cells, self.max_axis, self.max_vertices = max_cells, max_axis, max_vertices
        self.max_cache_bytes, self._cache_bytes = max_cache_bytes, 0
        self._pieces = {}
        self._materials = {}

    def check_geometry(self, geometry, resolution):
        width, height = bbox_dimensions(geometry)
        if width <= 0 or height <= 0:
            raise RasterPreparationError("Degenerate geometry after RN-04 normalization.")
        axes = [int((length / resolution).to_integral_value(rounding="ROUND_CEILING"))
                for length in (width, height)]
        if max(width, height) > INTERNAL_MAX_DIMENSION_MM or max(axes) > self.max_axis or axes[0] * axes[1] > self.max_cells:
            raise RasterExtentExceeded("Geometry exceeds the internal cutting budget (4000 mm / 4000 cells per axis, 16000000 cells).")
        if len(geometry.get("vertices_mm", ())) > self.max_vertices:
            raise RasterPreparationError("Too many geometry vertices.")
        return axes

    def _raster(self, geometry, resolution, *, material=False):
        columns, rows = self.check_geometry(geometry, resolution)
        # Conservative CPython int-row allocation bound, including tuple slots.
        # Check BEFORE allocating and bound all retained orientations/materials.
        estimated = rows * (32 + 4 * ((columns + 29) // 30) + 8) + 4096 + len(geometry.get('vertices_mm', ())) * 512
        if self._cache_bytes + estimated > self.max_cache_bytes:
            raise RasterPreparationError("Internal cutting raster cache exceeds its 64 MiB budget.")
        try:
            mask = (rasterize_material if material else rasterize_geometry)(dict(geometry), raster_number(resolution))
            self._cache_bytes += estimated
            return mask
        except (RasterizationError, OverflowError) as error:
            raise RasterPreparationError("Geometry cannot be safely rasterized by TA-005/006.") from error

    def _orientation(self, unit: PieceUnit, resolution, angle) -> Orientation:
        key = (_fingerprint(unit.geometry), resolution, angle)
        if key not in self._pieces:
            geometry = oriented_geometry(unit.geometry, angle)
            self.check_geometry(geometry, resolution)
            self._pieces[key] = Orientation(angle, geometry, self._raster(geometry, resolution))
        return self._pieces[key]

    def base(self, unit: PieceUnit, resolution) -> Orientation:
        """Normalized zero-degree base, shared with the subsequent TA-016 search."""
        resolution = decimal_value(resolution, 'resolution_mm', positive=True)
        self.check_geometry(unit.geometry, resolution)
        return self._orientation(unit, resolution, Decimal(0))

    def iter_orientations(self, unit: PieceUnit, resolution, step, *, checkpoint=None) -> Iterable[OrientedUnit]:
        """Shared, reiterable lazy TA-016 contract; same order/full-mask dedup.

        Constructing this view validates bounds/angles without rasterizing. A
        fresh iterator starts at the first angle even after another source failed.
        """
        resolution = decimal_value(resolution, "resolution_mm", positive=True)
        self.check_geometry(unit.geometry, resolution)
        angles = discrete_angles(step)
        if unit.shape_type == "CIRCUNFERENCIA":
            angles = (Decimal(0),)
        return _OrientationView(self, unit, resolution, angles, checkpoint if checkpoint is not None else lambda: None)

    def orientations(self, unit: PieceUnit, resolution, step) -> tuple[OrientedUnit, ...]:
        """Historical eager tuple adapter; metrics/confirmation remain compatible."""
        return tuple(self.iter_orientations(unit, resolution, step))

    def material(self, stock, resolution):
        resolution = decimal_value(resolution, "resolution_mm", positive=True)
        key = (_fingerprint(stock.geometry), resolution)
        if key not in self._materials:
            # Geometry retains the original shape; legacy normalizes polygon origins.
            self._materials[key] = self._raster(stock.geometry, resolution, material=True)
        return self._materials[key]
