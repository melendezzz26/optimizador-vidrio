# SP-004 — Investigación y experimentación de Djang and Finch (DJD)

## 1. Contexto

NewGlass estudia una cuarta política de selección sin incluirla en producción. La exploración previa de Filler (FL) queda conservada, pero se descarta como candidato principal: la auditoría encontró que el FF real ya ordena piezas por área decreciente y los tres fixtures produjeron resultados casi idénticos para ambos. El nuevo candidato es Djang and Finch adaptado al bin packing irregular 2D, con llenado inicial DJD-1/3.

La diferencia investigada es que DJD puede evaluar conjuntamente una, dos o tres piezas pendientes antes de decidir cómo continuar en la fuente activa. La suma de áreas solo da una condición necesaria; la geometría real determina si la secuencia puede colocarse.

## 2. Alternativas estudiadas

NewGlass compara FF, BF y WF. Filler se evaluó como política de llenado de una fuente con búsqueda de piezas pendientes, pero comparte con el FF local el orden decreciente de área. Su registro permanece en `SP-004-filler-candidato-descartado.md` y en la evidencia Filler etiquetada como descartada.

## 3. Filler y motivo de descarte

Filler y FF colocaron las mismas unidades y consumieron el mismo número de fuentes en SMALL, MEDIUM y COMPLEX. Coincidieron además en aprovechamiento. Filler mostró algunas diferencias de traza y mayor número de intentos, pero no reveló un eje de selección suficientemente distinto en TA-027. La decisión descarta Filler como candidato principal de M4; no borra su investigación ni implica que sea equivalente en todas las instancias.

## 4. Djang and Finch

El DJD original para bin packing unidimensional toma piezas en orden decreciente y llena un contenedor hasta al menos un tercio. Luego intenta hallar grupos de una, dos o tres piezas que llenen exactamente el espacio restante; si no lo logra, relaja progresivamente el desperdicio permitido: primero una unidad, después dos y así sucesivamente. DJT es una variación que considera combinaciones de hasta cinco elementos, más costosa.

La adaptación de López-Camacho et al. a 2D irregular mantiene DJD como heurística de selección y requiere una heurística de placement separada. En 2D, probar que el área sumada cabe no demuestra que las formas puedan acomodarse. El artículo enumera órdenes de piezas dentro del grupo y prueba la colocación secuencial, porque un mismo conjunto puede ser factible en un orden y no en otro.

## 5. Adaptación de DJD a 2D irregular

La adaptación primaria hace un llenado inicial por área decreciente hasta cubrir al menos un tercio del área nominal total del objeto. Luego busca singles, pares y ternas con residuos dentro de la tolerancia `w`. `w` inicia en cero. Si no hay grupo admisible y `w` aún es menor que el área nominal residual, se incrementa. Los grupos geométricos exitosos se colocan secuencialmente; si un miembro falla, el trial se descarta y no se muta el estado activo.

López-Camacho et al. describen el incremento 1/20 del área total del objeto como una elección empírica que balancea tiempo y calidad. Este Spike implementa literalmente `delta_w = stock.area_mm2 / 20`; también usa el área nominal total para el umbral 1/3. En su experimento prueban llenados iniciales 1/4, 1/3, 1/2 y 2/3: 1/4 se comporta mejor con BL y CA en sus datos; 1/3 logra los mejores promedios con CA, CAA y CAD; 1/2 y 2/3 son útiles en otras clases de instancia, en particular instancias rectangulares. Por ello este Spike fija 1/3, no afirma que sea universalmente óptimo.

## 6. Diferencia frente a FF/BF/WF reales

FF real de NewGlass fija la siguiente unidad —su orden común ya usa área decreciente— y acepta la primera fuente, orientación y posición row-major factible. BF compara fuentes para esa unidad por menor cantidad de celdas libres posterior; WF prefiere la de mayor cantidad. Ambos mantienen el orden de piezas de FF y la prioridad retazo antes que plancha. Ninguno de esos selectores propone un conjunto de piezas a colocar conjuntamente.

DJD también comienza con una fase de singles similar a un recorrido FF, pero después de alcanzar el umbral plantea elecciones explícitas de tamaño 1, 2 y 3. Puede seleccionar un par cuya suma de área se aproxime mejor a la capacidad restante aunque el chequeo individual actual no sea admisible bajo la misma tolerancia. La solución final aún depende de la primera colocación geométrica canónica de NewGlass; DJD no crea un nuevo solver geométrico.

## 7. Variante DJD-1/3

Se fija el nivel inicial `1/3`. La tolerancia se inicia en `w = 0`; el paso publicado por el artículo es `Δw = área_objeto / 20`, y se implementa como `stock.area_mm2 / 20`. El residual nominal (`stock.area_mm2 - áreas_oficiales_colocadas`) poda combinaciones imposibles; el layout raster decide cabida real con el margen, la separación y el contorno del material. Así, el uso del área nominal no sustituye ni relaja los controles geométricos.

