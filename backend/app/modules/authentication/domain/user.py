"""Datos de usuario que maneja la autenticación."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AuthenticatedUser:
    """Usuario con sesión válida. Es lo que reciben las rutas protegidas."""

    user_id: int
    username: str
    full_name: str
    role: str


@dataclass(frozen=True)
class UserAccount:
    """Cuenta tal como está guardada, con lo necesario para decidir si puede entrar."""

    user_id: int
    username: str
    full_name: str
    role: str
    is_active: bool
    # repr=False evita que el hash aparezca si el objeto se imprime o se registra.
    password_hash: str = field(repr=False)

    def to_authenticated_user(self) -> AuthenticatedUser:
        return AuthenticatedUser(
            user_id=self.user_id,
            username=self.username,
            full_name=self.full_name,
            role=self.role,
        )
