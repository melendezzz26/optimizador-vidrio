"""R4 metrics and conservative residual rectangles; never creates inventory.

One largest exact free raster rectangle per USED physical unit, PLAN §8.
Tie order: area DESC, top row ASC, left column ASC, width DESC, height DESC.
"""
from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_HALF_UP
from itertools import groupby

from .first_fit import _empty_layout
from .problem import MaterialSource, OptimizationMetrics
from .raster_mask import RasterMask
from .rotation import RasterCache, raster_number


@dataclass(frozen=True, kw_only=True)
class ResidualRectangle:
    material_source: str
    material_id: int
    stock_unit_index: int
    x_mm: Decimal
    y_mm: Decimal
    width_mm: Decimal
    height_mm: Decimal
    area_mm2: Decimal


def _column_segments(rows, columns):
    """Columns where SOME row differs from its left neighbour (column 0 always).

    Between two consecutive starts every row has the same bit in every column,
    so those columns always share one histogram height.
    """
    if columns <= 0:
        return [], 0
    full = (1 << columns) - 1
    changes = 1
    for bits in rows:
        bits &= full
        changes |= (bits ^ (bits << 1)) & full
    text = format(changes, "b")[::-1]  # text[c] is bit c
    starts, position = [], text.find("1")
    while position != -1:
        starts.append(position)
        position = text.find("1", position + 1)
    return starts, full


def largest_rectangle(free_rows, columns, *, checkpoint=None):
    rows = free_rows if isinstance(free_rows, (tuple, list)) else tuple(free_rows)
    # S2-M6 (F4b): the original scan visited every column of every run. Inside
    # a segment of equal columns its stack neither pops (the top already has
    # that height) nor pushes (equal heights are not pushed), so only segment
    # starts and the final sentinel can act. Visiting just those positions
    # yields the very same popped rectangles, in the same order, hence the same
    # result and tie order; widths still come from real column positions.
    starts, full = _column_segments(rows, columns)
    positions = starts + [columns]
    indexes = {column: index for index, column in enumerate(positions)}
    heights = [0] * len(starts)
    last_seen = [-1] * len(starts)
    best, best_key = None, None
    row = -1
    for bits, repeated in groupby(rows):
        if checkpoint is not None:
            checkpoint()
        count = sum(1 for _ in repeated)
        previous_row = row
        row += count
        # Within identical consecutive bit rows every possible rectangle only
        # grows vertically. Its maximum occurs at the last row of the run.
        # This preserves the exact area/top/left/width/height tie order.
        bits &= full
        while bits:
            leftmost = (bits & -bits).bit_length() - 1
            shifted = bits >> leftmost
            width = (shifted ^ (shifted + 1)).bit_length() - 1
            rightmost = leftmost + width
            stop = indexes[rightmost]
            stack = []
            # Every blocked span resets its columns' heights and flushes the
            # stack. The timestamp performs that reset on the next free row.
            for index in range(indexes[leftmost], stop + 1):
                column = start = positions[index]
                height = 0
                if index < stop:
                    height = count + (heights[index] if last_seen[index] == previous_row else 0)
                    heights[index] = height
                    last_seen[index] = row
                while stack and stack[-1][1] > height:
                    left, h = stack.pop()
                    width, top = column - left, row - h + 1
                    key = (-width * h, top, left, -width, -h)
                    if best_key is None or key < best_key:
                        best_key, best = key, (top, left, width, h)
                    start = left
                if height and (not stack or stack[-1][1] < height):
                    stack.append((start, height))
            bits &= ~((1 << rightmost) - 1)
    return best


def calculate_metrics(result, minimum_width_mm, minimum_height_mm):
    """Return calculated result and exact residual proposals; no stock mutation.

    Zero placed units means no valid R4 denominator, hence metrics=None.
    Geometry remains the existing numeric contract; all area arithmetic Decimal.
    """
    if not result.placements:
        return result, ()
    config, cache, residuals = result.problem.config, RasterCache(), []
    for stock in result.materials_used:
        layout = _empty_layout(cache.material(stock, config.resolution_mm), config)
        for placement in result.placements:
            if placement.stock.identity != stock.identity:
                continue
            # Contour is already oriented: rasterize at 0; NEVER rotate it again.
            piece = replace(placement.piece, geometry=placement.geometry)
            mask = cache.orientations(piece, config.resolution_mm, Decimal(360))[0].orientation.mask
            row, column = placement.y_mm / config.resolution_mm, placement.x_mm / config.resolution_mm
            if row != row.to_integral_value() or column != column.to_integral_value():
                raise ValueError("Placement is not aligned to the effective raster grid.")
            layout = layout.place(mask, int(row), int(column))
        free = tuple(usable & ~blocked for usable, blocked in zip(layout.usable, layout.blocked))
        rectangle = largest_rectangle(free, layout.material.columns)
        if rectangle is None:
            continue
        row, column, columns, rows = rectangle
        width, height = columns * config.resolution_mm, rows * config.resolution_mm
        if width < minimum_width_mm or height < minimum_height_mm:
            continue
        mask = RasterMask(raster_number(config.resolution_mm), columns, ((1 << columns) - 1,) * rows)
        if not layout.check(mask, row, column).is_valid:
            raise ValueError("Residual region is not contained in the actual free material.")
        residuals.append(ResidualRectangle(material_source=stock.source.value, material_id=stock.material_id,
            stock_unit_index=stock.physical_unit_index, x_mm=column * config.resolution_mm,
            y_mm=row * config.resolution_mm, width_mm=width, height_mm=height, area_mm2=width * height))
    material = sum((s.area_mm2 for s in result.materials_used), Decimal(0))
    pieces = sum((p.piece.area_mm2 for p in result.placements), Decimal(0))
    recovered = sum((r.area_mm2 for r in residuals), Decimal(0))
    waste = material - pieces - recovered
    if waste < 0 or pieces > material:
        raise ValueError("Inconsistent persisted areas; metrics cannot be calculated safely.")
    metrics = OptimizationMetrics(utilization_pct=(pieces / material * 100).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP),
        waste_mm2=waste, new_sheets_used=sum(s.source is MaterialSource.SHEET for s in result.materials_used),
        recoverable_remnant_mm2=recovered, material_area_mm2=material, placed_piece_area_mm2=pieces)
    return replace(result, metrics=metrics), tuple(residuals)
