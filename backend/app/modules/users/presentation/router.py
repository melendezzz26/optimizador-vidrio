"""Rutas de gestión de usuarios: traducen HTTP a casos de uso y errores a códigos."""
from contextlib import contextmanager
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.authentication.domain.user import AuthenticatedUser
from app.modules.users.application import use_cases
from app.modules.users.application.dto import CreateUserData, UpdateUserData
from app.modules.users.application.ports import UserRepository
from app.modules.users.domain.errors import (
    DuplicateDniError,
    InvalidUserDataError,
    SelfModificationError,
    UserNotFoundError,
)
from app.shared.security import hash_password

from .dependencies import get_user_repository, require_user_management
from .schemas import RoleResponse, UserCreateRequest, UserResponse, UserUpdateRequest

# Todas las rutas exigen sesión y el permiso GESTIONAR_USUARIOS.
router = APIRouter(
    prefix="/api/users",
    tags=["Usuarios"],
    dependencies=[Depends(require_user_management)],
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@contextmanager
def domain_errors_as_http():
    try:
        yield
    except InvalidUserDataError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error))
    except DuplicateDniError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un usuario con ese DNI.")
    except SelfModificationError:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No puedes desactivar tu propia cuenta ni cambiar tu propio rol.",
        )
    except UserNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado.")


@router.get("/roles", response_model=list[RoleResponse])
def list_roles(repository: UserRepository = Depends(get_user_repository)):
    return [RoleResponse.from_domain(role) for role in use_cases.list_roles(repository=repository)]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreateRequest, repository: UserRepository = Depends(get_user_repository)):
    with domain_errors_as_http():
        user = use_cases.create_user(
            CreateUserData(
                first_names=data.nombres,
                last_names=data.apellidos,
                dni=data.dni,
                password=data.password,
                role_id=data.id_rol,
            ),
            repository=repository,
            hash_password=hash_password,
            now=_utc_now,
        )
    return UserResponse.from_domain(user)


@router.get("", response_model=list[UserResponse])
def list_users(repository: UserRepository = Depends(get_user_repository)):
    return [UserResponse.from_domain(user) for user in use_cases.list_users(repository=repository)]


@router.get("/{id_usuario}", response_model=UserResponse)
def get_user(id_usuario: int, repository: UserRepository = Depends(get_user_repository)):
    with domain_errors_as_http():
        return UserResponse.from_domain(use_cases.get_user(id_usuario, repository=repository))


@router.patch("/{id_usuario}", response_model=UserResponse)
def update_user(
    id_usuario: int,
    data: UserUpdateRequest,
    repository: UserRepository = Depends(get_user_repository),
    acting_user: AuthenticatedUser = Depends(require_user_management),
):
    with domain_errors_as_http():
        user = use_cases.update_user(
            id_usuario,
            UpdateUserData(
                first_names=data.nombres,
                last_names=data.apellidos,
                role_id=data.id_rol,
                password=data.password,
                is_active=data.estado,
            ),
            acting_user_id=acting_user.user_id,
            repository=repository,
            hash_password=hash_password,
        )
    return UserResponse.from_domain(user)
