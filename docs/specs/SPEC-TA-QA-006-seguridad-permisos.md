# SPEC-TA-QA-006 — Seguridad y permisos por rol

## Información general

| Campo | Valor |
|---|---|
| ID | TA-QA-006 |
| Nombre | Seguridad y permisos: matriz de pruebas por rol y métricas de seguridad |
| Tipo | Tarea de calidad (pruebas y documentación, sin cambios de comportamiento) |
| Sprint | Sprint 2 |
| Prioridad / estimación | Alta / 1 SP |
| Versión | 1.1 |
| Estado | **Implemented**: pruebas, evidencia y documentos entregados en este PR; pasa a Verified después de la revisión, el CI verde (pruebas con PostgreSQL) y el merge |
| Responsable | Fabricio Danniel Aguilar Chavez (`fabrilar1`) |
| Reviewer | Andro Joseph Quispe Cesias (distinto del autor) |
| Rama | `test/S2-TA-QA-006-seguridad-permisos` |
| Base | `integration-02` en `137f2cc` (después del PR #114) |
| Fecha | 10/11/2026 |
| Dependencias | EN-003, HU-002 |
| Característica ISO/IEC 25010 | Seguridad (§4.6 del modelo de calidad); cubre el vacío **V-01** |
| Evidencia | [docs/evidence/sprint-02/TA-QA-006](../evidence/sprint-02/TA-QA-006/README.md) |
| Referencias | [Modelo de calidad ISO 25010](../quality/ISO-25010-modelo-calidad.md) · [Matriz TA-QA-001](../quality/TA-QA-001-matriz-metricas-iso25023.md) · [SPEC-S1-RBAC](SPEC-S1-RBAC-roles-permisos-configurables.md) · [matriz_permisos.md](../seguridad/matriz_permisos.md) · [Convenciones de pruebas](../testing/README.md) |

## 1. Objetivo

Demostrar con pruebas automatizadas que el backend **solo deja usar a cada rol
(Administrador, Almacenero, Operario) las rutas que le corresponden**, que los
accesos sin sesión, con token inválido o con cuenta desactivada se rechazan, y que un
intento rechazado **no confirma cortes ni consume stock**.

Además, definir y medir las **métricas de seguridad** que la matriz de TA-QA-001 no
tiene (vacío V-01 del modelo de calidad), sin editar esa matriz.

## 2. Alcance

### Incluye

- Matriz automatizada **rol × ruta protegida** sobre las **59 rutas protegidas**
  (§5.2): permiso declarado, 401 sin token, 403 para el rol sin permiso y paso de la
  autorización para el rol con permiso.
- Verificación automática de que la aplicación tiene **exactamente** las 59 rutas
  protegidas de la matriz, recorriendo sus routers (RN-07).
- Prueba con dobles espía de que, ante un rechazo, **no se invoca** ninguna operación
  de servicio o repositorio (inventario, pedidos, clientes, usuarios, roles,
  optimización, confirmación, selección y liberación). Corre en Windows.
- Pruebas con PostgreSQL (CI) de que un rechazo **no cambia el stock real**:
  confirmación de runs y de comparisons-v2 con Almacenero, y bajas de inventario con
  Operario, cada una con un control positivo del rol autorizado.
- Token vencido, firma inválida y cuenta desactivada en **una ruta de negocio por
  cada camino de autorización** (`require_permission` y `run_permission`), con el
  formato de error propio de cada uno.
- Verificación de que las respuestas 401 y 403 no exponen stack trace, SQL ni el
  código del permiso que falta.
- Métricas de seguridad MSEG-01 a MSEG-06 (§5.3), medidas en la evidencia.
- Actualización de `docs/seguridad/matriz_permisos.md`, que la auditoría F0
  comprobó desactualizada (§4.3).
- Registro del hallazgo H-01 (login sin límite de intentos) y alta del vacío V-19 en
  el modelo de calidad, con línea de historial (§4.4, D-10).

### Fuera de alcance

- Cambiar reglas de negocio, permisos, asignación inicial, contrato de la API o BD.
- **Configurar optimizador**: no existe endpoint ni permiso; los límites del
  optimizador son constantes del código. No se crean permisos (D-04).
- **Limitar intentos de login (resistencia)**: solo se registra como hallazgo H-01 y
  como vacío V-19; no se implementa nada (D-09).
- Cualquier otro cambio en `docs/quality/ISO-25010-modelo-calidad.md` distinto de V-19
  y su historial.
- Rendición de cuentas y no repudio de la confirmación, secretos en el repositorio y
  source maps: se citan como evidencia existente, sin pruebas nuevas.
- Editar la matriz de TA-QA-001 (entregable de Andro) o las pruebas de S1-RBAC.
- Pruebas de permisos en el frontend: la interfaz no es un control de acceso.

## 3. Actores y precondiciones

**Actores:** Administrador, Almacenero, Operario y un cliente HTTP sin sesión o con un
token alterado.

**Precondiciones:**

- Permisos por rol según `ASIGNACION_INICIAL` (`backend/app/core/permissions.py`),
  que es la carga inicial de `rol_permisos`.
- Pruebas de Windows: cuentas y permisos en memoria (`tests/auth_support.py`) y
  dobles para servicios y repositorios. Pruebas de CI: PostgreSQL de pruebas.

## 4. Situación actual (auditoría F0)

Auditoría de solo lectura sobre `integration-02` en `137f2cc`.

### 4.1 Control de acceso en el código

| Hallazgo | Evidencia |
|---|---|
| `get_current_user` responde 401 sin token, con token vencido, con firma o claims inválidos y con cuenta inexistente o desactivada. El rol se lee de la BD, no del token. | `backend/app/modules/authentication/presentation/dependencies.py:56-77` |
| `require_permission(code)` responde 403 con mensaje genérico y lee `rol_permisos` en cada petición. Un código fuera del catálogo falla al importar. | `dependencies.py:80-112` |
| Optimización usa `run_permission`, que reutiliza esas funciones; `RunRoute` convierte los errores a `{"detail": {"code", "message"}}` (`UNAUTHENTICATED`, `FORBIDDEN`). | `optimization/presentation/run_auth.py`, `run_routes.py:27-49` |
| El token se decodifica con algoritmo fijo y claims obligatorios. | `backend/app/shared/security/tokens.py:32-33` |
| 59 rutas protegidas: 58 con permiso y `GET /api/auth/me` solo con sesión. Rutas públicas: `/`, `/health/live`, `/health/ready`, `POST /api/auth/login`. | Routers de `users`, `inventory`, `orders`, `clients`, `optimization` |
| El módulo `configuration` está vacío: no hay endpoint ni permiso para configurar el optimizador. `results` no tiene router propio. | `backend/app/modules/configuration/`, `backend/app/modules/results/` |
| **No se encontró ningún defecto de autorización.** | Revisión de las 59 rutas |

**Observación O-01 (no es defecto):** en las rutas de inventario la dependencia del
servicio se declara antes que la del permiso, así que FastAPI construye el servicio
antes de responder 403, pero no invoca ningún método. Por eso la prueba con espía
comprueba que **no se llama a ningún método**, no que no se construya.

### 4.2 Pruebas existentes

| Prueba | Corre en Windows | Cubre | Vacío |
|---|---|---|---|
| `tests/api/authorization/test_endpoint_permissions.py` | Sí | 32 de 58 rutas: 403 sin el permiso y paso con solo ese permiso | Rol sintético, no los tres roles reales. Faltan las 21 de comparisons, `import/*`, `retazos/{id}/origen` y `runs/{id}/visual*` |
| `test_permissions_from_database.py`, `test_roles_api.py`, `test_require_permission.py` | Sí | RBAC desde la BD, roles, rol falsificado en el token | — |
| `tests/api/test_auth_api.py`, `tests/unit/shared/test_tokens.py` | Sí | Token vencido, firma ajena, malformado, incompleto, cuenta desactivada | Solo sobre `/api/auth/me`; nada sobre rutas de negocio ni sobre `run_permission` |
| `tests/api/test_users_api.py` | Sí | Rutas de users: 401, y 403 para Almacenero y Operario | — |
| `tests/api/inventory/test_inventory_api.py` | Sí | Solo `POST tipos-vidrio` con Operario → 403 | Bajas y PATCH sin prueba por rol real ni de no invocación |
| `tests/api/optimization/test_confirmation_api.py` | No (PostgreSQL) | Confirmación de runs rechazada por permiso revocado, sin cambio de stock | No prueba el rol Almacenero |
| `tests/api/optimization/test_comparison_v2_confirmation_api.py` | No (PostgreSQL) | 403 de confirmación v2 con permiso revocado | No verifica el stock; no hay 403 de selection ni de release |
| `tests/api/test_validation_errors_sanitized.py` | Sí | Los 422 no devuelven la contraseña | Nada transversal sobre 401/403 |

### 4.3 `matriz_permisos.md` frente al RBAC

Las 11 filas existentes coinciden con `ASIGNACION_INICIAL`, pero el documento está
**desactualizado**: incluye "Configurar optimizador", que no existe; le faltan
roles y permisos, confirmar solución, cancelar pedidos, consultar pedidos y clientes,
registrar clientes, bajas manuales, selección y liberación; y no aclara que es la
asignación inicial de un RBAC configurable.

### 4.4 Hallazgo H-01: login sin límite de intentos

| Campo | Contenido |
|---|---|
| Hallazgo | `POST /api/auth/login` no limita los intentos fallidos por cuenta ni por origen: un cliente puede probar contraseñas sin bloqueo ni espera. |
| Evidencia | `backend/app/modules/authentication/presentation/router.py:25-58` (sin contador ni bloqueo). Búsqueda de `rate`, `limit`, `attempt`, `intento`, `throttl`, `lockout` y `bloque` en `backend/app/modules/authentication/`: sin coincidencias relacionadas. |
| Mitigaciones actuales | Mensaje único ante credenciales incorrectas (no revela si la cuenta existe), bcrypt con costo deliberado y validación de formato del usuario antes de consultar la base. |
| Subcaracterística ISO 25010 | Resistencia (*resistance*). |
| Tratamiento | Fuera de alcance de TA-QA-006 (D-09): no se implementa nada. Se registra como vacío V-19 en el modelo de calidad (D-10). |

**Texto agregado a `docs/quality/ISO-25010-modelo-calidad.md`, §5.2:**

```markdown
| V-19 | Resistencia sin control: `POST /api/auth/login` no limita los intentos fallidos por cuenta ni por origen (hallazgo H-01 de TA-QA-006). Mitigaciones actuales: mensaje único, bcrypt y validación de formato. Falta decidir la regla (umbral, ventana y bloqueo temporal) y su métrica. | Por asignar (nueva tarea del backlog; fuera de TA-QA-006) |
```

## 5. Reglas y contrato verificado

### 5.1 Reglas

- RN-01: Sin token, toda ruta protegida responde **401**.
- RN-02: Un rol sin el permiso exigido recibe **403**; el rol con el permiso pasa la
  autorización (respuesta distinta de 401 y 403).
- RN-03: Ante un 401 o 403, el backend **no invoca** ninguna operación de servicio o
  repositorio, y el stock, los movimientos y el estado de los pedidos no cambian.
- RN-04: Token vencido, firma inválida y cuenta desactivada responden **401** en
  rutas de negocio por ambos caminos:
  - `require_permission`: cuerpo `{"detail": "<mensaje fijo>"}` y cabecera
    `WWW-Authenticate: Bearer`.
  - `run_permission`: cuerpo `{"detail": {"code": "UNAUTHENTICATED", "message": "<mensaje fijo>"}}`.
- RN-05: Los cuerpos 401 y 403 solo contienen los mensajes fijos de autenticación y
  autorización: sin stack trace, SQL ni el código del permiso.
- RN-06: El permiso declarado en cada ruta protegida coincide con la matriz §5.2;
  `GET /api/auth/me` solo exige sesión.
- RN-07: La aplicación tiene exactamente 59 rutas protegidas (que exigen un permiso o
  una sesión) y son las de la matriz §5.2. Una ruta protegida nueva o eliminada hace
  fallar la prueba hasta que se actualicen la matriz y esta SPEC.

### 5.2 Rutas protegidas y resultado esperado por rol

Permisos según `ASIGNACION_INICIAL`. ✔ = pasa la autorización; ✘ = 403. "Crítica"
marca las 28 rutas que escriben o administran (D-01); las pruebas con PostgreSQL se
hacen sobre rutas críticas.

| Grupo | Rutas | Permiso | Crítica | Admin | Almacenero | Operario |
|---|---|---|---|---|---|---|
| Sesión | `GET /api/auth/me` | solo sesión | No | ✔ | ✔ | ✔ |
| Usuarios | `GET /api/users`, `GET /api/users/roles`, `GET /api/users/{id}` | `users.view` | Sí | ✔ | ✘ | ✘ |
| | `POST /api/users`, `PATCH /api/users/{id}` | `users.manage` | Sí | ✔ | ✘ | ✘ |
| Roles y permisos | `GET /api/roles`, `GET /api/permissions` | `roles.view` | Sí | ✔ | ✘ | ✘ |
| | `PUT /api/roles/{id}/permissions` | `roles.manage` | Sí | ✔ | ✘ | ✘ |
| Inventario (lectura) | `GET /api/inventory/tipos-vidrio`, `GET /api/inventory/planchas`, `GET /api/inventory/planchas/{id}/movimientos`, `GET /api/inventory/retazos`, `GET /api/inventory/retazos/{id}/movimientos`, `GET /api/inventory/retazos/{id}/origen` | `inventory.view` | No | ✔ | ✔ | ✔ |
| Inventario (escritura y bajas) | `POST /api/inventory/tipos-vidrio`, `POST /api/inventory/planchas`, `PATCH /api/inventory/planchas/{id}`, `POST /api/inventory/planchas/{id}/baja`, `POST /api/inventory/retazos`, `PATCH /api/inventory/retazos/{id}`, `POST /api/inventory/retazos/{id}/baja` | `inventory.manage` | Sí | ✔ | ✔ | ✘ |
| Pedidos y clientes (lectura) | `GET /api/orders`, `GET /api/orders/{id}`, `GET /api/clients` | `orders.view` | No | ✔ | ✘ | ✔ |
| Pedidos y clientes (escritura) | `POST /api/orders`, `POST /api/orders/import/preview`, `POST /api/orders/import/validate`, `POST /api/clients` | `orders.create` | Sí | ✔ | ✘ | ✔ |
| | `PUT /api/orders/{id}` | `orders.update` | Sí | ✔ | ✘ | ✔ |
| | `DELETE /api/orders/{id}` | `orders.cancel` | Sí | ✔ | ✘ | ✔ |
| Optimización (inicio) | `POST /api/optimization/start`, `POST /api/optimization/rasterize`, `POST /api/optimization/runs`, `POST /api/optimization/comparisons`, `POST /api/optimization/comparisons-v2` | `optimization.execute` | No | ✔ | ✘ | ✔ |
| Selección y liberación | `PUT …/comparisons/{id}/selection`, `PUT …/comparisons-v2/{id}/selection`, `POST …/comparisons/{id}/release`, `POST …/comparisons-v2/{id}/release` | `optimization.execute` | Sí | ✔ | ✘ | ✔ |
| Confirmación de cortes | `POST …/runs/{id}/confirm`, `POST …/comparisons/{id}/confirm`, `POST …/comparisons-v2/{id}/confirm` | `optimization.confirm` | Sí | ✔ | ✘ | ✔ |
| Resultados (lectura) | runs: `GET …/runs/{id}`, `GET …/runs/{id}/visual`, `GET …/runs/{id}/visual/masks/{ref}`; comparisons: `GET …/requests/{key}`, `GET …/{id}`, `GET …/{id}/executions/{eid}`, `GET …/{id}/events`, `GET …/{id}/executions/{eid}/visual`, `GET …/{id}/executions/{eid}/visual/masks/{ref}`; comparisons-v2: las mismas seis más `GET …/history` | `optimization.view` | No | ✔ | ✔ | ✔ |

`…` = `/api/optimization`.

**Origen de las 59 rutas en la matriz:**

- 28 rutas críticas (D-01).
- 18 rutas sin prueba de 403 en Windows antes de esta tarea (D-08): 16 GET de
  resultados (`retazos/{id}/origen`, `runs/{id}/visual`, `runs/{id}/visual/masks/{ref}`,
  6 de comparisons y 7 de comparisons-v2) y los 2 POST que inician una comparación
  (`comparisons` y `comparisons-v2`).
- 13 rutas restantes, para medir MSEG-01 sobre las 59 con un criterio único (D-08):
  `GET /api/auth/me`, 5 lecturas de inventario, 3 lecturas de pedidos y clientes,
  `start`, `rasterize`, `POST runs` y `GET runs/{id}`.

**Totales de la matriz:**

| Concepto | Casos |
|---|---|
| Coherencia: totales de la matriz y resultado esperado frente a `ASIGNACION_INICIAL` | 2 |
| Rutas protegidas de la aplicación = rutas de la matriz (RN-07) | 1 |
| Permiso declarado (RN-06) | 59 |
| Sin token → 401 | 59 |
| Rol × ruta | 177 (59 × 3) |
| · Rechazos esperados (403) | **44**: Almacenero 29, Operario 15, Administrador 0 |
| · Pasos esperados | **133**: Administrador 59, Almacenero 30, Operario 44 |
| **Total** | **298** |

En 23 rutas los tres roles pasan (`/api/auth/me`, inventario de lectura y
resultados de lectura). En ellas el control de acceso se verifica con el permiso
declarado (RN-06) y el 401; el 403 de esos permisos ya está probado en
`test_endpoint_permissions.py` con un rol sin el permiso.

### 5.3 Métricas de seguridad propuestas

Métricas del proyecto, inspiradas en las medidas de confidencialidad, integridad y
autenticidad de ISO/IEC 25023; las metas son del proyecto, no de la norma. Cubren el
vacío V-01 sin editar la matriz de TA-QA-001.

| ID | Métrica | Subcaracterística | Fórmula | Meta | Fuente de medición |
|---|---|---|---|---|---|
| MSEG-01 | Cobertura de control de acceso en rutas protegidas | Confidencialidad / integridad | rutas protegidas con control verificado ÷ 59 × 100. Una ruta cuenta como verificada si su permiso declarado coincide con §5.2, responde 401 sin token y los tres roles obtienen el resultado esperado (403 o paso). El denominador se comprueba con RN-07: la aplicación tiene exactamente esas 59 rutas protegidas | 100 % | Matriz automatizada §5.2 y verificación RN-07 |
| MSEG-02 | Tasa de rechazo de accesos no autorizados | Confidencialidad / integridad | intentos no autorizados respondidos con 401/403 ÷ intentos no autorizados ejecutados × 100 | 100 % | 109 intentos: 59 sin token + 44 por rol + 6 de token o cuenta |
| MSEG-03 | Escrituras no autorizadas ejecutadas | Integridad | rechazos con una operación de servicio o repositorio invocada (espía) + rechazos con stock, movimientos o pedidos cambiados (PostgreSQL) | 0 | 109 rechazos con espía y 4 casos con PostgreSQL |
| MSEG-04 | Respuestas de error con información interna | Confidencialidad | respuestas 401/403 con texto distinto de los mensajes fijos, stack trace, SQL o código de permiso | 0 | Las 109 respuestas 401/403 de Windows y los 403 de PostgreSQL |
| MSEG-05 | Autenticidad del token en rutas de negocio | Autenticidad | casos (vencido, firma inválida, cuenta desactivada) × caminos (`require_permission`, `run_permission`) rechazados con 401 y el formato de §5.1 ÷ 6 × 100 | 100 % | Pruebas de token |
| MSEG-06 | Conformidad de la matriz documentada | Integridad (prueba + revisión) | filas de `matriz_permisos.md` que coinciden con `ASIGNACION_INICIAL` ÷ filas × 100, y permisos del catálogo representados ÷ 13 × 100 | 100 % y 100 % | Revisión documental, apoyada en dos pruebas: la matriz de las pruebas coincide con `ASIGNACION_INICIAL` y con las rutas reales de la aplicación (RN-07) |

## 6. Decisiones y preguntas abiertas

### Decisiones

| ID | Decisión | Motivo |
|---|---|---|
| D-01 | Rutas críticas: inventario (escritura y bajas), escritura de pedidos y clientes, confirmación, selección, liberación, usuarios y roles (28 rutas). | Decisión del responsable (P-01 de F0, 10/11/2026). Se incluyen pedidos y clientes para demostrar que el Almacenero no tiene permisos de pedidos. |
| D-02 | En la matriz de Windows, "paso del rol autorizado" significa respuesta distinta de 401 y 403. Los dobles no tienen datos, así que la respuesta puede ser 404, 422 o 500 seguro. | Mismo criterio que S1-RBAC. El éxito real con datos se demuestra con los controles positivos de PostgreSQL (D-03) y las pruebas funcionales existentes. |
| D-03 | Se prueban las dos cosas: con espía, que no se invoca la escritura (Windows), y con PostgreSQL, que el stock real no cambia (CI): confirmación de runs y de comparisons-v2 con Almacenero, y bajas con Operario. Cada caso tiene control positivo con el rol autorizado. | Decisión del responsable (P-02 de F0). El control positivo descarta que el 403 venga de datos no confirmables. |
| D-04 | "Configurar optimizador" queda fuera de alcance y sin endpoint; no se crean permisos. | Decisión del responsable (P-03 de F0). Crear un permiso cambiaría el contrato. |
| D-05 | Token vencido, firma inválida y cuenta desactivada se prueban en `POST /api/inventory/planchas` (`require_permission`) y en `POST /api/optimization/comparisons-v2` (`run_permission`). | Pedido del responsable: una ruta de negocio por camino, con su formato de error. |
| D-06 | Las pruebas van en archivos nuevos con nombre único; no se editan `test_endpoint_permissions.py` ni otras pruebas de S1-RBAC. | Regla del equipo sobre archivos de otros integrantes. |
| D-07 | `matriz_permisos.md` se actualiza indicando fuente (`ASIGNACION_INICIAL`) y fecha, y aclarando que es la asignación inicial de un RBAC configurable. | La auditoría F0 la comprobó desactualizada (§4.3). |
| D-08 | La matriz cubre las 59 rutas protegidas: las 28 críticas, las 18 sin prueba de 403 en Windows y las 13 restantes. El resultado esperado se deriva de `ASIGNACION_INICIAL`. MSEG-01 se mide sobre las 59. | Decisión del responsable (cierre de P-02 de F1, 10/11/2026): incluir las 18 y medir MSEG-01 sobre las rutas protegidas. Las 13 restantes se agregan para que la meta del 100 % se mida con un solo criterio. |
| D-09 | La limitación de intentos de login queda fuera de alcance. Se registra como hallazgo H-01 y se propone el vacío V-19 (§4.4). | Decisión del responsable (cierre de P-01 de F1, 10/11/2026). Implementarla cambiaría el comportamiento y el contrato del login. |
| D-10 | V-19 se agrega al modelo de calidad en este PR, con una línea de historial que indica que viene de TA-QA-006. | Decisión del responsable (F3, 10/11/2026). El modelo es entregable de EN-QA-001, del mismo responsable. |
| D-11 | Las rutas se buscan recorriendo los routers incluidos: desde FastAPI 0.141.1, `app.routes` contiene `_IncludedRouter` (con `original_router` e `include_context.prefix`) en lugar de las `APIRoute`. El path resuelto es la concatenación de prefijos más `route.path`, como hace FastAPI. | Hallazgo de F2: la primera versión fallaba con `AttributeError` en las 59 pruebas de permiso declarado. Se revisó `fastapi/routing.py` de la versión instalada. |

### Preguntas abiertas

Ninguna. P-01 se cerró con D-09 y P-02 con D-08.

### Hallazgos

| ID | Hallazgo | Tratamiento |
|---|---|---|
| O-01 | El servicio de inventario se construye antes del 403, sin invocar métodos (§4.1). | No es defecto; las pruebas con espía comprueban que no se invoca ningún método. |
| H-01 | Login sin límite de intentos (§4.4). | Fuera de alcance; registrado como V-19 en el modelo de calidad. |
| H-02 | Desde FastAPI 0.141.1 las rutas incluidas no aparecen directamente en `app.routes` (D-11). | Resuelto en la prueba; no afecta a la aplicación. |
| — | No se encontró ningún defecto de autorización. | — |

## 7. Diseño técnico

| Archivo | Capa | Cambio |
|---|---|---|
| `docs/specs/SPEC-TA-QA-006-seguridad-permisos.md` | Documentación | Nuevo: esta SPEC. |
| `backend/tests/api/authorization/test_security_role_matrix.py` | Pruebas API (Windows) | Nuevo. Matriz §5.2 de 59 rutas parametrizada: coherencia con la SPEC y con `ASIGNACION_INICIAL`, rutas protegidas de la aplicación = matriz (RN-07, recorriendo los routers incluidos según D-11), permiso declarado en la ruta, 401 sin token, 403 por rol y paso del autorizado. Dobles espía para todas las dependencias de servicio y repositorio de esas rutas (inventario, casos de uso de pedidos, clientes, usuarios, roles, inicio y rasterizado, UoW de runs, UoW y runtime de comparisons v1, coordinador de comparisons-v2). Ante 401 o 403, ningún método del espía se invoca. Verifica RN-05 en cada 401/403. |
| `backend/tests/api/authorization/test_security_token_paths.py` | Pruebas API (Windows) | Nuevo. Token vencido, firma inválida y cuenta desactivada en `POST /api/inventory/planchas` y `POST /api/optimization/comparisons-v2`, con el formato de cada camino (RN-04) y sin invocar la escritura. |
| `backend/tests/api/optimization/test_security_rejections_postgres.py` | Pruebas API (PostgreSQL, CI) | Nuevo. Almacenero confirma run → 403, foto de stock, movimientos y pedidos sin cambios; Operario confirma → 200 (control). Igual para la confirmación de comparisons-v2. Operario da de baja plancha y retazo → 403 sin cambios; Almacenero → 201 (control). Reutiliza las fixtures de `test_runs_api`, `test_comparisons_v2_api` y `snapshot`. |
| `docs/seguridad/matriz_permisos.md` | Documentación | Actualizada según D-07. |
| `docs/quality/ISO-25010-modelo-calidad.md` | Documentación | Vacío V-19 en §5.2 y sección de historial con la línea de TA-QA-006 (D-10). |
| `docs/evidence/sprint-02/TA-QA-006/README.md` | Evidencia | Nuevo: matriz de resultados, métricas medidas, hallazgos (O-01, H-01) y limitaciones. |

Sin cambios en `backend/app/`, `frontend/`, migraciones, contrato de la API ni workflows.

## 8. Criterios de aceptación

| ID | Criterio (Notion) | Cómo se verifica |
|---|---|---|
| CA-01 | Matriz de pruebas por Administrador / Almacenero / Operario. | `test_security_role_matrix.py` con las 59 rutas × 3 roles de §5.2 en verde (298 casos, incluida RN-07); tabla de resultados en la evidencia (MSEG-01). |
| CA-02 | Accesos denegados correctamente. | 401 sin token, 403 por rol, 401 por token vencido, firma inválida o cuenta desactivada en ambos caminos y con su formato; cuerpos sin información interna (MSEG-02, MSEG-04, MSEG-05). |
| CA-03 | Sin confirmación ni consumo no autorizado. | Espías sin invocación ante 401/403 (Windows) y stock, movimientos y pedidos sin cambios con PostgreSQL, con control positivo (MSEG-03 = 0). |
| CA-04 | Resultados registrados. | Evidencia con matriz de resultados, métricas medidas, hallazgos y limitaciones; `matriz_permisos.md` actualizada (MSEG-06); H-01 registrado y V-19 agregado al modelo de calidad. |

## 9. Pruebas previstas

| Archivo | Casos | Dónde corre |
|---|---|---|
| `test_security_role_matrix.py` | 2 de coherencia + 1 de rutas protegidas (RN-07) + 59 permisos declarados + 59 sin token + 177 rol × ruta = **298**; no invocación en los 103 rechazos (59 sin token + 44 por rol) | Windows y CI |
| `test_security_token_paths.py` | 3 casos × 2 caminos = 6, más 2 controles positivos = **8** | Windows y CI |
| `test_security_rejections_postgres.py` | 3 pruebas con **4** casos: confirmación de runs, confirmación de comparisons-v2, baja de plancha y baja de retazo, cada uno con control positivo | Solo CI (en Windows se omite) |

Total en Windows: 306 pruebas y 3 omitidas.

Regresión: suite completa del backend con los comandos del CI (`0 failed`).

## 10. Evidencia requerida

- Salida de pytest de los dos archivos de Windows y de la suite completa.
- Resultado del job de CI con el archivo de PostgreSQL.
- `docs/evidence/sprint-02/TA-QA-006/README.md` con la matriz de resultados, el valor
  medido de MSEG-01 a MSEG-06, los hallazgos (O-01, H-01 y V-19, H-02) y
  las limitaciones (login sin límite de intentos, configuración sin endpoint, éxito
  con datos reales solo en los casos de PostgreSQL).
- Capturas de PowerShell que guarda el responsable en esa carpeta.

## Historial de estado

| Fecha | Versión | Estado | Cambio |
|---|---|---|---|
| 10/11/2026 | 1.0 | Draft | Creación con la auditoría F0, matriz de las 59 rutas protegidas, métricas MSEG-01 a MSEG-06, hallazgo H-01 con propuesta de V-19, decisiones D-01 a D-09 y criterios de aceptación. |
| 10/11/2026 | 1.1 | Implemented | Pruebas entregadas: 306 en Windows (298 de la matriz, incluida RN-07, y 8 de tokens) y 3 con PostgreSQL para el CI. RN-07, D-10, D-11 y hallazgos. V-19 agregado al modelo de calidad, `matriz_permisos.md` actualizada y evidencia. Pendiente: CI del PR, revisión y merge para Verified. |
