"""Carga reproducible de los seis motores, sin base de datos y apta para Windows.

Evidencia S2-WF-CARGA (observación del profesor, revisión del 04/11/2026).

Uso, desde backend\\ con el venv activo:
    python -m scripts.benchmark_load_engines 46 100 150 200 300

Para cada tamaño ejecuta en secuencia los métodos de METHODS_V2 (FF, BF, WF, HF,
M5, M6-BS) con EngineExecutionAdapter, cada motor en su propio proceso, como el
comparador secuencial:
- checkpoint de cálculo de 120 s (DEFAULT_COMPARISON_BUDGET.calculation_seconds),
  igual que el worker de producción: al vencer, el motor termina con
  TIME_BUDGET_EXCEEDED en su siguiente checkpoint;
- límite de espacio virtual de 256 MiB (RLIMIT_AS) solo si el módulo `resource`
  existe (Linux). En Windows no existe y el script funciona igual, sin ese límite;
- si un motor no vuelve a un checkpoint, el proceso se detiene a los 30 s + 120 s
  (arranque + cálculo) y se informa SUPERVISOR_TIMEOUT.

No lee .env, no abre la base de datos, no confirma ni consume inventario. Los
tiempos son de reloj (wall time) en la máquina donde se ejecuta, no de CPU.
"""
import argparse
import math
import multiprocessing
import sys
import time
from decimal import Decimal as D

from app.modules.optimization.application.comparison_catalog import METHODS_V2
from app.modules.optimization.application.comparison_limits import DEFAULT_COMPARISON_BUDGET as BUDGET
from app.modules.optimization.application.engine_execution import EngineExecutionAdapter, ExecutionScope
from app.modules.optimization.application.errors import TimeBudgetExceeded
from app.modules.optimization.application.load_budget import DEFAULT_RUN_LOAD_BUDGET
from app.modules.optimization.domain.preparation import prepare_group_units
from app.modules.optimization.domain.problem import (
    MaterialGroup, MaterialSource, OptimizationConfig, OptimizationProblem, PieceUnit, StockCandidate,
)

MINIMUM_SHEETS_PER_MATERIAL = 4
MAX_SHEETS_PER_MATERIAL = DEFAULT_RUN_LOAD_BUDGET.max_stock_units_per_material  # L-07 = 50
RESIDUAL_MINIMUM_MM = D(10)  # Mismo mínimo de retazo que la configuración de benchmark_comparison.py


def sheets_for(units_in_material):
    """Una plancha por unidad del material, acotada a [4, 50] (L-07).

    Así ningún motor queda limitado por falta de stock (ni siquiera uno que abra
    una plancha por pieza) y la entrada sigue siendo admisible para la aplicación.
    """
    return max(MINIMUM_SHEETS_PER_MATERIAL, min(MAX_SHEETS_PER_MATERIAL, units_in_material))


