# PLAN-S1-OPT-UI

Derivado de AUDIT y SPEC S1-OPT-UI, 2026-10-15. Autorizado por encargo; revisión humana pendiente.

1. Documentar auditoría, SPEC y tareas antes de código.
2. Implementar modelo/reducer puro y contratos de fuentes inyectables; fixtures autocontenidos con reloj sustituible y cancelación.
3. Implementar pending GET automático y adapter de inventario sin mutaciones; no fingir endpoint First Fit.
4. Componer página con selección, preparación, progreso, visualizador SVG, métricas y ConfirmDialog compartidos. SVG es el canvas vectorial de colocación, Canvas HU-015 conserva máscara raster.
5. Conservar módulos técnicos HU-015; reemplazar pruebas de UI obsoleta por pruebas del flujo solicitado, mantener API/geometría/raster.
6. Ejecutar unit/component/lint/build/E2E focal sin backend ni BD. Capturar pantalla inicial y estados fixture; revisar responsive y consola.
7. Registrar resultados reales, limitaciones, diff check y commits locales por bloques. Sin push ni PR.

Arquitectura: pendingOrdersSource (carga/live), firstFitFixture (escenario/adaptador/stream), optimizationModel (estado), useFirstFit (lifecycle), PlacementCanvas (geometría), OptimizationPage (composición). Contratos públicos permiten sustituir adapters sin reescribir componentes.

Riesgos: falta contrato backend de agrupación, geometría rotada, unidades de inventario, stream/reanudación y confirmación transaccional. Polling no equivale a SSE y lista paginada no es snapshot transaccional. No inferir factibilidad a partir de grupos temporales. La demo solo reproduce colocaciones predefinidas.
