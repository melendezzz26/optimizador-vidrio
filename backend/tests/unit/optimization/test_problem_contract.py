from dataclasses import FrozenInstanceError, replace
from decimal import Decimal

import pytest

from app.modules.optimization.application.dto import OptimizationRun, Progress, RunStatus
from app.modules.optimization.domain.placement import SheetLayout
from app.modules.optimization.domain.problem import (
    MaterialGroup, MaterialSource, OptimizationConfig, OptimizationProblem,
    OptimizationResult, PieceUnit, Placement, StockCandidate,
)
from app.modules.optimization.domain.rasterizer import rasterize_geometry, rasterize_material


@pytest.fixture
def contract():
    geometry = dict(type="RECTANGULO", width_mm=10, height_mm=5)
    unit = PieceUnit(order_id=10, piece_id=27, unit_index=1, glass_type_id=7,
                     thickness_mm=Decimal("6.00"), geometry=geometry, area_mm2=Decimal("50.00"))
    second = replace(unit, unit_index=2)
    stock = StockCandidate(source=MaterialSource.SHEET, material_id=5, physical_unit_index=1,
                           glass_type_id=7, thickness_mm=Decimal("6.00"),
                           geometry=dict(type="RECTANGULO", width_mm=100, height_mm=50), area_mm2=Decimal("5000"))
    config = OptimizationConfig(resolution_mm=Decimal("5"), margin_mm=Decimal("0"),
                                separation_mm=Decimal("0"), angular_step_deg=Decimal("5"))
    group = MaterialGroup(glass_type_id=7, thickness_mm=Decimal("6"), units=(unit, second), stock_candidates=(stock,))
    problem = OptimizationProblem(order_ids=(10,), config=config, groups=(group,))
    placement = Placement(piece=unit, stock=stock, x_mm=Decimal("0"), y_mm=Decimal("0"),
                          rotation_deg=Decimal("0"), geometry=geometry)
    return unit, second, stock, problem, placement


def test_piece_units_retain_traceability_without_expanding_quantity(contract):
    unit, second, _, problem, _ = contract
    assert unit.identity == (27, 1) and second.identity == (27, 2)
    assert unit.order_id == 10 and unit.material_key == (7, Decimal("6.00"))
    assert unit.shape_type == "RECTANGULO" and unit.area_mm2 == Decimal("50.00")
    assert problem.units == (unit, second)
    assert unit != second


def test_geometry_snapshot_is_detached_and_deeply_immutable(contract):
    source = dict(type="POLIGONO_CONVEXO", vertices_mm=[[-10, 0], [10, 0], [0, 20]])
    unit = replace(contract[0], geometry=source)
    source["vertices_mm"][0][0] = 999
    assert unit.geometry["vertices_mm"][0] == (-10, 0)
    with pytest.raises(TypeError):
        unit.geometry["vertices_mm"][0][0] = 7
    with pytest.raises(TypeError):
        unit.geometry["type"] = "RECTANGULO"
    with pytest.raises(FrozenInstanceError):
        unit.unit_index = 2


def test_groups_distinguish_glass_and_exact_thickness(contract):
    unit, _, stock, problem, _ = contract
    different_glass = replace(unit, piece_id=28, glass_type_id=8)
    different_thickness = replace(unit, piece_id=29, thickness_mm=Decimal("4"))
    groups = (problem.groups[0],
              MaterialGroup(glass_type_id=8, thickness_mm=6, units=(different_glass,)),
              MaterialGroup(glass_type_id=7, thickness_mm=4, units=(different_thickness,)))
    assert len({g.key for g in groups}) == 3
    assert replace(problem, groups=groups).units[-1] == different_thickness
    with pytest.raises(ValueError, match="match the material"):
        MaterialGroup(glass_type_id=7, thickness_mm=4, units=(unit,))
    with pytest.raises(ValueError, match="match the material"):
        MaterialGroup(glass_type_id=8, thickness_mm=6, units=(different_glass,), stock_candidates=(stock,))


def test_stock_distinguishes_source_and_multiple_units_of_same_row(contract):
    stock = contract[2]
    second_sheet = replace(stock, physical_unit_index=2)
    remnant = replace(stock, source=MaterialSource.REMNANT)
    assert len({stock.identity, second_sheet.identity, remnant.identity}) == 3
    assert stock.material_id == second_sheet.material_id == remnant.material_id == 5
    with pytest.raises(ValueError, match="exactly one"):
        replace(remnant, physical_unit_index=2)


def test_traceable_placement_composes_snapshots_and_preserves_geometric_domain(contract):
    unit, _, stock, _, placement = contract
    layout = SheetLayout.empty(rasterize_material(dict(stock.geometry), 5))
    mask = rasterize_geometry(dict(unit.geometry), 5)
    assert layout.check(mask, row=0, column=0).is_valid
    placed = layout.place(mask, row=0, column=0)
    assert placed.occupied != layout.occupied
    assert placement.piece is unit and placement.stock is stock
    assert placement.piece.identity == (27, 1)
    assert placement.stock.identity == (MaterialSource.SHEET, 5, 1)
    assert placement.x_mm == placement.y_mm == placement.rotation_deg == 0
    with pytest.raises(ValueError, match="incompatible"):
        replace(placement, stock=replace(stock, glass_type_id=8))


