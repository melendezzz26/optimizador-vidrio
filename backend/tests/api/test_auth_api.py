"""API de autenticación de extremo a extremo sobre una base de prueba (SPEC-HU-001)."""
import importlib.util
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy import update

from app.models import Usuario
from app.modules.authentication.presentation.dependencies import get_user_reader
from app.shared.security import create_access_token
from app.shared.security.tokens import ALGORITHM, SECRET_KEY
from main import app

INVALID_CREDENTIALS = "Usuario o contraseña incorrectos."
ADMIN = "F70000001"
WAREHOUSE = "A70000002"
OPERATOR = "O70000003"
INACTIVE = "I70000004"


@pytest.fixture
def users(create_user) -> dict[str, int]:
    return {
        ADMIN: create_user(ADMIN, "Administrador", first_names="Fabiola", last_names="Quispe"),
        WAREHOUSE: create_user(WAREHOUSE, "Almacenero"),
        OPERATOR: create_user(OPERATOR, "Operario"),
        INACTIVE: create_user(INACTIVE, "Operario", active=False),
    }


def login(client, username, password):
    return client.post("/api/auth/login", json={"username": username, "password": password})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def token_for(client, username, password):
    return login(client, username, password).json()["access_token"]


# --- Inicio de sesión válido (CA-02, CA-03, CA-08) ---

def test_valid_login_returns_token_and_user(client, users, password):
    response = login(client, ADMIN, password)

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["usuario"] == {
        "id_usuario": users[ADMIN],
        "username": ADMIN,
        "nombre": "Fabiola Quispe",
        "rol": "Administrador",
    }


@pytest.mark.parametrize("typed", ["f70000001", "  F70000001  ", " f70000001"])
def test_username_is_normalized_before_login(client, users, password, typed):
    response = login(client, typed, password)
    assert response.status_code == 200
    assert response.json()["usuario"]["username"] == ADMIN


def test_login_response_never_exposes_private_data(client, users, password, password_hash):
    text = login(client, ADMIN, password).text
    assert password_hash not in text
    assert "password_hash" not in text
    assert "dni" not in text
    assert ADMIN[1:] not in text.replace(ADMIN, "")  # el DNI no aparece por separado


def test_token_contains_only_the_expected_claims(client, users, password):
    token = token_for(client, WAREHOUSE, password)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert set(payload) == {"sub", "username", "rol", "exp"}
    assert payload["sub"] == str(users[WAREHOUSE])
    assert payload["rol"] == "Almacenero"


# --- Formato del usuario (CA-04) ---

class CountingReader:
    """Lector que registra si alguien intentó consultar la base."""

    def __init__(self) -> None:
        self.calls = 0

    def find_by_username(self, username):
        self.calls += 1
        return None

    def find_by_id(self, user_id):
        self.calls += 1
        return None


@pytest.mark.parametrize(
    "username",
    [
        "70000001",              # DNI sin letra
        "F7000000",              # 7 dígitos
        "F700000011",            # 9 dígitos
        "FF0000001",             # dos letras
        "admin",
        "persona@example.test",  # correo
        "' OR 1=1 --",
        "   ",
    ],
)
def test_invalid_username_format_is_rejected_without_querying_the_database(client, username):
    reader = CountingReader()
    app.dependency_overrides[get_user_reader] = lambda: reader
    try:
        response = login(client, username, "cualquier-clave")
    finally:
        app.dependency_overrides.pop(get_user_reader, None)

    assert response.status_code == 422
    assert reader.calls == 0


def test_invalid_username_format_explains_the_expected_format(client):
    response = login(client, "admin", "cualquier-clave")
    assert "una letra seguida de 8 dígitos" in response.text


@pytest.mark.parametrize("body", [
    {"username": "", "password": "x"},
    {"username": ADMIN, "password": ""},
    {"username": ADMIN},
    {"password": "x"},
    {},
])
def test_missing_or_empty_fields_are_rejected(client, body):
    assert client.post("/api/auth/login", json=body).status_code == 422


# --- Credenciales incorrectas (CA-05, CA-06) ---

def test_wrong_password_is_rejected(client, users):
    response = login(client, ADMIN, "otra-clave")
    assert response.status_code == 401
    assert response.json()["detail"] == INVALID_CREDENTIALS


def test_unknown_user_gets_the_same_message(client, users, password):
    response = login(client, "Z99999999", password)
    assert response.status_code == 401
    assert response.json()["detail"] == INVALID_CREDENTIALS


