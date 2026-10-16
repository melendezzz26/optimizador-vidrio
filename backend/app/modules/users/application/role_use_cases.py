"""Casos de uso de roles y permisos (S1-RBAC). No conocen FastAPI ni SQLAlchemy."""
from app.modules.users.domain.errors import RoleNotRegisteredError, UnknownPermissionError
from app.modules.users.domain.role_permissions import (
    PermissionInfo,
    RoleWithPermissions,
    ensure_administrator_keeps_role_management,
    normalize_permission_codes,
)

from .ports import RolePermissionRepository


def list_roles_with_permissions(*, repository: RolePermissionRepository) -> list[RoleWithPermissions]:
    return repository.list_roles()


def list_permissions(*, repository: RolePermissionRepository) -> list[PermissionInfo]:
    return repository.list_permissions()


def replace_role_permissions(
    role_id: int, codes: list[str], *, repository: RolePermissionRepository,
) -> RoleWithPermissions:
    """Reemplaza los permisos del rol (PLAN §2.3). Valida todo antes de escribir."""
    requested = normalize_permission_codes(codes)
    known = {permission.code for permission in repository.list_permissions()}
    if not requested <= known:
        raise UnknownPermissionError("Hay permisos que no existen en el catálogo.")
    role = repository.find_role(role_id)
    if role is None:
        raise RoleNotRegisteredError("Rol no encontrado.")
    ensure_administrator_keeps_role_management(role.name, requested)
    return repository.replace_permissions(role_id, requested)