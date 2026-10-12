# HU-012 T03 — Asociar cliente al pedido

Estado: implementado; validación técnica registrada abajo; **pendiente de revisión humana**. No se declara Verified.
Fecha de trabajo: 09/10/2026 (contexto del usuario).
Rama: `feature/HU-012-T03-asociar-cliente-pedido`.
Base: `6ae091b` de `integration/sprint-01`, actualizada con fetch y pull --ff-only.
T01 integrada: `06ff44e` / `9f605bf`; T02 integrada: `fcf16be`, `6269176`, `f29e744`, merge `36916b6`.

## Objetivo y alcance

Todo pedido nuevo requiere un cliente existente, independiente del usuario que lo registra.
Desde Nuevo pedido se busca por nombre parcial o documento exacto, se selecciona un resultado o
se registra un cliente usando T02. Se envía y persiste `id_cliente`, visible en creación y consulta.
Se conservan las piezas multimaterial HU-006 y el editor real HU-007, incluyendo sus vértices y cantidades.

La pantalla vigente es `frontend/src/features/orders/NuevoPedido.jsx`.
La ruta `frontend/src/pages/NuevoPedido.jsx` citada en el encargo ya no existe en la base integrada.
No se crea una pantalla duplicada.

## Fuentes y decisiones

Revisados [SPEC-HU-012](../../../specs/SPEC-HU-012-gestion-clientes.md),
[evolución BD v1.3 pre-raster](../../../database/evolucion-v1.3-pre-raster.md),
[ADR-002](../../../adr/ADR-002-operacion-pre-raster.md), SPEC-HU006, [evidencia T02](t02-api-clientes.md),
convenciones de pruebas, CONTRIBUTING y feedback compartido TA-034.
El SPEC-HU006 Draft conserva descripciones de material global anteriores al código integrado:
se toma como contrato vigente la persistencia por pieza HU-006 y su regresión multimaterial.

- **Actividad:** ninguna fuente vigente revisada prohíbe asociar clientes inactivos a pedidos nuevos.
  T02 lista activos e inactivos. Se permiten ambos, se muestra su estado y se prueba la decisión.
  No se cambia el estado del cliente. Una futura restricción requiere decisión de negocio explícita.
- **Error de referencia:** `422`, siguiendo la validación de referencias de catálogo en Orders;
  `404` continúa reservado para un pedido consultado que no existe.
- **Respuesta mínima:** se añade solamente `id_cliente`. No se duplica un resumen de cliente en el DTO.
- **Históricos:** GET acepta y expone `id_cliente: null`; BD sigue nullable, sin clientes ficticios.
- **Autorización:** se conserva `GESTIONAR_PEDIDOS`. El usuario sale del JWT validado contra BD.
  El request no puede imponer `id_usuario_registro`. Cliente no contiene password, roles ni login.
- **Arquitectura:** Orders Application depende del puerto read-only `ClientLookup` de Clients Application.
  `SqlAlchemyClientRepository` implementa `exists`; el ensamblaje ocurre en Orders Presentation.
  Se comparte la sesión. No hay HTTP interno ni imports de Presentation de Clients dentro de Orders.
  Domain/Application siguen sin FastAPI, SQLAlchemy ni Pydantic.
- **Transacción:** Orders conserva el commit único después de cabecera y piezas, rollback ante cualquier fallo.
  El lookup no hace commit. La FK de T01 continúa protegiendo la referencia.
- **API frontend:** se reutiliza `ordersApi.js` y se añade `clientsApi.js`, siguiendo fetch, API_URL y token existentes.
  Se elimina el fetch disperso de NuevoPedido y la divergencia VITE_API_BASE_URL; se usa `VITE_API_URL`,
  igual que Auth/Inventory/Users y el entorno E2E existente. No se añaden dependencias.
- **Búsqueda:** botón explícito/Enter, filtro elegido por el operario. Evita consultas por tecla y no combina
  nombre/documento con AND accidentalmente. El documento es exacto, conforme a T02.
