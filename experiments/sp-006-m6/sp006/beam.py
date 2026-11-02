"""BS-k v1: árbol de placements raster, orden fijo y poda determinista.

Solo SP-006. Este módulo no forma parte del backend ni del coordinador.
"""
from dataclasses import dataclass, replace
from decimal import Decimal
from functools import cached_property
from time import perf_counter

from app.modules.optimization.domain.metrics import largest_rectangle
from app.modules.optimization.domain.packing import _coordinate, _empty_layout
from app.modules.optimization.domain.preparation import prepare_group_units
from app.modules.optimization.domain.problem import MaterialSource, OptimizationResult, Placement
from app.modules.optimization.domain.run_geometry import prepare_run_geometry

VERSION = "SP006-BS-v1"


@dataclass(frozen=True)
class SearchLimits:
    width: int = 3
    children_per_parent: int = 12
    positions_per_orientation: int = 2
    max_expansions: int = 60000
    max_geometry_probes: int = 1000000
    max_state_bytes: int = 32 * 1024 * 1024
    seconds: float = 30.0

    def __post_init__(self):
        if self.width not in (2, 3, 4):
            raise ValueError("SP-006 evalúa k=2,3,4.")
        for name in ("children_per_parent", "max_expansions", "max_geometry_probes", "max_state_bytes"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"Límite inválido: {name}")
        if self.positions_per_orientation not in (1, 2) or not 0 < self.seconds <= 120:
            raise ValueError("Posiciones o tiempo fuera del rango experimental.")


class SearchStopped(RuntimeError):
    pass


class ExperimentalBeamResult(OptimizationResult):
    @property
    def method(self):
        return "M6-BS"


@dataclass(frozen=True)
class Node:
    # Índice de layouts = rango estable de fuente física, incluso fuentes sin usar.
    layouts: tuple
    placements: tuple = ()
    trace: tuple = ()
    processed: int = 0

    @cached_property
    def score(self):
        used = {p.stock.identity: p.stock for p in self.placements}
        area = sum((p.piece.area_mm2 for p in self.placements), Decimal(0))
        recovered_cells = envelope_cells = 0
        for layout in self.layouts:
            if not any(layout.occupied):
                continue
            free = tuple(u & ~b for u, b in zip(layout.usable, layout.blocked))
            rectangle = largest_rectangle(free, layout.material.columns)
            if rectangle:
                recovered_cells += rectangle[2] * rectangle[3]
            cells = [(r, bits) for r, bits in enumerate(layout.occupied) if bits]
            left = min((bits & -bits).bit_length() - 1 for _, bits in cells)
            right = max(bits.bit_length() for _, bits in cells)
            envelope_cells += (cells[-1][0] - cells[0][0] + 1) * (right - left)
        return (
            self.processed - len(self.placements), -area,
            sum(s.source is MaterialSource.SHEET for s in used.values()),
            sum((s.area_mm2 for s in used.values()), Decimal(0)),
            -recovered_cells, envelope_cells, self.trace,
        )


@dataclass(frozen=True)
class BeamOutcome:
    result: OptimizationResult
    processed: int
    stop_reason: str | None
    statistics: dict
    trace: tuple


