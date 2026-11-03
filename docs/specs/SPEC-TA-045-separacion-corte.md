# SPEC TA-045 — Separación de corte

**Autor:** Andro Joseph Quispe Cesias. **Revisor académico designado:** Andro Joseph Quispe Cesias. No se afirma aprobación de GitHub. **Estado:** T01/T02 implementadas; T03 pendiente por TA-043.

## Contrato observado

`Configuracion.separacion_mm` es `Numeric(8,2)`, no negativa y obligatoria. La configuración vigente procede de BD; el seed **optativo de demostración** usa separación 0 mm, margen 0 mm y resolución 1 mm. No hay valor comercial decidido ni default en `OptimizationConfig`: sus tres distancias son obligatorias.

`RunRequestV1` recibe `order_ids`, no una separación elegida en cada petición. `SqlAlchemyRunUnitOfWork.configuration()` exige una única configuración vigente y construye `OptimizationConfig` con `Decimal`; `ConfigV1` devuelve las distancias en el resultado. El flujo es configuración vigente → snapshot `OptimizationConfig` → `prepare_run_geometry` y `RasterCache` → `_empty_layout`/`SheetLayout` → placements y configuración serializados. La publicación actual de configuración angular conserva separación y margen anteriores.

## Semántica raster y límites

Para resolución `r` y separación `X`, el motor calcula exactamente `n = ceil(X/r)` con cocientes enteros; `X=0` produce `n=0`. Cada pieza se rasteriza conservadoramente a su orientación real. Después de colocarla, se dilata la unión ocupada en una vecindad **cuadrada** de radio `n` celdas (distancia de Chebyshev); la siguiente máscara no puede intersectarla. No se añade `n` dos veces: para dos rectángulos alineados hay al menos `n` celdas libres entre máscaras. En diagonal se aplica la misma vecindad cuadrada, una reserva conservadora, no una simulación euclidiana precisa del disco de corte. La cuantización y la rasterización conservadora pueden reservar más espacio físico que X.

El margen es independiente: erosiona la máscara interior de la fuente `ceil(margen/r)` celdas; protege pieza ↔ borde. La separación protege pieza ↔ pieza y no se aplica por sí sola al borde. Un límite de dilatación en el motor trunca `n` al máximo de filas/columnas: a partir de allí ninguna segunda celda puede ser válida. Retazos y planchas usan la misma construcción y comprobación de layout; las formas usan sus máscaras oficiales y las rotaciones discretas usan la máscara orientada, no la caja como criterio de aceptación.

Se corrigió un bug de la API directa `distance_in_cells`: restar una tolerancia de `1e-9` podía convertir una distancia positiva pequeña en cero o subestimar valores apenas superiores a un múltiplo. Ahora el techo se calcula exactamente sobre las representaciones decimales de las entradas; el motor pasa conteos enteros al layout sin multiplicar y dividir floats. Las pruebas cubren `1e-12`, `1.0000000001`, `0.07/0.01` y la resolución `0.1`. No se cambia la regla de separación comercial ni la métrica cuadrada.

## Métodos y alcance

FF, BF y WF usan `pack` y los candidatos de `SheetLayout`. M4/Hole Filling también usa `pack` y valida candidatos de bolsillo con `check`/`place`. M5 usa `pack` y puntúa layouts válidos. M6 crea layouts con `_empty_layout` y usa `first_position`, `check` y `place`. Las seis implementaciones de dominio pasan los casos transversales; ello no afirma que las seis estén disponibles en la API o la interfaz final. El comparador existente registra FF/BF/WF y M5; M4 y M6 mantienen sus puntos de entrada propios.

T03 no se implementa: no hay evidencia de TA-043 mergeada en la base auditada. Al integrarse, deberá visualizar la configuración real y preservar la geometría original sin representar la reserva como vidrio.

La separación es un parámetro configurable expresado en mm, interpretado uniformemente por el motor raster compartido dentro de los límites y la cuantización descritos.
