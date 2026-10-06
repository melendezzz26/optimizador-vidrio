"""Dependencias de FastAPI: conectan las rutas con los casos de uso."""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.permissions import tiene_permiso
from app.modules.authentication.application.ports import UserReader
from app.modules.authentication.application.use_cases import get_active_user
from app.modules.authentication.domain.errors import SessionNotValidError
from app.modules.authentication.domain.user import AuthenticatedUser
from app.shared.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_database_session():
    """Sesión de base de datos de la petición.

    La base se importa aquí y no al cargar el módulo, para que la API pueda
    arrancar sin abrir la conexión (regla que comprueba test_lazy_db_import).
    """
    from app.shared.database import get_db

    yield from get_db()


def get_user_reader(db: Session = Depends(get_database_session)) -> UserReader:
    """Único punto donde se elige la implementación real del lector de cuentas."""
    from app.modules.authentication.infrastructure.sqlalchemy_user_reader import (
        SqlAlchemyUserReader,
    )

    return SqlAlchemyUserReader(db)


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED, message, headers={"WWW-Authenticate": "Bearer"}
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    user_reader: UserReader = Depends(get_user_reader),
) -> AuthenticatedUser:
    """Protege una ruta: exige un token válido y una cuenta que siga activa.

    Otros módulos la usan con ``Depends(get_current_user)`` y reciben la
    identidad con el rol vigente en la base.
    """
    if credentials is None:
        raise _unauthorized("Debes iniciar sesión.")
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Tu sesión expiró. Inicia sesión otra vez.")
    except jwt.InvalidTokenError:
        raise _unauthorized("Sesión no válida. Inicia sesión otra vez.")

    try:
        return get_active_user(int(payload["sub"]), user_reader=user_reader)
    except SessionNotValidError:
        raise _unauthorized("La cuenta no existe o está desactivada.")


def require_permission(permission: str):
    """Protege una ruta: exige que el rol del usuario tenga el permiso indicado.

    Se usa con ``Depends(require_permission("GESTIONAR_USUARIOS"))``. Sin
    sesión responde 401 (lo decide get_current_user) y sin permiso, 403.
    """

    def checker(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        # El rol es el vigente en la base, no el que traía el token.
        if not tiene_permiso(user.role, permission):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, f"No tienes el permiso: {permission}"
            )
        return user

    return checker
