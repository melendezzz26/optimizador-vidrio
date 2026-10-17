# Optimization UI — integración RBAC y contrato T1

> **Registro histórico.** Este documento conserva decisiones, cifras y límites de su entrega original. El estado vigente y los resultados integrados están en el [índice canónico](../README.md). Los logs supersedidos se consolidaron y las capturas enlazadas a integración son equivalentes de cobertura de una corrida posterior, no imágenes de este hito. Los originales se pueden recuperar desde `cbfa6ad` con el índice SHA256 de consolidación.

Fecha: 16/10/2026 (Lima). Rama única de escritura: feature/S1-optimization-ui.
Responsabilidad conservada: interfaz de Quispe. No se implementa backend ni se
integra UI hacia integration. No PR, rebase ni force-push.

## Base, fuentes y resolución

- UI inicial: e42829d8b695d97434542205871703106ca646f9.
- Integration incorporada: c4c5e5cf046a27cc57e9b33a9bd8f8f144b28f8c (PR #50 RBAC).
- Merge local de sincronización: e8d1d149b5c3124e625836f5ab32a544e44c8e80.
- RBAC 4189193 es ancestro de la nueva base; no hubo avances posteriores al merge
  en el precheck. Se incorporan modelos/migración/guards **exactamente desde integration**;
  no hay modificaciones backend propias ni una migración creada por esta tarea.
- Core consultado únicamente en lectura: 3aca3c839ebe7b22a0269826c26d2518157fcb17.
  Fuente: run_schemas.py, run_serialization.py y fixtures/s1_contract_v1.json.
- Orders observada únicamente en lectura: 2a5d835. No integrada ni modificada.

Conflicto único: OptimizationPage.test.jsx. Se preservaron los tests funcionales
Quispe y se integró withPermissions de RBAC; también se adaptó el usuario de
GroupRasterInspection. No se eligió una rama entera como resolución. La cobertura
histórica de la antigua pantalla se recuperó en Hu015Rasterization.test.jsx.
[Detalle y validación del merge](integration.md).

El JSON contractV1Fixture.json es una copia de **datos contractuales**, idéntica
byte por byte al fixture de core; no es implementación backend copiada. SHA256:
`4f90be20f69b3a4b5319783b287ed4ee90a171c45a1bf841cd248f187d6025ed`.
No se hace merge de core y sus clases/schemas no se incorporan a esta rama.

## Contrato y frontera de presentación

- buildRunRequest emite exclusivamente `{order_ids:[...]}`; no geometría/config cliente.
- unit_index 1..cantidad; stock se identifica por fuente+ID+stock_unit_index.
  PLANCHA:5:1 y PLANCHA:5:2 tienen keys, selección y escenas independientes.
- PLANCHA/RETAZO se conservan como transporte; etiquetas humanas solo al presentar.
- Decimal strings se conservan en DTO/modelo/labels. renderNumber convierte solo
  donde la matemática de render lo necesita. Las claves Decimal se normalizan con
  texto sin pasar por Number. No se cambia geometría numérica HU-015.
- Placement usa su geometria ya orientada/local. SVG solo traslada X/Y; 3D usa el
  mismo contorno, sin repetir rotation_deg. El ángulo se conserva como información.
- Envelope v1: schema_version, sequence, event, id_optimizacion, occurred_at, data.
  Se validan correlación/secuencia; gap o transporte incompleto requiere recuperar,
  no fabricar completitud. group_completed tiene contadores de grupo, no globales.
- Progreso real de placed_units/total_units; hitos visuales locales, sin requerir
  stage_changed ni usar eventos de un cálculo anterior después de discard/unmount.
- EN_EJECUCION, COMPLETADA, SIN_SOLUCION y FALLIDA se representan separadamente.
  SIN_SOLUCION conserva diagnóstico y nunca ofrece confirmar. Métricas null son válidas.
- Métricas con nombres T1: aprovechamiento_pct (%), merma_mm2 (mm²), tiempo_computacional_ms
  (ms), planchas nuevas, áreas y retazo recuperable. No se recalculan reglas del motor.
- confirmable/confirmed provienen del resultado canónico. Completar el stream solo
  no habilita confirmar. Adapter.confirm recibe únicamente id_optimizacion; 409 se
  representa como conflicto. La implementación real permanece desconectada.
- readNdjson decodifica UTF-8 incremental, líneas partidas/múltiples, EOF y terminal;
  límite técnico 1MiB de buffer. createRunTransport recibe operaciones inyectadas:
  no contiene fetch ni inventa endpoints. GET/result_url también quedan como interfaz.

La preparación y las máscaras ilustrativas existentes se conservan. Su condición
rasterReady afecta al fixture, no impone un endpoint de preflight nuevo al backend.
La demo temporizada está explícitamente etiquetada como simulación; no es un
transporte real ni prueba del motor FF. Los resultados de ejemplo son predefinidos.

## Vistas, capacidades y fixtures

Se preservan layout/CSS NewGlass, selección y polling, preparación, zoom/scroll,
2D, 3D, yaw por teclado/mouse/touch, grilla y comparación raster. Se inspeccionaron
capturas reales de resultado 2D y escena 3D, sin rediseño global.

Se reutilizan canViewResults/canExecuteOptimization/hasPermission de RBAC real:
view permite acceso/consulta, execute permite inicio y confirm permite botón solo
cuando también confirmable=true y confirmed=false. Sin matriz nueva ni roles
hardcodeados. App/Sidebar cambian su acceso al módulo a view; los tests de navegación
se adaptan a esa separación. Un usuario solo view no consulta Orders automáticamente.

Fixtures T1 incluyen: completo; SIN_SOLUCION; dos pedidos; dos materiales; quantity=3;
dos unidades de plancha 5; retazo 8; placement 90° ya orientado; métricas no disponibles;
confirmable=false; confirmed=true; FALLIDA. Hay además el fixture compartido de core
y la demo visual original de cuatro piezas (incluidos 30°/90°), preservada y adaptada.

## HU-015 preservada

La rama original había eliminado hu015-rasterization.spec.js. Se recupera desde
integration y se adapta únicamente su navegación a la pestaña «Rasterización de
piezas». Se restaura la pantalla técnica con useOptimization y los endpoints reales
/start y /rasterize existentes; no se les añade FF como requisito.

La suite de componentes histórica se conserva en Hu015Rasterization.test.jsx:
inicio, selección, cantidad como atributo de una pieza persistida, recuperación
EN_OPTIMIZACION sin POST nuevo, errores 401/403/409/422, respuestas tardías,
resolución/reintento y geometría/máscara. E2E real cubre escritorio/móvil, cantidad 5,
rectángulo/círculo/polígono con coordenadas negativas, más de 53 columnas, cambio de
resolución, presupuesto raster, recuperación, teclado y responsive.

## Validación final

| Comprobación | Resultado |
|---|---|
| npm run test:unit | 158 passed, 0 failed/skipped |
| npm run test:component | 429 passed, 37 archivos, 0 failed/skipped |
| Optimization focalizada (incluye HU-015) | 108 passed, 0 failed/skipped |
| npm run lint | exit 0 |
| npm run build | exit 0 |
| Playwright Optimization UI | 8 passed, escritorio/móvil, 0 skips |
| Playwright HU-015 real | 6 passed, escritorio/móvil, 0 skips |

Los conteos de esta entrega permanecen arriba y en el índice histórico. Los logs
intermedios y las capturas repetidas se consolidaron en la evidencia real posterior;
el índice SHA256 permite recuperar los originales desde `cbfa6ad`. Los reportes
finales y sus límites están en el [índice canónico](../README.md).
Warnings observados: NO_COLOR/FORCE_COLOR en Playwright; informaciones de rendimiento
jsdom y actualización npm. Ninguno representa un fallo de producto.

Primeros intentos detectaron conflicto todavía sin resolver, mocks antiguos sin
canViewResults, expectativa anterior de navegación por execute y un mock de lectura
consumido al abrir primero la página FF. Se corrigieron fixtures/navegación y se
restauró un modo inicial HU-015 testeable; no se borraron assertions para ocultar
fallos. Los resultados de esa entrega reemplazaron esos intentos; el estado actual se
describe en el cierre integrado enlazado desde el índice canónico.

## Reproducción

Desde frontend, Node 24.19.0/npm 11.9.0 y dependencias del lockfile:

```bash
npm run test:unit
npm run test:component
npm run test:component -- src/features/optimization
npm run lint
npm run build
PLAYWRIGHT_EXECUTABLE_PATH=/usr/bin/chromium npx playwright test --config=playwright.optimization.config.js
```

HU-015: activar primero el Python backend y NEWGLASS_TEST_PG_BIN/LD_LIBRARY_PATH
locales (`source /workspace/.setup/runtime.sh` en este entorno); proporcionar las
variables HU015_E2E_USERNAME/HU015_E2E_PASSWORD **del usuario sintético ya definido
en tests/e2e_server.py**, sin destinos ni credenciales compartidos. Después:

```bash
PLAYWRIGHT_EXECUTABLE_PATH=/usr/bin/chromium npx playwright test --config=playwright.hu015.config.js
```

Playwright HU-015 inicia y detiene su servidor y clúster PostgreSQL temporal. La
config UI usa puerto 5186 y HU-015 5173/8017; outputDir separados. Chromium del
sistema evita descargar otro navegador; Chrome sigue siendo el default existente.

## Dependencias y siguiente integración

Pendientes backend según la numeración solicitada: T7 persistencia/resultado
canónico; T8 NDJSON real; T10 confirmación transaccional. También debe coordinarse
la eventual preparación de selección sin inventar endpoints ni geometrías del cliente.
La rama UI queda preparada para consumir operaciones reales cuando existan; no
se declara esa conexión implementada ni Verified.

Orders c0dbfb9 cambia prioridad del listado; el selector conserva IDs explícitos,
paginación completa y snapshots y no depende de esa prioridad. dd10ec0 envía material/
espesor por pieza; el backend base ya dispone de ese contrato. La feature Orders
no añade API batch. No se integra ni corrige su funcionalidad. El baseline Cloud
anterior 20 E2E passed / 4 failed por Orders/422 sigue siendo histórico: esta tarea
no ejecuta su suite para afirmar resolución ni lo atribuye a Optimization UI.

Para integrar posteriormente: revisar este diff contra integration, mantener los
guards RBAC y la regresión HU-015, volver a verificar la head de integration y
regresiones UI. La integración de endpoints reales requiere pruebas adicionales
con core persistente; la UI/fixture verde no las reemplaza. Integración hacia
integration debe ser una acción posterior autorizada del equipo. SPEC intactas.
