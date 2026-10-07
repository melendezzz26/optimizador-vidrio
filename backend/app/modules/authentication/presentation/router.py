"""Rutas de autenticación: traducen HTTP a casos de uso y errores a códigos."""
from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.authentication.application.ports import UserReader
from app.modules.authentication.application.use_cases import authenticate
from app.modules.authentication.domain.errors import (
    InactiveAccountError,
    InvalidCredentialsError,
    InvalidUsernameError,
)
from app.modules.authentication.domain.user import AuthenticatedUser
from app.modules.authentication.domain.username import Username
from app.shared.security import create_access_token, verify_password

from .dependencies import get_current_user, get_user_reader
from .schemas import LoginRequest, LoginResponse, PublicUser, SessionInfo

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])

# Mensaje único para no revelar si el usuario existe.
INVALID_CREDENTIALS_MESSAGE = "Usuario o contraseña incorrectos."
INACTIVE_ACCOUNT_MESSAGE = "Tu cuenta está desactivada. Pide al administrador que la active."


@router.post("/login", response_model=LoginResponse)
def login(credentials: LoginRequest, user_reader: UserReader = Depends(get_user_reader)):
    try:
        # Si el formato no es válido se responde aquí, sin consultar la base.
        username = Username.parse(credentials.username)
    except InvalidUsernameError as error:
        raise HTTPException(422, str(error))

    try:
        user = authenticate(
            username,
            credentials.password,
            user_reader=user_reader,
            verify_password=verify_password,
        )
    except InvalidCredentialsError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID_CREDENTIALS_MESSAGE)
    except InactiveAccountError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, INACTIVE_ACCOUNT_MESSAGE)

    return LoginResponse(
        access_token=create_access_token(user.user_id, user.username, user.role),
        usuario=PublicUser(
            id_usuario=user.user_id,
            username=user.username,
            nombre=user.full_name,
            rol=user.role,
        ),
    )


@router.get("/me", response_model=SessionInfo)
def me(user: AuthenticatedUser = Depends(get_current_user)):
    return SessionInfo(id_usuario=user.user_id, username=user.username, rol=user.role)
