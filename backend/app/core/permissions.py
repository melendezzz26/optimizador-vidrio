"""Permisos del sistema (S1-RBAC).

- CATALOGO: los permisos que existen. Cada endpoint declara el suyo, por eso
  sus códigos viven en el código.
- ASIGNACION_INICIAL: datos de carga inicial (equivalentes a la matriz previa).
  NO es la fuente de verdad: la autorización consulta la tabla rol_permisos.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Permission:
    code: str
    module: str
    description: str


CATALOGO: tuple[Permission, ...] = (
    Permission("users.view", "users", "Ver usuarios y roles disponibles"),
    Permission("users.manage", "users", "Crear, editar, activar y desactivar usuarios"),
    Permission("roles.view", "roles", "Ver roles y sus permisos"),
    Permission("roles.manage", "roles", "Cambiar los permisos de un rol"),
    Permission("inventory.view", "inventory", "Ver catálogo de vidrio, planchas, retazos e historial"),
    Permission("inventory.manage", "inventory", "Registrar, editar y dar de baja tipos, planchas y retazos"),
    Permission("orders.view", "orders", "Ver pedidos y clientes"),
    Permission("orders.create", "orders", "Registrar pedidos y clientes"),
    Permission("orders.update", "orders", "Editar pedidos pendientes"),
    Permission("orders.cancel", "orders", "Cancelar pedidos pendientes"),
    Permission("optimization.view", "optimization", "Ver resultados de optimización"),
    Permission("optimization.execute", "optimization", "Ejecutar la optimización y la rasterización"),
    Permission("optimization.confirm", "optimization", "Confirmar una solución (descuenta stock)"),
)

CODIGOS: frozenset[str] = frozenset(permission.code for permission in CATALOGO)

# Permisos que el Administrador debe conservar siempre (RN-05).
PERMISOS_PROTEGIDOS_ADMINISTRADOR: frozenset[str] = frozenset({"roles.view", "roles.manage"})

ASIGNACION_INICIAL: dict[str, frozenset[str]] = {
    "Administrador": CODIGOS,
    "Almacenero": frozenset({"inventory.view", "inventory.manage", "optimization.view"}),
    "Operario": frozenset({
        "inventory.view",
        "orders.view", "orders.create", "orders.update", "orders.cancel",
        "optimization.view", "optimization.execute", "optimization.confirm",
    }),
}