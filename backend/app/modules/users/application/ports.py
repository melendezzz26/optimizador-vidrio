"""Contratos que la aplicación necesita y que la infraestructura implementa."""
from collections.abc import Callable
from datetime import datetime
from typing import Protocol

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


# Recibe la contraseña y devuelve su hash.
PasswordHasher = Callable[[str], str]
# Devuelve la fecha y hora actuales en UTC.
Clock = Callable[[], datetime]
