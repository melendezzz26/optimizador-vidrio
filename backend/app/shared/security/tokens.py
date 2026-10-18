"""Creación y validación de los tokens JWT de acceso."""
from datetime import datetime, timedelta, timezone

import jwt

from app.shared.config import required_value, token_minutes

ALGORITHM = "HS256"
REQUIRED_CLAIMS = ["exp", "sub", "username", "rol"]
MAX_USER_ID = 2_147_483_647  # límite de INTEGER en PostgreSQL

SECRET_KEY = required_value("SECRET_KEY")
TOKEN_MINUTES = token_minutes()  # Por defecto, jornada de 8 h.


def create_access_token(user_id: int, username: str, role: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_MINUTES)
    payload = {"sub": str(user_id), "username": username, "rol": role, "exp": expires_at}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Devuelve el contenido del token.

    Lanza jwt.InvalidTokenError si el token expiró, fue alterado o le falta
    algún dato, de modo que quien lo llama solo necesita manejar ese error.
    """
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": REQUIRED_CLAIMS},
        )
        subject = payload["sub"]
        if (
            not isinstance(subject, str)
            or not subject.isascii()
            or not subject.isdecimal()
            or len(subject) > 10
            or not 1 <= int(subject) <= MAX_USER_ID
        ):
            raise jwt.InvalidTokenError("Identificador de usuario inválido.")
        if type(payload["exp"]) is not int:
            raise jwt.InvalidTokenError("Expiración inválida.")
        for claim, max_length in (("username", 150), ("rol", 50)):
            value = payload[claim]
            if not isinstance(value, str) or not value.strip() or len(value) > max_length:
                raise jwt.InvalidTokenError(f"Campo {claim} inválido.")
        return payload
    except (TypeError, ValueError, OverflowError) as exc:
        raise jwt.InvalidTokenError("Contenido del token inválido.") from exc
