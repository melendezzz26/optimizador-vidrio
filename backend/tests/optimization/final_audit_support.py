"""Audit oracles only. Never used by application code or as a packing fallback.

Reuse canonical rasterization, then check raw bits independently of SheetLayout.
The residual oracle exhausts compressed row intervals instead of using the
production histogram implementation. Inputs are bounded frozen fixtures.
"""
from decimal import Decimal as D, ROUND_HALF_UP
from itertools import groupby
import hashlib
import importlib.util
import json
import math
from pathlib import Path

from app.modules.optimization.domain import packing
from app.modules.optimization.domain.problem import MaterialSource
from app.modules.optimization.domain.rotation import RasterCache
from app.modules.optimization.domain.run_geometry import prepare_run_geometry
from app.modules.optimization.infrastructure.comparison_snapshot import canonical_json
from app.modules.optimization.infrastructure.run_snapshot import json_value

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('final_audit_cases', ROOT / 'experiments/optimization/final_audit_cases.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)


def nominal_area(geometry):
    if geometry['type'] == 'RECTANGULO':
        value = D(str(geometry['width_mm'])) * D(str(geometry['height_mm']))
    elif geometry['type'] == 'CIRCUNFERENCIA':
        value = D(str(math.pi)) * D(str(geometry['radius_mm'])) ** 2
    else:
        points = [(D(str(x)),D(str(y))) for x,y in geometry['vertices_mm']]
        value = abs(sum(x * points[(i+1)%len(points)][1] - y * points[(i+1)%len(points)][0]
            for i,(x,y) in enumerate(points))) / 2
    return value.quantize(D('.01'),rounding=ROUND_HALF_UP)


def verify_rigid_orientation(placement):
    original, observed, angle = placement.piece.geometry, placement.geometry, float(placement.rotation_deg)
    if original['type'] == 'CIRCUNFERENCIA':
        assert angle == 0 and observed == original
        return
    if original['type'] == 'RECTANGULO':
        w,h = float(original['width_mm']),float(original['height_mm'])
        points = [(0,0),(w,0),(w,h),(0,h)]
    else: points = original['vertices_mm']
    theta = math.radians(angle)
    rotated = [(float(x)*math.cos(theta)-float(y)*math.sin(theta),
                float(x)*math.sin(theta)+float(y)*math.cos(theta)) for x,y in points]
    lowx,lowy = min(x for x,y in rotated),min(y for x,y in rotated)
    expected = [(x-lowx,y-lowy) for x,y in rotated]
    if observed['type'] == 'RECTANGULO':
        assert math.isclose(max(x for x,y in expected),float(observed['width_mm']),abs_tol=2e-6)
        assert math.isclose(max(y for x,y in expected),float(observed['height_mm']),abs_tol=2e-6)
    else:
        assert len(expected) == len(observed['vertices_mm'])
        assert all(math.isclose(a,float(b),abs_tol=2e-6) for p,q in zip(expected,observed['vertices_mm']) for a,b in zip(p,q))


def mask_record(mask):
    runs = []
    first = 0
    for bits, rows in groupby(mask.rows):
        count = sum(1 for _ in rows)
        runs.append(dict(first_row=first, rows=count, bits_hex=hex(bits)))
        first += count
    return dict(columns=mask.columns, rows=mask.row_count, resolution_mm=mask.resolution_mm,
        occupied_cells=mask.occupied_cells, row_runs=runs,
        sha256=hashlib.sha256(canonical_json([mask.columns, mask.rows]).encode()).hexdigest())


def largest_rectangle_oracle(rows, columns):
    compressed, first = [], 0
    for bits, same in groupby(rows):
        count = sum(1 for _ in same)
        compressed.append((first, count, bits)); first += count
    best = None
    # A maximal rectangle includes whole consecutive equal-row runs.
    for i, (top, _, _) in enumerate(compressed):
        common, height = (1 << columns) - 1, 0
        for _, count, bits in compressed[i:]:
            common &= bits; height += count
            column = 0
            while column < columns:
                if not (common >> column) & 1:
                    column += 1; continue
                start = column
                while column < columns and (common >> column) & 1:
                    column += 1
                width = column - start
                key = (-width * height, top, start, -width, -height)
                if best is None or key < best[0]:
                    best = key, (top, start, width, height)
    return None if best is None else best[1]


def verify_geometry_and_metrics(result, residuals, minimums):
    cfg, cache = result.problem.config, RasterCache()
    assert all(nominal_area(u.geometry) == u.area_mm2 for u in result.problem.units)
    assert all(nominal_area(s.geometry) == s.area_mm2 for s in result.materials_used)
    margin = int((cfg.margin_mm / cfg.resolution_mm).to_integral_value(rounding='ROUND_CEILING'))
    separation = int((cfg.separation_mm / cfg.resolution_mm).to_integral_value(rounding='ROUND_CEILING'))
    expected_residuals, masks = [], []
    for source in result.materials_used:
        material = cache.material(source, cfg.resolution_mm)
        full, occupied = (1 << material.columns) - 1, [0] * material.row_count
        usable = []
        for row in range(material.row_count):
            bits = full
            for dy in range(-margin, margin + 1):
                neighbor = material.rows[row + dy] if 0 <= row + dy < material.row_count else 0
                for dx in range(-margin, margin + 1):
                    bits &= (neighbor << dx if dx >= 0 else neighbor >> -dx)
            usable.append(bits & full)
        blocked = [0] * material.row_count
        for placement in [p for p in result.placements if p.stock.identity == source.identity]:
            assert placement.rotation_deg % 5 == 0
            verify_rigid_orientation(placement)
            # Already-oriented contour: rasterize exactly once, no second rotation.
            from dataclasses import replace
            oriented = replace(placement.piece, geometry=placement.geometry)
            mask = cache.orientations(oriented, cfg.resolution_mm, D(360))[0].orientation.mask
            row, column = placement.y_mm / cfg.resolution_mm, placement.x_mm / cfg.resolution_mm
            assert row == int(row) and column == int(column)
            row, column = int(row), int(column)
            assert row >= 0 and column >= 0
            assert row + mask.row_count <= len(usable) and column + mask.columns <= material.columns
            for offset, bits in enumerate(mask.rows):
                translated = bits << column
                assert translated & ~usable[row + offset] == 0, 'outside material/margin'
                assert translated & blocked[row + offset] == 0, 'overlap/separation'
                occupied[row + offset] |= translated
            # Commit dilation only after checking the whole mask; rows of the
            # same piece do not have to be separated from one another.
            for offset, bits in enumerate(mask.rows):
                translated = bits << column
                for dy in range(-separation, separation + 1):
                    if not 0 <= row + offset + dy < len(blocked): continue
                    for dx in range(-separation, separation + 1):
                        blocked[row + offset + dy] |= (translated << dx if dx >= 0 else translated >> -dx) & full
            masks.append(dict(piece=placement.piece.identity, stock=source.identity, mask=mask_record(mask)))
        rectangle = largest_rectangle_oracle([u & ~b for u, b in zip(usable, blocked)], material.columns)
        if rectangle:
            row, column, width, height = rectangle
            if width * cfg.resolution_mm >= minimums[0] and height * cfg.resolution_mm >= minimums[1]:
                expected_residuals.append((source.identity, column * cfg.resolution_mm, row * cfg.resolution_mm,
                    width * cfg.resolution_mm, height * cfg.resolution_mm))
    observed = [((MaterialSource(r.material_source), r.material_id, r.stock_unit_index), r.x_mm, r.y_mm, r.width_mm, r.height_mm) for r in residuals]
    assert observed == expected_residuals
    material_area = sum((s.area_mm2 for s in result.materials_used), D(0))
    placed_area = sum((p.piece.area_mm2 for p in result.placements), D(0))
    recovered = sum((r[3] * r[4] for r in expected_residuals), D(0))
    metrics = result.metrics
    if not result.placements:
        assert metrics is None
    else:
        assert metrics.material_area_mm2 == material_area
        assert metrics.placed_piece_area_mm2 == placed_area
        assert metrics.recoverable_remnant_mm2 == recovered
        assert metrics.waste_mm2 == material_area - placed_area - recovered >= 0
        assert metrics.utilization_pct == (placed_area / material_area * 100).quantize(D('.001'), rounding=ROUND_HALF_UP)
        assert metrics.new_sheets_used == sum(s.source is MaterialSource.SHEET for s in result.materials_used)
    assert len({p.piece.identity for p in result.placements}) == len(result.placements)
    assert result.placed_units + len(result.unplaced_units) == result.total_units
    return masks


def trace_policy(result):
    prepared = prepare_run_geometry(result.problem)
    layouts, decisions = {}, []
    actual = {p.piece.identity: p for p in result.placements}
    for group in result.problem.groups:
        for unit in group.units:
            candidates, tier = [], None
            for source in (MaterialSource.REMNANT, MaterialSource.SHEET):
                candidates = list(packing._feasible_candidates(group, source, prepared.orientations(unit), prepared,
                    layouts, result.problem.config, lambda: None))
                if candidates:
                    tier = source.value; break
            def key(c):
                score = c.remaining_free_cells_after_placement
                return ((-score if result.method == 'WF' else score), c.stock_rank, c.orientation_rank, c.row, c.column)
            def tie(c):
                return c.stock_rank, c.orientation_rank, c.row, c.column
            if not candidates:
                winner = None
            elif result.method == 'FF':
                winner = candidates[0]
            elif result.method == 'WF':
                # SPEC-TA-019 v2: best source already in use; otherwise lowest-rank unused one.
                in_use = [c for c in candidates if any(c.layout.occupied)]
                winner = min(in_use, key=key) if in_use else min(candidates, key=tie)
            else:
                winner = min(candidates, key=key)
            placement = actual.get(unit.identity)
            assert (winner is None) == (placement is None)
            if winner:
                assert placement.stock == winner.stock
                assert placement.x_mm == winner.column * result.problem.config.resolution_mm
                assert placement.y_mm == winner.row * result.problem.config.resolution_mm
                assert placement.rotation_deg == winner.orientation.rotation_deg
                assert placement.geometry == winner.orientation.geometry
                layouts[winner.stock.identity] = winner.layout_after
            decisions.append(dict(piece=unit.identity, tier=tier, candidates=[dict(source=c.stock.identity,
                stock_rank=c.stock_rank, orientation_rank=c.orientation_rank, row=c.row, column=c.column,
                score=c.remaining_free_cells_after_placement) for c in candidates],
                chosen=winner.stock.identity if winner else None))
    return decisions


def normalized_pattern(result):
    return json_value(dict(placements=result.placements, unplaced=result.unplaced_units, metrics=result.metrics))
