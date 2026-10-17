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


def largest_rectangle(free_rows, columns):
    heights = [0] * columns
    best, best_key = None, None
    row = -1
    for bits, repeated in groupby(free_rows):
        count = sum(1 for _ in repeated)
        row += count
        # Within identical consecutive bit rows every possible rectangle only
        # grows vertically. Its maximum occurs at the last row of the run.
        # This preserves the exact area/top/left/width/height tie order.
        heights = [heights[c] + count if (bits >> c) & 1 else 0 for c in range(columns)]
        stack = []
        for column in range(columns + 1):
            height = heights[column] if column < columns else 0
            start = column
            while stack and stack[-1][1] > height:
                left, h = stack.pop()
                width, top = column - left, row - h + 1
                key = (-width * h, top, left, -width, -h)
                if best_key is None or key < best_key:
                    best_key, best = key, (top, left, width, h)
                start = left
            if height and (not stack or stack[-1][1] < height):
                stack.append((start, height))
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
