"""Pruebas del detector aislado; no tocan optimizadores ni datos productivos."""
from decimal import Decimal
import hashlib
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from app.modules.optimization.domain.placement import PlacementIssue, SheetLayout
from app.modules.optimization.domain.raster_mask import RasterMask
from app.modules.optimization.domain.rotation import discrete_angles
from experiments.optimization.hole_filling.lab import (
    CASE_DIR,
    _components,
    _domain_boundary_rows,
    feasible_anchor_map,
    physical_free_regions,
    prepare_case,
    read_case,
)


def _maps_for_pending(setup, unit, stock, layout):
    return tuple(
        feasible_anchor_map(layout, unit, stock, oriented)
        for oriented in setup.prepared.orientations(unit)
    )


def test_internal_hole_is_separate_from_exterior_component():
    full = (1 << 7) - 1
    material = RasterMask(1.0, 7, (full,) * 7)
    ring = (0, 0, 0b0011100, 0b0010100, 0b0011100, 0, 0)
    layout = SheetLayout(material, (full,) * 7, ring, ring, 0)

    regions = physical_free_regions(layout)

    holes = [region for region in regions if region.region_type == "internal_hole"]
    exterior = [region for region in regions if region.region_type == "exterior"]
    assert len(holes) == 1
    assert holes[0].area_cells == 1
    assert len(exterior) == 1


def test_circle_case_has_a_candidate_specific_pocket():
    setup = prepare_case("HF-DIAGNOSTIC-001")
    unit = setup.pending[0]
    stock = setup.stocks_by_id[901]
    anchor_maps = _maps_for_pending(setup, unit, stock, setup.layouts[stock.identity])

    assert any(anchor.pockets for anchor in anchor_maps)
    pocket = next(pocket for anchor in anchor_maps for pocket in anchor.pockets)
    anchor_map = next(anchor for anchor in anchor_maps if anchor.pockets)
    row, column = min(pocket.cells, key=lambda cell: (cell[1], cell[0]))
    oriented = next(item for item in setup.prepared.orientations(unit)
                    if item.orientation.rotation_deg == anchor_map.rotation_deg)
    assert setup.layouts[stock.identity].check(oriented.orientation.mask, row, column).is_valid
    assert setup.layouts[stock.identity].place(oriented.orientation.mask, row, column) is not setup.layouts[stock.identity]


def test_triangle_case_has_pocket_and_keeps_five_degree_motor_grid():
    setup = prepare_case("HF-DIAGNOSTIC-002")
    unit = setup.pending[0]
    stock = setup.stocks_by_id[902]
    anchor_maps = _maps_for_pending(setup, unit, stock, setup.layouts[stock.identity])
    step = setup.problem.config.angular_step_deg

    assert len(discrete_angles(step)) == 72
    assert discrete_angles(step)[1] == Decimal(5)
    assert any(anchor.pockets for anchor in anchor_maps)
    five_degree = setup.prepared._cache._orientation(unit, setup.problem.config.resolution_mm, Decimal(5))
    assert five_degree.rotation_deg == Decimal(5)


def test_convex_polygon_case_detects_pocket_with_margin():
    setup = prepare_case("HF-DIAGNOSTIC-003")
    unit = setup.pending[0]
    stock = setup.stocks_by_id[903]
    layout = setup.layouts[stock.identity]
    anchor_maps = _maps_for_pending(setup, unit, stock, layout)
    zero = next(item for item in setup.prepared.orientations(unit)
                if item.orientation.rotation_deg == Decimal(0))

    assert any(anchor.pockets for anchor in anchor_maps)
    assert layout.check(zero.orientation.mask, 0, 0).issue is PlacementIssue.MARGIN


def test_negative_control_keeps_exterior_out_of_pocket_class():
    setup = prepare_case("HF-DIAGNOSTIC-004")
    unit = setup.pending[0]
    remnant = setup.stocks_by_id[904]
    remnant_layout = setup.layouts[remnant.identity]
    assert not any(anchor.pockets for anchor in _maps_for_pending(setup, unit, remnant, remnant_layout))

    sheet = setup.stocks_by_id[905]
    empty = SheetLayout.empty(
        setup.prepared.material(sheet),
        margin_mm=float(setup.problem.config.margin_mm),
        separation_mm=float(setup.problem.config.separation_mm),
    )
    assert not any(anchor.pockets for anchor in _maps_for_pending(setup, unit, sheet, empty))


