# PLAN-S1-RBAC — Roles y permisos configurables

## Información general

| Campo | Valor |
|---|---|
| Estado del plan | Draft |
| SPEC de referencia | [SPEC-S1-RBAC-roles-permisos-configurables.md](SPEC-S1-RBAC-roles-permisos-configurables.md), Draft, 11 CA |
| Autor | Fabricio Danniel Aguilar Chávez |
| Reviewer | Por asignar |
| Rama | `feature/S1-dynamic-rbac` |
| Base | `origin/integration/sprint-01` en `cf84d73` |
| Fecha | 15/10/2026 |
| Checkpoint 1 | Viernes 16/10, 8:00 a. m.: modelo propuesto, API/flujo y pruebas previstas (este PLAN + SPEC), PR sin merge |

Siguiendo la convención de `docs/specs/`, las **TASKS están en §10 de este PLAN**.

## 1. Situación actual (auditoría)

- **Backend:** `backend/app/core/permissions.py` define `PERMISOS`, un diccionario permiso → roles, y `tiene_permiso(rol, permiso)`. `require_permission` en `authentication/presentation/dependencies.py` llama a `tiene_permiso` con el rol vigente leído de la base. Es decir, el **rol** ya viene de la BD, pero la **matriz** está en código.
- **Usos:** la matriz define 11 códigos; los routers usan 8 (`GESTIONAR_USUARIOS`, `CONSULTAR_TIPOS_VIDRIO`, `GESTIONAR_TIPOS_VIDRIO`, `CONSULTAR_STOCK`, `GESTIONAR_PLANCHAS`, `GESTIONAR_RETAZOS`, `GESTIONAR_PEDIDOS`, `EJECUTAR_OPTIMIZACION`) en `users`, `inventory`, `orders`, `clients` y `optimization`. Ninguno tiene lógica propia de permisos fuera de `require_permission`.
- **BD:** existe `roles` (`id_rol`, `nombre`, `descripcion`). No existen `permisos` ni `rol_permisos`. Los roles se cargan con `backend/seed.py`. Head Alembic actual: `ta036a1b2c3d`.
- **Pruebas:** `backend/tests/test_permissions.py` prueba la matriz en memoria; `tests/conftest.py` usa SQLite en memoria con `metadata.create_all`.
- **Frontend:** `features/authentication/permissions.js` decide la visibilidad con listas de roles (`['Administrador', 'Operario'].includes(user.rol)`). El Sidebar muestra "Panel de roles" con `canManageUsers`. `UsersPage` es la gestión de usuarios. `InventoryPage` ya tiene un patrón de pestañas accesible (`role="tablist"`).
- **Documentación:** `docs/seguridad/matriz_permisos.md` describe la matriz actual.

## 2. Diseño backend

### 2.1 Capas

```text
authentication/
  application/ports.py        + PermissionReader (protocolo): permissions_for_role(id_rol) -> frozenset[str]
                                                              role_has_permission(id_rol, codigo) -> bool
  infrastructure/              + sqlalchemy_permission_reader.py (EXISTS sobre rol_permisos + permisos)
  presentation/dependencies.py   require_permission(codigo) usa PermissionReader (ya no tiene_permiso)
  presentation/router.py         /me y login agregan permisos
users/
  domain/                      + reglas: RN-05 (bloqueo del Administrador), RN-06 (códigos válidos)
  application/                 + ListRolesWithPermissions, ListPermissions, ReplaceRolePermissions
  infrastructure/              + repositorio de roles y permisos (reemplazo en una transacción)
  presentation/                + roles_router: /api/roles, /api/permissions
core/permissions.py            solo CATALOGO: códigos, módulo y descripción (sin roles)
models.py                      + Permiso, RolPermiso
```

`AuthenticatedUser` agrega `role_id` para consultar por clave y no por nombre.

### 2.2 Consulta de autorización

```sql
SELECT EXISTS (
  SELECT 1 FROM rol_permisos rp
  JOIN permisos p ON p.id_permiso = rp.id_permiso
  WHERE rp.id_rol = :id_rol AND p.codigo = :codigo
)
```

Una consulta indexada por petición protegida. **Sin caché entre peticiones**, para que el cambio rija en la siguiente petición (RN-02). Si más adelante se mide un costo relevante, se evalúa una caché con invalidación al hacer PUT.

### 2.3 Reemplazo de permisos

`ReplaceRolePermissions(id_rol, codigos)`:

1. Deduplica y valida formato y existencia (422 si alguno falla).
2. Verifica el rol (404).
3. Aplica RN-05 si el rol es Administrador (409).
4. En una transacción: `DELETE FROM rol_permisos WHERE id_rol = :id` e `INSERT` de los nuevos.
5. Devuelve el rol con sus permisos.

### 2.4 Errores

403 con mensaje genérico (`No tienes permiso para realizar esta acción.`), sin incluir el código del permiso, a diferencia del mensaje actual. 404, 409 y 422 con mensajes en español; nunca SQL ni stack trace.

## 3. Diseño frontend

- **`permissions.js`:** los helpers pasan de "rol en lista" a "permiso en `user.permisos`". Ejemplo: `canManageUsers(user) → hasPermission(user, 'users.manage')`. Se conservan los nombres de las funciones para no tocar a sus consumidores.
- **Sesión:** `useSession` ya guarda `usuario` de login y `/me`; ahora incluye `permisos`.
- **Sidebar:** "Panel de roles" → **"Administración"**, visible con `users.view` o `roles.view`.
- **`AdministrationPage`** (en `features/users`): `PageHeader` y pestañas **Usuarios | Roles y permisos**, con el patrón accesible de `InventoryPage`. Cada pestaña solo aparece si se tiene su permiso de vista.
  - **Usuarios:** la `UsersPage` actual, sin cambios visuales.
  - **Roles y permisos (`RolePermissionsPanel`):** selector de rol, casillas agrupadas por módulo con su descripción, botones **Guardar cambios** y **Descartar**, con feedback compartido (TA-034).
    - `roles.view` y `roles.manage` aparecen bloqueados para el Administrador, con la explicación (RN-05).
    - Si se cambian los permisos del propio rol, se vuelve a pedir `/me`.
- **API:** `rolesApi.js` con `listRoles`, `listPermissions` y `replaceRolePermissions`, usando el transporte compartido.
- **Estilo:** tokens y componentes existentes; sin CSS de rediseño.

## 4. Base de datos y migración (pendiente de coordinación)

**No se genera la migración Alembic definitiva en este checkpoint** (indicación del responsable de integración). Se deja propuesto:

- `upgrade`:
  1. Crear `permisos` y `rol_permisos` (§4.1 de la SPEC).
  2. Insertar el catálogo (13 códigos).
  3. Insertar la asignación inicial (§4.3 de la SPEC), resolviendo `id_rol` por nombre.
- `downgrade`: borrar `rol_permisos` y `permisos`. Es seguro porque `roles` y `usuarios` no cambian.
- **Revisión anterior:** `ta036a1b2c3d` o la de optimización, según lo que se integre primero. Se acuerda en el grupo antes de generarla para mantener una sola línea de revisiones.
- **Pruebas mientras tanto:** los modelos `Permiso` y `RolPermiso` se agregan a `models.py`, y las pruebas con SQLite usan `create_all` más una función compartida de carga inicial (`seed_permissions`), que la migración reutilizará.
- **`seed.py`** carga también el catálogo y la asignación inicial para entornos locales.

## 5. Archivos previstos

| Archivo | Cambio |
|---|---|
| `backend/app/models.py` | + `Permiso`, `RolPermiso` |
| `backend/app/core/permissions.py` | matriz → catálogo de códigos |
| `backend/app/modules/authentication/**` | `PermissionReader`, `require_permission`, `/me`, login |
| `backend/app/modules/users/**` | casos de uso, repositorio y router de roles y permisos |
| routers de `inventory`, `orders`, `clients`, `optimization`, `users` | solo el código de permiso |
| `backend/seed.py` | carga del catálogo y la asignación |
| `backend/alembic/versions/…` | **después de coordinar** |
| `frontend/src/features/authentication/permissions.js` | helpers por permiso |
| `frontend/src/features/users/AdministrationPage.jsx`, `RolePermissionsPanel.jsx`, `rolesApi.js` | nuevos |
| `frontend/src/shared/components/Sidebar.jsx` | rótulo y condición |
| `docs/seguridad/matriz_permisos.md` | indica que es la asignación inicial, no la fuente de verdad |

## 6. Coordinación con el equipo

- Cambiar los códigos en los routers de otros módulos: **se avisa en el grupo antes de hacerlo**, porque es una línea por endpoint y no altera su lógica.
- La migración: se acuerda el orden con el responsable de optimización.
- Frontend: los helpers conservan sus nombres, así Dashboard, Orders e Inventory no necesitan cambios.

## 7. Riesgos

