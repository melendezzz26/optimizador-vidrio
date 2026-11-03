# SPEC-SP-004 — Investigación comparativa de heurística M4

**Autor:** Andro Joseph Quispe Cesias

**Revisor:** Andro Joseph Quispe Cesias

## Estado

**M4 seleccionado: Raster Hole Filling / Pocket Filling, con GO condicionado para estudiar una versión optimizada en TA-042.** Busca aprovechar espacios entre piezas ya colocadas. En un caso controlado evitó abrir una plancha, pero no mejoró todos los pedidos: la búsqueda exhaustiva experimental fue lenta y empeoró un pedido mixto. Por ello, esa implementación conserva su **NO-GO para integración directa**. Filler, DJD y Pair-Block también conservan sus resultados y dictámenes históricos. No se cambia producción, FF/BF/WF, TA-027, API, frontend ni BD.

## Contexto y objetivo

SP-004 estudia una cuarta política M4 para NewGlass. Las evaluaciones de Filler, DJD-1/3 y Pair-Block se conservan como antecedentes descartados. Este mini-spike evalúa si una política que busca primero encajes en huecos/pockets existentes puede cambiar placements sin cambiar el motor productivo ni fixtures oficiales.

La investigación comprobó si Hole Filling puede poner una pieza pendiente en un espacio útil que dejaron otras piezas. La validación geométrica sigue a cargo del motor raster de NewGlass. Los resultados de Pair-Block se conservan como historia experimental.

## Alcance experimental histórico: Pair-Block

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

## Criterios de aceptación históricos de Pair-Block

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
| CA-10 | Notebook Colab, evidencia y decisión comparativa quedan registrados; la publicación y PR se verifican en el cierre de SP-004. |

## Métricas

Se conservan las métricas oficiales de `calculate_metrics`: requested/placed/unplaced, retazos, planchas, aprovechamiento, merma, área recuperable y runtime. Diagnósticos Pair-Block: `candidate_pairs`, `filtered_pairs`, `geometrically_checked_pairs`, `accepted_blocks`, `pieces_in_blocks`, `standalone_pieces`, `block_compaction`, `block_generation_ms` y `packing_ms`. Diagnósticos DJD se mantienen en sus campos existentes.

## Evaluación comparativa y selección de candidato M4

- Pair-Block creó un bloque triangular y produjo un patrón distinto en el discriminante, pero sus métricas empataron con FF/BF/WF. En los tres casos oficiales no colocó ningún bloque. En COMPLEX aceptó una composición geométrica, no cupo, aplicó fallback individual y conservó métricas FF con runtime 17.7 veces mayor.
- Los cuatro diagnósticos DJD se clasificaron A. DJD-1/3 eligió una terna en DJD-DIAGNOSTIC-003, con métricas iguales a los baselines; ningún caso mejoró al mejor baseline.
- El notebook tiene 34 secciones y outputs locales de ejecuciones reales; las firmas Pair-Block se mantuvieron iguales en tres repeticiones por caso.
- Estado al cierre de Pair-Block v1: **NO-GO para Filler y DJD-1/3**; Pair-Block v2 seguía pendiente en esa revisión. Esta nota es histórica; el dictamen posterior de Pair-Block v2 fue NO-GO (ver la evidencia de SP-004 al final de esta SPEC). No hay selección productiva de M4.

Una reconsideración futura de Pair-Block debe reducir el costo de generación y obtener bloques colocados con mejoras funcionales repetibles en instancias operativas. La diferencia de patrón en un caso discriminante confirma el mecanismo, no justifica su integración.

Pair-Block v1 fue un ensayo de rotaciones cardinales con una métrica raster local; sus resultados se conservan como antecedente, no como evaluación final del candidato.

## Fuera de alcance

Implementación de TA-042, cambios productivos, alteración de fixtures, merge y smoke post-merge. La publicación y revisión del PR pertenecen al cierre documental de SP-004.

## Mini-spike HF — especificación experimental conservada

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

### Resultados del mini-spike y benchmark condicionado

Los cuatro layouts congelados se ejecutaron con FF/BF/WF y luego HF; HF se repitió tres veces por caso. Todas las semillas y placements finales se volvieron a validar al reproducir cada layout con `SheetLayout.check/place`.