def test_seed_layouts_are_valid_and_detection_does_not_mutate_snapshots():
    setup = prepare_case("HF-DIAGNOSTIC-001")
    units_before = tuple((unit.identity, unit.geometry, unit.area_mm2) for unit in setup.problem.units)
    stock_before = tuple((stock.identity, stock.geometry) for stock in setup.problem.groups[0].stock_candidates)
    layouts_before = {identity: (layout.occupied, layout.blocked) for identity, layout in setup.layouts.items()}
    unit = setup.pending[0]
    stock = setup.stocks_by_id[901]
    layout = setup.layouts[stock.identity]
    for oriented in setup.prepared.orientations(unit):
        feasible_anchor_map(layout, unit, stock, oriented)

    assert tuple((unit.identity, unit.geometry, unit.area_mm2) for unit in setup.problem.units) == units_before
    assert tuple((stock.identity, stock.geometry) for stock in setup.problem.groups[0].stock_candidates) == stock_before
    assert {identity: (layout.occupied, layout.blocked) for identity, layout in setup.layouts.items()} == layouts_before
    assert all(len(placement.piece.identity) == 2 for placement in setup.seed_placements)


def test_bit_parallel_anchor_map_matches_sheetlayout_check_at_every_origin():
    for case_id in (
        "HF-DIAGNOSTIC-001", "HF-DIAGNOSTIC-002",
        "HF-DIAGNOSTIC-003", "HF-DIAGNOSTIC-004",
    ):
        setup = prepare_case(case_id)
        unit = setup.pending[0]
        for stock in setup.problem.groups[0].stock_candidates:
            layout = setup.layouts.get(stock.identity)
            if layout is None:
                zeros = (0,) * setup.prepared.material(stock).row_count
                layout = SheetLayout.empty(
                    setup.prepared.material(stock),
                    margin_mm=float(setup.problem.config.margin_mm),
                    separation_mm=float(setup.problem.config.separation_mm),
                )
            for oriented in setup.prepared.orientations(unit):
                anchor = feasible_anchor_map(layout, unit, stock, oriented)
                assert anchor.positions_examined == anchor.rows * anchor.columns
                for row in range(anchor.rows):
                    for column in range(anchor.columns):
                        expected = layout.check(oriented.orientation.mask, row, column).is_valid
                        actual = bool(anchor.valid_rows[row] & (1 << column))
                        assert actual is expected, (case_id, row, column, oriented.orientation.rotation_deg)


def test_realistic_orders_are_frozen_compatible_and_have_no_seed_placements():
    intent = (CASE_DIR / "HF-REALISTIC-INTENT.md").read_text(encoding="utf-8")
    counts = {"HF-REALISTIC-001": 15, "HF-REALISTIC-002": 18, "HF-REALISTIC-003": 20}
    for case_id, expected_count in counts.items():
        case_path = CASE_DIR / f"{case_id}.json"
        case = read_case(case_id)
        assert len(case["pieces"]) == expected_count
        assert all(piece["role"] == "pending" for piece in case["pieces"])
        assert len(case["stocks"]) == 2
        assert {stock["source"] for stock in case["stocks"]} == {"RETAZO", "PLANCHA"}
        assert case["config"] == {
            "resolution_mm": 1, "angular_step_deg": 5,
            "margin_mm": 5, "separation_mm": 3,
        }
        assert all(stock["geometry"]["type"] == "RECTANGULO" for stock in case["stocks"])
        expected_hash = re.search(rf"{case_id}.*?([0-9a-f]{{64}})", intent).group(1)
        assert hashlib.sha256(case_path.read_bytes()).hexdigest() == expected_hash


def test_bit_row_exterior_flood_matches_reference_component_labels():
    for case_id in (
        "HF-DIAGNOSTIC-001", "HF-DIAGNOSTIC-002",
        "HF-DIAGNOSTIC-003", "HF-DIAGNOSTIC-004",
    ):
        setup = prepare_case(case_id)
        unit = setup.pending[0]
        stock = setup.problem.groups[0].stock_candidates[0]
        layout = setup.layouts.get(stock.identity)
        if layout is None:
            layout = SheetLayout.empty(
                setup.prepared.material(stock),
                margin_mm=float(setup.problem.config.margin_mm),
                separation_mm=float(setup.problem.config.separation_mm),
            )
        oriented = next(iter(setup.prepared.orientations(unit)))
        anchor = feasible_anchor_map(layout, unit, stock, oriented)
        boundary = _domain_boundary_rows(anchor.domain_rows, anchor.columns)
        expected_exterior = [0] * anchor.rows
        expected_pockets = [0] * anchor.rows
        for region in _components(anchor.valid_rows, anchor.columns):
            touches_edge = any(boundary[row] & (1 << column) for row, column in region.cells)
            target = expected_exterior if touches_edge else expected_pockets
            for row, column in region.cells:
                target[row] |= 1 << column
        assert tuple(expected_exterior) == anchor.exterior_rows
        assert tuple(expected_pockets) == anchor.pocket_rows
