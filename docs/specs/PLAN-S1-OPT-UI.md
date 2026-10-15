# PLAN-S1-OPT-UI

Derivado de AUDIT y SPEC S1-OPT-UI, 2026-10-15. SPEC frontend **APPROVED** por indicación expresa del equipo. Implementación frontend **COMPLETED WITH FIXTURES**; integración First Fit real **PENDING**. No se atribuye un reviewer individual ni una aprobación adicional distinta de la comunicada.

1. Documentar auditoría, SPEC y tareas antes de código.
2. Implementar modelo/reducer puro y contratos de fuentes inyectables; fixtures autocontenidos con reloj sustituible y cancelación.
3. Implementar pending GET automático y adapter de inventario sin mutaciones; no fingir endpoint First Fit.
4. Componer página con selección, preparación, progreso, visualizador SVG, métricas y ConfirmDialog compartidos. SVG es el canvas vectorial de colocación, Canvas HU-015 conserva máscara raster.
5. Conservar módulos técnicos HU-015; reemplazar pruebas de UI obsoleta por pruebas del flujo solicitado, mantener API/geometría/raster.
6. Ejecutar unit/component/lint/build/E2E focal sin backend ni BD. Capturar pantalla inicial y estados fixture; revisar responsive y consola.
7. Registrar resultados reales, limitaciones, diff check y commits por bloques. Nueva política del equipo: mantener publicada la feature y sincronizarla periódicamente mediante merge normal desde origin/integration/sprint-01; detenerse ante conflictos para análisis previo a resolver. Push de feature autorizado; sin PR, rebase ni merge hacia integration.

Arquitectura: pendingOrdersSource (carga/live), firstFitFixture (escenario/adaptador/stream), optimizationModel (estado), useFirstFit (lifecycle), PlacementCanvas (geometría), OptimizationPage (composición). Contratos públicos permiten sustituir adapters sin reescribir componentes.

Riesgos: falta contrato backend de agrupación, geometría rotada, unidades de inventario, stream/reanudación y confirmación transaccional. Polling no equivale a SSE y lista paginada no es snapshot transaccional. No inferir factibilidad a partir de grupos temporales. La demo solo reproduce colocaciones predefinidas.

## Dependencia y siguiente fase

- UI y visualización S1: implementadas por Andro Q., con fixture solo para desarrollo/validación visual.
- Motor First Fit real: **PENDIENTE**, responsable Fabricio Meléndez. No se declara terminado el cálculo automático real de rotaciones.
- Integración backend/frontend: **PENDIENTE**, responsable Andro Q. cuando el motor esté disponible. Acordar contratos de grupos, eventos públicos, origen/giro, dimensiones y métricas antes de sustituir adapters. stage_changed permanece opcional/interno.
- Confirmación/persistencia real: pendiente del contrato backend; no fingir guardado ni descontar stock en frontend.
- Validar la integración real cuando exista; no declarar la solución de producción Verified mientras esté pendiente. Los resultados frontend/fixture ya ejecutados conservan su estado y alcance.
- Sincronización actual: cf84d73 cambia solo docs/specs/SPEC-HU-015-interfaz-rasterizacion.md. Inspección del diff, git diff --check y git status; no se repiten suites por un merge y ajuste exclusivamente documentales.
