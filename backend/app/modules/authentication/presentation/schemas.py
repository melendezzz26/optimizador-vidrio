"""Datos de entrada y salida de las rutas de autenticación."""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    # El formato exacto del usuario lo valida el dominio; aquí solo se acota el tamaño.
    username: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=1, max_length=128)


class PublicUser(BaseModel):
    id_usuario: int
    username: str
    nombre: str
    rol: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: PublicUser


class SessionInfo(BaseModel):
    id_usuario: int
    username: str
    rol: str
