# Compatibilidad de eventos y regresión HU-015

Ajuste posterior al cierre inicial, 2026-10-15, rama feature/S1-optimization-ui. Working tree limpio al iniciar. Sin cambios de backend, BD, migraciones ni contratos HTTP.

## Eventos públicos e internos

El contrato público contiene únicamente optimization_started, group_started, piece_started, piece_placed, group_completed, metrics_calculated, optimization_completed, optimization_failed. `stage_changed` es opcional e interno del fixture/UI. No se exige al backend ni se espera para colocar, calcular métricas, finalizar, fallar o reintentar.

Sin él, run inicia preparing_orders; group_started activa first_fit; metrics_calculated activa calculating_metrics; optimization_completed completa las etapas. Preparación/agrupación/raster/ordenación se muestran como hitos anteriores inferidos, no como mediciones individuales recibidas. No todas las etapas deben mostrarse activas antes de terminar.

El fixture admite includeInternalStages=false. Nueva prueba unitaria recorre eventos públicos hasta completar; nueva prueba de componente verifica colocación intermedia, First Fit activo, seis etapas completadas, métricas y diálogo sin stage_changed. Fallo/reintento ya se probaban con eventos públicos.

## Cobertura HU-015 conservada

Retirar el E2E antiguo **sí retiró cobertura navegador→backend de aquella interacción**. El E2E S1 con HTTP/stream simulados no la reemplaza. No se restaura una prueba incompatible con la UX nueva.

La regresión de integración real de rasterización **no se perdió totalmente**: sigue en la suite API con PostgreSQL real aislado, conforme a la alternativa API/integration solicitada.

| Archivo/caso existente | Cobertura | Límite |
|---|---|---|
| backend/tests/api/optimization/test_optimization_api.py::test_start_then_three_shapes_contract_quantity_and_no_excluded_writes | Login, pedido persistido, POST start, estado, POST rasterize de rectángulo/círculo/polígono, geometría/cantidad/espesor, spans, 120×160 y 19200 celdas, ausencia de escrituras en inventario/resultados | FastAPI TestClient en proceso, PostgreSQL temporal; no navegador/cliente JS. Happy path sin mock del rasterizador |
| Mismo archivo: test_roles_use_current_database_role, test_raster_wrong_state_does_not_transition, test_missing_order_and_piece_and_foreign_piece | Permisos, estados y pertenencia de pieza por endpoints/repositorios reales | Datos sintéticos persistidos |
| Mismo archivo: test_limit_prevents_raster_call_and_leaves_started_state, test_corrupt_geometry_after_start_is_safe_422 | Límites/errores sin transición falsa | Algunos casos negativos usan patch explícito |
| backend/tests/unit/optimization/test_use_cases.py | Orquestación y dominio | Gateway de pedidos fake |
| backend/tests/optimization/test_rasterize_standard.py, test_rasterize_polygon.py | Rasterización geométrica real y resoluciones | Dominio puro, sin API/UI |
| frontend/src/features/optimization/__tests__/optimizationApi.test.jsx | Cliente JS, cuerpo IDs/resolución, validación de respuesta/errores | fetch simulado: NO integración backend |
| frontend/src/features/optimization/__tests__/OptimizationVisualizations.test.jsx | Geometría, raster y escalas | jsdom/Canvas controlado: NO respuesta backend real |

Se auditaron conftest.py de tests/api/optimization y tests, orders_support.py y integration/postgres_support.py. TestClient usa la aplicación real, con conexión de sesión sustituida por BD local exclusiva. orders_database crea BD, aplica Alembic y prepara datos; temporary_postgres usa initdb/pg_ctl en loopback y no toma la conexión remota. No se atribuye ejecución nueva por inspeccionar código.

## Reproducción de la integración real existente

Requiere Python/dependencias backend y PostgreSQL local. Desde backend, en un entorno autorizado para crear/migrar **BD temporales de prueba**:

```powershell
$env:NEWGLASS_TEST_PG_BIN = 'C:\Program Files\PostgreSQL\18\bin'
$env:NEWGLASS_REQUIRE_POSTGRES = '1'
python -m pytest -q tests/api/optimization/test_optimization_api.py
```

NEWGLASS_REQUIRE_POSTGRES=1 evita confundir ausencia de PostgreSQL con PASS por skips. Para el mínimo focal añadir `::test_start_then_three_shapes_contract_quantity_and_no_excluded_writes` a la ruta. Se conserva la suite existente sin duplicarla ni modificar la UX.

**No ejecutada en este ajuste:** esta suite crea BD, aplica migraciones y escribe fixtures; se mantiene la restricción previa «NO modificaciones de BD / NO migraciones». No se ejecutó tampoco el servidor E2E general que realiza esas operaciones. La cobertura existente queda documentada y reproducible, pero no se declara PASS actual de PostgreSQL ni de navegador→backend. Se ejecutan las pruebas frontend afectadas, lint/build y E2E S1 aislado.

## Validación del ajuste

Se registran los resultados nuevos en compatibility-*.txt; los logs del cierre anterior se conservan como antecedentes.

Ejecución nueva con Node 24.15.0/npm 11.9.0 portátil, desde frontend:

| Comando | Resultado | Log |
|---|---|---|
| npm run test:unit | 132 PASS, 0 fallos/skips | [unit](compatibility-unit.txt) |
| npm run test:component -- src/features/optimization | 46 PASS en 3 archivos | [component](compatibility-component.txt) |
| npm run lint | exit 0, sin advertencias | [lint](compatibility-lint.txt) |
| npm run build | exit 0 | [build](compatibility-build.txt) |
| npx playwright test --config playwright.optimization.config.js | 4 PASS, 23.9 s, desktop/mobile | [E2E fixture](compatibility-e2e.txt) |

El log E2E conserva la advertencia NO_COLOR/FORCE_COLOR de Node emitida por stderr; el proceso terminó con exit 0. Las capturas regeneradas sin cambio funcional de UI se descartaron para conservar las del cierre inicial. No se reejecutó la suite completa de componentes ajenos a Optimization ni la suite API/PostgreSQL; no se transfieren los resultados anteriores a esta ejecución. Diff check y búsqueda de marcadores verificados antes del commit local.
