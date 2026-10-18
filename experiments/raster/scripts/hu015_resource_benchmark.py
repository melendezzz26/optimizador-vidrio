"""Desde raíz: backend/venv/Scripts/python.exe experiments/raster/scripts/hu015_resource_benchmark.py.

Sin BD. Cada combinación corre en proceso propio con timeout; tiempos sin
tracemalloc y memoria en una pasada separada. JSON productivo Pydantic compacto.
"""
import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))

from app.modules.optimization.application.ports import RasterizedPiece  # noqa: E402
from app.modules.optimization.application.resource_policy import estimate_grid, geometry_bounds  # noqa: E402
from app.modules.optimization.domain.rasterizer import rasterize_geometry  # noqa: E402
from app.modules.optimization.presentation.serialization import raster_response  # noqa: E402
from app.modules.orders.application.persisted_pieces import validate_persisted_piece  # noqa: E402

CASES = ROOT / "experiments/raster/cases/hu015-resources.json"
OUTPUT = ROOT / "experiments/raster/results/hu015/benchmark.json"
REPETITIONS = 5


def encode(geometry, mask, quantity=5):
    piece = dict(id_pedido=10, id_pieza=25, tipo_forma=geometry["type"],
                 geometria=geometry, id_tipo_vidrio=7, espesor_mm="6.00", cantidad=quantity)
    start = time.perf_counter()
    response = raster_response(RasterizedPiece(piece, mask))
    dto_ms = (time.perf_counter() - start) * 1000
    start = time.perf_counter()
    payload = response.model_dump_json().encode("utf-8")
    return dto_ms, (time.perf_counter() - start) * 1000, len(payload)


def measure(case, resolution):
    geometry = case["geometry"]
    rows, columns = estimate_grid(geometry, resolution)
    # Guardas del runner, no límites del producto: no ampliar sin evaluar RAM.
    if rows * columns > 5_000_000 or max(rows, columns) > 5_000:
        return dict(case=case["name"], resolution_mm=resolution, skipped="runner safety envelope")
    mask = rasterize_geometry(geometry, resolution)
    encode(geometry, mask)  # Warmup.
    samples = []
    piece = dict(id_pedido=10, id_pieza=25, id_tipo_vidrio=7, cantidad=5, espesor_mm=6,
                 tipo_forma=geometry["type"], geometria=geometry)
    for _ in range(REPETITIONS):
        start = time.perf_counter()
        validate_persisted_piece(piece)
        validation_ms = (time.perf_counter() - start) * 1000
        start = time.perf_counter()
        mask = rasterize_geometry(geometry, resolution)
        raster_ms = (time.perf_counter() - start) * 1000
        dto_ms, json_ms, size = encode(geometry, mask)
        samples.append(dict(validation_ms=validation_ms, raster_ms=raster_ms, dto_ms=dto_ms, json_ms=json_ms))
    tracemalloc.start()
    validate_persisted_piece(piece)
    memory_mask = rasterize_geometry(geometry, resolution)
    encode(geometry, memory_mask)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    quantity_one_bytes = encode(geometry, mask, quantity=1)[2]
    return dict(case=case["name"], shape=geometry["type"], dimensions_mm=geometry_bounds(geometry),
                vertices=len(geometry.get("vertices_mm", [])), resolution_mm=resolution,
                row_count=mask.row_count, columns=mask.columns, total_cells=rows * columns,
                occupied_cells=mask.occupied_cells, quantity=5, json_bytes=size,
                quantity_one_json_bytes=quantity_one_bytes,
                peak_python_bytes=peak, samples=samples,
                median_ms={key: statistics.median(s[key] for s in samples) for key in samples[0]},
                max_ms={key: max(s[key] for s in samples) for key in samples[0]})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", nargs=2, type=int)
    args = parser.parse_args()
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    # Coste adicional de convexidad/tamaño de geometría, sin dimensiones absurdas.
    for count in (64, 128, 256):
        cases.append(dict(name=f"polygon-{count}", geometry=dict(type="POLIGONO_CONVEXO",
            vertices_mm=[[500 + 500 * math.cos(2 * math.pi * i / count),
                          500 + 500 * math.sin(2 * math.pi * i / count)] for i in range(count)])))
    if args.worker:
        index, resolution = args.worker
        print(json.dumps(measure(cases[index], resolution), allow_nan=False))
        return
    results = []
    for index, case in enumerate(cases):
        for resolution in (20, 10, 5, 2, 1):
            run = subprocess.run([sys.executable, __file__, "--worker", str(index), str(resolution)],
                                 capture_output=True, text=True, timeout=60)
            if run.returncode:
                raise RuntimeError(run.stderr)
            result = json.loads(run.stdout)
            results.append(result)
            print(f"{case['name']:14} {resolution:2} mm {result.get('total_cells', 'SKIP')} cells "
                  f"{result.get('median_ms', {})}", flush=True)
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    metadata = dict(python=sys.version, platform=platform.platform(), processor=platform.processor(),
                    logical_cpus=os.cpu_count(), ram="N/D: no hardware RAM query in this runner",
                    dependencies={name: importlib.metadata.version(name) for name in ("pydantic", "fastapi", "SQLAlchemy")},
                    executed_at_utc=datetime.now(timezone.utc).isoformat(),
                    base_commit=git("rev-parse", "HEAD"), dirty=git("status", "--short"),
                    cases_sha256=hashlib.sha256(CASES.read_bytes()).hexdigest(), repetitions=REPETITIONS,
                    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    serializer_sha256=hashlib.sha256((ROOT / "backend/app/modules/optimization/presentation/serialization.py").read_bytes()).hexdigest(),
                    schemas_sha256=hashlib.sha256((ROOT / "backend/app/modules/optimization/presentation/schemas.py").read_bytes()).hexdigest(),
                    memory="tracemalloc peak Python allocations; separate pass, not RSS",
                    serialization="raster_response + Pydantic model_dump_json UTF-8; same as API")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(dict(metadata=metadata, results=results), indent=2), encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
