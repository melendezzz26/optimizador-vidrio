from decimal import Decimal
from unittest.mock import Mock, call

import pytest

from app.modules.orders.application.ports import OrderMutationResult
from app.modules.orders.application.use_cases import (
    CancelOrderUseCase,
    CreateOrderUseCase,
    GetOrderUseCase,
    UpdateOrderUseCase,
)
from app.modules.orders.domain.exceptions import (
    InvalidGeometryException,
    InvalidOrderException,
    OrderNotFoundException,
    OrderStateConflictException,
)


RECTANGLE = {"id_tipo_vidrio": 1, "espesor_mm": 6, "tipo_forma": "RECTANGULO",
             "cantidad": 1, "width_mm": 100, "height_mm": 200}


@pytest.fixture
def mock_repo():
    repo = Mock()
    repo.validate_catalog.return_value = True
    repo.create_order.return_value = 123
    return repo


@pytest.fixture
def use_case(mock_repo):
    return CreateOrderUseCase(mock_repo)


def test_create_order_multiple_pieces(use_case, mock_repo):
    pieces = [RECTANGLE,
              {"id_tipo_vidrio": 1, "espesor_mm": 6.0, "tipo_forma": "CIRCUNFERENCIA", "cantidad": 2, "radius_mm": 50},
              {"id_tipo_vidrio": 2, "espesor_mm": 4, "tipo_forma": "POLIGONO_CONVEXO", "cantidad": 3,
               "vertices_mm": [[0, 0], [100, 0], [0, 100]]}]
    assert use_case.execute(1, pieces) == 123
    assert mock_repo.validate_catalog.call_args_list == [call(1, Decimal("6")), call(2, Decimal("4"))]
    mock_repo.create_order.assert_called_once()
    user_id, validated = mock_repo.create_order.call_args.args
    assert user_id == 1
    assert len(validated) == 3 and validated[0]["area_mm2"] == 20000
    assert [(p["id_tipo_vidrio"], p["espesor_mm"], p["cantidad"]) for p in validated] == [(1, 6, 1), (1, 6, 2), (2, 4, 3)]


def test_create_order_invalid_catalog(use_case, mock_repo):
    mock_repo.validate_catalog.side_effect = [True, False]
    with pytest.raises(InvalidOrderException, match="Combinación inválida"):
        use_case.execute(1, [RECTANGLE, RECTANGLE | {"id_tipo_vidrio": 99}])
    mock_repo.create_order.assert_not_called()


def test_create_order_zero_cantidad(use_case, mock_repo):
    with pytest.raises(InvalidOrderException, match="cantidad debe ser mayor a 0"):
        use_case.execute(1, [RECTANGLE, RECTANGLE | {"cantidad": 0}])
    mock_repo.create_order.assert_not_called()


def test_create_order_invalid_geometry(use_case, mock_repo):
    with pytest.raises(InvalidGeometryException):
        use_case.execute(1, [RECTANGLE, RECTANGLE | {"width_mm": -100}])
    mock_repo.create_order.assert_not_called()


def test_empty_order_cannot_be_persisted(use_case, mock_repo):
    with pytest.raises(InvalidOrderException):
        use_case.execute(1, [])
    mock_repo.create_order.assert_not_called()


@pytest.mark.parametrize("change", [{"id_tipo_vidrio": True}, {"espesor_mm": True}, {"espesor_mm": float("inf")}, {"espesor_mm": 0}])
def test_application_rejects_invalid_pair_before_catalog(use_case, mock_repo, change):
    with pytest.raises(InvalidOrderException):
        use_case.execute(1, [RECTANGLE | change])
    mock_repo.validate_catalog.assert_not_called()
    mock_repo.create_order.assert_not_called()


def test_get_order_returns_complete_data_without_writes(mock_repo):
    mock_repo.get_order.return_value = {"id_pedido": 123, "piezas": [RECTANGLE]}
    assert GetOrderUseCase(mock_repo).execute(123) == mock_repo.get_order.return_value
    mock_repo.get_order.assert_called_once_with(123)
    mock_repo.create_order.assert_not_called()


def test_get_missing_order(mock_repo):
    mock_repo.get_order.return_value = None
    with pytest.raises(OrderNotFoundException):
        GetOrderUseCase(mock_repo).execute(123)


def test_update_pending_order_maps_repository_success(mock_repo):
    mock_repo.update_order.return_value = OrderMutationResult.UPDATED
    UpdateOrderUseCase(mock_repo).execute(123, [RECTANGLE])
    mock_repo.update_order.assert_called_once()
    mock_repo.get_order.assert_not_called()


def test_update_missing_order_raises_not_found(mock_repo):
    mock_repo.update_order.return_value = OrderMutationResult.NOT_FOUND
    with pytest.raises(OrderNotFoundException):
        UpdateOrderUseCase(mock_repo).execute(123, [RECTANGLE])
    mock_repo.update_order.assert_called_once()
    mock_repo.get_order.assert_not_called()


def test_update_concurrent_state_change_result_raises_conflict(mock_repo):
    mock_repo.update_order.return_value = OrderMutationResult.STATE_CONFLICT
    with pytest.raises(OrderStateConflictException):
        UpdateOrderUseCase(mock_repo).execute(123, [RECTANGLE])
    mock_repo.update_order.assert_called_once()
    mock_repo.get_order.assert_not_called()


def test_cancel_pending_order_maps_repository_success(mock_repo):
    mock_repo.cancel_order.return_value = OrderMutationResult.UPDATED
    CancelOrderUseCase(mock_repo).execute(123)
    mock_repo.cancel_order.assert_called_once_with(123)
    mock_repo.get_order.assert_not_called()


def test_cancel_missing_order_raises_not_found(mock_repo):
    mock_repo.cancel_order.return_value = OrderMutationResult.NOT_FOUND
    with pytest.raises(OrderNotFoundException):
        CancelOrderUseCase(mock_repo).execute(123)
    mock_repo.cancel_order.assert_called_once_with(123)
    mock_repo.get_order.assert_not_called()


def test_cancel_state_conflict_comes_from_repository(mock_repo):
    mock_repo.cancel_order.return_value = OrderMutationResult.STATE_CONFLICT
    with pytest.raises(OrderStateConflictException):
        CancelOrderUseCase(mock_repo).execute(123)
    mock_repo.cancel_order.assert_called_once_with(123)
    mock_repo.get_order.assert_not_called()
