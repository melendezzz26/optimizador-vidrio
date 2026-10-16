"""Repositorio de permisos por rol sobre roles, permisos y rol_permisos (S1-RBAC)."""
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Permiso, Rol, RolPermiso
from app.modules.users.domain.errors import RoleNotRegisteredError
from app.modules.users.domain.role_permissions import PermissionInfo, RoleWithPermissions


class SqlAlchemyRolePermissionRepository:
    """Implementa RolePermissionRepository. No contiene reglas de negocio."""

    def __init__(self, session: Session):
        self._session = session

    def list_roles(self) -> list[RoleWithPermissions]:
        roles = self._session.execute(select(Rol).order_by(Rol.id_rol)).scalars().all()
        return [self._with_permissions(role) for role in roles]

    def find_role(self, role_id: int) -> RoleWithPermissions | None:
        role = self._session.get(Rol, role_id)
        return None if role is None else self._with_permissions(role)

    def list_permissions(self) -> list[PermissionInfo]:
        rows = self._session.execute(select(Permiso).order_by(Permiso.id_permiso)).scalars()
        return [PermissionInfo(code=row.codigo, module=row.modulo, description=row.descripcion) for row in rows]

    def replace_permissions(self, role_id: int, codes: frozenset[str]) -> RoleWithPermissions:
        try:
            # Bloquea la fila del rol: dos reemplazos simultáneos del mismo rol se ordenan.
            role = self._session.execute(
                select(Rol).where(Rol.id_rol == role_id).with_for_update()
            ).scalar_one_or_none()
            if role is None:
                raise RoleNotRegisteredError("Rol no encontrado.")
            permission_ids = self._session.execute(
                select(Permiso.id_permiso).where(Permiso.codigo.in_(codes))
            ).scalars().all()
            # RN-07: borrar e insertar en la misma transacción; un error deshace ambos.
            self._session.execute(delete(RolPermiso).where(RolPermiso.id_rol == role_id))
            self._session.add_all(
                [RolPermiso(id_rol=role_id, id_permiso=permission_id) for permission_id in permission_ids]
            )
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        return self._with_permissions(role)

    def _with_permissions(self, role: Rol) -> RoleWithPermissions:
        codes = self._session.execute(
            select(Permiso.codigo)
            .join(RolPermiso, RolPermiso.id_permiso == Permiso.id_permiso)
            .where(RolPermiso.id_rol == role.id_rol)
        ).scalars()
        return RoleWithPermissions(role_id=role.id_rol, name=role.nombre, permissions=frozenset(codes))