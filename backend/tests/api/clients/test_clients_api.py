from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
import pytest
from sqlalchemy import func, select, update
from sqlalchemy.exc import SQLAlchemyError

from app.models import Cliente, Usuario
from app.modules.clients.infrastructure.sqlalchemy_client_repository import SqlAlchemyClientRepository
from app.shared.security.tokens import ALGORITHM, SECRET_KEY

PAYLOAD = {
    "nombre_razon_social": "  Vidrios Norte  ",
    "tipo_documento": "TEST",
    "numero_documento": "00001234",
    "telefono": "+51 900 000 001",
}
FIELDS = {"id_cliente", "nombre_razon_social", "tipo_documento", "numero_documento",
          "telefono", "estado", "fecha_registro"}


@pytest.fixture
def authenticated(client, create_user, password):
    identifier = create_user("O70000001", "Operario")
    response = client.post("/api/auth/login", json={"username": "O70000001", "password": password})
    assert response.status_code == 200
    return identifier, {"Authorization": "Bearer " + response.json()["access_token"]}


def test_post_persists_only_client_data_and_generates_utc_time(client, authenticated, session_factory):
    _, headers = authenticated
    before = datetime.now(timezone.utc)
    response = client.post("/api/clients", json=PAYLOAD, headers=headers)
    after = datetime.now(timezone.utc)
    assert response.status_code == 201, response.text
    body = response.json()
    assert set(body) == FIELDS
    assert body["id_cliente"] > 0 and body["estado"] is True
    assert body["nombre_razon_social"] == "Vidrios Norte"
    assert body["tipo_documento"] == "TEST" and body["numero_documento"] == "00001234"
    assert body["telefono"] == PAYLOAD["telefono"]
    timestamp = datetime.fromisoformat(body["fecha_registro"].replace("Z", "+00:00"))
    assert timestamp.utcoffset() == timedelta(0)
    assert before <= timestamp <= after
    with session_factory() as session:
        row = session.get(Cliente, body["id_cliente"])
        assert row.nombre_razon_social == body["nombre_razon_social"]
        assert row.fecha_registro == timestamp
        assert session.scalar(select(func.count()).select_from(Usuario)) == 1
    result = client.get("/api/clients", headers=headers)
    assert result.status_code == 200 and result.json() == [body]


def test_minimal_client_without_document_can_be_created_multiple_times(client, authenticated):
    _, headers = authenticated
    for _ in range(2):
        response = client.post("/api/clients", json={"nombre_razon_social": "Cliente sin documento"}, headers=headers)
        assert response.status_code == 201
        body = response.json()
        assert body["tipo_documento"] is None and body["numero_documento"] is None
        assert body["telefono"] is None
    assert len(client.get("/api/clients", headers=headers).json()) == 2


def test_duplicate_is_409_without_sql_and_preserves_original(client, authenticated):
    _, headers = authenticated
    original = client.post("/api/clients", json=PAYLOAD, headers=headers).json()
    response = client.post("/api/clients", json=PAYLOAD | {"numero_documento": " 00001234 "}, headers=headers)
    assert response.status_code == 409
    assert response.json() == {"detail": "Ya existe un cliente con ese tipo y número de documento."}
    assert client.get("/api/clients", headers=headers).json() == [original]


@pytest.mark.parametrize("params, names", [
    ({}, ["Vidrios Norte", "Taller Sur", "NORTE Empresa"]),
    ({"document": " 00001234 "}, ["Vidrios Norte"]),
    ({"query": "nOrTe"}, ["Vidrios Norte", "NORTE Empresa"]),
    ({"document": "00001234", "query": "sur"}, []),
    ({"query": "ausente"}, []),
    ({"document": "1234"}, []),
])
def test_list_and_search(client, authenticated, params, names):
    _, headers = authenticated
    for number, name in [("00001234", "Vidrios Norte"), ("2", "Taller Sur"), ("3", "NORTE Empresa")]:
        response = client.post("/api/clients", json=PAYLOAD | {
            "nombre_razon_social": name, "numero_documento": number,
        }, headers=headers)
        assert response.status_code == 201
    response = client.get("/api/clients", params=params, headers=headers)
    assert response.status_code == 200
    assert [row["nombre_razon_social"] for row in response.json()] == names
    assert all(set(row) == FIELDS for row in response.json())


def test_empty_list_is_200(client, authenticated):
    response = client.get("/api/clients", headers=authenticated[1])
    assert response.status_code == 200 and response.json() == []


def test_listing_preserves_inactive_clients_with_explicit_state(client, authenticated, session_factory):
    _, headers = authenticated
    created = client.post("/api/clients", json=PAYLOAD, headers=headers).json()
    with session_factory() as session:
        session.execute(update(Cliente).where(Cliente.id_cliente == created["id_cliente"]).values(estado=False))
        session.commit()
    assert client.get("/api/clients", headers=headers).json() == [created | {"estado": False}]


