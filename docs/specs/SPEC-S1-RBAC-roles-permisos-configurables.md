# SPEC-S1-RBAC — Roles y permisos configurables

## Información general

| Campo | Valor |
|---|---|
| Estado | Draft |
| PBI relacionado | Corrección Sprint 1: roles y permisos configurables (observación del ingeniero: la matriz de permisos no debe quedar hardcodeada) |
| Responsable | Fabricio Danniel Aguilar Chávez |
| Reviewer | Por asignar (distinto del autor) |
| Rama | `feature/S1-dynamic-rbac` |
| Base | `origin/integration/sprint-01` en `cf84d73` |
| Fecha | 15/10/2026 |
| Plan y tareas | [PLAN-S1-RBAC-roles-permisos-configurables.md](PLAN-S1-RBAC-roles-permisos-configurables.md) |

## 1. Objetivo

Que la relación entre roles y permisos se guarde en la base de datos y se pueda administrar desde la aplicación, y que FastAPI consulte esa relación en cada petición para autorizar. La matriz `PERMISOS` de `backend/app/core/permissions.py` y las listas de roles de `frontend/src/features/authentication/permissions.js` dejan de ser la fuente de verdad.

## 2. Alcance

### Incluye

- Tablas `permisos` y `rol_permisos`, relacionadas con la tabla existente `roles`.
- Catálogo de permisos con códigos `modulo.accion` y carga inicial equivalente a la matriz actual.
- Autorización en backend basada en la base: `require_permission(<código>)` consulta `rol_permisos` del rol vigente del usuario.
- API para consultar roles, consultar el catálogo de permisos y reemplazar los permisos de un rol.
- Permisos efectivos del usuario en `GET /api/auth/me` y en la respuesta del login, solo para que el frontend decida qué mostrar.
- Frontend: el "Panel de roles" pasa a ser **Administración** con dos pestañas, **[ Usuarios ] [ Roles y permisos ]**. En la segunda, el administrador elige un rol y marca o desmarca sus permisos.
- Migración de todos los `require_permission("GESTIONAR_…")` existentes a los nuevos códigos.

### Fuera de alcance

- Crear, renombrar o eliminar roles. Los roles siguen siendo Administrador, Almacenero y Operario.
- Permisos por usuario individual (solo por rol).
- Historial o auditoría de cambios de permisos (se deja como mejora futura).
- La migración Alembic definitiva: se propone el modelo, pero se genera solo después de coordinarla con la migración del módulo de optimización para mantener una sola línea de revisiones.

## 3. Actor y precondiciones

**Actores:** Administrador (configura permisos); cualquier usuario autenticado (es autorizado según su rol).

**Precondiciones:**

- Los tres roles existen en `roles`.
- El catálogo de permisos y su asignación inicial están cargados.
- El usuario tiene sesión válida (JWT) y cuenta activa.

## 4. Entradas y datos

### 4.1 Modelo propuesto

```text
roles (existente)            permisos (nueva)                     rol_permisos (nueva)
─────────────────            ────────────────                     ────────────────────
id_rol        PK             id_permiso   PK                      id_rol      PK, FK → roles.id_rol        ON DELETE CASCADE
nombre        UNIQUE         codigo       VARCHAR(50) UNIQUE      id_permiso  PK, FK → permisos.id_permiso ON DELETE CASCADE
descripcion                  modulo       VARCHAR(30)
                             descripcion  VARCHAR(150)
```

- `rol_permisos` tiene clave primaria compuesta `(id_rol, id_permiso)`: un rol no puede tener el mismo permiso dos veces.
- `permisos.codigo` con CHECK `codigo ~ '^[a-z]+\.[a-z]+$'` y `modulo` igual a la parte anterior al punto.
- Índice en `rol_permisos(id_rol)` para la consulta de autorización. La clave compuesta ya lo cubre por ser su primer componente.

### 4.2 Catálogo de permisos

| Código | Módulo | Descripción |
|---|---|---|
| `users.view` | users | Ver usuarios y roles disponibles |
| `users.manage` | users | Crear, editar, activar y desactivar usuarios |
| `roles.view` | roles | Ver roles y sus permisos |
| `roles.manage` | roles | Cambiar los permisos de un rol |
| `inventory.view` | inventory | Ver catálogo de vidrio, planchas, retazos e historial |
| `inventory.manage` | inventory | Registrar, editar y dar de baja tipos, planchas y retazos |
| `orders.view` | orders | Ver pedidos y clientes |
| `orders.create` | orders | Registrar pedidos y clientes |
| `orders.update` | orders | Editar pedidos pendientes |
| `orders.cancel` | orders | Cancelar pedidos pendientes |
| `optimization.view` | optimization | Ver resultados de optimización |
| `optimization.execute` | optimization | Ejecutar la optimización y la rasterización |
| `optimization.confirm` | optimization | Confirmar una solución (descuenta stock) |

El catálogo se mantiene en código (`app/core/permissions.py`, solo códigos y descripciones, sin roles) y se carga en la tabla. Es correcto que el código conozca los nombres de los permisos, porque cada endpoint declara el suyo; lo que deja de estar en código es **qué rol tiene qué permiso**.

