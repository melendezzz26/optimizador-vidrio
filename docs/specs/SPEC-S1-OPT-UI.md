# SPEC-S1-OPT-UI — First Fit visualization

| Campo | Valor |
|---|---|
| Estado SPEC frontend | **APPROVED** |
| Implementación frontend | **COMPLETED WITH FIXTURES** |
| Vista 2D | **IMPLEMENTED** |
| Vista 3D | **IMPLEMENTED** |
| Agrupación visual por material/espesor | **IMPLEMENTED** |
| Preparación raster previa | **IMPLEMENTED** |
| Rotación automática real calculada por motor | **PENDING** |
| Integración First Fit real | **PENDING** |
| Responsable UI y visualización | Andro Q. |
| Aprobación | Confirmada por indicación expresa del equipo comunicada el 2026-10-15; reviewer individual no indicado |
| Responsable motor First Fit real | Fabricio Meléndez — motor **PENDIENTE** |
| Responsable integración backend/frontend | Andro Q. — integración **PENDIENTE** |
| Confirmación/persistencia real | **PENDING** — pendiente del contrato backend |
| Base | ee4e704 |

## Objetivo y alcance

### Refinamiento aprobado: grupos y preparación raster

Agrupar automáticamente la selección por ID de material y espesor numérico, desglosando pedidos que contienen materiales diferentes. Mostrar pedidos/unidades, plancha base de una fuente desacoplada y estado por grupo. No inferir compatibilidad cuando faltan datos. Validar pertenencia pieza/unidad/grupo y material del contenedor en cada colocación. Navegar un grupo y un contenedor a la vez, sin mezclar grupos en 2D/3D/raster.

Preparación raster explícita antes de ejecutar: máscaras recibidas/fixture, tamaño de celda, estado y advertencia de costo computacional. No rasterizar ni optimizar geometría real en frontend. Tras colocaciones válidas habilitar modos 2D/3D/máscara; inspección raster local por pieza claramente diferenciada de una máscara global de plancha, que requiere contrato backend. Zoom acotado, ajuste y celdas visibles; desplazamiento del plano ampliado. Conservar snapshot, live, acciones y eventos públicos (stage_changed opcional).

Criterios CA16–CA19: agrupación automática y aislamiento, raster previo, inspección/zoom en tres modos y conservación de navegación/snapshot. Motor, agrupación final, rotaciones y persistencia reales continúan PENDING a cargo de Fabricio Meléndez; Andro Q. prepara la UI.

Contrato temporal de grupo: id = materialId:espesor numérico, units con pedido/pieza/índice, containers con ID/fuente, dimensiones, geometría, id_tipo_vidrio y espesor_mm. Un contenedor no pertenece a grupos incompatibles. La UI valida estos campos y pertenencia antes de aceptar/dibujar colocaciones; no verifica factibilidad geométrica. `resolveMaterial(id)` es la fuente desacoplada de nombres/stock para la vista previa; la fuente fixture nunca se utiliza para pedidos reales.

Preparación: snapshot.rasters admite clave pedido:pieza (preferida) o id_pieza (compatibilidad actual HU-015). Máscaras recibidas mediante resolution_mm, columns, row_count y spans_by_row; se validan dimensiones, resolución y límites de spans. Faltas/errores mantienen preparación pendiente y deshabilitan ejecución. No se modifica resolución localmente: las máscaras fixture son explícitas a 100 mm/celda, sin rasterizador frontend.

