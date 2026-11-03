# SPEC TA-042 — Hole Filling M4

**Autor:** Andro Joseph Quispe Cesias. **Revisor académico designado:** Andro Joseph Quispe Cesias; revisión formal pendiente. **Alcance:** T01/T02, motor aislado. **Estado tras auditoría:** REQUIERE AJUSTE antes de PR. SP-004 seleccionó Raster Hole Filling con GO condicionado; su detector exhaustivo no se incorpora.

## Contrato y política

`HoleFillingOptimizer` reutiliza `pack`, su preparación y orden RN-06, `SheetLayout`, orientaciones, inventario inmutable y grupos material/espesor. La entrada se mantiene sin mutar. No registra M4 en coordinadores, API ni interfaz. El paso angular lo proporciona la configuración del motor: la configuración estándar es 5°; también se respetan otras configuraciones admitidas por el contrato existente.

Para la pieza actual, se toma solo el primer candidato factible de FF: el mismo material, fuente y primera orientación válida. Se intenta un anclaje pocket para dicha pieza; no se cambian el orden de piezas, la prioridad retazo → plancha ni el stock escogido por FF. La primera posición interior por fila y columna gana. Si no hay candidato útil se conserva FF exactamente. No hay búsqueda de todas las piezas pendientes ni de todas las orientaciones para detectar pockets; esto limita oportunidades respecto al spike.

Un mapa define anclajes válidos usando el verificador raster oficial. Se identifica la frontera de la región usable con el mismo material y margen, pero sin ocupación; se expande desde ella por anclajes válidos 4-conexos. Los componentes legales que no llegan a esa frontera son pockets para la pieza y orientación, no necesariamente huecos físicos cerrados. Cada placement vuelve a pasar por `SheetLayout.place`.

## Activación y presupuesto

Solo se inspecciona un layout ocupado, con pieza de hasta 64 celdas raster, hasta 16 filas y área de su caja delimitadora no mayor a 1/8 de la caja de la fuente. Son límites técnicos configurables, no reglas comerciales: favorecen insertos pequeños y acotan el trabajo; pueden excluir pockets reales. Por pasada: máximo 8 mapas, 1.024 anclajes por mapa y 8.192 anclajes en total; cada anclaje invoca como máximo dos comprobaciones de placement. Si no cabe el mapa completo en el presupuesto, no se usa un mapa parcial y se aplica FF. El algoritmo de conectividad también está acotado por esos mapas. Se utiliza número de operaciones, no un reloj.

Si se propone al menos un pocket, se ejecuta FF completo como referencia y se conserva M4 solo cuando contiene todas las identidades colocadas por FF. De lo contrario se devuelve FF íntegro. La protección es por identidad, más estricta que comparar solo cantidades; no promete una solución global óptima. Con callbacks se repite la pasada seleccionada para emitir únicamente eventos reales del resultado final: esa repetición añade hasta otra pasada de presupuesto y retrasa los eventos hasta que se decide la cobertura. Las estadísticas corresponden a la pasada exploratoria inicial; no incluyen la reproducción de eventos ni el cálculo FF de cobertura. Se debe usar una instancia por ejecución simultánea.

## Criterios de aceptación

| CA | Resultado | Evidencia |
| --- | --- | --- |
| 01 | PASS: motor aislado sobre raster compartido | `domain/hole_filling.py`; suite HF |
| 02–03 | PASS: rectángulo, círculo, polígono y configuración de 5° | HF-02–07 y regresión geometría/rotación |
| 04 | PASS: margen y separación | HF-08/09 y comprobación de layouts |
| 05–06 | PARCIAL: compatibilidad y prioridad local PASS; la cobertura no impide abrir más planchas que FF | HF-10/12 y contraejemplo de auditoría |
| 07–08 | PASS: fallback determinista y límites por operaciones | HF-01, HF-13/14 |
| 09–10 | PARCIAL: pocket y diferenciación con inserto de 2 × 1 mm; falta capacidad demostrada en dimensiones del caso SP-004 | HF-02/03 y auditoría final |
| 11–13 | PASS: suites HF y regresiones relevantes | evidencia TA-042 |
| 14 | REQUIERE AJUSTE: evidencia disponible, pero la auditoría encontró limitaciones conceptuales | PLAN, TASKS, review y evidencia; revisión académica pendiente |

Fuera de alcance: TA-043, registro de métodos, comparación pública, UI, selección automática, migraciones y cambio de experimentos. Mediciones y limitaciones en `docs/evidence/sprint-02/TA-042/README.md`.

## Hallazgos de auditoría previos al PR

A 1 mm/celda, un rectángulo de 8 × 8 mm tiene 64 celdas; el inserto de 32 × 32 mm de HF-CAPABILITY-001 tiene 1.024 celdas y 32 filas, y queda excluido. Incluso elevando solo ambos límites de pieza, su mapa tiene 60.507 anclajes frente al máximo de 1.024. La misma pieza de 8 × 8 mm sobre fuente de 24 × 24 mm activó el detector a resolución 1 mm y 2 mm, pero no a 0,5 mm. Los límites relativos podrían ser una señal de activación más estable, pero no eliminan por sí mismos el costo del mapa completo; hace falta rediseñar la búsqueda acotada y medirla sin adoptar un porcentaje como regla comercial.

En un caso sintético de 13 piezas con retazo y planchas, HF y FF completan 13/13, pero HF usa una plancha nueva y FF ninguna; la salvaguarda actual compara identidades, no planchas ni merma. Como política a evaluar en el ajuste: preservar las identidades colocadas por FF; si ambos colocan exactamente las mismas piezas, rechazar un resultado HF que use más planchas nuevas; si HF coloca un superconjunto estricto, considerar la cobertura adicional antes de descartar por planchas. No se aplica esa propuesta en el código actual ni se selecciona FF solo por merma.

El primer ángulo FF también limita oportunidades: en un subconjunto validado de HF-DIAGNOSTIC-001, 0° no encuentra pocket y vuelve a FF, mientras la misma pieza tiene pocket legal a 5°. Ver auditoría reproducible en la evidencia. Estas observaciones no modifican los resultados experimentales de SP-004.