| Caso | Clasificación | Componentes pocket | Usados | HF ms | HF/rápido baseline | Resultado |
|---|---:|---:|---:|---:|---:|---|
| HF-DIAGNOSTIC-001 círculo/marco | B | 3 | 1 | 14.09 | 4.60× | Rectángulo 1×1 en (7,5), retazo, 0°; mismo resultado funcional que el mejor baseline. |
| HF-DIAGNOSTIC-002 triángulos | B | 12 | 1 | 21.68 | 5.85× | Triángulo 2×2 en (5,13), plancha, 0°; mismo resultado funcional. |
| HF-DIAGNOSTIC-003 polígono convexo | B | 3 | 1 | 13.46 | 3.85× | Rectángulo 1×1 en (7,5), plancha, 0°; mismo resultado funcional. |
| HF-DIAGNOSTIC-004 control | A | 0 | 0 | 13.13 | 1.08× | Sin pocket; fallback FF coloca 6×6 en plancha porque no cabe en retazo. |

Ninguno de los cuatro layouts formó un hueco físico completamente cerrado; las separaciones dejan el espacio de celdas conectado. Los casos 001–003 sí formaron componentes interiores en el mapa específico de anclajes válidos. En tres repeticiones por caso se repitieron firma de placements y decisiones de pocket. El máximo costo relativo fue 5.85×, inferior al umbral local congelado de 10×. **Dictamen del mini-spike: VIABLE.**

El tiempo se desgloso para separar deteccion y busqueda geometrica; los anclajes legales se generan con operaciones raster por bits y sus componentes se etiquetan de forma determinista.

| Caso | Orientaciones | Anclajes evaluados | Opciones por decision | Pockets | Usados | Checks geometricos exactos | Deteccion ms | Placement ms | Total HF ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| HF-DIAGNOSTIC-001 | 2 | 839 | 3 | 3 | 1 | 1 | 0.89 | 9.43 | 14.09 |
| HF-DIAGNOSTIC-002 | 12 | 8,532 | 12 | 12 | 1 | 1 | 7.22 | 11.07 | 21.68 |
| HF-DIAGNOSTIC-003 | 2 | 839 | 3 | 3 | 1 | 1 | 0.59 | 9.31 | 13.46 |
| HF-DIAGNOSTIC-004 | 15 | 19 | 0 | 0 | 0 | 0 | 0.02 | 11.25 | 13.13 |

En total, el detector inspecciono 10,229 origenes de anclaje en los cuatro casos. Las opciones por decision y los checks exactos son contadores del trace. La verificacion final de cada placement seleccionado se hizo con `SheetLayout.place/check`; la generacion del mapa no sustituye la comprobacion geometrica del motor. Las corridas fueron seriales, sin multiprocessing; el pico de RAM no se midio.


La puerta VIABLE autorizó la comparación posterior sobre los tres fixtures EXP existentes, leídos sin edición:

| Caso | Clase | Colocadas | Planchas | Uso | Merma mm² | Recuperable mm² | HF ms | HF/rápido baseline | Pockets usados |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| EXP-SMALL-001 | A | 3/3 | 1 | 60.000% | 0.00 | 8 | 12.57 | 1.15× | 0 |
| EXP-MEDIUM-001 | D | 9/9 | 1 | 28.413% | 201.86 | 58 | 87.53 | 4.92× | 0 |
| EXP-COMPLEX-001 | E | 24/24 | 3 | 29.598% | 746.72 | 184 | 1,325.45 | 14.83× | 0 |

HF no usó ningún pocket en EXP. SMALL empató con FF; MEDIUM reprodujo FF y quedó detrás de BF en merma (8 mm²) y área recuperable (8 mm²); COMPLEX también reprodujo FF y la búsqueda superó 10× el baseline más rápido. El dictamen para integración en TA-042 es **NO-GO** aunque el detector/placement funcionen en los diagnósticos deliberadamente apropiados. Esto demuestra que la señal es poco frecuente en esta matriz y que el costo puede crecer sin producir una decisión nueva.

La evidencia está en [traza mini-spike](../evidence/sprint-02/SP-004/hole-filling/sp004_hole_filling_trace.json), [CSV mini-spike](../evidence/sprint-02/SP-004/hole-filling/sp004_hole_filling_results.csv), [detección](../evidence/sprint-02/SP-004/hole-filling/sp004_hole_filling_detection.json), [traza EXP](../evidence/sprint-02/SP-004/hole-filling/sp004_hole_filling_official_trace.json), [CSV EXP](../evidence/sprint-02/SP-004/hole-filling/sp004_hole_filling_official_results.csv) y [notebook con outputs locales](../../experiments/optimization/colab/SP004-Hole-Filling.ipynb). La verificación final distingue cuatro alcances: 13 pruebas específicas HF; 65 de la suite experimental completa SP-004; 138 de la suite combinada HF/motor/casos/reglas/métricas/ángulos; y 145 regresiones FF/BF/WF, placement y ángulos. Son selecciones distintas y solapadas, no conteos aditivos. Los comandos y archivos exactos están en el [README de evidencia](../evidence/sprint-02/SP-004/README.md).

