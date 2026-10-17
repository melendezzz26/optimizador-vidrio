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

Refinamiento grupos/raster: auditar pertenencia de colocaciones → modelo puro de agrupación y fuente de planchas fixture → tarjetas automáticas → preparación raster previa reutilizando contrato spans_by_row HU-015 → resultado filtrado por grupo y modos 2D/3D/raster con zoom → regresiones de incompatibilidad, snapshot e interacción → suites frontend y evidencia. Base f538eeb limpia; fetch sin avances de integration. No tocar backend/BD ni convertir raster fixture en algoritmo real.

Refinamiento implementado: agrupación visual y preparación raster previa **IMPLEMENTED**; 2D/3D **IMPLEMENTED**, SPEC **APPROVED**, frontend **COMPLETED WITH FIXTURES**. Integración, agrupación final del motor, rotaciones reales y persistencia **PENDING**. Se mantienen fuente de material configurable, prepare/eventSource/confirm y máscaras HU-015 para integración futura de Fabricio con la UI preparada por Andro. Evidencia actual: [grupos/raster](../evidence/sprint-01/S1-OPT-UI/groups-raster.md).

Estado tras la ampliación: SPEC **APPROVED**, frontend **COMPLETED WITH FIXTURES**, vistas 2D y 3D **IMPLEMENTED**. Integración First Fit, rotación automática real y confirmación persistente **PENDING**. Fabricio Meléndez desarrollará e integrará el motor/rotaciones; Andro Q. prepara y conecta la UI coordinando el contrato. Validación actual: 141 unit, 351 component, 6 E2E, lint/build exit 0; [evidencia](../evidence/sprint-01/S1-OPT-UI/visualization-3d.md).

Ampliación 3D autorizada: implementar proyección matemática SVG de geometría extruida (superficie/cantos), cámara con inclinación fija y yaw acotado. Sin dependencias adicionales: el alcance es inspección de resultados planos convexos, sin escena CAD, iluminación física ni operaciones sobre geometría. Separar modelo puro de contornos/proyección, visor interactivo y selección común de contenedor/vista. Mantener el SVG 2D actual y el raster HU-015.

Secuencia: modelo puro + pruebas de transformaciones/inmutabilidad → visor/profundidad/grilla/leyenda → selector condicional y estado común → componentes y E2E mouse/touch/teclado/mobile → revisión de capturas → evidencia, commit y publicación de feature. No tocar backend/BD ni cerrar dependencias del motor. Mantener activo el entorno de revisión manual previo; ejecutar E2E en un puerto separado si está ocupado.

- UI y visualización S1: implementadas por Andro Q., con fixture solo para desarrollo/validación visual.
- Motor First Fit real: **PENDIENTE**, responsable Fabricio Meléndez. No se declara terminado el cálculo automático real de rotaciones.
- Integración backend/frontend: **PENDIENTE**, responsable Andro Q. cuando el motor esté disponible. Acordar contratos de grupos, eventos públicos, origen/giro, dimensiones y métricas antes de sustituir adapters. stage_changed permanece opcional/interno.
- Confirmación/persistencia real: pendiente del contrato backend; no fingir guardado ni descontar stock en frontend.
- Validar la integración real cuando exista; no declarar la solución de producción Verified mientras esté pendiente. Los resultados frontend/fixture ya ejecutados conservan su estado y alcance.
- Sincronización previa: cf84d73 cambió solo docs/specs/SPEC-HU-015-interfaz-rasterizacion.md. En aquella entrega no se repitieron suites por el merge documental. Al iniciar la ampliación 3D desde 2d444c0, fetch no encontró commits nuevos de integration; no fue necesario otro merge. Esta ampliación sí ejecuta las suites frontend indicadas.
