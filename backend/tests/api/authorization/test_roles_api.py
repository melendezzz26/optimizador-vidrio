"""S1-RBAC: API de roles y permisos con la app real y la base de prueba (CA-05 a CA-09)."""
import pytest
from sqlalchemy import select

from app.core.permissions import ASIGNACION_INICIAL, CATALOGO, CODIGOS
from app.models import Permiso, RolPermiso
from app.shared.security import create_access_token

ROLE_IDS = {"Administrador": 1, "Almacenero": 2, "Operario": 3}  # Los de tests/conftest.py
ADMIN = "F70000001"
WAREHOUSE = "A70000002"
OPERATOR = "O70000003"
FORBIDDEN = {"detail": "No tienes permiso para realizar esta acción."}


@pytest.fixture
def headers(create_user) -> dict[str, dict]:
    accounts = {ADMIN: "Administrador", WAREHOUSE: "Almacenero", OPERATOR: "Operario"}
    result = {}
    for username, role in accounts.items():
        user_id = create_user(username, role)
        result[role] = {"Authorization": f"Bearer {create_access_token(user_id, username, role)}"}
    return result


def stored_permissions(session_factory, role: str) -> set[str]:
    with session_factory() as db:
        return set(db.scalars(
            select(Permiso.codigo)
            .join(RolPermiso, RolPermiso.id_permiso == Permiso.id_permiso)
            .where(RolPermiso.id_rol == ROLE_IDS[role])
        ))


def put_permissions(client, headers, role: str, codes):
    return client.put(f"/api/roles/{ROLE_IDS[role]}/permissions", json={"permisos": codes}, headers=headers)


# --- Lectura ---------------------------------------------------------------

def test_administrator_lists_roles_with_their_initial_permissions(client, headers):
    response = client.get("/api/roles", headers=headers["Administrador"])
    assert response.status_code == 200
    assert {role["nombre"]: set(role["permisos"]) for role in response.json()} == {
        role: set(codes) for role, codes in ASIGNACION_INICIAL.items()
    }


def test_administrator_lists_the_permission_catalog(client, headers):
    response = client.get("/api/permissions", headers=headers["Administrador"])
    assert response.status_code == 200
    assert response.json() == [
        {"codigo": p.code, "modulo": p.module, "descripcion": p.description} for p in CATALOGO
    ]


@pytest.mark.parametrize("role", ["Almacenero", "Operario"])
@pytest.mark.parametrize("path", ["/api/roles", "/api/permissions"])
def test_roles_without_roles_view_cannot_read(client, headers, role, path):
    response = client.get(path, headers=headers[role])
    assert response.status_code == 403
    assert response.json() == FORBIDDEN


def test_reading_requires_a_session(client):
    assert client.get("/api/roles").status_code == 401


# --- Reemplazo y persistencia (CA-05) --------------------------------------

def test_replacing_permissions_persists_and_applies_on_the_next_request(client, headers, session_factory):
    warehouse = headers["Almacenero"]
    assert client.get("/api/users", headers=warehouse).status_code == 403

    response = put_permissions(
        client, headers["Administrador"], "Almacenero", ["inventory.view", "users.view", "users.view"],
    )
    assert response.status_code == 200
    assert response.json() == {
        "id_rol": ROLE_IDS["Almacenero"], "nombre": "Almacenero", "permisos": ["inventory.view", "users.view"],
    }
    # Persistido en la base y visible por GET.
    assert stored_permissions(session_factory, "Almacenero") == {"inventory.view", "users.view"}
    roles = client.get("/api/roles", headers=headers["Administrador"]).json()
    assert next(r for r in roles if r["nombre"] == "Almacenero")["permisos"] == ["inventory.view", "users.view"]
    # Rige en la siguiente petición, con el mismo token (sin volver a iniciar sesión).
    assert client.get("/api/users", headers=warehouse).status_code == 200
    assert client.get("/api/auth/me", headers=warehouse).json()["permisos"] == ["inventory.view", "users.view"]
    # Y lo quitado (inventory.manage) deja de estar permitido.
    assert client.post("/api/inventory/tipos-vidrio", json={}, headers=warehouse).status_code == 403


def test_a_role_can_be_left_without_permissions(client, headers, session_factory):
    response = put_permissions(client, headers["Administrador"], "Operario", [])
    assert response.status_code == 200
    assert response.json()["permisos"] == []
    assert stored_permissions(session_factory, "Operario") == set()
    assert client.get("/api/orders", headers=headers["Operario"]).status_code == 403


# --- Reglas: RN-05, RN-06 y 404 --------------------------------------------

@pytest.mark.parametrize("removed", ["roles.view", "roles.manage"])
def test_administrator_cannot_lose_role_management(client, headers, session_factory, removed):
    response = put_permissions(client, headers["Administrador"], "Administrador", sorted(CODIGOS - {removed}))
    assert response.status_code == 409
    assert stored_permissions(session_factory, "Administrador") == set(CODIGOS)


@pytest.mark.parametrize("codes", [["inventory.view", "inventario.ver"], ["GESTIONAR_USUARIOS"]])
def test_unknown_codes_answer_422_and_change_nothing(client, headers, session_factory, codes):
    response = put_permissions(client, headers["Administrador"], "Almacenero", codes)
    assert response.status_code == 422
    assert stored_permissions(session_factory, "Almacenero") == set(ASIGNACION_INICIAL["Almacenero"])


@pytest.mark.parametrize("body", [{}, {"permisos": "inventory.view"}, {"permisos": [1, 2]},
                                  {"permisos": ["inventory.view"], "rol": "Administrador"}])
def test_malformed_bodies_answer_422_and_change_nothing(client, headers, session_factory, body):
    response = client.put(
        f"/api/roles/{ROLE_IDS['Almacenero']}/permissions", json=body, headers=headers["Administrador"],
    )
    assert response.status_code == 422
    assert stored_permissions(session_factory, "Almacenero") == set(ASIGNACION_INICIAL["Almacenero"])


def test_unknown_role_answers_404(client, headers):
    response = client.put("/api/roles/99/permissions", json={"permisos": []}, headers=headers["Administrador"])
    assert response.status_code == 404


# --- Sin escalada de privilegios (CA-06) -----------------------------------

@pytest.mark.parametrize("role", ["Almacenero", "Operario"])
def test_a_role_without_roles_manage_cannot_grant_itself_permissions(client, headers, session_factory, role):
    response = put_permissions(client, headers[role], role, sorted(CODIGOS))
    assert response.status_code == 403
    assert response.json() == FORBIDDEN
    assert stored_permissions(session_factory, role) == set(ASIGNACION_INICIAL[role])


def test_roles_view_alone_does_not_allow_changes(client, headers, session_factory):
    put_permissions(client, headers["Administrador"], "Almacenero", ["roles.view"])
    response = put_permissions(client, headers["Almacenero"], "Almacenero", sorted(CODIGOS))
    assert response.status_code == 403
    assert stored_permissions(session_factory, "Almacenero") == {"roles.view"}


def test_permissions_sent_in_the_token_or_body_of_other_requests_are_ignored(client, headers, create_user):
    """El cliente no puede declarar sus propios permisos: se leen siempre de la base."""
    operator_id = create_user("O70000009", "Operario")
    token = create_access_token(operator_id, "O70000009", "Administrador")
    forged = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/roles", headers=forged).status_code == 403
    me = client.get("/api/auth/me", headers=forged).json()
    assert me["rol"] == "Operario"
    assert "roles.manage" not in me["permisos"]