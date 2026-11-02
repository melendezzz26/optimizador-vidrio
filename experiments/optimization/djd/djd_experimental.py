"""DJD-1/3 experimental sobre la geometría inmutable existente de NewGlass.

La política prueba conjuntos de hasta tres unidades y sus órdenes posibles.
Las áreas solo descartan conjuntos imposibles o demasiado holgados; cada
secuencia superviviente se valida pieza por pieza sobre layouts temporales.
"""
from dataclasses import dataclass, replace
from decimal import Decimal
from fractions import Fraction
from itertools import combinations, permutations
from time import perf_counter_ns

from app.modules.optimization.domain.first_fit import _coordinate, _empty_layout
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.domain.packing import _feasible_candidates
from app.modules.optimization.domain.problem import (
    MaterialSource, OptimizationProblem, OptimizationResult, Placement,
)
from app.modules.optimization.domain.run_geometry import prepare_run_geometry


INITIAL_FULLNESS = Fraction(1, 3)
WASTE_INCREMENT_FRACTION = Fraction(1, 20)
MAX_COMBINATION_SIZE = 3


@dataclass(frozen=True)
class DJDTrace:
    """Contadores y decisiones para analizar el costo y el comportamiento DJD."""
    initial_fill_ratio: tuple[dict, ...]
    combinations_size_1: int
    combinations_size_2: int
    combinations_size_3: int
    combinations_pruned: int
    pruned_by_size: dict[int, int]
    geometric_sequence_checks: int
    cached_sequences_skipped: int
    geometric_checks: int
    feasible_combinations: int
    waste_tolerance_steps: int
    selected_combination_sizes: tuple[int, ...]
    selected_groups: tuple[dict, ...]
    source_switches: int
    processing_order: tuple[tuple[int, int], ...]
    source_decisions: tuple[dict, ...]


def _combination_sets(pending, size):
    """Genera subconjuntos de tamaño fijo en el orden actual, sin materializarlos."""
    return combinations(pending, size)


