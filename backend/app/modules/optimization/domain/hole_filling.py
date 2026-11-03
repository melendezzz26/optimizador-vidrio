"""Deterministic bounded local placement-pocket search over the shared packer."""
from collections import deque
from dataclasses import dataclass, replace
from itertools import chain
from typing import Literal

from .packing import pack
from .placement import PlacementIssue
from .problem import MaterialSource, OptimizationProblem, OptimizationResult


@dataclass(frozen=True)
class HoleFillingLimits:
    # Technical work caps, not minimum/maximum commercial piece sizes.
    max_regions: int = 8
    max_region_anchors: int = 512
    max_region_checks: int = 512
    max_anchors: int = 8192
    max_check_rows: int = 262144
    max_seed_probes: int = 2048
    max_seeds_per_orientation: int = 256
    max_boundary_rows: int = 512
    max_edges_per_row: int = 64
    max_orientations: int = 3
    max_orientation_evaluations: int = 24
    max_bbox_fraction_denominator: int = 8

    def __post_init__(self):
        if any(type(value) is not int or value < 0 for value in vars(self).values()):
            raise ValueError("Hole filling limits must be non-negative integers")
        if self.max_bbox_fraction_denominator == 0:
            raise ValueError("bbox denominator must be positive")


@dataclass
class HoleFillingStats:
    activation_attempts: int = 0
    orientations_inspected: int = 0
    boundary_rows: int = 0
    seed_probes: int = 0
    pocket_candidates: int = 0  # Connected regions explored, not proven pockets.
    max_region_checks_observed: int = 0
    max_region_anchors_observed: int = 0
    anchors_checked: int = 0
    placement_checks: int = 0
    check_rows: int = 0
    accepted_pocket: int = 0
    budget_exhausted: bool = False
    fallback_used: int = 0
    coverage_fallback: bool = False
    sheet_fallback: bool = False


class _BudgetReached(Exception):
    pass


