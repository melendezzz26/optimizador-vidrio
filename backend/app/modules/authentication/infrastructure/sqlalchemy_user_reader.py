"""Lectura de cuentas desde las tablas usuarios y roles con SQLAlchemy."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Rol, Usuario
from app.modules.authentication.domain.user import UserAccount
from app.modules.authentication.domain.username import Username


class SqlAlchemyUserReader:
    """Implementa el contrato UserReader. Solo lee; nunca modifica datos."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_username(self, username: Username) -> UserAccount | None:
        return self._find(Usuario.usuario == username.value)

    def find_by_id(self, user_id: int) -> UserAccount | None:
        return self._find(Usuario.id_usuario == user_id)

    def _find(self, condition) -> UserAccount | None:
        # El JOIN exige un rol existente: una cuenta sin rol válido no se autentica (RN-08).
        statement = (
            select(Usuario, Rol.nombre)
            .join(Rol, Rol.id_rol == Usuario.id_rol)
            .where(condition)
        )
        row = self._db.execute(statement).first()
        if row is None:
            return None
        user, role_name = row
        return UserAccount(
            user_id=user.id_usuario,
            username=user.usuario,
            full_name=f"{user.nombres} {user.apellidos}".strip(),
            role=role_name,
            is_active=bool(user.estado),
            password_hash=user.password_hash,
        )
