# Revisión técnica TA-052 — M5 Best Residual Fit

**Autor académico de la revisión:** Andro Joseph Quispe Cesias

**Autor de TA-052:** Luis Anthony Ibáñez Herrera

**Estado:** revisión técnica preparada; aprobación formal de GitHub pendiente.

**PR:** #95, `feature/TA-052-implementar-m5` → `integration/sprint-01`.

## Implementación y semántica

`BestResidualFitOptimizer` usa `packing.pack`, `SheetLayout`, preparación, orientaciones, raster y métricas oficiales del backend. Su selector minimiza exactamente `(-área_del_mayor_rectángulo_libre, celdas_libres_fragmentadas, stock_rank, orientation_rank, fila, columna)`, el score validado en SP-005. Best Fit minimiza celdas libres totales; una prueba con fuentes reales muestra BF en la fuente 2 y M5 en la fuente 1. Las pruebas cubren rectángulos, círculos, polígonos convexos, rotación de 5°, margen, separación, compatibilidad de material/espesor, ausencia de solapamiento, prioridad retazo → plancha, desempates, determinismo e inmutabilidad.

La ejecución funcional del motor productivo conserva los resultados registrados en SP-005: MEDIUM M5 9/9, 2 planchas nuevas, merma 281.86 mm² y recuperable 170 mm²; COMPLEX M5 24/24, 4 planchas nuevas, merma 836.72 mm² y recuperable 318 mm². Esto verifica coherencia funcional sin repetir benchmarks de tiempo.

## Pruebas y regresiones

Desde `backend`, `python -m pytest tests/unit/optimization/test_best_residual_fit.py -q -ra` obtuvo **18 passed, 0 failed, 0 skipped**: pruebas directas del motor productivo. La selección conjunta al agregar `tests/unit/optimization/test_sp005_m5.py` obtuvo **29 passed, 0 failed, 0 skipped**. Las 11 pruebas heredadas de SP-005 todavía importan el optimizador experimental; las selecciones se solapan y no se suman.

Sobre el merge de prueba de GitHub con la integración actual pasaron M4 43, auditoría M4 7, FF/BF/WF y prioridad 102, placement/raster 143, geometría/rotación 78, reglas/métricas 36, TA-027 23 y comparación portable 80. Son grupos de regresión distintos; no se presentan como pruebas únicas aditivas.

Una ejecución que incluyó `test_comparison_runner.py` en Windows obtuvo **84 passed, 10 failed**. Los diez fallos proceden del requisito explícito de Linux `procfs` y límites de recursos del runner; no se clasifican como regresión de M5. El CI backend en Linux, frontend y e2e del PR finalizaron en **PASS**. El CI se vuelve a comprobar tras el commit documental.

## Alcance y limitaciones

M5 compara la primera colocación factible de cada fuente física dentro del nivel activo; no explora todas las posiciones. La decisión de SP-005 sigue siendo **GO CONDICIONADO**: en MEDIUM y COMPLEX M5 preserva más área recuperable que WF, pero FF/BF usan menos planchas y generan menos merma. No hay garantía de superioridad general ni selector automático.

`DEFAULT_METHODS` continúa en FF/BF/WF. M5 es ejecutable por su entrada de aplicación y por la lista opcional `EXTENDED_METHODS`; su registro en el coordinador multimétodo y su exposición pública/UI corresponden a TA-043. Este documento no representa una review `APPROVED` en GitHub.
