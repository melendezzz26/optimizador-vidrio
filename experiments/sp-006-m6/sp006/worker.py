"""Proceso CPU por ejecución: sin imports web, ORM ni configuración de aplicación."""
from dataclasses import asdict
from decimal import Decimal
import json
from pathlib import Path
import sys
from time import perf_counter

import psutil
from experiments.optimization.loader import CASES, build_problem, read_case
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.best_fit import BestFitOptimizer
from app.modules.optimization.domain.worst_fit import WorstFitOptimizer
from app.modules.optimization.domain.metrics import calculate_metrics
from sp006.beam import BeamSearch, SearchLimits, SearchStopped, VERSION
from sp006.validation import audit, jsonable, placement_rows, stable_signature


def calculate(request):
    method, case_id = request["method"], request["case_id"]
    if case_id not in CASES:
        raise ValueError("Fixture no oficial.")
    data = read_case(case_id)
    before = json.dumps(data, sort_keys=True)
    started = perf_counter()
    calls = 0
    proc = psutil.Process()

    def checkpoint():
        nonlocal calls
        calls += 1
        if perf_counter() - started > request.get("seconds", 30):
            raise SearchStopped("TIME_LIMIT")
        if calls % 64 == 0 and proc.memory_info().rss > request.get("rss_limit_mib", 256) * 1024 ** 2:
            raise SearchStopped("RSS_MEMORY_LIMIT")

    problem = build_problem(data)
    processed = len(problem.units)
    stop, stats, trace = None, {}, ()
    if method.startswith("BS-"):
        params = dict(request.get("search", {}), width=int(method.split("-")[1]))
        params.setdefault("seconds", request.get("seconds", 30))
        outcome = BeamSearch(SearchLimits(**params)).optimize(problem, checkpoint=checkpoint)
        result, processed, stop, stats, trace = (outcome.result, outcome.processed, outcome.stop_reason,
                                                outcome.statistics, outcome.trace)
    else:
        optimizer = {"FF": FirstFitOptimizer, "BF": BestFitOptimizer, "WF": WorstFitOptimizer}[method]()
        result = optimizer.optimize(problem, checkpoint=checkpoint)
    limits = {k: Decimal(str(v)) for k, v in data["residual_limits"].items()}
    result, residuals = calculate_metrics(result, **limits)
    checkpoint()
    elapsed = perf_counter() - started
    audit_started = perf_counter()
    checks = audit(result, processed)
    if before != json.dumps(data, sort_keys=True) or build_problem(data) != problem:
        raise ValueError("Se alteró la entrada experimental.")
    metrics = jsonable(asdict(result.metrics)) if result.metrics is not None else None
    used_remnants = sum(s.source.value == "RETAZO" for s in result.materials_used)
    placed_ids = {p.piece.identity for p in result.placements}
    no_fit = [[u.piece_id, u.unit_index] for u in result.problem.units[:processed] if u.identity not in placed_ids]
    pending = [[u.piece_id, u.unit_index] for u in result.problem.units[processed:]]
    status = "LIMIT" if stop else ("COMPLETE" if result.complete else "PARTIAL_GEOMETRIC")
    record = dict(case_id=case_id, method=method, algorithm_version=VERSION if method.startswith("BS-") else "NewGlass-snapshot",
        status=status, stop_reason=stop, requested=result.total_units, placed=result.placed_units,
        unplaced=[[u.piece_id, u.unit_index] for u in result.unplaced_units], processed_units=processed,
        no_fit_units=no_fit, pending_units=pending,
        sheets_used=sum(s.source.value == "PLANCHA" for s in result.materials_used), remnants_used=used_remnants,
        metrics=metrics, elapsed_s=elapsed, audit_s=perf_counter() - audit_started,
        placements=placement_rows(result), residuals=[jsonable(asdict(r)) for r in residuals],
        validation=checks, search_statistics=stats, trace=jsonable(trace), input_unchanged=True)
    record["signature"] = stable_signature(record)
    return record


def main():
    request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    try:
        record = calculate(request)
    except SearchStopped as error:
        record = dict(case_id=request["case_id"], method=request["method"], status="LIMIT",
                      stop_reason=str(error))
    except Exception as error:
        record = dict(case_id=request["case_id"], method=request["method"], status="ERROR",
                      error_type=type(error).__name__, error=str(error))
    Path(sys.argv[2]).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
