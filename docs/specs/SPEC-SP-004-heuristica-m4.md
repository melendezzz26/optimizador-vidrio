# SPEC-SP-004 — Investigación comparativa de heurística M4

## Estado

Filler, DJD-1/3 y Pair-Block v1/v2 quedan como candidatos **NO-GO para TA-042**, con evidencia histórica preservada. El candidato actual de SP-004 es un mini-spike local de Raster Hole Filling / Pocket Filling. No se integra ninguna heurística en producción; no se cambian FF/BF/WF, TA-027, API, frontend ni BD.

## Contexto y objetivo

SP-004 estudia una cuarta política M4 para NewGlass. Las evaluaciones de Filler, DJD-1/3 y Pair-Block se conservan como antecedentes descartados. Este mini-spike evalúa si una política que busca primero encajes en huecos/pockets existentes puede cambiar placements sin cambiar el motor productivo ni fixtures oficiales.

El objetivo vigente es determinar si una política de pocket-first puede aprovechar espacios ya formados y producir placements diferentes usando la geometría y validación raster existentes. Los resultados Pair-Block que preceden a esta actualización se conservan como historia experimental, no como candidato actual.

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
- Estado al cierre de Pair-Block v1: **NO-GO para Filler y DJD-1/3**; Pair-Block v2 seguía pendiente en esa revisión. Esta nota es histórica; el dictamen posterior de Pair-Block v2 fue NO-GO (ver la evidencia de SP-004 al final de esta SPEC). No hay selección productiva de M4.

Una reconsideración futura de Pair-Block debe reducir el costo de generación y obtener bloques colocados con mejoras funcionales repetibles en instancias operativas. La diferencia de patrón en un caso discriminante confirma el mecanismo, no justifica su integración.

Pair-Block v1 fue un ensayo de rotaciones cardinales con una m?trica raster local; sus resultados se conservan como antecedente, no como evaluaci?n final del candidato.

Pair-Block v1 fue un ensayo de rotaciones cardinales con una métrica raster local; sus resultados se conservan como antecedente, no como evaluación final del candidato.

## Fuera de alcance

Integración en TA-042, cambios productivos, alteración de fixtures, publicación de rama, PR, merge y smoke post-merge.

## Mini-spike HF — especificación experimental vigente

### Literatura y atribución

**Método publicado.** Abeysooriya, Bennell y Martinez-Sykora (2018) conservan como polígonos los espacios cerrados que aparecen al unir las piezas colocadas, descartan huecos menores que el área de la pieza pendiente más pequeña y comprueban el encaje de una pieza dentro del hueco mediante Inner Fit Polygon (IFP). Ordenan los huecos por coordenada x izquierda y prueban primero hole filling antes de las reglas de placement restantes. Błażewicz et al. (1993) describen backfilling de huecos con una búsqueda tabu que cambia layouts; el artículo de Burke et al. (2006) resume el antecedente y advierte que comprobar la factibilidad de los movimientos era el reto principal. Una revisión de 2022 también describe el uso de IFP para llenar huecos geométricos. Ninguna de estas fuentes define el detector raster local de este spike.

**Adaptación experimental NewGlass.** Se medirán dos objetos diferentes, sin llamar “pocket” a cualquier celda libre:

1. **Hueco interno físico:** componente 4-conexo de celdas libres dentro de la máscara del material que no toca una celda exterior al material. Se informa su área, celdas y caja envolvente. Es una definición topológica de la grilla, no de geometría continua.
2. **Pocket utilizable por una pieza/orientación:** componente 4-conexo del mapa de anclajes raster donde `SheetLayout.check(mask, fila, columna)` acepta el placement. Si la componente no toca el borde del dominio de anclajes, es un pocket para esa máscara y orientación: existe un placement legal dentro de la zona, pero no una secuencia de desplazamientos unitarios 4-conexos legales que lo conecte con el exterior. Esta definición detecta también una cavidad parcialmente abierta cuando su abertura no admite esa pieza bajo la orientación y reglas actuales. Si la abertura sí la admite, el detector no la clasifica como pocket; queda en el espacio exterior.

El tamaño del pocket de placement se expresará como número de anclajes legales y `anchor_cells × resolution_mm²`; **no** se confundirá con el área física de la cavidad. Para la imagen se mostrarán por separado celdas ocupadas/libres/huecos físicos y las componentes de anclajes de la pieza inspeccionada. La conectividad 4-direccional y el dominio discreto son decisiones explícitas del laboratorio; no se atribuyen a un algoritmo publicado ni equivalen a accesibilidad continua.

### Auditoría del motor

