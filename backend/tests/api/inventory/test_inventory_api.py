from datetime import datetime, timezone
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from main import app
from app.modules.inventory.application.dto import TipoVidrioData, PlanchaData, RetazoData
from app.modules.inventory.presentation.dependencies import get_inventory_service
from tests.auth_support import token_for, use_in_memory_accounts

class FakeInventoryService:
    def list_tipos_vidrio(self):
        return [TipoVidrioData(id_tipo_vidrio=1, nombre="Claro", descripcion=None, estado=True,
                              espesores_mm=(Decimal("3"), Decimal("5.5"), Decimal("12")))]

    def create_tipo_vidrio(self, data):
        from app.modules.inventory.domain.exceptions import InventoryConflictError
        if data.nombre == "Duplicado":
            raise InventoryConflictError("Duplicado")
        return TipoVidrioData(id_tipo_vidrio=2, nombre=data.nombre, descripcion=data.descripcion, estado=True)

    def list_planchas(self):
        return [PlanchaData(
            id_plancha=1, ancho_mm=Decimal("1000"), alto_mm=Decimal("500"), espesor_mm=Decimal("5"),
            cantidad=10, estado=True, fecha_registro=datetime.now(timezone.utc), id_tipo_vidrio=1
        )]

    def create_plancha(self, data):
        from app.modules.inventory.domain.exceptions import InventoryValidationError
        if data.cantidad == 0:
            raise InventoryValidationError("cantidad 0 no permitida")
        if data.espesor_mm == Decimal("7"):
            raise InventoryValidationError("espesor no permitido")
        return PlanchaData(
            id_plancha=2, ancho_mm=data.ancho_mm, alto_mm=data.alto_mm, espesor_mm=data.espesor_mm,
            cantidad=data.cantidad, estado=True, fecha_registro=datetime.now(timezone.utc),
            id_tipo_vidrio=data.id_tipo_vidrio
        )

    def update_plancha(self, id_plancha, data):
        from app.modules.inventory.domain.exceptions import InventoryNotFoundError
        if id_plancha == 999:
            raise InventoryNotFoundError("Not found")
        return PlanchaData(
            id_plancha=id_plancha, ancho_mm=Decimal("1000"), alto_mm=Decimal("500"), espesor_mm=Decimal("5"),
            cantidad=data.cantidad if data.cantidad is not None else 10,
            estado=data.estado if data.estado is not None else True,
            fecha_registro=datetime.now(timezone.utc), id_tipo_vidrio=1
        )

    def list_retazos(self):
        return [RetazoData(
            id_retazo=1, codigo="EXISTENTE", espesor_mm=Decimal("4"), geometria={"type": "RECTANGULO", "width_mm": 100, "height_mm": 100},
            area_mm2=Decimal("10000.00"), estado=True, fecha_registro=datetime.now(timezone.utc),
            id_tipo_vidrio=1, id_ejecucion_origen=None
        )]

    def create_retazo(self, data):
        from app.modules.inventory.domain.exceptions import InventoryConflictError
        if data.codigo == "DUPLICADO":
            raise InventoryConflictError("Duplicado")
        return RetazoData(
            id_retazo=2, codigo=data.codigo, espesor_mm=data.espesor_mm, geometria=data.geometria,
            area_mm2=Decimal("10.00"), estado=True, fecha_registro=datetime.now(timezone.utc),
            id_tipo_vidrio=data.id_tipo_vidrio, id_ejecucion_origen=None
        )

    def update_retazo(self, id_retazo, data):
        return RetazoData(
            id_retazo=id_retazo, codigo=data.codigo if data.codigo is not None else "UPDATED", espesor_mm=Decimal("4"),
            geometria=data.geometria if data.geometria is not None else {"type": "RECTANGULO", "width_mm": 100, "height_mm": 100},
            area_mm2=Decimal("10000.00"), estado=data.estado if data.estado is not None else False,
            fecha_registro=datetime.now(timezone.utc), id_tipo_vidrio=1, id_ejecucion_origen=None
        )

def get_fake_inventory_service():
    return FakeInventoryService()

