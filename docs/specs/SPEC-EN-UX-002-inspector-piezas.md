# SPEC-EN-UX-002 — Selección e inspección contextual de piezas 2D/3D

| Campo | Valor |
|---|---|
| Estado | Draft — ejecución y revisión de CI pendiente |
| Responsable | Fabricio Melendez Quezada |
| Dependencia | SPEC-EN-UX-001 (PR documental #118, aún Draft); [Frontend #2](https://github.com/melendezzz26/newglass-frontend/pull/2) aún sin fusionar |
| Implementación | [Frontend PR #3 — apilado sobre EN-UX-001](https://github.com/melendezzz26/newglass-frontend/pull/3) |
| Arquitectura | ADR-001, SPEC-S1-OPT-UI; React/Vite y modelo de presentación; backend sin cambios |
| Auditorías | `Auditoria_NewGlass_2026-11-10.pdf` y `Auditoria_Complementaria_NewGlass_2026-11-10.pdf` aportadas por responsable |
| Trazabilidad | U03, Q04, Q05, Q06, B04, UX08 |

## Objetivo
Que el operario seleccione y consulte **cada unidad colocada concreta** con un único inspector, sin mover el zoom, la cámara o la página y sin volver a imprimir todas las colocaciones ni las etiquetas 3D sobre el patrón. Se mantiene el acceso a los valores técnicos y originales guardados, sin inventar coordenadas o dimensiones y sin alterar heurísticas.

## Diagnóstico técnico de base
- `PlacementCanvas` renderiza 2D como SVG interactuable, resuelve grupo/vidrio, `containerKey` y `placementKey`, cambia 2D/3D/raster y conserva zoom por modo.
- `PlacementScene3D` **no utiliza Three.js ni raycasting**: usa `placementScene.js` con proyección matemática y superficies SVG de geometría extruida. La selección debe enlazarse al `<g>` de la pieza proyectada y no al movimiento general del viewport/cámara.
- `runContract.js` y `optimizationModel.js` ya entregan identidad `pedido:pieza:unit_index` y fuente `material_source:material_id:stock_unit_index`. El campo de comparación/motor lo proporciona `EnginePanel`, no se necesita generar ID persistente adicional.
- `resultSnapshot(result)` contiene la geometría original de las `groups.units`; `result.placements` contiene la geometría ya orientada por el motor. Está prohibido describir la segunda como si fuese la medida original.
- EN-UX-001 eliminó visor anidado, compactó resultados y fuentes. EN-UX-002 **no duplica** ese trabajo.

## Reglas de identidad y selección
1. Clave de selección efímera = tupla JSON `[comparisonId, executionId, material_source, material_id, stock_unit_index, id_pedido, id_pieza, unit_index]`.
2. `PlacementCanvas` es el **único propietario de estado** `selectedKey`. Lo usan 2D, 3D, listado e inspector; ninguno crea una selección paralela.
3. Al pulsar otra pieza, cambia resaltado/ficha sin mover zoom, scroll ni cámara. Las fuentes y geometrías del resultado son inmutables.
4. Al cambiar de plancha, retazo o vidrio, la selección se limpia. Si una pieza sale de un snapshot actualizado, no se presenta seleccionada.
5. Al cambiar de vista 2D↔3D, se conserva la unidad si pertenece a la fuente visible.
6. En cambio de comparación o ejecución, cambia la identidad y el visor se monta con `key` de comparación+ejecución para impedir fuga de estado. La restauración por motor únicamente es válida si sigue montado el mismo resultado y fuente.
7. Abrir histórico usa `result.placements` y `groups.units` persistidos; no depende de una máscara temporal del motor.

## UI de escritorio
- Columna izquierda: patrón y controles existentes, listado de colocaciones único y compacto/filtrable por ID, unidad o pedido.
- Columna derecha: inspector compacto con pedido, pieza, unidad, forma, dimensiones originales, rotación, vidrio, espesor, fuente y unidad física; detalle técnico expandible con coordenadas y área guardada **solo si existen**.
- Estado vacío: «Selecciona una pieza del patrón para consultar sus detalles».
- 3D: por defecto solo etiquetas de pieza seleccionada; un control optativo permite mostrar IDs generales, sin dimensiones masivas. Se conservan cámara/zoom, órbita, pan, vistas superior/perspectiva, centrar, restablecer.
- A11y: botones del listado con `aria-pressed`, nombres por pedido/pieza/unidad, foco visible, inspector anunciado sin desplazar foco.
- No hay segunda biblioteca 3D; se utiliza SVG ya existente.

## Criterios de aceptación
| CA | Validación |
|---|---|
| CA-01 | Unidades repetidas, mismo pedido/pieza y diferentes fuentes o comparación/motor tienen claves distintas. |
| CA-02 | Seleccionar en 2D resalta exactamente una unidad y actualiza la ficha original sin alterar zoom. |
| CA-03 | Seleccionar en 3D resalta exactamente una unidad y actualiza la misma ficha sin alterar yaw, pan, elevación ni zoom. |
| CA-04 | Cambiar 2D↔3D mantiene la selección compatible. |
| CA-05 | Listado compacto seleccionable por teclado con foco, búsqueda y `aria-pressed`, sincronizado al patrón. |
| CA-06 | Cambiar fuente/vidrio limpia pieza incompatible. Cambiar comparación/ejecución evita presentar estados anteriores. |
| CA-07 | Inspector técnico solo muestra campos disponibles; posiciones, área y dimensiones originales se distinguen de geometría orientada. |
| CA-08 | En 3D no se pintan todas las medidas por defecto; etiquetas generales únicamente bajo acción explícita. |
| CA-09 | Unit/component/Playwright, lint y build verdes sin cambios a cálculo, stock, API, migración ni presupuesto. |
| CA-10 | Revisar escritorio 1366×768 y 1920×1080: inspector no tapa patrón y barra contextual mantiene foco visible. |
| CA-11 | Un resultado parcial e histórico conserva selección/diagnóstico sin requerir máscaras temporales; no habilita confirmación inválida. |

## Alcance y límites
No modificar backend, BD, supervisor, geometría de cálculo, heurísticas o criterios de confirmación. El dibujo de círculo en 3D usa teselación de visualización existente, que no sustituye la geometría exacta. El resaltado por SVG no constituye una revalidación de colisiones. La comparación #103 histórica es una referencia de reproducción manual, no se consultará en producción durante tests automatizados.

El PR queda Draft hasta revisar E2E, accesibilidad, viewports y recibir aprobación del equipo; **no fusionar ni desplegar automáticamente**.
