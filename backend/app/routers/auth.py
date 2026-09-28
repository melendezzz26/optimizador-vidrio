"""Endpoints de autenticación (HU-001 T02)."""
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import crear_token, decodificar_token, verificar_password
from app.schemas.auth import LoginRequest, LoginResponse, UsuarioPublico
from app.services.usuarios import obtener_usuario_por_username

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])
bearer = HTTPBearer(auto_error=False)

# Mensaje único para no revelar si el usuario existe
CREDENCIALES_INVALIDAS = "Usuario o contraseña incorrectos."


@router.post("/login", response_model=LoginResponse)
def login(datos: LoginRequest):
    usuario = obtener_usuario_por_username(datos.username)
    if usuario is None or not verificar_password(datos.password, usuario.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, CREDENCIALES_INVALIDAS)
    if not usuario.activo:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Tu cuenta está desactivada. Pide al administrador que la active.",
        )
    token = crear_token(usuario.id_usuario, usuario.username, usuario.rol)
    return LoginResponse(
        access_token=token,
        usuario=UsuarioPublico(
            id_usuario=usuario.id_usuario,
            username=usuario.username,
            nombre=usuario.nombre,
            rol=usuario.rol,
        ),
    )


def usuario_actual(cred: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    """Dependencia reutilizable para proteger rutas (servirá para HU-002)."""
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Debes iniciar sesión.")
    try:
        return decodificar_token(cred.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Tu sesión expiró. Inicia sesión otra vez.")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión no válida. Inicia sesión otra vez.")


@router.get("/me")
def me(payload: dict = Depends(usuario_actual)):
    return {"id_usuario": int(payload["sub"]), "username": payload["username"], "rol": payload["rol"]}