@pytest.mark.parametrize("payload", [
    {}, {"nombre_razon_social": None}, {"nombre_razon_social": ""}, {"nombre_razon_social": " \t\n"},
    {"nombre_razon_social": 23}, {"nombre_razon_social": True}, {"nombre_razon_social": "bad\0"},
    PAYLOAD | {"tipo_documento": []}, PAYLOAD | {"numero_documento": 1234}, PAYLOAD | {"telefono": False},
])
def test_invalid_input_is_422_without_writes(client, authenticated, session_factory, payload):
    response = client.post("/api/clients", json=payload, headers=authenticated[1])
    assert response.status_code == 422, response.text
    assert "detail" in response.json()
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Cliente)) == 0


@pytest.mark.parametrize("field, value", [
    ("id_cliente", 900), ("fecha_registro", "2000-01-01T00:00:00Z"), ("estado", False),
    ("password", "not-accepted-secret"), ("password_hash", "hash"), ("rol", "Administrador"),
    ("id_rol", 1), ("usuario", "admin"), ("credenciales", {"token": "not-accepted-secret"}),
])
def test_server_fields_and_credentials_are_rejected(client, authenticated, field, value):
    response = client.post("/api/clients", json=PAYLOAD | {field: value}, headers=authenticated[1])
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "extra_forbidden"
    assert "not-accepted-secret" not in response.text


def test_nonfinite_json_input_returns_serializable_validation_error(client, authenticated):
    response = client.post("/api/clients", content='{"nombre_razon_social":1e400}',
                           headers=authenticated[1] | {"Content-Type": "application/json"})
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "string_type"


@pytest.mark.parametrize("params", [{"document": ""}, {"query": " \t"}, {"query": "bad\0"}])
def test_invalid_search_is_422(client, authenticated, params):
    response = client.get("/api/clients", params=params, headers=authenticated[1])
    assert response.status_code == 422 and "detail" in response.json()


@pytest.mark.parametrize("token", [None, "invalid.jwt.token"])
def test_both_routes_require_authentication(client, token):
    headers = {} if token is None else {"Authorization": f"Bearer {token}"}
    assert client.get("/api/clients", headers=headers).status_code == 401
    assert client.post("/api/clients", json=PAYLOAD, headers=headers).status_code == 401


def test_expired_token_is_rejected(client, authenticated):
    token = jwt.encode({"sub": str(authenticated[0]), "exp": datetime.now(timezone.utc) - timedelta(seconds=1)},
                       SECRET_KEY, algorithm=ALGORITHM)
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/clients", headers=headers).status_code == 401
    assert client.post("/api/clients", json=PAYLOAD, headers=headers).status_code == 401


def test_inactive_account_cannot_access_either_route(client, authenticated, session_factory):
    identifier, headers = authenticated
    with session_factory() as session:
        session.execute(update(Usuario).where(Usuario.id_usuario == identifier).values(estado=False))
        session.commit()
    assert client.get("/api/clients", headers=headers).status_code == 401
    assert client.post("/api/clients", json=PAYLOAD, headers=headers).status_code == 401


@pytest.mark.parametrize("role_id, expected", [(1, 201), (2, 403), (3, 201)])
def test_current_role_uses_existing_orders_permission(client, authenticated, session_factory, role_id, expected):
    identifier, headers = authenticated
    with session_factory() as session:
        session.execute(update(Usuario).where(Usuario.id_usuario == identifier).values(id_rol=role_id))
        session.commit()
    assert client.post("/api/clients", json=PAYLOAD, headers=headers).status_code == expected
    assert client.get("/api/clients", headers=headers).status_code == (200 if expected == 201 else 403)


@pytest.mark.parametrize("method, operation", [("POST", "add"), ("GET", "list_clients")])
def test_unexpected_persistence_error_is_sanitized(client, authenticated, method, operation):
    with patch.object(SqlAlchemyClientRepository, operation, side_effect=SQLAlchemyError("SQL secret traceback")):
        response = client.request(method, "/api/clients", json=PAYLOAD if method == "POST" else None,
                                  headers=authenticated[1])
    assert response.status_code == 500
    assert response.json() == {"detail": "No se pudo completar la operación de clientes. Inténtalo otra vez."}


def test_openapi_documents_own_schemas_and_bearer_protection(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    document = response.json()
    routes = document["paths"]["/api/clients"]
    assert set(routes) == {"get", "post"}
    assert "201" in routes["post"]["responses"] and "200" in routes["get"]["responses"]
    assert {item["name"] for item in routes["get"]["parameters"]} == {"document", "query"}
    for route in routes.values():
        assert route["security"] == [{"HTTPBearer": []}]
    schemas = document["components"]["schemas"]
    assert set(schemas["ClientCreateRequest"]["properties"]) == {
        "nombre_razon_social", "tipo_documento", "numero_documento", "telefono",
    }
    assert schemas["ClientCreateRequest"]["additionalProperties"] is False
    assert set(schemas["ClientResponse"]["properties"]) == FIELDS
