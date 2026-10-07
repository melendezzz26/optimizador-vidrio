import pytest
from unittest.mock import patch
from fastapi import status
from fastapi.testclient import TestClient
from app.main import app
from app.modules.authentication.domain.user import AuthenticatedUser
from app.modules.authentication.presentation.dependencies import get_current_user

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_auth():
    user = AuthenticatedUser(id_usuario=1, role="Administrador")
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)

@patch("app.modules.orders.application.use_cases.CreateOrderUseCase.execute")
def test_create_order_201(mock_execute, client, mock_auth):
    mock_execute.return_value = 100
    payload = {
        "id_tipo_vidrio": 1,
        "espesor_mm": 6.0,
        "piezas": [
            {
                "tipo_forma": "RECTANGULO",
                "cantidad": 1,
                "width_mm": 100.0,
                "height_mm": 200.0
            }
        ]
    }
    response = client.post("/api/orders", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["id_pedido"] == 100

def test_create_order_401_no_auth(client):
    payload = {
        "id_tipo_vidrio": 1,
        "espesor_mm": 6.0,
        "piezas": [{"tipo_forma": "RECTANGULO", "cantidad": 1, "width_mm": 100.0, "height_mm": 200.0}]
    }
    response = client.post("/api/orders", json=payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@patch("app.modules.orders.application.use_cases.CreateOrderUseCase.execute")
def test_create_order_422_invalid_schema(mock_execute, client, mock_auth):
    payload = {
        "id_tipo_vidrio": 1,
        "espesor_mm": 6.0,
        "piezas": []  # empty pieces should fail Pydantic validation
    }
    response = client.post("/api/orders", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
