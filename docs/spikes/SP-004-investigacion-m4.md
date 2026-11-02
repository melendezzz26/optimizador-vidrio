# SP-004 — Investigación y experimentación de heurística adicional M4

## 1. Contexto

SP-004 conserva dos evaluaciones previas: Filler se descartó por similitud práctica con FF real; DJD-1/3 mostró elecciones de grupos distintas pero obtuvo NO-GO provisional por costo y no cambiar las métricas de TA-027. La nueva evaluación principal es **Adaptación experimental Pair-Block de la heurística basada en bloques**. También se hará un diagnóstico pequeño de DJD, sin rediseñar el algoritmo ni tocar los fixtures oficiales.

## 2. Fuentes y alcance de Block Packing

Cai, Deng, Lee, Chew y Li (2023) estudian bin packing irregular 2D con rotaciones limitadas. Su artículo introduce bloques de dos o más piezas, combinando formas complementarias para mejorar la utilización local; además utiliza espacios residuales con líneas de referencia, puntuación de compatibilidad entre bloque/pieza y espacio, operadores de ajuste/movimiento/llenado/reemplazo/intercambio y estrategias de repacking. El artículo reporta que los bloques son una parte de un método más amplio, no un optimizador autónomo.

**Método publicado:** bloques de dos o más piezas de formas complementarias para mejorar la utilización local; selección/placement guiados también por espacios residuales con líneas de referencia y puntuación, además de operaciones de ajuste, movimiento, llenado, reemplazo, intercambio y repacking. El artículo describe la utilización local como objetivo de los bloques, pero los pasajes editoriales disponibles no proporcionan una fórmula universal autónoma de compacidad. La página editorial deja ver el resumen, la introducción y una descripción parcial del proceso; el texto completo devuelve 403 en esta sesión.

**Adaptación experimental NewGlass:** Pair-Block limita el grupo a dos piezas, usa las orientaciones cardinales que pertenezcan al conjunto permitido por la configuración, prueba hasta ocho anclajes relativos por eje y crea una máscara raster compuesta temporal. Ordena bloques por suma de área y piezas sueltas por su área, descendente, con desempate estable. Cada pieza sigue produciendo su propio placement e identidad. No se implementan las líneas de referencia, los operadores de búsqueda ni el repacking del artículo.

La ficha editorial y el texto indexado de la publicación dicen que se generan bloques con dos o más piezas para mejorar la utilización local y reducir desperdicio mediante formas complementarias; por separado, mencionan reglas de puntuación que emparejan espacios residuales con piezas o bloques para elegir secuencia y posición. No encontramos en los pasajes accesibles una fórmula universal de “compactación de bloque”. Por eso, antes de ejecutar benchmarks, se fijó esta regla experimental observable: `densidad_raster = celdas ocupadas por A∪B / celdas de la caja envolvente de A∪B`; solo se acepta la pareja si supera estrictamente la mayor densidad raster individual de A y B. Este índice no se atribuye al artículo: es una operacionalización local de su objetivo de uso local y complementariedad. El filtro económico rechaza parejas cuya caja envolvente mayor tenga más de cuatro veces las celdas de la menor. La búsqueda explora como máximo ocho offsets deterministas por eje y orientaciones cardinales permitidas; esos límites acotan el costo en hardware de 8 GB y hacen que el laboratorio no replique la búsqueda publicada completa.

