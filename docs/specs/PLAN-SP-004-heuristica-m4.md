# PLAN-SP-004 — Investigación comparativa de heurística M4

## Estado

SP-004 selecciona Raster Hole Filling / Pocket Filling como M4 con **GO condicionado para estudiar una versión optimizada en TA-042**. Su búsqueda experimental fue demasiado costosa y conserva el NO-GO para integración directa. Filler, DJD y Pair-Block quedan como antecedentes descartados. Este plan conserva las fases y resultados originales; el cierre documental y la publicación del PR se registran al final.

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

Esta matriz corresponde a los criterios históricos de Pair-Block. La matriz final de SP-004, con enlaces a evidencia, aparece al cierre del documento.

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
| CA-10 | Notebook, decisión y commits del hito Pair-Block | PASS para el hito histórico; publicación y PR se verifican aparte. |


## Reapertura Pair-Block v2

| Fase | Trabajo | Evidencia | Estado |
|---|---|---|---|
| Auditoria rotacional | Explicar la simplificacion v1, el efecto por geometria, las oportunidades omitidas y el alcance de la literatura. | [Auditoria v2](../spikes/SP-004-pair-block-v2-auditoria.md). | Completa antes de tocar codigo; commit `3e46c45`. |
| Criterio de bloque | Retirar el umbral v1 no respaldado y fijar una ganancia local explicita antes de correr. | Formula local y limites de atribucion en auditoria v2. | Completo antes de ejecucion; criterio documentado. |
| Implementacion/pruning | Usar angulos del motor cada 5 grados, equivalencia raster exacta y cotas seguras. | Nuevos contadores y tests aislados. | Completa; resultados v2 preservados. |
| Casos predeclarados | Mantener fixtures y discriminante; declarar hasta tres casos razonables antes de benchmarks. | Manifiesto de intencion y JSON congelados. | Completos antes de benchmark; sin cambios posteriores. |
| Benchmark v2 | Comparar FF/BF/WF/Pair-Block en serie; registrar clasificacion A-E, placements y tres tiempos. | CSV/JSON v2. | Completo; NO-GO por baja aplicabilidad y costo. |
| Notebook/decision | Actualizar celdas, outputs reales y GO/NO-GO TA-042. | Notebook ejecutado y decision final. | Completo; NO-GO para TA-042. |

## Estado histórico — mini-spike y benchmark EXP Hole Filling

La tabla de Pair-Block v2 anterior es histórica y queda cerrada por la decisión NO-GO documentada en `docs/evidence/sprint-02/SP-004/README.md`. El trabajo de la etapa histórica siguiente fue el mini-spike HF:

| Fase | Trabajo | Evidencia | Estado |
|---|---|---|---|
| Literatura y auditoría | Contrastar hole filling/IFP publicado con la adaptación raster y documentar el motor actual. | SPEC y `SP-004-investigacion-m4.md`. | Completa antes de implementación. |
| Definición raster | Separar hueco interno físico de pocket candidato por pieza/orientación. | Componentes 4-conexas del espacio físico y de anclajes válidos; definición congelada en SPEC. | Completa antes de implementación. |
| Diagnosticos | Fijar hasta cuatro layouts, dimensiones y geometrias fuera de TA-027. | Manifiesto HF y casos JSON. | Completa antes de ejecucion; congelados en commits e624e60 y 3ac7b97. |
| Detector | Reutilizar mascaras existentes y el mapa de anclajes; no crear rasterizador. | Codigo aislado, SVG, JSON y pruebas. | Completa; tres positivos y control negativo. |
| Comparacion | Ejecutar FF/BF/WF/HF en los diagnosticos; clasificar A-E y decidir viabilidad. | CSV/JSON y trazas de placement. | Completa; VIABLE, B/B/B/A; maximo 5.85x. |
| Puerta oficial | Comparar EXP solo despues de VIABLE. | CSV/JSON oficial y dictamen. | Completa; A/D/E, cero pockets usados; NO-GO TA-042. |
| Notebook y cierre | Crear notebook con outputs reales y cerrar documentacion/commits locales. | SPEC/PLAN/TASKS/SP-004; sin push/PR/merge. | Completa al crear commits locales; sin push/PR/merge. |

### Matriz de verificacion del mini-spike HF

La matriz CA anterior pertenece al cierre histórico de Pair-Block. La verificación de HF se registra aquí y se resume con evidencia en la matriz final.

