# Evidencia TA-050

Autor y revisor académico asignado: Andro Joseph Quispe Cesias. No consta aprobación GitHub.

Base `origin/integration/sprint-01`: `7556a700496673d00fe41b6036d69d91d0939959`. Al crear la rama no había cambios rastreados ni archivos no rastreados visibles; el experimento ajeno ignorado permanece fuera del commit.

## Auditoría

Flujo individual: pedido → claves material/espesor → `AcceptRun` cuenta stock → `InventoryStockAdapter` → repositorio de inventario → DTO → `prepare_persisted_problem` → `CalculateRun`, que consulta el adaptador otra vez → raster y optimizador. Antes, cada lectura llamaba `list_retazos` y `list_planchas` sin filtro y descartaba en Python los incompatibles; tras el cambio, el repositorio aplica los filtros SQL. El contador y el cálculo siguen leyendo por separado para preservar su ciclo de vida y límites; no hay caché global.

Comparación: `AcceptComparison` → `SqlComparisonStock.capture`, que ya filtra en SQL todas las claves mediante `UNION ALL` y captura un snapshot. No se modificó. El repositorio de catálogo público sigue listando activos e inactivos como antes. El mapeo DTO usa columnas de la fila, sin carga de relaciones ni N+1 detectado.

## Pruebas

| Suite | Resultado |
| --- | --- |
| Stock: adaptador y SQL SQLite; integración PostgreSQL | 9 aprobadas, 2 omitidas |
| Stock: integración PostgreSQL 16 aislado en WSL | 2 aprobadas |
| Inventario integración y stock PostgreSQL 16 en WSL | 79 aprobadas |
| Suite unitaria completa de optimización en WSL | 596 aprobadas |
| Suite unitaria completa de optimización en Windows | 586 aprobadas, 10 fallidas |
| Inventario unidad/API/integración | 420 aprobadas, 77 omitidas |
| Pedidos unidad/API | 150 aprobadas, 99 omitidas |
| API pedidos y corrida en WSL/PostgreSQL 16 | 126 aprobadas |
| Preparación, raster, placement, rotación y reglas | 193 aprobadas |
| FF/BF/WF/M4/M5/M6 y TA-027 | 190 aprobadas |
| API de corrida y límites | 47 aprobadas, 27 omitidas |

Las omisiones registradas en Windows requieren PostgreSQL temporal, cuyos binarios no estaban disponibles en ese entorno. Después se ejecutaron las dos pruebas de stock con PostgreSQL 16 aislado en WSL. Las diez fallas de la suite Windows son del runner de comparación, que requiere Linux, procfs y límites de recursos; el mismo conjunto completo pasó en WSL. Las suites de esta tabla se solapan y no deben sumarse como pruebas únicas.

TA-047 no está en la base de integración. Una prueba puntual cargó en memoria su núcleo desde `origin/feature/S2-TA047-preflight-optimizacion` (`a345f332`) y usó el adaptador TA-050 con SQLite: el stock compatible pasó y una consulta vacía produjo `NO_COMPATIBLE_STOCK` para la pieza 1. Esto verifica el contrato entre componentes, no la integración real de ambas ramas ni el flujo comparativo, que sigue pendiente de TA-043.

## Medición descriptiva

Inventario sintético SQLite con seis retazos y seis planchas, mezcla de materiales, espesores y disponibilidad; una ejecución por versión. Antes se materializaron 12 filas y se retuvieron 3 en 6,621 ms; después se materializaron 3 filas en 5,152 ms: reducción de 9 filas, un 75 %. Ambas rutas hicieron dos consultas y produjeron los mismos tres registros compatibles. Son tiempos de un fixture pequeño, no un benchmark PostgreSQL ni evidencia de latencia de producción.

## Índices

Modelo y migración R1 declaran `ix_planchas_stock_compatible` e `ix_retazos_stock_compatible` en `(id_tipo_vidrio, espesor_mm, estado)`. No se inspeccionó una BD desplegada ni un plan de ejecución; no se añadió índice o migración.
