# S1-OPT-UI — Evidencia y entrega

Fecha: 2026-10-15 (America/Bogota). Responsable del frente: Andro Q. Verificación técnica del frontend con fixtures; revisión humana pendiente.

## Base y secuencia

Antes de cualquier cambio: `git status` informó working tree clean; `git branch --show-current` devolvió `feature/S1-optimization-ui`; `git log HEAD..origin/integration/sprint-01 --oneline` quedó vacío; HEAD `ee4e704`. Fetch completado y mismas condiciones confirmadas después. La primera tentativa de fetch encontró protección del sandbox sobre FETCH_HEAD; la ejecución autorizada terminó sin actualizaciones.

Se siguió auditoría → SPEC → PLAN → TASKS → implementación → pruebas → evidencia → commits locales. Documentación previa al código: commit `665d42a`.

- [Auditoría](../../../specs/AUDIT-S1-OPT-UI.md)
- [SPEC y contrato](../../../specs/SPEC-S1-OPT-UI.md)
- [PLAN](../../../specs/PLAN-S1-OPT-UI.md)
- [TASKS T01–T10](../../../specs/TASKS-S1-OPT-UI.md)

## Entrega funcional y arquitectura

1. **Rama:** feature/S1-optimization-ui, directamente desde ee4e704; integration no se modificó.
2. **Documentos:** cuatro archivos enlazados arriba; aceptación CA01–CA11 en la matriz inferior.
3. **Composición:** OptimizationPage usa AppShell, PageCard, PageHeader, ActionBar, LoadingState, EmptyState, FeedbackMessage y ConfirmDialog existentes. App/Sidebar/permisos permanecen intactos.
4. **Archivos de producto:** modificados OptimizationPage.jsx y OptimizationPage.css; creados optimizationModel.js, pendingOrdersSource.js, firstFitFixture.js, useFirstFit.js y PlacementCanvas.jsx, todos en frontend/src/features/optimization.
5. **UI eliminada:** botón Actualizar pedidos, panel grande Pedido seleccionado, selección individual exclusiva y acciones antiguas de inicio/raster en el flujo normal. No había drag & drop implementado; no se introdujo ninguno. El nuevo flujo sirve a 1..N sin modos individual/agrupado.
6. **Selección:** checkboxes nativos, seleccionar todos/ninguno, contador, cliente y unidades cuando existen. Los listados reales no contienen cantidades: no se inventan.
7. **Actualización automática:** PendingOrdersLiveSource load/subscribe/refresh/dispose; GET existente cada 15 s, todas las páginas antes de publicar, sin solapar solicitudes; AbortController, deduplicación y generación para ignorar respuestas antiguas. No es SSE ni snapshot transaccional del servidor.
8. **Pedidos durante corrida:** las altas no se seleccionan; las bajas/cambios de estado depuran la selección futura. El snapshot profundo de la ejecución conserva pedidos, geometrías, grupos y contenedores. Un aviso indica nuevos pedidos para la siguiente ejecución.
9. **Preparación:** adapter prepare(ids), grupos temporales por id_tipo_vidrio/espesor; resumen de pedidos/unidades/grupos. No hay API integrada de grupos: en datos reales se explica la dependencia; no se inventa una respuesta satisfactoria.
10. **Eventos:** optimization_started, group_started, piece_started, piece_placed, group_completed, metrics_calculated, optimization_completed, optimization_failed; stage_changed adicional. run_id separa corridas; pedido/pieza/unit_index evita duplicados. Geometría referenciada desde snapshot, sin duplicarla en eventos.
11. **Estado:** loading_orders, selection_ready, preparing, prepared, running, completed, failed; seis etapas con texto Pendiente/Activo/Completado/Error. Terminales y run_id descartan eventos tardíos. Error del listado es independiente de la corrida.
12. **Fixtures:** pedidos #21/#22, alta automática #24 a los 7 s; fuentes programables para alta, cambio, baja, error y reconexión. Stream cancelable con schedule/cancel y delayMs inyectables. Colocaciones explícitas, no implementación de algoritmo ni cálculo de mejor rotación.
13. **First Fit:** reproducción progresiva de decisiones predefinidas, agrupadas por material; no se promete optimalidad ni se calcula stock. La demostración se abre explícitamente y está rotulada, nunca reemplaza errores de datos reales.
14. **Rotación:** ángulo recibido preservado, fixtures 0°, 90°, 30°; renderer acepta grados finitos generales. Sin controles manuales de rotación.
15. **Rasterización:** HU-015 conserva optimizationApi/useOptimization, GeometryPreview, RasterPreview, RasterComparison, rasterCanvas y visualizationGeometry. RasterComparison se reutiliza en un inspector de la pieza #101 con máscara explícita compatible. No se calcula ni reemplaza el raster backend.
16. **mm→px:** SVG viewBox/preserveAspectRatio aplica scale=min(viewportWidth/materialWidth, viewportHeight/materialHeight). Traslación en unidades físicas y escala uniforme; E2E compara componentes a/d de getScreenCTM. Rectángulos, círculos y polígonos conservan proporción.
17. **Origen temporal:** normalizar geometría a bounding box local; girar horario sobre su origen normalizado y trasladar a x_mm/y_mm, origen contenedor arriba/izquierda. x/y no representa bounding box posrotación. El dominio raster existente usa fila/columna pero no define ese contrato HTTP de giro; debe acordarse antes de conectar backend.
18. **Inventario:** sheetToContainer toma exclusivamente ancho_mm/alto_mm registrados, admite decimales serializados y rechaza dimensiones inválidas. Fixture usa una plancha sintética 3300×2140 y retazo sintético rectangular 1600×1000; no consulta ni modifica stock real. No se agregó tabla comercial ni fallback estándar.
19. **Canvas:** PlacementCanvas es un canvas vectorial SVG, no HTML Canvas; navega contenedores por fuente+ID, representa contenedor y piezas, leyenda por pedido y detalle textual de pieza/unidad/giro. La máscara raster sí usa el Canvas existente de HU-015.
20. **Métricas:** llegan por metrics_calculated: colocadas/total, pedidos, grupos, retazos, planchas, aprovechamiento, merma y tiempo. El fixture calcula áreas sintéticas (12.2% y 87.8% para #21+#22); 842 ms es tiempo sintético del proceso, no duración del playback. UI no inventa métricas.
21. **Acciones:** descartar cancela y limpia; ejecutar nuevamente reutiliza snapshot con run_id nuevo y colocaciones vacías; confirmar abre diálogo compartido con advertencia sobre inventario. El adapter actual rechaza confirmación e informa que no se guardó nada.
22. **Pruebas creadas:** siete unit del reducer; doce component/adapter (selección, live, snapshot, flujo, rotación, error/retry, diálogo, permisos, loading/401, polling/paginación/StrictMode/inventario); dos escenarios Playwright por dos viewports.
23. **Pruebas sustituidas:** OptimizationPage.test.jsx reemplaza expectativas de la UI eliminada; hu015-rasterization.spec.js (255 líneas de flujo individual, POST y BD) fue reemplazado por s1-optimization-ui.spec.js. API/raster/geometría existentes permanecen cubiertos. El total de componentes baja respecto a la base porque se retiraron pruebas del flujo antiguo; no se atribuye conservación de sus interacciones eliminadas.
24. **Pruebas ejecutadas:** tabla y salidas originales abajo, todos con exit 0.
25. **No ejecutado:** E2E general con backend/BD, autenticación real, confirmación persistente, SSE/WebSocket, pruebas backend y migraciones. No son demostrados por estos E2E fixture.
26. **Evidencia:** 14 capturas (7 estados × 2 viewports), cinco logs y este informe; identidades y pedidos son sintéticos.
27. **Commits:** documentación previa `665d42a`, implementación `4e27f33`, pruebas `0268677`; este informe/capturas/logs se entregan en el commit documental siguiente, consultable en `git log ee4e704..HEAD --oneline`. Sin publicación remota.
28. **Estado Git:** verificado después de commits en la entrega final. Diff check y búsqueda de marcadores sin conflictos antes de commit. No archivos backend modificados.
29. **Dependencias:** contrato definitivo de agrupación, stock compatible/unidades de contenedor, origen de rotación, stream/reconexión/reanudación, validación de factibilidad y confirmación transaccional. Los adapters temporales permiten sustituir fuentes sin reescribir la UI.
30. **Restricciones:** NO push, NO PR, NO rebase, NO modificaciones de BD, NO migraciones, NO cambios en integration, NO Best Fit/Worst Fit ni comparación.

## Validación reproducible

Node/npm no estaban instalados en PATH. Se descargó Node portátil oficial en TEMP, sin instalación global; validación final con Node 24.15.0/npm 11.9.0. npm ci usó package-lock existente, sin cambios al manifiesto/lock. El primer runtime 24.14.0 emitió advertencias de engine y se sustituyó por 24.15.0 antes de validar.

Desde frontend, con Node en PATH:

| Comando | Resultado real | Salida |
|---|---|---|
| npm run test:unit | 131/131 PASS; 7 nuevos | [unit.txt](unit.txt) |
| npm run test:component | 344/344 PASS, 31 archivos | [component.txt](component.txt) |
| npm run lint | exit 0, sin errores/advertencias | [lint.txt](lint.txt) |
| npm run build | exit 0, Vite 8.3.1 | [build.txt](build.txt) |
| npx playwright test --config playwright.optimization.config.js | 4/4 PASS, desktop/mobile, 30.1 s | [e2e.txt](e2e.txt) |

Primer pase focal: 44 pruebas Optimization aprobadas; se añadió luego una regresión de reinicio StrictMode, incluida en las 344 finales. Primer pase de lint tenía una advertencia del cleanup del hook, corregida. Primer E2E aprobó cuatro casos pero el sandbox impidió cerrar Vite automáticamente; se cerró exclusivamente su PID y terminó con exit 0. Pase final con permisos de proceso completó limpieza y exit 0 en 30.1 s. Las advertencias NO_COLOR/FORCE_COLOR del log E2E no son fallos; PowerShell las rotula NativeCommandError por proceder de stderr, pero el exit real fue 0.

E2E focal inicia únicamente Vite en puerto 5186. Intercepta todo /api/**, simula sesión y GET y rechaza mutaciones salvo login simulado. No inicia backend ni ejecuta teardown de BD. Login usa componentes reales con HTTP simulado, no credenciales reales. Verifica selección por teclado, progreso antes del resultado, giros 90/30, círculo, escala uniforme, modal/foco, ausencia de overflow horizontal y ausencia de errores JS en flujo principal.

## Matriz de aceptación

| Criterio | Evidencia | Alcance/resultado |
|---|---|---|
| CA01 diseño/accesibilidad | desktop/mobile; teclado, foco, no overflow; CSS reduced motion | PASS frontend; sin auditoría formal WCAG |
| CA02 selección/estados | component single/multiple/all, empty/permission/loading | PASS |
| CA03 live/reconciliación | component live + polling + restart; E2E alta #24 | PASS fixture/polling mock |
| CA04 grupos | component y captura groups | PASS fixture; backend pendiente |
| CA05 snapshot | reducer y component con alta/baja durante run; E2E conserva #21/#22 | PASS |
| CA06 eventos/etapas/retry | siete unit, component progressive/retry/discard | PASS contrato temporal |
| CA07 geometrías/giro/escala | E2E transform 90/30, círculo, getScreenCTM; visualizaciones HU-015 | PASS |
| CA08 dimensiones/material | sheetToContainer 1234×5678, selector de contenedores | PASS adapter; inventario real no conectado a run |
| CA09 métricas | event/reducer/component/E2E result | PASS fixture |
| CA10 acciones/modal | retry/discard; Escape, foco, aviso sin guardado | PASS; persistencia pendiente explícita |
| CA11 tests/evidencia | logs + capturas reproducibles | PASS alcance frontend/fixture |

## Capturas

Estado anterior documentado en auditoría: botón Actualizar pedidos, panel Pedido seleccionado y raster individual; código recuperable en ee4e704. Las siguientes son capturas auténticas de la nueva UI, no del estado anterior:

| Estado | Escritorio 1440 px | Móvil 390 px |
|---|---|---|
| Inicial demo | [initial](desktop-initial.png) | [initial](mobile-initial.png) |
| Selección múltiple/grupos | [groups](desktop-groups.png) | [groups](mobile-groups.png) |
| Colocación progresiva | [progress](desktop-progress.png) | [progress](mobile-progress.png) |
| Resultado/rotaciones/métricas | [result](desktop-result.png) | [result](mobile-result.png) |
| Geometría y máscara HU-015 | [raster](desktop-raster.png) | [raster](mobile-raster.png) |
| Confirmación/inventario | [confirm](desktop-confirm.png) | [confirm](mobile-confirm.png) |
| Alta automática | [live](desktop-live.png) | [live](mobile-live.png) |

Inspección visual realizada sobre desktop-result, mobile-confirm y mobile-raster. No se observó deformación ni desbordamiento horizontal. En capturas fullPage el backdrop fijo del diálogo cubre el viewport visible; no representa un overlay de altura completa del documento.
