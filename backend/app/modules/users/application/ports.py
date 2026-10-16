"""Contratos que la aplicación necesita y que la infraestructura implementa."""
from collections.abc import Callable
from datetime import datetime
from typing import Protocol
from app.modules.users.domain.role_permissions import PermissionInfo, RoleWithPermissions

from app.modules.users.domain.user import NewUser, Role, User, UserChanges


class UserRepository(Protocol):
    """Almacén de usuarios. La aplicación no sabe si detrás hay SQL u otra cosa."""

    def list_roles(self) -> list[Role]:
        ...

    def role_exists(self, role_id: int) -> bool:
        ...

    def list_users(self) -> list[User]:
        ...

    def find_by_id(self, user_id: int) -> User | None:
        ...

    def dni_exists(self, dni: str) -> bool:
        ...

    def add(self, new_user: NewUser) -> User:
        """Guarda el usuario. Lanza DuplicateDniError si el DNI ya existe."""
        ...

    def update(self, user_id: int, changes: UserChanges) -> User:
        """Aplica los cambios. Lanza UserNotFoundError si el usuario no existe."""
        ...

class RolePermissionRepository(Protocol):
    """Almacén de los permisos de cada rol (S1-RBAC)."""

    def list_roles(self) -> list[RoleWithPermissions]:
        ...

    def find_role(self, role_id: int) -> RoleWithPermissions | None:
        ...

    def list_permissions(self) -> list[PermissionInfo]:
        ...

    def replace_permissions(self, role_id: int, codes: frozenset[str]) -> RoleWithPermissions:
        """Reemplaza todos los permisos del rol en una sola transacción (RN-07)."""
        ...

# Recibe la contraseña y devuelve su hash.
PasswordHasher = Callable[[str], str]
# Devuelve la fecha y hora actuales en UTC.
Clock = Callable[[], datetime]