@pytest.fixture(autouse=True)
def override_dependency():
    app.dependency_overrides[get_inventory_service] = get_fake_inventory_service
    use_in_memory_accounts(app)
    yield
    app.dependency_overrides.clear()

client = TestClient(app)

def make_token(rol: str) -> str:
    return token_for(rol)

def test_auth_sin_token():
    response = client.get("/api/inventory/tipos-vidrio")
    assert response.status_code == 401

def test_operario_get_permitido():
    response = client.get("/api/inventory/tipos-vidrio", headers={"Authorization": f"Bearer {make_token('Operario')}"})
    assert response.status_code == 200
    assert response.json()[0]["espesores_mm"] == [3, 5.5, 12]

def test_operario_post_prohibido():
    response = client.post("/api/inventory/tipos-vidrio", json={"nombre": "Nuevo"}, headers={"Authorization": f"Bearer {make_token('Operario')}"})
    assert response.status_code == 403

def test_almacenero_escritura_permitida():
    response = client.post("/api/inventory/tipos-vidrio", json={"nombre": "Nuevo"}, headers={"Authorization": f"Bearer {make_token('Almacenero')}"})
    assert response.status_code == 201
    assert response.json()["nombre"] == "Nuevo"

def test_administrador_escritura_permitida():
    response = client.post("/api/inventory/tipos-vidrio", json={"nombre": "Admin"}, headers={"Authorization": f"Bearer {make_token('Administrador')}"})
    assert response.status_code == 201

def test_tipos_vidrio_errores():
    token = make_token('Administrador')
    assert client.post("/api/inventory/tipos-vidrio", json={"descripcion": "D"}, headers={"Authorization": f"Bearer {token}"}).status_code == 422
    assert client.post("/api/inventory/tipos-vidrio", json={"nombre": "A", "extra": 1}, headers={"Authorization": f"Bearer {token}"}).status_code == 422
    assert client.post("/api/inventory/tipos-vidrio", json={"nombre": "Duplicado"}, headers={"Authorization": f"Bearer {token}"}).status_code == 409

def test_planchas():
    token = make_token('Administrador')
    headers = {"Authorization": f"Bearer {token}"}

    # GET
    assert client.get("/api/inventory/planchas", headers=headers).status_code == 200

    # POST valido
    res = client.post("/api/inventory/planchas", json={"ancho_mm": 1000, "alto_mm": 500, "espesor_mm": 5, "cantidad": 2, "id_tipo_vidrio": 1}, headers=headers)
    assert res.status_code == 201

    # POST errores
    assert client.post("/api/inventory/planchas", json={"ancho_mm": 1000, "alto_mm": 500, "espesor_mm": 5, "cantidad": 0, "id_tipo_vidrio": 1}, headers=headers).status_code == 422
    assert client.post("/api/inventory/planchas", json={"ancho_mm": -10, "alto_mm": 500, "espesor_mm": 5, "cantidad": 2, "id_tipo_vidrio": 1}, headers=headers).status_code == 422
    assert client.post("/api/inventory/planchas", json={"ancho_mm": 1000, "alto_mm": 500, "espesor_mm": 7, "cantidad": 2, "id_tipo_vidrio": 1}, headers=headers).status_code == 422
    assert client.post("/api/inventory/planchas", json={"ancho_mm": 1000, "alto_mm": 500, "espesor_mm": 5, "cantidad": 2, "id_tipo_vidrio": 1, "estado": False}, headers=headers).status_code == 422

    # PATCH valido
    res = client.patch("/api/inventory/planchas/1", json={"cantidad": 5}, headers=headers)
    assert res.status_code == 200

    # PATCH cantidad=0 y estado=false
    res = client.patch("/api/inventory/planchas/1", json={"cantidad": 0}, headers=headers)
    assert res.status_code == 200
    assert res.json()["cantidad"] == 0
    res = client.patch("/api/inventory/planchas/1", json={"estado": False}, headers=headers)
    assert res.status_code == 200
    assert res.json()["estado"] is False

    # PATCH errores
    assert client.patch("/api/inventory/planchas/999", json={"cantidad": 5}, headers=headers).status_code == 404
    assert client.patch("/api/inventory/planchas/1", json={}, headers=headers).status_code == 422
    assert client.patch("/api/inventory/planchas/1", json={"cantidad": None}, headers=headers).status_code == 422

