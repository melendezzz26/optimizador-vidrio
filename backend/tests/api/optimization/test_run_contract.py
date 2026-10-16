"""Contract fixtures only: no route, transport, DB or optimizer mocks."""
import copy
import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from app.modules.optimization.application.dto import OptimizationRun, RunStatus
from app.modules.optimization.domain.problem import (
    MaterialGroup, MaterialSource, OptimizationConfig, OptimizationMetrics,
    OptimizationProblem, OptimizationResult, PieceUnit, Placement, StockCandidate,
)
from app.modules.optimization.presentation.run_schemas import (
    ConfirmResponseV1, ErrorResponseV1, OptimizationEventV1, RunRequestV1, RunResponseV1,
)
from app.modules.optimization.presentation.run_serialization import run_response

FIXTURE_PATH = Path(__file__).with_name("fixtures") / "s1_contract_v1.json"


@pytest.fixture
def examples():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def run():
    unit = PieceUnit(order_id=10, piece_id=27, unit_index=1, glass_type_id=7, thickness_mm=Decimal("6.00"),
                     geometry=dict(type="RECTANGULO", width_mm=10, height_mm=5), area_mm2=Decimal("50.00"))
    stock = StockCandidate(source=MaterialSource.SHEET, material_id=5, physical_unit_index=1,
                           glass_type_id=7, thickness_mm=Decimal("6.00"),
                           geometry=dict(type="RECTANGULO", width_mm=100, height_mm=50), area_mm2=Decimal("5000"))
    config = OptimizationConfig(resolution_mm=5, margin_mm=0, separation_mm=0, angular_step_deg=5)
    problem = OptimizationProblem(order_ids=(10,), config=config, groups=(
        MaterialGroup(glass_type_id=7, thickness_mm=Decimal("6.00"), units=(unit,), stock_candidates=(stock,)),
    ))
    placement = Placement(piece=unit, stock=stock, x_mm=0, y_mm=0, rotation_deg=0, geometry=unit.geometry)
    metrics = OptimizationMetrics(utilization_pct=1, waste_mm2=4950, new_sheets_used=1,
                                  recoverable_remnant_mm2=0, material_area_mm2=5000, placed_piece_area_mm2=Decimal("50.00"))
    result = OptimizationResult(problem=problem, placements=(placement,), metrics=metrics, computation_time_ms=3)
    return OptimizationRun(optimization_id=101, status=RunStatus.COMPLETED, result=result)


def test_versioned_examples_cover_start_eight_event_types_result_and_confirmation(examples):
    assert RunRequestV1.model_validate(examples["request"]).order_ids == [10]
    event_adapter = TypeAdapter(OptimizationEventV1)
    events = examples["success_events"] + [examples["failed_event"]]
    assert len({event["event"] for event in events}) == 8
    for event in events:
        model = event_adapter.validate_python(event)
        assert event_adapter.validate_json(model.model_dump_json()) == model
    assert [e["sequence"] for e in examples["success_events"]] == list(range(1, 8))
    assert RunResponseV1.model_validate(examples["result"]).confirmable
    assert ConfirmResponseV1.model_validate(examples["confirmation"]).confirmed
    assert ErrorResponseV1.model_validate(examples["conflict"]).detail.code == "STOCK_CONFLICT"


def test_model_serialization_matches_shared_fixture_exactly_and_round_trips(run, examples):
    response = run_response(run)
    assert response.model_dump(mode="json") == examples["result"]
    assert RunResponseV1.model_validate_json(response.model_dump_json()) == response
    assert response.placements[0].stock_unit_index == run.result.placements[0].stock.physical_unit_index


@pytest.mark.parametrize("order_ids", [[], [10, 10], [True], [0], [-1], [2147483648], ["10"]])
def test_start_requires_explicit_distinct_valid_ids(order_ids):
    with pytest.raises(ValidationError):
        RunRequestV1(order_ids=order_ids)


@pytest.mark.parametrize("extra", [dict(configuracion={}), dict(geometria={}), dict(metodo="BF")])
def test_client_cannot_override_persisted_geometry_or_config(extra):
    with pytest.raises(ValidationError):
        RunRequestV1(order_ids=[10], **extra)


def test_partial_and_no_stock_results_are_reconstructible_and_not_confirmable(run):
    first = run.result.placements[0]
    other_unit = replace(first.piece, unit_index=2)
    group = replace(run.result.problem.groups[0], units=(first.piece, other_unit))
    problem = replace(run.result.problem, groups=(group,))
    partial = replace(run.result, problem=problem)
    response = run_response(replace(run, result=partial, status=RunStatus.NO_SOLUTION))
    assert response.placed_units == 1 and response.total_units == 2 and response.progress_pct == 50
    assert not response.completo and not response.confirmable
    assert response.unplaced_units[0].unit_index == 2 and response.unplaced_units[0].reason == "NO_FIT"
    assert response.materials_used[0].material_id == first.stock.material_id
    empty_problem = replace(problem, groups=(replace(group, stock_candidates=()),))
    empty = OptimizationResult(problem=empty_problem, placements=(), computation_time_ms=0)
    empty_response = run_response(replace(run, result=empty, status=RunStatus.NO_SOLUTION))
    assert empty_response.metrics is None and not empty_response.metrics_available
    assert not empty_response.materials_used and empty_response.progress_pct == 0
    assert RunResponseV1.model_validate_json(empty_response.model_dump_json()) == empty_response


