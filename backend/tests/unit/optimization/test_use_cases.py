from copy import deepcopy
from unittest.mock import Mock, patch

import pytest

from app.modules.optimization.application.errors import (
    InvalidRasterInput, OptimizationNotFoundError, OptimizationStateError, RasterBudgetExceeded,
)
from app.modules.optimization.application.resource_policy import RasterBudget, estimate_grid
from app.modules.optimization.application.use_cases import StartOptimizationUseCase, RasterizeOrderPieceUseCase
from app.modules.optimization.domain.rasterizer import rasterize_geometry
from app.modules.optimization.infrastructure.orders_adapter import OrdersOptimizationAdapter
from app.modules.orders.application.ports import OrderMutationResult

PIECE = dict(id_pedido=10, id_pieza=25, id_tipo_vidrio=7, espesor_mm=6, cantidad=5,
             tipo_forma="RECTANGULO", geometria=dict(type="RECTANGULO", width_mm=100, height_mm=50))
BUDGET = RasterBudget(10_000, 1000, 128, 262_144)


@pytest.fixture
def gateway():
    repo = Mock()
    repo.get_order.return_value = dict(id_pedido=10, estado="EN_OPTIMIZACION", piezas=[deepcopy(PIECE)])
    def start(identifier, validate):
        validate(repo.get_order.return_value)
        return OrderMutationResult.UPDATED
    repo.start_optimization.side_effect = start
    return OrdersOptimizationAdapter(repo)


def test_start_validates_once_and_returns_minimal_response_without_raster(gateway):
    with patch("app.modules.optimization.application.use_cases.rasterize_geometry") as raster:
        assert StartOptimizationUseCase(gateway, BUDGET).execute(10) == {
            "id_pedido": 10, "estado": "EN_OPTIMIZACION"}
    raster.assert_not_called()
    gateway.repository.start_optimization.assert_called_once()


@pytest.mark.parametrize("result,error", [
    (OrderMutationResult.NOT_FOUND, OptimizationNotFoundError),
    (OrderMutationResult.STATE_CONFLICT, OptimizationStateError),
])
def test_start_missing_or_conflict_never_reports_success(gateway, result, error):
    gateway.repository.start_optimization.side_effect = None
    gateway.repository.start_optimization.return_value = result
    with pytest.raises(error):
        StartOptimizationUseCase(gateway, BUDGET).execute(10)


@pytest.mark.parametrize("pieces", [[], [PIECE | {"cantidad": 0}], [PIECE | {"id_pedido": 11}],
                                      [PIECE | {"geometria": {"type": "OTHER"}}]])
def test_start_rejects_empty_invalid_or_inconsistent_pieces(gateway, pieces):
    gateway.repository.get_order.return_value["piezas"] = pieces
    with pytest.raises(InvalidRasterInput):
        StartOptimizationUseCase(gateway, BUDGET).execute(10)


def test_start_checks_budget_before_validation_or_raster(gateway):
    gateway.repository.get_order.return_value["piezas"] = [PIECE | {
        "geometria": dict(type="RECTANGULO", width_mm=10000, height_mm=10000)}]
    with pytest.raises(RasterBudgetExceeded):
        StartOptimizationUseCase(gateway, BUDGET).execute(10)


@pytest.mark.parametrize("identifier", [True, 0, -1, 1.2, "10", 2147483648])
def test_invalid_id_never_accesses_repository(gateway, identifier):
    with pytest.raises(InvalidRasterInput):
        StartOptimizationUseCase(gateway, BUDGET).execute(identifier)
    gateway.repository.start_optimization.assert_not_called()


def test_raster_quantity_five_calls_domain_once_and_never_mutates(gateway):
    with patch("app.modules.optimization.application.use_cases.rasterize_geometry", wraps=rasterize_geometry) as raster:
        result = RasterizeOrderPieceUseCase(gateway, BUDGET).execute(10, 25, 5)
    raster.assert_called_once_with(PIECE["geometria"], 5)
    assert result.piece["cantidad"] == 5
    assert (result.mask.row_count, result.mask.columns) == (10, 20)
    gateway.repository.start_optimization.assert_not_called()
    assert [c[0] for c in gateway.repository.mock_calls] == ["get_order"]


@pytest.mark.parametrize("state", ["PENDIENTE", "CANCELADO", "OPTIMIZADO", "CONFIRMADO"])
def test_raster_requires_started_order(gateway, state):
    gateway.repository.get_order.return_value["estado"] = state
    with pytest.raises(OptimizationStateError):
        RasterizeOrderPieceUseCase(gateway, BUDGET).execute(10, 25, 5)


def test_raster_missing_order(gateway):
    gateway.repository.get_order.return_value = None
    with pytest.raises(OptimizationNotFoundError):
        RasterizeOrderPieceUseCase(gateway, BUDGET).execute(10, 25, 5)