Referencia principal: Cai, S., Deng, J., Lee, L. H., Chew, E. P. y Li, H. (2023), “Heuristics for the two-dimensional irregular bin packing problem with limited rotations”, *Computers & Operations Research*, 160, 106398. DOI: [10.1016/j.cor.2023.106398](https://doi.org/10.1016/j.cor.2023.106398). [Ficha editorial](https://www.sciencedirect.com/science/article/pii/S0305054823002629).

Para la geometría de contacto y separación en nesting se revisará también la bibliografía de NFP, en particular Bennell y Song (2008/2009) y la revisión académica de packing irregular; ninguna fuente sustituye la validación raster local.

## 3. Explicación sencilla

En vez de entregar siempre cada pieza por separado, Pair-Block busca dos geometrías compatibles que puedan formar una composición compacta. Por ejemplo, dos triángulos complementarios pueden crear una forma conjunta cercana a un rectángulo. El bloque solo organiza el packing: al devolver el resultado, las piezas mantienen sus IDs, geometrías, giros y posiciones individuales. Si una pieza no encuentra pareja útil o el bloque no cabe, sigue como unidad individual.

## 4. Diferencia frente a FF/BF/WF y BRF

El comportamiento local real está en `domain/packing.py`: FF elige la primera fuente/rotación/posición viable para una pieza; BF elige entre fuentes candidatas para esa pieza la que deja menos celdas libres; WF usa la que deja más. No se encontró un método BRF registrado en el backend actual; la comparación BRF será conceptual y se marcará así. BRF examina qué tan valioso/calificable es el espacio sobrante de una colocación. Pair-Block examina si dos piezas pueden formar una composición densa antes de pasarla a packing. Son decisiones distintas.

## 5. Auditoría del motor y viabilidad sin producción

`PieceUnit.geometry` y `Placement.geometry` se limitan a rectángulos, círculos y polígonos convexos. La unión de dos piezas puede ser no convexa o tener huecos; no puede guardarse como una única geometría canónica sin ampliar producción. En cambio `SheetLayout` opera sobre `RasterMask` inmutables y acepta una máscara compuesta temporal. Por tanto Pair-Block puede:

1. rasterizar cada miembro con las orientaciones disponibles de `PreparedRunGeometry`;
2. explorar offsets relativos deterministas en una caja sintética y validar separación/no solape mediante `SheetLayout.check`;
3. combinar las filas de bits en una máscara de bloque local;
4. colocar esa máscara con el layout del stock y guardar dos placements originales traducidos por sus offsets internos.

Así se reutilizan rasterización, giros, separación, margen, stock y métricas, sin introducir geometrías de producción. La máscara no se persiste ni se presenta como geometría de una pieza.

## 6. Criterio experimental de Pair-Block

La medida de adaptación es `celdas ocupadas en la unión / (columnas de su bounding box × filas de su bounding box)`. Se aceptan solo valores estrictamente mayores que la mayor densidad raster entre los dos miembros por separado; una pareja que no supera ese piso sigue como dos piezas individuales. Las dos huellas deben pasar `SheetLayout.check` en una hoja sintética usando la separación vigente. Bloques y piezas individuales se ordenan por área unitaria (para un bloque, suma del área de sus miembros), descendente y con desempate por identidad estable. No se está afirmando que Cai et al. usen esta fracción o este orden exacto: el artículo respalda el objetivo de complementariedad/utilización local; estas reglas dan una política acotada y reproducible para filtrar pares y evitar copiar FF por pieza. El filtro de escala 4:1 y los hasta ocho anclajes por eje limitan esfuerzo; son decisiones del laboratorio.

La composición trabaja con celdas raster conservadoras, no área geométrica continua. Se registra el promedio de densidad de los bloques seleccionados y cada valor individual para hacer visible esa limitación. El bloque temporal se prueba en los stocks del motor; las dos geometrías originales se reconstruyen después con sus ángulos y offsets.

## 7. Diagnóstico DJD

Se prepararon cuatro instancias externas a TA-027; el manifiesto de intención se guardó antes de ejecutar FF/BF/WF/DJD y las dimensiones no se cambiaron después.

| Caso | Decisión DJD | Métricas frente a mejor baseline | Categoría | Runtime DJD |
|---|---|---|---:|---:|
| DJD-DIAGNOSTIC-001 | Cuatro selecciones individuales: pieza grande en retazo, luego círculo y dos rectángulos en plancha. | 4/4; 1 retazo, 1 plancha; 58.729%; merma 11.43 mm²; recuperable 48 mm². Igual a FF/BF/WF. | A | 3.266 ms |
| DJD-DIAGNOSTIC-002 | Dos selecciones individuales; no seleccionó pareja de triángulos. | 2/3; 1 plancha; 50%; merma 48 mm²; recuperable 16 mm². Igual a FF/BF/WF, incluida una pieza sin colocar. | A | 23.969 ms |
| DJD-DIAGNOSTIC-003 | Una pieza inicial y luego una terna con las tres unidades 4×4; la terna llena el área residual. | 4/4; 1 plancha; 100%; merma y recuperable 0. Igual a FF/BF/WF. | A | 2.275 ms |
| DJD-DIAGNOSTIC-004 | Cuatro selecciones individuales; usó retazo y una plancha. | 4/4; 1 retazo, 1 plancha; 65.570%; merma 6.43 mm²; recuperable 28 mm². Igual al mejor FF/BF; mejor que WF. | A | 5.578 ms |

Las categorías usan como referencia el mejor baseline lexicográfico por cobertura, planchas, aprovechamiento, merma y área recuperable. A indica empate funcional con el mejor baseline cuando se observan decisiones distintas, o empate con todos los baselines; B cambia sin mejorar; C mejora frente al mejor baseline; D pierde cobertura, usa más planchas, cae al menos 5 puntos de aprovechamiento o aumenta merma más de 5% (piso 1 mm²). El caso 003 sí seleccionó una terna con distinta decisión pero sin mejora funcional. No hubo evidencia de que la selección grupal DJD mejore FF/BF en esta matriz acotada.

## 8. Resultados Pair-Block y comparación oficial

Ejecución local en Windows/Python 3.11.15, en serie, resolución 1 mm y paso angular 5°. Las entradas oficiales, fuentes, orientaciones, margen, separación y cálculo de métricas no cambiaron. El runtime contiene generación del bloque, packing y cálculo de métricas.

| Caso | Método | Colocadas | Retazos | Planchas | Uso | Merma mm² | Recuperable mm² | Runtime ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| SMALL | FF | 3/3 | 1 | 1 | 60.000% | 0.00 | 8 | 20.095 |
| SMALL | BF | 3/3 | 1 | 1 | 60.000% | 0.00 | 8 | 20.207 |
| SMALL | WF | 3/3 | 1 | 1 | 60.000% | 0.00 | 8 | 19.458 |
| SMALL | Pair-Block | 3/3 | 1 | 1 | 60.000% | 0.00 | 8 | 23.220 |
| MEDIUM | FF | 9/9 | 2 | 1 | 28.413% | 201.86 | 58 | 31.954 |
| MEDIUM | BF | 9/9 | 2 | 1 | 28.413% | 193.86 | 66 | 47.703 |
| MEDIUM | WF | 9/9 | 2 | 2 | 18.584% | 301.86 | 150 | 30.278 |
| MEDIUM | Pair-Block | 9/9 | 2 | 1 | 28.413% | 201.86 | 58 | 291.847 |
| COMPLEX | FF | 24/24 | 3 | 3 | 29.598% | 746.72 | 184 | 169.095 |
| COMPLEX | BF | 24/24 | 3 | 3 | 29.598% | 746.72 | 184 | 166.715 |
| COMPLEX | WF | 24/24 | 3 | 4 | 25.309% | 886.72 | 268 | 161.658 |
| COMPLEX | Pair-Block | 24/24 | 3 | 3 | 29.598% | 746.72 | 184 | 2,998.492 |
| Discriminante | FF | 3/3 | 0 | 1 | 94.444% | 10.00 | 0 | 14.831 |
| Discriminante | BF | 3/3 | 0 | 1 | 94.444% | 10.00 | 0 | 14.175 |
| Discriminante | WF | 3/3 | 0 | 1 | 94.444% | 10.00 | 0 | 15.341 |
| Discriminante | Pair-Block | 3/3 | 0 | 1 | 94.444% | 10.00 | 0 | 109.618 |

Pair-Block aceptó una composición de triángulos en COMPLEX con densidad 0.7778, pero el bloque no cabía en el stock restante y las unidades pasaron al fallback individual. En SMALL y MEDIUM no hubo parejas que superaran el criterio. En el discriminante sí se colocó el bloque triangular (IDs 2 y 3, giros 0°/180°, offset interno de una celda). Su patrón sí difiere de FF: Pair-Block colocó primero el bloque y luego el rectángulo, mientras FF colocó primero el rectángulo; las métricas funcionales empataron.

El costo de generación dominó la ejecución: Pair-Block registró 260 ms de generación en MEDIUM y 2.823 s en COMPLEX, frente a 28 ms y 165 ms de packing. El runtime total fue 9.1× FF en MEDIUM y 17.7× FF en COMPLEX. En la demo fuera del benchmark fue 7.4× FF. Las tres repeticiones de Pair-Block dieron firmas idénticas en SMALL, MEDIUM, COMPLEX y discriminante; solo cambió runtime.

## 9. Evidencia previa preservada

- Filler y descarte: [investigación archivada](SP-004-filler-candidato-descartado.md), [resultados crudos](../evidence/sprint-02/SP-004/benchmark-results/sp004_filler_descartado_results.csv).
- DJD oficial y NO-GO anterior: [investigación DJD](SP-004-djd.md), [evidencia acumulada](../evidence/sprint-02/SP-004/README.md).
- Intenciones y casos DJD nuevos: [manifiesto](../../experiments/optimization/djd/DJD-DIAGNOSTIC-INTENT.md), JSON `DJD-DIAGNOSTIC-001` a `004`.
- Resultados Pair-Block: [CSV](../evidence/sprint-02/SP-004/benchmark-results/sp004_block_results.csv), [traza](../evidence/sprint-02/SP-004/benchmark-results/sp004_block_trace.json).
- Resultados DJD adicional: [CSV](../evidence/sprint-02/SP-004/benchmark-results/sp004_djd_diagnostic_results.csv), [traza y categorías](../evidence/sprint-02/SP-004/benchmark-results/sp004_djd_diagnostic_trace.json).
- Notebook ejecutado: [SP004-Block-Packing.ipynb](../../experiments/optimization/colab/SP004-Block-Packing.ipynb).

## Evaluación comparativa y selección de candidato M4

| Candidato | Diferencia demostrada | Costo y resultado | Decisión para TA-042 |
|---|---|---|---|
| Filler | Progresión por fuente activa, pero FF real ya ordena por área; resultados oficiales prácticamente iguales a FF. | Runtime cercano a FF; no aporta cambio estable de métricas. | **NO-GO**, descartado como principal. |
| DJD-1/3 | Selecciona grupos de 1/2/3; la terna se observó en COMPLEX previo y en el diagnóstico 003. | En TA-027 no cambió métricas y llegó a 7.69 s en COMPLEX; los cuatro diagnósticos nuevos no superaron al mejor baseline. | **NO-GO**, diferencia conceptual real sin beneficio medido. |
| Pair-Block | Cambia el patrón en la demo; conserva las piezas. Ningún bloque llegó a colocarse en TA-027. | 9.1×–17.7× FF en MEDIUM/COMPLEX; métricas oficiales iguales a FF, con una propuesta de bloque que falló al colocar. | **NO-GO por ahora**; mecanismo válido, rendimiento/beneficio insuficientes. |

La recomendación es **no integrar una heurística M4 en TA-042 con la evidencia actual**. Pair-Block es el mecanismo más alineado con las formas complementarias y queda como posible siguiente investigación, pero antes requiere reducir el costo de generación y lograr bloques colocados en instancias operativas con mejoras o beneficios claros en fuentes/merma/recuperable. Filler y DJD quedan archivados como candidatos revisados. No se modificó producción ni TA-027.