| Area | Evidencia | Estado |
|---|---|---|
| Detector y clasificacion | Hueco fisico y exterior separados; componentes de anclajes por pieza/orientacion; casos de circulo, triangulos, convexo y control negativo. | PASS; 7 pruebas de detector. |
| Reglas de placement | Material/espesor, margen, separacion, no solape, rotacion de 5 grados, layout inmutable, determinismo y fallback FF. | PASS; 4 pruebas de optimizer, con tres repeticiones funcionales. |
| Diagnosticos predeclarados | Cuatro JSON congelados antes de ejecutar; clases B/B/B/A. | PASS; HF-DIAGNOSTIC-001 a 004. |
| Gate de viabilidad | Pocket utilizado en tres casos, patron distinto, reglas validas y maximo 5.85x frente al baseline mas rapido, menor al umbral congelado de 10x. | VIABLE para habilitar comparacion EXP. |
| Benchmark oficial | Tres EXP inalterados; HF no utilizo pockets, clases A/D/E; COMPLEX supero 10x. | NO-GO para TA-042. |
| Regresiones | Tests HF y suites enfocadas FF/BF/WF, placement y ángulos. | PASS; recuento actualizado en la matriz final. |
| Notebook y evidencia | Notebook con outputs derivados de trazas guardadas, SVGs, CSV y JSON. | Completo; commits locales al cierre, sin push/PR/merge. |

## Cierre final — pedidos realistas

El mini-spike y el benchmark EXP anteriores se conservan como evidencia histórica. La última fase comparó pedidos sintéticos realistas congelados en `fda6d12`, sin cambiar TA-027 ni los fixtures previos.

| Fase | Trabajo | Evidencia | Estado |
|---|---|---|---|
| Intención y congelación | Definir y guardar tres pedidos con círculos, triángulos/convexos y mezcla antes de ejecutar métodos. | Tres SHA-256 y manifiesto con stock, dimensiones y regla de clasificación. | PASS; commit `fda6d12`. |
| Benchmark serial | FF/BF/WF y tres repeticiones HF por fixture, configuración compartida y métricas oficiales intactas. | CSV/JSON con tiempos, placements y contadores. | PASS; ejecuciones secuenciales. |
| Determinismo | Comparar firmas funcionales HF entre tres repeticiones. | Firmas sin tiempo y resultados por repetición en JSON. | PASS ×3 fixtures. |
| Visualización | Crear figuras de layout previo, pocket, pieza pendiente y placement solo si HF utilizó pocket. | Una figura para 002 y seis para 003; ninguna para 001. | PASS; escala de grises y SVG parseable. |
| Dictamen y notebook | Publicar resultados reales y aplicar la regla E > 10× predeclarada. | Notebook con outputs locales, CSV/JSON y reporte. | NO-GO para TA-042; A/E, B/E y D/E. |
| Pruebas | Ejecutar las pruebas específicas HF y regresiones FF/BF/WF/placement/ángulos. | Comandos y selección exacta de archivos en el [README de evidencia](../evidence/sprint-02/SP-004/README.md). | 13 HF específicas PASS; 145 regresiones PASS. Son grupos separados. |

HF-REALISTIC-001 no utilizó pockets y empató el baseline (A funcional), pero el runtime fue 270.88×. HF-REALISTIC-002 cambió el patrón con un pocket y métricas empatadas (B funcional), a 136.02×. HF-REALISTIC-003 usó seis pockets, pero colocó 19/20 y empeoró utilización, merma y recuperable (D funcional), a 424.65×. E prevalece como categoría registrada por el costo; la lectura funcional se informa aparte. La recomendación final es **NO-GO**.

Evidencia final: [intención y fixtures](../../experiments/optimization/hole_filling/cases/), [CSV](../evidence/sprint-02/SP-004/hole-filling/sp004_hf_realistic_results.csv), [traza](../evidence/sprint-02/SP-004/hole-filling/sp004_hf_realistic_trace.json), [notebook](../../experiments/optimization/colab/SP004-Hole-Filling.ipynb) y [reporte acumulado](../evidence/sprint-02/SP-004/README.md). Sin push, PR, merge ni integración TA-042.

## Matriz final de aceptación y decisión

Los CA-01–CA-10 pertenecen a la fase Pair-Block de esta SPEC. Se conservan como verificación histórica; la selección final de M4 se apoya además en la evidencia HF indicada debajo. PASS significa que el artefacto o la prueba citada existe; no significa que la heurística haya mejorado los benchmarks.

