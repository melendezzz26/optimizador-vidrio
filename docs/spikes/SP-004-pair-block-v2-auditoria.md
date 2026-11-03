# SP-004 — Auditoría previa a Pair-Block v2

## Alcance y orden

Esta auditoría se registró antes de cambiar el código experimental. La decisión NO-GO que acompañó Pair-Block v1 queda aplazada para Pair-Block; los resultados de Filler y DJD no cambian. Esta revisión no modifica el motor, los fixtures oficiales ni TA-027.

## Por qué v1 limitó las rotaciones

Pair-Block v1 consultaba solo 0°, 90°, 180° y 270° para reducir el costo inicial de explorar pares. Fue una simplificación del laboratorio, no una restricción deducida del artículo ni una limitación del contrato de NewGlass. Aunque esos cuatro ángulos pertenecen a la grilla de 5°, solo cubren cuatro de sus 72 ángulos.

Además, v1 eliminaba orientaciones comparando solo el ancho y el alto de la máscara. Eso podía descartar polígonos rastermente diferentes con el mismo bounding box: por ejemplo, 0° y 180° pueden tener idénticas dimensiones y ocupar celdas distintas. Por tanto, la cobertura real de v1 fue menor que la de una búsqueda cardinal completa.

La referencia de Cai et al. estudia rotaciones permitidas por conjuntos discretos y describe bloques de dos o más piezas complementarias para mejorar la utilización local. No prescribe que los bloques se limiten a giros cardinales. El artículo combina los bloques con espacios residuales y líneas de referencia para guiar la selección/colocación, y con operaciones de mejora y repacking. La regla cardinal de v1 no procede de ese método. [Ficha editorial del artículo](https://www.sciencedirect.com/science/article/pii/S0305054823002629) · [DOI 10.1016/j.cor.2023.106398](https://doi.org/10.1016/j.cor.2023.106398).

## Efecto de omitir ángulos

- **Rectángulos:** los giros cardinales solo producen sus dos ejes principales; los otros 68 ángulos convierten la huella raster en un polígono orientado. Estos pueden descubrir ajustes diagonales o complementar esquinas, aunque también pueden aumentar el bounding box.
- **Círculos:** la máscara es invariante a la rotación. No se pierde una forma distinta al conservar un solo representante.
- **Polígonos convexos:** los ángulos intermedios cambian las aristas que se enfrentan y pueden permitir una composición más regular. La deduplicación de v1 por dimensiones también podía borrar máscaras distintas entre giros cardinales.

## Magnitud de la búsqueda omitida

NewGlass configura 72 ángulos: 0°, 5°, …, 355°. En una pareja sin simetrías, la matriz cruda contiene 72 × 72 = 5,184 combinaciones de orientación, antes de probar offsets. Para estimar el alcance de la reducción de v1 se enumeraron las máscaras con el rasterizador vigente, sin cambiar archivos. Se deduplicaron máscaras solo para esta estimación mediante dimensiones y filas de bits idénticas.

| Caso | Pares compatibles | Pares de orientaciones v1 según su deduplicación por bounding box | Pares de máscaras v2 después de equivalencias raster exactas | Teórico crudo 72 × 72 por pareja |
|---|---:|---:|---:|---:|
| SMALL | 3 | 3 | 12 | 15,552 |
| MEDIUM | 36 | 113 | 7,513 | 186,624 |
| COMPLEX | 181 | 586 | 156,856 | 938,304 |
| BLOCK-DISCRIMINANT-001 | 3 | 5 | 10,080 | 15,552 |
| **Total** | **223** | **707** | **174,461** | **1,156,032** |

Las 174,461 combinaciones exactas equivalentes son un techo previo al pruning geométrico; no representan 174,461 composiciones útiles ni chequeos costosos ya realizados. Respecto a lo que la implementación v1 enumeró, quedan 173,754 combinaciones de máscara-orientación adicionales como máximo teórico en esta matriz. En el caso oficial COMPLEX, la grilla completa eleva la matriz de 586 combinaciones v1 a 156,856 combinaciones únicas por máscara antes de filtrar. Se requiere pruning determinista y contadores separados para no convertir este crecimiento en una búsqueda exhaustiva de offsets.

## Qué respalda la literatura sobre calidad del bloque

El resumen editorial accesible respalda un objetivo cualitativo: combinar formas complementarias para reducir espacio desperdiciado y aumentar utilización local. También describe el uso posterior de espacios residuales con líneas de referencia para escoger piezas/bloques y sus ubicaciones. No publica en los pasajes accesibles una fórmula universal de “compactación” ni un umbral numérico para aceptar una pareja. La página editorial bloqueó el texto completo en esta sesión; no se atribuye a Cai et al. ningún cociente raster ni umbral local.

V1 usó `celdas ocupadas / área del bounding box` y rechazó una pareja si esa densidad no superaba la mayor densidad individual. Esa regla era una adaptación local, no una regla publicada, y su umbral relativo a la mejor pieza podía descartar una pareja que mejorara el aprovechamiento conjunto sin superar al miembro más denso.

Para Pair-Block v2 se fija como criterio experimental una **ganancia de bounding box** en celdas raster:

`ganancia = bbox_area(A) + bbox_area(B) - bbox_area(A ∪ B)`

La unión se calcula solo tras validar que las máscaras no se solapen y respeten la separación. Se considera complementaria una composición cuya ganancia sea positiva: su envolvente conjunta ocupa menos celdas que las dos envolventes individuales sumadas. La ganancia se usa como puntuación, no como una fórmula atribuida al artículo. Se eliminan el umbral `densidad > max(densidades individuales)` y el filtro fijo de razón 4:1. La densidad conjunta queda como valor descriptivo y desempate, no como requisito de aceptación. Así no se impone un porcentaje elegido manualmente y una pareja colocada lado a lado sin ahorro de envolvente no se etiqueta como bloque complementario.

## Pruning y contadores que implementará v2

1. Generar parejas solo dentro del grupo de igual material y espesor.
2. Enumerar los ángulos con `discrete_angles(angular_step_deg)` y pedir sus geometrías/máscaras al motor común de rotación y rasterización. No crear ángulos fuera de la grilla.
3. Reutilizar orientaciones por geometría equivalente y eliminar duplicados solo cuando coincidan dimensiones **y todas las filas de bits**; dimensiones iguales por sí solas no bastan.
4. Aplicar cotas optimistas de bounding box y compatibilidad con dimensiones de stock antes de `SheetLayout.check`. Una orientación se poda por cota solo si no puede superar la mejor ganancia encontrada para el par; los empates siguen siendo elegibles por su posible ajuste al stock.
5. Mantener offsets relativos deterministas y acotados; contar por separado pares, producto de orientaciones teórico, duplicados/pruning, pares de orientaciones enviados a validación geométrica y posiciones relativas comprobadas.
6. Eliminar el filtro de escala 4:1, ya que no se ha justificado y puede excluir piezas pequeñas que llenen recortes de una pieza mayor. No usar procesamiento paralelo.

**Pruning por fase global:** tras equivalencia de máscaras, las combinaciones se agrupan por el giro relativo `angle_B - angle_A`. Para cada giro relativo se conserva una sola fase global: primero la de menor área de caja envolvente mínima posible; en empate, la de mayor cota optimista de ahorro, densidad optimista acotada a 1 y desempate por ángulos. Priorizar la caja mínima evita favorecer rotaciones que solo aumentan las cajas individuales y su ahorro teórico. Esto reduce el máximo geométrico a 72 pares de orientación por pareja antes de offsets. Es un pruning heurístico, no una cota sin pérdida: la rasterización puede hacer que otra fase del mismo giro relativo tenga un resultado distinto. V2 cuenta por separado combinaciones tras simetría, tras cotas, tras fase, composiciones geométricas y offsets probados para que esta pérdida potencial sea visible.

**Pruning de offsets:** por cada fase se prueba primero una grilla corta y determinista de alineaciones (origen, contacto positivo/negativo y medio ancho/alto). Solo si una de ellas produce una composición sin solapamiento, con separación y ahorro positivo se amplía la búsqueda al conjunto acotado completo de hasta 8 offsets por eje. Si la primera grilla no encuentra composición, los offsets restantes se podan; esto también es heurístico y puede omitir una alineación válida que solo aparezca fuera de la grilla corta. Se registran offsets teóricos, podados y comprobados.

## Resultados Pair-Block v2

Se ejecutaron FF/BF/WF/Pair-Block v2 en serie sobre los tres fixtures TA-027 inalterados, `BLOCK-DISCRIMINANT-001` y los dos diagnósticos congelados en `BLOCK-V2-DIAGNOSTIC-INTENT.md`. El producto angular teórico se calcula sobre todos los pares iniciales; los pares incompatibles por material/espesor aparecen como pruning de compatibilidad. Por ello no coincide con la tabla previa, que solo enumeraba parejas compatibles.

| Caso | Pares iniciales / compatibles / filtrados | Orientaciones teóricas / podadas / evaluadas | Offsets teóricos / podados / comprobados | Bloques aceptados / colocados | Generación / packing / total ms | Clase |
|---|---:|---:|---:|---:|---:|:---:|
| SMALL | 3 / 3 / 0 | 15,552 / 15,543 / 9 | 291 / 210 / 81 | 0 / 0 | 10.686 / 0.911 / 12.457 | D |
| MEDIUM | 36 / 36 / 0 | 186,624 / 185,048 / 1,576 | 98,494 / 81,915 / 16,579 | 0 / 0 | 224.766 / 3.999 / 231.137 | E |
| COMPLEX | 276 / 181 / 95 | 1,430,784 / 1,420,632 / 10,152 | 648,736 / 544,518 / 104,218 | 0 / 0 | 1,918.168 / 34.022 / 1,957.860 | E |
| Discriminante | 3 / 3 / 0 | 15,552 / 15,336 / 216 | 13,728 / 10,668 / 3,060 | 1 / 1 | 76.093 / 0.320 / 77.925 | E |
| Triángulos oblicuos | 1 / 1 / 0 | 5,184 / 5,112 / 72 | 4,608 / 3,546 / 1,062 | 1 / 1 | 60.668 / 0.273 / 62.464 | E |
| Triángulo + círculo | 1 / 1 / 0 | 5,184 / 5,164 / 20 | 2,816 / 2,361 / 455 | 1 / 1 | 22.624 / 0.241 / 24.927 | E |

En total se podaron 1,646,835 de 1,658,880 combinaciones angulares teóricas: 492,480 por compatibilidad material/espesor, 986,683 por máscaras raster equivalentes, 9,950 por cotas, 157,698 por selección heurística de fase y 24 por cota contra el mejor bloque actual. Se comprobaron 125,455 de 768,673 offsets teóricos; 643,218 se podaron en la búsqueda escalonada. Los 95 pares filtrados en COMPLEX son incompatibles entre grupos de material/espesor, no pérdidas del fixture.

| Caso | FF/BF/WF frente a Pair-Block v2 | Resultado funcional |
|---|---|---|
| SMALL | 3/3; 1 retazo + 1 plancha; 60%; merma 0; recuperable 8. Pair-Block total 12.457 ms. | Empate funcional; no colocó bloque (D). |
| MEDIUM | Mejor baseline BF: 9/9; 2 retazos + 1 plancha; 28.413%; merma 193.86; recuperable 66. Pair-Block: merma 201.86, recuperable 58; total 231.137 ms. | Empeora dos métricas y tarda 12.549× el baseline más rápido (E). |
| COMPLEX | FF/BF: 24/24; 3 retazos + 3 planchas; 29.598%; merma 746.72; recuperable 184. Pair-Block conserva esas métricas; total 1,957.860 ms. | No colocó bloque y tarda 20.852× el baseline más rápido (E). |
| Discriminante | 3/3; 1 plancha; 94.444%; merma 10. Pair-Block colocó los triángulos originales en 0°/180°, con offset de 1 mm; total 77.925 ms. | Cambió el patrón, métricas iguales; 10.602× (E por precedencia de costo). |
| Triángulos oblicuos | Baseline: 2/2; 1 plancha; merma 180; recuperable 160. Pair-Block usó 60°/60°, merma 140, recuperable 200; total 62.464 ms. | Mejora merma y recuperable, pero cuesta 37.027× (E por precedencia). |
| Triángulo + círculo | Baseline: 2/2; 1 plancha; merma 87.37; recuperable 77. Pair-Block: merma 116.37, recuperable 48; total 24.927 ms. | Empeora métricas y cuesta 18.898× (E). |

La clasificación A–E aplica la precedencia declarada antes de correr métodos: E si empeora una métrica funcional o si el total supera 10× el baseline más rápido; después C para mejora sin pérdida de cobertura/fuentes; D si no se colocó bloque; B/A para bloque colocado con patrón distinto/igual y empate funcional. El umbral 10× es diagnóstico, no un criterio atribuido a la literatura. Las seis ejecuciones de determinismo ×3 pasaron para identidades, placements, orientaciones, bloques y métricas.

Los placements individuales que respaldan la formación de bloques quedaron en la traza y el notebook: en el discriminante las piezas 2 y 3 terminaron en (0, 0, 0°) y (1, 0, 180°), y el rectángulo en (11, 0, 0°); FF ubicó el rectángulo en x=0 y los triángulos en x=7/8, así que el patrón sí cambia. El diagnóstico oblicuo terminó con las piezas 1/2 en x=3/0, y=0, ambas a 60°. El caso mixto colocó el triángulo a 180° y el círculo a 0° en el origen, legal por sus máscaras raster.

## Decisión v2

La corrección angular sí encontró composiciones 5° válidas: el discriminante colocó dos triángulos en una caja raster densa y el diagnóstico oblicuo colocó su pareja a 60°. El diagnóstico mixto también formó y colocó un bloque, pero empeoró merma y recuperable. Ninguno de los fixtures oficiales colocó bloques. Los filtros reducen el espacio de búsqueda de forma determinista, aunque fase global y offsets son heurísticas con pérdida posible declarada.

**NO-GO para TA-042 con Pair-Block v2.** La causa es funcional y de costo: ninguna instancia oficial utilizó un bloque, MEDIUM empeoró merma/recuperable, y COMPLEX tardó 20.852× el baseline más rápido sin cambio de métricas. El resultado oblicuo demuestra utilidad geométrica en una instancia declarada de antemano, pero su costo 37.027× excede el umbral previo. Se preservan v1 y sus resultados, DJD y Filler. No se modifica código productivo ni se autoriza integración.
