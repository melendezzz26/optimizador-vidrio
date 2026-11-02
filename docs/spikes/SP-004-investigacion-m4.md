# SP-004 — Investigación y experimentación de heurística adicional M4

## Estado vigente — Raster Hole Filling / Pocket Filling

Filler, DJD-1/3 y Pair-Block v1/v2 son antecedentes **NO-GO para TA-042**; no se borran sus resultados, notebooks, pruebas ni commits. Hole Filling es el candidato actual de SP-004 y comienza como mini-spike local. No hay cambios de producción, fixtures TA-027, API, frontend ni BD; no se hace push, PR o merge.

La investigación publicada verifica hole filling con huecos cerrados representados como polígonos e IFP para decidir encaje. Abeysooriya et al. (2018) ordenan los huecos por x mínima y prueban hole filling antes del placement normal; Błażewicz et al. (1993) son antecedente de backfilling con búsqueda tabu, y Burke et al. (2006) documentan la dificultad de validar movimientos de backfilling. Esto no define un detector raster llamado “Raster Hole Filling”: la adaptación local queda separada y etiquetada como experimental. Fuentes y atribución completas están en [SPEC-SP-004](../specs/SPEC-SP-004-heuristica-m4.md).

### Definición de regiones en la adaptación local

- **Hueco interno físico:** componente 4-conexo de celdas libres de la máscara del material que no toca el exterior de esa máscara.
- **Pocket utilizable por una pieza/orientación:** componente 4-conexa de anclajes aceptados por `SheetLayout.check()` que no conecta con el borde del dominio de anclajes. Una abertura que no admite la huella bajo margen/separación no conecta con el pocket. Se registra cantidad y área de anclajes por separado del área física.
- La inspección reutilizará `RasterMask`, `SheetLayout.check/place`, `RasterCache`, el paso angular de 5° y la distinción `REMANENT`/`SHEET`. El estado se copia mediante layouts inmutables; no hay rasterizador o validador geométrico nuevo.
- La política será pocket-first: ordenar las regiones por posición, intentar una pieza pendiente con orientación permitida y anclaje legal, y usar FF como fallback. Es una regla local determinista inspirada en la secuencia publicada de probar huecos antes del placement normal; no copia IFP ni introduce un score BRF.

La auditoría, definición y fuentes verificables están en la SPEC. El siguiente hito es fijar y commitear hasta cuatro diagnósticos antes de ejecutar comparaciones. EXP-SMALL/MEDIUM/COMPLEX solo se ejecutan si el mini-spike supera su puerta de viabilidad.

## Antecedente histórico — Pair-Block v2

Pair-Block v1/v2 y DJD se conservan en las secciones históricas siguientes. Pair-Block v2 terminó con NO-GO; su evidencia está en `docs/evidence/sprint-02/SP-004/README.md`. Esta investigación anterior no representa el candidato vigente.

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

## Evaluación comparativa y selección de candidato M4 - pendiente de v2

| Candidato | Diferencia demostrada | Costo y resultado | Decisión para TA-042 |
|---|---|---|---|
| Filler | Progresión por fuente activa, pero FF real ya ordena por área; resultados oficiales prácticamente iguales a FF. | Runtime cercano a FF; no aporta cambio estable de métricas. | **NO-GO**, descartado como principal. |
| DJD-1/3 | Selecciona grupos de 1/2/3; la terna se observó en COMPLEX previo y en el diagnóstico 003. | En TA-027 no cambió métricas y llegó a 7.69 s en COMPLEX; los cuatro diagnósticos nuevos no superaron al mejor baseline. | **NO-GO**, diferencia conceptual real sin beneficio medido. |
| Pair-Block | Cambia el patrón en la demo; conserva las piezas. Ningún bloque llegó a colocarse en TA-027. | 9.1×–17.7× FF en MEDIUM/COMPLEX; métricas oficiales iguales a FF, con una propuesta de bloque que falló al colocar. | **Pendiente de dictamen v2**; los resultados v1 no bastan para decidir con la grilla completa. |

El dictamen de TA-042 para Filler y DJD permanece NO-GO. Para Pair-Block queda pendiente completar v2 con la grilla real de 5 grados, pruning medible y nuevos resultados. No se modifica producción ni TA-027.


## Resultado mini-spike Raster Hole Filling / Pocket Filling

El candidato vigente se investigo como experimento aislado. Se conservaron Filler (NO-GO), DJD-1/3 (NO-GO provisional/descartado) y Pair-Block v1/v2 (NO-GO) como evidencia previa. El detector local es una adaptacion raster de NewGlass; no se atribuye a la literatura como algoritmo publicado. La investigacion verificable, la auditoria de `RasterMask`/`SheetLayout` y la definicion de hueco fisico frente a pocket de placement estan en la [SPEC vigente](../specs/SPEC-SP-004-heuristica-m4.md).

