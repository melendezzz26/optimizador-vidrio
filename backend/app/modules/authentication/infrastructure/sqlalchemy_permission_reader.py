"""Lectura de permisos por rol desde las tablas roles, permisos y rol_permisos."""
from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.models import Permiso, Rol, RolPermiso


class SqlAlchemyPermissionReader:
    """Implementa el contrato PermissionReader. Solo lee; nunca modifica datos."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def role_has_permission(self, role: str, permission: str) -> bool:
        # Una sola consulta EXISTS por petición protegida (PLAN §2.2).
        statement = select(exists().where(
            RolPermiso.id_rol == Rol.id_rol,
            RolPermiso.id_permiso == Permiso.id_permiso,
            Rol.nombre == role,
            Permiso.codigo == permission,
        ))
        return bool(self._db.scalar(statement))

    def permissions_for_role(self, role: str) -> frozenset[str]:
        statement = (
            select(Permiso.codigo)
            .join(RolPermiso, RolPermiso.id_permiso == Permiso.id_permiso)
            .join(Rol, Rol.id_rol == RolPermiso.id_rol)
            .where(Rol.nombre == role)
        )
        return frozenset(self._db.scalars(statement))