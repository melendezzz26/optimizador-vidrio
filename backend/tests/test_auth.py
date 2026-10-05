"""Pruebas del flujo de autenticación (HU-001 T03)."""
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.shared.security.tokens import ALGORITHM, SECRET_KEY
from app.routers.auth import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)

PASSWORD = "Vidrio2026!"


def login(username, password):
    return client.post("/api/auth/login", json={"username": username, "password": password})


# --- Credenciales válidas ---
def test_login_valido_devuelve_token_y_rol():
    r = login("admin", PASSWORD)
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["usuario"]["rol"] == "Administrador"
    assert "password_hash" not in body["usuario"]


def test_login_ignora_mayusculas_y_espacios_en_usuario():
    assert login("  Operario ", PASSWORD).status_code == 200


def test_token_permite_acceder_a_ruta_protegida():
    token = login("almacenero", PASSWORD).json()["access_token"]
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["rol"] == "Almacenero"


# --- Credenciales inválidas ---
def test_password_incorrecta_es_rechazada():
    r = login("admin", "otra-clave")
    assert r.status_code == 401
    assert r.json()["detail"] == "Usuario o contraseña incorrectos."


def test_usuario_inexistente_usa_el_mismo_mensaje():
    r = login("noexiste", PASSWORD)
    assert r.status_code == 401
    assert r.json()["detail"] == "Usuario o contraseña incorrectos."


def test_usuario_inactivo_es_rechazado():
    assert login("inactivo", PASSWORD).status_code == 403


def test_campos_vacios_son_rechazados():
    assert login("", PASSWORD).status_code == 422
    assert login("admin", "").status_code == 422


# --- Rutas protegidas ---
def test_ruta_protegida_sin_token():
    assert client.get("/api/auth/me").status_code == 401


def test_token_alterado_es_rechazado():
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer token.falso.123"})
    assert r.status_code == 401


def test_token_expirado_es_rechazado():
    vencido = jwt.encode(
        {"sub": "1", "username": "admin", "rol": "Administrador",
         "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        SECRET_KEY, algorithm=ALGORITHM,
    )
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {vencido}"})
    assert r.status_code == 401
    assert "expiró" in r.json()["detail"]
