"""Apoyo para probar rutas protegidas sin depender de la base de datos.

La autenticación comprueba en cada petición que la cuenta del token exista y
siga activa. Estas utilidades entregan un token y un lector de cuentas en
memoria coherentes entre sí, para las pruebas de otros módulos.
"""
from app.modules.authentication.domain.user import UserAccount
from app.modules.authentication.presentation.dependencies import get_user_reader
from app.shared.security import create_access_token

_ROLE_BY_USER_ID: dict[int, str] = {}


def _user_id_for(role: str) -> int:
    for user_id, known_role in _ROLE_BY_USER_ID.items():
        if known_role == role:
            return user_id
    user_id = len(_ROLE_BY_USER_ID) + 1
    _ROLE_BY_USER_ID[user_id] = role
    return user_id


def token_for(role: str) -> str:
    """Token válido de una cuenta de prueba activa con ese rol."""
    user_id = _user_id_for(role)
    return create_access_token(user_id, f"T{user_id:08d}", role)


class InMemoryUserReader:
    """Lector de cuentas que conoce las cuentas creadas con token_for."""

    def find_by_username(self, username):
        return None

    def find_by_id(self, user_id: int) -> UserAccount | None:
        role = _ROLE_BY_USER_ID.get(user_id)
        if role is None:
            return None
        return UserAccount(
            user_id=user_id,
            username=f"T{user_id:08d}",
            full_name="Cuenta De Prueba",
            password_hash="",
            role=role,
            is_active=True,
        )


def use_in_memory_accounts(app) -> None:
    """Hace que la aplicación lea las cuentas de prueba en lugar de la base."""
    app.dependency_overrides[get_user_reader] = InMemoryUserReader
