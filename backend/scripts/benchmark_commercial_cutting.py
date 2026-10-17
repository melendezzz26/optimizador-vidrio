"""Reproducible CPU/heap benchmark, no DB or environment credentials.

From backend: python -m scripts.benchmark_commercial_cutting
Time runs without tracemalloc overhead; a separate identical run measures heap.
Windows peak process working set is reported too (includes interpreter/imports).
"""
import ctypes
import gc
import json
import sys
import tracemalloc
from time import perf_counter
from decimal import Decimal as D

from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.domain.problem import (
    MaterialSource, MaterialGroup, OptimizationProblem, OptimizationConfig, PieceUnit, StockCandidate,
)
from app.modules.optimization.domain.rotation import RasterCache


def commercial_problem(width, height):
    return OptimizationProblem(order_ids=(64,), config=OptimizationConfig(
        resolution_mm=1, margin_mm=0, separation_mm=0, angular_step_deg=90), groups=(MaterialGroup(
        glass_type_id=2, thickness_mm=6,
        units=tuple(PieceUnit(order_id=64, piece_id=64, unit_index=i, glass_type_id=2,
            thickness_mm=6, area_mm2=480000, geometry=dict(type='RECTANGULO', width_mm=600, height_mm=800))
            for i in range(1, 9)),
        stock_candidates=(StockCandidate(source=MaterialSource.SHEET, material_id=64, physical_unit_index=1,
            glass_type_id=2, thickness_mm=6, area_mm2=width * height,
            geometry=dict(type='RECTANGULO', width_mm=width, height_mm=height)),)),))


def calculate(problem):
    result = FirstFitOptimizer().optimize(problem)
    return calculate_metrics(result, D(10), D(10))


def process_peak():
    if sys.platform != 'win32':
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    class Counters(ctypes.Structure):
        _fields_ = [('cb', ctypes.c_ulong), ('faults', ctypes.c_ulong)] + [
            (name, ctypes.c_size_t) for name in ('peak', 'working', 'peak_paged', 'paged', 'peak_nonpaged', 'nonpaged', 'pagefile', 'peak_pagefile')]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(-1), ctypes.byref(counters), counters.cb)
    return counters.peak


def main():
    for width, height in ((2140, 3300), (4000, 4000)):
        problem = commercial_problem(width, height)
        begin = perf_counter()
        cache = RasterCache()
        mask = cache.material(problem.groups[0].stock_candidates[0], D(1))
        mask_ms = (perf_counter() - begin) * 1000
        mask_bytes = sys.getsizeof(mask.rows) + sum(sys.getsizeof(row) for row in mask.rows)
        del mask, cache
        begin = perf_counter()
        result, residuals = calculate(problem)
        time_ms = (perf_counter() - begin) * 1000
        gc.collect()
        tracemalloc.start()
        for _ in range(3):
            measured, _ = calculate(problem)
            assert measured == result
        del measured
        gc.collect()
        retained, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        assert result.complete and peak < 64 * 1024 * 1024 and retained < 1024 * 1024
        print(json.dumps(dict(width=width, height=height, resolution_mm=1, cells=width * height,
            mask_bytes=mask_bytes, mask_ms=round(mask_ms, 3), calculation_ms=round(time_ms, 3),
            peak_python_bytes=peak, retained_python_bytes_after_3_runs=retained,
            peak_process_bytes=process_peak(), placed=result.placed_units,
            positions=[(str(p.x_mm), str(p.y_mm), str(p.rotation_deg)) for p in result.placements],
            residuals=[dict(x=str(r.x_mm), y=str(r.y_mm), width=str(r.width_mm), height=str(r.height_mm)) for r in residuals],
            utilization_pct=str(result.metrics.utilization_pct), waste_mm2=str(result.metrics.waste_mm2),
            recovered_mm2=str(result.metrics.recoverable_remnant_mm2))))


if __name__ == '__main__':
    main()