def test_retazos():
    token = make_token('Administrador')
    headers = {"Authorization": f"Bearer {token}"}

    # GET
    assert client.get("/api/inventory/retazos", headers=headers).status_code == 200

    # POST valido
    res = client.post("/api/inventory/retazos", json={"codigo": "R1", "espesor_mm": 4, "geometria": {"type": "RECTANGULO", "width_mm": 10, "height_mm": 5}, "id_tipo_vidrio": 1}, headers=headers)
    assert res.status_code == 201

    res = client.post("/api/inventory/retazos", json={"codigo": "R2", "espesor_mm": 4, "geometria": {"type": "CIRCUNFERENCIA", "radius_mm": 10}, "id_tipo_vidrio": 1}, headers=headers)
    assert res.status_code == 201

    res = client.post("/api/inventory/retazos", json={"codigo": "R3", "espesor_mm": 4, "geometria": {"type": "POLIGONO_CONVEXO", "vertices_mm": [[0,0], [10,0], [0,10]]}, "id_tipo_vidrio": 1}, headers=headers)
    assert res.status_code == 201

    # Vertice con 1 coordenada o 3 coordenadas
    assert client.post("/api/inventory/retazos", json={"codigo": "R3", "espesor_mm": 4, "geometria": {"type": "POLIGONO_CONVEXO", "vertices_mm": [[0,0], [10], [0,10]]}, "id_tipo_vidrio": 1}, headers=headers).status_code == 422
    assert client.post("/api/inventory/retazos", json={"codigo": "R3", "espesor_mm": 4, "geometria": {"type": "POLIGONO_CONVEXO", "vertices_mm": [[0,0], [10,0,1], [0,10]]}, "id_tipo_vidrio": 1}, headers=headers).status_code == 422

    # Geometria errores
    assert client.post("/api/inventory/retazos", json={"codigo": "R4", "espesor_mm": 4, "geometria": {"type": "OTRO"}, "id_tipo_vidrio": 1}, headers=headers).status_code == 422
    assert client.post("/api/inventory/retazos", json={"codigo": "R5", "espesor_mm": 4, "geometria": {"type": "RECTANGULO", "width_mm": 10, "height_mm": 5, "extra": 1}, "id_tipo_vidrio": 1}, headers=headers).status_code == 422

    # Propiedades prohibidas en POST
    assert client.post("/api/inventory/retazos", json={"codigo": "R6", "espesor_mm": 4, "geometria": {"type": "CIRCUNFERENCIA", "radius_mm": 10}, "id_tipo_vidrio": 1, "area_mm2": 100}, headers=headers).status_code == 422
    assert client.post("/api/inventory/retazos", json={"codigo": "R7", "espesor_mm": 4, "geometria": {"type": "CIRCUNFERENCIA", "radius_mm": 10}, "id_tipo_vidrio": 1, "id_ejecucion_origen": 1}, headers=headers).status_code == 422

    # Duplicado codigo
    assert client.post("/api/inventory/retazos", json={"codigo": "DUPLICADO", "espesor_mm": 4, "geometria": {"type": "CIRCUNFERENCIA", "radius_mm": 10}, "id_tipo_vidrio": 1}, headers=headers).status_code == 409

    # PATCH
    res = client.patch("/api/inventory/retazos/1", json={"estado": False}, headers=headers)
    assert res.status_code == 200
    assert client.patch("/api/inventory/retazos/1", json={}, headers=headers).status_code == 422
    assert client.patch("/api/inventory/retazos/1", json={"codigo": None}, headers=headers).status_code == 422

def test_openapi():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/inventory/tipos-vidrio" in paths
    assert "/api/inventory/planchas" in paths
    assert "/api/inventory/planchas/{id_plancha}" in paths
    assert "/api/inventory/retazos" in paths
    assert "/api/inventory/retazos/{id_retazo}" in paths