| Riesgo | Mitigación |
|---|---|
| Dejar al sistema sin administrador de permisos | RN-05 en dominio + casillas bloqueadas en UI + prueba |
| Un endpoint queda con un código que no existe | Prueba estática que recorre las rutas (CA-11) |
| Cambio de permisos no se refleja por caché | Sin caché; prueba de persistencia y efecto inmediato |
| Conflicto de migraciones con optimización | No generar la migración hasta coordinar |
| Romper pruebas existentes que asumen la matriz | Reescribir `test_permissions.py` sobre la BD y ejecutar la suite completa |

## 8. Estrategia de pruebas

| Requisito del encargo | Prueba | Ubicación prevista |
|---|---|---|
| Permisos obtenidos desde BD | Al insertar o borrar una fila de `rol_permisos`, `require_permission` cambia su respuesta; `/me` devuelve lo de la tabla | `tests/integration/authentication/test_permission_reader.py`, `tests/api/authentication/test_me_permissions.py` |
| 403 sin permiso | Por cada código del catálogo, un usuario sin ese permiso recibe 403 en un endpoint representativo | `tests/api/authorization/test_endpoint_permissions.py` |
| Acceso con permiso | El mismo endpoint responde con éxito para un rol con el permiso | mismo archivo |
| Persistencia al cambiar permisos | PUT → GET `/api/roles` refleja el cambio → la siguiente petición protegida obedece el nuevo conjunto, sin nuevo login | `tests/api/users/test_role_permissions_api.py` |
| No ganar permisos manipulando el frontend | (a) petición directa sin permiso → 403; (b) PUT sin `roles.manage` → 403 y sin cambios; (c) token con `rol` o `permisos` alterados → ignorados o 401; (d) campos extra (`rol`, `permisos`) en otros payloads no tienen efecto | `tests/api/authorization/test_privilege_escalation.py` |
| RN-05, RN-06, RN-07 | 409 al quitar `roles.manage` al Administrador; 422 con códigos inválidos; atomicidad ante error simulado | `tests/unit/users/test_replace_role_permissions.py` |
| CA-02 | La carga inicial reproduce la tabla 4.3 | `tests/unit/test_permission_seed.py` |
| CA-11 | Todas las dependencias `require_permission` usan códigos del catálogo | `tests/unit/test_permission_catalog.py` |
| Frontend | helpers por permiso; Sidebar; pestañas; panel: carga, marcar, guardar, error 403/409, casillas bloqueadas | `frontend/src/features/**/__tests__/` |
| E2E | Admin quita `inventory.manage` a Almacenero → Almacenero ya no ve "Nueva plancha" y la API responde 403 → se restaura | Playwright |

Comandos: `python -m pytest -q` (backend); `npm run lint`, `npm run build`, `npm run test:unit`, `npm run test:component` (frontend), igual que el CI.

## 9. Checkpoints

| Fecha | Entregable |
|---|---|
| Vie 16/10, 8:00 | SPEC + PLAN/TASKS en la rama, PR abierto sin merge |
| Según indicación del equipo | Avance parcial demostrable: backend con permisos desde BD y pruebas 403/200 |
| Antes de la integración | Frontend completo, migración coordinada, evidencia |

## 10. TASKS

| ID | Tarea | Capa | Depende de | Estado |
|---|---|---|---|---|
| T01 | SPEC + PLAN/TASKS | docs | — | En curso |
| T02 | Modelos `Permiso`/`RolPermiso`, catálogo en `core/permissions.py` y `seed_permissions` | domain/infra | T01 | Pendiente |
| T03 | `PermissionReader` (puerto + SQLAlchemy) y `require_permission` desde BD; mensaje 403 genérico | authentication | T02 | Pendiente |
| T04 | Cambiar los códigos en los routers (avisando al equipo) + prueba estática CA-11 | presentación | T03 | Pendiente |
| T05 | `/me` y login con `permisos` | authentication | T03 | Pendiente |
| T06 | Casos de uso y API de roles y permisos (GET roles, GET permissions, PUT) con RN-05/06/07 | users | T02 | Pendiente |
| T07 | Pruebas backend de §8 (BD, 403/200, persistencia, escalada) y reescritura de `test_permissions.py` | tests | T03–T06 | Pendiente |
| T08 | Helpers por permiso en `permissions.js` y sesión con `permisos` | frontend | T05 | Pendiente |
| T09 | `AdministrationPage` con pestañas y `RolePermissionsPanel` + `rolesApi.js`; Sidebar | frontend | T06, T08 | Pendiente |
| T10 | Pruebas frontend y E2E | tests | T09 | Pendiente |
| T11 | Migración Alembic coordinada (después de acordar el orden) | migración | T02 y acuerdo | Bloqueada (coordinación) |
| T12 | Evidencia, actualización de `matriz_permisos.md`, SPEC → Implemented | docs | T07, T10, T11 | Pendiente |