| CA | Evidencia comprobable | Estado |
|---|---|---|
| CA-01 | [Investigación y fuentes](../spikes/SP-004-investigacion-m4.md) distinguen el artículo de la adaptación. | PASS |
| CA-02 | [Pruebas Pair-Block](../../experiments/optimization/block_packing/test_block_experimental.py) cubren material, espesor y orientaciones. | PASS |
| CA-03 | [Pruebas Pair-Block](../../experiments/optimization/block_packing/test_block_experimental.py) cubren colisión, separación y layout. | PASS |
| CA-04 | [Pruebas Pair-Block](../../experiments/optimization/block_packing/test_block_experimental.py) y [traza](../evidence/sprint-02/SP-004/benchmark-results/sp004_block_v2_trace.json) conservan placements originales. | PASS |
| CA-05 | [Pruebas Pair-Block](../../experiments/optimization/block_packing/test_block_experimental.py) cubren fallback individual. | PASS |
| CA-06 | [CSV v2](../evidence/sprint-02/SP-004/benchmark-results/sp004_block_v2_results.csv) y [traza v2](../evidence/sprint-02/SP-004/benchmark-results/sp004_block_v2_trace.json) contienen métricas y diagnósticos. | PASS |
| CA-07 | [CSV v2](../evidence/sprint-02/SP-004/benchmark-results/sp004_block_v2_results.csv) identifica EXP-SMALL/MEDIUM/COMPLEX y el discriminante. | PASS |
| CA-08 | [Intención DJD](../../experiments/optimization/djd/DJD-DIAGNOSTIC-INTENT.md) y [traza diagnóstica](../evidence/sprint-02/SP-004/benchmark-results/sp004_djd_diagnostic_trace.json) documentan cuatro casos y su clasificación. | PASS |
| CA-09 | [Traza v2](../evidence/sprint-02/SP-004/benchmark-results/sp004_block_v2_trace.json) registra repeticiones; la suite experimental completa SP-004 (pruebas Filler, DJD, Pair-Block, HF y loader de casos) terminó con 65 passed, 0 failed, 0 skipped. | PASS |
| CA-10 | [Cuatro notebooks](../../experiments/optimization/colab/) con outputs preservados, [evidencia](../evidence/sprint-02/SP-004/README.md), [SPEC](SPEC-SP-004-heuristica-m4.md) y revisión académica. | PASS para el cierre documental; publicación y CI se verifican en el PR. |

| Verificación final HF | Evidencia comprobable | Estado |
|---|---|---|
| Detector y reglas | [Pruebas HF](../../experiments/optimization/hole_filling/test_detector.py) y [optimizer](../../experiments/optimization/hole_filling/test_optimizer.py): suite específica HF, 13 passed. Este grupo está incluido en las suites de 65 y 138; no se suma otra vez. | PASS |
| EXP y realistas | [Resultados oficiales](../evidence/sprint-02/SP-004/hole-filling/sp004_hole_filling_official_results.csv) y [realistas](../evidence/sprint-02/SP-004/hole-filling/sp004_hf_realistic_results.csv) conservan los resultados adversos. | PASS como evidencia; NO-GO para integrar esta implementación. |
| Capacidad específica | [CSV](../evidence/sprint-02/SP-004/hole-filling/sp004_hf_capability_results.csv), [traza](../evidence/sprint-02/SP-004/hole-filling/sp004_hf_capability_trace.json) y [figura](../../experiments/optimization/hole_filling/figures/HF-CAPABILITY-001-comparison.svg) muestran una plancha evitada en el caso controlado. | PASS como prueba de capacidad, sin extrapolación. |
| Selección M4 | La [SPEC](SPEC-SP-004-heuristica-m4.md) y la [investigación](../spikes/SP-004-investigacion-m4.md) exigen filtros previos, límite de costo y fallback a FF. | **GO condicionado para estudiar implementación optimizada en TA-042.** |

La suite combinada focalizada (HF, FF/BF/WF, loader de casos, reglas, métricas y ángulos) terminó con **138 passed, 0 failed, 0 skipped**. Es distinta de las 145 regresiones que incluyen placement y no incluyen los tests HF; ambas se repitieron. La suite experimental completa SP-004 terminó con **65 passed, 0 failed, 0 skipped**. Los cuatro grupos se solapan y no son aditivos; los comandos exactos están en el [README de evidencia](../evidence/sprint-02/SP-004/README.md). TA-042 no se implementa en esta rama.
