# Evidencia TA-QA-006 — Seguridad y permisos por rol

| Campo | Valor |
|---|---|
| Tarea | TA-QA-006 (1 SP, Alta) |
| Característica ISO/IEC 25010 | Seguridad; cubre el vacío V-01 del [modelo de calidad](../../../quality/ISO-25010-modelo-calidad.md) |
| SPEC | [SPEC-TA-QA-006](../../../specs/SPEC-TA-QA-006-seguridad-permisos.md) (Implemented) |
| Rama | `test/S2-TA-QA-006-seguridad-permisos`, desde `integration-02` en `137f2cc` |
| Responsable | Fabricio Danniel Aguilar Chavez (`fabrilar1`) |
| Reviewer | Andro Joseph Quispe Cesias |
| Fecha | 10/11/2026 |

## Qué se entregó

- **Matriz automatizada rol × ruta** de las 59 rutas protegidas con los tres roles
  reales: `backend/tests/api/authorization/test_security_role_matrix.py` (298 casos).
- **Token vencido, firma inválida y cuenta desactivada** en una ruta de negocio por
  cada camino de autorización: `backend/tests/api/authorization/test_security_token_paths.py`
  (8 casos).
- **Rechazos sin cambio de stock real** con PostgreSQL:
  `backend/tests/api/optimization/test_security_rejections_postgres.py` (3 pruebas,
  4 casos, solo en el CI).
- [`docs/seguridad/matriz_permisos.md`](../../../seguridad/matriz_permisos.md) actualizada.
- Vacío **V-19** (login sin límite de intentos) agregado al modelo de calidad.

Sin cambios en `backend/app/`, `frontend/`, migraciones, contrato de la API ni workflows.

## Matriz de resultados

Resultado observado en las pruebas locales, igual al esperado en todos los casos.
"Pasa" = la autorización deja pasar la petición (respuesta distinta de 401 y 403);
"403" = rechazo con el mensaje genérico y sin usar ningún servicio o repositorio.

| Grupo | Rutas | Permiso | Sin token | Administrador | Almacenero | Operario |
|---|---|---|---|---|---|---|
| Sesión (`/api/auth/me`) | 1 | solo sesión | 401 (1/1) | Pasa | Pasa | Pasa |
| Usuarios | 5 | `users.view`, `users.manage` | 401 (5/5) | Pasa | 403 (5/5) | 403 (5/5) |
| Roles y permisos | 3 | `roles.view`, `roles.manage` | 401 (3/3) | Pasa | 403 (3/3) | 403 (3/3) |
| Inventario (lectura) | 6 | `inventory.view` | 401 (6/6) | Pasa | Pasa | Pasa |
| Inventario (escritura y bajas) | 7 | `inventory.manage` | 401 (7/7) | Pasa | Pasa | 403 (7/7) |
| Pedidos y clientes (lectura) | 3 | `orders.view` | 401 (3/3) | Pasa | 403 (3/3) | Pasa |
| Pedidos y clientes (escritura) | 6 | `orders.create`, `orders.update`, `orders.cancel` | 401 (6/6) | Pasa | 403 (6/6) | Pasa |
| Optimización (inicio) | 5 | `optimization.execute` | 401 (5/5) | Pasa | 403 (5/5) | Pasa |
| Selección y liberación | 4 | `optimization.execute` | 401 (4/4) | Pasa | 403 (4/4) | Pasa |
| Confirmación de cortes | 3 | `optimization.confirm` | 401 (3/3) | Pasa | 403 (3/3) | Pasa |
| Resultados (lectura) | 16 | `optimization.view` | 401 (16/16) | Pasa | Pasa | Pasa |
| **Total** | **59** | | **401: 59/59** | **Pasa: 59** | **403: 29 · Pasa: 30** | **403: 15 · Pasa: 44** |

Token y cuenta en rutas de negocio (6/6 rechazados con 401 y el formato de cada camino):