def test_inactive_account_is_rejected_without_token(client, users, password):
    response = login(client, INACTIVE, password)
    assert response.status_code == 403
    assert "access_token" not in response.text


def test_inactive_account_with_wrong_password_looks_like_invalid_credentials(client, users):
    response = login(client, INACTIVE, "otra-clave")
    assert response.status_code == 401
    assert response.json()["detail"] == INVALID_CREDENTIALS


def test_password_longer_than_72_bytes_is_rejected_not_an_error(client, users):
    response = login(client, ADMIN, "a" * 100)
    assert response.status_code == 401
    assert response.json()["detail"] == INVALID_CREDENTIALS


def test_password_longer_than_the_field_limit_is_rejected(client, users):
    assert login(client, ADMIN, "a" * 129).status_code == 422


def test_account_with_a_corrupt_stored_hash_cannot_log_in(client, create_user, password):
    create_user("C70000005", stored_hash="no-es-un-hash-bcrypt")
    response = login(client, "C70000005", password)
    assert response.status_code == 401


# --- Rutas protegidas (CA-07) ---

def test_me_returns_the_current_user(client, users, password):
    response = client.get("/api/auth/me", headers=bearer(token_for(client, WAREHOUSE, password)))
    assert response.status_code == 200
    assert response.json() == {
        "id_usuario": users[WAREHOUSE],
        "username": WAREHOUSE,
        "rol": "Almacenero",
    }


def test_me_without_token_is_rejected(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Debes iniciar sesión."


@pytest.mark.parametrize("token", ["token.falso.123", "no-es-un-jwt"])
def test_me_with_a_malformed_token_is_rejected(client, token):
    assert client.get("/api/auth/me", headers=bearer(token)).status_code == 401


def test_me_with_a_token_signed_by_another_key_is_rejected(client, users):
    forged = jwt.encode(
        {"sub": str(users[ADMIN]), "username": ADMIN, "rol": "Administrador",
         "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        "otra-clave-que-no-es-la-del-backend-0123456789",
        algorithm=ALGORITHM,
    )
    assert client.get("/api/auth/me", headers=bearer(forged)).status_code == 401


def test_me_with_an_expired_token_is_rejected(client, users):
    expired = jwt.encode(
        {"sub": str(users[ADMIN]), "username": ADMIN, "rol": "Administrador",
         "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    response = client.get("/api/auth/me", headers=bearer(expired))
    assert response.status_code == 401
    assert "expiró" in response.json()["detail"]


def test_me_with_an_incomplete_token_is_rejected(client, users):
    incomplete = jwt.encode(
        {"sub": str(users[ADMIN]), "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    assert client.get("/api/auth/me", headers=bearer(incomplete)).status_code == 401


def test_me_rejects_the_token_after_the_account_is_deactivated(client, users, password, db_session):
    token = token_for(client, OPERATOR, password)
    db_session.execute(update(Usuario).where(Usuario.usuario == OPERATOR).values(estado=False))
    db_session.commit()

    assert client.get("/api/auth/me", headers=bearer(token)).status_code == 401


def test_me_rejects_a_token_of_an_account_that_does_not_exist(client):
    token = create_access_token(999, "Z99999999", "Administrador")
    assert client.get("/api/auth/me", headers=bearer(token)).status_code == 401


def test_me_returns_the_role_stored_in_the_database_not_the_token(client, users, password, db_session):
    token = token_for(client, OPERATOR, password)
    db_session.execute(update(Usuario).where(Usuario.usuario == OPERATOR).values(id_rol=2))
    db_session.commit()

    response = client.get("/api/auth/me", headers=bearer(token))
    assert response.status_code == 200
    assert response.json()["rol"] == "Almacenero"


# --- Configuración (CA-10) y CORS ---

@pytest.mark.parametrize("module", ["app.services.usuarios", "app.routers.auth", "app.core.security"])
def test_legacy_authentication_modules_were_removed(module):
    # Los usuarios en memoria y la clave por defecto vivían en estos módulos.
    try:
        found = importlib.util.find_spec(module)
    except ModuleNotFoundError:
        found = None  # tampoco existe ya la carpeta que lo contenía
    assert found is None


@pytest.mark.parametrize("username", ["admin", "almacenero", "operario"])
def test_in_memory_development_users_no_longer_work(client, username):
    assert login(client, username, "cualquier-clave").status_code == 422


def test_cors_allows_the_local_frontend(client):
    response = client.options(
        "/api/auth/login",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_does_not_allow_other_origins(client):
    response = client.options(
        "/api/auth/login",
        headers={"Origin": "https://otro-sitio.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in response.headers
