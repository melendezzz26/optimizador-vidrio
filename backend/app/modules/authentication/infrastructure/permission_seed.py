"""Carga del catálogo de permisos y de la asignación inicial (S1-RBAC, TA-039).

Reglas, pensadas para no deshacer lo que configure un administrador:
- Inserta los permisos del catálogo que falten.
- Un permiso recién insertado se asigna a los roles que lo tienen en
  ASIGNACION_INICIAL, aunque el rol esté vacío: no es un permiso retirado.
- Un rol recibe su asignación inicial completa solo si:
  a) quien llama lo acaba de crear (created_roles), o
  b) la base nunca se inicializó: rol_permisos no tiene ninguna fila. Es el caso
     de una base nueva, porque la migración crea los permisos antes de que
     seed.py cree los roles. Desde la aplicación, rol_permisos no puede volver a
     quedar vacía: RN-05 obliga al Administrador a conservar roles.view y
     roles.manage.
- Un rol existente sin permisos se respeta: el administrador lo dejó así (RN-06).
- Nunca quita permisos ni vuelve a agregar uno que el administrador retiró.
- Hace un único commit al final; quien llama decide la transacción.
"""
from collections.abc import Collection

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import ASIGNACION_INICIAL, CATALOGO
from app.models import Permiso, Rol, RolPermiso


def seed_permissions(db: Session, created_roles: Collection[str] = ()) -> None:
    existing_codes = set(db.scalars(select(Permiso.codigo)))
    new_codes = set()
    for permission in CATALOGO:
        if permission.code not in existing_codes:
            db.add(Permiso(
                codigo=permission.code,
                modulo=permission.module,
                descripcion=permission.description,
            ))
            new_codes.add(permission.code)
    db.flush()

    permission_ids = dict(db.execute(select(Permiso.codigo, Permiso.id_permiso)).all())
    role_ids = dict(db.execute(select(Rol.nombre, Rol.id_rol)).all())
    assigned = set(db.execute(select(RolPermiso.id_rol, RolPermiso.id_permiso)).all())
    fresh_database = not assigned

    for role_name, codes in ASIGNACION_INICIAL.items():
        role_id = role_ids.get(role_name)
        if role_id is None:
            continue  # seed.py crea los roles antes de llamar a esta función.
        initialize = fresh_database or role_name in created_roles
        to_assign = codes if initialize else codes & new_codes
        for code in sorted(to_assign):
            pair = (role_id, permission_ids[code])
            if pair not in assigned:
                db.add(RolPermiso(id_rol=role_id, id_permiso=permission_ids[code]))
                assigned.add(pair)
    db.commit()