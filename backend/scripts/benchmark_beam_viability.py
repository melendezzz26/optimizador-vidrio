"""Synthetic six-engine matrix, one fresh bounded process per case/method.

python -m scripts.benchmark_beam_viability
No database, dotenv, confirmation or inventory writes. JSON lines go to stdout.
Engine wall time includes metrics; process RSS includes the interpreter/cache.
This isolates native limits, NOT the comparator's 180-second shared deadline.
"""
import os
os.environ["PYTHON_DOTENV_DISABLED"] = "1"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "synthetic-local-benchmark-only-key"

import argparse
from dataclasses import replace
from decimal import Decimal as D
import json
import math
import resource
import subprocess
import sys
import time

from app.modules.optimization.application.comparison_catalog import METHODS_V2
from app.modules.optimization.application.engine_execution import EngineExecutionAdapter, ExecutionScope
from app.modules.optimization.application.errors import TimeBudgetExceeded
from app.modules.optimization.domain.preparation import prepare_group_units
from app.modules.optimization.domain.problem import MaterialSource, MaterialGroup, OptimizationProblem, PieceUnit, StockCandidate
from scripts.benchmark_comparison import problem as original_problem

CASES = ("original-6", "original-18", "original-46", "small-mixed",
         "medium-small", "remnants", "two-thickness")


def case_problem(name):
    if name.startswith("original-"):
        return original_problem(int(name.split("-")[1]))
    original = original_problem(6)
    shapes = [(dict(type="CIRCUNFERENCIA", radius_mm=80), D(str(math.pi * 80**2)).quantize(D(".001")))]
    count, size = 6, 1000
    if name == "small-mixed":
        shapes = [(dict(type="RECTANGULO", width_mm=200, height_mm=300), D(60000)),
                  (dict(type="CIRCUNFERENCIA", radius_mm=100), D(str(math.pi*100**2)).quantize(D(".001"))),
                  (dict(type="POLIGONO_CONVEXO", vertices_mm=((0,0),(125,0),(155,100),(62.5,175),(0,100))), D("19812.5"))]
    elif name == "medium-small":
        count, size = 18, 500
        shapes = [(dict(type="CIRCUNFERENCIA", radius_mm=40), D(str(math.pi*40**2)).quantize(D(".001")))]
    units = tuple(PieceUnit(order_id=900069, piece_id=100+i%len(shapes), unit_index=i//len(shapes)+1,
        glass_type_id=1, thickness_mm=6, geometry=shapes[i%len(shapes)][0], area_mm2=shapes[i%len(shapes)][1]) for i in range(count))
    sheet = StockCandidate(source=MaterialSource.SHEET, material_id=1, physical_unit_index=1,
        glass_type_id=1, thickness_mm=6, geometry=dict(type="RECTANGULO", width_mm=size, height_mm=size), area_mm2=size*size)
    stocks = (sheet,)
    if name == "remnants":
        stocks = tuple(replace(sheet, source=MaterialSource.REMNANT, material_id=10+i,
            geometry=dict(type="RECTANGULO", width_mm=500, height_mm=500), area_mm2=250000) for i in range(4)) + stocks
    group = MaterialGroup(glass_type_id=1, thickness_mm=6, units=prepare_group_units(units), stock_candidates=stocks)
    groups = (group,)
    if name == "two-thickness":
        groups = (replace(group, units=group.units[:3]), replace(group, thickness_mm=D(8),
            units=tuple(replace(u, piece_id=u.piece_id+100, thickness_mm=D(8)) for u in group.units[3:]),
            stock_candidates=(replace(sheet, material_id=2, thickness_mm=D(8)),)))
    return OptimizationProblem(order_ids=original.order_ids, config=original.config, groups=groups)


def measure(case, method):
    maximum = 256 * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (maximum, maximum))
    problem = case_problem(case)
    started = time.monotonic()
    def checkpoint():
        if time.monotonic() - started >= 120:
            raise TimeBudgetExceeded()
    adapted = EngineExecutionAdapter(method).execute(ExecutionScope(comparison_id=1, execution_id=1, method=method),
        problem, minimum_width_mm=D(10), minimum_height_mm=D(10), checkpoint=checkpoint)
    elapsed = time.monotonic() - started
    payload, result = adapted.payload, adapted.payload.result
    print(json.dumps(dict(case=case, method=method, wall_s=round(elapsed, 4),
        placed=result.placed_units if result else None,
        unplaced=len(result.unplaced_units) if result else None,
        sheets=sum(s.source is MaterialSource.SHEET for s in result.materials_used) if result else None,
        remnants=sum(s.source is MaterialSource.REMNANT for s in result.materials_used) if result else None,
        utilization=str(result.metrics.utilization_pct) if result and result.metrics else None,
        waste_mm2=str(result.metrics.waste_mm2) if result and result.metrics else None,
        complete=bool(result and result.complete), origin=payload.diagnostic.origin,
        reason=payload.diagnostic.termination_reason, statistics=dict(payload.diagnostic.statistics),
        peak_process_rss_mib=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024, 3),
        worker_address_limit_bytes=maximum, error=adapted.error_type)), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASES)
    parser.add_argument("--method", choices=METHODS_V2)
    args = parser.parse_args()
    if args.case and args.method:
        measure(args.case, args.method)
    else:
        for case in (args.case,) if args.case else CASES:
            for method in (args.method,) if args.method else METHODS_V2:
                subprocess.run([sys.executable, "-B", "-m", "scripts.benchmark_beam_viability",
                                "--case", case, "--method", method], check=True)
