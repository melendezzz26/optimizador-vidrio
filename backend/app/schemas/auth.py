"""Esquemas de entrada/salida del login (HU-001 T02)."""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class UsuarioPublico(BaseModel):
    id_usuario: int
    username: str
    nombre: str
    rol: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioPublico
