"""Adaptación experimental Pair-Block sobre los contratos inmutables NewGlass.

Se exploran bloques de exactamente dos unidades. La búsqueda interna utiliza
orientaciones cardinales que estén permitidas por el paso angular configurado y
un conjunto acotado de alineaciones relativas; el bloque es una RasterMask
temporal y el resultado se descompone en los dos Placement originales.
"""
from dataclasses import dataclass, replace
from decimal import Decimal
from itertools import combinations
from time import perf_counter_ns

from app.modules.optimization.domain.first_fit import _coordinate, _empty_layout
from app.modules.optimization.domain.packing import _feasible_candidates
from app.modules.optimization.domain.preparation import prepare_group_units
from app.modules.optimization.domain.problem import (
    MaterialSource, OptimizationProblem, OptimizationResult, Placement,
)
from app.modules.optimization.domain.raster_mask import RasterMask
from app.modules.optimization.domain.run_geometry import prepare_run_geometry
from app.modules.optimization.domain.rotation import discrete_angles
from app.modules.optimization.domain.placement import SheetLayout


MAX_BBOX_AREA_RATIO = 4
"""Cheap screen: a member's bounding-box area may not exceed 4x its mate."""
MAX_RELATIVE_ANCHORS_PER_AXIS = 8


@dataclass(frozen=True)
class BlockComposition:
    first: object
    second: object
    mask: RasterMask
    first_orientation: object
    second_orientation: object
    first_offset: tuple[int, int]
    second_offset: tuple[int, int]
    compactness: float

    @property
    def identities(self):
        return self.first.identity, self.second.identity


@dataclass(frozen=True)
class BlockPackingTrace:
    candidate_pairs: int
    filtered_pairs: int
    geometrically_checked_pairs: int
    accepted_blocks: int
    placed_blocks: int
    pieces_in_blocks: int
    standalone_pieces: int
    block_compaction: float
    block_compaction_values: tuple[float, ...]
    block_generation_ms: float
    packing_ms: float
    selected_blocks: tuple[dict, ...]
    processing_order: tuple[tuple[int, int], ...]


def _area_ratio_passes(first, second):
    """Rechaza pares con bounding boxes de escalas muy distintas antes de rasterizar."""
    first_area = first.mask.columns * first.mask.row_count
    second_area = second.mask.columns * second.mask.row_count
    return max(first_area, second_area) <= MAX_BBOX_AREA_RATIO * min(first_area, second_area)


def _relative_anchors(first_extent, second_extent, separation):
    """Puntos de alineación acotados, incluyendo contacto y bordes casi coincidentes."""
    values = {
        -second_extent + 1, -second_extent // 2, -1, 0, 1,
        first_extent - second_extent,
        first_extent // 2 - second_extent // 2,
        first_extent - 1,
        first_extent + separation,
        -second_extent - separation,
    }
    ordered = sorted(values)
    if len(ordered) > MAX_RELATIVE_ANCHORS_PER_AXIS:
        # Retain extremes and values closest to the center with stable tie order.
        center = min(ordered, key=lambda value: (abs(value), value))
        ranked = sorted(ordered, key=lambda value: (abs(value - center), value))
        ordered = sorted({ordered[0], ordered[-1], *ranked[:MAX_RELATIVE_ANCHORS_PER_AXIS - 2]})
    return tuple(ordered)


def _cardinal_orientations(prepared, unit):
    """Return unique 0/90/180/270 masks already present in NewGlass' angle set."""
    allowed = set(discrete_angles(prepared.config.angular_step_deg))
    chosen = []
    seen = set()
    for angle in (Decimal(0), Decimal(90), Decimal(180), Decimal(270)):
        if angle not in allowed:
            continue
        # Reuse the run cache without rasterizing every 5-degree angle.
        orientation = prepared._cache._orientation(unit, prepared.config.resolution_mm, angle)
        signature = (orientation.mask.columns, orientation.mask.rows)
        if signature not in seen:
            seen.add(signature)
            chosen.append(orientation)
    return tuple(chosen)


