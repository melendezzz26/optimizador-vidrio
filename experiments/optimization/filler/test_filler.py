from dataclasses import replace
from decimal import Decimal as D

from app.modules.optimization.domain.problem import MaterialSource, OptimizationConfig, StockCandidate
from app.modules.optimization.application.preparation import prepare_persisted_problem
from experiments.optimization.filler import FillerExperimental


def _problem(specs, stocks, *, separation=0, margin=0, step=90):
    rows = []
    for identifier, width, height, quantity in specs:
        rows.append({"id_pedido": 1, "id_pieza": identifier, "cantidad": quantity,
                     "id_tipo_vidrio": 1, "espesor_mm": 6, "tipo_forma": "RECTANGULO",
                     "geometria": {"type": "RECTANGULO", "width_mm": width, "height_mm": height},
                     "area_mm2": D(width * height)})
    config = OptimizationConfig(resolution_mm=D(1), margin_mm=D(margin),
                                separation_mm=D(separation), angular_step_deg=D(step))
    prepared = prepare_persisted_problem([1], rows, config)
    candidates = tuple(StockCandidate(
        source=source, material_id=identifier, physical_unit_index=1,
        glass_type_id=1, thickness_mm=D(6),
        geometry={"type": "RECTANGULO", "width_mm": width, "height_mm": height},
        area_mm2=D(width * height),
    ) for identifier, source, width, height in stocks)
    return replace(prepared, groups=tuple(replace(g, stock_candidates=candidates) for g in prepared.groups))


def test_descending_area_and_stable_identifier_tie_break():
    problem = _problem([(9, 2, 2, 1), (3, 1, 4, 1), (5, 2, 2, 1)], [(1, MaterialSource.SHEET, 10, 10)])
    _, trace = FillerExperimental().optimize(problem)
    assert trace.processing_order == ((3, 1), (5, 1), (9, 1))


def test_temporarily_skips_large_unfit_piece_then_fills_active_source():
    problem = _problem([(1, 3, 2, 1), (2, 2, 2, 1), (3, 1, 2, 1)],
                       [(1, MaterialSource.SHEET, 4, 2), (2, MaterialSource.SHEET, 2, 2)])
    result, trace = FillerExperimental().optimize(problem)
    assert [(p.piece.piece_id, p.stock.material_id) for p in result.placements] == [(1, 1), (3, 1), (2, 2)]
    assert trace.successful_fill_after_skip >= 1
    assert trace.pieces_per_source["PLANCHA:1:1"] == 2


def test_switch_only_after_active_source_has_no_feasible_pending_piece():
    problem = _problem([(1, 3, 2, 1), (2, 2, 2, 1), (3, 1, 2, 1)],
                       [(1, MaterialSource.SHEET, 4, 2), (2, MaterialSource.SHEET, 2, 2)])
    _, trace = FillerExperimental().optimize(problem)
    assert trace.source_switches == 1
    switches = [a for a in trace.attempts if a["decision"] == "skip_temporarily"]
    assert any(a["piece_id"] == 2 and a["material_id"] == 1 for a in switches)


def test_remnants_precede_sheets_and_incompatible_material_is_never_used():
    problem = _problem([(1, 2, 2, 1)], [(2, MaterialSource.SHEET, 4, 4),
                                       (1, MaterialSource.REMNANT, 2, 2)])
    result, _ = FillerExperimental().optimize(problem)
    assert result.placements[0].stock.source is MaterialSource.REMNANT
    assert all(p.piece.material_key == p.stock.material_key for p in result.placements)


def test_material_and_thickness_groups_remain_compatible():
    from experiments.optimization.loader import load_problem
    problem = load_problem("EXP-COMPLEX-001")
    result, _ = FillerExperimental().optimize(problem)
    assert result.placed_units == result.total_units
    assert all(p.piece.glass_type_id == p.stock.glass_type_id for p in result.placements)
    assert all(p.piece.thickness_mm == p.stock.thickness_mm for p in result.placements)


def test_separation_margin_rotation_and_non_overlap_are_delegated_to_layout():
    problem = _problem([(1, 3, 2, 1), (2, 3, 2, 1)], [(1, MaterialSource.SHEET, 8, 5)],
                       separation=1, margin=1, step=90)
    result, _ = FillerExperimental().optimize(problem)
    assert result.placed_units == 2
    assert all(p.x_mm >= 1 and p.y_mm >= 1 for p in result.placements)
    assert result.placements[1].x_mm - result.placements[0].x_mm >= 4


def test_rotation_and_determinism():
    problem = _problem([(1, 3, 2, 1)], [(1, MaterialSource.SHEET, 2, 3)])
    first, first_trace = FillerExperimental().optimize(problem)
    second, second_trace = FillerExperimental().optimize(problem)
    assert first.placements == second.placements
    assert first_trace == second_trace
    assert first.placements[0].rotation_deg == 90


def test_frozen_case_input_is_not_mutated():
    from experiments.optimization.loader import read_case, build_problem
    data = read_case("EXP-MEDIUM-001")
    before = repr(data)
    problem = build_problem(data)
    FillerExperimental().optimize(problem)
    assert repr(data) == before
