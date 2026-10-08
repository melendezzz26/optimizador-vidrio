import pytest
from unittest.mock import Mock
from app.modules.orders.application.use_cases import CreateOrderUseCase
from app.modules.orders.domain.exceptions import InvalidOrderException, InvalidGeometryException

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
    piezas = [
        {"tipo_forma": "RECTANGULO", "cantidad": 1, "width_mm": 100, "height_mm": 200},
        {"tipo_forma": "CIRCUNFERENCIA", "cantidad": 2, "radius_mm": 50},
        {"tipo_forma": "POLIGONO_CONVEXO", "cantidad": 1, "vertices_mm": [[0,0], [100,0], [0,100]]}
    ]

    order_id = use_case.execute(1, 1, 6.0, piezas)

    assert order_id == 123
    mock_repo.create_order.assert_called_once()
    _, kwargs = mock_repo.create_order.call_args
    # It passes positional args actually
    args = mock_repo.create_order.call_args.args
    assert args[0] == 1
    assert args[1] == 1
    assert args[2] == 6.0
    validadas = args[3]
    assert len(validadas) == 3
    assert validadas[0]["area_mm2"] == 20000

def test_create_order_invalid_catalog(use_case, mock_repo):
    mock_repo.validate_catalog.return_value = False
    with pytest.raises(InvalidOrderException, match="Combinación inválida"):
        use_case.execute(1, 99, 10.0, [{"tipo_forma": "RECTANGULO", "cantidad": 1, "width_mm": 100, "height_mm": 200}])

def test_create_order_zero_cantidad(use_case):
    with pytest.raises(InvalidOrderException, match="cantidad debe ser mayor a 0"):
        use_case.execute(1, 1, 6.0, [{"tipo_forma": "RECTANGULO", "cantidad": 0, "width_mm": 100, "height_mm": 200}])

def test_create_order_invalid_geometry(use_case):
    with pytest.raises(InvalidGeometryException):
        use_case.execute(1, 1, 6.0, [{"tipo_forma": "RECTANGULO", "cantidad": 1, "width_mm": -100, "height_mm": 200}])


def test_empty_order_cannot_be_persisted(use_case, mock_repo):
    with pytest.raises(InvalidOrderException):
        use_case.execute(1, 1, 6, [])
    mock_repo.create_order.assert_not_called()