| Caso | `require_permission` (`POST /api/inventory/planchas`) | `run_permission` (`POST /api/optimization/comparisons-v2`) |
|---|---|---|
| Token vencido | 401 · `{"detail": "Tu sesión expiró. Inicia sesión otra vez."}` | 401 · `{"detail": {"code": "UNAUTHENTICATED", "message": "Tu sesión expiró. Inicia sesión otra vez."}}` |
| Firma inválida | 401 · `{"detail": "Sesión no válida. Inicia sesión otra vez."}` | 401 · mismo mensaje con `code: UNAUTHENTICATED` |
| Cuenta desactivada | 401 · `{"detail": "La cuenta no existe o está desactivada."}` | 401 · mismo mensaje con `code: UNAUTHENTICATED` |
| Control: token válido | Pasa y llega al servicio | Pasa y llega al servicio |

Rechazos con PostgreSQL (CI), cada uno con control positivo:

| Caso | Rechazo esperado | Datos que no deben cambiar | Control positivo |
|---|---|---|---|
| Almacenero confirma un run | 403 `FORBIDDEN` | Pedidos, piezas, planchas, retazos, movimientos y optimización | Operario confirma → 200 |
| Almacenero confirma una comparisons-v2 | 403 `FORBIDDEN` | Los mismos, plancha 5 con 2 unidades y sin movimientos | Operario confirma → 200 |
| Operario da de baja una plancha | 403 | Planchas, retazos y movimientos | Almacenero → 201 |
| Operario da de baja un retazo | 403 | Planchas, retazos y movimientos | Almacenero → 201 |

