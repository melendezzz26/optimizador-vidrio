"""Shared, lazy raster packing traversal; selectors only choose feasible sources."""
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from decimal import Decimal, localcontext
from functools import cached_property
from typing import Literal

from .placement import SheetLayout
from .preparation import prepare_group_units
from .problem import MaterialSource, OptimizationProblem, OptimizationResult, PieceUnit, Placement, StockCandidate
from .rotation import Orientation, RasterPreparationError, raster_number
from .run_geometry import prepare_run_geometry
from .visual_events import VisualEvent


@dataclass(frozen=True, kw_only=True)
class FirstFitEvent:
    """Existing in-process milestone contract, also usable by other selectors."""
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


@dataclass(frozen=True, kw_only=True)
class FeasibleCandidate:
    """Canonical placement for one physical source, without committing its layout.

    Scoring is lazy: FF never constructs or scores rejected trial layouts.
    SheetLayout.place returns a new immutable value; only the winner is retained
    in the calculation's layouts. Selectors need retain only their current best.
    """
    stock: StockCandidate
    stock_rank: int
    layout: SheetLayout
    orientation: Orientation
    orientation_rank: int
    row: int
    column: int

    @cached_property
    def free_cells_before(self) -> int:
        return sum((usable & ~blocked).bit_count()
                   for usable, blocked in zip(self.layout.usable, self.layout.blocked))

    @cached_property
    def layout_after(self) -> SheetLayout:
        return self.layout.place(self.orientation.mask, self.row, self.column)

    @cached_property
    def remaining_free_cells_after_placement(self) -> int:
        return sum((usable & ~blocked).bit_count()
                   for usable, blocked in zip(self.layout_after.usable, self.layout_after.blocked))


def _feasible_candidates(group, source, orientations, prepared, layouts, config, checkpoint, observe=None):
    # Preserve upstream stock order. Source priority is eligibility, not a score.
    for stock_rank, stock in enumerate(group.stock_candidates):
        if stock.source is not source:
            continue
        checkpoint()
        layout = layouts.get(stock.identity)
        if layout is None:
            layout = _empty_layout(prepared.material(stock), config)
        for orientation_rank, oriented in enumerate(orientations):
            checkpoint()
            orientation, mask = oriented.orientation, oriented.orientation.mask
            if observe is not None:
                observe(stock, orientation)
            # Negative bbox prefilter only; acceptance uses real material bits.
            if layout.material.row_count < mask.row_count or layout.material.columns < mask.columns:
                continue
            position = layout.first_position(mask)
            checkpoint()
            if position is not None:
                row, column = position
                yield FeasibleCandidate(stock=stock, stock_rank=stock_rank, layout=layout,
                                        orientation=orientation, orientation_rank=orientation_rank,
                                        row=row, column=column)
                # A selector compares sources, never alternate positions/angles.
                break


def pack(problem: OptimizationProblem, on_event: Callable[[FirstFitEvent], None] | None = None,
         *, select: Callable[[Iterable[FeasibleCandidate]], FeasibleCandidate | None] | None = None,
         checkpoint: Callable[[], None] | None = None,
         on_visual: Callable[[VisualEvent], None] | None = None,
         ) -> OptimizationResult:
    """Existing FF traversal with one optional source-selection decision point."""
    groups = tuple(replace(group, units=prepare_group_units(group.units), stock_candidates=tuple(
        sorted(group.stock_candidates, key=lambda stock: stock.source is MaterialSource.SHEET)
    )) for group in sorted(problem.groups, key=lambda group: group.key))
    problem = replace(problem, order_ids=tuple(sorted(problem.order_ids)), groups=groups)
    checkpoint = checkpoint if checkpoint is not None else lambda: None
    prepared = prepare_run_geometry(problem, checkpoint=checkpoint, on_visual=on_visual)
    layouts, placements = {}, []
    layout_bytes = 0
    total = len(problem.units)
    processed = 0
    evaluation_index = 0

    def visual(kind, **kwargs):
        if on_visual is not None:
            on_visual(VisualEvent(kind=kind, processed_units=processed, placed_units=len(placements),
                total_units=total, **kwargs))

    def emit(kind, group, unit=None, placement=None):
        if on_event is not None:
            on_event(FirstFitEvent(kind=kind, group_key=group.key, unit=unit, placement=placement,
                                  placed_units=len(placements), total_units=total))

    for group in problem.groups:
        emit("group_started", group)
        for unit in group.units:
            checkpoint()
            emit("piece_started", group, unit)
            orientations = prepared.orientations(unit)
            def observe(stock, orientation):
                nonlocal evaluation_index
                evaluation_index += 1
                visual('orientation_testing', unit=unit, stock=stock, orientation=orientation,
                       evaluation_index=evaluation_index)
            for source in (MaterialSource.REMNANT, MaterialSource.SHEET):
                candidates = _feasible_candidates(group, source, orientations, prepared, layouts, problem.config,
                    checkpoint, observe if on_visual is not None else None)
                # next() preserves FF's early exit, without examining later stock.
                winner = next(candidates, None) if select is None else select(candidates)
                if winner is None:
                    continue
                stock, layout = winner.stock, winner.layout
                if stock.identity not in layouts:
                    # Only USED layouts are retained, with the existing FF budget.
                    estimate = layout.material.row_count * (40 + 4 * ((layout.material.columns + 29) // 30)) * 4
                    if layout_bytes + estimate > 128 * 1024 * 1024:
                        raise RasterPreparationError('Internal cutting layouts exceed their 128 MiB budget.')
                    layout_bytes += estimate
                layouts[stock.identity] = winner.layout_after
                accepted = Placement(
                    piece=unit, stock=stock, x_mm=_coordinate(winner.column, problem.config.resolution_mm),
                    y_mm=_coordinate(winner.row, problem.config.resolution_mm),
                    rotation_deg=winner.orientation.rotation_deg, geometry=winner.orientation.geometry,
                )
                placements.append(accepted)
                processed += 1
                if on_visual is not None:
                    visual('source_selected', unit=unit, stock=stock, orientation=winner.orientation,
                        material_mask=prepared.material(stock), placement=accepted,
                        score=winner.remaining_free_cells_after_placement if select is not None else None)
                emit("piece_placed", group, unit, accepted)
                break
            else:
                processed += 1
                visual('piece_unplaced', unit=unit)
            # Failure for one unit does not suppress attempts for subsequent units.
        emit("group_completed", group)
    return OptimizationResult(problem=problem, placements=tuple(placements))
