"""Descriptive TA-042 timing, not a performance acceptance threshold."""
from pathlib import Path
import json
import platform
from statistics import median
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT)]

from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.hole_filling import HoleFillingOptimizer
from experiments.optimization.loader import load_problem
from tests.unit.optimization.test_first_fit import problem, stock
from tests.unit.optimization.test_preparation import piece
from tests.unit.optimization.test_hole_filling import differentiating_problem


def measure(optimizer_type, problem_value, repeats=5):
    optimizer_type().optimize(problem_value)  # warm-up
    times = []
    signatures = []
    stats = None
    for _ in range(repeats):
        optimizer = optimizer_type()
        start = perf_counter()
        result = optimizer.optimize(problem_value)
        times.append((perf_counter() - start) * 1000)
        signatures.append(result.placements)
        stats = getattr(optimizer, "stats", None)
    assert all(signature == signatures[0] for signature in signatures)
    return median(times), result, stats


def main():
    cases = {
        "fallback_rectangles": problem([piece(width=2, height=2, quantity=3)], [stock(width=5, height=5)]),
        "pocket_mixto": differentiating_problem(),
        **{name: load_problem(name) for name in ("EXP-SMALL-001", "EXP-MEDIUM-001", "EXP-COMPLEX-001")},
    }
    report = {"python": platform.python_version(), "repetitions": 5, "statistic": "median_ms", "cases": []}
    for name, problem_value in cases.items():
        ff_ms, ff, _ = measure(FirstFitOptimizer, problem_value)
        hf_ms, hf, stats = measure(HoleFillingOptimizer, problem_value)
        report["cases"].append({
            "case": name, "hf_ms": round(hf_ms, 3), "ff_ms": round(ff_ms, 3),
            "ratio": round(hf_ms / ff_ms, 2), "hf_placed": hf.placed_units,
            "ff_placed": ff.placed_units, "pocket_used": bool(stats.accepted_pocket and not stats.coverage_fallback),
            "fallback_calls": stats.fallback_used, "coverage_fallback": stats.coverage_fallback,
            "activation_attempts": stats.activation_attempts, "maps_examined": stats.pocket_candidates,
            "anchors_checked": stats.anchors_checked, "placement_checks": stats.placement_checks,
            "budget_exhausted": stats.budget_exhausted,
        })
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