- **UI:** resumen visible, estado escrito, cambiar cliente limpia la selección y conserva piezas;
  alta contextual, selección automática, campos opcionales, errores controlados, bloqueo durante solicitudes,
  retorno de foco y cancelación de consultas al desmontar. Limpiar pedido requiere confirmación y limpia
  también el cliente. Guardar sin cliente está bloqueado y explica la causa. Un error conserva el borrador.
- **Responsive:** se conserva la identidad visual y los componentes TA-034. Se adapta el contenedor vigente
  para que el nuevo flujo y las piezas sean utilizables a 390 px; no se rehace la pantalla.

## Flujo y contratos

```text
Nuevo pedido → buscar/registrar cliente (T02) → seleccionar → configurar piezas
→ POST /api/orders → validar ID y existencia → validar piezas → commit
→ GET /api/orders/{id} → id_cliente + usuario + piezas
```

| Endpoint | Contrato T03 |
|---|---|
| `GET /api/clients?query=Norte` | T02 sin cambios: nombre parcial, ambos estados |
| `GET /api/clients?document=DEMO-003` | T02 sin cambios: número exacto |
| `POST /api/clients` | T02 sin cambios: 201; duplicado 409; validación 422 |
| `POST /api/orders` | `id_cliente` requerido, entero estricto positivo <= 2147483647; 201 |
| `GET /api/orders/{id_pedido}` | Incluye `id_cliente` entero o null histórico |

Payload de creación (los IDs deben existir; estos corresponden al entorno sintético):

```json
{
  "id_cliente": 41,
  "piezas": [
    {"id_tipo_vidrio": 7, "espesor_mm": 6, "tipo_forma": "RECTANGULO", "cantidad": 2, "width_mm": 100, "height_mm": 200},
    {"id_tipo_vidrio": 7, "espesor_mm": 5.5, "tipo_forma": "POLIGONO_CONVEXO", "cantidad": 1, "vertices_mm": [[0,0],[100,0],[0,100]]}
  ]
}
```

Respuesta 201 (ID ilustrativo, asignado por PostgreSQL):

```json
{"id_pedido": 1, "id_cliente": 41, "estado": "PENDIENTE"}
```

GET conserva los campos existentes: `id_pedido`, `fecha_registro`, `estado`, `id_usuario_registro`,
`piezas` (IDs, material, espesor, forma, cantidad, dimensiones, geometría y área), y añade `id_cliente`.
Ejemplo abreviado de referencia histórica: `{"id_pedido": 1, "id_cliente": null, ...}`.

Sin `id_cliente`: 422 de schema, localización `body.id_cliente`, tipo `missing`.
Null, bool, string, decimal, cero, negativos y overflow: 422. La aplicación también rechaza ausencia e IDs inválidos.
Cliente inexistente: `422 {"detail":"El cliente seleccionado no existe. Busca o registra otro cliente."}`.
Sesión ausente/inválida: 401; permiso incorrecto: 403. Fallo interno: 500 con mensaje seguro y rollback.
La interfaz traduce errores estructurales 422 y de red; no muestra SQL, tracebacks ni objetos de validación.

## Archivos

### Creados

- `frontend/src/features/clients/clientsApi.js`: GET/POST autenticados reutilizando T02.
- `frontend/src/features/orders/OrderClientSelector.jsx`: búsqueda, selección y alta contextual.
- `frontend/src/features/orders/OrderClientSelector.css`: disposición y estados responsive.
- `frontend/src/features/orders/__tests__/OrderClientSelector.test.jsx`: estados, teclado, errores y payload de alta.
- `frontend/tests/e2e/hu012-client-order.spec.js`: flujo real completo y casos alternativos.
- Este documento y `test-results/t03/`: comandos/resultados de validación.

### Modificados

- Clients: `application/ports.py`, `infrastructure/sqlalchemy_client_repository.py`.
- Orders: `application/ports.py`, `application/use_cases.py`, `infrastructure/repositories.py`,
  `presentation/dependencies.py`, `presentation/router.py`, `presentation/schemas.py`.
