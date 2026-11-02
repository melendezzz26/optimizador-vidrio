# PLAN-SP-004 — Investigación comparativa de heurística M4

## Estado

Filler, DJD-1/3 y Pair-Block v1/v2 están cerrados como NO-GO para TA-042. El candidato actual es el mini-spike local Raster Hole Filling / Pocket Filling. No se hace push, PR ni integración en TA-042.

## Secuencia de trabajo

| Fase | Trabajo | Evidencia | Estado |
|---|---|---|---|
| Auditoría | Revisar geometrías admitidas, rotaciones, máscaras, layouts inmutables, métricas y métodos reales. | Viabilidad sin tocar producción y límites del modelo de geometría. | Completa: Pair-Block se puede colocar con una máscara compuesta temporal y descomponer en dos placements originales. |
| Investigación | Revisar Cai et al. (2023), criterios publicados de bloque, NFP/contacto, BRF y adaptación limitada. | `SP-004-investigacion-m4.md` y fuentes académicas. | Completa; medida raster local identificada como adaptación. |
| SPEC/revisión | Definir CA, reglas, métricas y riesgo de equivalencia. | SPEC y revisión técnica antes de avanzar. | Completa; [revisión M4](../reviews/SP-004-heuristica-m4-review.md). |
| Diagnóstico DJD | Definir 3–5 casos no oficiales y sus intenciones antes de ejecutar FF/BF/WF/DJD. | JSON y manifiesto de intención; matriz A/B/C/D. | Completa; cuatro instancias predeclaradas. |
| Laboratorio Pair-Block | Formar pares compatibles, evaluar compactación y ejecutar layout compuesto aislado. | Código y pruebas sin cambios productivos. | Completa; fallback individual validado. |
| Caso discriminante | Preparar `BLOCK-DISCRIMINANT-001` con formas complementarias. | Patrón y placements verificables, no victoria fabricada. | Completa; bloque colocado y patrón distinto, métricas iguales. |
| Benchmarks | Ejecutar los cuatro métodos en serie para fixtures oficiales y caso discriminante. | CSV/JSON de métricas y diagnósticos. | Completa; [CSV Pair-Block](../evidence/sprint-02/SP-004/benchmark-results/sp004_block_results.csv). |
| Determinismo/regresión | Ejecutar tres veces SMALL/MEDIUM/COMPLEX/discriminante; suite block + DJD + regresiones. | Firmas iguales y pruebas verdes. | Pair-Block PASS ×3 en cuatro casos; suite final: 104 pruebas PASS. |
| Notebook/evidencia | Construir notebook con explicaciones, figuras y outputs locales. | 24+ secciones con outputs; evidencia reproducible. | Completa; 34 secciones y 28 celdas de código ejecutadas. |
| Comparación final | Recomendar GO/NO-GO individual y candidato TA-042. | Documento SP-004 M4 actualizado con resultados. | Completa; NO-GO para integración en TA-042. |
| Git local | Crear commits coherentes y revisar árbol limpio. | Historial local preservado. | Completa; commits locales creados y árbol limpio; no push/PR/merge. |

## Matriz de verificación CA

La tabla se completará con referencia a prueba y archivo de evidencia al cerrar el hito. Ningún criterio se marca PASS a partir del diseño solamente.

| CA | Evidencia esperada | Estado |
|---|---|---|
| CA-01 | Investigación y fuentes verificables | PASS |
| CA-02 | Test de rotaciones solo permitidas y pares compatibles | PASS (11 pruebas de Pair-Block) |
| CA-03 | Tests de separación, no solape y placement en layout | PASS (separación, no solape y layout) |
| CA-04 | Test de descomposición de bloque a placements originales | PASS (identidad y reconstrucción) |
| CA-05 | Test de fallback individual | PASS (fallback individual) |
| CA-06 | CSV/JSON con métricas y contadores | PASS (CSV y trazas JSON) |
| CA-07 | Corridas oficiales y caso Pair-Block | PASS (3 fixtures y discriminante) |
| CA-08 | Matriz DJD con manifiestos previos y categorías A/B/C/D | PASS (4 diagnósticos clasificados A) |
| CA-09 | Repeticiones ×3 y pruebas/regresiones | PASS (3 repeticiones/caso; 104 pruebas) |
| CA-10 | Notebook, decisión, commits y estado limpio local | PASS (5 commits locales; árbol limpio) |


## Reapertura Pair-Block v2

| Fase | Trabajo | Evidencia | Estado |
|---|---|---|---|
| Auditoria rotacional | Explicar la simplificacion v1, el efecto por geometria, las oportunidades omitidas y el alcance de la literatura. | [Auditoria v2](../spikes/SP-004-pair-block-v2-auditoria.md). | Completa antes de tocar codigo; commit `3e46c45`. |
| Criterio de bloque | Retirar el umbral v1 no respaldado y fijar una ganancia local explicita antes de correr. | Formula local y limites de atribucion en auditoria v2. | Definido para implementar. |
| Implementacion/pruning | Usar angulos del motor cada 5 grados, equivalencia raster exacta y cotas seguras. | Nuevos contadores y tests aislados. | Pendiente. |
| Casos predeclarados | Mantener fixtures y discriminante; declarar hasta tres casos razonables antes de benchmarks. | Manifiesto de intencion y JSON congelados. | Pendiente. |
| Benchmark v2 | Comparar FF/BF/WF/Pair-Block en serie; registrar clasificacion A-E, placements y tres tiempos. | CSV/JSON v2. | Pendiente. |
| Notebook/decision | Actualizar celdas, outputs reales y GO/NO-GO TA-042. | Notebook ejecutado y decision final. | Pendiente. |

## Estado vigente — mini-spike Hole Filling

La tabla de Pair-Block v2 anterior es histórica y queda cerrada por la decisión NO-GO documentada en `docs/evidence/sprint-02/SP-004/README.md`. El trabajo vigente se limita al mini-spike HF:

| Fase | Trabajo | Evidencia | Estado |
|---|---|---|---|
| Literatura y auditoría | Contrastar hole filling/IFP publicado con la adaptación raster y documentar el motor actual. | SPEC y `SP-004-investigacion-m4.md`. | Completa antes de implementación. |
| Definición raster | Separar hueco interno físico de pocket candidato por pieza/orientación. | Componentes 4-conexas del espacio físico y de anclajes válidos; definición congelada en SPEC. | Completa antes de implementación. |
| Diagnósticos | Fijar hasta cuatro layouts, dimensiones y geometrías fuera de TA-027. | Manifiesto HF y casos JSON. | Pendiente de commit previo a ejecución. |
| Detector y colocación | Usar máscaras y `SheetLayout.check`; pocket-first y fallback FF, en paquete experimental aislado. | Pruebas, mapas y contadores temporales. | Pendiente. |
| Comparación | Ejecutar FF/BF/WF/HF en los diagnósticos; clasificar A-E y decidir viabilidad. | CSV/JSON y trazas de placement. | Pendiente. |
| Puerta oficial | SMALL/MEDIUM/COMPLEX solo después de superar el mini-spike. | Comparativa oficial solo si es VIABLE. | Condicional; no iniciar todavía. |
| Cierre | Actualizar evidencia y cerrar commits locales con árbol limpio. | SPEC/PLAN/TASKS/SP-004 y commits locales. | Pendiente; sin push/PR/merge. |
