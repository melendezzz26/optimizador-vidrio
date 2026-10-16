"""Pure validation of the stored solution; no First Fit search or inventory I/O."""
from dataclasses import dataclass, replace

from .problem import MaterialSource, StockCandidate
from .rotation import discrete_angles, oriented_geometry
from .metrics import calculate_metrics


@dataclass(frozen=True, kw_only=True)
class MaterialConsumption:
    stock: StockCandidate
    unit_indices: tuple[int, ...]

    @property
    def quantity(self):
        return len(self.unit_indices)


def consumption_groups(result):
    if not result.complete or result.placed_units != result.total_units:
        raise ValueError("Confirmation requires every requested unit placed.")
    groups = {}
    # materials_used deduplicates (source,id,physical_index), NEVER count placements.
    for stock in result.materials_used:
        key = stock.source, stock.material_id
        groups.setdefault(key, []).append(stock)
    output = []
    for key in sorted(groups, key=lambda k: (k[0] is MaterialSource.REMNANT, k[1])):
        stocks = sorted(groups[key], key=lambda s: s.physical_unit_index)
        first = stocks[0]
        if any(replace(s, physical_unit_index=first.physical_unit_index) != first for s in stocks):
            raise ValueError("Physical units of one stock row must have identical material snapshots.")
        indices = tuple(s.physical_unit_index for s in stocks)
        if any(type(i) is not int or not 0 < i <= 2147483647 for i in indices) or len(set(indices)) != len(indices):
            raise ValueError("Invalid physical stock unit identity.")
        if first.source is MaterialSource.REMNANT and indices != (1,):
            raise ValueError("A remnant is one physical unit.")
        output.append(MaterialConsumption(stock=first, unit_indices=indices))
    return tuple(output)


def validate_stored_geometry(result, minimum_width, minimum_height, stored_residuals):
    """Revalidate raster/layout and residual proof, without moving ANY placement."""
    angles = set(discrete_angles(result.problem.config.angular_step_deg))
    for p in result.placements:
        if p.rotation_deg not in angles or oriented_geometry(p.piece.geometry, p.rotation_deg) != p.geometry:
            raise ValueError("Stored contour does not match the original piece and configured rotation.")
    checked, residuals = calculate_metrics(result, minimum_width, minimum_height)
    if residuals != tuple(stored_residuals):
        raise ValueError("Stored residual proposals cannot be reproduced from the actual free raster.")
    if result.metrics is not None and result.metrics != checked.metrics:
        raise ValueError("Stored metrics do not match placements and residual proposals.")
    return residuals