def _canvas_mask(columns, rows, resolution):
    full = (1 << columns) - 1
    return RasterMask(float(resolution), columns, (full,) * rows)


def _compose(first_unit, second_unit, first_orientation, second_orientation, dx, dy, resolution, separation_cells):
    """Validate an internal relative placement and build its local union mask."""
    a, b = first_orientation.mask, second_orientation.mask
    min_x, min_y = min(0, dx), min(0, dy)
    ax, ay, bx, by = -min_x, -min_y, dx - min_x, dy - min_y
    columns = max(ax + a.columns, bx + b.columns)
    rows = max(ay + a.row_count, by + b.row_count)
    layout = SheetLayout.empty(_canvas_mask(columns, rows, resolution), separation_mm=separation_cells * float(resolution))
    layout = layout.place(a, ay, ax)
    if not layout.check(b, by, bx).is_valid:
        return None
    combined = [0] * rows
    for index, bits in enumerate(a.rows):
        combined[ay + index] |= bits << ax
    for index, bits in enumerate(b.rows):
        combined[by + index] |= bits << bx
    mask = RasterMask(float(resolution), columns, tuple(combined))
    density = mask.occupied_cells / (mask.columns * mask.row_count)
    standalone = max(
        a.occupied_cells / (a.columns * a.row_count),
        b.occupied_cells / (b.columns * b.row_count),
    )
    if density <= standalone + 1e-12:
        return None
    return BlockComposition(
        first=first_unit, second=second_unit, mask=mask,
        first_orientation=first_orientation, second_orientation=second_orientation,
        first_offset=(ax, ay), second_offset=(bx, by), compactness=density,
    )


def _pair_compositions(first, second, prepared, separation_cells, first_orientations, second_orientations):
    """Evaluate bounded relative placements and retain the best composition."""
    best = None
    resolution = prepared.config.resolution_mm
    for orient_a in first_orientations:
        for orient_b in second_orientations:
            mask_a, mask_b = orient_a.mask, orient_b.mask
            xs = _relative_anchors(mask_a.columns, mask_b.columns, separation_cells)
            ys = _relative_anchors(mask_a.row_count, mask_b.row_count, separation_cells)
            for dy in ys:
                for dx in xs:
                    composition = _compose(first, second, orient_a, orient_b, dx, dy, resolution, separation_cells)
                    if composition is None:
                        continue
                    key = (-composition.compactness, orient_a.rotation_deg, orient_b.rotation_deg,
                           composition.second_offset[1], composition.second_offset[0])
                    if best is None or key < best[0]:
                        best = key, composition
    return best[1] if best else None


def _generate_blocks(group, prepared, separation_cells):
    units = tuple(group.units)
    candidate_pairs = len(units) * (len(units) - 1) // 2
    filtered = checked = 0
    compositions = []
    orientation_cache = {unit.identity: _cardinal_orientations(prepared, unit) for unit in units}
    for first, second in combinations(units, 2):
        if not _area_ratio_passes(orientation_cache[first.identity][0], orientation_cache[second.identity][0]):
            filtered += 1
            continue
        checked += 1
        composition = _pair_compositions(first, second, prepared, separation_cells,
            orientation_cache[first.identity], orientation_cache[second.identity])
        if composition is not None:
            compositions.append(composition)
    # Greedy deterministic disjoint matching: densest valid local composition first.
    compositions.sort(key=lambda item: (-item.compactness, -float(item.first.area_mm2 + item.second.area_mm2),
        item.first.order_id, item.first.piece_id, item.first.unit_index,
        item.second.order_id, item.second.piece_id, item.second.unit_index,
        item.first_orientation.rotation_deg, item.second_orientation.rotation_deg,
        item.second_offset[1], item.second_offset[0]))
    selected, used = [], set()
    for item in compositions:
        if item.first.identity in used or item.second.identity in used:
            continue
        selected.append(item)
        used.update(item.identities)
    return candidate_pairs, filtered, checked, tuple(selected)


