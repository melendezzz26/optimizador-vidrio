"""Reproducible native six-method benchmark; synthetic data, no database or stock writes.

From backend: python -m scripts.benchmark_academic_800
Each measurement uses a fresh process capped at 256 MiB / 120 calculation s.
The benchmark exercises real adapters and validates the resulting raster layouts;
it is not a deployed HTTP/browser/persistence measurement.
"""
import argparse
from decimal import Decimal as D
import json
import math
import os
import resource
import subprocess
import sys
import time

os.environ['PYTHON_DOTENV_DISABLED'] = '1'

from app.modules.optimization.application.comparison_catalog import METHODS_V2
from app.modules.optimization.application.engine_execution import EngineExecutionAdapter, ExecutionScope
from app.modules.optimization.application.errors import TimeBudgetExceeded
from app.modules.optimization.infrastructure.comparison_snapshot import problem_fingerprint
from app.modules.optimization.domain.preparation import prepare_group_units
from app.modules.optimization.domain.problem import (
    MaterialGroup, MaterialSource, OptimizationConfig, OptimizationProblem, PieceUnit, StockCandidate,
)


def case_problem(count):
    if count not in (600, 700, 800):
        raise ValueError('Use 600, 700 or 800 physical units')
    shapes = [({'type': 'RECTANGULO', 'width_mm': 120, 'height_mm': 80}, D(9600)),
              ({'type': 'CIRCUNFERENCIA', 'radius_mm': 40}, D(str(math.pi*40**2)).quantize(D('.001'))),
              ({'type': 'POLIGONO_CONVEXO', 'vertices_mm': ((0,0),(80,0),(100,60),(20,60))}, D(4800))]
    groups = []
    for material in (1, 2):
        units = tuple(PieceUnit(order_id=980000+count, piece_id=material*100+i%3,
            unit_index=i//3+1, glass_type_id=material, thickness_mm=D(6),
            geometry=shapes[i%3][0], area_mm2=shapes[i%3][1]) for i in range(count//2))
        stocks = tuple(StockCandidate(source=MaterialSource.SHEET, material_id=material,
            physical_unit_index=i+1, glass_type_id=material, thickness_mm=D(6),
            geometry={'type':'RECTANGULO','width_mm':2440,'height_mm':3300}, area_mm2=D(8052000))
            for i in range(2))
        groups.append(MaterialGroup(glass_type_id=material, thickness_mm=D(6),
                                   units=prepare_group_units(units), stock_candidates=stocks))
    return OptimizationProblem(order_ids=(980000+count,), groups=tuple(groups),
        config=OptimizationConfig(resolution_mm=1, angular_step_deg=5, margin_mm=3, separation_mm=3))


def measure(count, method):
    resource.setrlimit(resource.RLIMIT_AS, (256*1024*1024, 256*1024*1024))
    p = case_problem(count)
    started = time.monotonic()
    def checkpoint():
        if time.monotonic()-started >= 120:
            raise TimeBudgetExceeded()
    adapted = EngineExecutionAdapter(method).execute(
        ExecutionScope(comparison_id=count, execution_id=METHODS_V2.index(method)+1, method=method),
        p, minimum_width_mm=D(10), minimum_height_mm=D(10), checkpoint=checkpoint)
    elapsed = time.monotonic()-started
    payload, result = adapted.payload, adapted.payload.result
    valid = bool(result and result.metrics is not None and result.problem == p and
                 len({x.piece.identity for x in result.placements}) == result.placed_units and
                 all(x.piece.material_key == x.stock.material_key for x in result.placements))
    # calculate_metrics inside the real adapter replays every placement using
    # SheetLayout.place, which rejects overlaps, separation and boundary errors.
    print(json.dumps(dict(units=count, method=method, input_sha256=problem_fingerprint(p), placed=result.placed_units if result else None,
        processed=adapted.beam_outcome.processed if adapted.beam_outcome else count if result else None,
        complete=bool(result and result.complete), geometry_revalidated=valid,
        wall_s=round(elapsed, 4), reason=payload.diagnostic.termination_reason,
        origin=payload.diagnostic.origin, statistics=dict(payload.diagnostic.statistics),
        sheets=result.metrics.new_sheets_used if result and result.metrics else None,
        utilization=str(result.metrics.utilization_pct) if result and result.metrics else None,
        peak_process_rss_mib=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,3),
        error=adapted.error_type)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--units', type=int, choices=(600,700,800))
    parser.add_argument('--method', choices=METHODS_V2)
    args = parser.parse_args()
    if args.units and args.method:
        measure(args.units, args.method)
    else:
        for count in (args.units,) if args.units else (600,700,800):
            for method in (args.method,) if args.method else METHODS_V2:
                subprocess.run([sys.executable,'-B','-m','scripts.benchmark_academic_800',
                                '--units',str(count),'--method',method],check=True,timeout=140)
