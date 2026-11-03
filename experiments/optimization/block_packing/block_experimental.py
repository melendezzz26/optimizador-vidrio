"""Pair-Block v2 over NewGlass immutable geometry and raster contracts.

Pairs use the full configured discrete angle set. Exact raster-mask equivalence
and optimistic bbox bounds prune work before relative placements are checked.
Temporary blocks are decomposed into the original individual placements.
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
from app.modules.optimization.domain.placement import SheetLayout, _dilate


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
    bbox_saving_cells: int

    @property
    def identities(self):
        return self.first.identity, self.second.identity


@dataclass(frozen=True)
class BlockPackingTrace:
    candidate_pairs: int
    compatible_pairs: int
    filtered_pairs: int
    geometrically_checked_pairs: int
    orientation_combinations_theoretical: int
    orientation_combinations_after_symmetry: int
    orientation_combinations_after_bounds: int
    orientation_combinations_after_phase: int
    orientation_combinations_pruned: int
    orientation_combinations_pruned_by_compatibility: int
    orientation_combinations_pruned_by_symmetry: int
    orientation_combinations_pruned_by_bounds: int
    orientation_combinations_pruned_by_phase: int
    orientation_combinations_pruned_by_best_bound: int
    orientation_combinations_evaluated: int
    relative_positions_theoretical: int
    relative_positions_pruned: int
    relative_positions_checked: int
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


def _geometry_signature(unit):
    """Hashable exact geometry key for sharing the common rotation cache."""
    geometry = unit.geometry
    shape = geometry["type"]
    if shape == "RECTANGULO":
        return (shape, Decimal(str(geometry["width_mm"])), Decimal(str(geometry["height_mm"])))
    if shape == "CIRCUNFERENCIA":
        return (shape, Decimal(str(geometry["radius_mm"])))
    return (shape, tuple(tuple(Decimal(str(value)) for value in point)
                         for point in geometry["vertices_mm"]))


def _orientation_options(prepared, units, checkpoint):
    """Use the full discrete angle set and collapse only identical raster masks."""
    by_geometry, by_identity = {}, {}
    angles = discrete_angles(prepared.config.angular_step_deg)
    for unit in units:
        signature = _geometry_signature(unit)
        if signature not in by_geometry:
            candidates = (Decimal(0),) if unit.geometry["type"] == "CIRCUNFERENCIA" else angles
            seen_masks, unique = set(), []
            for angle in candidates:
                checkpoint()
                orientation = prepared._cache._orientation(
                    unit, prepared.config.resolution_mm, angle)
                mask = orientation.mask
                mask_signature = (mask.columns, mask.row_count, mask.rows)
                if mask_signature not in seen_masks:
                    seen_masks.add(mask_signature)
                    unique.append(orientation)
            by_geometry[signature] = tuple(unique)
        by_identity[unit.identity] = by_geometry[signature]
    return by_identity


def _orientation_upper_bounds(first_mask, second_mask):
    """Return optimistic bounds on bbox savings and raster density."""
    minimum_bbox = max(first_mask.columns, second_mask.columns) * max(
        first_mask.row_count, second_mask.row_count)
    separate_bbox = (first_mask.columns * first_mask.row_count
                     + second_mask.columns * second_mask.row_count)
    saving_upper = separate_bbox - minimum_bbox
    density_upper = min(1.0, (first_mask.occupied_cells + second_mask.occupied_cells) / minimum_bbox
                        if minimum_bbox else 0.0)
    return saving_upper, density_upper, minimum_bbox


def _relative_anchors(first_extent, second_extent, separation):
    """Puntos de alineación acotados, incluyendo contacto y bordes casi coincidentes."""
    values = {
        -second_extent + 1, -second_extent // 2,
        -(separation + 1), -1, 0, 1, separation + 1,
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


def _quick_relative_anchors(first_extent, second_extent, separation, full):
    """Small deterministic first pass: origin, legal contact and half-span alignments."""
    candidates = (0, separation + 1, -(separation + 1), -(second_extent // 2))
    return tuple(dict.fromkeys(value for value in candidates if value in full))


def _compose(first_unit, second_unit, first_orientation, second_orientation, dx, dy, resolution, separation_cells):
    """Validate an internal relative placement and build its local union mask."""
    a, b = first_orientation.mask, second_orientation.mask
    min_x, min_y = min(0, dx), min(0, dy)
    ax, ay, bx, by = -min_x, -min_y, dx - min_x, dy - min_y
    columns = max(ax + a.columns, bx + b.columns)
    rows = max(ay + a.row_count, by + b.row_count)
    first_rows, second_rows = [0] * rows, [0] * rows
    for index, bits in enumerate(a.rows):
        first_rows[ay + index] |= bits << ax
    for index, bits in enumerate(b.rows):
        second_rows[by + index] |= bits << bx
    # Mirror SheetLayout's square-neighborhood separation check without
    # allocating a temporary stock layout for every relative offset.
    blocked = _dilate(tuple(first_rows), columns, separation_cells)
    if any(piece_row & blocked_row for piece_row, blocked_row in zip(second_rows, blocked)):
        return None
    mask = RasterMask(float(resolution), columns,
                      tuple(left | right for left, right in zip(first_rows, second_rows)))
    density = mask.occupied_cells / (mask.columns * mask.row_count)
    bbox_saving = (a.columns * a.row_count + b.columns * b.row_count
                   - mask.columns * mask.row_count)
    if bbox_saving <= 0:
        return None
    return BlockComposition(
        first=first_unit, second=second_unit, mask=mask,
        first_orientation=first_orientation, second_orientation=second_orientation,
        first_offset=(ax, ay), second_offset=(bx, by), compactness=density,
        bbox_saving_cells=bbox_saving,
    )


def _pair_compositions(first, second, prepared, separation_cells, first_orientations,
                       second_orientations, stock_sizes):
    """Keep a deterministic global phase per relative angle before geometry checks."""
    resolution = prepared.config.resolution_mm
    after_symmetry = len(first_orientations) * len(second_orientations)
    best_phase_by_relative_angle = {}
    after_bounds = 0
    for orient_a in first_orientations:
        for orient_b in second_orientations:
            saving_upper, density_upper, minimum_bbox = _orientation_upper_bounds(
                orient_a.mask, orient_b.mask)
            min_columns = max(orient_a.mask.columns, orient_b.mask.columns)
            min_rows = max(orient_a.mask.row_count, orient_b.mask.row_count)
            fits_some_stock_bound = any(min_columns <= columns and min_rows <= rows
                                        for columns, rows in stock_sizes)
            if saving_upper <= 0 or not fits_some_stock_bound:
                continue
            after_bounds += 1
            # Decimal remainder keeps the dividend sign; normalize through int
            # and Python's non-negative modulo to obtain exactly 72 bins.
            relative_angle = int(orient_b.rotation_deg - orient_a.rotation_deg) % 360
            key = (minimum_bbox, -saving_upper, -density_upper,
                   orient_a.rotation_deg, orient_b.rotation_deg)
            previous = best_phase_by_relative_angle.get(relative_angle)
            if previous is None or key < previous[0]:
                best_phase_by_relative_angle[relative_angle] = (key, orient_a, orient_b)

    candidates = sorted(best_phase_by_relative_angle.values(),
                        key=lambda item: (item[0], item[1].rotation_deg, item[2].rotation_deg))
    after_phase = len(candidates)
    best = None
    evaluated = positions_theoretical = positions_checked = 0
    for phase_key, orient_a, orient_b in candidates:
        mask_a, mask_b = orient_a.mask, orient_b.mask
        xs = _relative_anchors(mask_a.columns, mask_b.columns, separation_cells)
        ys = _relative_anchors(mask_a.row_count, mask_b.row_count, separation_cells)
        positions_theoretical += len(xs) * len(ys)
        saving_upper, density_upper = -phase_key[1], -phase_key[2]
        if best is not None:
            best_saving, best_density = -best[0][0], -best[0][1]
            if saving_upper < best_saving or (
                    saving_upper == best_saving and density_upper < best_density - 1e-12):
                continue
        evaluated += 1
        quick_x = _quick_relative_anchors(mask_a.columns, mask_b.columns, separation_cells, xs)
        quick_y = _quick_relative_anchors(mask_a.row_count, mask_b.row_count, separation_cells, ys)

        def check_offset(dx, dy):
            nonlocal best, positions_checked
            positions_checked += 1
            composition = _compose(first, second, orient_a, orient_b, dx, dy,
                                   resolution, separation_cells)
            if composition is None:
                return False
            # Keep only blocks whose actual raster envelope fits an available
            # source when empty. Occupied-layout failures still use single fallback.
            if not any(composition.mask.columns <= columns
                       and composition.mask.row_count <= rows
                       for columns, rows in stock_sizes):
                return True
            key = (-composition.bbox_saving_cells, -composition.compactness,
                   composition.mask.columns * composition.mask.row_count,
                   orient_a.rotation_deg, orient_b.rotation_deg,
                   composition.second_offset[1], composition.second_offset[0])
            if best is None or key < best[0]:
                best = key, composition
            return True

        # Most relative placements fail cheap raster feasibility. Expand to all
        # alignments only when a canonical origin/contact/half-span finds a block.
        quick_found = False
        for dy in quick_y:
            for dx in quick_x:
                quick_found = check_offset(dx, dy) or quick_found
        if quick_found:
            for dy in ys:
                for dx in xs:
                    if dx not in quick_x or dy not in quick_y:
                        check_offset(dx, dy)
    return (best[1] if best else None, after_symmetry, after_bounds, after_phase,
            evaluated, positions_theoretical, positions_checked,
            bool(best_phase_by_relative_angle))


def _generate_blocks(group, prepared, separation_cells, checkpoint):
    units = tuple(group.units)
    candidate_pairs = len(units) * (len(units) - 1) // 2
    filtered = checked = after_symmetry = after_bounds = after_phase = 0
    evaluated = positions_theoretical = positions_checked = 0
    compositions = []
    orientation_cache = _orientation_options(prepared, units, checkpoint)
    stock_sizes = tuple((prepared.material(stock).columns, prepared.material(stock).row_count)
                        for stock in group.stock_candidates)
    for first, second in combinations(units, 2):
        checkpoint()
        (composition, pair_after_symmetry, pair_after_bounds, pair_after_phase,
         pair_evaluated, pair_positions_theoretical, pair_positions, has_potential) = _pair_compositions(
            first, second, prepared, separation_cells,
            orientation_cache[first.identity], orientation_cache[second.identity], stock_sizes)
        after_symmetry += pair_after_symmetry
        after_bounds += pair_after_bounds
        after_phase += pair_after_phase
        evaluated += pair_evaluated
        positions_checked += pair_positions
        positions_theoretical += pair_positions_theoretical
        if not has_potential:
            filtered += 1
            continue
        checked += 1
        if composition is not None:
            compositions.append(composition)
    # Greedy deterministic disjoint matching by bbox savings, then raster density.
    compositions.sort(key=lambda item: (
        -item.bbox_saving_cells, -item.compactness,
        -float(item.first.area_mm2 + item.second.area_mm2),
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
    return {
        "candidate_pairs": candidate_pairs,
        "filtered_pairs": filtered,
        "geometrically_checked_pairs": checked,
        "orientation_combinations_theoretical": candidate_pairs *
            len(discrete_angles(prepared.config.angular_step_deg)) ** 2,
        "orientation_combinations_after_symmetry": after_symmetry,
        "orientation_combinations_after_bounds": after_bounds,
        "orientation_combinations_after_phase": after_phase,
        "orientation_combinations_pruned": candidate_pairs *
            len(discrete_angles(prepared.config.angular_step_deg)) ** 2 - evaluated,
        "orientation_combinations_pruned_by_symmetry": candidate_pairs *
            len(discrete_angles(prepared.config.angular_step_deg)) ** 2 - after_symmetry,
        "orientation_combinations_pruned_by_bounds": after_symmetry - after_bounds,
        "orientation_combinations_pruned_by_phase": after_bounds - after_phase,
        "orientation_combinations_pruned_by_best_bound": after_phase - evaluated,
        "orientation_combinations_evaluated": evaluated,
        "relative_positions_theoretical": positions_theoretical,
        "relative_positions_pruned": positions_theoretical - positions_checked,
        "relative_positions_checked": positions_checked,
        "selected": tuple(selected),
    }


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
        candidate_pairs = len(problem.units) * (len(problem.units) - 1) // 2
        compatible_pairs = filtered_pairs = checked_pairs = 0
        orientation_theoretical = orientation_after_symmetry = 0
        orientation_after_bounds = orientation_after_phase = 0
        orientation_pruned = orientation_evaluated = relative_positions_checked = 0
        relative_positions_theoretical = relative_positions_pruned = 0
        generation_started = perf_counter_ns()
        for group in problem.groups:
            checkpoint()
            # Current geometry expands the requested distance upward to whole raster cells.
            separation = _empty_layout(prepared.material(group.stock_candidates[0]), problem.config).separation_cells \
                if group.stock_candidates else 0
            counts = _generate_blocks(group, prepared, separation, checkpoint)
            compatible_pairs += counts["candidate_pairs"]
            filtered_pairs += counts["filtered_pairs"]
            checked_pairs += counts["geometrically_checked_pairs"]
            orientation_theoretical += counts["orientation_combinations_theoretical"]
            orientation_after_symmetry += counts["orientation_combinations_after_symmetry"]
            orientation_after_bounds += counts["orientation_combinations_after_bounds"]
            orientation_after_phase += counts["orientation_combinations_after_phase"]
            orientation_pruned += counts["orientation_combinations_pruned"]
            orientation_evaluated += counts["orientation_combinations_evaluated"]
            relative_positions_checked += counts["relative_positions_checked"]
            relative_positions_theoretical += counts["relative_positions_theoretical"]
            relative_positions_pruned += counts["relative_positions_pruned"]
            generated.append((group, counts["selected"]))
        # Groups already enforce exact glass type and thickness compatibility.
        filtered_pairs += candidate_pairs - compatible_pairs
        raw_per_pair = len(discrete_angles(prepared.config.angular_step_deg)) ** 2
        orientation_theoretical = candidate_pairs * raw_per_pair
        orientation_pruned = orientation_theoretical - orientation_evaluated
        orientation_pruned_by_compatibility = (candidate_pairs - compatible_pairs) * raw_per_pair
        orientation_pruned_by_symmetry = compatible_pairs * raw_per_pair - orientation_after_symmetry
        orientation_pruned_by_bounds = orientation_after_symmetry - orientation_after_bounds
        orientation_pruned_by_phase = orientation_after_bounds - orientation_after_phase
        orientation_pruned_by_best_bound = orientation_after_phase - orientation_evaluated
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
                    "compactness": round(composition.compactness, 6),
                    "bbox_saving_cells": composition.bbox_saving_cells, "placed": False,
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
            candidate_pairs=candidate_pairs, compatible_pairs=compatible_pairs,
            filtered_pairs=filtered_pairs,
            geometrically_checked_pairs=checked_pairs,
            orientation_combinations_theoretical=orientation_theoretical,
            orientation_combinations_after_symmetry=orientation_after_symmetry,
            orientation_combinations_after_bounds=orientation_after_bounds,
            orientation_combinations_after_phase=orientation_after_phase,
            orientation_combinations_pruned=orientation_pruned,
            orientation_combinations_pruned_by_compatibility=orientation_pruned_by_compatibility,
            orientation_combinations_pruned_by_symmetry=orientation_pruned_by_symmetry,
            orientation_combinations_pruned_by_bounds=orientation_pruned_by_bounds,
            orientation_combinations_pruned_by_phase=orientation_pruned_by_phase,
            orientation_combinations_pruned_by_best_bound=orientation_pruned_by_best_bound,
            orientation_combinations_evaluated=orientation_evaluated,
            relative_positions_theoretical=relative_positions_theoretical,
            relative_positions_pruned=relative_positions_pruned,
            relative_positions_checked=relative_positions_checked,
            accepted_blocks=accepted_count,
            placed_blocks=len(blocks_used),
            pieces_in_blocks=2 * len(blocks_used), standalone_pieces=total_units - 2 * len(blocks_used),
            block_compaction=(sum(compactions) / len(compactions) if compactions else 0.0),
            block_compaction_values=compactions, block_generation_ms=block_generation_ms,
            packing_ms=packing_ms, selected_blocks=tuple(selected_details),
            processing_order=tuple(processing_order),
        )
        return result, trace