En cada estado se generan perezosamente subconjuntos deterministas de tamaño 1, 2 y 3 en orden de área/ID; sus permutaciones se revisan en orden estable. La suma oficial de áreas descarta grupos mayores que el residual nominal y grupos cuyo residuo estimado exceda `w`. El grupo restante se prueba elemento por elemento sobre layouts temporales inmutables. Solo se conserva el layout posterior si el grupo entero cabe. Una colocación aceptada reinicia `w` a cero y el intento continúa en la fuente activa.

## 8. Adaptación a NewGlass

La unidad seleccionada y el stock pertenecen al mismo grupo `(glass_type_id, thickness_mm)`. Los stocks compatibles se recorren con prioridad retazo→plancha y desempate estable por identidad. La poda compara áreas oficiales de piezas contra el residual nominal de la fuente. Margen, separación, raster, geometrías, rotación de 5°, máscaras, colisión y métricas se delegan a los imports existentes.

`SheetLayout` es inmutable: cada trial usa `candidate.layout_after` y asigna el resultado a una referencia local. Una secuencia incompleta no reemplaza el layout activo. El cache experimental registra órdenes geométricas fallidas solo mientras el layout no cambia; tras aceptar un grupo se limpia para permitir combinaciones que pudieran volverse factibles.

## 9. Figuras

El ejemplo conceptual de fuente y grupos de 1/2/3 piezas está en `assets/SP-004-djd-example.png`. Está etiquetado como figura conceptual y no muestra un resultado de benchmark. La demo JSON discriminante separada tampoco forma parte de TA-027.

## 10. Protocolo experimental

Se ejecutan FF, BF, WF y DJD-1/3 secuencialmente con EXP-SMALL-001, EXP-MEDIUM-001 y EXP-COMPLEX-001 originales. Como demostración adicional se usa `DJD-DISCRIMINANT-001`, marcado como caso de discriminación y no como fixture oficial. Se conserva resolución 1 mm, paso de rotación 5°, configuración, stock, compatibilidad, separación y métricas oficiales.

El costo se observa en tres niveles: subconjuntos de tamaños 1/2/3 visitados; subconjuntos podados por área o residuo antes de geometría; y secuencias ordenadas que requieren validaciones geométricas. También se registran placements de pieza, chequeos por miembro, secuencias geométricamente factibles, cache hits y pasos de `w`. Las combinaciones se consumen como iteradores, no se guardan todas en memoria.

## 11. Resultados

Los resultados ejecutados y las trazas se guardan en `docs/evidence/sprint-02/SP-004/benchmark-results/sp004_djd_results.csv` y `sp004_djd_trace.json`. FF, BF, WF y DJD colocaron todas las unidades en los tres fixtures oficiales. SMALL coincide en cobertura, stock, aprovechamiento y merma. MEDIUM y COMPLEX dejan a DJD con las mismas métricas de FF; BF reduce la merma MEDIUM en 8 mm². WF usa una plancha adicional en MEDIUM y COMPLEX.

| Caso | Método | Colocadas | Retazos | Planchas | Aprovechamiento | Merma (mm²) | Tiempo (ms) |
|---|---|---:|---:|---:|---:|---:|---:|
| SMALL | FF | 3/3 | 1 | 1 | 60.000% | 0.00 | 20.495 |
| SMALL | BF | 3/3 | 1 | 1 | 60.000% | 0.00 | 19.392 |
| SMALL | WF | 3/3 | 1 | 1 | 60.000% | 0.00 | 17.958 |
| SMALL | DJD-1/3 | 3/3 | 1 | 1 | 60.000% | 0.00 | 2.411 |
| MEDIUM | FF | 9/9 | 2 | 1 | 28.413% | 201.86 | 30.501 |
| MEDIUM | BF | 9/9 | 2 | 1 | 28.413% | 193.86 | 44.089 |
| MEDIUM | WF | 9/9 | 2 | 2 | 18.584% | 301.86 | 29.752 |
| MEDIUM | DJD-1/3 | 9/9 | 2 | 1 | 28.413% | 201.86 | 267.294 |
| COMPLEX | FF | 24/24 | 3 | 3 | 29.598% | 746.72 | 154.009 |
| COMPLEX | BF | 24/24 | 3 | 3 | 29.598% | 746.72 | 168.081 |
| COMPLEX | WF | 24/24 | 3 | 4 | 25.309% | 886.72 | 159.980 |
| COMPLEX | DJD-1/3 | 24/24 | 3 | 3 | 29.598% | 746.72 | 7,693.620 |

DJD sí presenta decisiones operacionales distintas: eligió una terna durante COMPLEX y no se limitó a singles. Sin embargo, su resultado final iguala FF en unidades, fuentes, aprovechamiento y merma, a un costo de 7.694 s, aproximadamente 50 veces los 154 ms de FF en esta corrida. MEDIUM tarda 267 ms frente a 31 ms de FF, también sin cambio de resultado final.

