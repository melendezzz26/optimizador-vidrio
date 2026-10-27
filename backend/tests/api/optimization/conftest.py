from tests.integration.postgres_support import isolated_postgres  # noqa: F401
from tests.orders_support import orders_database, session_factory  # noqa: F401

import pytest


@pytest.fixture
def authenticated(client, create_user, password):
    identifier = create_user("O70000001")
    response = client.post("/api/auth/login", json={"username": "O70000001", "password": password})
    assert response.status_code == 200
    return identifier, {"Authorization": "Bearer " + response.json()["access_token"]}


@pytest.fixture
def order(client, authenticated):
    pieces = [
        dict(id_tipo_vidrio=7, espesor_mm=6, cantidad=5, tipo_forma="RECTANGULO", width_mm=800, height_mm=600),
        dict(id_tipo_vidrio=8, espesor_mm=4, cantidad=2, tipo_forma="CIRCUNFERENCIA", radius_mm=50),
        dict(id_tipo_vidrio=9, espesor_mm=6, cantidad=1, tipo_forma="POLIGONO_CONVEXO",
             vertices_mm=[[-10, -10], [90, -10], [-10, 90]]),
    ]
    response = client.post("/api/orders", json={"id_cliente": 41, "piezas": pieces}, headers=authenticated[1])
    assert response.status_code == 201, response.text
    return client.get(f"/api/orders/{response.json()['id_pedido']}", headers=authenticated[1]).json()


@pytest.fixture(autouse=True)
def run_admission():
    """TA-037 T03: cada prueba empieza con una admisión limpia (sin plazas de pruebas anteriores)."""
    from main import app
    from app.modules.optimization.infrastructure.in_process_admission import InProcessRunAdmission
    from app.modules.optimization.presentation.run_routes import get_run_admission
    admission = InProcessRunAdmission()
    app.dependency_overrides[get_run_admission] = lambda: admission
    yield admission
    app.dependency_overrides.pop(get_run_admission, None)