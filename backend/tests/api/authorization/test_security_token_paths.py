"""TA-QA-006: token vencido, firma inválida y cuenta desactivada en rutas de negocio (RN-04, D-05).

Una ruta por cada camino de autorización, cada una con su formato de error:
- require_permission: POST /api/inventory/planchas → {"detail": "<mensaje>"}.
- run_permission: POST /api/optimization/comparisons-v2 → {"detail": {"code", "message"}}.

En los dos casos el rol sí tiene el permiso y la petición es válida: el único
motivo del rechazo es el token o la cuenta. El control positivo lo demuestra:
con un token válido la petición pasa y llega al servicio.
Corre en Windows: no necesita PostgreSQL.
"""
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.modules.authentication.domain.user import UserAccount
from app.modules.authentication.presentation.dependencies import get_user_reader
from app.shared.security.tokens import ALGORITHM, SECRET_KEY
from main import app
from tests.api.authorization.test_security_role_matrix import (
    assert_safe_error,
    bearer,
    secured_client,  # noqa: F401 (fixture)
)
from tests.auth_support import token_for

OTHER_KEY = "clave-ajena-al-backend-para-pruebas-0123456789abcdef0123456789"

PATHS = {
    "require_permission": dict(
        role="Almacenero",
        path="/api/inventory/planchas",
        json={"ancho_mm": 1000, "alto_mm": 500, "espesor_mm": 6, "cantidad": 1, "id_tipo_vidrio": 7},
        headers={},
    ),
    "run_permission": dict(
        role="Operario",
        path="/api/optimization/comparisons-v2",
        json={"order_ids": [1]},
        headers={"Idempotency-Key": "seguridad-0001"},
    ),
}

CASES = {
    "expired": "Tu sesión expiró. Inicia sesión otra vez.",
    "bad_signature": "Sesión no válida. Inicia sesión otra vez.",
    "inactive_account": "La cuenta no existe o está desactivada.",
}


class InactiveAccounts:
    """Lector de cuentas cuyas cuentas existen pero están desactivadas."""

    def find_by_username(self, username):
        return None

    def find_by_id(self, user_id: int) -> UserAccount:
        return UserAccount(
            user_id=user_id,
            username=f"T{user_id:08d}",
            full_name="Cuenta Desactivada",
            password_hash="",
            role="Almacenero",
            is_active=False,
        )


def claims_of(role: str, expires_in: timedelta) -> dict:
    """Claims de una cuenta de prueba activa con ese rol y la expiración pedida."""
    valid = jwt.decode(token_for(role), options={"verify_signature": False})
    return {**valid, "exp": datetime.now(timezone.utc) + expires_in}


def token_for_case(case: str, role: str) -> str:
    if case == "expired":
        return jwt.encode(claims_of(role, timedelta(minutes=-1)), SECRET_KEY, algorithm=ALGORITHM)
    if case == "bad_signature":
        return jwt.encode(claims_of(role, timedelta(minutes=5)), OTHER_KEY, algorithm=ALGORITHM)
    # inactive_account: token válido; la cuenta se desactiva en el lector.
    from app.modules.optimization.presentation.run_auth import get_run_user_reader

    app.dependency_overrides[get_user_reader] = InactiveAccounts
    app.dependency_overrides[get_run_user_reader] = InactiveAccounts
    return token_for(role)


def send(client, route: dict, token: str):
    return client.post(route["path"], json=route["json"], headers={**route["headers"], **bearer(token)})


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("auth_path", PATHS)
def test_business_route_rejects_the_token_with_401_and_its_error_format(secured_client, auth_path, case):
    client, calls = secured_client
    route = PATHS[auth_path]
    response = send(client, route, token_for_case(case, route["role"]))
    assert response.status_code == 401, response.text
    assert response.headers.get("www-authenticate") == "Bearer"
    assert_safe_error(response, route["path"], "UNAUTHENTICATED", CASES[case])
    assert calls == []


@pytest.mark.parametrize("auth_path", PATHS)
def test_with_a_valid_token_the_same_request_reaches_the_service(secured_client, auth_path):
    """Control positivo: con token válido y cuenta activa la petición pasa la autorización."""
    client, calls = secured_client
    route = PATHS[auth_path]
    response = send(client, route, token_for(route["role"]))
    assert response.status_code not in (401, 403), response.text
    assert calls != []
