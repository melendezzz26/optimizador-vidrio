"""Revalidación común independiente de la elección de placements."""
from decimal import Decimal
from collections.abc import Mapping
from enum import Enum
import hashlib
import json
from pathlib import Path

from app.modules.optimization.domain.packing import _empty_layout
from app.modules.optimization.domain.problem import MaterialSource, OptimizationResult, Placement
from app.modules.optimization.domain.rotation import RasterCache, oriented_geometry

ROOT = Path(__file__).resolve().parents[1]


def jsonable(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [jsonable(v) for v in value]
    return value


def verify_snapshot():
    manifest = json.loads((ROOT / "snapshot-manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        actual = hashlib.sha256((ROOT / entry["target"]).read_bytes()).hexdigest()
        if actual != entry["sha256"]:
            raise ValueError(f"Snapshot alterado: {entry['target']}")
    return manifest


def audit(result, processed=None):
    """Reproducir el prefijo intentado, incluyendo NO_FIT y prioridad por etapa."""
    problem = result.problem
    config, cache = problem.config, RasterCache()
    units = problem.units
    processed = len(units) if processed is None else processed
    if not 0 <= processed <= len(units):
        raise ValueError("Prefijo procesado inválido.")
    layouts = {}
    placements = {p.piece.identity: p for p in result.placements}
    checked = priority_checks = no_fit_checks = 0
    for unit in units[:processed]:
        group = next(g for g in problem.groups if g.key == unit.material_key)
        placement = placements.get(unit.identity)

        def feasible(stock):
            layout = layouts.get(stock.identity)
            if layout is None:
                layout = _empty_layout(cache.material(stock, config.resolution_mm), config)
            return any(layout.first_position(o.orientation.mask) is not None
                       for o in cache.iter_orientations(unit, config.resolution_mm, config.angular_step_deg))

        if placement is None:
            no_fit_checks += 1
            if any(feasible(s) for s in group.stock_candidates):
                raise ValueError("NO_FIT sin demostrar: existe colocación factible.")
            continue
        if placement.stock.source is MaterialSource.SHEET:
            priority_checks += 1
            if any(feasible(s) for s in group.stock_candidates if s.source is MaterialSource.REMNANT):
                raise ValueError("Plancha elegida mientras existe retazo factible.")
        angle = placement.rotation_deg
        if angle % config.angular_step_deg != 0 or not 0 <= angle < 360:
            raise ValueError("Ángulo fuera de la discretización común.")
        if oriented_geometry(unit.geometry, angle) != placement.geometry:
            raise ValueError("Contorno no corresponde a la rotación declarada.")
        layout = layouts.get(placement.stock.identity)
        if layout is None:
            layout = _empty_layout(cache.material(placement.stock, config.resolution_mm), config)
        # El contorno ya está orientado. Nunca volver a aplicar angle.
        from dataclasses import replace
        mask = cache.orientations(replace(unit, geometry=placement.geometry), config.resolution_mm,
                                  Decimal(360))[0].orientation.mask
        row = placement.y_mm / config.resolution_mm
        column = placement.x_mm / config.resolution_mm
        if row != int(row) or column != int(column):
            raise ValueError("Posición no alineada a rejilla.")
        if not layout.check(mask, int(row), int(column)).is_valid:
            raise ValueError("Falla margen, separación, límites o superposición.")
        layouts[placement.stock.identity] = layout.place(mask, int(row), int(column))
        checked += 1
    if checked != len(result.placements):
        raise ValueError("Placement fuera del prefijo procesado.")
    return dict(valid=True, placements_checked=checked, sheet_priority_checks=priority_checks,
                no_fit_checks=no_fit_checks, processed_units=processed,
                pending_units=len(units) - processed)


def placement_rows(result):
    return [dict(piece_id=p.piece.piece_id, unit_index=p.piece.unit_index,
                 source=p.stock.source.value, material_id=p.stock.material_id,
                 stock_unit_index=p.stock.physical_unit_index, x_mm=str(p.x_mm), y_mm=str(p.y_mm),
                 rotation_deg=str(p.rotation_deg), geometry=jsonable(p.geometry)) for p in result.placements]


def rebuild_result(problem, rows):
    pieces = {u.identity: u for u in problem.units}
    stocks = {s.identity: s for g in problem.groups for s in g.stock_candidates}
    return OptimizationResult(problem=problem, placements=tuple(Placement(
        piece=pieces[(p["piece_id"], p["unit_index"])],
        stock=stocks[(MaterialSource(p["source"]), p["material_id"], p["stock_unit_index"])],
        x_mm=Decimal(p["x_mm"]), y_mm=Decimal(p["y_mm"]), rotation_deg=Decimal(p["rotation_deg"]),
        geometry=p["geometry"]) for p in rows))


def stable_signature(record):
    data = {k: record.get(k) for k in ("method", "case_id", "status", "processed_units",
             "placements", "metrics", "trace", "stop_reason")}
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
