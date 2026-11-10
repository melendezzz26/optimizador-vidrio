# PLAN-EN-UX-002 — Selección 2D/3D e inspector de unidades

**Estado:** Draft. **Responsable:** Fabricio Melendez Quezada. **Base:** EN-UX-001, PR #2 `feature/EN-UX-001-resultados-operativos`, pendiente de merge. **Implementación:** [PR frontend #3](https://github.com/melendezzz26/newglass-frontend/pull/3), apilado, sin cambios de `main`.

## Plan de tareas
1. **T01 Inspección y contrato**: localizar `PlacementCanvas`, `PlacementScene3D`, `placementScene`, `InspectionViewport`, `resultSnapshot` y `runContract`; verificar unidad, fuente y dimensión original. No inventar IDs.
2. **T02 Modelo**: `pieceInspectionModel.js`: clave de identidad con comparación+ejecución+pedido+pieza+unidad+fuente; resolución original desde snapshot y fallback explícito sin valores fabricados.
3. **T03 Inspector**: `PieceInspector.jsx`, `PieceInspectorTechnical.jsx`, CSS reutilizando paleta; una sola ficha compacta y detalle mm²/mm opcional.
4. **T04 2D/listado**: `PlacementCanvas.jsx` comparte `selectedKey` con SVG y `PiecePlacementList.jsx`, filtro y teclado; eliminar listados extensos duplicados y no intervenir zoom.
5. **T05 3D**: `PlacementScene3D.jsx` maneja clic sobre superficie SVG proyectada y evita secuestrar drag de cámara; etiquetas ocultas salvo pieza seleccionada o petición explícita. Sin paquete 3D adicional.
6. **T06 Contexto**: `ComparisonWorkspace.jsx` provee `runId`, `executionId` y clave de render por comparación/ejecución; otras ejecuciones permanecen aisladas.
7. **T07 Regresión**: Vitest modelos/componentes y tests previos actualizados; Playwright con backend efímero y resultados reales generados solo en la infraestructura aislada de CI, sin producción ni inventario real. Verificar completos, parciales e históricos.
8. **T08 Evidencia visual y accesibilidad**: comprobar viewport exacto de 1366×768 y 1920×1080, clicks y teclado, zoom/cámara y capturas mínimas del inspector. Gate sin fallas antes de review.

## Riesgos y contramedidas
- **Duplicados**: `id_pieza` no es único por colocación. Testear pedidos, unidades, fuente física y ejecución.
- **3D**: el viewport existente captura eventos para órbita; el clic sobre una superficie debe detener captura sin afectar arrastre sobre fondo. Probar cámara antes/después.
- **Dimensiones**: las piezas del motor están orientadas; el inspector lee `groups.units` para medidas originales. Si faltan, mostrar «No disponible», no adivinar.
- **Tamaño**: una lista de cientos de colocaciones no debe crecer toda la pantalla; scroll interno y búsqueda, sin renderizar otra geometría.
- **Compatibilidad**: selección nunca cambia contratos, selección de motores o cantidades de material ni consume stock.
- **Stacked PR**: PR #3 debe apuntar a rama EN-UX-001 mientras PR #2 permanezca abierto; posteriormente actualizar su base a `main` solo tras merge oficial del PR #2 (acción revisable, no merge implícito).

## Evidencia exigida por cierre
- Diff de componentes y modelos nuevos; pruebas del modelo de identidad y selección 2D/3D/listado/teclado/fuente/cámara/histórico.
- CI `frontend` + `e2e` verdes para el SHA final; no confundir checks de EN-UX-001 con EN-UX-002.
- Capturas mínimas 2D con ficha, 3D con ficha y fuente cambiada (sin selección), con viewports exactos si entorno permite.
- Review externo antes de integrar; si cualquier gate falla, permanecer Draft.
