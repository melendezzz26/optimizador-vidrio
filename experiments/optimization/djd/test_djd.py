from dataclasses import replace
from decimal import Decimal as D
from itertools import combinations
from pathlib import Path
import json

from app.modules.optimization.application.preparation import prepare_persisted_problem
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.best_fit import BestFitOptimizer
from app.modules.optimization.domain.worst_fit import WorstFitOptimizer
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.domain.problem import MaterialSource, OptimizationConfig, StockCandidate
from experiments.optimization.djd import DJDExperimental
from experiments.optimization.djd.djd_experimental import _combination_sets


def _problem(specs, stocks, *, margin=0, separation=0, step=90):
    rows = [{
        "id_pedido": 1, "id_pieza": piece_id, "cantidad": quantity,
        "id_tipo_vidrio": 1, "espesor_mm": 6, "tipo_forma": "RECTANGULO",
        "geometria": {"type": "RECTANGULO", "width_mm": width, "height_mm": height},
        "area_mm2": D(width * height),
    } for piece_id, width, height, quantity in specs]
    config = OptimizationConfig(resolution_mm=D(1), margin_mm=D(margin),
                                separation_mm=D(separation), angular_step_deg=D(step))
    prepared = prepare_persisted_problem([1], rows, config)
    candidates = tuple(StockCandidate(
        source=source, material_id=material_id, physical_unit_index=1,
        glass_type_id=glass, thickness_mm=D(thickness),
        geometry={"type": "RECTANGULO", "width_mm": width, "height_mm": height},
        area_mm2=D(width * height),
    ) for material_id, source, width, height, glass, thickness in stocks)
    return replace(prepared, groups=tuple(replace(
        group, stock_candidates=tuple(candidate for candidate in candidates if candidate.material_key == group.key),
    ) for group in prepared.groups))


def _discriminant_problem():
    path = Path(__file__).resolve().parent / "cases/DJD-DISCRIMINANT-001.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    from experiments.optimization.loader import build_problem
    return data, build_problem(data)


def test_deterministic_largest_first_order_and_initial_fullness_one_third():
    # El margen reduce el área raster útil, pero el umbral publicado usa el área nominal 20x20.
    problem = _problem([(8, 8, 9, 1), (2, 10, 6, 1), (3, 2, 2, 1)],
                       [(1, MaterialSource.SHEET, 20, 20, 1, 6)], margin=1)
    _, trace = DJDExperimental().optimize(problem)
    assert trace.processing_order == ((8, 1), (2, 1), (3, 1))
    first_source_ratio = trace.initial_fill_ratio[0]["ratio"]
    assert D(trace.initial_fill_ratio[0]["initial_capacity_mm2"]) == D(400)
    assert D(first_source_ratio) == D(136) / D(400)
    assert trace.selected_groups[0]["phase"] == "initial_fill"
    assert all(group["phase"] == "initial_fill" for group in trace.selected_groups)


def test_lazy_combinations_of_sizes_one_two_and_three():
    items = tuple(range(5))
    assert list(_combination_sets(items, 1)) == list(combinations(items, 1))
    assert len(list(_combination_sets(items, 1))) == 5
    assert len(list(_combination_sets(items, 2))) == 10
    assert len(list(_combination_sets(items, 3))) == 10


def test_discriminant_selects_pair_at_published_one_twentieth_increment():
    data, problem = _discriminant_problem()
    result, trace = DJDExperimental().optimize(problem)
    selected_pair = next(group for group in trace.selected_groups if group["size"] == 2)
    assert data["label"] == "CASO DE DISCRIMINACIÓN HEURÍSTICA — NO FORMA PARTE DE TA-027"
    assert selected_pair["piece_ids"] == [2, 3]
    assert D(selected_pair["waste_tolerance_mm2"]) == D(5)
    assert trace.waste_tolerance_steps == 1
    assert result.placed_units == result.total_units == 3
    assert trace.feasible_combinations >= 1


def test_area_pruning_precedes_geometric_checks_on_discriminant():
    _, problem = _discriminant_problem()
    _, trace = DJDExperimental().optimize(problem)
    assert trace.combinations_pruned > 0
    assert trace.pruned_by_size[1] > 0
    assert trace.geometric_checks > 0
    assert trace.combinations_size_2 > 0


def test_djd_and_baselines_complete_discriminant_but_trace_group_decision_differs():
    _, problem = _discriminant_problem()
    djd_result, trace = DJDExperimental().optimize(problem)
    assert djd_result.complete
    assert any(size == 2 for size in trace.selected_combination_sizes)
    for optimizer in (FirstFitOptimizer, BestFitOptimizer, WorstFitOptimizer):
        baseline = optimizer().optimize(problem)
        measured, _ = calculate_metrics(baseline, D(1), D(1))
        assert measured.complete
        assert [(p.piece.identity, p.stock.identity) for p in measured.placements] != []


def test_remnant_priority_material_and_thickness_compatibility():
    problem = _problem([(1, 2, 2, 1)], [
        (2, MaterialSource.SHEET, 4, 4, 1, 6),
        (1, MaterialSource.REMNANT, 2, 2, 1, 6),
    ])
    result, _ = DJDExperimental().optimize(problem)
    assert result.placements[0].stock.source is MaterialSource.REMNANT
    assert all(p.piece.material_key == p.stock.material_key for p in result.placements)


def test_margin_separation_rotation_and_no_overlap_use_existing_layout():
    problem = _problem([(1, 3, 2, 2)], [(1, MaterialSource.SHEET, 8, 7, 1, 6)],
                       margin=1, separation=1, step=90)
    result, _ = DJDExperimental().optimize(problem)
    assert result.complete
    assert all(p.x_mm >= 1 and p.y_mm >= 1 for p in result.placements)
    assert result.placements[1].x_mm - result.placements[0].x_mm >= 4 or result.placements[1].y_mm - result.placements[0].y_mm >= 3


def test_rotation_is_allowed_and_result_is_deterministic():
    problem = _problem([(1, 3, 2, 1)], [(1, MaterialSource.SHEET, 2, 3, 1, 6)])
    first, trace1 = DJDExperimental().optimize(problem)
    second, trace2 = DJDExperimental().optimize(problem)
    assert first.placements == second.placements
    assert trace1 == trace2
    assert first.placements[0].rotation_deg == 90


def test_complex_fixture_snapshots_are_not_mutated_and_keys_remain_compatible():
    from experiments.optimization.loader import load_problem, read_case
    data = read_case("EXP-COMPLEX-001")
    before = repr(data)
    result, _ = DJDExperimental().optimize(load_problem("EXP-COMPLEX-001"))
    assert repr(data) == before
    assert all(p.piece.glass_type_id == p.stock.glass_type_id for p in result.placements)
    assert all(p.piece.thickness_mm == p.stock.thickness_mm for p in result.placements)
