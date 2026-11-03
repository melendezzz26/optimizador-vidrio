"""TA-042 local-search measurements; medians are descriptive, never gates."""
import json
from pathlib import Path
import platform
from statistics import median
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT)]

from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.hole_filling import HoleFillingLimits, HoleFillingOptimizer, HoleFillingSelector, _fallback_reason
from app.modules.optimization.domain.packing import FeasibleCandidate, _coordinate, _feasible_candidates
from app.modules.optimization.domain.problem import MaterialSource, OptimizationResult, Placement
from experiments.optimization.hole_filling.lab import prepare_case
from experiments.optimization.loader import load_problem
from tests.unit.optimization.test_first_fit import problem, stock
from tests.unit.optimization.test_hole_filling import differentiating_problem, product_problem
from tests.unit.optimization.test_preparation import piece


def seeded_run(setup, selector=None):
    """Start with SP-004's unchanged, validated seeds and pack its pending units."""
    layouts = dict(setup.layouts)
    placements = list(setup.seed_placements)
    group = setup.problem.groups[0]
    for unit in setup.pending:
        orientations = setup.prepared.orientations(unit)
        for source in (MaterialSource.REMNANT, MaterialSource.SHEET):
            choices = _feasible_candidates(group, source, orientations, setup.prepared, layouts,
                                            setup.problem.config, lambda: None)
            winner = selector.select(choices) if selector else next(choices, None)
            if winner is None:
                continue
            layouts[winner.stock.identity] = winner.layout_after
            placements.append(Placement(piece=unit, stock=winner.stock,
                x_mm=_coordinate(winner.column, setup.problem.config.resolution_mm),
                y_mm=_coordinate(winner.row, setup.problem.config.resolution_mm),
                rotation_deg=winner.orientation.rotation_deg, geometry=winner.orientation.geometry))
            break
    return OptimizationResult(problem=setup.problem, placements=tuple(placements))


def capability_hf(setup):
    selector = HoleFillingSelector()
    trial = seeded_run(setup, selector)
    if selector.stats.accepted_pocket:
        baseline = seeded_run(setup)
        reason = _fallback_reason(trial, baseline)
        if reason:
            selector.stats.coverage_fallback = reason == "coverage"
            selector.stats.sheet_fallback = reason == "sheets"
            selector.stats.fallback_used += 1
            trial = baseline
    return trial, selector.stats


def measure(run, repeats=5):
    run()  # warm caches and interpreter
    durations, results, stats = [], [], None
    for _ in range(repeats):
        start = perf_counter()
        result, stats = run()
        durations.append((perf_counter() - start) * 1000)
        results.append(result.placements)
    assert all(item == results[0] for item in results)
    return median(durations), result, stats


def record(name, ff_run, hf_run):
    ff_ms, ff, _ = measure(ff_run)
    hf_ms, hf, stats = measure(hf_run)
    return {
        "case": name, "hf_ms": round(hf_ms, 3), "ff_ms": round(ff_ms, 3),
        "ratio": round(hf_ms / ff_ms, 2), "hf_placed": hf.placed_units,
        "ff_placed": ff.placed_units,
        "hf_sheets": sum(s.source is MaterialSource.SHEET for s in hf.materials_used),
        "ff_sheets": sum(s.source is MaterialSource.SHEET for s in ff.materials_used),
        "pocket_used": bool(stats.accepted_pocket and not stats.coverage_fallback and not stats.sheet_fallback),
        "fallback_calls": stats.fallback_used, "coverage_fallback": stats.coverage_fallback,
        "sheet_fallback": stats.sheet_fallback, "orientations_inspected": stats.orientations_inspected,
        "regions": stats.pocket_candidates, "max_region_checks_observed": stats.max_region_checks_observed,
        "max_region_anchors_observed": stats.max_region_anchors_observed,
        "boundary_rows": stats.boundary_rows, "anchors_checked": stats.anchors_checked,
        "placement_checks": stats.placement_checks, "check_rows": stats.check_rows,
        "seed_probes": stats.seed_probes, "budget_exhausted": stats.budget_exhausted,
    }


def main():
    problems = {
        "fallback_rectangles": problem([piece(width=2, height=2, quantity=3)], [stock(width=5, height=5)]),
        "pocket_productivo": product_problem(),
        "mixto_anterior": differentiating_problem(),
        **{name: load_problem(name) for name in ("EXP-SMALL-001", "EXP-MEDIUM-001", "EXP-COMPLEX-001")},
    }
    report = {"python": platform.python_version(), "repetitions": 5, "statistic": "median_ms", "cases": []}
    for name, value in problems.items():
        def ff_run():
            return FirstFitOptimizer().optimize(value), None
        def hf_run():
            optimizer = HoleFillingOptimizer()
            result = optimizer.optimize(value)
            return result, optimizer.stats
        report["cases"].append(record(name, ff_run, hf_run))
    # The unchanged 16 validated seeds are input state, not packed again by FF.
    # Timings cover the two pending pieces and HF's baseline guard, excluding setup.
    setup = prepare_case("HF-CAPABILITY-001")
    report["cases"].append(record("HF-CAPABILITY-001_seeded",
                                  lambda: (seeded_run(setup), None),
                                  lambda: capability_hf(setup)))
    source = setup.stocks_by_id[8201]
    layout = setup.layouts[source.identity]
    orientation = next(iter(setup.prepared.orientations(setup.units_by_id[11]))).orientation
    row, column = layout.first_position(orientation.mask)
    candidate = FeasibleCandidate(stock=source, stock_rank=0, layout=layout, orientation=orientation,
                                  orientation_rank=0, row=row, column=column)
    report["bbox_sensitivity"] = []
    for denominator in (4, 8, 16, 32, 64, 128):
        limits = HoleFillingLimits(max_bbox_fraction_denominator=denominator)
        selector = HoleFillingSelector(limits)
        selector.select(iter((candidate,)))
        optimizer = HoleFillingOptimizer(limits)
        result = optimizer.optimize(problems["pocket_productivo"])
        report["bbox_sensitivity"].append({
            "denominator": denominator,
            "capability_pocket": bool(selector.stats.accepted_pocket),
            "product_pocket": bool(optimizer.stats.accepted_pocket and
                                   not optimizer.stats.coverage_fallback and not optimizer.stats.sheet_fallback),
            "product_regions": optimizer.stats.pocket_candidates,
            "product_anchors": optimizer.stats.anchors_checked,
            "product_placed": result.placed_units,
        })
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