- Backend tests: `tests/orders_support.py`, `tests/e2e_server.py`,
  `tests/unit/modules/orders/application/test_use_cases.py`,
  `tests/integration/modules/orders/infrastructure/test_repositories.py`, `tests/api/orders/test_orders_api.py`.
- Frontend Orders: `NuevoPedido.jsx`, `NuevoPedido.css`, `ordersApi.js`.
- Componentes: `NuevoPedido.test.jsx`, `NuevoPedidoFeedback.test.jsx`, `CustomPieceEditor.test.jsx`.
- E2E: `playwright.config.js`, `hu007-order-integration.spec.js`, `hu007-custom-piece.spec.js`.

## Pruebas y regresiones

Se añaden 23 casos backend: 9 de aplicación, 10 de API y 4 de persistencia.
La suite completa recoge 1090 casos frente a los 1067 informados de T02.
Las comprobaciones funcionales anteriores se conservan y reciben un cliente válido en sus fixtures.

Pruebas añadidas: ID ausente/inválido/inexistente sin escrituras; persistencia y lectura de cliente;
usuario y cliente distintos; lookup con activos/inactivos; FK real y recuperación de sesión tras rollback;
lectura histórica nullable; búsqueda por nombre/documento; alta con opcionales; 409/422/error de servidor/red;
foco/teclado; carga/vacío; cambio de cliente; payload con tres formas y materiales por pieza; doble envío;
conservación del borrador; E2E con login, API, PostgreSQL, duplicado y cliente inactivo en dos viewports.

Línea base frontend ejecutada antes de editar la UI: **14 fallos / 63 aprobadas**.
Doce fallos correspondían a NuevoPedido.test.jsx, que esperaba el formulario retirado con material global,
editor permanente y bloqueo de pedidos multimaterial. Se migraron los escenarios al formulario actual:
se mantienen pruebas de cantidades, geometría, catálogo, tres formas, atomicidad del envío y recuperación.
Las dos expectativas restantes eran textos antiguos del editor aislado: se sincronizan con el texto vigente,
conservando los asserts de botón deshabilitado, geometría y descripción accesible. No se cambia su producción.
No se borran casos, se omiten pruebas ni se usan xfail. Los casos de parejas distintas ahora comprueban
la aceptación multimaterial de HU-006, respaldada por el contrato backend.

Al recuperar esos escenarios se detectaron problemas en NuevoPedido: truncaba cantidades decimales,
aceptaba medidas negativas y no bloqueaba la edición durante el envío. Se corrigieron localmente,
reutilizando `validateConvexPolygon`, sin modificar el editor HU-007 ni las reglas geométricas.
El caso integral de tres formas usa 15 s por dibujar y recorrer el editor real en jsdom; no elimina asserts.

Todos los tests de integración utilizan clúster temporal propio, host `127.0.0.1`, usuario `r1_test` y:

```powershell
$env:NEWGLASS_TEST_PG_BIN='C:/Users/Andro/.cache/tooling/hu007-postgres/server/pgsql/bin'
```

No se ejecutan upgrades ni escrituras contra Supabase. Alembic se aplica solamente a bases temporales
mediante el soporte existente. Tests de autenticación aislados conservan SQLite donde ya correspondía;
todas las nuevas pruebas de persistencia Orders/Clients utilizan PostgreSQL real.

