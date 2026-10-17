# Cierre funcional de Sprint 1 — NewGlass

Fecha: 2026-10-16 (America/Lima). Rama: `chore/S1-final-integration`.
Destino previsto para revisión humana: `integration/sprint-01`. Sin push ni PR.

Este informe conserva los resultados del cierre previo al hardening. Los ajustes
posteriores de seed, lenguaje operativo y grupos plegables, junto con su nueva
validación, se registran en el [hardening final](S1-final-hardening.md).

## Integración

- Estado inicial: `e24d39a`, con Orders ya integrado y dos constantes sin uso eliminadas localmente.
- `86ed943` registra esa eliminación pendiente sin alterar el editor.
- `ac13d9e` integra `origin/feature/S1-optimization-ui` mediante merge `--no-ff`, sin conflictos. Padres: `86ed943` y `70a6c36`.
- Se conserva la autoría e historia de UI y Orders. No se realizó rebase, reset ni force push.
- Al terminar la integración funcional se conservaron los 350 archivos de evidencia incorporados por el merge. El saneamiento documental posterior se registra en la [auditoría de consolidación](S1-evidence-consolidation.md), con procedencia por SHA256 y equivalentes vigentes.

## Correcciones funcionales

1. **Editor compartido:** se restaura `onGeometryChange` para publicar geometría válida y retirar el payload anterior al invalidar o reiniciar. Esto repara el registro/edición de retazos, además de Orders. Se mantiene el lienzo único y la selección de vértices del editor integrado.
2. **Accesibilidad:** nombres de lienzo, campos, segmentos y ángulos; selección de vértices mediante teclado; errores asociados a los campos; descripción del resultado geométrico en el botón. Un contorno inválido conserva su diagnóstico específico aunque también falle el cálculo dimensional.
3. **Diálogo de Orders:** Escape, devolución y contención del foco. `Ver figura` permite inspección de un pedido no editable con los controles bloqueados.
4. **Inicialización:** `useEffectEvent` consulta `creating` al completar la carga sin convertir un cambio de presentación en una recarga del catálogo. Se mantiene la cancelación de solicitudes obsoletas y se comprueba que un rerender no borra el borrador ni vuelve a consultar el catálogo.

No se cambió el contrato del payload ni el backend productivo. No se modificó ni eliminó ninguna migración.

## Pruebas adaptadas y regresiones

- Creación: cliente → grupo de vidrio/espesor → pieza inicial. Se comprueba el bloqueo de forma, cantidad y medidas antes de completar el material.
- Piezas diferentes dentro del mismo grupo; segundo grupo; combinación duplicada deshabilitada; liberación de espesor al borrar un grupo; cambio de material que limpia espesor y conserva las medidas.
- Rectángulos, círculos y polígonos; cantidades enteras y medidas positivas; geometría inválida; persistencia POST/PUT y exclusión de `rawState` del payload.
- Cambio de cliente conservando borrador, catálogo fallido/reintento, errores HTTP/red, doble envío y limpieza únicamente tras éxito.
- El editor se prueba como lienzo único: selección de lados y vértices, restricciones angulares, medidas independientes, reinicio e invalidación. No se reinstalaron los dos SVG ni la selección de material por pieza.
- Navegación bajo subpath y retazos usan el editor y el flujo vigentes.
- E2E de pedidos confirmados usa el filtro de estado: la lista prioriza pedidos pendientes y el confirmado puede estar en otra página.
- HU-014 crea stock propio por ejecución. Se elimina el `skip` previo de móvil, conservando todas las comprobaciones de baja e historial.
- La configuración específica de Optimization inicia el backend PostgreSQL temporal real y apunta Vite a su API. Las capturas de Optimization van al directorio de resultados de cada prueba; exportar a evidencia requiere `NEWGLASS_OPTIMIZATION_EVIDENCE_DIR` explícito.

## Verificación

- `npm run test:unit`: **159 passed, 0 failed, 0 skipped**.
- `npm run test:component`: **453 passed, 0 failed, 0 skipped**.
- `npm run lint`: **0 errors, 0 warnings**.
- `npm run build`: **OK**, Vite transformó 1,985 módulos.
- `npm run test:e2e`: **86 passed, 0 failed, 0 skipped** en Chromium de escritorio y móvil. Incluye Orders, inventario, rasterización HU-015, dashboard y los diez escenarios reales de Optimization en ambos viewports.
- Backend focalizado de Optimization: **379 passed, 1 warning** (deprecación Starlette/httpx en `test_confirmation_api.py`).
- Alembic: única head **`s1opt02b4c6d`**. Sin archivos de migración modificados.
- `git diff --check`: OK, sin errores de whitespace.

