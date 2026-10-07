"""Datos de entrada y salida de las rutas de usuarios."""
from pydantic import BaseModel, Field, StrictBool, StrictInt, StrictStr

from app.modules.users.domain.user import Role, User


class BaseSchema(BaseModel):
    # Un campo no previsto (por ejemplo "usuario" o "dni" al modificar) se rechaza con 422.
    model_config = {"extra": "forbid"}


class RoleResponse(BaseSchema):
    id_rol: int
    nombre: str

    @classmethod
    def from_domain(cls, role: Role) -> "RoleResponse":
        return cls(id_rol=role.role_id, nombre=role.name)


# Aquí solo se acota el tamaño; las reglas exactas las aplica el dominio.
class UserCreateRequest(BaseSchema):
    nombres: StrictStr = Field(max_length=255)
    apellidos: StrictStr = Field(max_length=255)
    dni: StrictStr = Field(max_length=32)
    password: StrictStr = Field(max_length=255)
    id_rol: StrictInt


class UserUpdateRequest(BaseSchema):
    """Todos los campos son opcionales: solo se modifica lo que se envía."""

    nombres: StrictStr | None = Field(default=None, max_length=255)
    apellidos: StrictStr | None = Field(default=None, max_length=255)
    id_rol: StrictInt | None = None
    password: StrictStr | None = Field(default=None, max_length=255)
    estado: StrictBool | None = None


class UserResponse(BaseSchema):
    """Nunca incluye la contraseña ni su hash."""

    id_usuario: int
    nombres: str
    apellidos: str
    dni: str
    usuario: str
    estado: bool
    id_rol: int
    rol: str

    @classmethod
    def from_domain(cls, user: User) -> "UserResponse":
        return cls(
            id_usuario=user.user_id,
            nombres=user.first_names,
            apellidos=user.last_names,
            dni=user.dni,
            usuario=user.username,
            estado=user.is_active,
            id_rol=user.role_id,
            rol=user.role_name,
        )
