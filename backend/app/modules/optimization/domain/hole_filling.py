"""Bounded, deterministic pocket-first selector over the shared raster packer.

Only the current FF candidate is considered. A pocket is a legal-anchor
component disconnected from the usable material boundary for that mask.
The limits below are technical work caps, not commercial cutting rules.
"""
from collections import deque
from dataclasses import dataclass, replace
from typing import Literal

from .packing import pack
from .problem import OptimizationProblem, OptimizationResult


@dataclass(frozen=True)
class HoleFillingLimits:
    # At most 8 small maps and 8192 anchor positions per exploratory pass.
    max_maps: int = 8
    max_anchors: int = 8192
    max_map_anchors: int = 1024
    max_piece_cells: int = 64
    max_piece_rows: int = 16
    # Only small inserts, with bbox no larger than 1/8 of source bbox.
    max_bbox_fraction_denominator: int = 8

    def __post_init__(self):
        if any(type(value) is not int or value < 0 for value in vars(self).values()):
            raise ValueError("Hole filling limits must be non-negative integers")
        if self.max_bbox_fraction_denominator == 0:
            raise ValueError("bbox denominator must be positive")


@dataclass
class HoleFillingStats:
    activation_attempts: int = 0
    pocket_candidates: int = 0
    anchors_checked: int = 0
    placement_checks: int = 0
    accepted_pocket: int = 0
    budget_exhausted: bool = False
    fallback_used: int = 0
    coverage_fallback: bool = False


class HoleFillingSelector:
    """Keep FF source and orientation ordering; inspect only its first candidate."""

    def __init__(self, limits=None, stats=None, checkpoint=None):
        self.limits = limits or HoleFillingLimits()
        self.stats = stats if stats is not None else HoleFillingStats()
        self.checkpoint = checkpoint if checkpoint is not None else lambda: None

    def select(self, candidates):
        candidate = next(iter(candidates), None)
        if candidate is None:
            return None
        layout = candidate.layout
        mask = candidate.orientation.mask
        stats, limits = self.stats, self.limits
        # A pocket requires prior occupation and a small pending insert.
        if (not any(layout.occupied)
                or mask.row_count > limits.max_piece_rows
                or sum(bits.bit_count() for bits in mask.rows) > limits.max_piece_cells
                or mask.row_count * mask.columns * limits.max_bbox_fraction_denominator
                > layout.material.row_count * layout.material.columns):
            stats.fallback_used += 1
            return candidate
        stats.activation_attempts += 1
        height = layout.material.row_count - mask.row_count + 1
        width = layout.material.columns - mask.columns + 1
        size = height * width
        if (stats.pocket_candidates >= limits.max_maps or size > limits.max_map_anchors
                or stats.anchors_checked + size > limits.max_anchors):
            stats.budget_exhausted = True
            stats.fallback_used += 1
            return candidate
        stats.pocket_candidates += 1
        zeros = (0,) * layout.material.row_count
        empty = replace(layout, occupied=zeros, blocked=zeros)
        material_legal = bytearray(size)
        legal = bytearray(size)
        for row in range(height):
            self.checkpoint()
            for column in range(width):
                index = row * width + column
                stats.anchors_checked += 1
                stats.placement_checks += 1
                if empty.check(mask, row, column).is_valid:
                    material_legal[index] = 1
                    stats.placement_checks += 1
                    legal[index] = layout.check(mask, row, column).is_valid

        # A legal origin touching the boundary of the *usable* material is
        # exterior, including irregular materials and margins. Flood through
        # legal origins only; other components are certified pockets.
        queue = deque()
        exterior = bytearray(size)
        for index, is_legal in enumerate(legal):
            if not is_legal:
                continue
            row, column = divmod(index, width)
            if (row == 0 or column == 0 or row == height - 1 or column == width - 1
                    or not material_legal[index - width] or not material_legal[index + width]
                    or not material_legal[index - 1] or not material_legal[index + 1]):
                exterior[index] = 1
                queue.append(index)
        while queue:
            self.checkpoint()
            index = queue.popleft()
            row, column = divmod(index, width)
            for neighbor in (index - width if row else -1,
                             index + width if row + 1 < height else -1,
                             index - 1 if column else -1,
                             index + 1 if column + 1 < width else -1):
                if neighbor >= 0 and legal[neighbor] and not exterior[neighbor]:
                    exterior[neighbor] = 1
                    queue.append(neighbor)
        for index, is_legal in enumerate(legal):
            if is_legal and not exterior[index]:
                row, column = divmod(index, width)
                # The official checker was called above. First row/column wins.
                if (row, column) != (candidate.row, candidate.column):
                    stats.accepted_pocket += 1
                    return replace(candidate, row=row, column=column)
                break
        stats.fallback_used += 1
        return candidate


class HoleFillingResult(OptimizationResult):
    @property
    def method(self) -> Literal["HF"]:
        return "HF"


class HoleFillingOptimizer:
    def __init__(self, limits=None):
        self.limits = limits or HoleFillingLimits()
        self.stats = HoleFillingStats()

    def optimize(self, problem: OptimizationProblem, on_event=None, *, checkpoint=None, on_visual=None):
        self.stats = HoleFillingStats()
        selector = HoleFillingSelector(self.limits, self.stats, checkpoint)
        # Buffer no events from speculative execution: emit only the final run.
        trial = pack(problem, select=selector.select, checkpoint=checkpoint)
        use_hf = bool(self.stats.accepted_pocket)
        chosen = trial
        if use_hf:
            baseline = pack(problem, checkpoint=checkpoint)
            baseline_ids = {placement.piece.identity for placement in baseline.placements}
            trial_ids = {placement.piece.identity for placement in trial.placements}
            if not baseline_ids <= trial_ids:
                chosen = baseline
                use_hf = False
                self.stats.coverage_fallback = True
                self.stats.fallback_used += 1
        if on_event is not None or on_visual is not None:
            replay_selector = HoleFillingSelector(self.limits, checkpoint=checkpoint) if use_hf else None
            # The shared packer emits a capacity score for source selectors;
            # HF has no capacity score, so do not publish that misleading value.
            def visual(event):
                on_visual(replace(event, score=None) if event.kind == "source_selected" else event)

            replay = pack(problem, on_event, select=replay_selector.select if replay_selector else None,
                          checkpoint=checkpoint, on_visual=visual if on_visual is not None else None)
            if replay.placements != chosen.placements:
                raise RuntimeError("Hole filling replay did not reproduce the selected result")
            chosen = replay
        return HoleFillingResult(problem=chosen.problem, placements=chosen.placements)