def test_result_complete_partial_and_empty_use_actual_placements(contract):
    unit, second, stock, problem, first = contract
    other = replace(first, piece=second, x_mm=Decimal("10"))
    complete = OptimizationResult(problem=problem, placements=(first, other))
    partial = replace(complete, placements=(first,))
    empty = replace(complete, placements=())
    assert complete.method == "FF" and complete.total_units == complete.placed_units == 2
    assert complete.complete and not complete.unplaced_units
    assert complete.materials_used == (stock,)  # One physical sheet, two piece placements.
    assert not partial.complete and partial.unplaced_units == (second,)
    assert empty.placed_units == 0 and empty.unplaced_units == (unit, second)
    assert empty.metrics is None and empty.computation_time_ms is None
    assert OptimizationRun(optimization_id=1, status=RunStatus.COMPLETED, result=complete).confirmable
    assert not OptimizationRun(optimization_id=1, status=RunStatus.NO_SOLUTION, result=partial).confirmable
    assert not OptimizationRun(optimization_id=1, status=RunStatus.COMPLETED, result=complete, confirmed=True).confirmable
    with pytest.raises(ValueError, match="COMPLETADA"):
        OptimizationRun(optimization_id=1, status=RunStatus.COMPLETED, result=partial)


@pytest.mark.parametrize("changes", [
    dict(unit_index=0), dict(piece_id=True), dict(thickness_mm=Decimal("NaN")),
    dict(thickness_mm=6.0), dict(area_mm2=Decimal("-1")),
    dict(geometry=dict(type="UNKNOWN")),
])
def test_invalid_unit_invariants_are_rejected(contract, changes):
    with pytest.raises(ValueError):
        replace(contract[0], **changes)


def test_duplicate_unknown_and_mutated_snapshots_cannot_fake_completeness(contract):
    unit, _, stock, problem, placement = contract
    with pytest.raises(ValueError, match="distinct requested"):
        OptimizationResult(problem=problem, placements=(placement, placement))
    with pytest.raises(ValueError, match="distinct requested"):
        OptimizationResult(problem=problem, placements=(replace(placement, piece=replace(unit, order_id=11)),))
    with pytest.raises(ValueError, match="stock"):
        OptimizationResult(problem=problem, placements=(replace(placement, stock=replace(stock, physical_unit_index=2)),))
    with pytest.raises(ValueError, match="selected orders"):
        replace(problem, order_ids=(11,))
    with pytest.raises(ValueError, match="Duplicate order"):
        replace(problem, order_ids=(10, 10))
    with pytest.raises(ValueError, match="Duplicate material"):
        replace(problem, groups=problem.groups * 2)
    with pytest.raises(ValueError, match="Duplicate physical"):
        replace(problem.groups[0], units=(unit, unit))
    with pytest.raises(ValueError, match="share its snapshot"):
        replace(problem, groups=(replace(problem.groups[0], units=(unit, replace(unit, unit_index=2, order_id=11))),),
                order_ids=(10, 11))


@pytest.mark.parametrize("changes", [dict(resolution_mm=0), dict(margin_mm=-1),
                                        dict(angular_step_deg=361), dict(separation_mm=Decimal("Infinity"))])
def test_configuration_has_no_defaults_and_rejects_invalid_measures(contract, changes):
    with pytest.raises(ValueError):
        replace(contract[3].config, **changes)


def test_progress_counts_accepted_units_and_never_attempts():
    assert Progress(placed_units=1, total_units=4).progress_pct == Decimal("25")
    with pytest.raises(ValueError):
        Progress(placed_units=5, total_units=4)
    with pytest.raises(ValueError):
        Progress(placed_units=0, total_units=0)


def test_multiorder_result_retains_two_physical_sheets_from_one_inventory_row(contract):
    unit, _, stock, problem, placement = contract
    other = replace(unit, order_id=11, piece_id=28)
    second_sheet = replace(stock, physical_unit_index=2)
    group = replace(problem.groups[0], units=(unit, other), stock_candidates=(stock, second_sheet))
    problem = replace(problem, order_ids=(10, 11), groups=(group,))
    result = OptimizationResult(problem=problem, placements=(
        placement, replace(placement, piece=other, stock=second_sheet),
    ))
    assert result.complete and result.problem.order_ids == (10, 11)
    assert len(result.materials_used) == 2
    assert {s.material_id for s in result.materials_used} == {5}
    assert {s.physical_unit_index for s in result.materials_used} == {1, 2}
    assert {p.piece.order_id for p in result.placements} == {10, 11}


@pytest.mark.parametrize("changes", [dict(x_mm=-1), dict(rotation_deg=360),
                                        dict(rotation_deg=Decimal("NaN")),
                                        dict(geometry=dict(type="POLIGONO_CONVEXO", vertices_mm=[[-5, 0], [5, 0], [0, 10]]))])
def test_invalid_placement_coordinates_cannot_enter_reconstructed_pattern(contract, changes):
    with pytest.raises(ValueError):
        replace(contract[4], **changes)


def test_physical_stock_duplicates_cannot_be_opened_as_distinct_candidates(contract):
    _, _, stock, problem, _ = contract
    with pytest.raises(ValueError, match="Duplicate physical"):
        replace(problem.groups[0], stock_candidates=(stock, stock))
