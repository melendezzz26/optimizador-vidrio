"""Reproducible synthetic FF examples; no database, API, frontend or stock writes.

Run with the backend virtualenv Python. Output is observed, not a fixture claiming
an unexecuted layout. The timer covers only the pure optimizer, excluding I/O.
"""
import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "backend"))

from app.modules.optimization.application.preparation import prepare_persisted_problem
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.problem import MaterialSource, OptimizationConfig, StockCandidate
from app.modules.optimization.domain.rasterizer import rasterize_geometry
from app.modules.optimization.presentation.run_serialization import placement_response


def example(quantity, width, height, sheet_width, sheet_height, resolution, step):
    row = dict(id_pedido=21, id_pieza=101, id_tipo_vidrio=7, espesor_mm=Decimal(6),
               tipo_forma="RECTANGULO", cantidad=quantity,
               geometria=dict(type="RECTANGULO", width_mm=width, height_mm=height),
               area_mm2=Decimal(width * height))
    config = OptimizationConfig(resolution_mm=resolution, angular_step_deg=step,
                                margin_mm=0, separation_mm=0)
    problem = prepare_persisted_problem([21], [row], config)
    candidate = StockCandidate(source=MaterialSource.SHEET, material_id=5, physical_unit_index=1,
                               glass_type_id=7, thickness_mm=6, area_mm2=sheet_width * sheet_height,
                               geometry=dict(type="RECTANGULO", width_mm=sheet_width, height_mm=sheet_height))
    problem = replace(problem, groups=(replace(problem.groups[0], stock_candidates=(candidate,)),))
    events = []
    start = perf_counter()
    result = FirstFitOptimizer().optimize(problem, events.append)
    elapsed_ms = (perf_counter() - start) * 1000
    output = dict(complete=result.complete, total_units=result.total_units, placed_units=result.placed_units,
                  elapsed_domain_ms=round(elapsed_ms, 3),
                  config=dict(resolution_mm=resolution, angular_step_deg=step, margin_mm=0, separation_mm=0),
                  placements=[placement_response(p, config).model_dump(mode="json") for p in result.placements],
                  milestones=[e.kind for e in events])
    return output, result


if __name__ == "__main__":
    small, result = example(3, 2, 2, 4, 4, 1, 90)
    print("SMALL")
    print(json.dumps(small, ensure_ascii=False, indent=2))
    grid = [["." for _ in range(4)] for _ in range(4)]
    for index, placement in enumerate(result.placements):
        mask = rasterize_geometry(dict(placement.geometry), 1)
        for row, bits in enumerate(mask.rows):
            for column in range(mask.columns):
                if bits & (1 << column):
                    grid[int(placement.y_mm) + row][int(placement.x_mm) + column] = chr(65 + index)
    print("ACTUAL RASTER LAYOUT")
    print("\n".join("".join(row) for row in grid))
    representative, _ = example(12, 100, 50, 600, 300, 10, 5)
    print("REPRESENTATIVE: 12 units, 60x30 material grid, 5-degree search")
    print(json.dumps(representative, ensure_ascii=False, indent=2))
