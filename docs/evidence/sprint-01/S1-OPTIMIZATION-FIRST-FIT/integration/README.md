# Sprint 1 — evidencia de integración real de Optimization

Fecha de los escenarios conservados: **16/10/2026**. Procedencia:
`feature/S1-optimization-ui`, código `c5baa8a`, evidencia publicada en `70a6c36`.
Merge local final con Orders: `ac13d9e`; saneamiento funcional hasta `e1faf3e`.
Revisión humana y PR pendientes. No se cambia el estado de las SPEC.

**Resultados vigentes:** [cierre final y reproducción](final/README.md):
1976 backend completo previo (1 warning), 163 Orders focalizado previo,
379 Optimization focalizado posterior (1 warning), 159 unit, 453 componentes,
86 E2E aprobados sin skips, lint 0 errores/warnings, build OK y única head
`s1opt02b4c6d`. No se reejecutaron pruebas durante la consolidación documental.

La evidencia visual y los payloads de esta carpeta pertenecen a la entrega UI
real anterior. Su baseline fue 446 componentes y 85 E2E + 1 skip. Ese skip de
HU-014 móvil se eliminó al aislar el stock en el cierre funcional posterior,
cuya evidencia tabular está en `final/`. No se presentan imágenes antiguas como
capturas nuevas del flujo final de Orders.

## Procedencia técnica y fuentes

- [Auditoría de ramas, autoría y Alembic](branch-audit.md): mantiene la cronología original.
- [SPEC First Fit](../../../../specs/SPEC-S1-optimization-first-fit.md) y
  [PLAN/CA-01–28](../../../../specs/PLAN-S1-optimization-first-fit.md).
- [SPEC UI/CA01–CA11](../../../../specs/SPEC-S1-OPT-UI.md),
  [HU-015](../../../../specs/SPEC-HU-015-interfaz-rasterizacion.md) e
  [índice de antecedentes UI](../../S1-OPT-UI/README.md).
- [OpenAPI del servidor real](openapi-optimization.json): contrato capturado.
- [Informe final](../../../../reviews/S1-final-integration.md) y
  [manifiesto vigente](../../../../reviews/S1-final-integration-files.txt).

La aplicación usa POST `/api/optimization/runs` con IDs explícitos, NDJSON real
sobre `Response.body`, GET durable y POST de confirmación sin body. Se mantienen
Decimal como texto, índices desde 1, fuente/ID/unidad física de stock, contornos
ya orientados y permisos separados view/execute/confirm. Un 409 no inicia ni
confirma de nuevo automáticamente. T1 no entrega máscaras RLE; HU-015 sigue en
su pestaña con start/rasterize reales. [Resultados y comandos](final/README.md).

## Expedientes: un archivo por criterio distinto

Cada expediente agrupa **ambos viewports**, con sus IDs propios, respuestas GET,
confirmación, stock, pedidos y movimientos cuando corresponden. Los nombres de
artefacto son claves dentro de `viewports.chromium-desktop` o
`viewports.chromium-mobile`. La clave `stream.ndjson` conserva el texto exacto de
la respuesta HTTP original, incluidos orden y saltos de línea. Se compararon los
**194 contenidos** originales después de agruparlos: igualdad completa para
JSON y byte textual idéntico para NDJSON. No se cruzan IDs entre ejecuciones.

| Caso | Criterio demostrado | Expediente |
|---|---|---|
| E2E1 N=1 | Selección, NDJSON, métricas, GET, confirmación; stock 1→0; repetición 409; Orders e Inventory | [Respuestas](scenarios/E2E1.json) |
| E2E2 multipedido | Dos pedidos, una corrida y confirmación de ambos | [Respuestas](scenarios/E2E2.json) |
| E2E3 multimaterial | Dos combinaciones, layouts y métricas separados | [Respuestas](scenarios/E2E3.json) |
| E2E4 unidades físicas | Tres piezas usan dos unidades; stock 4→2; identidad 2D/3D | [Respuestas](scenarios/E2E4.json) |
| E2E5 retazo primero | Dos piezas consumen una sola vez el retazo; plancha sin consumo | [Respuestas](scenarios/E2E5.json) |
| E2E6 SIN_SOLUCION | Diagnóstico, 1/2 piezas, pedidos PENDIENTE y stock intacto; sin confirmar | [Respuestas](scenarios/E2E6.json) |
| E2E7 409 | Cambio real de stock; confirmación rechazada; movimientos vacíos y sin consumo parcial | [Respuestas](scenarios/E2E7.json) |
| E2E8 RBAC | Sin view, view, execute y confirm independientes; 403 reales | [Respuestas](scenarios/E2E8.json) |
| E2E9 orientación | Pieza 70×40 en plancha 40×70, giro 90°; sin segunda rotación 2D/3D | [Respuestas](scenarios/E2E9.json) |
| E2E10 CA-28 | Dos pedidos y materiales; seis piezas sobre tres unidades físicas; confirmación conjunta | [Respuestas](scenarios/E2E10.json) |

