"""Pure First Fit: candidate -> orientation -> row -> column, first valid wins.

No stock writes, lifecycle transitions, metrics or HTTP. Partial patterns remain
diagnostic OptimizationResult values; only the outer lifecycle can confirm a run.
"""
from dataclasses import dataclass, replace
from decimal import Decimal, localcontext
from typing import Callable, Literal

from .placement import SheetLayout
from .preparation import prepare_group_units
from .problem import MaterialSource, OptimizationProblem, OptimizationResult, PieceUnit, Placement
from .rotation import RasterCache, raster_number


@dataclass(frozen=True, kw_only=True)
class FirstFitEvent:
    """In-process milestones. Application may adapt them to the T1 wire schema."""
    kind: Literal["group_started", "piece_started", "piece_placed", "group_completed"]
    group_key: tuple[int, Decimal]
    placed_units: int
    total_units: int
    unit: PieceUnit | None = None
    placement: Placement | None = None


def _distance_cells(distance: Decimal, resolution: Decimal) -> int:
    # Exact rational ceil, including distances smaller than legacy float epsilon.
    dn, dd = distance.as_integer_ratio()
    rn, rd = resolution.as_integer_ratio()
    numerator, denominator = dn * rd, dd * rn
    return (numerator + denominator - 1) // denominator


def _empty_layout(material, config):
    margin = _distance_cells(config.margin_mm, config.resolution_mm)
    separation = _distance_cells(config.separation_mm, config.resolution_mm)
    # Beyond this distance every cell is blocked; avoid unbounded dilation work.
    separation = min(separation, max(material.row_count, material.columns))
    if 2 * margin >= min(material.row_count, material.columns):
        empty = (0,) * material.row_count
        return SheetLayout(material, empty, empty, empty, separation)
    resolution = raster_number(config.resolution_mm)
    # Pass exact cell counts through TA-007's public factory; never round distance down.
    return SheetLayout.empty(material, margin_mm=margin * resolution,
                             separation_mm=separation * resolution)


def _coordinate(index, resolution):
    with localcontext() as context:
        context.prec = max(28, len(resolution.as_tuple().digits) + len(str(index)) + 2)
        return index * resolution


class FirstFitOptimizer:
    def optimize(self, problem: OptimizationProblem,
                 on_event: Callable[[FirstFitEvent], None] | None = None) -> OptimizationResult:
        # Public T1 dataclasses preserve input ordering; normalize at this entry.
        groups = tuple(replace(group, units=prepare_group_units(group.units), stock_candidates=tuple(
            sorted(group.stock_candidates, key=lambda stock: stock.source is MaterialSource.SHEET)
        )) for group in sorted(problem.groups, key=lambda group: group.key))
        problem = replace(problem, order_ids=tuple(sorted(problem.order_ids)), groups=groups)
        cache, layouts, placements = RasterCache(), {}, []  # fresh per calculation
        total = len(problem.units)

        def emit(kind, group, unit=None, placement=None):
            if on_event is not None:
                on_event(FirstFitEvent(kind=kind, group_key=group.key, unit=unit, placement=placement,
                                      placed_units=len(placements), total_units=total))

        for group in problem.groups:
            emit("group_started", group)
            for unit in group.units:
                emit("piece_started", group, unit)
                orientations = cache.orientations(unit, problem.config.resolution_mm, problem.config.angular_step_deg)
                accepted = None
                for stock in group.stock_candidates:
                    if stock.identity not in layouts:
                        layouts[stock.identity] = _empty_layout(cache.material(stock, problem.config.resolution_mm), problem.config)
                    layout = layouts[stock.identity]
                    for prepared in orientations:
                        orientation, mask = prepared.orientation, prepared.orientation.mask
                        # Negative bbox prefilter only: acceptance always uses real material bits.
                        rows = layout.material.row_count - mask.row_count + 1
                        columns = layout.material.columns - mask.columns + 1
                        if rows <= 0 or columns <= 0:
                            continue
                        for row in range(rows):
                            for column in range(columns):
                                if layout.check(mask, row, column).is_valid:
                                    layouts[stock.identity] = layout.place(mask, row, column)
                                    accepted = Placement(
                                        piece=unit, stock=stock, x_mm=_coordinate(column, problem.config.resolution_mm),
                                        y_mm=_coordinate(row, problem.config.resolution_mm),
                                        rotation_deg=orientation.rotation_deg, geometry=orientation.geometry,
                                    )
                                    placements.append(accepted)
                                    emit("piece_placed", group, unit, accepted)
                                    break
                            if accepted is not None:
                                break
                        if accepted is not None:
                            break
                    if accepted is not None:
                        break
                # Failure for one unit does not suppress attempts for subsequent units.
            emit("group_completed", group)
        return OptimizationResult(problem=problem, placements=tuple(placements))