| Ejecución | Resultado | Registro |
|---|---|---|
| Orders + Clients (unit/API/integración) | 219 passed, 0 failed/errors/skipped | [orders-clients.txt](test-results/t03/orders-clients.txt) |
| Focalizada ampliada (API, permisos y migraciones pertinentes) | 369 passed, 0 failed/errors/skipped | [backend-focalizado.txt](test-results/t03/backend-focalizado.txt) |
| Backend completo: `python -m pytest` | FULL_PENDING | [backend-completo.txt](test-results/t03/backend-completo.txt) |
| `npm.cmd run test:unit` | 84 passed, 0 fallos/skips | [frontend-unit.txt](test-results/t03/frontend-unit.txt) |
| `npm.cmd run test:component -- --reporter=dot` | 86 passed, 11 archivos | [frontend-components.txt](test-results/t03/frontend-components.txt) |
| `npm.cmd run lint` | Exit 0, sin errores | [frontend-lint.txt](test-results/t03/frontend-lint.txt) |
| `npm.cmd run build` | Exit 0, 1934 módulos, build de producción generado | [frontend-build.txt](test-results/t03/frontend-build.txt) |
| E2E T03: `npm.cmd run test:e2e -- hu012-client-order` | 4 passed, Chrome escritorio/móvil | [e2e-t03.txt](test-results/t03/e2e-t03.txt) |
| E2E completo: `npm.cmd run test:e2e` | 28 passed, sin capturas automáticas | [e2e-completo.txt](test-results/t03/e2e-completo.txt) |
| Compileall + Alembic heads | Exit 0; único head `ef6564220e70` | [backend-checks.txt](test-results/t03/backend-checks.txt) |

Contexto probado: los cambios funcionales y de pruebas que quedaron en `7fd7c08`.
Las suites focalizadas/frontend se ejecutaron antes de crear esos commits, con el mismo contenido;
la suite backend completa se ejecuta sobre `7fd7c08`, con documentación sin commit.

Comando de la ejecución focalizada ampliada desde backend:

```powershell
python -m pytest tests/unit/clients tests/unit/modules/orders tests/api tests/integration/clients tests/integration/modules/orders tests/integration/test_clients_migration.py tests/integration/test_orders_multimaterial_migration.py tests/test_permissions.py -q
```

Warnings observados: Starlette advierte de la deprecación de httpx en TestClient (una advertencia backend).
Playwright/Node advierten del conflicto de variables NO_COLOR/FORCE_COLOR; no afectan resultados.
No se cambian dependencias para silenciarlos. Logs copiados de ejecuciones reales, normalizando UTF-8/finales de línea.
Node v24.21.0, npm 11.19.0, Vite 8.3.1 y Vitest 5.0.3.
No se creó migración; no se modificó `ef6564220e70`.


## Riesgos, límites y fuera de alcance

- El POST ahora exige `id_cliente`: consumidores antiguos deben actualizar su payload. GET histórico sigue compatible.
- El contrato T02 todavía no pagina clientes; el selector requiere búsqueda explícita y limita visualmente el listado.
- El estado inactivo no impide asociación mientras no se apruebe una regla distinta.
- No se añade listado/edición de pedidos, stock candidato HU-008/HU-013, bajas, rasterización, optimización,
  autenticación de clientes, permisos ni cambios de estado. No se inicia HU-013.
- La prueba móvil emula 390×844 en Chrome; no certifica dispositivos físicos ni todos los navegadores/lectores de pantalla.
- No se generan capturas automáticamente, incluyendo screenshots/traces de Playwright. La revisión visual final es humana.
- Entorno ejecutado: Python 3.14.7; README backend cita 3.11.9. Se informa la versión real, sin modificar dependencias.
- No se crea PR, merge ni migración. `main` y Supabase quedan fuera de las operaciones de esta tarea.

## Evidencias manuales para presentación

No se han generado PNG. Los siguientes pasos describen las 16 capturas solicitadas.
Guardar manualmente en `docs/evidence/sprint-01/HU-012/capturas/` si el equipo decide versionarlas.

### Preparación aislada

Cerrar servidores que ocupen 8017/5173. No ejecutar E2E al mismo tiempo que esta demostración.
Terminal A, PostgreSQL temporal y API con usuarios/datos sintéticos:

```powershell
cd C:\Users\Andro\optimizador-vidrio\backend
$env:NEWGLASS_TEST_PG_BIN='C:/Users/Andro/.cache/tooling/hu007-postgres/server/pgsql/bin'
python -m tests.e2e_server
```

Terminal B:

```powershell
cd C:\Users\Andro\optimizador-vidrio\frontend
$env:VITE_API_URL='http://127.0.0.1:8017'
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Abrir `http://127.0.0.1:5173`, iniciar sesión con usuario sintético `O70000001` y contraseña de prueba
`Orders-test-2026!`. Estos valores pertenecen exclusivamente al servidor de pruebas.
El catálogo contiene material 7 y espesores 5.5/6. Clientes preparados:
41 Vidrios Norte / TEST / DEMO-003, activo; 42 Cliente inactivo / TEST / DEMO-004.
Para repetir un alta documental exitosa usar un número nuevo; la unicidad T02 sigue vigente.

