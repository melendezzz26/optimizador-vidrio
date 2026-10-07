"""API de gestión de usuarios de extremo a extremo sobre una base de prueba (SPEC-HU-003)."""
import pytest
from sqlalchemy import func, select

from app.models import Usuario
from app.shared.security import create_access_token, verify_password

ADMIN = "F70000001"
WAREHOUSE = "A70000002"
OPERATOR = "O70000003"
NEW_PASSWORD = "clave-segura-1"

ROUTES = [
    ("GET", "/api/users/roles"),
    ("GET", "/api/users"),
    ("POST", "/api/users"),
    ("GET", "/api/users/1"),
    ("PATCH", "/api/users/1"),
]


@pytest.fixture
def users(create_user) -> dict[str, int]:
    return {
        ADMIN: create_user(ADMIN, "Administrador", first_names="Fabiola", last_names="Quispe"),
        WAREHOUSE: create_user(WAREHOUSE, "Almacenero"),
        OPERATOR: create_user(OPERATOR, "Operario"),
    }


def headers_for(users, username, role) -> dict:
    token = create_access_token(users[username], username, role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin(users) -> dict:
    """Cabeceras de una sesión de Administrador."""
    return headers_for(users, ADMIN, "Administrador")


def payload(**changes) -> dict:
    data = {
        "nombres": "Álvaro",
        "apellidos": "Rojas Paz",
        "dni": "71234567",
        "password": NEW_PASSWORD,
        "id_rol": 3,
    }
    data.update(changes)
    return {key: value for key, value in data.items() if value is not ...}


def create(client, admin, **changes):
    return client.post("/api/users", json=payload(**changes), headers=admin)


def login(client, username, password):
    return client.post("/api/auth/login", json={"username": username, "password": password})


def count_users(session_factory) -> int:
    with session_factory() as db:
        return db.execute(select(func.count()).select_from(Usuario)).scalar_one()


# --- Roles ---

def test_roles_are_listed_for_the_form(client, admin):
    response = client.get("/api/users/roles", headers=admin)
    assert response.status_code == 200
    assert response.json() == [
        {"id_rol": 1, "nombre": "Administrador"},
        {"id_rol": 2, "nombre": "Almacenero"},
        {"id_rol": 3, "nombre": "Operario"},
    ]


# --- Alta (CA-02, CA-03, CA-04) ---

def test_valid_creation_returns_201_with_the_generated_username(client, admin):
    response = create(client, admin)

    assert response.status_code == 201
    body = response.json()
    assert body.pop("id_usuario") > 0
    assert body == {
        "nombres": "Álvaro",
        "apellidos": "Rojas Paz",
        "dni": "71234567",
        "usuario": "A71234567",
        "estado": True,
        "id_rol": 3,
        "rol": "Operario",
    }


def test_creation_stores_a_hash_and_the_creation_date(client, admin, session_factory):
    user_id = create(client, admin).json()["id_usuario"]

    with session_factory() as db:
        row = db.get(Usuario, user_id)
    assert row.password_hash != NEW_PASSWORD
    assert verify_password(NEW_PASSWORD, row.password_hash)
    assert row.fecha_creacion is not None
    assert row.estado is True


def test_created_user_can_sign_in_with_the_generated_username(client, admin):
    create(client, admin)

    response = login(client, "A71234567", NEW_PASSWORD)

    assert response.status_code == 200
    assert response.json()["usuario"]["rol"] == "Operario"


def test_names_are_stored_without_extra_spaces(client, admin):
    body = create(client, admin, nombres="  María   José ", apellidos=" De la  Cruz ").json()
    assert (body["nombres"], body["apellidos"], body["usuario"]) == ("María José", "De la Cruz", "M71234567")


def test_duplicate_dni_returns_409_and_creates_nothing(client, admin, session_factory):
    create(client, admin)
    before = count_users(session_factory)

    response = create(client, admin, nombres="Otra", apellidos="Persona")

    assert response.status_code == 409
    assert response.json()["detail"] == "Ya existe un usuario con ese DNI."
    assert count_users(session_factory) == before


@pytest.mark.parametrize(
    "changes",
    [
        {"dni": "1234567"},
        {"dni": "123456789"},
        {"dni": "7123456A"},
        {"dni": ""},
        {"nombres": "   "},
        {"nombres": "9lvaro"},
        {"nombres": "a" * 101},
        {"apellidos": ""},
        {"password": "corta"},
        {"password": "a" * 73},
        {"id_rol": 99},
        {"id_rol": "3"},
        {"dni": 71234567},
        {"correo": "alguien@example.com"},
        {"usuario": "Z99999999"},
        {"estado": False},
        {"nombres": ...},
        {"password": ...},
        {"id_rol": ...},
    ],
)
def test_invalid_creation_returns_422_and_creates_nothing(client, admin, session_factory, changes):
    before = count_users(session_factory)

    response = create(client, admin, **changes)

    assert response.status_code == 422
    assert count_users(session_factory) == before


def test_unknown_role_message(client, admin):
    assert create(client, admin, id_rol=99).json()["detail"] == "El rol indicado no existe."


# --- Consulta (CA-05) ---

def test_list_returns_every_user_with_its_role(client, admin, users):
    response = client.get("/api/users", headers=admin)

    assert response.status_code == 200
    listed = {user["usuario"]: user["rol"] for user in response.json()}
    assert listed == {ADMIN: "Administrador", WAREHOUSE: "Almacenero", OPERATOR: "Operario"}


def test_get_returns_one_user(client, admin, users):
    response = client.get(f"/api/users/{users[ADMIN]}", headers=admin)
    assert response.status_code == 200
    assert response.json()["usuario"] == ADMIN
    assert response.json()["nombres"] == "Fabiola"


def test_get_unknown_user_returns_404(client, admin):
    response = client.get("/api/users/9999", headers=admin)
    assert response.status_code == 404
    assert response.json()["detail"] == "Usuario no encontrado."


# --- Modificación (CA-06, CA-07) ---

def test_update_changes_names_and_role_but_not_dni_or_username(client, admin):
    created = create(client, admin).json()

    response = client.patch(
        f"/api/users/{created['id_usuario']}",
        json={"nombres": "Zoila", "apellidos": "Paz", "id_rol": 2},
        headers=admin,
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["nombres"], body["apellidos"], body["rol"]) == ("Zoila", "Paz", "Almacenero")
    assert (body["dni"], body["usuario"]) == ("71234567", "A71234567")


@pytest.mark.parametrize("field, value", [("dni", "70000009"), ("usuario", "Z70000009"), ("correo", "a@b.pe")])
def test_update_rejects_fields_that_cannot_be_modified(client, admin, field, value):
    created = create(client, admin).json()

    response = client.patch(f"/api/users/{created['id_usuario']}", json={field: value}, headers=admin)

    assert response.status_code == 422
    unchanged = client.get(f"/api/users/{created['id_usuario']}", headers=admin).json()
    assert unchanged == created


def test_update_with_an_empty_body_changes_nothing(client, admin):
    created = create(client, admin).json()
    response = client.patch(f"/api/users/{created['id_usuario']}", json={}, headers=admin)
    assert response.status_code == 200
    assert response.json() == created


def test_update_password_replaces_the_previous_one(client, admin):
    created = create(client, admin).json()

    response = client.patch(
        f"/api/users/{created['id_usuario']}", json={"password": "otra-clave-22"}, headers=admin
    )

    assert response.status_code == 200
    assert login(client, "A71234567", "otra-clave-22").status_code == 200
    assert login(client, "A71234567", NEW_PASSWORD).status_code == 401


@pytest.mark.parametrize(
    "changes",
    [{"nombres": " "}, {"apellidos": "a" * 101}, {"password": "corta"}, {"id_rol": 99}, {"estado": "no"}],
)
def test_invalid_update_returns_422_and_changes_nothing(client, admin, changes):
    created = create(client, admin).json()

    response = client.patch(f"/api/users/{created['id_usuario']}", json=changes, headers=admin)

    assert response.status_code == 422
    assert client.get(f"/api/users/{created['id_usuario']}", headers=admin).json() == created
    assert login(client, "A71234567", NEW_PASSWORD).status_code == 200


def test_update_unknown_user_returns_404(client, admin):
    assert client.patch("/api/users/9999", json={"nombres": "Nadie"}, headers=admin).status_code == 404


def test_deactivated_user_cannot_sign_in_and_reactivated_user_can(client, admin):
    created = create(client, admin).json()
    url = f"/api/users/{created['id_usuario']}"

    deactivated = client.patch(url, json={"estado": False}, headers=admin)
    assert deactivated.status_code == 200
    assert deactivated.json()["estado"] is False
    assert login(client, "A71234567", NEW_PASSWORD).status_code == 403

    reactivated = client.patch(url, json={"estado": True}, headers=admin)
    assert reactivated.json()["estado"] is True
    assert login(client, "A71234567", NEW_PASSWORD).status_code == 200


def test_deactivation_ends_the_open_sessions_of_that_user(client, admin):
    created = create(client, admin).json()
    token = login(client, "A71234567", NEW_PASSWORD).json()["access_token"]
    session = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/auth/me", headers=session).status_code == 200

    client.patch(f"/api/users/{created['id_usuario']}", json={"estado": False}, headers=admin)

    assert client.get("/api/auth/me", headers=session).status_code == 401


# --- RN-07: el Administrador no puede dejarse sin acceso (CA-08) ---

@pytest.mark.parametrize("changes", [{"estado": False}, {"id_rol": 3}])
def test_administrator_cannot_deactivate_or_demote_their_own_account(client, admin, users, changes):
    response = client.patch(f"/api/users/{users[ADMIN]}", json=changes, headers=admin)

    assert response.status_code == 409
    assert response.json()["detail"] == "No puedes desactivar tu propia cuenta ni cambiar tu propio rol."
    current = client.get(f"/api/users/{users[ADMIN]}", headers=admin).json()
    assert (current["estado"], current["rol"]) == (True, "Administrador")


def test_administrator_can_edit_their_own_names(client, admin, users):
    response = client.patch(f"/api/users/{users[ADMIN]}", json={"nombres": "Fabia"}, headers=admin)
    assert response.status_code == 200
    assert response.json()["nombres"] == "Fabia"


def test_administrator_can_deactivate_another_user(client, admin, users):
    response = client.patch(f"/api/users/{users[OPERATOR]}", json={"estado": False}, headers=admin)
    assert response.status_code == 200
    assert response.json()["estado"] is False


# --- Autorización (CA-09) ---

@pytest.mark.parametrize("method, url", ROUTES)
def test_every_route_requires_a_session(client, users, method, url):
    assert client.request(method, url, json={}).status_code == 401


@pytest.mark.parametrize("method, url", ROUTES)
@pytest.mark.parametrize("username, role", [(WAREHOUSE, "Almacenero"), (OPERATOR, "Operario")])
def test_roles_without_the_permission_get_403(client, users, session_factory, method, url, username, role):
    before = count_users(session_factory)

    response = client.request(method, url, json=payload(), headers=headers_for(users, username, role))

    assert response.status_code == 403
    assert count_users(session_factory) == before


def test_permission_follows_the_current_role(client, admin, users):
    operator = headers_for(users, OPERATOR, "Operario")
    assert client.get("/api/users", headers=operator).status_code == 403

    client.patch(f"/api/users/{users[OPERATOR]}", json={"id_rol": 1}, headers=admin)
    # Mismo token: el permiso se evalúa con el rol vigente en la base.
    assert client.get("/api/users", headers=operator).status_code == 200

    client.patch(f"/api/users/{users[OPERATOR]}", json={"id_rol": 3}, headers=admin)
    assert client.get("/api/users", headers=operator).status_code == 403


# --- Datos sensibles (CA-10) ---

def test_responses_never_expose_the_password_or_its_hash(client, admin, users, password_hash):
    created = create(client, admin)
    responses = [
        created,
        client.get("/api/users", headers=admin),
        client.get(f"/api/users/{created.json()['id_usuario']}", headers=admin),
        client.patch(f"/api/users/{created.json()['id_usuario']}", json={"nombres": "Ana"}, headers=admin),
    ]
    for response in responses:
        assert "password" not in response.text
        assert NEW_PASSWORD not in response.text
        assert password_hash not in response.text


# --- CORS ---

def test_frontend_origin_may_send_patch_requests(client):
    response = client.options(
        "/api/users/1",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code == 200
    assert "PATCH" in response.headers["access-control-allow-methods"]
