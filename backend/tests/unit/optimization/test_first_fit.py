import ast
from dataclasses import replace
from decimal import Decimal as D
from pathlib import Path
from unittest.mock import patch

import pytest

from app.modules.optimization.application.dto import OptimizationRun, RunStatus
from app.modules.optimization.application.first_fit import calculate_first_fit
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.placement import SheetLayout
from app.modules.optimization.domain.problem import MaterialSource, OptimizationConfig, StockCandidate
from app.modules.optimization.domain.rotation import RasterCache, RasterPreparationError
from app.modules.optimization.domain.run_geometry import PreparedRunGeometry
from app.modules.optimization.infrastructure.stock_adapter import InventoryStockAdapter
from app.modules.optimization.presentation.run_serialization import placement_response, run_response
from tests.unit.optimization.test_preparation import piece, prepare_persisted_problem
from tests.unit.optimization.test_stock import Inventory, sheet, remnant


def config(**changes):
    return OptimizationConfig(**(dict(resolution_mm=D(1), margin_mm=D(0), separation_mm=D(0), angular_step_deg=D(90)) | changes))


def stock(identifier=1, width=6, height=4, source=MaterialSource.SHEET, physical=1, glass=1, thickness=6, geometry=None):
    return StockCandidate(source=source, material_id=identifier, physical_unit_index=physical,
                          glass_type_id=glass, thickness_mm=D(thickness), area_mm2=D(width * height),
                          geometry=geometry or dict(type="RECTANGULO", width_mm=width, height_mm=height))


def problem(rows=None, candidates=None, cfg=None):
    rows = [piece()] if rows is None else rows
    result = prepare_persisted_problem(sorted({p["id_pedido"] for p in rows}), rows, cfg or config())
    candidates = [stock()] if candidates is None else candidates
    return replace(result, groups=tuple(replace(g, stock_candidates=tuple(c for c in candidates if c.material_key == g.key))
                                        for g in result.groups))


def optimize(rows=None, candidates=None, cfg=None, callback=None):
    return FirstFitOptimizer().optimize(problem(rows, candidates, cfg), callback)


def test_one_piece_complete_traceable_and_serializable_without_metrics():
    result = optimize()
    assert result.complete and result.placed_units == result.total_units == 1
    placement, = result.placements
    assert (placement.x_mm, placement.y_mm, placement.rotation_deg) == (D(0), D(0), D(0))
    assert (placement.piece.order_id, placement.piece.piece_id, placement.piece.unit_index) == (1, 1, 1)
    wire = placement_response(placement, result.problem.config).model_dump(mode="json")
    assert wire["x_mm"] == "0" and wire["stock_unit_index"] == 1
    assert run_response(OptimizationRun(optimization_id=1, status=RunStatus.COMPLETED, result=result)).metrics is None


def test_small_manually_inspectable_row_major_pattern_and_replay_checks():
    # Three 2x2 squares on a 4x4 sheet: AA BB / AA BB / CC .. / CC .. .
    result = optimize([piece(width=2, height=2, quantity=3)], [stock(width=4, height=4)])
    assert result.complete
    assert [(p.x_mm, p.y_mm, p.rotation_deg) for p in result.placements] == [(0, 0, 0), (2, 0, 0), (0, 2, 0)]
    cache = RasterCache()
    layout = SheetLayout.empty(cache.material(result.placements[0].stock, D(1)))
    for p in result.placements:
        mask = cache.orientations(p.piece, D(1), D(90))[0].orientation.mask
        assert layout.check(mask, int(p.y_mm), int(p.x_mm)).is_valid
        layout = layout.place(mask, int(p.y_mm), int(p.x_mm))
    assert sum(bits.bit_count() for bits in layout.occupied) == 12


def test_no_fit_incomplete_not_confirmable_no_metrics_or_fake_placement():
    result = optimize([piece(width=7, height=7)])
    assert not result.complete and result.placed_units == 0 and result.total_units == 1
    assert result.metrics is None and result.unplaced_units == result.problem.units
    observed = OptimizationRun(optimization_id=1, status=RunStatus.NO_SOLUTION, result=result)
    assert not observed.confirmable
    with pytest.raises(ValueError):
        OptimizationRun(optimization_id=1, status=RunStatus.COMPLETED, result=result)


