# SPEC-S1-OPT-UI — First Fit visualization

| Campo | Valor |
|---|---|
| Estado | Implemented; verificación técnica frontend/fixture completada, revisión humana pendiente |
| Responsable | Andro Q. |
| Reviewer | Pendiente |
| Base | ee4e704 |

## Objetivo y alcance

Seleccionar 1..N pedidos pendientes, preparar grupos compatibles, visualizar progresivamente Primer ajuste con rotación automática recibida, métricas y diálogo de confirmación. Actualizar pendientes automáticamente, congelando cada ejecución. UI española y código nuevo inglés.

Fuera de alcance: Best/Worst Fit, comparación, optimalidad global, descuento frontend, BD, migraciones, persistencia inexistente. El fixture es una simulación explícita, no un motor ni validación geométrica de producción.

## Contratos y reglas

PendingOrdersLiveSource: load, refresh, subscribe(listener), dispose. Publica snapshots completos pendientes o error; preserva selección válida y nunca selecciona nuevos pedidos. Implementaciones: polling GET existente (15 s, sin solapar, abortable) y fixture programable (alta, cambio, eliminación, error, reconexión).

Optimization adapter: prepare(orderIds), createEventSource(prepared), confirm(result). Sin endpoint real, prepare/confirm informan indisponibilidad; nunca llaman start para simular First Fit. Fixture agrupa por tipo/espesor temporalmente. Snapshot profundo de pedidos, geometrías, grupos y contenedores; selección bloqueada durante preparación/corrida, cambios live no alteran snapshot.

Eventos públicos: optimization_started, group_started, piece_started, piece_placed, group_completed, metrics_calculated, optimization_completed, optimization_failed. Todos llevan run_id. piece_placed: id_pedido, id_pieza, unit_index (base cero), x_mm, y_mm, rotation_deg, material_source, material_id, group_id. Identidad de colocación pedido/pieza/unidad, idempotente. Material fuente + ID identifica contenedor; geometría por pedido/pieza desde snapshot. Grupos transportan contenedores con dimensiones y geometría.

`stage_changed` es interno/opcional del fixture/UI, nunca un requisito backend. El backend puede no emitirlo. Sin él, run inicia preparing_orders, group_started activa first_fit, metrics_calculated activa calculating_metrics y optimization_completed completa las etapas visuales. Los hitos intermedios se infieren del avance público; no se afirma telemetría detallada backend. El fixture permite desactivarlo con includeInternalStages=false; pruebas de reducer y componente cubren el flujo completo sin ese evento.

Convención temporal: contenedor origen superior izquierdo, +x derecha, +y abajo; geometría local normalizada a bounding box, giro horario alrededor del origen local normalizado; x/y es ese pivote trasladado, NO esquina de bounding box después de girar. SVG translate(x,y) rotate(angle) translate(-minX,-minY). Backend debe acordar esta convención antes de integración. Escala uniforme min(viewportWidth/materialWidth, viewportHeight/materialHeight), xPx=x_mm*scale, yPx=y_mm*scale. SVG viewBox/preserveAspectRatio expresa la misma transformación sin deformación.

Dimensiones: siempre inventario ancho_mm/alto_mm en adaptador de plancha. Fixture contiene inventario sintético rotulado; no tabla comercial ni fallback. Retazos incluyen geometría real del contenedor. RasterComparison conserva raster HU-015 sin reemplazarlo; la simulación muestra máscaras explícitas cuando disponibles.

Estados: loading_orders, selection_ready, preparing, prepared, running, completed, failed. Etapas: preparing_orders, grouping_materials, rasterizing, sorting_pieces, first_fit, calculating_metrics. Terminales no aceptan eventos tardíos; nuevo run_id al repetir. Descartar cancela stream y limpia resultado. Confirmar abre ConfirmDialog y comunica que no se guardó si falta endpoint.

## Criterios verificables

- CA01: diseño compartido, responsive, teclado, foco, reduced motion; sin refresh manual normal, dropzone, drag & drop ni modo individual/agrupado.
- CA02: pendientes exclusivamente, seleccionar uno/varios/todos/ninguno, contador, cliente y cantidad si existe; loading/empty/error/permiso.
- CA03: altas automáticas no seleccionadas; bajas/cambio de estado depuran selección; error/reconexión; cancelación al desmontar.
- CA04: preparación muestra pedidos, unidades y grupos por material/espesor; no inventa contrato backend.
- CA05: snapshot inmutable durante corrida y aviso de pedidos nuevos para siguiente ejecución.
- CA06: ocho eventos requeridos, seis etapas textuales, progreso y colocaciones idempotentes; retry sin duplicar ni aceptar eventos antiguos.
- CA07: rectángulo, círculo y polígono convexo; 0/90/30 grados; contenedores navegables, escala uniforme y origen documentado.
- CA08: dimensiones de inventario sin estándares inventados; fuente, material, espesor, pedido/pieza/rotación visibles.
- CA09: métricas solo de eventos: colocadas/total, pedidos, grupos, retazos, planchas, aprovechamiento, merma, tiempo.
- CA10: descartar, repetir y confirmar; modal advierte impacto de inventario, sin persistencia ficticia ni descuento.
- CA11: unit/component y E2E focal fixture Login→Optimización→resultado→modal; live sin botón. Evidencia real con limitaciones.

## Impacto y evidencia

Solo frontend de Optimization, tests/config focal y docs. Backend intacto. E2E usa sesión HTTP simulada, no valida autenticación/backend reales. Evidencia en docs/evidence/sprint-01/S1-OPT-UI. No atribuir aprobación humana ni pruebas no ejecutadas.

## Historial

2026-10-15: auditoría y planificación previas al código en 665d42a; implementación y validación técnica del alcance fixture completadas. CA01–CA11 contrastados en la evidencia. Integración First Fit real y aprobación humana siguen pendientes, por lo que no se declara Verified de producto backend.