@pytest.mark.parametrize("pieces", [[], [PIECE | {"id_pedido": 11}], [PIECE | {"id_pieza": 26}]])
def test_raster_missing_or_foreign_piece_is_not_found(gateway, pieces):
    gateway.repository.get_order.return_value["piezas"] = pieces
    with pytest.raises(OptimizationNotFoundError):
        RasterizeOrderPieceUseCase(gateway, BUDGET).execute(10, 25, 5)


@pytest.mark.parametrize("resolution", [0, -1, True, "5", None, float("inf"), float("nan")])
def test_invalid_resolution_never_reads_or_rasterizes(gateway, resolution):
    with pytest.raises(InvalidRasterInput):
        RasterizeOrderPieceUseCase(gateway, BUDGET).execute(10, 25, resolution)
    gateway.repository.get_order.assert_not_called()


def test_budget_rejects_before_domain(gateway):
    with patch("app.modules.optimization.application.use_cases.rasterize_geometry") as raster:
        with pytest.raises(RasterBudgetExceeded):
            RasterizeOrderPieceUseCase(gateway, BUDGET).execute(10, 25, 0.01)
    raster.assert_not_called()


@pytest.mark.parametrize("geometry,resolution", [
    (dict(type="RECTANGULO", width_mm=802, height_mm=1), 5),
    (dict(type="RECTANGULO", width_mm=10.0000004, height_mm=0.001), 5),
    (dict(type="CIRCUNFERENCIA", radius_mm=10.0000003), 5),
    (dict(type="POLIGONO_CONVEXO", vertices_mm=[[-2.1, -5], [8.90000001, -5], [-2.1, 5]]), 2),
    (dict(type="RECTANGULO", width_mm=7.00000049, height_mm=2.1), 0.7),
    (dict(type="RECTANGULO", width_mm=7.00000051, height_mm=2.1), 0.7),
    (dict(type="CIRCUNFERENCIA", radius_mm=12.3456), 0.7),
    (dict(type="POLIGONO_CONVEXO", vertices_mm=[[123.1, -70.4], [134.1, -70.4], [123.1, -60.4]]), 0.35),
])
def test_preflight_matches_existing_domain_rounding(geometry, resolution):
    mask = rasterize_geometry(geometry, resolution)
    assert estimate_grid(geometry, resolution) == (mask.row_count, mask.columns)


def test_budget_boundary_and_next_cell():
    geometry = dict(type="RECTANGULO", width_mm=100, height_mm=100)
    assert BUDGET.check(geometry, 1) == (100, 100)
    with pytest.raises(RasterBudgetExceeded):
        BUDGET.check(geometry | {"width_mm": 101}, 1)


@pytest.mark.parametrize("geometry,resolution", [
    (dict(type="RECTANGULO", width_mm=1e308, height_mm=1), 1e-300),
    (dict(type="CIRCUNFERENCIA", radius_mm=1e308), 5),
    (dict(type="RECTANGULO", width_mm=1, height_mm=1), 5e-324),
    (dict(type="CIRCUNFERENCIA", radius_mm=10**308), 5),
])
def test_extreme_finite_inputs_fail_preflight_safely(geometry, resolution):
    with pytest.raises(RasterBudgetExceeded):
        BUDGET.check(geometry, resolution)


def test_vertex_and_axis_and_payload_budgets():
    with pytest.raises(RasterBudgetExceeded, match="vértices"):
        BUDGET.check(dict(type="POLIGONO_CONVEXO", vertices_mm=[[0, 0]] * 129), 5)
    with pytest.raises(RasterBudgetExceeded):
        BUDGET.check(dict(type="RECTANGULO", width_mm=1001, height_mm=1), 1)
    with pytest.raises(RasterBudgetExceeded, match="respuesta"):
        RasterBudget(10000, 1000, 128, 100).check(PIECE["geometria"], 5)


def test_production_budget_boundary_and_next_row_or_axis():
    from app.modules.optimization.application.resource_policy import DEFAULT_RASTER_BUDGET
    geometry = dict(type="RECTANGULO", width_mm=1000, height_mm=1000)
    assert DEFAULT_RASTER_BUDGET.check(geometry, 1) == (1000, 1000)
    with pytest.raises(RasterBudgetExceeded):
        DEFAULT_RASTER_BUDGET.check(geometry | {"height_mm": 1000.000001}, 1)
    assert DEFAULT_RASTER_BUDGET.check(dict(type="RECTANGULO", width_mm=2440, height_mm=1), 1) == (1, 2440)
    with pytest.raises(RasterBudgetExceeded):
        DEFAULT_RASTER_BUDGET.check(dict(type="RECTANGULO", width_mm=2441, height_mm=1), 1)
