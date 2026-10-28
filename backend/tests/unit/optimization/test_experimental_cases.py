"""TA-027 validation and sanity only: no benchmark or method ranking."""
from copy import deepcopy
from decimal import Decimal
import importlib.util
from pathlib import Path

import pytest

from app.modules.optimization.domain.best_fit import BestFitOptimizer
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.domain.worst_fit import WorstFitOptimizer

ROOT = Path(__file__).resolve().parents[4]
SPEC = importlib.util.spec_from_file_location("experimental_cases", ROOT / "experiments/optimization/loader.py")
loader = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(loader)
METHODS = [FirstFitOptimizer, BestFitOptimizer, WorstFitOptimizer]
EXPECTED = {"EXP-SMALL-001": (1, 3, 2, 1), "EXP-MEDIUM-001": (3, 9, 4, 1),
            "EXP-COMPLEX-001": (6, 24, 7, 2)}


@pytest.mark.parametrize("case_id", loader.CASES)
def test_cases_load_with_frozen_counts_materials_and_complete_configuration(case_id):
    data = loader.read_case(case_id)
    problem = loader.build_problem(data)
    definitions, units, sources, groups = EXPECTED[case_id]
    assert data["case_id"] == case_id
    assert len(data["pieces"]) == definitions
    assert len(problem.units) == units == sum(p["cantidad"] for p in data["pieces"])
    assert sum(len(g.stock_candidates) for g in problem.groups) == sources
    assert len(problem.groups) == groups
    assert problem.config.angular_step_deg == 5
    assert problem.config.resolution_mm == 1
    assert problem.config.margin_mm == problem.config.separation_mm == (0 if units == 3 else 1)
    assert data["rotation_allowed"] is True
    for group in problem.groups:
        assert all(p.material_key == group.key for p in group.units)
        assert all(s.material_key == group.key for s in group.stock_candidates)
    assert loader.load_problem(case_id) == problem


@pytest.mark.parametrize("case_id", loader.CASES)
def test_reconstructions_are_equal_deeply_detached_and_original_file_is_unchanged(case_id):
    path = loader.CASE_DIR / f"{case_id}.json"
    before = path.read_bytes()
    data = loader.read_case(case_id)
    original = deepcopy(data)
    inputs = [loader.build_problem(data) for _ in METHODS]
    assert data == original
    assert inputs[0] == inputs[1] == inputs[2]
    assert len({id(p) for p in inputs}) == 3
    assert len({id(p.units[0].geometry) for p in inputs}) == 3
    data["pieces"][0]["geometria"]["width_mm"] = 999
    data["stock"][0]["geometry"]["type"] = "INVALID"
    assert all(p == loader.build_problem(original) for p in inputs)
    with pytest.raises(TypeError):
        inputs[0].units[0].geometry["width_mm"] = 99
    assert path.read_bytes() == before


@pytest.mark.parametrize("case_id", loader.CASES)
@pytest.mark.parametrize("optimizer", METHODS)
def test_sanity_repeated_execution_and_real_geometry_revalidation(case_id, optimizer):
    data = loader.read_case(case_id)
    initial = loader.build_problem(data)
    before = repr(initial)
    first = optimizer().optimize(initial)
    second = optimizer().optimize(loader.load_problem(case_id))
    assert first == second
    assert repr(initial) == before and data == loader.read_case(case_id)
    assert first.placed_units > 0
    assert first.placed_units + len(first.unplaced_units) == first.total_units
    limits = {k: Decimal(str(v)) for k, v in data["residual_limits"].items()}
    # Shared metrics replays every placement and raises on invalid geometry.
    assert calculate_metrics(first, **limits) == calculate_metrics(second, **limits)


@pytest.mark.parametrize("case_id", loader.CASES)
def test_method_order_does_not_contaminate_later_runs(case_id):
    expected = {cls: cls().optimize(loader.load_problem(case_id)) for cls in METHODS}
    for cls in reversed(METHODS):
        assert cls().optimize(loader.load_problem(case_id)) == expected[cls]


@pytest.mark.parametrize("field,value", [("angular_step_deg", 90), ("resolution_mm", 0),
                                         ("margin_mm", -1), ("separation_mm", -1)])
def test_invalid_baseline_configuration_is_rejected(field, value):
    data = loader.read_case("EXP-SMALL-001")
    data["config"][field] = value
    with pytest.raises(ValueError):
        loader.build_problem(data)


def test_exactly_three_distinct_cases_and_geometry_diversity():
    assert {p.stem for p in loader.CASE_DIR.glob("*.json")} == set(loader.CASES)
    data = [loader.read_case(cid) for cid in loader.CASES]
    counts = [sum(p["cantidad"] for p in d["pieces"]) for d in data]
    assert counts == sorted(set(counts))
    shapes = [{p["tipo_forma"] for p in d["pieces"]} for d in data]
    assert shapes[0] < shapes[1] < shapes[2]