def test_partial_retained_and_smaller_units_still_attempted_after_no_fit():
    result = optimize([piece(1, width=20, height=20), piece(2, width=2, height=2), piece(3, width=10, height=10)])
    assert result.placed_units == 1 and result.total_units == 3 and not result.complete
    assert result.placements[0].piece.piece_id == 2
    assert [u.piece_id for u in result.unplaced_units] == [1, 3]


def test_first_candidate_wins_without_trying_later_better_sheet():
    first, better = stock(5, width=9, height=9), stock(6, width=4, height=2)
    # Source lookup during search, distinct from preparing all base masks.
    with patch.object(PreparedRunGeometry, "material", autospec=True, side_effect=PreparedRunGeometry.material) as material:
        result = optimize(candidates=[first, better])
        assert result.placements[0].stock == first
        assert material.call_count == 1


def test_remnant_has_priority_even_if_input_includes_sheet_first():
    sheet_candidate, remnant_candidate = stock(), stock(9, source=MaterialSource.REMNANT)
    assert optimize(candidates=[sheet_candidate, remnant_candidate]).placements[0].stock == remnant_candidate


def test_fallback_from_too_small_remnant_to_sheet():
    small = stock(9, width=1, height=1, source=MaterialSource.REMNANT)
    assert optimize(candidates=[small, stock()]).placements[0].stock.source is MaterialSource.SHEET


def test_rotation_allows_fit_and_first_rotation_wins():
    result = optimize([piece(width=3, height=2)], [stock(width=2, height=3)])
    assert result.complete and result.placements[0].rotation_deg == D(90)
    assert result.placements[0].geometry["width_mm"] == 2


def test_nonquarter_rotation_and_polygon_circle_pieces():
    result = optimize([piece(width=6, height=1)], [stock(width=5, height=5)], config(angular_step_deg=D(45)))
    assert result.complete and result.placements[0].rotation_deg == 45
    assert result.placements[0].geometry["type"] == "POLIGONO_CONVEXO"
    circle = piece(2) | dict(tipo_forma="CIRCUNFERENCIA", geometria=dict(type="CIRCUNFERENCIA", radius_mm=1), area_mm2=D("3.14"))
    polygon = piece(3) | dict(tipo_forma="POLIGONO_CONVEXO", geometria=dict(type="POLIGONO_CONVEXO", vertices_mm=[[-2, -2], [0, -2], [-2, 0]]), area_mm2=D(2))
    result = optimize([circle, polygon], [stock(width=5, height=5)], config(angular_step_deg=D(5)))
    assert result.complete and result.placements[0].rotation_deg == 0
    assert result.placements[1].geometry["vertices_mm"][0] == (0, 0)


def test_candidate_before_rotation_not_global_best_angle():
    result = optimize([piece(width=3, height=2)], [stock(1, width=2, height=3), stock(2, width=3, height=2)])
    assert result.placements[0].stock.material_id == 1 and result.placements[0].rotation_deg == 90


def test_margin_exact_and_just_too_large():
    cfg = config(margin_mm=D(1))
    result = optimize([piece(width=2, height=2)], [stock(width=4, height=4)], cfg)
    assert result.complete and (result.placements[0].x_mm, result.placements[0].y_mm) == (1, 1)
    assert not optimize([piece(width=3, height=2)], [stock(width=4, height=4)], cfg).complete


def test_large_margin_fails_without_unbounded_morphology():
    assert not optimize(cfg=config(margin_mm=D("1e20"))).complete


def test_separation_requires_empty_cell_between_squares():
    rows = [piece(width=2, height=2, quantity=2)]
    result = optimize(rows, [stock(width=5, height=2)], config(separation_mm=D(1)))
    assert [(p.x_mm, p.y_mm) for p in result.placements] == [(0, 0), (3, 0)]
    assert not optimize(rows, [stock(width=4, height=2)], config(separation_mm=D(1))).complete


def test_nonintegral_and_sub_epsilon_distances_round_up_exactly():
    rows = [piece(width=2, height=2, quantity=2)]
    result = optimize(rows, [stock(width=5, height=2)], config(separation_mm=D("0.00000000001")))
    assert result.complete and result.placements[1].x_mm == 3
    result = optimize([piece(width=2, height=2)], [stock(width=6, height=6)], config(margin_mm=D("1.00000000001")))
    assert result.complete and result.placements[0].x_mm == 2