def _estimate_layout_bytes(layout):
    return layout.material.row_count * (40 + 4 * ((layout.material.columns + 29) // 30)) * 4


class BlockPackingExperimental:
    """Greedy Pair-Block with individual-piece fallback and remnant priority."""

    def optimize(self, problem: OptimizationProblem, *, checkpoint=None):
        checkpoint = checkpoint or (lambda: None)
        groups = tuple(replace(group, units=prepare_group_units(group.units), stock_candidates=tuple(
            sorted(group.stock_candidates, key=lambda stock: stock.source is MaterialSource.SHEET)
        )) for group in sorted(problem.groups, key=lambda group: group.key))
        problem = replace(problem, order_ids=tuple(sorted(problem.order_ids)), groups=groups)
        prepared = prepare_run_geometry(problem, checkpoint=checkpoint)
        layouts, placements = {}, []
        layout_bytes = 0
        generated = []
        candidate_pairs = filtered_pairs = checked_pairs = 0
        generation_started = perf_counter_ns()
        for group in problem.groups:
            checkpoint()
            # Current geometry expands the requested distance upward to whole raster cells.
            separation = _empty_layout(prepared.material(group.stock_candidates[0]), problem.config).separation_cells \
                if group.stock_candidates else 0
            counts = _generate_blocks(group, prepared, separation)
            candidate_pairs += counts[0]
            filtered_pairs += counts[1]
            checked_pairs += counts[2]
            generated.append((group, counts[3]))
        block_generation_ms = (perf_counter_ns() - generation_started) / 1_000_000
        # The public diagnostic includes all pair construction, independent of packing.
        packing_started = perf_counter_ns()
        selected_details, blocks_used = [], []
        processing_order = []
        total_units = len(problem.units)

        def retain_layout(candidate_layout):
            nonlocal layout_bytes
            if candidate_layout.material is None:
                return
            estimate = _estimate_layout_bytes(candidate_layout)
            if layout_bytes + estimate > 128 * 1024 * 1024:
                from app.modules.optimization.domain.rotation import RasterPreparationError
                raise RasterPreparationError('Internal cutting layouts exceed their 128 MiB budget.')
            layout_bytes += estimate

        def try_block(group, composition):
            """Try each allowed source tier; a feasible retazo always beats a sheet."""
            for source in (MaterialSource.REMNANT, MaterialSource.SHEET):
                choices = []
                for stock_rank, stock in enumerate(group.stock_candidates):
                    if stock.source is not source:
                        continue
                    checkpoint()
                    layout = layouts.get(stock.identity)
                    if layout is None:
                        layout = _empty_layout(prepared.material(stock), problem.config)
                    mask = composition.mask
                    if mask.row_count > layout.material.row_count or mask.columns > layout.material.columns:
                        continue
                    position = layout.first_position(mask)
                    if position is not None:
                        row, column = position
                        after = layout.place(mask, row, column)
                        free = sum((usable & ~blocked).bit_count()
                            for usable, blocked in zip(after.usable, after.blocked))
                        choices.append((stock_rank, stock, layout, row, column, after, free))
                if choices:
                    # Pair-Block uses first feasible stock, like FF's source/placement policy.
                    stock_rank, stock, layout, row, column, after, free = min(choices, key=lambda value: value[0])
                    if stock.identity not in layouts:
                        retain_layout(layout)
                    layouts[stock.identity] = after
                    for unit, oriented, offset in (
                        (composition.first, composition.first_orientation, composition.first_offset),
                        (composition.second, composition.second_orientation, composition.second_offset),
                    ):
                        placements.append(Placement(piece=unit, stock=stock,
                            x_mm=_coordinate(column + offset[0], problem.config.resolution_mm),
                            y_mm=_coordinate(row + offset[1], problem.config.resolution_mm),
                            rotation_deg=oriented.rotation_deg, geometry=oriented.geometry))
                    detail = next(item for item in selected_details if item["piece_identities"] == [
                        list(composition.first.identity), list(composition.second.identity)])
                    detail.update(placed=True, source=stock.source.value, material_id=stock.material_id,
                                  block_x_mm=str(_coordinate(column, problem.config.resolution_mm)),
                                  block_y_mm=str(_coordinate(row, problem.config.resolution_mm)))
                    return True
                # A block cannot leapfrog a single piece that could use an available retazo.
                if source is MaterialSource.REMNANT:
                    for unit in (composition.first, composition.second):
                        if any(_feasible_candidates(group, source, prepared.orientations(unit), prepared,
                                layouts, problem.config, checkpoint)):
                            return False
            return False

        def try_single(group, unit):
            """Fallback individual compatible with the ordinary FF source and angle scan."""
            orientations = prepared.orientations(unit)
            winner = next(_feasible_candidates(group, MaterialSource.REMNANT, orientations, prepared,
                layouts, problem.config, checkpoint), None)
            if winner is None:
                winner = next(_feasible_candidates(group, MaterialSource.SHEET, orientations, prepared,
                    layouts, problem.config, checkpoint), None)
            if winner is not None:
                if winner.stock.identity not in layouts:
                    retain_layout(winner.layout)
                layouts[winner.stock.identity] = winner.layout_after
                placements.append(Placement(piece=unit, stock=winner.stock,
                    x_mm=_coordinate(winner.column, problem.config.resolution_mm),
                    y_mm=_coordinate(winner.row, problem.config.resolution_mm),
                    rotation_deg=winner.orientation.rotation_deg, geometry=winner.orientation.geometry))
            processing_order.append(unit.identity)

        for group, selected in generated:
            for composition in selected:
                selected_details.append({
                    "piece_identities": [list(composition.first.identity), list(composition.second.identity)],
                    "rotations_deg": [str(composition.first_orientation.rotation_deg),
                                      str(composition.second_orientation.rotation_deg)],
                    "offsets_cells": [list(composition.first_offset), list(composition.second_offset)],
                    "compactness": round(composition.compactness, 6), "placed": False,
                })
            paired_ids = {identity for block in selected for identity in block.identities}
            tasks = [(-float(block.first.area_mm2 + block.second.area_mm2), block.identities, 0, block)
                     for block in selected]
            tasks.extend((-float(unit.area_mm2), (unit.identity,), 1, unit)
                         for unit in group.units if unit.identity not in paired_ids)
            task_key = lambda task: (task[0], task[1], task[2])
            tasks.sort(key=task_key)
            task_index = 0
            while task_index < len(tasks):
                checkpoint()
                _, _, task_type, task = tasks[task_index]
                if task_type == 0 and try_block(group, task):
                    blocks_used.append(task)
                    processing_order.extend(task.identities)
                elif task_type == 0:
                    fallback_units = sorted((task.first, task.second), key=lambda unit: (
                        -unit.area_mm2, unit.order_id, unit.piece_id, unit.unit_index))
                    fallback_tasks = [(-float(unit.area_mm2), (unit.identity,), 1, unit)
                                      for unit in fallback_units]
                    tasks[task_index + 1:] = sorted(tasks[task_index + 1:] + fallback_tasks, key=task_key)
                else:
                    try_single(group, task)
                task_index += 1
        packing_ms = (perf_counter_ns() - packing_started) / 1_000_000
        result = OptimizationResult(problem=problem, placements=tuple(placements))
        compactions = tuple(block.compactness for block in blocks_used)
        accepted_count = len(selected_details)
        trace = BlockPackingTrace(
            candidate_pairs=candidate_pairs, filtered_pairs=filtered_pairs,
            geometrically_checked_pairs=checked_pairs, accepted_blocks=accepted_count,
            placed_blocks=len(blocks_used),
            pieces_in_blocks=2 * len(blocks_used), standalone_pieces=total_units - 2 * len(blocks_used),
            block_compaction=(sum(compactions) / len(compactions) if compactions else 0.0),
            block_compaction_values=compactions, block_generation_ms=block_generation_ms,
            packing_ms=packing_ms, selected_blocks=tuple(selected_details),
            processing_order=tuple(processing_order),
        )
        return result, trace
