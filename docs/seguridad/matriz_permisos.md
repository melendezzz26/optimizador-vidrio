# Matriz de permisos por rol

| Campo | Valor |
|---|---|
| Fuente | `ASIGNACION_INICIAL` en `backend/app/core/permissions.py` (catálogo de 13 permisos) |
| Actualizada | 10/11/2026, TA-QA-006 ([SPEC-TA-QA-006](../specs/SPEC-TA-QA-006-seguridad-permisos.md), D-07) |
| Verificación | `backend/tests/api/authorization/test_security_role_matrix.py` comprueba esta asignación sobre las 59 rutas protegidas |

## Cómo leer esta matriz

- Los permisos **son configurables**: el Administrador puede cambiar los permisos de
  cada rol desde **Gestión de roles** (`PUT /api/roles/{id}/permissions`, permiso
  `roles.manage`). La autorización se lee de la tabla `rol_permisos` en cada petición.
- Esta matriz describe la **asignación inicial** (`ASIGNACION_INICIAL`) que se carga en
  una base nueva. Si un administrador cambia los permisos, lo vigente es lo que muestra
  Gestión de roles.
- El Administrador siempre conserva `roles.view` y `roles.manage`, para no perder el
  acceso a Gestión de roles.
- La autorización se valida siempre en el backend; la interfaz solo oculta opciones.

## Asignación inicial

| Funcionalidad | Permiso | Administrador | Almacenero | Operario |
|---|---|---|---|---|
| Consultar usuarios y roles disponibles | `users.view` | Sí | No | No |
| Crear, editar, activar y desactivar usuarios | `users.manage` | Sí | No | No |
| Consultar roles y sus permisos | `roles.view` | Sí | No | No |
| Cambiar los permisos de un rol | `roles.manage` | Sí | No | No |
| Consultar tipos de vidrio, stock de planchas y retazos, historial de movimientos y origen de retazos | `inventory.view` | Sí | Sí | Sí |
| Registrar y editar tipos de vidrio, planchas y retazos | `inventory.manage` | Sí | Sí | No |
| Dar de baja planchas y retazos (rotura, merma, error de registro, retiro) | `inventory.manage` | Sí | Sí | No |
| Consultar pedidos y clientes | `orders.view` | Sí | No | Sí |
| Registrar pedidos y piezas (incluida la importación masiva) y registrar clientes | `orders.create` | Sí | No | Sí |
| Editar pedidos pendientes | `orders.update` | Sí | No | Sí |
| Cancelar pedidos pendientes | `orders.cancel` | Sí | No | Sí |
| Ejecutar la optimización, la rasterización y las comparaciones; seleccionar y liberar una solución | `optimization.execute` | Sí | No | Sí |
| Consultar resultados de optimización y comparaciones | `optimization.view` | Sí | Sí | Sí |
| Confirmar una solución (descuenta stock) | `optimization.confirm` | Sí | No | Sí |

Cualquier sesión válida puede consultar su propia cuenta (`GET /api/auth/me`), sin
permiso adicional.

## Cambios respecto de la versión anterior

- Se agregaron las filas de consulta de usuarios, roles y permisos, bajas manuales,
  consulta de pedidos y clientes, registro de clientes, cancelación de pedidos,
  selección y liberación de soluciones, y confirmación.
- Se quitó "Configurar optimizador": no existe endpoint ni permiso para esa función
  (SPEC-TA-QA-006, D-04).
- Se agregó la columna de permiso y se aclaró que la matriz es la asignación inicial
  de un RBAC configurable.