### Capturas 01–09: código y comportamiento

| Nº / archivo PNG sugerido | Pasos exactos y qué debe verse | Título de diapositiva |
|---|---|---|
| 01 `HU012-T03-01-arquitectura.png` | Abrir VS Code en la raíz. Mostrar Orders `application/use_cases.py` (validación y puerto), Clients `application/ports.py` y Orders `infrastructure/repositories.py` (asignación/lectura id_cliente). Deben verse capas separadas y la referencia persistida. | Asociación de cliente con arquitectura modular |
| 02 `HU012-T03-02-nuevo-pedido.png` | Entrar a Nuevo pedido después del login; no seleccionar cliente. Mostrar sección Cliente, Buscar por, Nombre del cliente, Registrar nuevo cliente y Guardar deshabilitado. | Cliente requerido en el registro de pedidos |
| 03 `HU012-T03-03-busqueda.png` | Elegir Nombre o razón social, escribir `Norte`, pulsar Buscar. Mostrar Vidrios Norte, TEST — DEMO-003, Activo y Seleccionar. Alternativa: Documento exacto, DEMO-003. | Consulta de clientes integrada con T02 |
| 04 `HU012-T03-04-seleccion.png` | Pulsar Seleccionar Vidrios Norte. Mostrar resumen Cliente seleccionado, nombre/documento/estado y Cambiar cliente. | Confirmación visible del cliente del pedido |
| 05 `HU012-T03-05-alta-contextual.png` | Cambiar cliente → Registrar nuevo cliente. Completar `Vidrios Sur Demo`, `TEST`, `DEMO-T03-001`, teléfono opcional. Capturar antes de Registrar y seleccionar; después pulsarlo y comprobar selección automática. | Alta de cliente sin abandonar el pedido |
| 06 `HU012-T03-06-pedido-listo.png` | Con cliente elegido: Agregar pieza → Material de prueba → 6 mm → Rectángulo → cantidad 2 → ancho 100 → alto 200. Puede agregarse otra pieza de 5.5 mm. Mostrar cliente, piezas y Guardar habilitado. | Pedido multimaterial asociado a un cliente |
| 07 `HU012-T03-07-creacion-exitosa.png` | Guardar pedido. Mostrar mensaje Pedido registrado correctamente y su ID, con formulario reiniciado. Anotar ese ID para la siguiente evidencia. | Registro transaccional completado |
| 08 `HU012-T03-08-api-referencia.png` | DevTools → Network → seleccionar POST `/api/orders` → Response. Mostrar `id_pedido`, `id_cliente`, `estado`; en Payload, `id_cliente` y piezas. Para consulta usar el comando de abajo y mostrar el mismo `id_cliente` en GET. No capturar Authorization ni almacenamiento de sesión. | Referencia de cliente persistida y consultable |
| 09 `HU012-T03-09-validacion.png` | Agregar una pieza válida sin elegir cliente: mostrar aviso Selecciona un cliente y Guardar deshabilitado. Alternativa: usar el comando API de cliente inexistente de abajo y mostrar 422/mensaje controlado. | Validación de cliente en UI y API |

Terminal C para consultar el pedido (sustituir solamente el ID por el observado):

```powershell
$login = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8017/api/auth/login' -ContentType 'application/json' -Body '{"username":"O70000001","password":"Orders-test-2026!"}'
$headers = @{ Authorization = "Bearer $($login.access_token)" }
$orderId = 1 # Reemplazar por el ID mostrado al guardar.
Invoke-RestMethod -Uri "http://127.0.0.1:8017/api/orders/$orderId" -Headers $headers | ConvertTo-Json -Depth 10
```

Prueba controlada de cliente inexistente, solo API local:

```powershell
$payload = '{"id_cliente":2147483647,"piezas":[{"id_tipo_vidrio":7,"espesor_mm":6,"tipo_forma":"RECTANGULO","cantidad":1,"width_mm":100,"height_mm":200}]}'
try {
  Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8017/api/orders' -Headers $headers -ContentType 'application/json' -Body $payload
} catch {
  [int]$_.Exception.Response.StatusCode
  $_.ErrorDetails.Message
}
```

Al acabar la demostración: Ctrl+C en A/B y, desde backend, `python -m tests.e2e_server --stop`.
El helper detiene únicamente el clúster temporal que él creó. No borra datos compartidos.

### Capturas 10–16: validación y entrega

Los logs de `test-results/t03/` corresponden a esta ejecución; para una evidencia nueva ejecutar los comandos.
Todos los comandos backend parten de `backend/` con NEWGLASS_TEST_PG_BIN definido como arriba.
Los comandos frontend parten de `frontend/`. Para E2E liberar antes 5173/8017; Playwright inicia y detiene el entorno.

| Nº / archivo PNG sugerido | Comando/pasos y qué debe verse | Título de diapositiva |
|---|---|---|
| 10 `HU012-T03-10-backend-focalizado.png` | `python -m pytest tests/unit/modules/orders tests/unit/clients tests/api/orders tests/api/clients tests/integration/modules/orders tests/integration/clients -q`. Mostrar comando y resumen sin fallos/errores/skips. | Validación de Orders y Clients en PostgreSQL |
| 11 `HU012-T03-11-frontend.png` | `npm.cmd run test:unit` y `npm.cmd run test:component`. Mostrar los dos resúmenes aprobados y los casos Orders/ClientSelector. | Pruebas de interacción y regresión frontend |
| 12 `HU012-T03-12-e2e.png` | `npm.cmd run test:e2e -- hu012-client-order`. Mostrar las cuatro ejecuciones aprobadas, escritorio/móvil. La suite completa es `npm.cmd run test:e2e`. | Flujo completo: navegador, API y PostgreSQL |
| 13 `HU012-T03-13-backend-completo.png` | `python -m pytest`. Mostrar total final >=1067 y 0 fallos, errores y skips. | Regresión completa del backend |
| 14 `HU012-T03-14-calidad.png` | En frontend: `npm.cmd run lint`, después `npm.cmd run build`. En backend: `python -m compileall -q app tests` y `python -m alembic heads`. Mostrar lint/build exitosos y único head ef6564220e70. | Calidad de código y esquema estable |
| 15 `HU012-T03-15-commits.png` | En raíz: `git log --oneline --decorate 6ae091b..HEAD`. Mostrar commits separados backend, frontend, tests y documentación en la rama T03. | Implementación trazable por commits |
| 16 `HU012-T03-16-rama-sincronizada.png` | En raíz: `git branch --show-current`; `git status --short`; `git rev-list --left-right --count HEAD...origin/feature/HU-012-T03-asociar-cliente-pedido`; `git diff --check`. Mostrar rama correcta, status/diff vacíos y `0 0`. | Rama publicada, limpia y lista para revisión |

## Entrega Git

| Commit | Contenido |
|---|---|
| `3c78dc2` | feat(HU-012): asociar cliente en creacion y consulta de pedidos |
| `94aceab` | feat(HU-012): integrar seleccion de cliente en nuevo pedido |
| `7fd7c08` | test(HU-012): cubrir asociacion cliente pedido |
| Commit que incorpora este documento | docs(HU-012): documentar evidencias T03 |

El hash del propio commit documental se consulta con `git log -1 --format=%h -- docs/evidence/sprint-01/HU-012/t03-asociar-cliente-pedido.md`.
Antes de cada commit: diff --check, status --short y diff --cached --check.
El reporte final de entrega registra el hash documental y el resultado del push, status y sincronización.
Comprobación reproducible tras publicar:

```powershell
git status --short
git rev-list --left-right --count HEAD...origin/feature/HU-012-T03-asociar-cliente-pedido
```

Se espera status vacío y `0 0`. La revisión humana sigue pendiente.
