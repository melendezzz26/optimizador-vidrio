# Auditoría S1 Optimization UI

## Revisión de grupos/raster sobre f538eeb

2026-10-15: rama feature/S1-optimization-ui y árbol limpio confirmados antes de cambios; fetch origin --prune sin commits nuevos de integration. Se revisaron OptimizationPage, firstFitFixture, reducer, PlacementCanvas, escena 3D, HU-015 y sus pruebas. Hallazgos: agrupación solo tras preparar, selector global de contenedores, pertenencia de pieza a grupo no validada, un único raster accesible después de iniciar y ausencia de zoom. Refinamiento aprobado en SPEC/PLAN/TASKS: separar vista previa, preparación raster y resultados por grupo; conservar adapters y compatibilidad pública. No backend/BD.

Fecha: 2026-10-15. Rama `feature/S1-optimization-ui`, HEAD/base remota `ee4e704`.
Antes de cambios: git status limpio, rama correcta, rango HEAD..origin/integration/sprint-01 vacío. Fetch realizado; mismas condiciones después. No se cambió integration.

## Hallazgos

- OptimizationPage/useOptimization: selección individual, refresh manual, inicio POST y recuperación EN_OPTIMIZACION; no colocación First Fit. El panel Pedido seleccionado domina la pantalla.
- optimizationApi: solo POST start y rasterize. No API de grupos, stream, métricas ni confirmación. No integrar ramas paralelas HU-008.
- HU-015: GeometryPreview, RasterPreview, RasterComparison, rasterCanvas y visualizationGeometry reutilizables. Conservar clientes, hook y pruebas técnicas; sustituir pruebas de la experiencia que se elimina.
- Dominio placement.py valida máscaras con esquina superior izquierda en fila/columna, pero no publica contrato HTTP de x_mm/y_mm/rotation_deg. La convención de giro de esta UI será explícitamente temporal.
- Orders: GET paginado con estado PENDIENTE; listado no incluye cantidades, detalle sí incluye piezas/geometría/cantidad. Consulta automática puede reutilizar GET sin inventar SSE.
- Inventory: planchas tienen ancho_mm/alto_mm, tipo, espesor, cantidad y estado; retazos tienen geometría. No existe selección compatible integrada. No usar medidas comerciales para reemplazar inventario.
- App/Sidebar: navegación interna y permisos Administrador/Operario ya correctos; no necesitan cambios. Almacenero no puede ejecutar.
- Pedidos, InventoryPage, UsersPage, Dashboard: AppShell, PageCard, PageHeader, ActionBar, feedback, ConfirmDialog y tokens compartidos. Reutilizar tipografía, azul, bordes y controles.
- Tests: node:test, Vitest/RTL, Playwright. Config E2E general inicia backend y teardown: crear configuración focal aislada sin BD, con HTTP de sesión simulado y fixture explícito.

## Decisiones

Nuevo flujo único 1..N. Datos reales por defecto, consulta periódica GET cancelable; demostración explícita con fixtures independientes, nunca fallback silencioso de errores. Preparación/ejecución reales bloqueadas honestamente hasta contrato backend; demo cubre flujo completo sin mutaciones.
Preservar rasterización técnica existente; reutilizar RasterComparison para inspeccionar geometría/máscara de fixture. No implementar heurística ni rotación en cliente: reproducir decisiones de eventos.
La instrucción actual autoriza visualización First Fit en Sprint 1 y prevalece sobre el alcance histórico de CONTRIBUTING/ADR. Sin push/PR/BD/migraciones/rebase.
