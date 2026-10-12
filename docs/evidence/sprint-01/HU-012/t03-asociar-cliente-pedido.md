# HU-012 T03 — Asociar cliente al pedido

Estado: implementado e integrado con la línea base actual; revisión visual humana
realizada sin observaciones; listo para revisión de código tras las verificaciones
finales de entrega. **No se declara Verified.**
Fecha: 11/10/2026, contexto del usuario. Rama: `feature/HU-012-T03-asociar-cliente-pedido`.
HEAD inicial: `7fd7c08`. Ancestro común inicial: `6ae091b`.
Integración remota revisada e incorporada: `bf6ca1a`. Merge: `5103734`.

## Objetivo, alcance y contratos

Cada pedido nuevo se asocia a un cliente existente, independiente del usuario que
lo registra. Se permite buscar por nombre parcial o documento exacto, dar de alta
un cliente, seleccionarlo automáticamente o cambiarlo conservando las piezas.

Fuentes: [SPEC-HU-012](../../../specs/SPEC-HU-012-gestion-clientes.md),
[SPEC-HU-013](../../../specs/SPEC-HU-013-gestion-pedidos.md),
[ADR-002](../../../adr/ADR-002-operacion-pre-raster.md),
[evidencia T02](t02-api-clientes.md), implementación vigente y regresiones HU-006/HU-007.

- **Backend:** Orders Application depende del puerto read-only `ClientLookup` de
  Clients. El adaptador verifica existencia usando la sesión compartida; no hace
  commit. Orders conserva la transacción de cabecera y piezas y el rollback.
- **POST `/api/orders`:** `id_cliente` obligatorio, entero estricto positivo hasta
  2147483647. Cliente inexistente: 422 con mensaje controlado. IDs ausentes, null,
  booleanos, strings, decimales, negativos y overflow se rechazan sin escrituras.
  Respuesta 201 incluye `id_pedido`, `id_cliente`, `estado`.
- **GET `/api/orders/{id}`:** devuelve `id_cliente`, usuario y piezas. Los históricos
  con `id_cliente: null` siguen siendo legibles, sin clientes ficticios.
- **PUT `/api/orders/{id}` de HU-013:** mantiene su payload de piezas, sin cliente.
  Se separó `UpdateOrderRequest` del esquema de creación. La edición preserva la
  referencia existente, incluso NULL; intentar reasignarla en PUT devuelve 422
  por campo extra. No se introduce edición de cliente en pedidos existentes.
- **Actividad:** se permiten clientes activos e inactivos. Ninguna regla formal
  revisada los prohíbe; la UI informa el estado y las pruebas cubren ambos.
- **Autorización:** `GESTIONAR_PEDIDOS` permanece. El usuario procede del JWT y la
  validación contra BD. `id_usuario_registro` e `id_cliente` son conceptos separados;
  el request no puede imponer el usuario. Cliente no incorpora credenciales/roles.
- **Frontend:** `clientsApi.js` reutiliza los endpoints de T02, token y `VITE_API_URL`.
  `OrderClientSelector` está en el modo crear de **FormularioPedido**, usado por
  `GestionPedidos` y por el wrapper de compatibilidad `NuevoPedido`.
- **UX:** búsqueda explícita, loading/error/empty, alta contextual, documento/teléfono
  opcionales, selección automática, cambio sin perder piezas, foco tras seleccionar,
  bloqueo sin cliente/doble envío, mensajes seguros y reintento conservando borrador.
  El catálogo permite reintento. Limpiar en modo standalone requiere confirmación.
- **HU-006:** material/espesor por pieza, cantidades y tres formas se conservan.
- **HU-007:** se mantiene el editor real y la validación convexa, su geometría y
  medidas; `rawState` no se envía al backend.

```json
{
  "id_cliente": 41,
  "piezas": [
    {"id_tipo_vidrio": 7, "espesor_mm": 6, "tipo_forma": "RECTANGULO", "cantidad": 2, "width_mm": 100, "height_mm": 200},
    {"id_tipo_vidrio": 7, "espesor_mm": 5.5, "tipo_forma": "POLIGONO_CONVEXO", "cantidad": 1, "vertices_mm": [[0,0],[100,0],[0,100]]}
  ]
}
```

Los IDs del ejemplo solo corresponden al entorno sintético. Clientes inexistentes:
`422 {"detail":"El cliente seleccionado no existe. Busca o registra otro cliente."}`.
401/403 mantienen su significado de sesión/permisos; 404 corresponde a pedido no
hallado; HU-013 conserva 409 para conflicto de estado. No se exponen detalles SQL.

