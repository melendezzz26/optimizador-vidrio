"""Read-only validity of frozen v2 inputs; feasibility belongs to the engines."""
from app.modules.inventory.domain.geometry import calculate_area_mm2

from ..domain.problem import MaterialSource
from ..domain.rotation import RasterCache, discrete_angles, raster_number


def validate_comparison_geometry(problem):
    """Reuse preparation/Inventory rules without masks, positions or fit decisions.

    Orders already validates requested contours in prepare_persisted_problem.
    Inventory owns the stricter remnant contour contract. Check all extents
    before its quadratic polygon validation. Repeated physical units need only
    one check per source; nothing is normalized back into the frozen snapshot.
    """
    resolution = problem.config.resolution_mm
    raster_number(resolution)
    discrete_angles(problem.config.angular_step_deg)
    cache = RasterCache()
    pieces = {unit.piece_id: unit for unit in problem.units}
    stocks = {(stock.source, stock.material_id): stock
              for group in problem.groups for stock in group.stock_candidates}
    for item in (*pieces.values(), *stocks.values()):
        cache.check_base_geometry(item.geometry, resolution)
    for stock in stocks.values():
        if stock.source is MaterialSource.REMNANT:
            calculate_area_mm2(stock.geometry)
