"""TA-053 T01: bounded Beam Search rules and fixture regression."""
from decimal import Decimal
import importlib.util
from pathlib import Path

import pytest

from app.modules.optimization.domain.beam_search import (
    BeamSearchLimits,
    BeamSearchOptimizer,
)
from app.modules.optimization.domain.problem import MaterialSource

ROOT = Path(__file__).resolve().parents[4]
SPEC = importlib.util.spec_from_file_location(
    "experimental_cases", ROOT / "experiments/optimization/loader.py"
)
loader = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(loader)


@pytest.mark.parametrize("case_id", loader.CASES)
def test_official_cases_are_complete_and_deterministic(case_id):
    first = BeamSearchOptimizer().optimize(loader.load_problem(case_id))
    second = BeamSearchOptimizer().optimize(loader.load_problem(case_id))

    assert first == second
    assert first.method == "M6-BS"
    assert first.complete
    assert first.placed_units == first.total_units
    assert all(placement.piece.material_key == placement.stock.material_key
               for placement in first.placements)


def test_m6_prioritizes_a_feasible_remnant_before_a_sheet():
    problem = loader.load_problem("EXP-SMALL-001")
    assert any(stock.source is MaterialSource.REMNANT
               for stock in problem.groups[0].stock_candidates)
    assert any(stock.source is MaterialSource.SHEET
               for stock in problem.groups[0].stock_candidates)

    result = BeamSearchOptimizer().optimize(problem)
    assert result.placements[0].stock.source is MaterialSource.REMNANT


def test_no_fit_is_not_reported_as_complete_and_does_not_mutate_problem():
    problem = loader.load_problem("EXP-SMALL-001")
    group = problem.groups[0]
    before_stock = group.stock_candidates
    # A zero-width compatible source is rejected by the existing contract;
    # use a tiny valid sheet that cannot hold the 2 mm unit instead.
    from dataclasses import replace
    from app.modules.optimization.domain.problem import StockCandidate

    tiny = StockCandidate(
        source=MaterialSource.SHEET,
        material_id=999,
        physical_unit_index=1,
        glass_type_id=group.glass_type_id,
        thickness_mm=group.thickness_mm,
        geometry={"type": "RECTANGULO", "width_mm": 1, "height_mm": 1},
        area_mm2=Decimal("1"),
    )
    problem = replace(problem, groups=(replace(
        group, stock_candidates=(tiny,),
    ),)    )
    result = BeamSearchOptimizer().optimize(problem)

    assert not result.complete
    assert result.placed_units == 0
    assert group.stock_candidates == before_stock


def test_expansion_limit_is_distinguished_from_no_fit():
    problem = loader.load_problem("EXP-SMALL-001")
    optimizer = BeamSearchOptimizer(BeamSearchLimits(
        width=2, children_per_parent=1, positions_per_orientation=1,
        max_expansions=1, max_geometry_probes=1000000,
        max_state_bytes=32 * 1024 * 1024, seconds=30, complete_on_stop=False,
    ))
    outcome = optimizer.run(problem)

    assert outcome.stop_reason == "EXPANSION_LIMIT"
    assert outcome.result.placed_units < outcome.result.total_units