## Cambios recibidos desde integration/sprint-01

El fetch avanzó la referencia de `6ae091b` a `bf6ca1a`: **48 commits, 43 archivos**.
Inventarios completos, con autores/fechas/rutas:
[commits](test-results/t03/post-integration/integration-commits.txt) y
[archivos](test-results/t03/post-integration/integration-files.txt).

| Grupo | Commits representativos / autores | Impacto |
|---|---|---|
| HU-013, PR #36 | `a9c0888`; Luis Anthony Ibañez Herrera | Listado/filtros, PUT/DELETE, transacciones y modal con FormularioPedido. App deja de abrir NuevoPedido directamente. |
| Saneamiento UI, PR #37 | `050286a`, `68922c3`, `48e5d51`, `d255a8b`; Fabricio Dev y Wilder Fabricio | Formulario canónico, estilos compartidos, inventario y regresiones multimaterial/gestión. |
| HU-003 T04/T05, PR #38 | `bf6ca1a`, `5a89b4e`, `122e800`, `8a4557d`, `f9e5e61`, `8790758`; fabrilar1 | Búsqueda/filtros de usuarios, alta/edición bajo acción, SPEC y evidencias. |

| Módulo consultado | Cambio nuevo desde ancestro común |
|---|---|
| Orders backend/frontend | Sí; impacto directo en creación/edición, API y navegación. |
| Clients backend/frontend | No. Las diferencias HEAD..integration aquí eran T03 todavía ausente, no eliminaciones upstream. |
| NuevoPedido/App | Sí; NuevoPedido pasa a wrapper de FormularioPedido y App abre GestionPedidos. |
| Authentication | No; CORS sí cambia en main.py para habilitar PUT/DELETE. |
| Modelos/BD/Alembic | No. |
| Shared UI / Inventory / Users | Sí; estilos, feedback, gestión y sus pruebas. |
| Tests | Sí; API, Application, Infrastructure y componentes. E2E upstream sin cambios. |
| Contratos/API | Sí: GET listado, PUT y DELETE Orders; POST aún no exigía cliente en upstream. |
| package.json/dependencias | No. |
| docs/specs/evidencias | Sí: HU-013, HU-003 T04/T05. docs/database, adr y testing sin cambios. |

## Preservación y resolución del merge

Los tres commits T03 ya existían y no se duplicaron. El WIP era exclusivamente
10 archivos de evidencia en staging, revisados y preservados en `6175c6d` antes
del merge. No se usaron stash, rebase, reset, clean, force push ni checkout destructivo.

Nueve conflictos de contenido, resueltos individualmente:

| Archivo (ruta abreviada) | Resolución |
|---|---|
| Orders application/use_cases.py | Combinar ClientLookup con OrderMutationResult; mantener creación T03 y casos de uso HU-013. |
| Orders presentation/dependencies.py | Conservar inyección de Clients y añadir dependencias list/update/cancel. |
| backend/tests/api/orders/test_orders_api.py | Conservar ambas familias; POST usa cliente, PUT mantiene piezas. Añadir tres casos de preservación/rechazo de reasignación. |
| backend/tests/integration/modules/orders/infrastructure/test_repositories.py | Conservar persistencia T03 y regresiones transaccionales HU-013; fixture de creación con cliente válido. |
| backend/tests/unit/modules/orders/application/test_use_cases.py | Conservar ambos bloques de casos de uso y validaciones. |
| NuevoPedido.jsx | Mantener wrapper upstream; trasladar T03 a FormularioPedido, sin pantalla duplicada. |
| NuevoPedido.css | Mantener estilos compartidos upstream; selector usa esos tokens. |
| NuevoPedido.test.jsx | Mantener suite upstream y preservar suite T03 en NuevoPedidoT03.test.jsx; adaptar selección/DOM real. |
| ordersApi.js | Mantener cliente CRUD upstream y validación de creación comprensible para cliente/piezas. |

Conflictos semánticos adicionales: separación POST/PUT para históricos; feedback de
creación con ID propagado a GestionPedidos al cerrar el modal; E2E entra por Nuevo
pedido desde la gestión y distingue POST del GET que refresca el listado. Se mantiene
la revalidación geométrica T03 y reintento de catálogo. No se borraron ni omitieron
pruebas, ni se usaron xfail/reintentos para pasar.

