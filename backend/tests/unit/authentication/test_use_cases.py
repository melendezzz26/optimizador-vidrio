"""Casos de uso de autenticación con un lector de cuentas simulado (SPEC-HU-001)."""
import pytest

from app.modules.authentication.application.use_cases import authenticate, get_active_user
from app.modules.authentication.domain.errors import (
    InactiveAccountError,
    InvalidCredentialsError,
    SessionNotValidError,
)
from app.modules.authentication.domain.user import AuthenticatedUser, UserAccount
from app.modules.authentication.domain.username import Username

USERNAME = Username("F71234567")
STORED_HASH = "hash-guardado"


class FakeUserReader:
    """Sustituye a la base de datos: devuelve las cuentas que cada prueba define."""

    def __init__(self, *accounts: UserAccount) -> None:
        self._accounts = accounts

    def find_by_username(self, username: Username) -> UserAccount | None:
        return next((a for a in self._accounts if a.username == username.value), None)

    def find_by_id(self, user_id: int) -> UserAccount | None:
        return next((a for a in self._accounts if a.user_id == user_id), None)


def account(**changes) -> UserAccount:
    data = {
        "user_id": 7,
        "username": USERNAME.value,
        "full_name": "Fabiola Quispe",
        "role": "Administrador",
        "is_active": True,
        "password_hash": STORED_HASH,
    }
    data.update(changes)
    return UserAccount(**data)


def accept_only(expected_password: str):
    """Verificador simulado: evita depender de bcrypt en estas pruebas."""
    return lambda password, password_hash: password == expected_password and password_hash == STORED_HASH


def login(reader, password="correcta"):
    return authenticate(USERNAME, password, user_reader=reader, verify_password=accept_only("correcta"))


def test_valid_credentials_return_the_authenticated_user():
    user = login(FakeUserReader(account()))
    assert user == AuthenticatedUser(
        user_id=7, username="F71234567", full_name="Fabiola Quispe", role="Administrador"
    )


def test_authenticated_user_does_not_carry_the_password_hash():
    user = login(FakeUserReader(account()))
    assert not hasattr(user, "password_hash")


def test_wrong_password_is_rejected():
    with pytest.raises(InvalidCredentialsError):
        login(FakeUserReader(account()), password="incorrecta")


def test_unknown_user_is_rejected_with_the_same_error():
    with pytest.raises(InvalidCredentialsError):
        login(FakeUserReader())


def test_password_is_not_checked_when_the_user_does_not_exist():
    def fail_if_called(password, password_hash):
        raise AssertionError("no debe verificarse una contraseña sin cuenta")

    with pytest.raises(InvalidCredentialsError):
        authenticate(USERNAME, "correcta", user_reader=FakeUserReader(), verify_password=fail_if_called)


def test_inactive_account_with_correct_password_is_rejected():
    with pytest.raises(InactiveAccountError):
        login(FakeUserReader(account(is_active=False)))


def test_inactive_account_with_wrong_password_looks_like_invalid_credentials():
    # Quien no conoce la contraseña no debe poder saber que la cuenta existe.
    with pytest.raises(InvalidCredentialsError):
        login(FakeUserReader(account(is_active=False)), password="incorrecta")


def test_active_user_is_returned_with_current_data():
    user = get_active_user(7, user_reader=FakeUserReader(account(role="Operario")))
    assert user.role == "Operario"


def test_deleted_account_invalidates_the_session():
    with pytest.raises(SessionNotValidError):
        get_active_user(7, user_reader=FakeUserReader())


def test_deactivated_account_invalidates_the_session():
    with pytest.raises(SessionNotValidError):
        get_active_user(7, user_reader=FakeUserReader(account(is_active=False)))


def test_account_representation_hides_the_password_hash():
    assert STORED_HASH not in repr(account())
