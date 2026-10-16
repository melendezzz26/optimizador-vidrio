"""Rutas de roles y permisos (S1-RBAC): ver y cambiar qué permisos tiene cada rol."""
from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.modules.authentication.presentation.dependencies import require_permission
from app.modules.users.application import role_use_cases
from app.modules.users.application.ports import RolePermissionRepository
from app.modules.users.domain.errors import (
    ProtectedPermissionError,
    RoleNotRegisteredError,
    UnknownPermissionError,
)

from .dependencies import get_role_permission_repository
from .role_schemas import (
    PermissionResponse,
    RolePermissionsUpdateRequest,
    RoleWithPermissionsResponse,
)

router = APIRouter(tags=["Roles y permisos"])


@router.get("/api/roles", response_model=list[RoleWithPermissionsResponse])
def list_roles(
    repository: RolePermissionRepository = Depends(get_role_permission_repository),
    _=Depends(require_permission("roles.view")),
):
    return [
        RoleWithPermissionsResponse.from_domain(role)
        for role in role_use_cases.list_roles_with_permissions(repository=repository)
    ]


@router.get("/api/permissions", response_model=list[PermissionResponse])
def list_permissions(
    repository: RolePermissionRepository = Depends(get_role_permission_repository),
    _=Depends(require_permission("roles.view")),
):
    return [
        PermissionResponse.from_domain(permission)
        for permission in role_use_cases.list_permissions(repository=repository)
    ]


@router.put("/api/roles/{id_rol}/permissions", response_model=RoleWithPermissionsResponse)
def replace_role_permissions(
    data: RolePermissionsUpdateRequest,
    id_rol: int = Path(gt=0, le=2147483647),
    repository: RolePermissionRepository = Depends(get_role_permission_repository),
    _=Depends(require_permission("roles.manage")),
):
    try:
        role = role_use_cases.replace_role_permissions(id_rol, data.permisos, repository=repository)
    except UnknownPermissionError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error))
    except RoleNotRegisteredError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error))
    except ProtectedPermissionError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error))
    return RoleWithPermissionsResponse.from_domain(role)