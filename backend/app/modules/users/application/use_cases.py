"""Casos de uso de gestión de usuarios. No conocen FastAPI ni SQLAlchemy."""
from app.modules.users.domain.errors import (
    DuplicateDniError,
    RoleNotFoundError,
    SelfModificationError,
    UserNotFoundError,
)
from app.modules.users.domain.rules import (
    generate_access_username,
    normalize_name,
    validate_dni,
    validate_password,
)
from app.modules.users.domain.user import NewUser, Role, User, UserChanges

from .dto import CreateUserData, UpdateUserData
from .ports import Clock, PasswordHasher, UserRepository


def list_roles(*, repository: UserRepository) -> list[Role]:
    return repository.list_roles()


def list_users(*, repository: UserRepository) -> list[User]:
    return repository.list_users()


def get_user(user_id: int, *, repository: UserRepository) -> User:
    user = repository.find_by_id(user_id)
    if user is None:
        raise UserNotFoundError()
    return user


def create_user(
    data: CreateUserData,
    *,
    repository: UserRepository,
    hash_password: PasswordHasher,
    now: Clock,
) -> User:
    """Valida los datos, genera el usuario de acceso y guarda la cuenta activa."""
    first_names = normalize_name(data.first_names, "nombres")
    last_names = normalize_name(data.last_names, "apellidos")
    dni = validate_dni(data.dni)
    password = validate_password(data.password)
    username = generate_access_username(first_names, dni)

    if not repository.role_exists(data.role_id):
        raise RoleNotFoundError("El rol indicado no existe.")
    if repository.dni_exists(dni):
        raise DuplicateDniError()

    return repository.add(
        NewUser(
            dni=dni,
            first_names=first_names,
            last_names=last_names,
            username=username,
            password_hash=hash_password(password),
            role_id=data.role_id,
            created_at=now(),
        )
    )


def update_user(
    user_id: int,
    data: UpdateUserData,
    *,
    acting_user_id: int,
    repository: UserRepository,
    hash_password: PasswordHasher,
) -> User:
    """Modifica nombres, apellidos, rol, contraseña o estado.

    El DNI y el usuario de acceso no forman parte de los datos modificables.
    """
    user = get_user(user_id, repository=repository)

    first_names = None if data.first_names is None else normalize_name(data.first_names, "nombres")
    last_names = None if data.last_names is None else normalize_name(data.last_names, "apellidos")
    password = None if data.password is None else validate_password(data.password)

    if data.role_id is not None and not repository.role_exists(data.role_id):
        raise RoleNotFoundError("El rol indicado no existe.")

    # Quien administra no puede dejarse sin acceso: así siempre queda al menos
    # un Administrador activo.
    if user_id == acting_user_id:
        deactivates_self = data.is_active is False
        changes_own_role = data.role_id is not None and data.role_id != user.role_id
        if deactivates_self or changes_own_role:
            raise SelfModificationError()

    return repository.update(
        user_id,
        UserChanges(
            first_names=first_names,
            last_names=last_names,
            role_id=data.role_id,
            password_hash=None if password is None else hash_password(password),
            is_active=data.is_active,
        ),
    )
