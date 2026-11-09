"""Bounded Beam Search (M6) over the shared immutable raster contracts."""
from dataclasses import dataclass, replace
from decimal import Decimal
from functools import cached_property
from time import perf_counter
from typing import Callable

from .beam_memory import BeamStateMemory, StateMemoryLimit, initial_bound, successor_reserve
from .metrics import largest_rectangle
from .packing import FirstFitEvent, _coordinate, _empty_layout
from .placement import LayoutQueryMemo
from .preparation import prepare_group_units
from .problem import MaterialSource, OptimizationProblem, OptimizationResult, Placement
from .run_geometry import prepare_run_geometry


@dataclass(frozen=True)
class BeamSearchLimits:
    width: int = 2
    children_per_parent: int = 12
    positions_per_orientation: int = 1
    max_expansions: int = 60000
    max_geometry_probes: int = 1000000
    max_state_bytes: int = 32 * 1024 * 1024
    seconds: float = 110.0
    # Bound work BEFORE scoring; None reproduces the historical enumeration.
    # Both policies are native Beam Search and never complete with another engine.
    candidate_limit: int | None = 12

    def __post_init__(self):
        if self.width not in (2, 3, 4):
            raise ValueError("Beam width must be one of 2, 3 or 4.")
        for name in ("children_per_parent", "max_expansions",
                     "max_geometry_probes", "max_state_bytes"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive integer.")
        if self.positions_per_orientation not in (1, 2):
            raise ValueError("positions_per_orientation must be 1 or 2.")
        if not 0 < self.seconds <= 900:
            raise ValueError("seconds must be between zero and 900.")
        if self.candidate_limit is not None and (
            type(self.candidate_limit) is not int or not 1 <= self.candidate_limit <= 128
        ):
            raise ValueError("candidate_limit must be None or an integer between 1 and 128.")


class BeamSearchStopped(RuntimeError):
    """A configured resource limit stopped the current search."""


class BeamSearchResult(OptimizationResult):
    @property
    def method(self):
        return "M6-BS"


def _layout_score(layout, checkpoint=None, *, compact=False):
    if not any(layout.occupied):
        return 0, 0
    # The academic bounded policy minimizes the occupied envelope, after
    # coverage/material usage. Exact largest-residual scoring belongs to the
    # historical policy; computing it for every successor scales with the
    # entire free raster and dominated the 600-800 unit workload.
    recovered = 0
    if not compact:
        free = tuple(usable & ~blocked for usable, blocked in zip(layout.usable, layout.blocked))
        rectangle = largest_rectangle(free, layout.material.columns, checkpoint=checkpoint)
        recovered = rectangle[2] * rectangle[3] if rectangle else 0
    cells = [(row, bits) for row, bits in enumerate(layout.occupied) if bits]
    left = min((bits & -bits).bit_length() - 1 for _, bits in cells)
    right = max(bits.bit_length() for _, bits in cells)
    return recovered, (cells[-1][0] - cells[0][0] + 1) * (right - left)


@dataclass(frozen=True)
class BeamNode:
    layouts: tuple
    placements: tuple = ()
    trace: tuple = ()
    processed: int = 0
    layout_scores: tuple = ()

    @cached_property
    def score(self):
        used = {placement.stock.identity: placement.stock for placement in self.placements}
        area = sum((placement.piece.area_mm2 for placement in self.placements), Decimal(0))
        scores = self.layout_scores or tuple(_layout_score(layout) for layout in self.layouts)
        recovered_cells = sum(score[0] for score in scores)
        envelope_cells = sum(score[1] for score in scores)
        return (
            self.processed - len(self.placements),
            -area,
            sum(stock.source is MaterialSource.SHEET for stock in used.values()),
            sum((stock.area_mm2 for stock in used.values()), Decimal(0)),
            -recovered_cells,
            envelope_cells,
            self.trace,
        )


@dataclass(frozen=True)
class BeamSearchOutcome:
    result: OptimizationResult
    processed: int
    stop_reason: str | None
    statistics: dict
    trace: tuple


@dataclass(frozen=True)
class BeamSearchProgress:
    """Counters of the retained frontier; no provisional placements escape here."""
    completed_levels: int
    processed_units: int
    total_units: int
    expansions: int
    geometry_probes: int
    frontier_size: int


class BeamSearchOptimizer:
    def __init__(self, limits: BeamSearchLimits | None = None):
        self.limits = limits or BeamSearchLimits()

    def optimize(self, problem: OptimizationProblem,
                 on_event: Callable[[FirstFitEvent], None] | None = None,
                 *, checkpoint=None) -> OptimizationResult:
        return self.run(problem, on_event=on_event, checkpoint=checkpoint).result

    def run(self, problem: OptimizationProblem,
            on_event: Callable[[FirstFitEvent], None] | None = None,
            *, checkpoint=None, on_progress: Callable[[BeamSearchProgress], None] | None = None) -> BeamSearchOutcome:
        limits = self.limits
        external_check = checkpoint or (lambda: None)
        started = perf_counter()
        stats = dict(expansions=0, geometry_probes=0, parents=0,
                     alternatives_pruned=0, max_frontier=1, completed_levels=0)

        def check():
            external_check()
            if perf_counter() - started >= limits.seconds:
                raise BeamSearchStopped("TIME_LIMIT")

        def probe(count=1):
            check()
            if stats["geometry_probes"] + count > limits.max_geometry_probes:
                stats["geometry_probes"] = limits.max_geometry_probes
                raise BeamSearchStopped("GEOMETRY_PROBE_LIMIT")
            stats["geometry_probes"] += count

        groups = tuple(
            replace(group, units=prepare_group_units(group.units),
                    stock_candidates=tuple(sorted(
                        group.stock_candidates,
                        key=lambda stock: stock.source is MaterialSource.SHEET,
                    )))
            for group in sorted(problem.groups, key=lambda group: group.key)
        )
        problem = replace(problem, order_ids=tuple(sorted(problem.order_ids)), groups=groups)
        stocks = tuple(stock for group in groups for stock in group.stock_candidates)
        memory = BeamStateMemory(limits.max_state_bytes, checkpoint=check)
        prepared = None
        try:
            memory.reserve(initial_bound(stocks, problem.config))
            ranks = {stock.identity: index for index, stock in enumerate(stocks)}
            prepared = prepare_run_geometry(problem, checkpoint=check)
            initial, empty = [], {}
            for stock in stocks:
                check()
                material = prepared.material(stock)
                # Erosion and empty rows coexist with previously built layouts.
                memory.check((problem, stocks, ranks, initial, material),
                             successor_reserve(material, 0))
                # S2-M6: RasterCache returns one material object per distinct
                # raster, so identical sources share one immutable empty layout
                # (same content as building it per source; nothing mutates it).
                if id(material) not in empty:
                    empty[id(material)] = _empty_layout(material, problem.config)
                initial.append(empty[id(material)])
            initial = tuple(initial)
            # Placing the same mask at the same origin of the same shared empty
            # layout always yields the same score: compute it once per level.
            shared_empty = frozenset(id(layout) for layout in empty.values())
            empty_scores = {}
            beam = [BeamNode(initial, layout_scores=((0, 0),) * len(initial))]
            memory.check((problem, stocks, ranks, initial, beam))
        except (BeamSearchStopped, StateMemoryLimit) as error:
            return self._finish(problem, BeamNode(()), str(error), stats, memory)
        stop_reason = None
        # Prepared geometry has validated the <=10000-angle contract. Reserve
        # Decimal angles, iterator dedup signatures and oriented-unit wrappers;
        # raster allocations themselves retain their independent 64 MiB guard.
        orientation_scratch = 65536 + 1024 * int((Decimal(360) /
            problem.config.angular_step_deg).to_integral_value(rounding="ROUND_CEILING"))

        def progress():
            if on_progress is not None:
                on_progress(BeamSearchProgress(
                    completed_levels=stats["completed_levels"],
                    processed_units=beam[0].processed,
                    total_units=len(problem.units), expansions=stats["expansions"],
                    geometry_probes=stats["geometry_probes"], frontier_size=len(beam),
                ))

        progress()
        positions_memo = LayoutQueryMemo()

        def emit(kind, group, unit=None, placement=None, placed_units=0):
            if on_event is not None:
                on_event(FirstFitEvent(
                    kind=kind, group_key=group.key, unit=unit,
                    placement=placement, placed_units=placed_units,
                    total_units=len(problem.units),
                ))

        def first_feasible(node, stock, orientations):
            layout = node.layouts[ranks[stock.identity]]
            for orientation_index, oriented in enumerate(orientations):
                probe()
                position = positions_memo.find(layout, oriented.orientation.mask)
                if position is not None:
                    return orientation_index, oriented.orientation, position
            return None

        def check_state(scratch):
            # Same roots as graph_bytes((problem, stocks, ranks, initial, beam, pool,
            # children)); only `children` changes within one parent's expansion.
            # The per-level score cache is charged as scratch.
            memory.check_search((problem, stocks, ranks, initial, beam, pool), children,
                                scratch + 512 * len(empty_scores) + positions_memo.bytes_bound)

        def successors(node, group, unit):
            check_state(orientation_scratch + max((successor_reserve(node.layouts[ranks[s.identity]].material,
                                                len(problem.units))
                              for s in group.stock_candidates), default=65536))
            orientations = tuple(prepared.orientations(unit))
            tier = []
            for source in (MaterialSource.REMNANT, MaterialSource.SHEET):
                tier = []
                for stock in group.stock_candidates:
                    if stock.source is source:
                        found = first_feasible(node, stock, orientations)
                        if found is not None:
                            tier.append((stock, found))
                if tier:
                    break
            if not tier:
                yield replace(
                    node, processed=node.processed + 1,
                    trace=node.trace + ((1, -1, -1, -1, -1),),
                )
                return
            bounded = limits.candidate_limit is not None
            if bounded:
                # Empty physical units sharing the same immutable layout are
                # symmetric. Keep the earliest rank, without discarding any
                # distinct used layout or different material contour.
                seen_empty, unique = set(), []
                for stock, found in tier:
                    layout = node.layouts[ranks[stock.identity]]
                    if id(layout) in shared_empty:
                        if id(layout) in seen_empty:
                            continue
                        seen_empty.add(id(layout))
                    unique.append((stock, found))
                ranked_orientations = sorted(enumerate(orientations), key=lambda item: (
                    item[1].orientation.rotation_deg % 90 != 0, item[0]))
                proposals = ((stock, found, index, oriented)
                             for index, oriented in ranked_orientations for stock, found in unique)
            else:
                proposals = ((stock, found, index, oriented)
                             for stock, found in tier for index, oriented in enumerate(orientations))
            generated = 0
            for stock, found, orientation_index, oriented in proposals:
                if bounded and generated >= limits.candidate_limit:
                    return
                rank = ranks[stock.identity]
                layout = node.layouts[rank]
                check_state(orientation_scratch + successor_reserve(layout.material, len(problem.units)))
                mask = oriented.orientation.mask
                probe()
                # Reuse the eligibility scan, retaining its logical probes.
                first = (None if orientation_index < found[0] else found[2]
                         if orientation_index == found[0] else positions_memo.find(layout, mask))
                if first is None:
                    continue
                positions = [first]
                if limits.positions_per_orientation == 2:
                    last = layout.last_position(mask, checkpoint=check, on_scan=probe)
                    if last is not None and last != first:
                        positions.append(last)
                for row, column in positions:
                    if bounded and generated >= limits.candidate_limit:
                        return
                    generated += 1
                    check()
                    if stats["expansions"] >= limits.max_expansions:
                        raise BeamSearchStopped("EXPANSION_LIMIT")
                    stats["expansions"] += 1
                    check_state(orientation_scratch + successor_reserve(layout.material, len(problem.units)))
                    placement = Placement(
                        piece=unit, stock=stock,
                        x_mm=_coordinate(column, problem.config.resolution_mm),
                        y_mm=_coordinate(row, problem.config.resolution_mm),
                        rotation_deg=oriented.orientation.rotation_deg,
                        geometry=oriented.orientation.geometry,
                    )
                    layouts = list(node.layouts)
                    layouts[rank] = layout.place(mask, row, column)
                    layout_scores = list(node.layout_scores)
                    # Unchanged layouts keep their scores; only the placed one is new.
                    key = ((id(layout), orientation_index, row, column)
                           if id(layout) in shared_empty else None)
                    score = empty_scores.get(key) if key is not None else None
                    if score is None:
                        score = _layout_score(layouts[rank], checkpoint=check, compact=bounded)
                        if key is not None:
                            empty_scores[key] = score
                    layout_scores[rank] = score
                    yield BeamNode(
                        tuple(layouts),
                        node.placements + (placement,),
                        node.trace + ((0, rank, orientation_index, row, column),),
                        node.processed + 1,
                        tuple(layout_scores),
                    )
        try:
            for group in groups:
                emit("group_started", group)
                for unit in group.units:
                    check()
                    emit("piece_started", group, unit)
                    # Orientation indexes in the score cache belong to this unit.
                    empty_scores.clear()
                    pool = []
                    for node in beam:
                        check()
                        stats["parents"] += 1
                        children = []
                        for child in successors(node, group, unit):
                            children.append(child)
                            children.sort(key=lambda candidate: candidate.score)
                            if len(children) > limits.children_per_parent:
                                children.pop()
                                stats["alternatives_pruned"] += 1
                        pool = sorted(pool + children, key=lambda candidate: candidate.score)
                        pool = pool[:limits.width]
                    beam = pool
                    stats["completed_levels"] += 1
                    stats["max_frontier"] = max(stats["max_frontier"], len(beam))
                    progress()
                    if beam and beam[0].placements and beam[0].placements[-1].piece.identity == unit.identity:
                        emit("piece_placed", group, unit,
                             beam[0].placements[-1], len(beam[0].placements))
                emit("group_completed", group)
        except (BeamSearchStopped, StateMemoryLimit) as error:
            stop_reason = str(error)

        winner = min(beam, key=lambda node: node.score) if beam else BeamNode(())
        return self._finish(problem, winner, stop_reason, stats, memory)

    def _finish(self, problem, winner, stop_reason, stats, memory):
        statistics = dict(stats, **memory.statistics())
        placements, processed = winner.placements, winner.processed
        statistics.update(bounded_candidates=int(self.limits.candidate_limit is not None),
                          candidate_limit=self.limits.candidate_limit or 0,
                          positions_per_orientation=self.limits.positions_per_orientation)
        result = BeamSearchResult(problem=problem, placements=placements)
        return BeamSearchOutcome(result, processed, stop_reason, statistics, winner.trace)