class BeamSearch:
    def __init__(self, limits=None):
        self.limits = limits or SearchLimits()

    def optimize(self, problem, *, checkpoint=None):
        limits = self.limits
        external_check = checkpoint or (lambda: None)
        started = perf_counter()
        stats = dict(expansions=0, geometry_probes=0, parents=0,
                     alternatives_pruned=0, max_frontier=1, completed_levels=0)

        def check():
            external_check()
            if perf_counter() - started >= limits.seconds:
                raise SearchStopped("TIME_LIMIT")

        def probe():
            check()
            if stats["geometry_probes"] >= limits.max_geometry_probes:
                raise SearchStopped("GEOMETRY_PROBE_LIMIT")
            stats["geometry_probes"] += 1

        groups = tuple(replace(g, units=prepare_group_units(g.units), stock_candidates=tuple(
            sorted(g.stock_candidates, key=lambda s: s.source is MaterialSource.SHEET)
        )) for g in sorted(problem.groups, key=lambda g: g.key))
        problem = replace(problem, order_ids=tuple(sorted(problem.order_ids)), groups=groups)
        stocks = tuple(s for g in groups for s in g.stock_candidates)
        ranks = {s.identity: i for i, s in enumerate(stocks)}
        # Antes de asignar layouts: cota conservadora sin contar compartición.
        from app.modules.optimization.domain.preparation import bbox_dimensions
        per_node = 2048 + len(problem.units) * 1024
        for stock in stocks:
            w, h = bbox_dimensions(stock.geometry)
            cols, rows = (int((v / problem.config.resolution_mm).to_integral_value(
                rounding="ROUND_CEILING")) for v in (w, h))
            per_node += rows * (40 + 4 * ((cols + 29) // 30)) * 4
        retained_bound = 3 * limits.width + limits.children_per_parent + 3
        estimated = per_node * retained_bound
        if estimated > limits.max_state_bytes:
            return BeamOutcome(ExperimentalBeamResult(problem=problem, placements=()), 0,
                               "STATE_MEMORY_LIMIT", dict(stats, state_bytes_bound=estimated), ())
        prepared = prepare_run_geometry(problem, checkpoint=check)
        initial = tuple(_empty_layout(prepared.material(s), problem.config) for s in stocks)
        beam = [Node(initial)]
        stop_reason = None

        def first_feasible(node, stock, orientations):
            """Certifica factibilidad completa del nivel, antes de cualquier poda."""
            layout = node.layouts[ranks[stock.identity]]
            for oi, oriented in enumerate(orientations):
                probe()
                position = layout.first_position(oriented.orientation.mask)
                if position is not None:
                    return oi, oriented.orientation, position
            return None

        def successors(node, group, unit):
            orientations = prepared.orientations(unit)  # vista reiterable común, 5° y dedup
            tier = []
            # Un límite nunca autoriza concluir que un retazo no cabe.
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
                yield replace(node, processed=node.processed + 1,
                              trace=node.trace + ((1, -1, -1, -1, -1),))
                return
            for stock, _ in tier:
                rank = ranks[stock.identity]
                layout = node.layouts[rank]
                for oi, oriented in enumerate(orientations):
                    orientation = oriented.orientation
                    mask = orientation.mask
                    probe()
                    first = layout.first_position(mask)
                    if first is None:
                        continue
                    positions = [first]
                    if limits.positions_per_orientation == 2:
                        # Segunda alternativa espacial: última posición válida fila/columna.
                        last = None
                        for row in range(layout.material.row_count - mask.row_count, -1, -1):
                            for column in range(layout.material.columns - mask.columns, -1, -1):
                                probe()
                                if layout.check(mask, row, column).is_valid:
                                    last = row, column
                                    break
                            if last is not None:
                                break
                        if last != first and last is not None:
                            positions.append(last)
                    for row, column in positions:
                        check()
                        if stats["expansions"] >= limits.max_expansions:
                            raise SearchStopped("EXPANSION_LIMIT")
                        stats["expansions"] += 1
                        placement = Placement(piece=unit, stock=stock,
                            x_mm=_coordinate(column, problem.config.resolution_mm),
                            y_mm=_coordinate(row, problem.config.resolution_mm),
                            rotation_deg=orientation.rotation_deg, geometry=orientation.geometry)
                        layouts = list(node.layouts)
                        layouts[rank] = layout.place(mask, row, column)
                        yield Node(tuple(layouts), node.placements + (placement,),
                                   node.trace + ((0, rank, oi, row, column),), node.processed + 1)

        try:
            for group in groups:
                for unit in group.units:
                    pool = []
                    for node in beam:
                        check()
                        stats["parents"] += 1
                        children = []
                        for child in successors(node, group, unit):
                            children.append(child)
                            children.sort(key=lambda n: n.score)
                            if len(children) > limits.children_per_parent:
                                children.pop()
                                stats["alternatives_pruned"] += 1
                        # beam anterior vive hasta completar TODO el nivel (rollback ante límite).
                        pool = sorted(pool + children, key=lambda n: n.score)[:limits.width]
                    beam = pool
                    stats["completed_levels"] += 1
                    stats["max_frontier"] = max(stats["max_frontier"], len(beam))
        except SearchStopped as error:
            stop_reason = str(error)
        winner = min(beam, key=lambda n: n.score)
        return BeamOutcome(ExperimentalBeamResult(problem=problem, placements=winner.placements),
            winner.processed, stop_reason, dict(stats, state_bytes_bound=estimated), winner.trace)