| Caso DJD | Generadas tamaño 1/2/3 | Podadas por área/residuo | Secuencias geométricas | Omitidas por cache | Checks por pieza | Factibles | Pasos `w` | Selección |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| SMALL | 3 / 0 / 0 | 0 | 0 | 0 | 3 | 0 | 0 | 1, 1, 1 |
| MEDIUM | 214 / 471 / 634 | 983 | 397 | 996 | 582 | 1 | 35 | solo singles |
| COMPLEX | 791 / 4,409 / 18,493 | 13,813 | 7,527 | 45,571 | 7,587 | 1 | 68 | una terna, resto singles |

Los contadores de subconjuntos registran intentos de singleton durante el llenado inicial y visitas durante los pasos de tolerancia; pueden volver a contar el mismo subconjunto en otra iteración. Las permutaciones fallidas se cachean mientras el layout no cambia. `feasible_combinations` cuenta secuencias que pasan íntegramente y se aceptan; la búsqueda se detiene en la primera secuencia válida de cada decisión. Eso permite interpretar el costo de las validaciones geométricas sin almacenar la expansión completa.

El caso discriminante no forma parte de TA-027. Los cuatro métodos colocaron 3/3 con una plancha, 95.000% de aprovechamiento y 0 mm² de merma. DJD seleccionó singles durante el llenado inicial y después el par `[2, 3]`, que dejaba residuo nominal 5 mm² dentro de `w = 5 mm²` al primer incremento (`100 / 20`). Es una diferencia de decisión, no una mejora de rendimiento.

El notebook ejecutado repitió DJD tres veces por fixture: SMALL, MEDIUM y COMPLEX dieron firma idéntica de placements y decisiones en las tres corridas. La duración se excluye de la firma. La suite aislada de DJD y las regresiones unitarias FF/BF/WF finalizaron con 93 pruebas aprobadas.

## 12. Limitaciones

- Los fixtures TA-027 son solo tres instancias y no representan la distribución completa de pedidos.
- La suma de áreas es un pruning necesario, no suficiente; la geometría rasterizada puede descartar una secuencia.
- La poda por área nominal puede dejar pasar combinaciones que luego fallen por margen, separación, forma irregular o discretización; la validación geométrica las rechaza sin mutar la fuente.
- Enumerar permutaciones hace crecer el costo aproximadamente con grupos de hasta tres elementos y el número de pasos de tolerancia.
- Los artículos prueban variantes junto a placement BL/CA/CAA/CAD, no con el motor raster de NewGlass; sus métricas no son directamente comparables.
- El caso discriminante demuestra una decisión de agrupación, no evidencia de mejora de rendimiento.

## 13. Evaluación de viabilidad

La recomendación es **NO-GO para avanzar esta implementación a TA-042**. La búsqueda es operativamente distinta, determinista, respeta la geometría y reglas compartidas y no duplica el motor productivo; sin embargo, en MEDIUM y COMPLEX su resultado final no mejora a FF y el tiempo crece aproximadamente 9× y 50×, respectivamente. En COMPLEX se validaron 7,527 órdenes geométricas distintas y 7,587 placements de miembros, lo que expone el costo de enumerar parejas/ternas y sus órdenes. El costo observado no justifica integrar el algoritmo sin antes investigar una poda que preserve la selección y los mismos resultados.

Esta decisión no invalida la hipótesis DJD ni el caso discriminante; detiene la propuesta de producción con el diseño medido. La evidencia no incluye pedidos reales ni un SLA objetivo de optimización, por lo que una futura variante con límites de búsqueda y perfiles de producción requeriría una evaluación nueva.

## 14. Referencias

1. Ross, P., Schulenburg, S., Marín-Blázquez, J. G. y Hart, E. (2002). “Hyper-heuristics: learning to combine simple heuristics in bin-packing problems.” *Proceedings of GECCO 2002*, 942–948. Fuente del DJD 1D descrito por la adaptación. [PDF del artículo](https://gpbib.cs.ucl.ac.uk/gecco2002/LCS260.pdf); [registro institucional](https://napier-repository.worktribe.com/output/270070).
2. López-Camacho, E., Ochoa, G., Terashima-Marín, H. y Burke, E. (2013). “An effective heuristic for the two-dimensional irregular bin packing problem.” *Annals of Operations Research*, 206, 241–264. DOI: [10.1007/s10479-013-1341-4](https://doi.org/10.1007/s10479-013-1341-4). [PDF académico](https://www.cs.stir.ac.uk/~goc/papers/EffectiveHueristic2DAOR2013.pdf).
3. López-Camacho, E., Ochoa, G., Terashima-Marín, H. y Burke, E. (2014). “A unified hyper-heuristic framework for solving bin packing problems.” *Expert Systems with Applications*, 41, 6876–6889. [PDF académico](https://citeseerx.ist.psu.edu/document?doi=d6247d95266323b415fbd12f23312f97efb83466&repid=rep1&type=pdf). Resume comparación de niveles iniciales DJD 1/4, 1/3 y 1/2.
