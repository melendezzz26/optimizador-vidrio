"""Run from repository root: .venv/Scripts/python experiments/raster/scripts/sp003_angles.py."""
import json
import platform
import sys
from dataclasses import asdict
from decimal import Decimal as D
from pathlib import Path
from statistics import median
from time import perf_counter
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
from app.modules.optimization.domain import packing
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.domain.placement import SheetLayout
from app.modules.optimization.domain.problem import (
    MaterialGroup, MaterialSource, OptimizationConfig, OptimizationProblem, PieceUnit, StockCandidate,
)
from app.modules.optimization.domain.rotation import RasterCache


def instance(step):
    # A diagonal rectangle plus ordinary rectangular pieces; same physical input.
    geometries = [
        ({"type": "POLIGONO_CONVEXO", "vertices_mm": [[0, 2], [2, 0], [8, 6], [6, 8]]}, 24),
        ({"type": "RECTANGULO", "width_mm": 4, "height_mm": 2}, 8),
        ({"type": "RECTANGULO", "width_mm": 3, "height_mm": 2}, 6),
    ]
    units = tuple(PieceUnit(order_id=1, piece_id=i, unit_index=1, glass_type_id=1,
                           thickness_mm=6, geometry=g, area_mm2=a)
                  for i, (g, a) in enumerate(geometries, 1))
    stocks = tuple(StockCandidate(source=source, material_id=i, physical_unit_index=1,
                                 glass_type_id=1, thickness_mm=6, area_mm2=w*h,
                                 geometry={"type": "RECTANGULO", "width_mm": w, "height_mm": h})
                   for i, source, w, h in [(1, MaterialSource.REMNANT, 10, 4),
                                          (2, MaterialSource.SHEET, 12, 12)])
    return OptimizationProblem(order_ids=(1,), config=OptimizationConfig(
        resolution_mm=1, margin_mm=0, separation_mm=0, angular_step_deg=step),
        groups=(MaterialGroup(glass_type_id=1, thickness_mm=6, units=units, stock_candidates=stocks),))


def measure(step):
    counts = dict(orientations_prepared=0, orientation_position_searches=0, feasible_candidates=0)
    original_orientations = RasterCache.orientations
    original_position = SheetLayout.first_position
    original_candidates = packing._feasible_candidates

    def orientations(self, *args):
        result = original_orientations(self, *args)
        counts["orientations_prepared"] += len(result)
        return result

    def position(self, *args):
        counts["orientation_position_searches"] += 1
        return original_position(self, *args)

    def candidates(*args):
        for candidate in original_candidates(*args):
            counts["feasible_candidates"] += 1
            yield candidate

    problem = instance(step)
    with patch.object(RasterCache, "orientations", orientations), patch.object(
        SheetLayout, "first_position", position
    ), patch.object(packing, "_feasible_candidates", candidates):
        result = FirstFitOptimizer().optimize(problem)
    times = []
    for _ in range(5):
        start = perf_counter()
        repeated = FirstFitOptimizer().optimize(problem)
        times.append(perf_counter() - start)
        assert repeated == result
    measured, _ = calculate_metrics(result, D(1), D(1))
    return dict(angle_step=step, **counts, placed=result.placed_units,
                metrics=asdict(measured.metrics), seconds=times, median_seconds=median(times),
                placements=[dict(piece=p.piece.identity, stock=p.stock.identity,
                                 x=p.x_mm, y=p.y_mm, angle=p.rotation_deg) for p in result.placements])


if __name__ == "__main__":
    output = ROOT / "docs/evidence/sprint-02/SP-003/results.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(dict(python=platform.python_version(), platform=platform.platform(),
        algorithm="FF", resolution_mm=1, margin_mm=0, separation_mm=0,
        minimum_residual_mm=[1, 1], memory="not measured: no existing instrumentation",
        runs=[measure(step) for step in (90, 45, 15, 5)]), default=str, indent=2) + "\n", encoding="utf-8")
    print(output)
