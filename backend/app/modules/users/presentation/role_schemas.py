"""Datos de entrada y salida de las rutas de roles y permisos (S1-RBAC)."""
from pydantic import BaseModel, Field, StrictStr

from app.modules.users.domain.role_permissions import PermissionInfo, RoleWithPermissions


class RolePermissionsUpdateRequest(BaseModel):
    # Un campo no previsto (por ejemplo "rol" o "id_rol") se rechaza con 422.
    model_config = {"extra": "forbid"}

    permisos: list[StrictStr] = Field(max_length=100)


class PermissionResponse(BaseModel):
    codigo: str
    modulo: str
    descripcion: str

    @classmethod
    def from_domain(cls, permission: PermissionInfo) -> "PermissionResponse":
        return cls(codigo=permission.code, modulo=permission.module, descripcion=permission.description)


class RoleWithPermissionsResponse(BaseModel):
    id_rol: int
    nombre: str
    permisos: list[str]

    @classmethod
    def from_domain(cls, role: RoleWithPermissions) -> "RoleWithPermissionsResponse":
        return cls(id_rol=role.role_id, nombre=role.name, permisos=sorted(role.permissions))