Resultado en el CI: ver [CI del PR](#ci-del-pr).

## Métricas de seguridad medidas

Métricas del proyecto definidas en SPEC-TA-QA-006 §5.3; las metas son del proyecto, no
de la norma.

| ID | Métrica | Meta | Resultado | Estado |
|---|---|---|---|---|
| MSEG-01 | Cobertura de control de acceso en rutas protegidas | 100 % | 59/59 = **100 %**. La prueba RN-07 confirma que la aplicación tiene exactamente esas 59 rutas protegidas. | Cumple |
| MSEG-02 | Tasa de rechazo de accesos no autorizados | 100 % | 109/109 = **100 %** (59 sin token + 44 por rol + 6 de token o cuenta). | Cumple (local). Los 4 rechazos con PostgreSQL se confirman en el CI. |
| MSEG-03 | Escrituras no autorizadas ejecutadas | 0 | **0** en los 109 rechazos con espía. | Cumple (local). Los 4 casos con PostgreSQL se confirman en el CI. |
| MSEG-04 | Respuestas de error con información interna | 0 | **0** de 109 respuestas 401/403: todas con el mensaje fijo exacto, sin stack trace, SQL ni código de permiso. | Cumple |
| MSEG-05 | Autenticidad del token en rutas de negocio | 100 % | 6/6 = **100 %**. | Cumple |
| MSEG-06 | Conformidad de la matriz documentada | 100 % y 100 % | Antes: 10/11 filas = 90,9 % ("Configurar optimizador" no existe) y 7/13 permisos representados = 53,8 %. **Después: 14/14 filas = 100 % y 13/13 permisos = 100 %.** Además, la matriz de las pruebas coincide con `ASIGNACION_INICIAL` y con las rutas reales. | Cumple |

Para MSEG-06, se cuenta como representado un permiso que tiene una fila propia en la
matriz. En la versión anterior faltaban `users.view`, `roles.view`, `roles.manage`,
`orders.view`, `orders.cancel` y `optimization.confirm`.

## Criterios de aceptación

| CA | Criterio | Cómo se verificó | Resultado |
|---|---|---|---|
| CA-01 | Matriz de pruebas por Administrador / Almacenero / Operario | `test_security_role_matrix.py`: 59 rutas × 3 roles más el permiso declarado, el 401 sin token y la verificación RN-07; tabla de resultados arriba. | Cumple |
| CA-02 | Accesos denegados correctamente | 401 sin token (59), 403 por rol (44), 401 por token vencido, firma inválida o cuenta desactivada en los dos caminos (6), cuerpos exactos y sin información interna. | Cumple |
| CA-03 | Sin confirmación ni consumo no autorizado | Espías sin uso en los 109 rechazos (local). Stock, movimientos y pedidos sin cambios con PostgreSQL, con control positivo. | Cumple en local; **la parte de PostgreSQL queda pendiente del CI** |
| CA-04 | Resultados registrados | Esta evidencia, `matriz_permisos.md` actualizada, V-19 en el modelo de calidad y SPEC en Implemented. | Cumple |

## Salidas de comandos

Comandos ejecutados por el responsable en Windows (PowerShell) el 10/11/2026. Se
registra el resumen de cada salida; no se adjuntan capturas.

### Pruebas nuevas (backend)

```powershell
# Desde backend\ con el venv activo
python -m pytest tests/api/authorization/test_security_role_matrix.py tests/api/authorization/test_security_token_paths.py tests/api/optimization/test_security_rejections_postgres.py -q -ra
```

```text
306 passed, 3 skipped, 1 warning
- 0 failed
- 3 skipped: pruebas con PostgreSQL (sin binarios locales initdb/pg_ctl)
- 1 warning: StarletteDeprecationWarning de fastapi/testclient (preexistente)
```

### Suite completa del backend (Windows)

```powershell
# Desde backend\ con el venv activo; mismos --ignore que se usan en Windows
python -m pytest -q --ignore=tests/unit/optimization/test_comparison_runner.py --ignore=tests/unit/optimization/test_sequential_runner.py --ignore=tests/unit/optimization/test_resource_profile.py
```

```text
2726 passed, 944 skipped, 1 warning
- 0 failed
- 944 skipped: pruebas de API e integración que necesitan PostgreSQL (las corre el CI)
- 1 warning: StarletteDeprecationWarning de fastapi/testclient (preexistente)
```

### CI del PR

En el CI, `NEWGLASS_REQUIRE_POSTGRES=1` hace que una prueba de PostgreSQL **falle en
lugar de omitirse** si falta el clúster (`backend/tests/integration/postgres_support.py`).
Por eso, un job `backend` en verde demuestra que las 3 pruebas de
`test_security_rejections_postgres.py` se ejecutaron y pasaron.

```text
Run de GitHub Actions: (pendiente: enlace al run del PR)
Job backend:           (pendiente: resultado)
Resumen de pytest:     (pendiente: línea final del paso "Run tests")
```

## Hallazgos

| ID | Hallazgo | Tratamiento |
|---|---|---|
| — | **No se encontró ningún defecto de autorización** en las 59 rutas protegidas. | — |
| O-01 | El servicio de inventario se construye antes de responder 403, sin invocar métodos. | No es defecto. Las pruebas con espía comprueban que no se invoca ningún método. |
| H-01 | `POST /api/auth/login` no limita los intentos fallidos (resistencia). | Fuera de alcance. Registrado como **V-19** en el modelo de calidad. |
| H-02 | Desde FastAPI 0.141.1, `app.routes` contiene `_IncludedRouter` en lugar de las rutas incluidas. | Resuelto en la prueba recorriendo los routers incluidos. No afecta a la aplicación. |

## Limitaciones

- **Login sin límite de intentos** (H-01 / V-19): no se implementa en esta tarea.
- **Configurar optimizador**: no tiene endpoint ni permiso; no hay nada que probar
  (SPEC D-04).
- En la matriz de Windows, "pasa" significa que la autorización deja pasar la petición:
  los dobles no tienen datos. El éxito con datos reales se demuestra en los controles
  positivos con PostgreSQL y en las pruebas funcionales existentes.
- En 23 rutas los tres roles tienen el permiso, así que no hay ningún 403 por rol. En
  ellas el control se verifica con el permiso declarado y el 401; el 403 de esos
  permisos ya lo cubre `test_endpoint_permissions.py`.
- La matriz se verifica sobre `ASIGNACION_INICIAL`. Si un administrador cambia los
  permisos desde Gestión de roles, lo vigente es lo configurado (RBAC configurable).

## Cómo reproducir

Ejecutar los comandos de [Salidas de comandos](#salidas-de-comandos) desde las
carpetas indicadas. Las pruebas de PostgreSQL necesitan
los binarios `initdb` y `pg_ctl` (variable `NEWGLASS_TEST_PG_BIN`), igual que en el CI.
