"""TA-037 T01: benchmark exploratorio de carga del optimizador (solo dominio).

No usa base de datos ni HTTP y no modifica inventario. Construye problemas
sintéticos y mide preparación, snapshot y First Fit tal como existen hoy.
Sirve para justificar los límites propuestos en SPEC-TA-037; no es una prueba
de CI ni un umbral automático.

Uso (desde backend/):
    python ../experiments/raster/scripts/ta037_load_benchmark.py            # escenarios cortos
    python ../experiments/raster/scripts/ta037_load_benchmark.py --largos   # incluye casos de minutos

Los tiempos dependen de la máquina: registrar CPU y versión de Python junto
con los resultados.
"""
import json
import math
import platform
import sys
import threading
import time
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from app.modules.optimization.domain.first_fit import FirstFitOptimizer  # noqa: E402
from app.modules.optimization.domain.preparation import PieceSnapshot, prepare_problem  # noqa: E402
from app.modules.optimization.domain.problem import (  # noqa: E402
    MaterialSource, OptimizationConfig, OptimizationResult, PieceUnit, StockCandidate,
)
from app.modules.optimization.infrastructure.run_snapshot import encode  # noqa: E402

SHEET = {"type": "RECTANGULO", "width_mm": 2440, "height_mm": 1830}


def rectangle(width, height):
    return {"type": "RECTANGULO", "width_mm": width, "height_mm": height}


def polygon(vertices, radius=150):
    return {"type": "POLIGONO_CONVEXO", "vertices_mm": [
        [round(radius + radius * math.cos(2 * math.pi * i / vertices), 3),
         round(radius + radius * math.sin(2 * math.pi * i / vertices), 3)] for i in range(vertices)]}


def problem(units, geometry, sheets, *, resolution="1", margin="0", step="90"):
    config = OptimizationConfig(resolution_mm=Decimal(resolution), margin_mm=Decimal(margin),
                                separation_mm=Decimal(0), angular_step_deg=Decimal(step))
    piece = PieceUnit(order_id=1, piece_id=1, unit_index=1, glass_type_id=1, thickness_mm=Decimal(6),
                      geometry=geometry, area_mm2=Decimal(70000))
    prepared = prepare_problem([1], [PieceSnapshot(quantity=units, unit=piece)], config)
    stock = tuple(StockCandidate(source=MaterialSource.SHEET, material_id=1, physical_unit_index=i + 1,
                                 glass_type_id=1, thickness_mm=Decimal(6), geometry=SHEET,
                                 area_mm2=Decimal(2440 * 1830)) for i in range(sheets))
    return replace(prepared, groups=tuple(replace(g, stock_candidates=stock) for g in prepared.groups))


def timed(label, function):
    started = time.perf_counter()
    try:
        outcome = function()
    except Exception as error:  # Se registra el rechazo interno, no se oculta.
        outcome = f"{type(error).__name__}: {error}"
    elapsed = (time.perf_counter() - started) * 1000
    print(f"{label:62s} {elapsed:10.0f} ms  {outcome}", flush=True)


def first_fit(p):
    result = FirstFitOptimizer().optimize(p)
    return f"colocadas {len(result.placements)}/{len(p.units)}"


def main(long_cases):
    print(f"Python {platform.python_version()} | {platform.machine()} | {platform.processor() or 'cpu n/d'}")
    print("\n# Preparación y snapshot (lineal en unidades)")
    for units in (500, 5000, 20000):
        prepared = {}
        timed(f"prepare_problem {units} unidades",
              lambda u=units: f"{len(prepared.setdefault('p', problem(u, rectangle(300, 200), 0)).units)} unidades")
        timed(f"snapshot JSON {units} unidades", lambda: f"{len(json.dumps(encode(OptimizationResult(problem=prepared['p'], placements=())))):,} bytes")

    print("\n# First Fit, 1 mm, paso 90°, piezas 300x200 (crece más que linealmente)")
    for units, sheets in ((200, 5), (500, 10), (1000, 20)):
        timed(f"FF {units} unidades, {sheets} planchas", lambda u=units, s=sheets: first_fit(problem(u, rectangle(300, 200), s)))
    timed("FF 500 unidades 600x400, 40 planchas", lambda: first_fit(problem(500, rectangle(600, 400), 40)))

    print("\n# Geometría y paso angular")
    timed("FF 50 polígonos de 128 vértices, paso 90°", lambda: first_fit(problem(50, polygon(128), 5)))
    timed("FF 50 polígonos de 128 vértices, paso 15°", lambda: first_fit(problem(50, polygon(128), 5, step="15")))

    print("\n# Stock voluminoso sin encaje (margen 10 mm): costo ~ unidades x planchas")
    timed("FF 20 unidades sin encaje x 100 planchas", lambda: first_fit(
        problem(20, rectangle(2430, 1820), 100, margin="10")))
    if long_cases:
        timed("FF 20 unidades sin encaje x 1000 planchas", lambda: first_fit(
            problem(20, rectangle(2430, 1820), 1000, margin="10")))

    print("\n# Presupuesto interno de layouts (128 MiB): planchas usadas a 1 mm")
    timed("FF 60 unidades 1300x1000, 60 planchas", lambda: first_fit(problem(60, rectangle(1300, 1000), 60)))
    timed("FF 150 unidades 1300x1000, 200 planchas", lambda: first_fit(problem(150, rectangle(1300, 1000), 200)))

    print("\n# Concurrencia en un proceso (GIL)")
    shared = problem(500, rectangle(300, 200), 10)
    timed("FF 500 unidades, una ejecución", lambda: first_fit(shared))
    started = time.perf_counter()
    threads = [threading.Thread(target=timed, args=(f"  ejecución simultánea #{i + 1}", lambda: first_fit(shared)))
               for i in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    print(f"{'3 ejecuciones simultáneas, tiempo total':62s} {(time.perf_counter() - started) * 1000:10.0f} ms")


if __name__ == "__main__":
    main("--largos" in sys.argv)