- Una fuente se rasteriza a `RasterMask`: cada fila es un entero de bits. `SheetLayout` mantiene `material`, `usable`, `occupied`, `blocked` y `separation_cells`; cada stock tiene su layout identificado por `StockCandidate.identity`.
- `SheetLayout.check()` valida dimensiones/resolución, límites y celdas completamente dentro del material, margen en `usable`, intersección de bits contra `occupied` y distancia contra `blocked`. La separación se aplica mediante dilatación raster; el margen mediante erosión de la máscara material. El motor convierte ambas distancias a celdas con redondeo hacia arriba.
- `first_position()` encuentra el primer origen legal con intersecciones por bits. El spike enumerará orígenes discretos llamando a `check()`; no implementa colisión alternativa ni crea un rasterizador.
- `OptimizationConfig.angular_step_deg` y `discrete_angles()` generan el conjunto discreto vigente; en estos casos será `0°, 5°, …, 355°`. El `RasterCache` de la corrida genera las máscaras con `rasterize_geometry` existente y deduplica máscaras completas idénticas como hace el motor.
- `SheetLayout` es inmutable: `place()` devuelve otro layout. `PieceUnit` y `StockCandidate` son snapshots inmutables. La prueba utilizará layouts temporales locales; no modificará inventario.
- La fuente es explícita: `MaterialSource.REMNANT` o `MaterialSource.SHEET`. El packing considera retazos antes que planchas y conserva estado por identidad física del stock; el spike retendrá esta prioridad en el fallback.

### Política experimental y límites

Después de colocar semillas válidas, Hole Filling inspecciona layouts ya usados. Ordena pockets por x mínima, luego y mínima, identidad estable de unidad y rango de orientación del motor; selecciona la primera pieza pendiente que tenga anclajes legales en una componente pocket y coloca su primer anclaje legal por (fila, columna). Esta es una política **local propia**, no la política completa de Abeysooriya et al. Si no encuentra placement pocket-first, usa el First Fit existente como fallback experimental. No minimiza rectángulos libres, merma ni un score BRF: intenta aprovechar una región ya existente.

La versión inicial corre solo sobre los cuatro diagnósticos predeclarados. Solo si demuestra una decisión distinta, placement pocket real, reglas respetadas, determinismo y costo razonable se considera pasar al benchmark EXP-SMALL/MEDIUM/COMPLEX. No se modifica TA-027 ni se crea notebook si el mini-spike resulta NO VIABLE.

### Fuentes académicas verificadas

- Abeysooriya, R. P., Bennell, J. A. y Martinez-Sykora, A. (2018), “Jostle heuristics for the 2D-irregular shapes bin packing problems with free rotation”, *International Journal of Production Economics* 195, 12–26, DOI [10.1016/j.ijpe.2017.09.014](https://doi.org/10.1016/j.ijpe.2017.09.014). [Artículo aceptado en White Rose](https://eprints.whiterose.ac.uk/id/eprint/134688/1/Accepted_article_IJPE.pdf).
- Błażewicz, J., Hawryluk, P. y Walkowiak, R. (1993), “Using a Tabu Search Approach for Solving the Two-Dimensional Irregular Cutting Problem”, *Annals of Operations Research* 41, 313–325, DOI [10.1007/BF02022998](https://doi.org/10.1007/BF02022998). El alcance observado aquí es búsqueda tabu/backfilling descrito por fuentes secundarias; no se atribuye a este artículo la definición raster de NewGlass.
- Burke, E., Hellier, R., Kendall, G. y Whitwell, G. (2006), “A New Bottom-Left-Fill Heuristic Algorithm for the Two-Dimensional Irregular Packing Problem”, *Operations Research* 54(3), 587–601, DOI [10.1287/opre.1060.0293](https://doi.org/10.1287/opre.1060.0293). [PDF de INFORMS](https://quaoar.su/files/papers/nesting/opre.1060.0293.pdf).
- Guo, B. et al. (2022), “Two-dimensional irregular packing problems: A review”, *Frontiers in Mechanical Engineering* 8, DOI [10.3389/fmech.2022.966691](https://doi.org/10.3389/fmech.2022.966691). [Texto completo](https://www.frontiersin.org/journals/mechanical-engineering/articles/10.3389/fmech.2022.966691/full).

### Diferencia frente a BRF

BRF puntúa el sobrante hipotético de una colocación candidata. Hole Filling parte de una región ya creada y pregunta si alguna pieza pendiente cabe en ella. El spike no optimiza `largest_rectangle`, no reutiliza el score BF/WF para detectar pockets y no formula un score de merma.
