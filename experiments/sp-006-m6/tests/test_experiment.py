from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from experiments.optimization.loader import build_problem, load_problem, read_case
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.domain.problem import MaterialSource, OptimizationResult
from app.modules.optimization.domain.rasterizer import rasterize_geometry, rasterize_material
from sp006.beam import BeamSearch, SearchLimits
from sp006.runner import CASES, METHODS, export, run_one, run_suite, table
from sp006.validation import ROOT, audit, verify_snapshot


@pytest.fixture(scope="session")
def bundle():
    return run_suite(repeats=2, progress=False)


def test_snapshot_original_bytes():
    manifest = verify_snapshot()
    repo = ROOT.parents[1]
    for entry in manifest["files"]:
        original = subprocess.check_output(["git", "show", f"{manifest['source_commit']}:{entry['source']}"], cwd=repo)
        assert (ROOT / entry["target"]).read_bytes() == original
    assert len(manifest["files"]) == 22


@pytest.mark.parametrize("case_id,units,remnants,sheets", zip(CASES, (3, 9, 24), (1, 2, 3), (1, 2, 4)))
def test_original_cases(case_id, units, remnants, sheets):
    problem = load_problem(case_id)
    stock = [s for g in problem.groups for s in g.stock_candidates]
    assert len(problem.units) == units
    assert sum(s.source is MaterialSource.REMNANT for s in stock) == remnants
    assert sum(s.source is MaterialSource.SHEET for s in stock) == sheets
    assert problem.config.resolution_mm == 1 and problem.config.angular_step_deg == 5
    assert load_problem(case_id) == problem and load_problem(case_id) is not problem


@pytest.mark.parametrize("case_id", CASES)
@pytest.mark.parametrize("method", ("FF", "BF", "WF"))
def test_original_engines_equal_portable(case_id, method):
    # Dos procesos con PYTHONPATH diferentes evitan que app ya importada oculte el original.
    portable = run_one(case_id, method)
    original = run_one(case_id, method, original_repo=ROOT.parents[1])
    assert portable["status"] == original["status"] == "COMPLETE"
    assert portable["signature"] == original["signature"]
    assert portable["placements"] == original["placements"]
    assert portable["metrics"] == original["metrics"]


@pytest.mark.parametrize("case_id", CASES)
@pytest.mark.parametrize("method", METHODS)
def test_measured_geometry_determinism_and_limits(bundle, case_id, method):
    records = [r for r in bundle["records"] if r["case_id"] == case_id and r["method"] == method]
    assert len(records) == 2
    for record in records:
        assert record["status"] == "COMPLETE", record
        assert record["validation"]["valid"]
        assert record["deterministic"] is True
        assert record["input_unchanged"]
        assert record["peak_rss_mib"] < 256 and record["elapsed_s"] < 30
        if method.startswith("BS-"):
            stats = record["search_statistics"]
            assert stats["max_frontier"] <= int(method[-1])
            assert stats["expansions"] <= 60000 and stats["geometry_probes"] <= 1000000
            assert stats["state_bytes_bound"] <= 32 * 1024 ** 2


def test_beam_decisions_are_independent(bundle):
    records = [r for r in bundle["records"] if r["repeat"] == 1 and r["case_id"] == CASES[-1]]
    baselines = [r["placements"] for r in records if not r["method"].startswith("BS-")]
    assert all(r["placements"] not in baselines for r in records if r["method"].startswith("BS-"))
    assert all(r["search_statistics"]["max_frontier"] >= 2 for r in records if r["method"].startswith("BS-"))


def test_known_raster_and_manual_small():
    square = dict(type="RECTANGULO", width_mm=2, height_mm=2)
    assert rasterize_geometry(square, 1).rows == rasterize_material(square, 1).rows == (3, 3)
    result = FirstFitOptimizer().optimize(load_problem(CASES[0]))
    assert [(p.stock.source.value, p.x_mm, p.y_mm) for p in result.placements] == [
        ("RETAZO", 0, 0), ("PLANCHA", 0, 0), ("PLANCHA", 2, 0)]
    measured, residuals = calculate_metrics(result, Decimal(1), Decimal(1))
    assert measured.metrics.utilization_pct == Decimal("60.000")
    assert measured.metrics.waste_mm2 == 0
    assert sum(r.area_mm2 for r in residuals) == 8


def test_invalid_rotation_margin_overlap_and_priority_are_rejected():
    result = FirstFitOptimizer().optimize(load_problem(CASES[1]))
    first = result.placements[0]
    for bad in (replace(first, x_mm=Decimal(0)), replace(first, rotation_deg=Decimal(1))):
        with pytest.raises(ValueError):
            audit(replace(result, placements=(bad,) + result.placements[1:]))
    second = result.placements[1]
    overlap = replace(second, stock=first.stock, x_mm=first.x_mm, y_mm=first.y_mm,
                      geometry=first.geometry, rotation_deg=first.rotation_deg)
    with pytest.raises(ValueError):
        audit(replace(result, placements=(first, overlap) + result.placements[2:]))
    small = FirstFitOptimizer().optimize(load_problem(CASES[0]))
    sheet = next(s for g in small.problem.groups for s in g.stock_candidates if s.source is MaterialSource.SHEET)
    with pytest.raises(ValueError, match="retazo factible"):
        audit(replace(small, placements=(replace(small.placements[0], stock=sheet),)))