@pytest.mark.parametrize("width,height,fits", [(4, 2, True), (4.1, 2, False), (4, 2.1, False)])
def test_exact_and_fractional_bounds(width, height, fits):
    assert optimize([piece(width=width, height=height)], [stock(width=4, height=2)]).complete is fits


def test_irregular_remnant_bbox_cannot_approve_outside_triangle():
    triangle = stock(8, width=4, height=4, source=MaterialSource.REMNANT,
                     geometry=dict(type="POLIGONO_CONVEXO", vertices_mm=[[0, 0], [4, 0], [0, 4]]))
    assert not optimize([piece(width=3, height=3)], [triangle]).complete
    result = optimize([piece(width=1, height=1, quantity=4)], [triangle])
    assert result.complete
    for p in result.placements:
        assert p.x_mm + p.y_mm + 2 <= 4  # every square's farthest corner is inside x+y<=4
    assert optimize([piece(width=3, height=3)], [triangle, stock()]).placements[0].stock.source is MaterialSource.SHEET


def test_circle_remnant_checks_interior_not_just_diameter():
    circle = stock(9, source=MaterialSource.REMNANT, width=6, height=6,
                   geometry=dict(type="CIRCUNFERENCIA", radius_mm=3))
    result = optimize([piece(width=2, height=2)], [circle])
    assert result.complete
    assert (result.placements[0].x_mm, result.placements[0].y_mm) == (1, 1)
    assert not optimize([piece(width=5, height=5)], [circle]).complete


def test_sheet_quantity_layouts_independent_and_third_physical_unit_unused():
    result = optimize([piece(width=2, height=2, quantity=3)],
                      [stock(5, width=2, height=2, physical=i) for i in range(1, 5)])
    assert result.complete
    assert [p.stock.physical_unit_index for p in result.placements] == [1, 2, 3]
    assert [(p.x_mm, p.y_mm) for p in result.placements] == [(0, 0)] * 3
    assert len(result.materials_used) == 3


def test_multiple_orders_materials_and_thickness_no_cross_placement_determinism():
    rows = [piece(1, order=2, glass=2), piece(2, order=1, thickness="5.5"), piece(3, order=2)]
    candidates = [stock(1, glass=2), stock(2, thickness="5.5"), stock(3)]
    result = optimize(rows, candidates)
    assert result.complete and result.problem.order_ids == (1, 2)
    assert all(p.piece.material_key == p.stock.material_key for p in result.placements)
    assert result == optimize(rows[::-1], candidates)


def test_vertical_slice_persisted_snapshots_inventory_dtos_no_mutation_or_repeated_queries():
    source = Inventory([remnant(8)], [sheet(5, ancho_mm=D(4), alto_mm=D(2), cantidad=2)])
    before = repr((source.remnants, source.sheets))
    rows = [piece(1, order=1, quantity=2), piece(2, order=2)]
    result = calculate_first_fit([2, 1], rows, config(), InventoryStockAdapter(source))
    assert result.complete and result.total_units == 3
    assert source.reads == 1 and source.calls == 2
    assert repr((source.remnants, source.sheets)) == before


def test_empty_stock_and_live_internal_events_are_real_not_failed_attempts():
    events = []
    result = optimize([piece(quantity=2)], [], callback=events.append)
    assert not result.complete
    assert [e.kind for e in events] == ["group_started", "piece_started", "piece_started", "group_completed"]
    assert all(e.placed_units == 0 for e in events)
    events.clear()
    result = optimize([piece(quantity=2)], callback=events.append)
    assert result.complete
    assert [e.kind for e in events] == ["group_started", "piece_started", "piece_placed", "piece_started", "piece_placed", "group_completed"]
    assert [e.placed_units for e in events] == [0, 0, 1, 1, 2, 2]
    assert [e.placement for e in events if e.kind == "piece_placed"] == list(result.placements)


def test_error_is_not_silently_reported_as_no_fit():
    with pytest.raises(RasterPreparationError):
        optimize(cfg=config(resolution_mm=D("0.10000000000000000001")))


def test_domain_has_no_application_framework_or_database_imports():
    domain = Path(__file__).resolve().parents[3] / "app/modules/optimization/domain"
    for path in domain.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom):
                assert not any(forbidden in (node.module or "") for forbidden in
                               ("sqlalchemy", "fastapi", "supabase", "infrastructure", "application"))
            if isinstance(node, ast.Import):
                assert all(name.name.split('.')[0] not in {"sqlalchemy", "fastapi", "supabase"} for name in node.names)
