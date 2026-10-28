"""TA-041: un 422 de validación nunca devuelve la contraseña ni otro dato enviado."""
import pytest

from tests.api.test_users_api import admin, payload, users  # noqa: F401

# Valores centinela: si aparecen en la respuesta, hubo eco.
SECRET = "Centinela-Clave-TA041"
NUMERIC_SECRET = 4104104104
SAFE_KEYS = {"loc", "msg", "type"}


def assert_sanitized(response, *sentinels):
    assert response.status_code == 422, response.text
    for sentinel in sentinels:
        assert str(sentinel) not in response.text
    detail = response.json()["detail"]
    assert isinstance(detail, list) and detail
    for item in detail:
        assert set(item) == SAFE_KEYS, item
    return detail


@pytest.mark.parametrize("body, field", [
    ({"username": "F70000001", "password": SECRET + "x" * 128}, "password"),  # demasiado larga
    ({"password": SECRET}, "username"),                                       # falta el usuario
    ({"username": ["F70000001"], "password": SECRET}, "username"),            # tipo inválido
])
def test_login_validation_error_never_echoes_the_password(client, body, field):
    """CA-01 y CA-03."""
    detail = assert_sanitized(client.post("/api/auth/login", json=body), SECRET)
    assert detail[0]["loc"] == ["body", field]


def test_malformed_login_json_is_sanitized(client):
    """CA-01: un JSON roto tampoco devuelve el texto recibido."""
    raw = '{"username": "F70000001", "password": "' + SECRET + '"'
    response = client.post("/api/auth/login", content=raw, headers={"Content-Type": "application/json"})
    assert_sanitized(response, SECRET)


def test_user_creation_error_in_another_field_does_not_echo_the_password(client, admin):
    """CA-02: el error es del DNI, pero el cuerpo completo no vuelve."""
    body = {key: value for key, value in payload(password=SECRET).items() if key != "dni"}
    detail = assert_sanitized(client.post("/api/users", json=body, headers=admin), SECRET)
    assert detail == [{"loc": ["body", "dni"], "msg": "Field required", "type": "missing"}]


@pytest.mark.parametrize("body, sentinel", [
    ({"password": NUMERIC_SECRET}, NUMERIC_SECRET),           # contraseña con tipo inválido
    ({"password": SECRET, "estado": "si"}, SECRET),           # error en otro campo
    ({"password": SECRET, "usuario": "X70000009"}, SECRET),   # campo no permitido
])
def test_user_update_error_never_echoes_the_password(client, admin, users, body, sentinel):
    """CA-02 y CA-03."""
    target = users["O70000003"]
    assert_sanitized(client.patch(f"/api/users/{target}", json=body, headers=admin), sentinel)


def test_business_messages_and_codes_do_not_change(client, users):
    """CA-04: los errores de negocio siguen siendo texto y con el mismo código."""
    response = client.post("/api/auth/login", json={"username": "F70000001", "password": SECRET})
    assert response.status_code == 401
    assert response.json() == {"detail": "Usuario o contraseña incorrectos."}
    assert SECRET not in response.text