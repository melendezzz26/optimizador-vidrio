"""Arnés estadístico de medición de carga y rendimiento (TA-QA-002).

Mide tiempos de reloj (mín, p50, p95, máx), consumo de memoria física residente (RSS pico)
y causas de error para los seis motores de optimización bajo la metodología SDD.

Uso desde backend/:
    python -m scripts.benchmark_qa_002 --sizes 10 25 50 100 150 200 --runs 3 --output-json ../docs/evidence/sprint-02/TA-QA-002/raw_results.json
"""
import argparse
import json
import math
import multiprocessing
import os
import sys
import threading
import time
from decimal import Decimal as D

import numpy as np
import psutil

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
MAX_SHEETS_PER_MATERIAL = DEFAULT_RUN_LOAD_BUDGET.max_stock_units_per_material  # 50
RESIDUAL_MINIMUM_MM = D(10)


def sheets_for(units_in_material: int) -> int:
    return max(MINIMUM_SHEETS_PER_MATERIAL, min(MAX_SHEETS_PER_MATERIAL, units_in_material))


def build_problem(count: int, resolution: int = 1) -> OptimizationProblem:
    if count < 2:
        raise ValueError("The benchmark requires at least two units for its two material groups")
    shapes = [
        (dict(type="RECTANGULO", width_mm=600, height_mm=800), D(480000)),
        (dict(type="CIRCUNFERENCIA", radius_mm=260), D(str(math.pi * 260**2)).quantize(D(".001"))),
        (dict(type="POLIGONO_CONVEXO", vertices_mm=((0, 0), (500, 0), (620, 400), (250, 700), (0, 400))), D(317000)),
    ]
    groups = []
    for glass, n in ((1, count // 2), (2, count - count // 2)):
        units = tuple(
            PieceUnit(
                order_id=900069,
                piece_id=glass * 100 + i % 3,
                unit_index=i // 3 + 1,
                glass_type_id=glass,
                thickness_mm=6,
                geometry=shapes[i % 3][0],
                area_mm2=shapes[i % 3][1],
            )
            for i in range(n)
        )
        stocks = tuple(
            StockCandidate(
                source=MaterialSource.SHEET,
                material_id=glass,
                physical_unit_index=i + 1,
                glass_type_id=glass,
                thickness_mm=6,
                geometry=dict(type="RECTANGULO", width_mm=2140, height_mm=3300),
                area_mm2=7062000,
            )
            for i in range(sheets_for(n))
        )
        groups.append(
            MaterialGroup(
                glass_type_id=glass,
                thickness_mm=6,
                units=prepare_group_units(units),
                stock_candidates=stocks,
            )
        )
    return OptimizationProblem(
        order_ids=(900069,),
        config=OptimizationConfig(
            resolution_mm=resolution,
            margin_mm=3,
            separation_mm=3,
            angular_step_deg=5,
        ),
        groups=tuple(groups),
    )


def _apply_address_limit():
    try:
        import resource
    except ImportError:
        return None
    old_hard = resource.getrlimit(resource.RLIMIT_AS)[1]
    limit = BUDGET.worker_address_bytes
    hard = limit if old_hard == resource.RLIM_INFINITY else min(old_hard, limit)
    resource.setrlimit(resource.RLIMIT_AS, (hard, hard))
    return hard


def _fallback_detail(statistics):
    if statistics.get("fallback_used") != 1:
        return None
    limit = next(
        (key.removeprefix("fallback_from_").upper() for key in statistics if key.startswith("fallback_from_")), "?"
    )
    return (
        f"respaldo FF por {limit}: M6 decidio {statistics.get('fallback_beam_units', 0)}, "
        f"respaldo {statistics.get('fallback_units', 0)}"
    )


def _run_engine(count, method, connection):
    try:
        _apply_address_limit()
        problem = build_problem(count)
        started = time.monotonic()

        def checkpoint():
            if time.monotonic() - started >= BUDGET.calculation_seconds:
                raise TimeBudgetExceeded()

        scope = ExecutionScope(comparison_id=1, execution_id=METHODS_V2.index(method) + 1, method=method)
        adapted = EngineExecutionAdapter(method).execute(
            scope,
            problem,
            minimum_width_mm=RESIDUAL_MINIMUM_MM,
            minimum_height_mm=RESIDUAL_MINIMUM_MM,
            checkpoint=checkpoint,
        )
        seconds = time.monotonic() - started
        result, diagnostic = adapted.payload.result, adapted.payload.diagnostic
        metrics = result.metrics if result is not None else None
        connection.send(
            dict(
                seconds=seconds,
                reason=diagnostic.termination_reason,
                error=adapted.error_type,
                placed=result.placed_units if result is not None else None,
                sheets=metrics.new_sheets_used if metrics is not None else None,
                utilization=float(metrics.utilization_pct) if metrics is not None else None,
                fallback=_fallback_detail(diagnostic.statistics),
            )
        )
    except BaseException as error:
        connection.send(
            dict(
                seconds=None,
                reason="EXECUTION_FAILED",
                error=type(error).__name__,
                placed=None,
                sheets=None,
                utilization=None,
                fallback=None,
            )
        )
    finally:
        connection.close()


def _monitor_rss(pid, stop_event, peak_container):
    try:
        proc = psutil.Process(pid)
        while not stop_event.is_set():
            try:
                mem = proc.memory_info().rss
                if mem > peak_container[0]:
                    peak_container[0] = mem
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
            time.sleep(0.04)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass


def measure_single_run(count: int, method: str) -> dict:
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_run_engine, args=(count, method, sender), daemon=True)

    peak_rss = [0]
    stop_event = threading.Event()
    began = time.monotonic()

    process.start()
    sender.close()

    monitor_thread = threading.Thread(target=_monitor_rss, args=(process.pid, stop_event, peak_rss), daemon=True)
    monitor_thread.start()

    row = None
    try:
        timeout = BUDGET.startup_seconds + BUDGET.calculation_seconds  # 150 s
        if receiver.poll(timeout):
            row = receiver.recv()
    except EOFError:
        row = None
    finally:
        stop_event.set()
        monitor_thread.join(timeout=1.0)

    if process.is_alive():
        process.terminate()
    process.join(10)

    if row is None:
        elapsed = time.monotonic() - began
        timed_out = elapsed >= timeout
        reason = "SUPERVISOR_TIMEOUT" if timed_out else f"PROCESS_EXITED({process.exitcode})"
        row = dict(
            seconds=elapsed,
            reason=reason,
            error=None,
            placed=None,
            sheets=None,
            utilization=None,
            fallback=None,
        )

    row["peak_rss_mib"] = round(peak_rss[0] / (1024 * 1024), 2)
    return row


def calculate_stats(runs_data: list[dict], count: int) -> dict:
    times = [r["seconds"] for r in runs_data if r["seconds"] is not None]
    rss_list = [r["peak_rss_mib"] for r in runs_data if r["peak_rss_mib"] > 0]
    reasons = [r["reason"] for r in runs_data]

    placed = runs_data[-1].get("placed")
    sheets = runs_data[-1].get("sheets")
    utilization = runs_data[-1].get("utilization")
    fallback = runs_data[-1].get("fallback")

    # Pick dominant reason
    dominant_reason = max(set(reasons), key=reasons.count)

    if times:
        p50 = float(np.percentile(times, 50))
        p95 = float(np.percentile(times, 95))
        min_time = float(np.min(times))
        max_time = float(np.max(times))
    else:
        p50 = p95 = min_time = max_time = None

    peak_rss = float(np.max(rss_list)) if rss_list else None

    return {
        "count": count,
        "runs": len(runs_data),
        "min_s": round(min_time, 3) if min_time is not None else None,
        "p50_s": round(p50, 3) if p50 is not None else None,
        "p95_s": round(p95, 3) if p95 is not None else None,
        "max_s": round(max_time, 3) if max_time is not None else None,
        "peak_rss_mib": peak_rss,
        "placed": placed,
        "sheets": sheets,
        "utilization_pct": utilization,
        "reason": dominant_reason,
        "fallback": fallback,
        "raw_runs": runs_data,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Medición de Carga y Rendimiento TA-QA-002.")
    parser.add_argument(
        "--sizes",
        nargs="+",
        type=int,
        default=[10, 25, 50, 100, 150, 200],
        help="Cantidades de unidades a evaluar (mínimo 2)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Número de iteraciones por escenario para cálculo de p50 y p95 (mínimo 1, sugerido >=3)",
    )
    parser.add_argument(
        "--methods",
        nargs="+",
        choices=METHODS_V2,
        default=METHODS_V2,
        help="Motores a evaluar (por defecto todos los seis de METHODS_V2)",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default=None,
        help="Ruta donde guardar el resumen y datos crudos en formato JSON",
    )

    args = parser.parse_args(argv)
    sizes = args.sizes
    runs = args.runs
    methods = args.methods

    if any(s < 2 for s in sizes):
        parser.error("Cada tamaño debe ser de al menos 2 unidades.")

    print(
        f"# TA-QA-002: Benchmark Estadistico con {runs} corridas por motor",
        flush=True,
    )
    print(
        f"# Entorno: Python {sys.version.split()[0]} en {sys.platform} | Checkpoint {BUDGET.calculation_seconds:g} s",
        flush=True,
    )
    print(
        f"# Motores evaluados: {', '.join(methods)}",
        flush=True,
    )

    header = f"{'piezas':>6}  {'motor':<6}  {'p50 (s)':>8}  {'p95 (s)':>8}  {'RSS (MiB)':>10}  {'colocadas':>10}  {'planchas':>8}  {'aprov.%':>8}  motivo"
    results_matrix = {}

    for size in sizes:
        per_mat = [sheets_for(size // 2), sheets_for(size - size // 2)]
        print(f"\n================================================================================")
        print(f"# Escenario: {size} piezas ({runs} corridas) | Planchas por material: {per_mat[0]} y {per_mat[1]}")
        print(f"================================================================================")
        print(header, flush=True)

        results_matrix[size] = {}

        for method in methods:
            run_records = []
            for r_idx in range(runs):
                single = measure_single_run(size, method)
                run_records.append(single)

            stats = calculate_stats(run_records, size)
            results_matrix[size][method] = stats

            p50_str = f"{stats['p50_s']:.2f}" if stats["p50_s"] is not None else "-"
            p95_str = f"{stats['p95_s']:.2f}" if stats["p95_s"] is not None else "-"
            rss_str = f"{stats['peak_rss_mib']:.2f}" if stats["peak_rss_mib"] is not None else "-"
            placed_str = f"{stats['placed']}/{size}" if stats["placed"] is not None else "-"
            sheets_str = str(stats["sheets"]) if stats["sheets"] is not None else "-"
            util_str = f"{stats['utilization_pct']:.2f}%" if stats["utilization_pct"] is not None else "-"

            reason_str = stats["reason"]
            if stats["fallback"]:
                reason_str += f" · {stats['fallback']}"

            print(
                f"{size:>6}  {method:<6}  {p50_str:>8}  {p95_str:>8}  {rss_str:>10}  {placed_str:>10}  {sheets_str:>8}  {util_str:>8}  {reason_str}",
                flush=True,
            )

    if args.output_json:
        out_dir = os.path.dirname(os.path.abspath(args.output_json))
        os.makedirs(out_dir, exist_ok=True)
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(results_matrix, f, indent=2)
        print(f"\n[+] Resultados exportados a JSON: {args.output_json}")


if __name__ == "__main__":
    main()
