"""Repositorio de usuarios sobre las tablas ``usuarios`` y ``roles``."""
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Rol, Usuario
from app.modules.users.domain.errors import DuplicateDniError, UserNotFoundError
from app.modules.users.domain.user import NewUser, Role, User, UserChanges


class SqlAlchemyUserRepository:
    """Implementa UserRepository con SQLAlchemy. No contiene reglas de negocio."""

    def __init__(self, session: Session):
        self._session = session

    def list_roles(self) -> list[Role]:
        rows = self._session.execute(select(Rol).order_by(Rol.id_rol)).scalars()
        return [Role(role_id=row.id_rol, name=row.nombre) for row in rows]

    def role_exists(self, role_id: int) -> bool:
        return self._session.get(Rol, role_id) is not None

    def list_users(self) -> list[User]:
        rows = self._session.execute(self._select_users().order_by(Usuario.id_usuario)).all()
        return [self._to_user(usuario, role_name) for usuario, role_name in rows]

    def find_by_id(self, user_id: int) -> User | None:
        row = self._session.execute(
            self._select_users().where(Usuario.id_usuario == user_id)
        ).one_or_none()
        return None if row is None else self._to_user(*row)

    def dni_exists(self, dni: str) -> bool:
        statement = select(Usuario.id_usuario).where(Usuario.dni == dni)
        return self._session.execute(statement).first() is not None

    def add(self, new_user: NewUser) -> User:
        usuario = Usuario(
            dni=new_user.dni,
            nombres=new_user.first_names,
            apellidos=new_user.last_names,
            usuario=new_user.username,
            password_hash=new_user.password_hash,
            estado=True,
            fecha_creacion=new_user.created_at,
            id_rol=new_user.role_id,
        )
        self._session.add(usuario)
        try:
            self._session.commit()
        except IntegrityError as error:
            # Dos altas simultáneas con el mismo DNI: la restricción UNIQUE de la
            # base decide cuál entra, aunque ambas hayan pasado la comprobación previa.
            self._session.rollback()
            raise DuplicateDniError() from error
        return self._require(usuario.id_usuario)

    def update(self, user_id: int, changes: UserChanges) -> User:
        usuario = self._session.get(Usuario, user_id)
        if usuario is None:
            raise UserNotFoundError()
        if changes.first_names is not None:
            usuario.nombres = changes.first_names
        if changes.last_names is not None:
            usuario.apellidos = changes.last_names
        if changes.role_id is not None:
            usuario.id_rol = changes.role_id
        if changes.password_hash is not None:
            usuario.password_hash = changes.password_hash
        if changes.is_active is not None:
            usuario.estado = changes.is_active
        self._session.commit()
        return self._require(user_id)

    @staticmethod
    def _select_users():
        return select(Usuario, Rol.nombre).join(Rol, Rol.id_rol == Usuario.id_rol)

    def _require(self, user_id: int) -> User:
        user = self.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError()
        return user

    @staticmethod
    def _to_user(usuario: Usuario, role_name: str) -> User:
        return User(
            user_id=usuario.id_usuario,
            dni=usuario.dni,
            first_names=usuario.nombres,
            last_names=usuario.apellidos,
            username=usuario.usuario,
            is_active=bool(usuario.estado),
            role_id=usuario.id_rol,
            role_name=role_name,
        )