def build_problem(count, resolution=1):
    """Problema sintético COPIADO de scripts/benchmark_comparison.py::problem().

    No se importa ese módulo: al cargarse fija DATABASE_URL/SECRET_KEY e importa
    tests.integration.postgres_support y tests.orders_support (PostgreSQL de
    pruebas), que no funcionan en Windows. Se conservan las mismas formas, medidas,
    identidades y configuración; lo único distinto es la cantidad de planchas por
    material, que aquí escala con sheets_for() en vez de ser 4 fijas.
    """
    if count < 2:
        raise ValueError('The benchmark requires at least two units for its two material groups')
    shapes = [(dict(type='RECTANGULO', width_mm=600, height_mm=800), D(480000)),
              (dict(type='CIRCUNFERENCIA', radius_mm=260), D(str(math.pi * 260**2)).quantize(D('.001'))),
              (dict(type='POLIGONO_CONVEXO', vertices_mm=((0, 0), (500, 0), (620, 400), (250, 700), (0, 400))), D(317000))]
    # Polygon shoelace area: 317000 mm2.
    groups = []
    for glass, n in ((1, count // 2), (2, count - count // 2)):
        units = tuple(PieceUnit(order_id=900069, piece_id=glass * 100 + i % 3, unit_index=i // 3 + 1,
            glass_type_id=glass, thickness_mm=6, geometry=shapes[i % 3][0], area_mm2=shapes[i % 3][1]) for i in range(n))
        stocks = tuple(StockCandidate(source=MaterialSource.SHEET, material_id=glass, physical_unit_index=i + 1,
            glass_type_id=glass, thickness_mm=6, geometry=dict(type='RECTANGULO', width_mm=2140, height_mm=3300),
            area_mm2=7062000) for i in range(sheets_for(n)))
        groups.append(MaterialGroup(glass_type_id=glass, thickness_mm=6, units=prepare_group_units(units),
                                    stock_candidates=stocks))
    return OptimizationProblem(order_ids=(900069,), config=OptimizationConfig(resolution_mm=resolution, margin_mm=3,
        separation_mm=3, angular_step_deg=5), groups=tuple(groups))


def _apply_address_limit():
    """Mismo límite que sequential_worker.py, solo donde existe `resource`."""
    try:
        import resource
    except ImportError:  # Windows: no hay RLIMIT; se mide igual, sin ese límite.
        return None
    old_hard = resource.getrlimit(resource.RLIMIT_AS)[1]
    limit = BUDGET.worker_address_bytes
    hard = limit if old_hard == resource.RLIM_INFINITY else min(old_hard, limit)
    resource.setrlimit(resource.RLIMIT_AS, (hard, hard))
    return hard


def _fallback_detail(statistics):
    """S2-M6: distingue un M6 que completó buscando de uno completado por el respaldo First Fit."""
    if statistics.get('fallback_used') != 1:
        return None
    limit = next((key.removeprefix('fallback_from_').upper() for key in statistics
                  if key.startswith('fallback_from_')), '?')
    return (f'respaldo FF por {limit}: M6 decidió {statistics.get("fallback_beam_units", 0)}, '
            f'respaldo {statistics.get("fallback_units", 0)}')


def _run_engine(count, method, connection):
    """Proceso hijo: un motor, un problema, un resultado resumido."""
    try:
        _apply_address_limit()
        problem = build_problem(count)
        started = time.monotonic()

        def checkpoint():
            if time.monotonic() - started >= BUDGET.calculation_seconds:
                raise TimeBudgetExceeded()

        scope = ExecutionScope(comparison_id=1, execution_id=METHODS_V2.index(method) + 1, method=method)
        adapted = EngineExecutionAdapter(method).execute(scope, problem, minimum_width_mm=RESIDUAL_MINIMUM_MM,
            minimum_height_mm=RESIDUAL_MINIMUM_MM, checkpoint=checkpoint)
        seconds = time.monotonic() - started
        result, diagnostic = adapted.payload.result, adapted.payload.diagnostic
        metrics = result.metrics if result is not None else None
        connection.send(dict(
            seconds=seconds, reason=diagnostic.termination_reason, error=adapted.error_type,
            placed=result.placed_units if result is not None else None,
            sheets=metrics.new_sheets_used if metrics is not None else None,
            utilization=str(metrics.utilization_pct) if metrics is not None else None,
            fallback=_fallback_detail(diagnostic.statistics),
        ))
    except BaseException as error:  # noqa: BLE001 - se informa como fila, nunca se oculta
        connection.send(dict(seconds=None, reason='EXECUTION_FAILED', error=type(error).__name__,
                             placed=None, sheets=None, utilization=None, fallback=None))
    finally:
        connection.close()


def measure(count, method):
    """Proceso padre: lanza el motor y lo detiene si supera arranque + cálculo."""
    context = multiprocessing.get_context('spawn')  # Igual en Windows y Linux
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_run_engine, args=(count, method, sender), daemon=True)
    began = time.monotonic()
    process.start()
    sender.close()
    row = None
    try:
        if receiver.poll(BUDGET.startup_seconds + BUDGET.calculation_seconds):
            row = receiver.recv()
    except EOFError:
        row = None  # El hijo terminó sin informar (por ejemplo, memoria agotada).
    if process.is_alive():
        process.terminate()
    process.join(10)
    if row is None:
        elapsed = time.monotonic() - began
        timed_out = elapsed >= BUDGET.startup_seconds + BUDGET.calculation_seconds
        reason = 'SUPERVISOR_TIMEOUT' if timed_out else f'PROCESS_EXITED({process.exitcode})'
        row = dict(seconds=elapsed, reason=reason, error=None, placed=None, sheets=None, utilization=None,
                   fallback=None)
    return row


def _cell(value, suffix=''):
    return '-' if value is None else f'{value}{suffix}'


def main(argv=None):
    parser = argparse.ArgumentParser(description='Carga reproducible de los seis motores (sin BD).')
    parser.add_argument('sizes', nargs='*', type=int, default=[46, 100, 150, 200, 300],
                        help='Cantidades de piezas (mínimo 2 cada una).')
    sizes = parser.parse_args(argv).sizes
    if any(size < 2 for size in sizes):
        parser.error('cada tamaño debe ser al menos 2 (dos grupos de material)')
    print(f'# Python {sys.version.split()[0]} en {sys.platform}; cálculo {BUDGET.calculation_seconds:g} s por motor; '
          f'RLIMIT_AS {"activo" if _resource_available() else "no disponible (Windows)"}', flush=True)
    header = f'{"piezas":>6}  {"motor":<6}  {"segundos":>8}  {"colocadas":>9}  {"planchas":>8}  {"aprov.%":>7}  motivo'
    for size in sizes:
        per_material = [sheets_for(size // 2), sheets_for(size - size // 2)]
        print(f'\n# {size} piezas; planchas 2140x3300 disponibles por material: {per_material[0]} y {per_material[1]}',
              flush=True)
        print(header, flush=True)
        for method in METHODS_V2:
            row = measure(size, method)
            seconds = None if row['seconds'] is None else f'{row["seconds"]:.2f}'
            placed = None if row['placed'] is None else f'{row["placed"]}/{size}'
            reason = row['reason'] + (f' ({row["error"]})' if row['error'] else '')
            reason += f' · {row["fallback"]}' if row['fallback'] else ''
            print(f'{size:>6}  {method:<6}  {_cell(seconds):>8}  {_cell(placed):>9}  {_cell(row["sheets"]):>8}  '
                  f'{_cell(row["utilization"]):>7}  {reason}', flush=True)


def _resource_available():
    try:
        import resource  # noqa: F401
    except ImportError:
        return False
    return True


if __name__ == '__main__':
    main()