### Diagnosticos predeclarados

Los cuatro casos se congelaron en JSON antes de comparar FF/BF/WF/Hole Filling. Todos estan rotulados `DIAGNOSTICO HOLE FILLING - NO PERTENECE A TA-027`. Ninguno formo un hueco fisico cerrado: el espacio libre seguia conectado al exterior. Los casos 001-003 si crearon componentes interiores en el mapa de anclajes legales de la pieza/orientacion, que es la definicion computable de pocket usada aqui.

| Caso | Clasificacion | Pocket y decision HF | Comparacion funcional | HF ms / baseline mas rapido |
|---|:---:|---|---|---:|
| HF-DIAGNOSTIC-001, circulo y marco abierto | B | 3 componentes; coloco rectangulo 1x1 en (7,5), retazo 901, 0 grados. | Cambio patron; 7/7, merma/uso/recuperable iguales al mejor baseline. | 14.09 / 4.60x |
| HF-DIAGNOSTIC-002, triangulos | B | 12 componentes; coloco triangulo 2x2 en (5,13), plancha 902, 0 grados. | Cambio patron; 5/5, metricas funcionales iguales al mejor baseline. | 21.68 / 5.85x |
| HF-DIAGNOSTIC-003, poligono convexo | B | 3 componentes; coloco rectangulo 1x1 en (7,5), plancha 903, 0 grados. | Cambio patron; 7/7, metricas funcionales iguales al mejor baseline. | 13.46 / 3.85x |
| HF-DIAGNOSTIC-004, control negativo | A | 0 componentes; no forzo pocket y uso fallback FF hacia plancha para la pieza 6x6 que no cabia en retazo. | Mismo placement y metricas que FF. | 13.13 / 1.08x |

**Que ocurrio con el circulo:** si produjo un pocket aprovechable para la pieza pendiente, aunque no creo un agujero fisico cerrado. El bolsillo existe para el rectangulo 1x1 porque en el mapa de origenes legales su componente no conecta con el borde. La misma distincion aplica a triangulos y al poligono convexo; el control no fue clasificado como pocket.

### Rendimiento y determinismo

La busqueda inspecciono 839, 8,532, 839 y 19 origenes de anclaje respectivamente. Las corridas fueron seriales, sin multiprocessing; el pico de RAM no se instrumento. La deteccion pocket costo 0.89, 7.22, 0.59 y 0.02 ms; la busqueda de placement, 9.43, 11.07, 9.31 y 11.25 ms. En cada caso las tres repeticiones HF conservaron los mismos placements y decisiones. El maximo ratio de tiempo fue 5.85x, por debajo del umbral predeclarado de 10x. El mini-spike queda **VIABLE** para habilitar el benchmark formal.

### Benchmark EXP condicionado por VIABLE

Los tres fixtures existentes se leyeron sin modificaciones. HF se comparo con FF/BF/WF y se repitio tres veces por fixture. No se uso ningun pocket en estos casos.

| Fixture | Clase HF | Colocadas | Planchas | Uso | Merma mm2 | Recuperable mm2 | HF ms | Ratio |
|---|:---:|---:|---:|---:|---:|---:|---:|---:|
| EXP-SMALL-001 | A | 3/3 | 1 | 60.000% | 0.00 | 8 | 12.57 | 1.15x |
| EXP-MEDIUM-001 | D | 9/9 | 1 | 28.413% | 201.86 | 58 | 87.53 | 4.92x |
| EXP-COMPLEX-001 | E | 24/24 | 3 | 29.598% | 746.72 | 184 | 1,325.45 | 14.83x |

SMALL empata con FF. MEDIUM reproduce FF y BF es mejor por 8 mm2 de merma y 8 mm2 de area recuperable. COMPLEX reproduce FF, no aprovecha pocket y tarda 14.83x el baseline mas rapido. La recomendacion para integrar HF en TA-042 es **NO-GO**. El resultado distingue mecanismo viable en diagnosticos de aplicabilidad insuficiente y costo alto en estos fixtures oficiales.

### Diferencias de decision

- **FF/BF/WF:** eligen como continuar colocando la pieza actual segun orden, menor sobrante o mayor sobrante de la fuente examinada. Hole Filling busca primero una pieza pendiente para una region que ya existe; si no encuentra una, vuelve a FF.
- **BRF:** califica el sobrante hipotetico de un placement candidato. HF no optimiza `largest_rectangle`, no reutiliza un score BRF y no busca minimizar merma.
- **Metodos publicados:** la literatura revisada conserva huecos geometricos como poligonos y usa IFP/backfilling para comprobar encajes. El mapa raster de anclajes 4-conexo y su politica pocket-first son una adaptacion experimental local.