Resultado: una plancha base por grupo fixture (Templado 6 mm #15; Bronce 5.5 mm #16), retazo #8 disponible solo dentro de Bronce, sin colocaciones en esta corrida. El retazo es inventario sintético preexistente, nunca sobrante calculado. Zoom 100–400% en cada modo; 2D/raster usan desplazamiento nativo accesible, 3D amplía la cámara manteniendo yaw limitado. Cambio de modo conserva snapshot, grupo, contenedor y métricas; zoom 2D/raster vuelve a ajuste al desmontar el panel, zoom/yaw 3D se conservan hasta restablecer o nueva corrida.

La UI S1 Optimization está implementada. El fixture First Fit está implementado únicamente para desarrollo y validación visual, permitiendo avanzar en paralelo al motor desarrollado por Fabricio Meléndez. No representa un motor First Fit real terminado ni cálculo automático real de rotaciones terminado. Cuando el motor esté disponible, Andro Q. integrará backend y frontend. La aprobación de esta SPEC no equivale a solución de producción Verified: la integración real y la confirmación/persistencia siguen pendientes.

Seleccionar 1..N pedidos pendientes, preparar grupos compatibles, visualizar progresivamente Primer ajuste con rotación automática recibida, métricas y diálogo de confirmación. Actualizar pendientes automáticamente, congelando cada ejecución. UI española y código nuevo inglés.

Fuera de alcance: Best/Worst Fit, comparación, optimalidad global, descuento frontend, BD, migraciones, persistencia inexistente. El fixture es una simulación explícita, no un motor ni validación geométrica de producción.

## Contratos y reglas

PendingOrdersLiveSource: load, refresh, subscribe(listener), dispose. Publica snapshots completos pendientes o error; preserva selección válida y nunca selecciona nuevos pedidos. Implementaciones: polling GET existente (15 s, sin solapar, abortable) y fixture programable (alta, cambio, eliminación, error, reconexión).

Optimization adapter: prepare(orderIds), createEventSource(prepared), confirm(result). Sin endpoint real, prepare/confirm informan indisponibilidad; nunca llaman start para simular First Fit. Fixture agrupa por tipo/espesor temporalmente. Snapshot profundo de pedidos, geometrías, grupos y contenedores; selección bloqueada durante preparación/corrida, cambios live no alteran snapshot.

Eventos públicos: optimization_started, group_started, piece_started, piece_placed, group_completed, metrics_calculated, optimization_completed, optimization_failed. Todos llevan run_id. piece_placed: id_pedido, id_pieza, unit_index (base cero), x_mm, y_mm, rotation_deg, material_source, material_id, group_id. Identidad de colocación pedido/pieza/unidad, idempotente. Material fuente + ID identifica contenedor; geometría por pedido/pieza desde snapshot. Grupos transportan contenedores con dimensiones y geometría.

`stage_changed` es interno/opcional del fixture/UI, nunca un requisito backend. El backend puede no emitirlo. Sin él, run inicia preparing_orders, group_started activa first_fit, metrics_calculated activa calculating_metrics y optimization_completed completa las etapas visuales. Los hitos intermedios se infieren del avance público; no se afirma telemetría detallada backend. El fixture permite desactivarlo con includeInternalStages=false; pruebas de reducer y componente cubren el flujo completo sin ese evento.

Convención temporal: contenedor origen superior izquierdo, +x derecha, +y abajo; geometría local normalizada a bounding box, giro horario alrededor del origen local normalizado; x/y es ese pivote trasladado, NO esquina de bounding box después de girar. SVG translate(x,y) rotate(angle) translate(-minX,-minY). Backend debe acordar esta convención antes de integración. Escala uniforme min(viewportWidth/materialWidth, viewportHeight/materialHeight), xPx=x_mm*scale, yPx=y_mm*scale. SVG viewBox/preserveAspectRatio expresa la misma transformación sin deformación.

Dimensiones: siempre inventario ancho_mm/alto_mm en adaptador de plancha. Fixture contiene inventario sintético rotulado; no tabla comercial ni fallback. Retazos incluyen geometría real del contenedor. RasterComparison conserva raster HU-015 sin reemplazarlo; la simulación muestra máscaras explícitas cuando disponibles.

Estados: loading_orders, selection_ready, preparing, prepared, running, completed, failed. Timeline: preparing_orders, grouping_materials, rasterizing, sorting_pieces, first_fit, evaluating_rotations, calculating_metrics y completed; fallo explícito aparte. Es simulación/hitos inferidos, no telemetría real de rotaciones. stage_changed sigue opcional. Terminales no aceptan eventos tardíos; nuevo run_id al repetir. Descartar cancela stream y limpia resultado. Confirmar abre ConfirmDialog y comunica que no se guardó si falta endpoint.

## Criterios verificables

### Ampliación aprobada: visualización 3D de resultados

La vista 2D sigue siendo la referencia precisa. Una vez recibida al menos una colocación con contenedor/geometría visualizables, se habilitan «Ver en 2D» y «Ver en 3D»; antes no se muestra selector vacío. Cambiar vista conserva contenedor, snapshot, selección, progreso y métricas. Una nueva corrida vuelve a 2D.

La vista 3D deriva de x_mm/y_mm/rotation_deg y geometrías/dimensiones del mismo snapshot, sin modificar datos ni resolver colocaciones. Representa superficie, cantos, profundidad ilustrativa (no espesor a escala), grilla de referencia y piezas identificadas por pedido/pieza/unidad/color. La superficie descubierta es área libre visual, no geometría calculada de retazos reutilizables. Mantiene acceso al inspector raster HU-015.

Interacción: yaw alrededor del eje Y limitado a [-90°, +90°], inclinación fija, sin órbita libre ni zoom CAD. Arrastre horizontal mouse/touch, flechas izquierda/derecha, control accesible y «Restablecer vista». Sin inercia ni autorrotación; respetar reduced motion. Responsive desktop/mobile.

- CA12: selector ausente sin colocaciones; presente al recibir resultado visualizable; 2D por defecto.
- CA13: 2D↔3D conserva corrida, contenedor, métricas y snapshot; descartar/repetir no conserva una escena anterior.
- CA14: rectángulo/círculo/polígono, pivote/giro recibido, profundidad y leyenda por unidad; datos originales inmutables.
- CA15: yaw limitado para mouse/touch/teclado, reset, foco, reduced motion y ausencia de overflow en móvil.

Motor First Fit real y cálculo automático real de rotaciones: **PENDING**, Fabricio Meléndez. Andro Q. prepara la UI y coordina su conexión a los resultados del motor con Fabricio cuando esté disponible. Confirmación persistente real: **PENDING**. Ninguna capacidad 3D cambia estos estados ni implica Verified de producción.

- CA01: diseño compartido, responsive, teclado, foco, reduced motion; sin refresh manual normal, dropzone, drag & drop ni modo individual/agrupado.
- CA02: pendientes exclusivamente, seleccionar uno/varios/todos/ninguno, contador, cliente y cantidad si existe; loading/empty/error/permiso.
- CA03: altas automáticas no seleccionadas; bajas/cambio de estado depuran selección; error/reconexión; cancelación al desmontar.
- CA04: preparación muestra pedidos, unidades y grupos por material/espesor; no inventa contrato backend.
- CA05: snapshot inmutable durante corrida y aviso de pedidos nuevos para siguiente ejecución.
- CA06: ocho eventos públicos, ocho hitos textuales y fallo explícito, progreso y colocaciones idempotentes; retry sin duplicar ni aceptar eventos antiguos.
- CA07: rectángulo, círculo y polígono convexo; 0/90/30 grados; contenedores navegables, escala uniforme y origen documentado.
- CA08: dimensiones de inventario sin estándares inventados; fuente, material, espesor, pedido/pieza/rotación visibles.
- CA09: métricas solo de eventos: colocadas/total, pedidos, grupos, retazos, planchas, aprovechamiento, merma, tiempo.
- CA10: descartar, repetir y confirmar; modal advierte impacto de inventario, sin persistencia ficticia ni descuento.
- CA11: unit/component y E2E focal fixture Login→Optimización→resultado→modal; live sin botón. Evidencia real con limitaciones.

## Impacto y evidencia

Solo frontend de Optimization, tests/config focal y docs. Backend intacto. E2E usa sesión HTTP simulada, no valida autenticación/backend reales. Evidencia en docs/evidence/sprint-01/S1-OPT-UI. No atribuir aprobación humana ni pruebas no ejecutadas.

## Historial

2026-10-15, ampliación 3D: implementada y validada la representación SVG proyectada del resultado, sin dependencias nuevas. El frontend queda preparado para recibir resultados según el contrato temporal documentado; Fabricio Meléndez desarrollará e integrará posteriormente el motor y las rotaciones automáticas reales, coordinando con Andro Q., responsable de preparar y conectar esta UI. No se declara solución de producción Verified. Evidencia y pruebas actuales: [visualization-3d.md](../evidence/sprint-01/S1-OPT-UI/visualization-3d.md).

2026-10-15: auditoría y planificación previas al código en 665d42a; implementación y validación técnica del alcance fixture completadas. CA01–CA11 contrastados en la evidencia. Integración First Fit real y aprobación humana siguen pendientes, por lo que no se declara Verified de producto backend.

2026-10-15, actualización del equipo: el estado vigente de la SPEC frontend pasa a **APPROVED**. **IMPLEMENTACIÓN FRONTEND = COMPLETED WITH FIXTURES**; **INTEGRACIÓN FIRST FIT REAL = PENDING**. Fabricio Meléndez desarrolla el motor; Andro Q. es responsable de integrarlo con esta UI cuando esté disponible. Se conserva el registro anterior como histórico y no se modifican resultados de pruebas. No se declara Verified de producción ni motor/rotaciones automáticas reales terminados.
