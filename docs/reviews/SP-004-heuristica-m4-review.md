# Revisión académica y de evidencia — SP-004 M4

**Revisor:** Andro Joseph Quispe Cesias

**Autor de la SPEC:** Andro Joseph Quispe Cesias

La revisión de Pair-Block que sigue se conserva como antecedente. El dictamen final de las cuatro alternativas y de Hole Filling aparece al cierre.

Este dictamen corresponde a Pair-Block v1 y queda supersedido para la decisión del candidato hasta completar v2. La auditoría previa al cambio está en [SP-004-pair-block-v2-auditoria.md](../spikes/SP-004-pair-block-v2-auditoria.md).

## Alcance revisado

Pair-Block experimental y diagnóstico adicional DJD. Se comprobaron la diferencia entre la referencia publicada y la adaptación local, el uso del motor geométrico inmutable, la descomposición a placements originales, la prioridad retazo→plancha, la separación, determinismo, métricas y regresiones. No se proponen cambios productivos.

## Revisión de investigación

Cai et al. (2023), DOI [10.1016/j.cor.2023.106398](https://doi.org/10.1016/j.cor.2023.106398), respaldan bloques de dos o más formas complementarias para mejorar utilización local. El método publicado también contiene residuales con líneas de referencia, scoring y operadores de búsqueda/repacking. La densidad raster de caja del spike es una métrica operacional explícita y no se presenta como fórmula de los autores. El texto completo del editor no fue accesible en esta sesión; la descripción se limita a los pasajes editoriales e indexados disponibles.

## Decisiones de diseño

- Solo parejas dentro del mismo material y espesor; se ordenan bloques por suma de áreas junto a unidades sueltas, descendente y con desempate estable.
- Solo orientaciones cardinales que ya pertenecen a la grilla de rotación de NewGlass; offsets relativos acotados, filtro de escala de bounding boxes 4:1 y ocho anclajes máximos por eje.
- Las máscaras de ambos miembros se validan en `SheetLayout` sintético con la separación configurada. El bloque se valida y coloca sobre el layout del stock; las salidas siguen siendo dos `Placement` originales.
- Si la máscara no cabe, el par se reintroduce en la cola como unidades individuales, manteniendo la prioridad de área y las reglas de retazo→plancha.
- La densidad exige mejora estricta sobre la mayor densidad individual de ambos miembros. Esto no garantiza una mejora global; solo filtra la formación local.

## Evidencia revisada

- Pair-Block: 11 pruebas específicas pasan; la suite combinada de Pair-Block, DJD, Filler y regresiones FF/BF/WF terminó con 104 passed. SMALL/MEDIUM/COMPLEX mantienen cobertura completa. Ningún bloque se coloca en TA-027; en COMPLEX se propuso uno y el fallback individual conservó las métricas FF. El runtime fue 2.998 s frente a 169 ms de FF. El discriminante coloca un bloque y cambia el patrón frente a FF, con métricas globales iguales.
- Determinismo Pair-Block: placements, composiciones y métricas iguales en tres repeticiones de cada uno de los cuatro casos.
- DJD adicional: cuatro casos declarados antes de correr. Solo DJD-DIAGNOSTIC-003 escoge una terna; sus métricas empatan con FF/BF/WF. DJD-DIAGNOSTIC-004 empata al mejor baseline; no mejora a FF/BF. No se observa mejora funcional sobre el mejor baseline en esta matriz.
- No se alteraron los fixtures TA-027 ni los módulos productivos.

## Dictamen

**Aprobado como evidencia de Spike y aprendizaje técnico. NO-GO para llevar Pair-Block, DJD o Filler a TA-042 con la evidencia actual.** Pair-Block prueba que se puede formar, validar y descomponer una unidad compuesta sin modificar producción, pero el costo de generación es alto y no se colocaron bloques en los casos oficiales. El resultado discriminante prueba patrón e identidad, no una mejora funcional.

En esta etapa histórica se recomendó no integrar Pair-Block. Una reevaluación requeriría reducir la búsqueda y medir casos operativos con mejoras repetibles. Los resultados de Filler y DJD permanecen archivados.

## Revisión final de SP-004

**Documentación revisada:** [SPEC](../specs/SPEC-SP-004-heuristica-m4.md), [PLAN y matriz CA](../specs/PLAN-SP-004-heuristica-m4.md), [TASKS](../specs/TASKS-SP-004-heuristica-m4.md), [investigación](../spikes/SP-004-investigacion-m4.md) y [evidencia](../evidence/sprint-02/SP-004/README.md). Se revisaron los cuatro notebooks de Filler, DJD, Pair-Block y Hole Filling: mantienen el orden título, código comentado, output real e interpretación breve.

**Resultados revisados:** Filler fue demasiado parecido al FF real; DJD eligió grupos distintos sin mejora funcional consistente y con costo alto; Pair-Block formó bloques en diagnósticos, pero rara vez los colocó en los casos oficiales y su costo fue alto. Hole Filling mostró decisiones propias, aunque EXP y los tres pedidos realistas no justifican integrar la búsqueda exhaustiva: el pedido mixto perdió cobertura y los tiempos fueron elevados. Los resultados negativos permanecen en CSV, trazas y notebooks.

En HF-CAPABILITY-001, FF/BF/WF usaron un retazo y una plancha; HF colocó P11 en un espacio interior y dejó libre el exterior para P12, por lo que usó solo un retazo. La utilización fue 33.787% frente a 67.575% y la merma 37,516.56 frente a 22,410.56 mm². HF registró menos área recuperable (2,466 frente a 64,080 mm²) y tardó más (262.99 frente a 62–63 ms). El fixture fue diseñado para demostrar esa capacidad y no representa el rendimiento general.

**CA y pruebas:** la matriz final del PLAN enlaza CA-01–CA-10 y la evidencia HF. La suite de las cuatro alternativas y loader terminó con **65 passed, 0 failed, 0 skipped**; la suite focalizada de HF, FF/BF/WF, casos experimentales, reglas, métricas y ángulos terminó con **138 passed, 0 failed, 0 skipped**. La evidencia permite marcar PASS de verificación documental y funcional, sin convertir los resultados adversos en mejoras.

**Decisión revisada:** Raster Hole Filling / Pocket Filling queda seleccionado como M4 con **GO condicionado para estudiar una implementación optimizada en TA-042**. TA-042 debe probar filtros baratos de activación, límite de costo y retorno a FF. La versión exhaustiva del Spike conserva el NO-GO para integración directa; no se recomienda superioridad general. Esta revisión no inicia TA-042 ni autoriza un merge.