Las salidas finales se conservan en el [índice de resultados reproducibles](../evidence/sprint-01/S1-OPTIMIZATION-FIRST-FIT/integration/final/README.md). La consolidación documental no repite estas pruebas ni cambia su alcance.

El baseline completo de backend aportado antes de esta sesión es **1976 passed, 1 warning**. No se presenta como una nueva ejecución. Los únicos archivos backend incorporados aquí son utilidades E2E del merge (`tests/e2e_server.py` y `tests/optimization_e2e_data.py`). La nueva verificación focalizada cubre unit/API/integration de Optimization.

Entorno: Windows, Node/npm existentes, Chrome instalado, Python 3.11.9 del `backend/venv`, PostgreSQL temporal propiedad de las pruebas. El launcher Python de Microsoft Store requiere ejecución fuera del sandbox. Se usó `npm.cmd` por la política local de PowerShell, sin cambiar dicha política. No se reutilizaron servicios compartidos ni bases de datos de desarrollo.

Para E2E se ejecuta el script existente `npm run test:e2e` con los dos proyectos de `playwright.config.js`. Se añade `backend/venv/Scripts` al PATH del proceso y se configuran `HU015_E2E_USERNAME/PASSWORD` y `TA_DASHBOARD_E2E_{ADMIN,OPERATOR,WAREHOUSE}_{USERNAME,PASSWORD}` con los usuarios sintéticos definidos en `backend/tests/e2e_server.py`. Los reportes, resultados y capturas de Dashboard se dirigen a `%TEMP%` mediante opciones de Playwright y `NEWGLASS_E2E_EVIDENCE_DIR`.

La aplicación usa `createBackendRunAdapter`, los endpoints reales `/api/optimization/runs`, NDJSON y recuperación de resultados persistidos. Se conservan `optimization.view`, `optimization.execute`, `optimization.confirm`, las vistas 2D/3D/raster, la confirmación explícita y los mensajes diferenciados de conflicto 409. Los fixtures de pruebas incorporados por UI no sustituyen el adaptador productivo.

## Archivos y revisión

El manifiesto `S1-final-integration-files.txt` enumera los archivos existentes del diff final contra `origin/integration/sprint-01` (`fe79530`), incluida la documentación consolidada. El punto de partida funcional de la sesión fue `e24d39a`; las bajas de evidencia se auditan por separado. Los commits de saneamiento están separados por corrección y cobertura. Los artefactos de ejecución no se incluyen en el repositorio.

Archivos saneados después del merge (rutas relativas a la raíz):

- `frontend/playwright.optimization.config.js`
- `frontend/src/features/inventory/__tests__/RegistrarRetazoGeometry.test.jsx`
- `frontend/src/features/orders/CustomPieceEditor.jsx`
- `frontend/src/features/orders/FormularioPedido.jsx`
- `frontend/src/features/orders/__tests__/ConstrainedPieceEditor.test.jsx`
- `frontend/src/features/orders/__tests__/CustomPieceEditor.test.jsx`
- `frontend/src/features/orders/__tests__/FormularioPedido.test.jsx`
- `frontend/src/features/orders/__tests__/MaterialGroups.test.jsx`
- `frontend/src/features/orders/__tests__/NuevoPedido.test.jsx`
- `frontend/src/features/orders/__tests__/NuevoPedidoFeedback.test.jsx`
- `frontend/src/features/orders/__tests__/NuevoPedidoT03.test.jsx`
- `frontend/src/shared/__tests__/stagingNavigation.test.jsx`
- `frontend/tests/e2e/hu007-custom-piece.spec.js`
- `frontend/tests/e2e/hu007-order-integration.spec.js`
- `frontend/tests/e2e/hu012-client-order.spec.js`
- `frontend/tests/e2e/hu014-inventory-writeoff.spec.js`
- `frontend/tests/e2e/optimizationRealSupport.js`
- `frontend/tests/e2e/s1-optimization-ui.spec.js`
- `frontend/tests/e2e/ta036-retazo-personalizado.spec.js`

Documentación de cierre: `docs/reviews/S1-final-integration.md` y `docs/reviews/S1-final-integration-files.txt`.
