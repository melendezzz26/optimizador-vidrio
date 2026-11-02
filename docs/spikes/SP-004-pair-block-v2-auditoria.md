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

## Estado de la evaluación

La especificación de v2 es una adaptación experimental. Una vez implementada se volverán a correr FF/BF/WF y Pair-Block en serie sobre SMALL/MEDIUM/COMPLEX inalterados, el discriminante y hasta tres instancias nuevas declaradas de antemano. Los resultados v1 permanecen como antecedente; el dictamen de Pair-Block queda pendiente hasta revisar la grilla de 5°, los nuevos contadores, los placements y el costo.
