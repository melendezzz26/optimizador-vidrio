"""Política Filler experimental sobre los componentes geométricos de NewGlass.

El recorrido de alto nivel está aislado porque el contrato productivo de pack()
no permite conservar una fuente activa ni su layout mientras se buscan piezas
pendientes alternativas. RasterCache, preparación geométrica, candidatos,
SheetLayout y Placement se importan de producción sin modificarla.
"""
from dataclasses import dataclass, replace
from decimal import Decimal
from time import perf_counter_ns

from app.modules.optimization.domain.first_fit import _coordinate, _empty_layout
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.domain.packing import _feasible_candidates
from app.modules.optimization.domain.problem import (
    MaterialSource, OptimizationProblem, OptimizationResult, Placement,
)
from app.modules.optimization.domain.run_geometry import prepare_run_geometry


@dataclass(frozen=True)
class FillerTrace:
    """Registro explicativo de intentos y decisiones de avance de Filler."""
    attempts: tuple[dict, ...]
    placements: tuple[dict, ...]
    source_switches: int
    skipped_piece_attempts: int
    successful_fill_after_skip: int
    processing_order: tuple[tuple[int, int], ...]
    pieces_per_source: dict[str, int]


class FillerExperimental:
    """Filler determinista; cada fuente activa se agota antes de avanzar."""

    def optimize(self, problem: OptimizationProblem, *, checkpoint=None,
                 minimum_width_mm=Decimal(1), minimum_height_mm=Decimal(1)):
        """Retorna resultado medido con métricas oficiales y una traza diagnóstica."""
        started = perf_counter_ns()
        checkpoint = checkpoint or (lambda: None)
        groups = tuple(replace(
            group,
            units=tuple(sorted(group.units, key=lambda unit: (
                -unit.area_mm2, unit.piece_id, unit.unit_index, unit.order_id,
            ))),
            stock_candidates=tuple(sorted(
                group.stock_candidates,
                key=lambda stock: (stock.source is MaterialSource.SHEET,
                                   stock.material_id, stock.physical_unit_index),
            )),
        ) for group in sorted(problem.groups, key=lambda group: group.key))
        problem = replace(problem, order_ids=tuple(sorted(problem.order_ids)), groups=groups)
        prepared = prepare_run_geometry(problem, checkpoint=checkpoint)
        layouts, placements, attempts, decisions = {}, [], [], []
        processing_order, pieces_per_source = [], {}
        switches = skips = successes_after_skip = 0

        for group in problem.groups:
            pending = list(group.units)
            # Cada candidato físico se convierte en fuente activa en orden:
            # primero retazos, luego planchas, con desempate estable por ID.
            for source_index, stock in enumerate(group.stock_candidates):
                if not pending:
                    break
                checkpoint()
                layout = layouts.get(stock.identity)
                if layout is None:
                    layout = _empty_layout(prepared.material(stock), problem.config)
                skipped_on_source = []
                placed_on_source = 0
                while pending:
                    checkpoint()
                    winner = None
                    winner_unit = None
                    # Filler recorre el orden pendiente completo y toma la
                    # primera unidad geométricamente factible en la fuente.
                    for position, unit in enumerate(pending):
                        checkpoint()
                        orientations = prepared.orientations(unit)
                        single_stock_group = replace(group, stock_candidates=(stock,))
                        candidates = _feasible_candidates(
                            single_stock_group, stock.source, orientations, prepared,
                            {stock.identity: layout}, problem.config, checkpoint,
                        )
                        candidate = next(candidates, None)
                        fits = candidate is not None
                        attempts.append({
                            "piece_id": unit.piece_id, "unit_index": unit.unit_index,
                            "area_mm2": str(unit.area_mm2), "source": stock.source.value,
                            "material_id": stock.material_id,
                            "physical_unit_index": stock.physical_unit_index,
                            "fits": fits,
                            "rotation_deg": str(candidate.orientation.rotation_deg) if fits else None,
                            "x_mm": str(_coordinate(candidate.column, problem.config.resolution_mm)) if fits else None,
                            "y_mm": str(_coordinate(candidate.row, problem.config.resolution_mm)) if fits else None,
                            "decision": "place" if fits else "skip_temporarily",
                        })
                        if fits:
                            winner, winner_unit = candidate, (position, unit)
                            break
                        skipped_on_source.append(unit.identity)
                        skips += 1
                    if winner is None:
                        decisions.append({"source": stock.source.value,
                                          "material_id": stock.material_id,
                                          "decision": "switch_source_no_pending_piece_fits"})
                        break
                    position, unit = winner_unit
                    pending.pop(position)
                    if skipped_on_source:
                        successes_after_skip += 1
                        decisions.append({"source": stock.source.value,
                                          "material_id": stock.material_id,
                                          "piece_id": unit.piece_id,
                                          "decision": "stay_after_temporary_skips"})
                    else:
                        decisions.append({"source": stock.source.value,
                                          "material_id": stock.material_id,
                                          "piece_id": unit.piece_id,
                                          "decision": "stay_after_placement"})
                    skipped_on_source = []
                    layout = winner.layout_after
                    layouts[stock.identity] = layout
                    placement = Placement(
                        piece=unit, stock=stock,
                        x_mm=_coordinate(winner.column, problem.config.resolution_mm),
                        y_mm=_coordinate(winner.row, problem.config.resolution_mm),
                        rotation_deg=winner.orientation.rotation_deg,
                        geometry=winner.orientation.geometry,
                    )
                    placements.append(placement)
                    processing_order.append(unit.identity)
                    placed_on_source += 1
                    decisions[-1]["piece_id"] = unit.piece_id
                    decisions[-1]["placement"] = {
                        "x_mm": str(placement.x_mm), "y_mm": str(placement.y_mm),
                        "rotation_deg": str(placement.rotation_deg),
                    }
                if placed_on_source:
                    pieces_per_source[f"{stock.source.value}:{stock.material_id}:{stock.physical_unit_index}"] = placed_on_source
                # Avanzar al siguiente stock solo cuando la fuente activa ya
                # no admite ninguna unidad de las que siguen pendientes.
                if pending and source_index + 1 < len(group.stock_candidates):
                    switches += 1
            # Las unidades sin factibilidad en ninguna fuente quedan pendientes
            # y OptimizationResult las expone como no colocadas.

        result = OptimizationResult(problem=problem, placements=tuple(placements))
        result, _ = calculate_metrics(result, minimum_width_mm, minimum_height_mm)
        result = replace(result, computation_time_ms=(perf_counter_ns() - started) // 1_000_000)
        trace = FillerTrace(
            attempts=tuple(attempts), placements=tuple({
                "piece_id": p.piece.piece_id, "unit_index": p.piece.unit_index,
                "source": p.stock.source.value, "material_id": p.stock.material_id,
                "physical_unit_index": p.stock.physical_unit_index,
                "x_mm": str(p.x_mm), "y_mm": str(p.y_mm),
                "rotation_deg": str(p.rotation_deg),
            } for p in placements),
            source_switches=switches, skipped_piece_attempts=skips,
            successful_fill_after_skip=successes_after_skip,
            processing_order=tuple(processing_order), pieces_per_source=pieces_per_source,
        )
        return result, trace