## Validación final con pedidos realistas

Los pedidos `HF-REALISTIC-001/002/003` quedaron congelados antes de correr los métodos en el commit local `fda6d12`; [HF-REALISTIC-INTENT.md](../../experiments/optimization/hole_filling/cases/HF-REALISTIC-INTENT.md) contiene la composición, rationale y SHA-256. Se compararon FF/BF/WF con HF serialmente, y HF se repitió tres veces por caso, con configuración idéntica: raster 1 mm, ángulos cada 5°, margen 5 mm, separación 3 mm, material 1, espesor 6 mm y stock retazo → plancha.

| Fixture | Resultado observado | Clasificación con regla congelada |
|---|---|---|
| HF-REALISTIC-001, círculos y piezas pequeñas | 0 pockets usados; 15/15, mismas métricas/patrón; HF 96.38 s contra mejor baseline 0.356 s (270.88×). | E por costo; funcionalmente A |
| HF-REALISTIC-002, triángulos y convexos | 11 componentes candidatos; 1 pocket usado para pieza 5 a 255°, (283, 41); métricas empatadas; HF 236.79 s contra 1.741 s (136.02×). | E por costo; funcionalmente B |
| HF-REALISTIC-003, mezcla heterogénea | 70 componentes candidatos; 6 placements pocket; 19/20, menor uso, mayor merma y menos recuperable; HF 238.46 s contra 0.562 s (424.65×). | E por costo; funcionalmente D |

La traza usa "pockets detectados" para componentes interiores del mapa de anclajes por pieza/orientación; no representa cavidades físicas únicas. Para el caso 003 los seis placements fueron reproducibles, pero no evitaron una pieza sin colocar. Las firmas funcionales de HF coinciden entre las tres repeticiones de cada caso. La generación del mapa de anclajes domina el costo y se informa separada del etiquetado y placement.

**Dictamen de la implementación experimental: NO-GO para integración directa en TA-042.** 001 no usa pockets y solo replica el baseline; 002 cambia el patrón pero empata métricas a 136×; 003 usa pockets pero empeora cobertura, aprovechamiento, merma y recuperable a 425×. El efecto práctico no compensa el costo de esta implementación. No se ajustó la regla de clasificación después de ver los resultados.

Artefactos: [CSV realista](../evidence/sprint-02/SP-004/hole-filling/sp004_hf_realistic_results.csv), [traza y firmas](../evidence/sprint-02/SP-004/hole-filling/sp004_hf_realistic_trace.json), [fixtures congelados](../../experiments/optimization/hole_filling/cases/) y [notebook final](../../experiments/optimization/colab/SP004-Hole-Filling.ipynb). En la repetición final pasaron 13 pruebas específicas HF y 145 regresiones FF/BF/WF, placement y ángulos. La suite experimental completa SP-004 pasó 65; una selección combinada más amplia de HF, motores, casos, reglas, métricas y ángulos pasó 138. Los grupos se solapan; no se suman. Los comandos reproducibles están en el [README de evidencia](../evidence/sprint-02/SP-004/README.md).

## Selección final y condición para TA-042

HF-CAPABILITY-001 se diseñó para mostrar una situación favorable. FF, BF y WF pusieron primero la pieza pequeña P11 en la parte exterior del retazo; cuando llegó el círculo P12, necesitaron una plancha. Hole Filling colocó P11 en un espacio interior aprovechable y conservó libre la zona exterior para P12. Todos colocaron 18/18 piezas.

| Método | Retazos | Planchas nuevas | Utilización | Merma | Área recuperable | Tiempo |
|---|---:|---:|---:|---:|---:|---:|
| FF/BF/WF | 1 | 1 | 33.787% | 37,516.56 mm² | 64,080 mm² | 62–63 ms |
| Hole Filling | 1 | 0 | 67.575% | 22,410.56 mm² | 2,466 mm² | 262.99 ms |

El área recuperable registrada fue menor y Hole Filling tardó más. Este caso controlado demuestra una capacidad específica; no estima el rendimiento general. La [traza](../evidence/sprint-02/SP-004/hole-filling/sp004_hf_capability_trace.json) y el [notebook](../../experiments/optimization/colab/SP004-Hole-Filling.ipynb) conservan las colocaciones y las mediciones.

**Decisión de SP-004: GO condicionado para continuar con Hole Filling como M4 en TA-042.** TA-042 deberá estudiar filtros previos baratos para activar la búsqueda solo en pedidos prometedores, limitar su costo y volver a FF cuando no encuentre un espacio útil. La implementación exhaustiva de este Spike no debe copiarse directamente a producción.
