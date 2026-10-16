"""Roles y sus permisos (S1-RBAC). Reglas puras: sin FastAPI ni base de datos."""
from dataclasses import dataclass

from app.core.permissions import PERMISOS_PROTEGIDOS_ADMINISTRADOR
from app.modules.users.domain.errors import ProtectedPermissionError

ADMINISTRATOR_ROLE = "Administrador"


@dataclass(frozen=True)
class PermissionInfo:
    code: str
    module: str
    description: str


@dataclass(frozen=True)
class RoleWithPermissions:
    role_id: int
    name: str
    permissions: frozenset[str]


def normalize_permission_codes(codes: list[str]) -> frozenset[str]:
    """RN-06: la lista se deduplica; una lista vacía es válida."""
    return frozenset(code.strip() for code in codes)


def ensure_administrator_keeps_role_management(role_name: str, codes: frozenset[str]) -> None:
    """RN-05: el Administrador conserva siempre roles.view y roles.manage."""
    if role_name == ADMINISTRATOR_ROLE and not PERMISOS_PROTEGIDOS_ADMINISTRADOR <= codes:
        raise ProtectedPermissionError(
            "El Administrador debe conservar los permisos para ver y gestionar roles."
        )