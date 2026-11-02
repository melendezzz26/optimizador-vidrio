"""Comparación seeded y política pocket-first, solo para los diagnósticos SP-004."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from time import perf_counter_ns

from app.modules.optimization.domain.best_fit import BestFitSelector
from app.modules.optimization.domain.first_fit import _coordinate
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.domain.packing import _feasible_candidates
from app.modules.optimization.domain.preparation import prepare_group_units
from app.modules.optimization.domain.problem import (
    MaterialSource,
    OptimizationResult,
    PieceUnit,
    Placement,
    StockCandidate,
)
from app.modules.optimization.domain.worst_fit import WorstFitSelector

from .lab import (
    AnchorMap,
    DiagnosticSetup,
    RasterRegion,
    feasible_anchor_map,
    prepare_case,
    setup_from_problem,
)


MIN_RESIDUAL_MM = Decimal(1)
BASELINE_FACTORIES = {
    "FF": None,
    "BF": BestFitSelector,
    "WF": WorstFitSelector,
}


@dataclass(frozen=True)
class PocketOption:
    unit: PieceUnit
    stock: StockCandidate
    anchor_map: AnchorMap
    region: RasterRegion
    orientation_rank: int
    unit_rank: int
    stock_rank: int
    layout_version: int


def _make_placement(unit, stock, orientation, row, column, resolution):
    return Placement(
        piece=unit,
        stock=stock,
        x_mm=_coordinate(column, resolution),
        y_mm=_coordinate(row, resolution),
        rotation_deg=orientation.rotation_deg,
        geometry=orientation.geometry,
    )


def _store_candidate(winner, unit, placements, layouts, resolution):
    layouts[winner.stock.identity] = winner.layout_after
    placements.append(_make_placement(
        unit, winner.stock, winner.orientation, winner.row, winner.column, resolution,
    ))


def _normal_candidate(setup: DiagnosticSetup, group, unit: PieceUnit, layouts: dict, selector=None):
    orientations = setup.prepared.orientations(unit)
    for source in (MaterialSource.REMNANT, MaterialSource.SHEET):
        candidates = _feasible_candidates(
            group, source, orientations, setup.prepared, layouts,
            setup.problem.config, checkpoint=lambda: None,
        )
        winner = next(candidates, None) if selector is None else selector.select(candidates)
        if winner is not None:
            return winner
    return None


def _result(setup: DiagnosticSetup, placements: list[Placement]):
    result = OptimizationResult(problem=setup.problem, placements=tuple(placements))
    return calculate_metrics(result, MIN_RESIDUAL_MM, MIN_RESIDUAL_MM)


def run_baseline(case_id: str, method: str) -> dict:
    if method not in BASELINE_FACTORIES:
        raise ValueError(f"Método baseline desconocido: {method}")
    started = perf_counter_ns()
    setup_started = perf_counter_ns()
    setup = prepare_case(case_id)
    setup_ms = (perf_counter_ns() - setup_started) / 1_000_000
    layouts = dict(setup.layouts)
    placements = list(setup.seed_placements)
    selector = BASELINE_FACTORIES[method]() if BASELINE_FACTORIES[method] else None
    group = setup.problem.groups[0]
    for unit in setup.pending:
        winner = _normal_candidate(setup, group, unit, layouts, selector)
        if winner is not None:
            _store_candidate(winner, unit, placements, layouts, setup.problem.config.resolution_mm)
    metrics_started = perf_counter_ns()
    result, residuals = _result(setup, placements)
    metrics_ms = (perf_counter_ns() - metrics_started) / 1_000_000
    total_ms = (perf_counter_ns() - started) / 1_000_000
    return {
        "case_id": case_id,
        "method": method,
        "setup": setup,
        "result": result,
        "residuals": residuals,
        "total_ms": total_ms,
        "diagnostics": {"setup_ms": setup_ms, "metrics_ms": metrics_ms},
    }


def _find_pockets(setup: DiagnosticSetup, group, remaining, layouts, layout_versions, diagnostics):
    options = []
    origin_row_cache = {}
    unit_rank_by_identity = {unit.identity: rank for rank, unit in enumerate(remaining)}
    stock_rank_by_identity = {stock.identity: rank for rank, stock in enumerate(group.stock_candidates)}
    for unit in remaining:
        unit_rank = unit_rank_by_identity[unit.identity]
        for stock in group.stock_candidates:
            layout = layouts.get(stock.identity)
            if layout is None:
                continue
            for orientation_rank, oriented in enumerate(setup.prepared.orientations(unit)):
                diagnostics["candidate_orientations_scanned"] += 1
                anchor_map = feasible_anchor_map(
                    layout, unit, stock, oriented, row_cache=origin_row_cache,
                )
                diagnostics["origin_generation_ns"] += anchor_map.origin_generation_ns
                diagnostics["pocket_detection_ns"] += anchor_map.component_detection_ns
                diagnostics["geometric_positions_evaluated"] += anchor_map.positions_examined
                diagnostics["pocket_components_detected"] += len(anchor_map.pockets)
                for region in anchor_map.pockets:
                    options.append(PocketOption(
                        unit=unit, stock=stock, anchor_map=anchor_map,
                        region=region, orientation_rank=orientation_rank,
                        unit_rank=unit_rank, stock_rank=stock_rank_by_identity[stock.identity],
                        layout_version=layout_versions.get(stock.identity, 0),
                    ))
    options.sort(key=lambda option: (
        option.region.min_column,
        option.region.min_row,
        option.unit_rank,
        option.orientation_rank,
        option.stock_rank,
        option.region.max_column,
        option.region.max_row,
    ))
    return options


def _run_hole_filling_setup(case_id: str, setup: DiagnosticSetup, started: int, setup_ms: float) -> dict:
    layouts = dict(setup.layouts)
    layout_versions = {identity: 0 for identity in layouts}
    placements = list(setup.seed_placements)
    diagnostics = {
        "candidate_orientations_scanned": 0,
        "geometric_positions_evaluated": 0,
        "pocket_components_detected": 0,
        "pockets_used": 0,
        "fallback_placements": 0,
        "fallback_unplaced": 0,
        "origin_generation_ns": 0,
        "exact_geometry_checks": 0,
        "pocket_detection_ns": 0,
        "placement_policy_ns": 0,
        "fallback_search_ns": 0,
        "placement_commit_ns": 0,
        "pocket_search_decisions": 0,
        "pocket_options_by_decision": [],
        "selected_pockets": [],
    }
    selected_anchor_maps = []
    pocket_placement_contexts = []
    for group in sorted(setup.problem.groups, key=lambda item: item.key):
        remaining = list(prepare_group_units(
            unit for unit in group.units if setup.roles_by_id[unit.piece_id] == "pending"
        ))
        ordered_stocks = tuple(sorted(group.stock_candidates,
                                      key=lambda stock: stock.source is MaterialSource.SHEET))
        group = type(group)(glass_type_id=group.glass_type_id, thickness_mm=group.thickness_mm,
                            units=group.units, stock_candidates=ordered_stocks)
        while remaining:
            diagnostics["pocket_search_decisions"] += 1
            generation_before = diagnostics["origin_generation_ns"]
            detection_before = diagnostics["pocket_detection_ns"]
            scan_started = perf_counter_ns()
            options = _find_pockets(setup, group, remaining, layouts, layout_versions, diagnostics)
            scan_elapsed = perf_counter_ns() - scan_started
            scan_generation = diagnostics["origin_generation_ns"] - generation_before
            scan_detection = diagnostics["pocket_detection_ns"] - detection_before
            diagnostics["placement_policy_ns"] += max(0, scan_elapsed - scan_generation - scan_detection)
            diagnostics["pocket_options_by_decision"].append(len(options))
            if options:
                commit_started = perf_counter_ns()
                option = options[0]
                row, column = min(option.region.cells, key=lambda cell: (cell[1], cell[0]))
                oriented = next(
                    item for item in setup.prepared.orientations(option.unit)
                    if item.orientation.rotation_deg == option.anchor_map.rotation_deg
                )
                if not option.anchor_map.valid_rows[row] & (1 << column):
                    raise AssertionError("El anclaje pocket-first dejó de ser factible antes de colocarse.")
                layout = layouts[option.stock.identity]
                pocket_placement_contexts.append((
                    layout, option.anchor_map, (row, column), oriented.orientation.mask,
                ))
                layouts[option.stock.identity] = layout.place(oriented.orientation.mask, row, column)
                diagnostics["exact_geometry_checks"] += 1
                layout_versions[option.stock.identity] += 1
                placements.append(_make_placement(
                    option.unit, option.stock, oriented.orientation, row, column,
                    setup.problem.config.resolution_mm,
                ))
                diagnostics["pockets_used"] += 1
                selected_anchor_maps.append((option.anchor_map, (row, column)))
                resolution = setup.problem.config.resolution_mm
                diagnostics["selected_pockets"].append({
                    "piece_id": option.unit.piece_id,
                    "unit_index": option.unit.unit_index,
                    "source": option.stock.source.value,
                    "material_id": option.stock.material_id,
                    "rotation_deg": str(option.anchor_map.rotation_deg),
                    "anchor_row": row,
                    "anchor_column": column,
                    "anchor_x_mm": str(Decimal(column) * resolution),
                    "anchor_y_mm": str(Decimal(row) * resolution),
                    "component_cells": len(option.region.cells),
                    "anchor_area_mm2": str(Decimal(len(option.region.cells)) * resolution * resolution),
                    "bbox_row_column": [option.region.min_row, option.region.min_column,
                                        option.region.max_row, option.region.max_column],
                    "candidate_options_at_decision": len(options),
                    "prior_layout_version": option.layout_version,
                })
                diagnostics["placement_commit_ns"] += perf_counter_ns() - commit_started
                remaining.remove(option.unit)
                continue

            unit = remaining.pop(0)
            fallback_started = perf_counter_ns()
            winner = _normal_candidate(setup, group, unit, layouts)
            diagnostics["fallback_search_ns"] += perf_counter_ns() - fallback_started
            if winner is None:
                diagnostics["fallback_unplaced"] += 1
                continue
            _store_candidate(winner, unit, placements, layouts, setup.problem.config.resolution_mm)
            layout_versions[winner.stock.identity] = layout_versions.get(winner.stock.identity, 0) + 1
            diagnostics["fallback_placements"] += 1

    metrics_started = perf_counter_ns()
    result, residuals = _result(setup, placements)
    metrics_ms = (perf_counter_ns() - metrics_started) / 1_000_000
    total_ms = (perf_counter_ns() - started) / 1_000_000
    origin_generation_ns = diagnostics.pop("origin_generation_ns")
    placement_policy_ns = diagnostics.pop("placement_policy_ns")
    fallback_search_ns = diagnostics.pop("fallback_search_ns")
    placement_commit_ns = diagnostics.pop("placement_commit_ns")
    diagnostics["anchor_map_generation_ms"] = origin_generation_ns / 1_000_000
    diagnostics["pocket_placement_ms"] = (placement_policy_ns + placement_commit_ns) / 1_000_000
    diagnostics["fallback_search_ms"] = fallback_search_ns / 1_000_000
    diagnostics["placement_search_ms"] = (
        origin_generation_ns + placement_policy_ns + fallback_search_ns + placement_commit_ns
    ) / 1_000_000
    diagnostics["pocket_detection_ms"] = diagnostics.pop("pocket_detection_ns") / 1_000_000
    diagnostics["total_ms"] = total_ms
    diagnostics["setup_ms"] = setup_ms
    diagnostics["metrics_ms"] = metrics_ms
    return {
        "case_id": case_id,
        "method": "Hole-Filling",
        "setup": setup,
        "result": result,
        "residuals": residuals,
        "total_ms": total_ms,
        "diagnostics": diagnostics,
        "anchor_maps_used": tuple(selected_anchor_maps),
        "pocket_placement_contexts": tuple(pocket_placement_contexts),
    }


def run_hole_filling(case_id: str) -> dict:
    started = perf_counter_ns()
    setup_started = perf_counter_ns()
    setup = prepare_case(case_id)
    setup_ms = (perf_counter_ns() - setup_started) / 1_000_000
    return _run_hole_filling_setup(case_id, setup, started, setup_ms)


def run_hole_filling_problem(problem, case_id: str) -> dict:
    """Puerta posterior al mini-spike: HF sobre un problema oficial inalterado."""
    started = perf_counter_ns()
    setup_started = perf_counter_ns()
    setup = setup_from_problem(problem, case_id)
    setup_ms = (perf_counter_ns() - setup_started) / 1_000_000
    return _run_hole_filling_setup(case_id, setup, started, setup_ms)


def placement_signature(run: dict, *, pending_only=False) -> tuple:
    roles = run["setup"].roles_by_id
    placements = run["result"].placements
    if pending_only:
        placements = tuple(p for p in placements if roles[p.piece.piece_id] == "pending")
    return tuple(sorted((
        placement.piece.piece_id,
        placement.stock.source.value,
        placement.stock.material_id,
        placement.stock.physical_unit_index,
        str(placement.x_mm),
        str(placement.y_mm),
        str(placement.rotation_deg),
    ) for placement in placements))


def metric_values(run: dict) -> dict:
    metrics = run["result"].metrics
    if metrics is None:
        return {
            "requested": run["result"].total_units,
            "placed": 0,
            "unplaced": run["result"].total_units,
            "new_sheets_used": 0,
            "utilization_pct": "0",
            "waste_mm2": "0",
            "recoverable_remnant_mm2": "0",
        }
    return {
        "requested": run["result"].total_units,
        "placed": run["result"].placed_units,
        "unplaced": run["result"].total_units - run["result"].placed_units,
        "new_sheets_used": metrics.new_sheets_used,
        "utilization_pct": str(metrics.utilization_pct),
        "waste_mm2": str(metrics.waste_mm2),
        "recoverable_remnant_mm2": str(metrics.recoverable_remnant_mm2),
        "materials_used": [
            {"source": stock.source.value, "material_id": stock.material_id,
             "physical_unit_index": stock.physical_unit_index}
            for stock in run["result"].materials_used
        ],
        "residuals": [
            {"source": residual.material_source, "material_id": residual.material_id,
             "x_mm": str(residual.x_mm), "y_mm": str(residual.y_mm),
             "width_mm": str(residual.width_mm), "height_mm": str(residual.height_mm),
             "area_mm2": str(residual.area_mm2)}
            for residual in run["residuals"]
        ],
    }
