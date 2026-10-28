"""HU-017: compare pure FF on a selected backend source tree.

Usage: python experiments/raster/scripts/hu017_preparation_benchmark.py /path/to/backend [--visual]
Uses synthetic 1 mm / 5 degree inputs, tracemalloc and the engine's charged cache
bytes; no database, HTTP, inventory writes or pass/fail performance threshold.
--visual adds the real bounded projection/store; frame sizes count only the
seven new visual fact types, not the eight legacy milestones or HTTP overhead.
"""
import sys
if len(sys.argv) not in (2, 3) or len(sys.argv) == 3 and sys.argv[2] != '--visual':
    raise SystemExit('Pass the backend source directory and optional --visual.')
visual_enabled = len(sys.argv) == 3
sys.path.insert(0, sys.argv[1])
import gc
import hashlib
import json
import time
import tracemalloc
from decimal import Decimal as D
from datetime import datetime, timezone
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.problem import (
    MaterialGroup, MaterialSource, OptimizationConfig, OptimizationProblem, PieceUnit, StockCandidate,
)
from app.modules.optimization.domain.rotation import RasterCache

if visual_enabled:
    from app.modules.optimization.infrastructure.visual_store import InMemoryVisualStore
    from app.modules.optimization.presentation.visual_serialization import VisualProjection, describe_record
    from app.modules.optimization.presentation.visual_schemas import EVENT_TYPES, VisualMaskV2
    from app.modules.optimization.application.visual import mask_window

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
    visual_counts = dict(visual_events=0, max_visual_frame_bytes=0, visual_frame_bytes=0)
    observation_seconds = [0.0]
    if visual_enabled:
        session = InMemoryVisualStore().reserve()
        session.bind(1, D(1))
        def emit(kind, data):
            frame = EVENT_TYPES[kind](schema_version=2, id_optimizacion=1,
                sequence=visual_counts['visual_events'] + 1, occurred_at=datetime.now(timezone.utc),
                event=kind, data=data).model_dump_json().encode() + b'\n'
            visual_counts['visual_events'] += 1
            visual_counts['visual_frame_bytes'] += len(frame)
            visual_counts['max_visual_frame_bytes'] = max(visual_counts['max_visual_frame_bytes'], len(frame))
        projection = VisualProjection(session, emit)
        def observe(fact):
            before = time.perf_counter()
            projection(fact)
            observation_seconds[0] += time.perf_counter() - before
    gc.collect()
    tracemalloc.start()
    started = time.perf_counter()
    result = FirstFitOptimizer().optimize(problem, **({'on_visual': observe} if visual_enabled else {}))
    duration = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    if visual_enabled:
        windows = []
        for record in session.records.values():
            window = mask_window(record)
            spans = window.pop('spans_by_row')
            body = VisualMaskV2(**describe_record(session, record), schema_version=2,
                geometria_original=dict(record.owner.geometry), geometria=dict(record.orientation.geometry),
                window=window, spans_by_row=spans)
            windows.append(len(body.model_dump_json().encode()))
        visual_counts.update(visual_refs=len(session.records), visual_charged_bytes=session.charged_bytes,
            max_window_bytes=max(windows, default=0), projection_ms=round(observation_seconds[0] * 1000, 2))
    print(json.dumps(dict(case=name, placed=result.placed_units, total=result.total_units,
        visual_enabled=visual_enabled, peak_python_bytes=peak, elapsed_ms=round(duration * 1000, 2), **counts,
        **(visual_counts if visual_enabled else {}),
        functional_sha256=hashlib.sha256(repr(result).encode()).hexdigest())), flush=True)
RasterCache._raster = original
