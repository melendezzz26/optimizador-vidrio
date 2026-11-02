# SPEC-SP-004 — Investigación comparativa de heurística M4

## Estado

El hito Pair-Block v1 está registrado, pero su dictamen queda abierto hasta evaluar Pair-Block v2 con la grilla completa de 5 grados y pruning medible. El NO-GO de Filler y DJD se conserva; no se integra ninguna heurística en producción. La auditoría previa a v2 está en [SP-004-pair-block-v2-auditoria.md](../spikes/SP-004-pair-block-v2-auditoria.md).

## Contexto y objetivo

SP-004 estudia una cuarta política M4 para NewGlass. Filler fue descartado porque coincidió prácticamente con FF en TA-027. DJD-1/3 demostró decisiones grupales distintas, pero quedó NO-GO provisional por su costo alto y no mejorar las métricas oficiales. Este hito evaluó Pair-Block y diagnosticó DJD en cuatro instancias nuevas, sin cambiar los fixtures oficiales.

El objetivo es medir si combinar temporalmente dos geometrías complementarias como una sola unidad de packing produce patrones o métricas distintos, manteniendo las piezas originales independientes para inventario, resultado y métricas.

## Alcance experimental

- Módulo nuevo: `experiments/optimization/block_packing/`.
- Unidad de bloque: exactamente dos piezas compatibles por material y espesor.
- Comparación oficial: FF, BF, WF y Pair-Block sobre EXP-SMALL-001, EXP-MEDIUM-001 y EXP-COMPLEX-001, sin cambiar sus JSON.
- Caso Pair-Block no oficial: `BLOCK-DISCRIMINANT-001`, diseñado para evaluar composición y trazabilidad, sin exigir una mejora de métricas.
- Diagnóstico DJD: 3–5 instancias razonadas antes de ejecutar; SMALL/MEDIUM/COMPLEX quedan intactos.
- No se modifican backend productivo, frontend, API, base de datos, FF/BF/WF ni TA-027.

## Método y adaptación

El trabajo publicado de Cai et al. (2023) genera bloques de dos o más piezas para mejorar la utilización local y combina formas complementarias. También incluye espacios residuales con líneas de referencia, reglas de puntuación para asociar piezas/bloques a esos espacios y operadores de mejora/repacking. Pair-Block no pretende reproducir esos componentes completos.

La adaptación forma solo pares. Utiliza orientaciones seleccionadas de las que ya produce NewGlass, separaciones del layout existente y un `RasterMask` compuesto temporal. Ordena los bloques por área total descendente (suma del área de sus dos miembros) junto con piezas sueltas, con desempate estable por identidad. El placement conserva dos `Placement` originales con identidad, orientación y posición propia; el bloque nunca se serializa como una pieza de inventario.

La densidad raster local se calcula como celdas ocupadas por la unión entre el área en celdas de su caja envolvente. Se acepta solo si supera estrictamente la mayor densidad individual de sus dos miembros. Es una medida de adaptación inspirada en el objetivo publicado de mejorar utilización local mediante formas complementarias; no se atribuye esta fórmula a Cai et al. El filtro 4:1 de área de cajas, los ocho anclajes relativos máximos por eje y las orientaciones cardinales permitidas son límites del laboratorio para contener costo, no partes afirmadas del método publicado. La selección de pares es determinista y registra filtros, pruebas geométricas, bloques aceptados y recursos usados.

## Criterios de aceptación

| ID | Criterio |
|---|---|
| CA-01 | La investigación distingue el método publicado de Pair-Block y contrasta fuentes académicas verificables. |
| CA-02 | Los pares se forman solo dentro del mismo material y espesor, con ángulos que pertenecen al conjunto permitido por NewGlass. |
| CA-03 | La formación de un par descarta solapamiento y respeta separación; el compuesto se valida contra el stock usando el layout existente. |
| CA-04 | Los resultados retienen las identidades, áreas, formas, orientaciones y coordenadas de ambas piezas originales. |
| CA-05 | Las piezas sin bloque aceptado o cuyo bloque no cabe continúan como unidades individuales. |
| CA-06 | Se registran métricas oficiales y diagnósticos solicitados de parejas/bloques/tiempos. |
| CA-07 | FF/BF/WF/Pair-Block se comparan en los tres fixtures oficiales inalterados y en un discriminante rotulado no oficial. |
| CA-08 | El diagnóstico DJD contiene entre 3 y 5 instancias externas a TA-027 con intención documentada antes de correr los métodos y clasificación A/B/C/D después. |
| CA-09 | Bloques, placements y métricas funcionales son deterministas en tres ejecuciones por caso; las pruebas cubren geometría, compatibilidad y no mutación. |
| CA-10 | Notebook Colab, evidencia, decisión comparativa y commits locales quedan registrados; la rama se detiene antes de push/PR/merge. |

## Métricas

Se conservan las métricas oficiales de `calculate_metrics`: requested/placed/unplaced, retazos, planchas, aprovechamiento, merma, área recuperable y runtime. Diagnósticos Pair-Block: `candidate_pairs`, `filtered_pairs`, `geometrically_checked_pairs`, `accepted_blocks`, `pieces_in_blocks`, `standalone_pieces`, `block_compaction`, `block_generation_ms` y `packing_ms`. Diagnósticos DJD se mantienen en sus campos existentes.

## Evaluación comparativa y selección de candidato M4

- Pair-Block creó un bloque triangular y produjo un patrón distinto en el discriminante, pero sus métricas empataron con FF/BF/WF. En los tres casos oficiales no colocó ningún bloque. En COMPLEX aceptó una composición geométrica, no cupo, aplicó fallback individual y conservó métricas FF con runtime 17.7 veces mayor.
- Los cuatro diagnósticos DJD se clasificaron A. DJD-1/3 eligió una terna en DJD-DIAGNOSTIC-003, con métricas iguales a los baselines; ningún caso mejoró al mejor baseline.
- El notebook tiene 34 secciones y outputs locales de ejecuciones reales; las firmas Pair-Block se mantuvieron iguales en tres repeticiones por caso.
- La decisión M4 para TA-042 es **NO-GO para Filler y DJD-1/3**; Pair-Block queda **pendiente de dictamen v2**. No hay evidencia suficiente para escoger una heurística productiva; no se modifica motor, API, frontend, BD ni fixtures TA-027.

Una reconsideración futura de Pair-Block debe reducir el costo de generación y obtener bloques colocados con mejoras funcionales repetibles en instancias operativas. La diferencia de patrón en un caso discriminante confirma el mecanismo, no justifica su integración.

Pair-Block v1 fue un ensayo de rotaciones cardinales con una m?trica raster local; sus resultados se conservan como antecedente, no como evaluaci?n final del candidato.

Pair-Block v1 fue un ensayo de rotaciones cardinales con una métrica raster local; sus resultados se conservan como antecedente, no como evaluación final del candidato.

## Fuera de alcance

Integración en TA-042, cambios productivos, alteración de fixtures, publicación de rama, PR, merge y smoke post-merge.