### 4.3 Asignación inicial (equivalente a la matriz actual)

| Permiso | Administrador | Almacenero | Operario |
|---|---|---|---|
| `users.view`, `users.manage` | ✔ | | |
| `roles.view`, `roles.manage` | ✔ | | |
| `inventory.view` | ✔ | ✔ | ✔ |
| `inventory.manage` | ✔ | ✔ | |
| `orders.view`, `orders.create`, `orders.update`, `orders.cancel` | ✔ | | ✔ |
| `optimization.view` | ✔ | ✔ | ✔ |
| `optimization.execute` | ✔ | | ✔ |
| `optimization.confirm` | ✔ | | ✔ |

### 4.4 Endpoints existentes y permiso requerido

| Método y ruta | Permiso actual | Permiso nuevo |
|---|---|---|
| GET `/api/users`, `/api/users/{id}`, `/api/users/roles` | GESTIONAR_USUARIOS | `users.view` |
| POST `/api/users`, PATCH `/api/users/{id}` | GESTIONAR_USUARIOS | `users.manage` |
| GET `/api/inventory/tipos-vidrio`, `/planchas`, `/retazos`, `…/movimientos` | CONSULTAR_TIPOS_VIDRIO / CONSULTAR_STOCK | `inventory.view` |
| POST/PATCH de tipos, planchas y retazos, y bajas | GESTIONAR_TIPOS_VIDRIO / PLANCHAS / RETAZOS | `inventory.manage` |
| GET `/api/orders`, `/api/orders/{id}`, GET `/api/clients` | GESTIONAR_PEDIDOS | `orders.view` |
| POST `/api/orders`, POST `/api/clients` | GESTIONAR_PEDIDOS | `orders.create` |
| PUT `/api/orders/{id}` | GESTIONAR_PEDIDOS | `orders.update` |
| DELETE `/api/orders/{id}` | GESTIONAR_PEDIDOS | `orders.cancel` |
| POST `/api/optimization/start`, `/api/optimization/rasterize` | EJECUTAR_OPTIMIZACION | `optimization.execute` |

### 4.5 API nueva

| Método y ruta | Permiso | Entrada | Respuesta |
|---|---|---|---|
| GET `/api/roles` | `roles.view` | — | `[{id_rol, nombre, descripcion, permisos: [codigo]}]` |
| GET `/api/permissions` | `roles.view` | — | `[{codigo, modulo, descripcion}]` ordenado por módulo y código |
| PUT `/api/roles/{id_rol}/permissions` | `roles.manage` | `{"permisos": ["inventory.view", …]}` | rol actualizado, mismo formato que GET |
| GET `/api/auth/me` (cambia) | sesión | — | se agrega `permisos: [codigo]` del rol vigente |
| POST `/api/auth/login` (cambia) | público | — | `usuario` incluye `permisos: [codigo]` |

`PUT` **reemplaza** el conjunto completo de permisos del rol en una sola transacción. No se agregan ni quitan permisos uno por uno, así el estado final siempre es exactamente lo enviado.

## 5. Reglas de negocio

- **RN-01 Fuente de verdad:** un rol tiene un permiso si y solo si existe la fila en `rol_permisos`. No existe otra matriz en backend ni frontend.
- **RN-02 Autorización en cada petición:** el backend consulta los permisos del **rol vigente en la base** en cada petición protegida. No se leen del token ni de la petición, así un cambio de permisos rige en la siguiente petición, sin volver a iniciar sesión.
- **RN-03 Backend como autoridad:** ocultar una opción en el frontend es solo presentación. Toda operación protegida valida el permiso en el backend; sin permiso responde 403 aunque la petición se haga a mano.
- **RN-04 Sin escalada:** la API ignora cualquier rol o permiso enviado por el cliente fuera de `PUT /api/roles/{id}/permissions`, y ese endpoint exige `roles.manage`.
- **RN-05 Protección contra bloqueo:** el rol **Administrador** debe conservar siempre `roles.view` y `roles.manage`. Un PUT que los quite responde 409 y no cambia nada, para que nadie deje el sistema sin quién administre permisos.
- **RN-06 Códigos válidos:** solo se aceptan códigos existentes en `permisos`; la lista se deduplica; una lista vacía es válida (rol sin permisos), salvo lo indicado en RN-05.
- **RN-07 Atomicidad:** el reemplazo de permisos de un rol ocurre en una transacción; ante cualquier error no queda un estado intermedio.
- **RN-08 Permiso desconocido en código:** si un endpoint declara un código que no está en el catálogo, la aplicación falla en las pruebas (verificación estática), no en producción.

## 6. Flujo principal

### 6.1 Autorización de una operación

1. El usuario hace una petición con su token.
2. `get_current_user` valida el token y lee la cuenta activa con su rol vigente.
3. `require_permission("inventory.manage")` consulta si `rol_permisos` tiene la fila (rol del usuario, permiso).
4. Si existe, la operación continúa; si no, responde 403.

### 6.2 Administración de permisos