class HoleFillingSelector:
    """Keep FF source order; examine bounded local regions and raw angles."""

    def __init__(self, limits=None, stats=None, checkpoint=None):
        self.limits = limits or HoleFillingLimits()
        self.stats = stats if stats is not None else HoleFillingStats()
        self.checkpoint = checkpoint if checkpoint is not None else lambda: None

    def _seeds(self, candidate, mask):
        layout, limits, stats = candidate.layout, self.limits, self.stats
        height = layout.material.row_count - mask.row_count + 1
        width = layout.material.columns - mask.columns + 1
        if height <= 0 or width <= 0:
            return
        if not limits.max_boundary_rows:
            stats.budget_exhausted = True
            return
        # Sample row transitions of the existing blocked raster; no anchor map.
        stride = max(1, (layout.material.row_count + limits.max_boundary_rows - 1)
                     // limits.max_boundary_rows)
        if stride > 1:
            stats.budget_exhausted = True
        transitions = []
        for row in range(1, layout.material.row_count, stride):
            stats.boundary_rows += 1
            self.checkpoint()
            if layout.blocked[row] != layout.blocked[max(0, row - stride)]:
                transitions.append(row)
        ys = {y for row in transitions for y in (row, row - mask.row_count,
                                                   row - mask.row_count + 1)
              if 0 <= y < height}
        for row in sorted(ys, reverse=True):
            columns = set()
            for physical_row in (row, row + mask.row_count - 1):
                bits = layout.blocked[physical_row]
                edges = (bits ^ (bits << 1)) & ((1 << (layout.material.columns + 1)) - 1)
                for _ in range(limits.max_edges_per_row):
                    if not edges:
                        break
                    bit = edges & -edges
                    edge = bit.bit_length() - 1
                    for column in (edge, edge - mask.columns):
                        if 0 <= column < width:
                            columns.add(column)
                    edges ^= bit
                if edges:
                    stats.budget_exhausted = True
            for column in sorted(columns):
                yield row, column

    def _find(self, candidate, orientation):
        layout, mask = candidate.layout, orientation.mask
        limits, stats = self.limits, self.stats
        height = layout.material.row_count - mask.row_count + 1
        width = layout.material.columns - mask.columns + 1
        cache, processed = {}, set()

        def check(row, column, region_start=None):
            if row < 0 or column < 0 or row >= height or column >= width:
                return False, PlacementIssue.OUT_OF_BOUNDS
            key = (row, column)
            if key not in cache:
                if (stats.anchors_checked >= limits.max_anchors
                        or stats.check_rows + mask.row_count > limits.max_check_rows
                        or (region_start is not None and
                            stats.anchors_checked - region_start >= limits.max_region_checks)):
                    raise _BudgetReached
                self.checkpoint()
                outcome = layout.check(mask, row, column)
                stats.anchors_checked += 1
                stats.placement_checks += 1
                stats.check_rows += mask.row_count
                cache[key] = (outcome.is_valid, outcome.issue)
            return cache[key]

        seeds_this_orientation = 0
        for row, column in self._seeds(candidate, mask):
            if seeds_this_orientation >= limits.max_seeds_per_orientation:
                stats.budget_exhausted = True
                break
            if stats.seed_probes >= limits.max_seed_probes:
                stats.budget_exhausted = True
                return None
            seeds_this_orientation += 1
            stats.seed_probes += 1
            if (row, column) in processed:
                continue
            component = None
            region_start = None
            try:
                valid, _ = check(row, column)
                if not valid:
                    continue
                directions = ((-1, 0), (1, 0), (0, -1), (0, 1))
                adjacent = [check(row + dy, column + dx)[1] for dy, dx in directions]
                obstruction = (PlacementIssue.OVERLAP, PlacementIssue.SEPARATION)
                if not (any(issue in obstruction for issue in adjacent[:2]) and
                        any(issue in obstruction for issue in adjacent[2:])):
                    continue
                if stats.pocket_candidates >= limits.max_regions:
                    stats.budget_exhausted = True
                    return None
                stats.pocket_candidates += 1
                region_start = stats.anchors_checked
                component = set()
                if not limits.max_region_anchors:
                    raise _BudgetReached
                queue = deque([(row, column)])
                component.add((row, column))
                external = False
                while queue and not external:
                    current_row, current_column = queue.popleft()
                    self.checkpoint()
                    for dy, dx in directions:
                        neighbor = (current_row + dy, current_column + dx)
                        if neighbor in component:
                            continue
                        legal, issue = check(*neighbor, region_start=region_start)
                        if issue in (PlacementIssue.OUT_OF_BOUNDS, PlacementIssue.MARGIN):
                            external = True
                            break
                        if legal:
                            if len(component) >= limits.max_region_anchors:
                                raise _BudgetReached
                            component.add(neighbor)
                            queue.append(neighbor)
                processed.update(component)
                if not external:
                    return min(component)
            except _BudgetReached:
                # A partial component is never treated as a certified pocket.
                stats.budget_exhausted = True
                if stats.anchors_checked >= limits.max_anchors or stats.check_rows + mask.row_count > limits.max_check_rows:
                    return None
                if component is not None:
                    processed.update(component)
                continue
            finally:
                if region_start is not None:
                    stats.max_region_checks_observed = max(
                        stats.max_region_checks_observed, stats.anchors_checked - region_start)
                    stats.max_region_anchors_observed = max(
                        stats.max_region_anchors_observed, len(component))
        return None

    def select(self, candidates):
        candidate = next(iter(candidates), None)
        if candidate is None:
            return None
        layout, mask = candidate.layout, candidate.orientation.mask
        limits, stats = self.limits, self.stats
        if not any(layout.occupied):
            stats.fallback_used += 1
            return candidate
        stats.activation_attempts += 1
        if not limits.max_orientations or stats.pocket_candidates >= limits.max_regions:
            stats.budget_exhausted = True
            stats.fallback_used += 1
            return candidate
        alternatives = ()
        if candidate.orientations is not None and limits.max_orientations > 1:
            alternatives = ((candidate.orientation_rank + index, item.orientation)
                            for index, item in enumerate(candidate.orientations.next_angles(
                                candidate.orientation.rotation_deg, limits.max_orientations - 1), start=1))
        orientations = iter(chain(((candidate.orientation_rank, candidate.orientation),), alternatives))
        seen = set()
        while limits.max_orientations and stats.orientations_inspected < limits.max_orientation_evaluations:
            try:
                rank, orientation = next(orientations)
            except StopIteration:
                break
            mask = orientation.mask
            signature = (mask.columns, mask.rows)
            if signature in seen:
                continue
            seen.add(signature)
            stats.orientations_inspected += 1
            if (mask.row_count * mask.columns * limits.max_bbox_fraction_denominator
                    > layout.material.row_count * layout.material.columns):
                continue
            position = self._find(candidate, orientation)
            if position is not None and (orientation.rotation_deg != candidate.orientation.rotation_deg or
                                         position != (candidate.row, candidate.column)):
                stats.accepted_pocket += 1
                return replace(candidate, orientation=orientation, orientation_rank=rank,
                               row=position[0], column=position[1])
        else:
            if limits.max_orientations and stats.orientations_inspected >= limits.max_orientation_evaluations:
                stats.budget_exhausted = True
        stats.fallback_used += 1
        return candidate


class HoleFillingResult(OptimizationResult):
    @property
    def method(self) -> Literal["HF"]:
        return "HF"


def _fallback_reason(trial, baseline):
    """Preserve FF identities; protect sheet count only for the same set."""
    baseline_ids = {placement.piece.identity for placement in baseline.placements}
    trial_ids = {placement.piece.identity for placement in trial.placements}
    if not baseline_ids <= trial_ids:
        return "coverage"
    if baseline_ids == trial_ids:
        hf_sheets = sum(stock.source is MaterialSource.SHEET for stock in trial.materials_used)
        ff_sheets = sum(stock.source is MaterialSource.SHEET for stock in baseline.materials_used)
        if hf_sheets > ff_sheets:
            return "sheets"
    return None


class HoleFillingOptimizer:
    def __init__(self, limits=None):
        self.limits = limits or HoleFillingLimits()
        self.stats = HoleFillingStats()

    def optimize(self, problem: OptimizationProblem, on_event=None, *, checkpoint=None, on_visual=None):
        self.stats = HoleFillingStats()
        selector = HoleFillingSelector(self.limits, self.stats, checkpoint)
        trial = pack(problem, select=selector.select, checkpoint=checkpoint)
        use_hf = bool(self.stats.accepted_pocket)
        chosen = trial
        if use_hf:
            baseline = pack(problem, checkpoint=checkpoint)
            reason = _fallback_reason(trial, baseline)
            if reason is not None:
                chosen = baseline
                use_hf = False
                self.stats.coverage_fallback = reason == "coverage"
                self.stats.sheet_fallback = reason == "sheets"
                self.stats.fallback_used += 1
        if on_event is not None or on_visual is not None:
            replay_selector = HoleFillingSelector(self.limits, checkpoint=checkpoint) if use_hf else None
            def visual(event):
                on_visual(replace(event, score=None) if event.kind == "source_selected" else event)
            replay = pack(problem, on_event, select=replay_selector.select if replay_selector else None,
                          checkpoint=checkpoint, on_visual=visual if on_visual is not None else None)
            if replay.placements != chosen.placements:
                raise RuntimeError("Hole filling replay did not reproduce the selected result")
            chosen = replay
        return HoleFillingResult(problem=chosen.problem, placements=chosen.placements)
