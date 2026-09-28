"""Acceso a usuarios para autenticación (HU-001 T02).

TEMPORAL: mientras se termina el modelo de datos (TA-002), los usuarios viven
en memoria. Cuando exista la tabla USUARIO, solo hay que reemplazar el cuerpo
de `obtener_usuario_por_username` por una consulta a la BD; el router y las
pruebas no cambian.
"""
from dataclasses import dataclass
from typing import Optional

from app.core.security import hashear_password


@dataclass
class Usuario:
    id_usuario: int
    username: str
    nombre: str
    password_hash: str
    rol: str  # "Administrador" | "Almacenero" | "Operario"
    activo: bool = True


# Usuarios de desarrollo (contraseña de todos: Vidrio2026!)
_PASSWORD_DEV = hashear_password("Vidrio2026!")
_USUARIOS_DEV = {
    u.username: u
    for u in [
        Usuario(1, "admin", "Administrador de prueba", _PASSWORD_DEV, "Administrador"),
        Usuario(2, "almacenero", "Almacenero de prueba", _PASSWORD_DEV, "Almacenero"),
        Usuario(3, "operario", "Operario de prueba", _PASSWORD_DEV, "Operario"),
        Usuario(4, "inactivo", "Usuario desactivado", _PASSWORD_DEV, "Operario", activo=False),
    ]
}


def obtener_usuario_por_username(username: str) -> Optional[Usuario]:
    # TODO(TA-002): reemplazar por consulta a la tabla USUARIO + ROL
    return _USUARIOS_DEV.get(username.strip().lower())