1. El administrador abre **Administración → Roles y permisos**.
2. El frontend carga `GET /api/roles` y `GET /api/permissions`.
3. Selecciona un rol; se muestran los permisos agrupados por módulo con su casilla marcada o no.
4. Marca o desmarca y presiona **Guardar cambios**.
5. El frontend envía `PUT /api/roles/{id}/permissions` con la lista completa.
6. El backend valida y reemplaza; responde el rol actualizado y el frontend muestra el mensaje de éxito.
7. Si el rol modificado es el del propio usuario, el frontend vuelve a consultar `GET /api/auth/me` para actualizar su menú.

## 7. Flujos alternativos y errores

| Caso | Respuesta |
|---|---|
| Sin sesión o token inválido | 401 (sin cambios respecto a hoy) |
| Usuario sin el permiso requerido | 403 `No tienes permiso para realizar esta acción.` (sin revelar el código ni la matriz) |
| Rol inexistente en PUT | 404 |
| Código de permiso inexistente o formato inválido | 422 con los códigos rechazados |
| PUT que quita `roles.view` o `roles.manage` al Administrador | 409 y sin cambios |
| Error de base de datos | 500 genérico, sin SQL ni stack trace; la transacción se revierte |
| Frontend: error al guardar | mensaje de error del patrón compartido; las casillas vuelven al último estado guardado |

## 8. Criterios de aceptación

- **CA-01** Los permisos de cada rol se obtienen de `rol_permisos`; no existe matriz rol→permiso en backend ni frontend.
- **CA-02** La carga inicial deja a los tres roles con exactamente los permisos de la tabla 4.3.
- **CA-03** Un usuario cuyo rol no tiene el permiso de un endpoint recibe 403.
- **CA-04** Un usuario cuyo rol sí lo tiene accede con normalidad.
- **CA-05** Tras `PUT /api/roles/{id}/permissions`, los permisos quedan persistidos: un GET posterior y una nueva petición protegida reflejan el cambio sin reiniciar la API ni volver a iniciar sesión.
- **CA-06** Un usuario no gana permisos manipulando el frontend: peticiones directas a endpoints sin permiso, un `PUT` de permisos sin `roles.manage` o un token con rol o permisos alterados responden 401/403 y no cambian nada.
- **CA-07** No es posible quitar `roles.view` ni `roles.manage` al Administrador (409).
- **CA-08** Códigos inexistentes responden 422 y no modifican nada.
- **CA-09** `GET /api/auth/me` devuelve los permisos efectivos del rol vigente.
- **CA-10** El frontend muestra **Administración** con las pestañas **Usuarios** y **Roles y permisos**, con el diseño visual actual; las opciones del menú dependen de los permisos recibidos y no de listas de roles.
- **CA-11** Todos los endpoints existentes usan un código del catálogo (verificación automática).

## 9. Impacto técnico

- **Módulos backend:**
  - `authentication`: `require_permission` y `/me` consultan permisos en la base mediante un puerto `PermissionReader`.
  - `users`: casos de uso y API de roles y permisos.
  - `core/permissions.py`: queda solo el catálogo de códigos.
  - `inventory`, `orders`, `clients`, `optimization`: **solo cambia el código de permiso** en sus dependencias, sin tocar su lógica. Se avisa al equipo antes de modificarlos.
- **API:** 3 endpoints nuevos; `/me` y login agregan `permisos`.
- **BD / migración:** 2 tablas nuevas y carga inicial. Migración **pendiente de coordinación** (ver PLAN §4); no se crea hasta acordar el orden con la de optimización.
- **UI:** `features/users` (pestañas y panel de permisos), `features/authentication/permissions.js` (helpers por permiso), `Sidebar` (rótulo y condición).

## 10. Pruebas previstas

Detalle y ubicación en PLAN §8. Resumen:

- Unitarias: catálogo, caso de uso de reemplazo, RN-05, RN-06.
- Integración con BD: permisos leídos de la base y persistencia del reemplazo.
- API: 403 sin permiso, acceso con permiso, persistencia tras PUT, protección contra manipulación, `/me`.
- Estática: todos los `require_permission` usan códigos del catálogo.
- Frontend: helpers por permiso, menú, pestañas y panel de roles.
- E2E: cambiar un permiso desde la interfaz y comprobar el efecto con otro rol.

## 11. Evidencias requeridas

- Salida de pytest, Vitest, lint y build.
- Capturas del panel **Roles y permisos** antes y después de un cambio.
- Prueba de 403 con una petición directa (sin pasar por el frontend).
- Ubicación: `docs/evidence/sprint-01/S1-RBAC/`.

## 12. Decisiones y preguntas abiertas

- **D-01** `CONFIGURAR_OPTIMIZADOR` (hoy solo Administrador) no está en la lista de ejemplo. Propuesta: agregar `optimization.configure` cuando exista el endpoint de configuración. Pendiente de confirmar.
- **D-02** Migración Alembic: se propone que dependa del head actual `ta036a1b2c3d`, o de la migración de optimización si se integra antes. Se decide con el equipo antes de generarla.
- **D-03** `GET /api/users/roles` se mantiene para el formulario de usuarios; `GET /api/roles` es el endpoint completo de administración.