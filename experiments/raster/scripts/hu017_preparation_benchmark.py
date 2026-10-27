"""HU-017 T02: compare pure FF on a selected backend source tree.

Usage: python experiments/raster/scripts/hu017_preparation_benchmark.py /path/to/backend
Uses synthetic 1 mm / 5 degree inputs, tracemalloc and the engine's charged cache
bytes; no database, HTTP, inventory writes or pass/fail performance threshold.
"""
import sys
if len(sys.argv) != 2:
    raise SystemExit('Pass the backend source directory to measure.')
sys.path.insert(0, sys.argv[1])
import gc
import hashlib
import json
import time
import tracemalloc
from decimal import Decimal as D
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.problem import (
    MaterialGroup, MaterialSource, OptimizationConfig, OptimizationProblem, PieceUnit, StockCandidate,
)
from app.modules.optimization.domain.rotation import RasterCache

cases = [
    ('eight-identical', [(400, 300, 8)], (2140, 3300)),
    ('rotation-needed', [(1200, 600, 1)], (800, 1800)),
    ('three-geometries', [(700, 450, 3), (600, 300, 3), (350, 200, 3)], (2140, 3300)),
]
original = RasterCache._raster
for name, shapes, sheet in cases:
    units = tuple(PieceUnit(order_id=1, piece_id=index, unit_index=unit, glass_type_id=1,
        thickness_mm=D(6), area_mm2=D(width * height),
        geometry=dict(type='RECTANGULO', width_mm=width, height_mm=height))
        for index, (width, height, count) in enumerate(shapes, 1) for unit in range(1, count + 1))
    stock = StockCandidate(source=MaterialSource.SHEET, material_id=1, physical_unit_index=1,
        glass_type_id=1, thickness_mm=D(6), area_mm2=D(sheet[0] * sheet[1]),
        geometry=dict(type='RECTANGULO', width_mm=sheet[0], height_mm=sheet[1]))
    problem = OptimizationProblem(order_ids=(1,),
        config=OptimizationConfig(resolution_mm=D(1), margin_mm=D(0), separation_mm=D(0), angular_step_deg=D(5)),
        groups=(MaterialGroup(glass_type_id=1, thickness_mm=D(6), units=units, stock_candidates=(stock,)),))
    counts = dict(piece_masks=0, material_masks=0, charged_peak_bytes=0)
    def raster(self, geometry, resolution, *, material=False):
        mask = original(self, geometry, resolution, material=material)
        counts['material_masks' if material else 'piece_masks'] += 1
        counts['charged_peak_bytes'] = max(counts['charged_peak_bytes'], self._cache_bytes)
        return mask
    RasterCache._raster = raster
    gc.collect()
    tracemalloc.start()
    started = time.perf_counter()
    result = FirstFitOptimizer().optimize(problem)
    duration = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(json.dumps(dict(case=name, placed=result.placed_units, total=result.total_units,
        peak_python_bytes=peak, elapsed_ms=round(duration * 1000, 2), **counts,
        functional_sha256=hashlib.sha256(repr(result).encode()).hexdigest())), flush=True)
RasterCache._raster = original
