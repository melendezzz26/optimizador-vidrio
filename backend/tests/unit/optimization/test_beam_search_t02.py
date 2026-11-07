"""TA-053 T02: exhaustive internal M6 validation."""
import json
import importlib.util
from decimal import Decimal
from pathlib import Path
from dataclasses import replace

import pytest

from app.modules.optimization.domain.beam_search import (
    BeamSearchLimits,
    BeamSearchOptimizer,
)
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.domain.problem import MaterialSource, StockCandidate

ROOT = Path(__file__).resolve().parents[4]
SPEC = importlib.util.spec_from_file_location(
    "experimental_cases", ROOT / "experiments/optimization/loader.py"
)
loader = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(loader)
EVIDENCE = json.loads(
    (ROOT / "experiments/sp-006-m6/evidence/local-cpu-results.json").read_text()
)


def _placement_signature(result):
    return tuple(
        (
            placement.piece.piece_id,
            placement.piece.unit_index,
            placement.stock.source.value,
            placement.stock.material_id,
            placement.stock.physical_unit_index,
            str(placement.x_mm),
            str(placement.y_mm),
            str(placement.rotation_deg),
        )
        for placement in result.placements
    )


def _evidence_record(case_id):
    return next(
        record for record in EVIDENCE["records"]
        if record["case_id"] == case_id
        and record["method"] == "BS-2"
        and record["repeat"] == 1
    )


def test_all_official_shapes_and_material_groups_are_covered():
    cases = [loader.read_case(case_id) for case_id in loader.CASES]
    shapes = {piece["tipo_forma"] for case in cases for piece in case["pieces"]}

    assert shapes == {"RECTANGULO", "CIRCUNFERENCIA", "POLIGONO_CONVEXO"}
    result = BeamSearchOptimizer().optimize(loader.load_problem("EXP-COMPLEX-001"))
    assert len(result.problem.groups) == 2
    assert {placement.piece.material_key for placement in result.placements} == {
        group.key for group in result.problem.groups
    }


@pytest.mark.parametrize("case_id", loader.CASES)
def test_fidelity_includes_sources_positions_rotations_and_metrics(case_id):
    problem = loader.load_problem(case_id)
    result = BeamSearchOptimizer().optimize(problem)
    evidence = _evidence_record(case_id)
    limits = loader.read_case(case_id)["residual_limits"]
    measured, _ = calculate_metrics(
        result,
        **{key: Decimal(str(value)) for key, value in limits.items()},
    )

    expected_signature = tuple(
        (
            placement["piece_id"],
            placement["unit_index"],
            placement["source"],
            placement["material_id"],
            placement["stock_unit_index"],
            placement["x_mm"],
            placement["y_mm"],
            placement["rotation_deg"],
        )
        for placement in evidence["placements"]
    )
    assert _placement_signature(result) == expected_signature
    assert measured.metrics is not None
    assert str(measured.metrics.waste_mm2) == evidence["metrics"]["waste_mm2"]
    assert str(measured.metrics.utilization_pct) == evidence["metrics"]["utilization_pct"]


@pytest.mark.parametrize("case_id", loader.CASES)
def test_repeated_runs_preserve_complete_result_and_source_order(case_id):
    problem = loader.load_problem(case_id)
    first = BeamSearchOptimizer().optimize(problem)
    second = BeamSearchOptimizer().optimize(problem)

    assert first == second
    assert first.complete
    assert _placement_signature(first) == _placement_signature(second)
    assert first.problem == problem


def test_geometry_is_revalidated_with_margin_separation_and_no_overlap():
    problem = loader.load_problem("EXP-COMPLEX-001")
    result = BeamSearchOptimizer().optimize(problem)
    checked, residuals = calculate_metrics(
        result, minimum_width_mm=Decimal("1"), minimum_height_mm=Decimal("1")
    )

    assert checked.metrics is not None
    assert all(residual.area_mm2 > 0 for residual in residuals)
    assert all(
        placement.rotation_deg % problem.config.angular_step_deg == 0
        for placement in result.placements
    )


def test_feasible_remnant_precedes_sheet_but_infeasible_remnant_falls_back():
    original = loader.load_problem("EXP-SMALL-001")
    group = original.groups[0]
    sheet = next(
        stock for stock in group.stock_candidates
        if stock.source is MaterialSource.SHEET
    )
    tiny_remnant = StockCandidate(
        source=MaterialSource.REMNANT,
        material_id=901,
        physical_unit_index=1,
        glass_type_id=group.glass_type_id,
        thickness_mm=group.thickness_mm,
        geometry={"type": "RECTANGULO", "width_mm": 1, "height_mm": 1},
        area_mm2=Decimal("1"),
    )
    problem = replace(
        original,
        groups=(replace(group, stock_candidates=(tiny_remnant, sheet)),),
    )

    result = BeamSearchOptimizer().optimize(problem)

    assert result.complete
    assert result.placements[0].stock.source is MaterialSource.SHEET
    assert original.groups[0].stock_candidates != problem.groups[0].stock_candidates
    assert original.groups[0].stock_candidates[0].source is MaterialSource.REMNANT


def test_no_fit_and_resource_limits_have_distinct_outcomes():
    problem = loader.load_problem("EXP-SMALL-001")
    group = problem.groups[0]
    impossible = StockCandidate(
        source=MaterialSource.SHEET,
        material_id=902,
        physical_unit_index=1,
        glass_type_id=group.glass_type_id,
        thickness_mm=group.thickness_mm,
        geometry={"type": "RECTANGULO", "width_mm": 1, "height_mm": 1},
        area_mm2=Decimal("1"),
    )
    no_fit_problem = replace(
        problem, groups=(replace(group, stock_candidates=(impossible,)),)
    )
    no_fit = BeamSearchOptimizer().run(no_fit_problem)
    limited = BeamSearchOptimizer(BeamSearchLimits(
        max_expansions=1,
        max_geometry_probes=1000000,
        complete_on_stop=False,
    )).run(problem)

    assert no_fit.stop_reason is None
    assert not no_fit.result.complete
    assert no_fit.result.placed_units == 0
    assert limited.stop_reason == "EXPANSION_LIMIT"
    assert limited.result.placed_units < limited.result.total_units


@pytest.mark.parametrize(
    ("limits", "reason"),
    [
        (BeamSearchLimits(max_geometry_probes=1, complete_on_stop=False), "GEOMETRY_PROBE_LIMIT"),
        (BeamSearchLimits(max_state_bytes=1, complete_on_stop=False), "STATE_MEMORY_LIMIT"),
        (BeamSearchLimits(seconds=0.000001, complete_on_stop=False), "TIME_LIMIT"),
    ],
)
def test_each_configured_resource_limit_is_observable(limits, reason):
    outcome = BeamSearchOptimizer(limits).run(
        loader.load_problem("EXP-MEDIUM-001")
    )

    assert outcome.stop_reason == reason
    assert outcome.result.placed_units <= outcome.result.total_units