def test_separation_boundary():
    from app.modules.optimization.domain.packing import _empty_layout
    from app.modules.optimization.domain.raster_mask import RasterMask
    from app.modules.optimization.domain.problem import OptimizationConfig
    layout = _empty_layout(RasterMask(1, 8, (255,) * 8), OptimizationConfig(
        resolution_mm=Decimal(1), margin_mm=Decimal(1), separation_mm=Decimal(1)))
    mask = RasterMask(1, 2, (3, 3))
    assert not layout.check(mask, 0, 1).is_valid
    occupied = layout.place(mask, 1, 1)
    assert not occupied.check(mask, 1, 3).is_valid
    assert occupied.check(mask, 1, 4).is_valid


@pytest.mark.parametrize("changes,reason", [({"max_expansions": 1}, "EXPANSION_LIMIT"),
    ({"max_geometry_probes": 1}, "GEOMETRY_PROBE_LIMIT"), ({"max_state_bytes": 1}, "STATE_MEMORY_LIMIT")])
def test_explicit_limits_and_no_sheet_fallback(changes, reason):
    outcome = BeamSearch(SearchLimits(**changes)).optimize(load_problem(CASES[-1]))
    assert outcome.stop_reason == reason
    assert outcome.processed == 0 and not outcome.result.placements
    assert audit(outcome.result, outcome.processed)["pending_units"] == 24


def test_time_limit():
    outcome = BeamSearch(SearchLimits(seconds=1e-9)).optimize
    # Preparación puede abortar antes de que exista un frontier: fallo técnico explícito.
    from sp006.beam import SearchStopped
    with pytest.raises(SearchStopped, match="TIME_LIMIT"):
        outcome(load_problem(CASES[0]))


def test_no_fit_continues_and_stock_not_invented():
    data = read_case(CASES[0])  # Variación de prueba, nunca se exporta como caso oficial.
    data["pieces"][0]["geometria"]["width_mm"] = 10
    problem = build_problem(data)
    outcome = BeamSearch().optimize(problem)
    assert outcome.stop_reason is None
    assert outcome.processed == 3 and outcome.result.placed_units == 0
    assert audit(outcome.result)["no_fit_checks"] == 3
    metrics, residuals = calculate_metrics(outcome.result, Decimal(1), Decimal(1))
    assert metrics.metrics is None and not residuals


def test_no_fit_does_not_suppress_smaller_piece():
    data = read_case(CASES[0])
    data["pieces"][0]["geometria"]["width_mm"] = 10
    data["pieces"].append(dict(data["pieces"][0], id_pieza=2, cantidad=1,
                               geometria=dict(type="RECTANGULO", width_mm=1, height_mm=1)))
    outcome = BeamSearch().optimize(build_problem(data))
    assert [p.piece.piece_id for p in outcome.result.placements] == [2]
    assert outcome.processed == 4 and audit(outcome.result)["no_fit_checks"] == 3


def test_infeasible_remnant_allows_sheet_and_stock_order_is_normalized():
    data = read_case(CASES[0])
    data["stock"][0]["geometry"] = dict(type="RECTANGULO", width_mm=1, height_mm=1)
    data["stock"].reverse()
    outcome = BeamSearch().optimize(build_problem(data))
    assert outcome.result.complete
    assert all(p.stock.source is MaterialSource.SHEET for p in outcome.result.placements)
    assert audit(outcome.result)["valid"]


def test_beam_does_not_call_baseline_optimizers(monkeypatch):
    from app.modules.optimization.domain.best_fit import BestFitOptimizer
    from app.modules.optimization.domain.worst_fit import WorstFitOptimizer
    def forbidden(*args, **kwargs):
        raise AssertionError("M6 ejecutó un baseline.")
    for cls in (FirstFitOptimizer, BestFitOptimizer, WorstFitOptimizer):
        monkeypatch.setattr(cls, "optimize", forbidden)
    result = BeamSearch().optimize(load_problem(CASES[0])).result
    assert result.complete and result.method == "M6-BS"


def test_supervisor_rss_limit():
    record = run_one(CASES[-1], "BS-4", rss_limit_mib=1)
    assert record["status"] == "LIMIT" and record["stop_reason"] == "RSS_MEMORY_LIMIT"
    assert "metrics" not in record


def test_inputs_deeply_immutable():
    data = read_case(CASES[0])
    problem = build_problem(data)
    with pytest.raises(TypeError):
        problem.units[0].geometry["width_mm"] = 5
    data["pieces"][0]["geometria"]["width_mm"] = 100
    assert problem.units[0].geometry["width_mm"] == 2
    assert BeamSearch().optimize(problem).result.problem == problem


def test_exports_real_values(bundle, tmp_path):
    target = export(bundle, tmp_path)
    assert json.loads((target / "results.json").read_text(encoding="utf-8")) == bundle
    import pandas as pd
    frame = pd.read_csv(target / "results.csv")
    assert len(frame) == 36 and frame.geometry_valid.all() and frame.deterministic.all()
    assert set(frame.origin) == {"measured_local_cpu"}


def test_visualization_includes_pending_units(tmp_path):
    # Control real con presupuesto reducido; no se mezcla con las mediciones oficiales.
    record = run_one(CASES[-1], "BS-2", search={"max_expansions": 1})
    assert record["status"] == "LIMIT" and len(record["pending_units"]) == 24
    from sp006.plots import plot_layout
    import matplotlib.pyplot as plt
    fig = plot_layout(record)
    target = tmp_path / "pending-control.png"
    fig.savefig(target, dpi=100)
    assert target.stat().st_size > 10000
    plt.close(fig)
