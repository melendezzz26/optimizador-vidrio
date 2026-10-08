import pytest
from fastapi.testclient import TestClient

# Asegúrate de importar tu app real (ajusta "main" si tu archivo principal se llama distinto)
from main import app 
from app.modules.orders.presentation.dependencies import get_create_order_use_case
from app.modules.authentication.presentation.dependencies import require_permission
from app.modules.orders.presentation.router import permiso_gestionar_pedidos

client = TestClient(app)

# --- 1. Mocks (Simuladores) ---
# Simulamos un usuario logueado para no necesitar un Token JWT real en la prueba
class MockAuthenticatedUser:
    user_id = 1

# Simulamos tu caso de uso para no tocar la base de datos (aislamos el test al router)
class MockCreateOrderUseCase:
    def execute(self, id_usuario, id_tipo_vidrio, espesor_mm, piezas_raw):
        # Simulamos que la lógica de negocio funcionó y nos devolvió el ID del nuevo pedido
        return 99 

app.dependency_overrides[get_create_order_use_case] = lambda: MockCreateOrderUseCase()
app.dependency_overrides[permiso_gestionar_pedidos] = lambda: MockAuthenticatedUser()


# --- 2. Casos de Prueba ---

def test_crear_pedido_exitoso():
    """Prueba de caja negra para un escenario válido."""
    payload = {
        "id_tipo_vidrio": 1,
        "espesor_mm": 6.0,
        "piezas": [
            {
                "tipo_forma": "RECTANGULO",
                "cantidad": 2,
                "width_mm": 1000.0,
                "height_mm": 500.0
            }
        ]
    }
    
    response = client.post("/api/orders/", json=payload)
    
    # Validamos que el API responda 201 Created y devuelva la estructura correcta
    assert response.status_code == 201
    assert response.json() == {"id_pedido": 99, "estado": "PENDIENTE"}

def test_crear_pedido_sin_piezas():
    """Prueba de validación: Un pedido no puede ir sin piezas."""
    payload = {
        "id_tipo_vidrio": 1,
        "espesor_mm": 6.0,
        "piezas": []
    }
    
    response = client.post("/api/orders/", json=payload)
    
    # FastAPI (Pydantic) o tu caso de uso debería rebotarlo por validación
    assert response.status_code == 422