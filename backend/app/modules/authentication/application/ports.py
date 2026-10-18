"""Contratos que la aplicación necesita y que la infraestructura implementa."""
from collections.abc import Callable
from typing import Protocol

from app.modules.authentication.domain.user import UserAccount
from app.modules.authentication.domain.username import Username


class UserReader(Protocol):
    """Lectura de cuentas. La aplicación no sabe si detrás hay SQL u otra cosa."""

    def find_by_username(self, username: Username) -> UserAccount | None:
        """Cuenta con ese usuario exacto y un rol existente, o None."""
        ...

    def find_by_id(self, user_id: int) -> UserAccount | None:
        """Cuenta con ese identificador y un rol existente, o None."""
        ...

class PermissionReader(Protocol):
    """Lectura de los permisos asignados a un rol (S1-RBAC).

    La fuente de verdad es la base: se consulta en cada petición, sin caché,
    para que un cambio de permisos rija en la siguiente petición (RN-02).
    """

    def role_has_permission(self, role: str, permission: str) -> bool:
        """True si el rol con ese nombre tiene asignado el permiso con ese código."""
        ...

    def permissions_for_role(self, role: str) -> frozenset[str]:
        """Códigos de los permisos asignados al rol con ese nombre."""
        ...

# Recibe la contraseña escrita y el hash guardado; devuelve si coinciden.
PasswordVerifier = Callable[[str, str], bool]