No se suman las corridas focalizadas a la suite completa. Los errores de navegador
vacíos y los runtimes repetidos quedan dentro de los expedientes, sin copias
sueltas. En E2E4, unidades de pieza 1/2/3 ocupan unidades de plancha 1/1/2 en
(0,0)/(50,0)/(0,0); el movimiento descuenta 2, no 3 placements. Los payloads
preservan todos los campos para comprobarlo.

## Capturas retenidas: 55, sin alterar imágenes

Se conservan vistas complementarias escritorio/móvil y dashboard por rol:

- [Selección](chromium-desktop/E2E1-selection.png),
  [progreso final](chromium-desktop/E2E1-progress-final.png),
  [2D](chromium-desktop/E2E1-placements.png) y
  [métricas](chromium-desktop/E2E1-metrics.png).
- [3D unidad física 2](chromium-desktop/E2E4-3d-unit2.png),
  [3D móvil](chromium-mobile/E2E4-3d-unit2.png),
  [orientación 90°](chromium-desktop/E2E9-oriented-3d.png).
- [Multipedido](chromium-desktop/E2E2-confirmed.png),
  [material 1](chromium-desktop/E2E3-material-10.png),
  [material 2](chromium-desktop/E2E3-material-11.png),
  [CA-28](chromium-desktop/E2E10-confirmed.png).
- [Confirmación explícita](chromium-desktop/E2E1-confirmation.png),
  [confirmado](chromium-desktop/E2E1-confirmed.png),
  [pedido](chromium-desktop/E2E1-orders-confirmed.png),
  [inventario](chromium-desktop/E2E1-inventory-updated.png) e
  [historial](chromium-desktop/E2E1-inventory-movement.png).
- [SIN_SOLUCION](chromium-desktop/E2E6-sin-solucion.png),
  [409](chromium-desktop/E2E7-409.png),
  [solo view](chromium-desktop/E2E8-view-only.png).
- HU-015 real: [rectángulo](chromium-desktop/HU-015-raster-rectangle.png),
  [círculo](chromium-desktop/HU-015-raster-circle.png),
  [polígono](chromium-desktop/HU-015-raster-polygon.png) y
  [móvil](chromium-mobile/HU-015-raster-rectangle.png).
- Dashboard: [administrador](dashboard/dashboard-administrador.png),
  [operario](dashboard/dashboard-operario.png),
  [almacenero](dashboard/dashboard-almacenero.png),
  [responsive](dashboard/dashboard-mobile-390.png),
  [fallo parcial controlado](dashboard/dashboard-partial-error.png).

La imagen de progreso muestra el estado final; el progreso intermedio se prueba
con el NDJSON capturado y las aserciones, sin fabricar una captura intermedia.
HU-015 conserva tres geometrías, resolución, recuperación y límites. El dashboard
incluye un escenario deliberado de error HTTP parcial; no es un fallo real del
backend. Los escenarios nuevos de Optimization/HU-015 usan HTTP y PostgreSQL
reales, con datos sintéticos y sin mocks productivos.

## Límites y reproducción

La auditoría original observó PostgreSQL 17.11; cada runtime original permanece
en su expediente. El cierre funcional posterior usó el entorno Windows descrito
en [final/README.md](final/README.md), no una nueva ejecución de esos screenshots.
Usar las configuraciones y scripts versionados del frontend; las copias de
runner/config para generar evidencia fueron supersedidas. No se guardan valores
de credenciales en esta carpeta.

CA-01–05, CA-12–17, CA-19–24 y CA-26–28 tienen recorrido integrado. CA-06–11/18
y concurrencia/rollback de CA-20/23/25 conservan sus evidencias backend y el
baseline completo. La reconciliación administrativa y una política residual de
área mínima independiente no se implementaron en este bloque.