`git diff --cached --check` durante el merge señaló líneas vacías finales en tres
logs HU-003 recibidos de integración. Se conservaron intactos para no incluir cambios
ajenos. El diff propio contra integration y los checks del working tree quedan limpios.

## Validación posterior a integración

Código funcional probado: árbol incorporado en `5103734` (la focalizada comenzó con
ese contenido backend antes del commit). Los logs antiguos de `test-results/t03/`
son antecedentes; **los resultados de cierre están en `post-integration/`**.

| Ejecución | Resultado real final | Registro |
|---|---|---|
| Backend focalizado ampliado | 395 passed; 0 failed/errors/skipped; 1 warning; 227.82 s | [log](test-results/t03/post-integration/backend-focalizado.txt) |
| Backend completo | 1116 collected/passed; 0 failed/errors/skipped; 1 warning; 332.86 s (5 min 32 s) | [log](test-results/t03/post-integration/backend-completo.txt) |
| Frontend unit | 84 passed; 0 failed/skipped/cancelled; 255.4085 ms | [log](test-results/t03/post-integration/frontend-unit.txt) |
| Frontend component | 148 passed, 17 archivos; 0 failed/skipped; 29.43 s | [log](test-results/t03/post-integration/frontend-components.txt) |
| Lint | Exit 0 | [log](test-results/t03/post-integration/frontend-lint.txt) |
| Build | Exit 0; 1938 módulos; dist generado; 521 ms | [log](test-results/t03/post-integration/frontend-build.txt) |
| E2E T03 | 4 passed, escritorio/móvil; 34.6 s | [log](test-results/t03/post-integration/e2e-t03-attempt1.txt) |
| E2E completo | 28 passed, escritorio/móvil; 38.8 s | [log](test-results/t03/post-integration/e2e-completo.txt) |
| Compileall + Alembic | Exit 0; único head ef6564220e70, cadena consistente | [log](test-results/t03/post-integration/backend-checks.txt) |
| Inspección adicional navegador | POST 201 / GET 200, mismo cliente; foco y sin overflow en 1440×900 y 390×844 | [registro DOM](test-results/t03/post-integration/browser-inspection.json) |
| Revisión visual humana | Usuario confirmó «Revisión realizada sin observaciones» en esta sesión | Apartado siguiente |

Primera pasada de componentes: **5 failed, 143 passed**, conservada en
[frontend-components-attempt1.txt](test-results/t03/post-integration/frontend-components-attempt1.txt).
Diferencias: texto de validación, mayúsculas del botón eliminar y dos literales afectados
por la codificación de PowerShell. Se corrigieron y se ejecutó la suite completa, 148 passed.
Hubo dos invocaciones preliminares desde directorio incorrecto (Alembic en raíz y
redirección frontend); no ejecutaron pruebas ni afectaron BD. Las ejecuciones finales
usan los directorios correctos. No se presenta un intento incompleto como aprobado.

Backend conserva la advertencia Starlette/httpx; Playwright/Node avisa por
NO_COLOR/FORCE_COLOR. No se cambiaron dependencias para ocultar advertencias.
Python 3.14.7, Node 24.21.0, npm 11.19.0; Vite 8.3.1 y Vitest 5.0.3.

### Comandos reproducibles

Desde backend, PostgreSQL **temporal**, nunca Supabase:

```powershell
$env:NEWGLASS_TEST_PG_BIN='C:/Users/Andro/.cache/tooling/hu007-postgres/server/pgsql/bin'
python -m pytest tests/unit/clients tests/unit/modules/orders tests/api tests/integration/clients tests/integration/modules/orders tests/integration/test_clients_migration.py tests/integration/test_orders_multimaterial_migration.py tests/test_permissions.py -q
python -m pytest
python -m compileall -q app tests
python -m alembic heads
python -m alembic history
```

Desde frontend (misma variable NEWGLASS_TEST_PG_BIN para E2E):

```powershell
npm.cmd run test:unit
npm.cmd run test:component -- --reporter=dot
npm.cmd run lint
npm.cmd run build
npm.cmd run test:e2e -- hu012-client-order
npm.cmd run test:e2e
```

Los tests fijan configuración aislada antes de importar la aplicación. Integración,
API Orders/Clients y migraciones utilizan PostgreSQL real temporal. Otras pruebas
heredadas de auth usan SQLite. Playwright administra API 8017 y Vite 5173; no reutiliza
servidores existentes. Screenshots y traces desactivados. Sin migraciones nuevas.

