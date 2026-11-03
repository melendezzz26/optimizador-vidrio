"""Read-only individual feasibility checks for prepared material groups."""
from dataclasses import dataclass

from .packing import _empty_layout
from .rotation import RasterCache


@dataclass(frozen=True)
class PreflightIssue:
    code: str
    piece_id: int | None = None


@dataclass(frozen=True)
class PreflightResult:
    errors: tuple[PreflightIssue, ...]

    @property
    def can_optimize(self):
        return not self.errors

    @property
    def affected_piece_ids(self):
        return tuple(sorted({issue.piece_id for issue in self.errors if issue.piece_id is not None}))


def preflight(groups, config):
    """Check each distinct piece against an empty compatible source.

    The same raster, angle and margin rules as packing are used. Separation
    affects occupied pieces only and therefore has no effect on an empty source.
    Resource/raster errors propagate; they are not evidence of impossibility.
    """
    groups = tuple(groups)
    if not groups:
        return PreflightResult((PreflightIssue("EMPTY_ORDER"),))
    errors = []
    cache = RasterCache()
    for group in sorted(groups, key=lambda group: group.key):
        pieces = {unit.piece_id: unit for unit in group.units}
        for piece_id, unit in sorted(pieces.items()):
            if not group.stock_candidates:
                errors.append(PreflightIssue("NO_COMPATIBLE_STOCK", piece_id))
                continue
            orientations = cache.iter_orientations(unit, config.resolution_mm, config.angular_step_deg)
            fits = False
            for stock in group.stock_candidates:
                layout = _empty_layout(cache.material(stock, config.resolution_mm), config)
                if any(layout.first_position(oriented.orientation.mask) is not None for oriented in orientations):
                    fits = True
                    break
            if not fits:
                errors.append(PreflightIssue("PIECE_DOES_NOT_FIT", piece_id))
    return PreflightResult(tuple(sorted(errors, key=lambda issue: (issue.piece_id, issue.code))))