class DJDExperimental:
    """Implementa selección DJD-1/3 sin modificar el motor productivo."""

    def optimize(self, problem: OptimizationProblem, *, checkpoint=None,
                 minimum_width_mm=Decimal(1), minimum_height_mm=Decimal(1)):
        """Devuelve el resultado oficial calculado y una traza de investigación."""
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
        placements, processing_order, selected_groups = [], [], []
        initial_ratios, source_decisions = [], []
        generated = {1: 0, 2: 0, 3: 0}
        pruned = {1: 0, 2: 0, 3: 0}
        geometric_sequence_checks = cached_sequences_skipped = 0
        geometric_checks = feasible_combinations = tolerance_steps = source_switches = 0

        def try_piece(unit, group, stock, layout):
            """Solicita el primer placement canónico en una copia inmutable del layout."""
            trial_group = replace(group, stock_candidates=(stock,))
            candidates = _feasible_candidates(
                trial_group, stock.source, prepared.orientations(unit), prepared,
                {stock.identity: layout}, problem.config, checkpoint,
            )
            return next(candidates, None)

        for group in problem.groups:
            pending = list(group.units)
            for source_index, stock in enumerate(group.stock_candidates):
                if not pending:
                    break
                checkpoint()
                layout = _empty_layout(prepared.material(stock), problem.config)
                resolution = problem.config.resolution_mm
                # La referencia define el umbral y el paso sobre el área total del objeto.
                initial_capacity = stock.area_mm2
                tolerance_increment = initial_capacity * Decimal(WASTE_INCREMENT_FRACTION.numerator) / Decimal(WASTE_INCREMENT_FRACTION.denominator)
                if initial_capacity <= 0:
                    source_decisions.append({"stock": stock.material_id, "source": stock.source.value,
                                             "decision": "advance_no_usable_capacity"})
                    if source_index + 1 < len(group.stock_candidates) and pending:
                        source_switches += 1
                    continue

                # La fase inicial replica el llenado largest-first hasta 1/3.
                initial_piece_area = Decimal(0)
                placed_piece_area = Decimal(0)
                while pending and initial_piece_area / initial_capacity < Decimal(INITIAL_FULLNESS.numerator) / Decimal(INITIAL_FULLNESS.denominator):
                    checkpoint()
                    selected = None
                    for position, unit in enumerate(pending):
                        generated[1] += 1
                        current_free_area = stock.area_mm2 - placed_piece_area
                        if unit.area_mm2 > current_free_area:
                            pruned[1] += 1
                            continue
                        geometric_checks += 1
                        candidate = try_piece(unit, group, stock, layout)
                        if candidate is None:
                            continue
                        selected = (position, unit, candidate)
                        break
                    if selected is None:
                        break
                    position, unit, candidate = selected
                    layout = candidate.layout_after
                    initial_piece_area += unit.area_mm2
                    placed_piece_area += unit.area_mm2
                    pending.pop(position)
                    placements.append(self._make_placement(unit, stock, candidate, resolution))
                    processing_order.append(unit.identity)
                    selected_groups.append({"source": stock.source.value, "material_id": stock.material_id,
                                            "size": 1, "phase": "initial_fill",
                                            "piece_ids": [unit.piece_id], "waste_tolerance_mm2": "0"})

                initial_ratio = initial_piece_area / initial_capacity
                initial_ratios.append({"source": stock.source.value, "material_id": stock.material_id,
                                       "physical_unit_index": stock.physical_unit_index,
                                       "ratio": str(initial_ratio),
                                       "initial_capacity_mm2": str(initial_capacity)})
                geometric_failure_cache = set()
                source_placed_before = len(placements)

                # La búsqueda vuelve a tamaño 1 después de cada grupo aceptado.
                while pending:
                    checkpoint()
                    # El residuo nominal alimenta el pruning; no certifica geometría.
                    free_area = stock.area_mm2 - placed_piece_area
                    if free_area <= 0:
                        break
                    waste = Decimal(0)
                    selected_trial = None
                    selected_size = None

                    while selected_trial is None:
                        checkpoint()
                        # El artículo prioriza singles, luego pares y después ternas.
                        for size in range(1, MAX_COMBINATION_SIZE + 1):
                            if len(pending) < size:
                                continue
                            found = False
                            for combination in _combination_sets(pending, size):
                                generated[size] += 1
                                combination_area = sum((unit.area_mm2 for unit in combination), Decimal(0))
                                residual_estimate = free_area - combination_area
                                if combination_area > free_area or residual_estimate > waste:
                                    pruned[size] += 1
                                    continue
                                # En 2D el orden importa: se enumeran permutaciones estables.
                                for ordered_group in permutations(combination):
                                    checkpoint()
                                    sequence_key = tuple(unit.identity for unit in ordered_group)
                                    if sequence_key in geometric_failure_cache:
                                        cached_sequences_skipped += 1
                                        continue
                                    geometric_sequence_checks += 1
                                    trial_layout = layout
                                    trial_candidates = []
                                    sequence_fits = True
                                    for unit in ordered_group:
                                        geometric_checks += 1
                                        candidate = try_piece(unit, group, stock, trial_layout)
                                        if candidate is None:
                                            sequence_fits = False
                                            break
                                        trial_candidates.append(candidate)
                                        trial_layout = candidate.layout_after
                                    if not sequence_fits:
                                        geometric_failure_cache.add(sequence_key)
                                        continue
                                    feasible_combinations += 1
                                    selected_trial = (ordered_group, trial_candidates, trial_layout)
                                    selected_size = size
                                    found = True
                                    break
                                if found:
                                    break
                            if found:
                                break
                        if selected_trial is not None:
                            break
                        current_free_area = stock.area_mm2 - placed_piece_area
                        if waste < current_free_area and tolerance_increment > 0:
                            waste += tolerance_increment
                            tolerance_steps += 1
                            continue
                        break

                    if selected_trial is None:
                        source_decisions.append({"source": stock.source.value, "material_id": stock.material_id,
                                                 "decision": "advance_no_acceptable_group",
                                                 "remaining_free_area_mm2": str(free_area)})
                        break

                    ordered_group, trial_candidates, layout_after_group = selected_trial
                    selected_ids = {unit.identity for unit in ordered_group}
                    pending = [unit for unit in pending if unit.identity not in selected_ids]
                    for unit, candidate in zip(ordered_group, trial_candidates):
                        placements.append(self._make_placement(unit, stock, candidate, resolution))
                        processing_order.append(unit.identity)
                    layout = layout_after_group
                    placed_piece_area += sum((unit.area_mm2 for unit in ordered_group), Decimal(0))
                    selected_groups.append({"source": stock.source.value, "material_id": stock.material_id,
                                            "size": selected_size,
                                            "piece_ids": [unit.piece_id for unit in ordered_group],
                                            "unit_ids": [list(unit.identity) for unit in ordered_group],
                                            "waste_tolerance_mm2": str(waste),
                                            "estimated_residual_mm2": str(free_area - sum((u.area_mm2 for u in ordered_group), Decimal(0)))})
                    geometric_failure_cache.clear()

                if pending and source_index + 1 < len(group.stock_candidates):
                    source_switches += 1
                if len(placements) > source_placed_before:
                    source_decisions.append({"source": stock.source.value, "material_id": stock.material_id,
                                             "decision": "source_complete",
                                             "placed_units": len(placements) - source_placed_before})

        result = OptimizationResult(problem=problem, placements=tuple(placements))
        result, _ = calculate_metrics(result, minimum_width_mm, minimum_height_mm)
        result = replace(result, computation_time_ms=(perf_counter_ns() - started) // 1_000_000)
        trace = DJDTrace(
            initial_fill_ratio=tuple(initial_ratios),
            combinations_size_1=generated[1], combinations_size_2=generated[2],
            combinations_size_3=generated[3], combinations_pruned=sum(pruned.values()),
            pruned_by_size=dict(pruned), geometric_sequence_checks=geometric_sequence_checks,
            cached_sequences_skipped=cached_sequences_skipped, geometric_checks=geometric_checks,
            feasible_combinations=feasible_combinations, waste_tolerance_steps=tolerance_steps,
            selected_combination_sizes=tuple(item["size"] for item in selected_groups),
            selected_groups=tuple(selected_groups), source_switches=source_switches,
            processing_order=tuple(processing_order), source_decisions=tuple(source_decisions),
        )
        return result, trace

    @staticmethod
    def _make_placement(unit, stock, candidate, resolution):
        """Crea un placement NewGlass a partir del candidato ya validado."""
        return Placement(
            piece=unit, stock=stock,
            x_mm=_coordinate(candidate.column, resolution),
            y_mm=_coordinate(candidate.row, resolution),
            rotation_deg=candidate.orientation.rotation_deg,
            geometry=candidate.orientation.geometry,
        )
