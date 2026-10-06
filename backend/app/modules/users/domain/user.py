"""Datos de un usuario tal como los maneja el módulo de usuarios."""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Role:
    role_id: int
    name: str


@dataclass(frozen=True)
class User:
    """Usuario registrado. No incluye la contraseña ni su hash."""

    user_id: int
    dni: str
    first_names: str
    last_names: str
    username: str
    is_active: bool
    role_id: int
    role_name: str


@dataclass(frozen=True)
class NewUser:
    """Datos ya validados de un usuario por guardar."""

    dni: str
    first_names: str
    last_names: str
    username: str
    # repr=False: el hash no debe aparecer en logs ni en mensajes de error.
    password_hash: str = field(repr=False)
    role_id: int
    created_at: datetime


@dataclass(frozen=True)
class UserChanges:
    """Cambios ya validados sobre un usuario. None significa "no modificar"."""

    first_names: str | None = None
    last_names: str | None = None
    role_id: int | None = None
    password_hash: str | None = field(default=None, repr=False)
    is_active: bool | None = None