@pytest.mark.parametrize("status,reason", [(RunStatus.RUNNING, "PENDING"), (RunStatus.FAILED, "INTERRUPTED")])
def test_get_distinguishes_running_and_failed_from_no_solution(run, status, reason):
    result = replace(run.result, placements=(), metrics=None, computation_time_ms=None)
    response = run_response(replace(run, status=status, result=result))
    assert not response.confirmable and response.unplaced_units[0].reason == reason
    assert response.tiempo_computacional_ms is None


@pytest.mark.parametrize("mutation", [
    lambda data: data.update(progress_pct="25"),
    lambda data: data.update(completo=False),
    lambda data: data.update(confirmable=False),
    lambda data: data["placements"].append(copy.deepcopy(data["placements"][0])),
    lambda data: data["placements"][0].update(id_pedido=11),
    lambda data: data["placements"][0].update(stock_unit_index=2),
    lambda data: data["placements"][0].update(espesor_mm="4"),
    lambda data: data["placements"][0].update(resolution_mm="10"),
    lambda data: data["placements"][0].update(rotation_deg="360"),
    lambda data: data["metrics"].update(aprovechamiento_pct="101"),
    lambda data: data["metrics"].update(area_material_total_mm2="0"),
    lambda data: data.update(metrics_available=False),
    lambda data: data.update(metodo="WF"),
])
def test_result_rejects_forged_progress_traceability_and_invalid_metrics(examples, mutation):
    data = examples["result"]
    mutation(data)
    with pytest.raises(ValidationError):
        RunResponseV1.model_validate(data)


def test_event_rejects_unknown_event_unsafe_extra_fields_and_naive_time(examples):
    adapter = TypeAdapter(OptimizationEventV1)
    event = examples["failed_event"]
    for change in (dict(event="invented"), dict(occurred_at="2026-10-16T15:00:00"), dict(sequence=0)):
        with pytest.raises(ValidationError):
            adapter.validate_python({**event, **change})
    event["data"]["stack_trace"] = "internal detail"
    with pytest.raises(ValidationError):
        adapter.validate_python(event)


def test_decimal_measures_preserve_precision_and_never_serialize_as_binary_floats(run):
    placement = replace(run.result.placements[0], x_mm=Decimal("0.1234567890123456789012345678"))
    response = run_response(replace(run, result=replace(run.result, placements=(placement,))))
    wire = json.loads(response.model_dump_json())
    assert wire["placements"][0]["x_mm"] == "0.1234567890123456789012345678"
    assert wire["configuracion"]["resolucion_raster_mm"] == "5"
    with pytest.raises(ValidationError):
        RunResponseV1.model_validate({**wire, "progress_pct": 100.0})


def test_geometry_supports_circle_polygon_and_integer_coordinates_above_js_safe_range(run):
    origin = 9007199254740993
    polygon = dict(type="POLIGONO_CONVEXO", vertices_mm=[[origin, 0], [origin + 10, 0], [origin, 10]])
    for geometry in (dict(type="CIRCUNFERENCIA", radius_mm=5), polygon):
        old = run.result.placements[0]
        unit = replace(old.piece, geometry=geometry)
        group = replace(run.result.problem.groups[0], units=(unit,))
        problem = replace(run.result.problem, groups=(group,))
        local_geometry = (dict(type="POLIGONO_CONVEXO", vertices_mm=[[0, 0], [10, 0], [0, 10]])
                          if geometry["type"] == "POLIGONO_CONVEXO" else geometry)
        placement = replace(old, piece=unit, geometry=local_geometry)
        response = run_response(replace(run, result=replace(run.result, problem=problem, placements=(placement,))))
        assert response.groups[0].units[0].tipo_forma == geometry["type"]
        wire = json.loads(response.model_dump_json())
        assert wire["groups"][0]["units"][0]["geometria"] == geometry
        assert wire["placements"][0]["geometria"] == local_geometry


def test_confirmation_cannot_describe_double_consumption(examples):
    data = examples["confirmation"]
    data["materials_consumed"] *= 2
    with pytest.raises(ValidationError):
        ConfirmResponseV1.model_validate(data)


def test_live_placement_rejects_mismatched_material_and_false_progress(examples):
    event = examples["success_events"][3]
    event["data"]["material"]["stock_unit_index"] = 2
    adapter = TypeAdapter(OptimizationEventV1)
    with pytest.raises(ValidationError):
        adapter.validate_python(event)
    event["data"]["material"]["stock_unit_index"] = 1
    event["data"].update(placed_units=0, progress_pct="0")
    with pytest.raises(ValidationError):
        adapter.validate_python(event)


def test_no_solution_terminal_and_unavailable_metrics_are_valid_contracts(examples):
    adapter = TypeAdapter(OptimizationEventV1)
    terminal = examples["success_events"][-1]
    terminal["data"].update(estado="SIN_SOLUCION", completo=False, placed_units=0, progress_pct="0")
    assert adapter.validate_python(terminal).data.estado == "SIN_SOLUCION"
    metrics = examples["success_events"][-2]
    metrics["data"].update(metrics_available=False, metrics=None)
    assert adapter.validate_python(metrics).data.metrics is None


def test_derived_progress_round_trip_for_nonterminating_decimal_ratio(run):
    unit = run.result.placements[0].piece
    group = replace(run.result.problem.groups[0], units=(unit, replace(unit, unit_index=2), replace(unit, unit_index=3)))
    problem = replace(run.result.problem, groups=(group,))
    response = run_response(replace(run, status=RunStatus.NO_SOLUTION, result=replace(run.result, problem=problem)))
    assert response.progress_pct == Decimal(1) / Decimal(3) * 100
    assert RunResponseV1.model_validate_json(response.model_dump_json()) == response
