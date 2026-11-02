# Revisión de diseño y evidencia — SP-004 M4

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

La recomendación para TA-042 es no integrar M4 en esta iteración. Se puede reevaluar Pair-Block tras reducir búsqueda de offsets/orientaciones y medir casos operativos con mejoras repetibles. Los resultados de Filler y DJD permanecen archivados.