### Pruebas y evidencia

Las 11 pruebas HF cubren componentes y exterior, circulo, triangulos, convexo, control, material/espesor, margen, separacion, no solapamiento, rotacion del motor a 5 grados, determinismo, no mutacion y fallback. Las regresiones enfocadas de FF/BF/WF, placement y angulos tuvieron 145 pruebas PASS. No se cambio produccion, TA-027, API, frontend, BD, ni FF/BF/WF.

- [Manifiesto y casos congelados](../../experiments/optimization/hole_filling/)
- [CSV y traza diagnosticos](../evidence/sprint-02/SP-004/hole-filling/sp004_hole_filling_results.csv) / [JSON completo](../evidence/sprint-02/SP-004/hole-filling/sp004_hole_filling_trace.json)
- [Deteccion y tiempos](../evidence/sprint-02/SP-004/hole-filling/sp004_hole_filling_detection.json)
- [CSV y traza EXP oficial](../evidence/sprint-02/SP-004/hole-filling/sp004_hole_filling_official_results.csv) / [JSON completo](../evidence/sprint-02/SP-004/hole-filling/sp004_hole_filling_official_trace.json)
- [Notebook ejecutado con outputs locales](../../experiments/optimization/colab/SP004-Hole-Filling.ipynb)
- [Evidencia acumulada de SP-004](../evidence/sprint-02/SP-004/README.md)

Trabajo local en `spike/S2-SP004-djd`: sin push, PR ni merge.

## Validación final de Hole Filling con pedidos realistas

Se completó el gate solicitado con tres pedidos sintéticos congelados antes del benchmark en `fda6d12`, cada fixture registrado por SHA-256 en [la intención predeclarada](../../experiments/optimization/hole_filling/cases/HF-REALISTIC-INTENT.md). Se ejecutaron FF, BF, WF y HF en serie con raster 1 mm, giros de 5°, margen 5 mm, separación 3 mm, material/espesor comunes y retazo antes de plancha. HF tuvo tres repeticiones por pedido.

| Caso | FF/BF/WF | Hole Filling | Lectura funcional / costo |
|---|---|---|---|
| 001, círculos y piezas pequeñas (15) | 15/15; 1 retazo + 1 plancha; 65.745%; merma 49,908.91 mm²; recuperable 18,738 mm² | Mismas métricas; 0 pockets usados; 96,383 ms (270.88×) | A funcional / E por costo |
| 002, triángulos y convexos (18) | 18/18; 1 + 1; 43.490%; merma 57,164 mm²; recuperable 66,536 mm² | Pieza 5 en pocket a 255°, (283, 41); métricas iguales; 236,795 ms (136.02×) | B funcional / E por costo |
| 003, mezcla heterogénea (20) | 20/20; 1 + 1; 74.329%; merma 60,627.26 mm²; recuperable 14,948 mm² | Seis placements pocket, 19/20; 71.101%; merma 77,120.58 mm²; recuperable 7,958 mm²; 238,463 ms (424.65×) | D funcional / E por costo |

Los contadores fueron 0/11/70 componentes de anclajes detectados y 0/1/6 pockets usados para 001/002/003. Las tres firmas funcionales se repitieron en los tres runs de cada caso. El costo dominante fue generar el mapa raster de anclajes (medianas 91.68 s, 226.46 s y 231.31 s); el etiquetado de componentes tomó 3.11 s, 5.53 s y 4.84 s. Las cifras completas, runtimes individuales, placements, fuentes, rotaciones y figuras están en [CSV](../evidence/sprint-02/SP-004/hole-filling/sp004_hf_realistic_results.csv), [JSON](../evidence/sprint-02/SP-004/hole-filling/sp004_hf_realistic_trace.json) y [notebook](../../experiments/optimization/colab/SP004-Hole-Filling.ipynb). Solo se generaron figuras para 002 y 003, que usaron pockets.

**Decisión final para TA-042: NO-GO.** HF altera patrones en 002/003, pero en 002 solo empata métricas a 136×; en 003 pierde cobertura y empeora las métricas funcionales a 425×; en 001 equivale al baseline sin pocket a 271×. El resultado no cumple el criterio de utilidad funcional y costo aceptable. Determinismo: PASS ×3 por fixture. Pruebas actuales: 13 de laboratorio HF y 145 regresiones enfocadas, todas PASS. La evidencia detallada está en el [README de SP-004](../evidence/sprint-02/SP-004/README.md). No hubo cambios de producción ni TA-027, push, PR o merge.

