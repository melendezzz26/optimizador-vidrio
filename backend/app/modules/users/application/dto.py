"""Datos que la capa de presentación entrega a los casos de uso."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CreateUserData:
    first_names: str
    last_names: str
    dni: str
    # repr=False: la contraseña no debe aparecer en logs ni en mensajes de error.
    password: str = field(repr=False)
    role_id: int


@dataclass(frozen=True)
class UpdateUserData:
    """Campos por modificar. None significa "no modificar"."""

    first_names: str | None = None
    last_names: str | None = None
    role_id: int | None = None
    password: str | None = field(default=None, repr=False)
    is_active: bool | None = None