## Evidencia humana y revisión de interfaz

Después de E2E se levantaron `python -m tests.e2e_server` y Vite local con
`VITE_API_URL=http://127.0.0.1:8017`, separados del entorno compartido.
El usuario confirmó **«Revisión realizada sin observaciones»** para login, Nuevo
pedido, buscador, alta, selección, cambio y guardado. No se infiere aprobación del
PR ni estado Verified de esa confirmación.

La inspección automatizada adicional del DOM ejecutó el flujo en ambos viewports:
foco en Cliente seleccionado; sin desbordamiento de documento/selector; botón Cambiar
cliente de 44 px de alto; POST 201 y lectura 200 con la misma referencia y una pieza.
No constituye una revisión visual humana adicional ni certificación WCAG/dispositivo
físico. Se aplicó la skill local impeccable para contexto/revisión acotada; su detector
no produjo hallazgos en los tres archivos inspeccionados (exit 0, registro vacío).
Se conservaron tokens/estilos vigentes. Sin capturas generadas automáticamente.

Para repetir manualmente, iniciar los mismos servidores, abrir http://127.0.0.1:5173
con la cuenta **exclusivamente sintética** `O70000001` / `Orders-test-2026!`, pulsar
Nuevo pedido. Cliente 41: Vidrios Norte / TEST / DEMO-003; cliente 42: inactivo /
TEST / DEMO-004. Registrar, seleccionar, cambiar, agregar rectángulo y/o polígono,
guardar y comprobar el ID. Al acabar: Ctrl+C y `python -m tests.e2e_server --stop`.

Capturas manuales recomendadas (opcionales): bloqueo inicial sin cliente; búsqueda
por nombre/documento; alta y selección; cambio conservando piezas; pedido multimaterial
con editor HU-007; éxito con ID y JSON de consulta sin tokens; resúmenes de pruebas;
Alembic y Git limpio/0 0. Guardar solo si el equipo lo decide en `capturas/`.

## Entrega, riesgos y fuera de alcance

| Commit | Contenido |
|---|---|
| 3c78dc2 | Backend T03: asociación en creación/consulta |
| 94aceab | Selección de cliente frontend |
| 7fd7c08 | Regresiones T03 |
| 6175c6d | Preservar evidencias previas al merge |
| 5103734 | Merge bf6ca1a y adaptación del formulario/contratos/pruebas |
| Commit documental de cierre | Este documento, readiness y resultados finales; consultar git log por ruta |

La comparación triple punto contra `origin/integration/sprint-01` contiene únicamente
T03, su adaptación necesaria al formulario/PUT vigente, pruebas y evidencias. No
reintroduce commits T01/T02 ni cambios de usuarios/inventario. Ver inventario final
junto con el informe de entrega. Push/sincronización se comprueban al publicar:

```powershell
git status --short
git rev-list --left-right --count HEAD...origin/feature/HU-012-T03-asociar-cliente-pedido
git log origin/integration/sprint-01..HEAD --oneline
git diff --stat origin/integration/sprint-01...HEAD
```

`gh` no está disponible; no se instala. Se prepara descripción revisable para crear
el PR manualmente, base `integration/sprint-01`, head de esta feature, título
**HU-012 T03 — Asociar cliente al registro de pedido**. No hacer merge ni desplegar.

Riesgos funcionales: consumidores POST antiguos deben enviar cliente; T02 no pagina
clientes; estado inactivo continúa permitido; cobertura móvil es Chrome emulado.
La suite local no sustituye CI sobre el runtime final. Históricos se conservan sin
backfill. No se añade edición/reasignación de cliente en pedidos existentes, nuevas
migraciones, autenticación de clientes, optimización ni otra HU. HU-013 llegó como
base vigente y solo se adaptó su compatibilidad con T03.

## Readiness de integration/sprint-01 para despliegue

**NO LISTO para despliegue público tal como está configurado.** CORS admite solamente
localhost, `/db-test` expone información de BD sin autenticación y la configuración
final/estado remoto todavía no están validados. T03 debe pasar revisión/merge antes
si se incluye en ese release. No se desplegó ni se tocó Supabase/main/integration.

Hallazgos, variables, comandos, cadena Alembic, alcance de seguridad y acciones
previas: [readiness-integration-sprint-01.md](readiness-integration-sprint-01.md).