## Experimento demostrativo de capacidad

> **CASO CONTROLADO DISEÑADO PARA MOSTRAR LA CLASE DE PEDIDO EN LA QUE HOLE FILLING PUEDE SER ÚTIL. NO REPRESENTA RENDIMIENTO GENERAL.**

La **evaluación general** sigue compuesta por TA-027/EXP y los tres HF-REALISTIC, con recomendación **NO-GO para TA-042**. HF-CAPABILITY-001 es una **prueba dirigida de capacidad** que muestra un mecanismo posible, sin cambiar esas conclusiones.

Se diseñó un trabajo ya iniciado en un retazo 274 × 280 mm con dieciséis piezas previas validadas, entre ellas un círculo y paneles. Quedaron pendientes el inserto P11 de 32 × 32 mm y el círculo P12 de Ø36 mm; una plancha de igual tamaño estaba disponible. Se mantuvieron raster 1 mm, giros cada 5°, margen 5 mm, separación 3 mm, material y espesor comunes y prioridad retazo → plancha. La [intención](../../experiments/optimization/hole_filling/cases/HF-CAPABILITY-INTENT.md) documenta la hipótesis, sus cambios durante el diseño y la búsqueda dirigida; el [registro](../../experiments/optimization/hole_filling/cases/HF-CAPABILITY-SEARCH.jsonl) contiene 20 candidatos. Se congeló el primero que cumplió los criterios, `f806a27`, antes de comparar definitivamente los cuatro métodos.

| Método | P11 | P12 | Colocadas | Retazos / planchas | Uso | Merma mm² | Recuperable mm² | Tiempo ms |
|---|---|---|---:|---:|---:|---:|---:|---:|
| FF | Exterior, retazo (5, 5) | Plancha (5, 5) | 18/18 | 1 / 1 | 33.787% | 37,516.56 | 64,080 | 63.05 |
| BF | Exterior, retazo (5, 5) | Plancha (5, 5) | 18/18 | 1 / 1 | 33.787% | 37,516.56 | 64,080 | 62.32 |
| WF | Exterior, retazo (5, 5) | Plancha (5, 5) | 18/18 | 1 / 1 | 33.787% | 37,516.56 | 64,080 | 62.81 |
| HF | Pocket, retazo (51, 191) | Retazo (5, 5) | 18/18 | 1 / 0 | 67.575% | 22,410.56 | 2,466 | 262.99 |

HF detectó siete componentes de anclajes y usó uno para P11 a 0°; P12 entró después mediante fallback en la franja exterior preservada. El pocket utilizado apareció abajo a la izquierda del marco, no en la cavidad superior imaginada al inicio. La prueba alcanzó el nivel 1 declarado: una plancha menos. También aumentó la utilización y redujo la merma, mientras el área recuperable registrada fue menor y HF tardó 4.22× el baseline más rápido. Las tres repeticiones HF conservaron pocket, piezas, giros, posiciones y métricas: **PASS**.

La [comparación visual](../../experiments/optimization/hole_filling/figures/HF-CAPABILITY-001-comparison.svg) y la [vista del pocket](../../experiments/optimization/hole_filling/figures/HF-CAPABILITY-001-pocket-stage.svg) se generaron con placements reales. [CSV](../evidence/sprint-02/SP-004/hole-filling/sp004_hf_capability_results.csv), [traza](../evidence/sprint-02/SP-004/hole-filling/sp004_hf_capability_trace.json) y [notebook ejecutable](../../experiments/optimization/colab/SP004-Hole-Filling.ipynb) permiten revisarlo.

**Interpretación acotada:** Hole Filling puede reservar espacio útil cuando hay geometrías que producen pockets legales, mezcla de tamaños y piezas pequeñas pendientes. Para TA-042 solo se recomienda investigar un filtro barato de activación por presencia de círculos/convexos, densidad y pockets detectados; no se integra lógica productiva con esta prueba. El NO-GO de la evaluación general permanece.

## Estado de continuidad M4

**M4 seleccionado para continuar: Raster Hole Filling / Pocket Filling, con GO condicionado para estudiar una implementación optimizada en TA-042.** Su oportunidad es especializada: pedidos donde se detecta un pocket legal antes de colocar una pieza pequeña. El caso HF-CAPABILITY-001 demuestra esa posibilidad en condiciones controladas, sin probar mejora general. Se mantienen los NO-GO y las mediciones negativas de la implementación experimental exhaustiva; TA-042 deberá evaluar activación con filtros baratos, límite de costo y fallback a FF antes de cualquier integración, sin copiarla directamente a producción.
