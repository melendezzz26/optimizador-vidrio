"""Casos de uso de autenticación. No conocen FastAPI ni SQLAlchemy."""
from app.modules.authentication.domain.errors import (
    InactiveAccountError,
    InvalidCredentialsError,
    SessionNotValidError,
)
from app.modules.authentication.domain.user import AuthenticatedUser
from app.modules.authentication.domain.username import Username

from .ports import PasswordVerifier, UserReader


def authenticate(
    username: Username,
    password: str,
    *,
    user_reader: UserReader,
    verify_password: PasswordVerifier,
) -> AuthenticatedUser:
    """Comprueba usuario y contraseña y devuelve la identidad autenticada."""
    account = user_reader.find_by_username(username)

    # Mismo error si la cuenta no existe o si la contraseña no coincide,
    # para no revelar qué usuarios están registrados.
    if account is None or not verify_password(password, account.password_hash):
        raise InvalidCredentialsError()

    # El estado solo se informa a quien ya demostró conocer la contraseña.
    if not account.is_active:
        raise InactiveAccountError()

    return account.to_authenticated_user()


def get_active_user(user_id: int, *, user_reader: UserReader) -> AuthenticatedUser:
    """Confirma que la cuenta de una sesión abierta sigue existiendo y activa.

    Devuelve los datos leídos ahora, de modo que el rol es el vigente en la
    base y no el que tenía la cuenta cuando se emitió el token.
    """
    account = user_reader.find_by_id(user_id)
    if account is None or not account.is_active:
        raise SessionNotValidError()
    return account.to_authenticated_user()
