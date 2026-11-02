# SP-004 — Evidencia experimental de Djang and Finch

## Responsable y estado

Responsable: Andro Joseph Quispe Cesias. Trabajo local en `spike/S2-SP004-djd`, derivado del historial de Filler con base `f7b8861`. DJD-1/3 fue evaluado en un laboratorio aislado y recibe recomendación **NO-GO para TA-042 con esta implementación** por costo computacional. La rama no se publicó y no hay PR ni merge.

Filler queda descartado como candidato M4 principal porque FF en NewGlass ya ordena por área descendente y Filler coincidió con FF en unidades, fuentes y aprovechamiento en SMALL, MEDIUM y COMPLEX. Se preservaron su Spike, notebook ejecutado, resultados, trazas y commits bajo nombres que indican candidato descartado. Ver [evidencia histórica de Filler](README-Filler-descartado.md).

## Protocolo

- Fixtures oficiales TA-027 sin modificaciones: `EXP-SMALL-001`, `EXP-MEDIUM-001`, `EXP-COMPLEX-001`.
- Métodos ejecutados en serie: FF, BF, WF y DJD-1/3.
- Resolución 1 mm, paso angular 5°, materiales, espesores, geometrías, retazos, planchas, margen, separación y cálculo oficial de métricas idénticos a los fixtures.
- Windows, Python 3.11, entorno virtual `.venv`; sin multiprocessing.
- DJD conserva `w = 0` inicial, umbral de llenado nominal 1/3 y `delta_w = stock.area_mm2 / 20`. El área nominal residual se usa para pruning; todo placement se valida por el layout real de NewGlass.
- El caso `DJD-DISCRIMINANT-001` se reporta separado y no es parte de TA-027.

Comandos reproducibles desde la raíz del repositorio:

```powershell
.venv/Scripts/python experiments/optimization/djd/run_benchmark.py
.venv/Scripts/python experiments/optimization/colab/create_sp004_djd_notebook.py
.venv/Scripts/python experiments/optimization/djd/create_figure.py
.venv/Scripts/python -c "import sys, pytest; sys.path.insert(0, 'backend'); raise SystemExit(pytest.main(['experiments/optimization/djd/test_djd.py', 'experiments/optimization/filler/test_filler.py', 'backend/tests/unit/optimization/test_first_fit.py', 'backend/tests/unit/optimization/test_best_fit.py', 'backend/tests/unit/optimization/test_worst_fit.py', '-q']))"
```

`SP004-DJD.ipynb` tiene 36 secciones, 98 celdas totales y 31 celdas Python ejecutadas con outputs sin errores. La ejecución fue local; no se dispuso de una sesión conectada a un kernel remoto de Google Colab. El notebook incluye las repeticiones DJD ×3 de cada fixture con firmas idénticas.

## Resultados TA-027

Los cuatro métodos colocaron todas las unidades solicitadas. El costo de ejecución es local y sirve como diagnóstico de esta corrida; no es un SLA de rendimiento.

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

DJD empata las métricas finales de FF en los tres fixtures y elige una terna en COMPLEX, pero su corrida tarda aproximadamente 50× FF. En MEDIUM tarda aproximadamente 8.8× FF sin mejorar el resultado final. WF usa una plancha adicional en MEDIUM y COMPLEX; BF reduce la merma en MEDIUM en 8 mm² frente a FF y DJD.

| Caso DJD | Subconjuntos generados 1/2/3 | Podados | Secuencias geométricas | Cache omitió | Checks geométricos por pieza | Factibles | Pasos `w` | Tamaños seleccionados |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| SMALL | 3/0/0 | 0 | 0 | 0 | 3 | 0 | 0 | 1, 1, 1 |
| MEDIUM | 214/471/634 | 983 | 397 | 996 | 582 | 1 | 35 | singles |
| COMPLEX | 791/4,409/18,493 | 13,813 | 7,527 | 45,571 | 7,587 | 1 | 68 | una terna, resto singles |

Los contadores de subconjuntos incluyen intentos singleton durante el llenado inicial y visitas a través de los pasos de tolerancia, por lo que pueden volver a contar un mismo subconjunto. Las secuencias geométricas fallidas se cachean mientras se conserva el mismo layout. `feasible_combinations` cuenta grupos aceptados; DJD termina la búsqueda de cada decisión en el primer grupo que cabe. El benchmark CSV/JSON contiene todos los diagnósticos además de las métricas oficiales.

## Caso discriminante no oficial

Los cuatro métodos colocaron 3/3 piezas, usaron una plancha, alcanzaron 95.000% de aprovechamiento y 0 mm² de merma. DJD seleccionó el par de piezas `[2, 3]` después del llenado inicial. El residuo nominal fue 5 mm² y se aceptó con el primer incremento `w = 100 / 20 = 5 mm²`. Esto demuestra una selección conjunta, no una mejora de rendimiento.

## Pruebas y verificación de CA

Comando ejecutado: ver los comandos reproducibles. Resultado: **93 passed**, incluyendo nueve pruebas DJD, Filler preservado y regresiones FF/BF/WF. Pytest mostró una advertencia de permisos al actualizar `.pytest_cache`; no afectó las pruebas.

CA-01–CA-10 están registrados y verificados en [PLAN-SP-004-djd.md](../../../specs/PLAN-SP-004-djd.md). No hay cambios productivos ni cambios a fixtures TA-027. La notebook pasó validación estructural: 36 secciones, 31 ejecuciones y cero outputs de error. Las firmas de placements y decisiones fueron iguales en las tres corridas por fixture; runtime no forma parte de la firma.

## Archivos de evidencia

- Benchmark y trazas: [CSV](benchmark-results/sp004_djd_results.csv), [JSON](benchmark-results/sp004_djd_trace.json).
- Investigación, resultados y decisión: [SP-004-djd.md](../../../spikes/SP-004-djd.md).
- SPEC / PLAN / TASKS: [SPEC](../../../specs/SPEC-SP-004-djd.md), [PLAN](../../../specs/PLAN-SP-004-djd.md), [TASKS](../../../specs/TASKS-SP-004-djd.md).
- Revisión técnica y verificación final: [SP-004-djd-review.md](../../../reviews/SP-004-djd-review.md).
- Notebook: [SP004-DJD.ipynb](../../../../experiments/optimization/colab/SP004-DJD.ipynb).
- Caso fuera de TA-027: [DJD-DISCRIMINANT-001.json](../../../../experiments/optimization/djd/cases/DJD-DISCRIMINANT-001.json).
- Figura conceptual: [SP-004-djd-example.png](../../../spikes/assets/SP-004-djd-example.png).

## Decisión

**NO-GO para llevar esta implementación a TA-042.** DJD tiene una diferencia operacional real, pasa las reglas geométricas y de inventario, es determinista y reutiliza el motor. El costo medido —7.7 s para 24 unidades frente a 154 ms de FF— no es razonable para esta comparación dado que no mejora cobertura, fuentes, aprovechamiento ni merma en COMPLEX. Para una futura reevaluación se necesitaría una poda más eficiente y evidencia adicional; la decisión no cambia fixtures ni producción.

## Commits locales

- `877d17b` — `docs(SP-004): seleccionar DJD y archivar Filler`
- `5843f6f` — `experiment(SP-004): implementar laboratorio DJD`
- `afe8637` — `test(SP-004): validar DJD y determinismo`
- `69bcae4` — `experiment(SP-004): agregar notebook DJD ejecutado`

Estos commits y el commit de cierre de evidencia permanecen solo en la rama local `spike/S2-SP004-djd`.

## Hito Pair-Block y diagnóstico adicional DJD

Responsable: Andro Joseph Quispe Cesias. La rama sigue local; no se hizo push, PR ni merge. Este hito mantiene todos los artefactos de Filler y DJD anteriores y agrega una adaptación experimental Pair-Block sin cambios productivos.

La referencia académica revisada fue Cai et al. (2023), *Heuristics for the two-dimensional irregular bin packing problem with limited rotations*, DOI [10.1016/j.cor.2023.106398](https://doi.org/10.1016/j.cor.2023.106398). La publicación combina bloques complementarios con espacios residuales, operadores de búsqueda y repacking. Pair-Block limita el concepto a dos piezas compatibles, orientaciones cardinales ya permitidas y una máscara raster temporal. La métrica de densidad de caja es una adaptación explícita, no una fórmula atribuida al artículo.

Pair-Block comparó los tres fixtures TA-027 inalterados y `BLOCK-DISCRIMINANT-001`. Ningún bloque llegó a colocarse en TA-027. En COMPLEX se aceptó geométricamente un par pero no cupo como máscara compuesta; el fallback individual mantuvo las mismas métricas de FF. Su runtime fue 2,998.492 ms frente a 169.095 ms de FF. En el discriminante la pareja triangular sí se colocó como bloque y cambió el patrón frente a FF; los cuatro métodos empataron con 3/3 piezas, una plancha, 94.444% de aprovechamiento y 10 mm² de merma.

El diagnóstico DJD usa cuatro casos nuevos con intenciones registradas antes de correr métodos. La selección de terna en `DJD-DIAGNOSTIC-003` produjo métricas iguales a FF/BF/WF. `DJD-DIAGNOSTIC-004` empató al mejor baseline y superó a WF; los otros casos empataron con todos. No hubo mejora frente al mejor baseline. Las cuatro clases son A, con un indicador adicional de si las decisiones variaron.

| Caso oficial | FF uso / merma / planchas | Pair-Block uso / merma / planchas | Bloques colocados | Pair-Block ms |
|---|---|---|---:|---:|
| SMALL | 60.000% / 0 / 1 | 60.000% / 0 / 1 | 0 | 23.220 |
| MEDIUM | 28.413% / 201.86 / 1 | 28.413% / 201.86 / 1 | 0 | 291.847 |
| COMPLEX | 29.598% / 746.72 / 3 | 29.598% / 746.72 / 3 | 0 | 2,998.492 |

Archivos de resultados:

- Pair-Block: [CSV](benchmark-results/sp004_block_results.csv), [traza JSON y determinismo](benchmark-results/sp004_block_trace.json).
- DJD diagnóstico: [CSV](benchmark-results/sp004_djd_diagnostic_results.csv), [traza JSON y categorías](benchmark-results/sp004_djd_diagnostic_trace.json).
- Manifiesto previo y casos: [`DJD-DIAGNOSTIC-INTENT.md`](../../../../experiments/optimization/djd/DJD-DIAGNOSTIC-INTENT.md), cuatro JSON `DJD-DIAGNOSTIC-001` a `004`.
- Caso didáctico y figuras de comparación: [`block_packing/`](../../../../experiments/optimization/block_packing/).
- Notebook ejecutado: [`SP004-Block-Packing.ipynb`](../../../../experiments/optimization/colab/SP004-Block-Packing.ipynb), 34 secciones de contenido y 28 celdas de código ejecutadas localmente.
- Decisión, criterio de compactación y resultados: [SP-004-investigacion-m4.md](../../../spikes/SP-004-investigacion-m4.md).
- SPEC/PLAN/TASKS nuevos: [SPEC](../../../specs/SPEC-SP-004-heuristica-m4.md), [PLAN](../../../specs/PLAN-SP-004-heuristica-m4.md), [TASKS](../../../specs/TASKS-SP-004-heuristica-m4.md).

## Validación de cierre del hito Pair-Block

Suite ejecutada: `104 passed in 16.58s`, incluyendo 11 pruebas específicas Pair-Block, DJD, Filler y regresiones FF/BF/WF. El notebook se regeneró y ejecutó localmente: 34 secciones, 28 celdas de código con outputs, comentarios en cada línea no vacía y cero errores. Los nueve JSON del laboratorio parsean correctamente; `git diff --check` no reportó errores.

Revisión final: [SP-004 M4](../../../reviews/SP-004-heuristica-m4-review.md); matriz CA: [PLAN](../../../specs/PLAN-SP-004-heuristica-m4.md). No se modificaron módulos productivos ni fixtures oficiales.


Commits locales del hito Pair-Block/DJD:

- `166551c` ? `experiment(SP-004): implementar Pair-Block y diagn?stico DJD`
- `379ad4e` ? `experiment(SP-004): agregar notebook Pair-Block ejecutado`
- `de60560` ? `docs(SP-004): registrar evaluaci?n comparativa y resultados`
- Cierre del hito: `docs(SP-004): cerrar hito y registrar commits locales`



## Reapertura Pair-Block v2

Los resultados anteriores corresponden a Pair-Block v1 y no cierran el dictamen del candidato. Antes de modificar codigo se documento por que v1 exploro solo giros cardinales, su deduplicacion por dimensiones, la expansion potencial de la grilla y el criterio experimental v2. Vease [auditoria previa](../../../spikes/SP-004-pair-block-v2-auditoria.md). Los benchmarks v2 se completaron en la reevaluacion siguiente; Filler y DJD permanecen intactos.

## Resultado de la reevaluación Pair-Block v2

La evaluación terminó en `spike/S2-SP004-djd`. Se conservaron intactos los resultados v1, Filler, DJD y los tres fixtures oficiales. V2 usa solo los 72 ángulos comunes de NewGlass, con equivalencia únicamente para máscaras idénticas; acepta una pareja si su ahorro de bounding box es positivo. La densidad queda descriptiva y no se atribuye a la literatura como criterio formal.

| Caso | Resultado y uso | Merma / recuperable | Generación / packing / total ms | Ratio vs baseline más rápido | Clase |
|---|---|---|---:|---:|:---:|
| SMALL | 3/3; 1 retazo + 1 plancha; no bloque | 0 / 8 | 10.686 / 0.911 / 12.457 | 1.161× | D |
| MEDIUM | 9/9; 2 retazos + 1 plancha; no bloque | 201.86 / 58; BF logra 193.86 / 66 | 224.766 / 3.999 / 231.137 | 12.549× | E |
| COMPLEX | 24/24; 3 retazos + 3 planchas; no bloque | 746.72 / 184, igual a FF/BF | 1,918.168 / 34.022 / 1,957.860 | 20.852× | E |
| Discriminante | Triángulos 0°/180°; bloque colocado; patrón distinto, métricas empatadas | 10 / 0 | 76.093 / 0.320 / 77.925 | 10.602× | E |
| Triángulos oblicuos | Triángulos 60°/60°; bloque colocado; baja merma 180→140 | 140 / 200; baseline 180 / 160 | 60.668 / 0.273 / 62.464 | 37.027× | E |
| Triángulo + círculo | Bloque colocado; no mejora el patrón funcional | 116.37 / 48; baseline 87.37 / 77 | 22.624 / 0.241 / 24.927 | 18.898× | E |

La clasificación siguió la precedencia congelada antes de ejecutar: E por deterioro funcional o runtime mayor de 10×; C por mejora sin pérdida de cobertura/fuentes; D sin bloque; B/A con bloque y empate funcional según cambie o no el patrón. Por ello el caso oblicuo queda E aunque mejore merma y recuperable. Las seis corridas de determinismo ×3 pasaron.

En los seis casos hubo 320 pares iniciales, 225 compatibles y 95 filtrados por material/espesor. De 1,658,880 combinaciones angulares teóricas se podaron 1,646,835 y se evaluaron 12,045. Se probaron 125,455 de 768,673 offsets teóricos. La poda por fase y por offsets es heurística y puede omitir opciones que dependen de la rasterización; se contó por separado.

**Decisión: NO-GO para TA-042 con Pair-Block v2.** No colocó bloques en los fixtures oficiales; COMPLEX tarda 20.852× el baseline más rápido sin cambiar métricas y MEDIUM empeora merma/recuperable. El oblicuo prueba complementariedad bajo 5°, pero tarda 37.027×; el mixto empeora métricas.

- [Auditoría y resultados detallados](../../../spikes/SP-004-pair-block-v2-auditoria.md)
- [CSV v2](benchmark-results/sp004_block_v2_results.csv) · [traza JSON y determinismo](benchmark-results/sp004_block_v2_trace.json)
- [Notebook v2 ejecutado](../../../../experiments/optimization/colab/SP004-Block-Packing.ipynb)
- [Revisión técnica local](../../../reviews/SP-004-pair-block-v2-review.md)

El trabajo queda local: sin push, PR, merge ni integración de TA-042.


## Mini-spike Raster Hole Filling / Pocket Filling

Candidato vigente de SP-004: adaptacion raster aislada, sin cambio productivo. Filler, DJD y Pair-Block permanecen archivados y conservados. Los cuatro diagnosticos se congelaron antes de ejecutar los metodos y no pertenecen a TA-027.

**Gate:** mini-spike **VIABLE**. HF uso pockets en 001 (circulo), 002 (triangulos) y 003 (poligono convexo); las tres clases son B y cambian el patron. El control 004 es A y usa fallback FF sin forzar un pocket. Ninguno genero hueco fisico completamente cerrado; los pockets se detectan en el mapa de origenes legales para una pieza/orientacion. Las cuatro corridas HF fueron deterministas en tres repeticiones, con maximo 5.85x sobre el baseline mas rapido.

| Caso EXP | Clase | Pockets usados | Resultado HF | Costo relativo |
|---|:---:|---:|---|---:|
| SMALL | A | 0 | 3/3; empata FF; 60.000%, merma 0, recuperable 8. | 1.15x |
| MEDIUM | D | 0 | 9/9; reproduce FF; BF ahorra 8 mm2 y recupera 8 mm2 mas. | 4.92x |
| COMPLEX | E | 0 | 24/24; reproduce FF, sin cambio funcional. | 14.83x |

Decision de integracion: **NO-GO para TA-042**. El mecanismo funciona en diagnosticos dirigidos, pero no encontro pockets usados en los fixtures EXP y el costo de COMPLEX excedio 10x.

- Diagnosticos: [CSV](hole-filling/sp004_hole_filling_results.csv), [traza](hole-filling/sp004_hole_filling_trace.json), [mapas y tiempos de deteccion](hole-filling/sp004_hole_filling_detection.json).
- Benchmark EXP condicionado por gate: [CSV](hole-filling/sp004_hole_filling_official_results.csv) y [traza](hole-filling/sp004_hole_filling_official_trace.json).
- Algoritmo, fixtures, pruebas y SVG: [`experiments/optimization/hole_filling`](../../../../experiments/optimization/hole_filling/).
- Notebook con outputs reales: [`SP004-Hole-Filling.ipynb`](../../../../experiments/optimization/colab/SP004-Hole-Filling.ipynb).
- Especificacion y plan: [SPEC](../../../specs/SPEC-SP-004-heuristica-m4.md), [PLAN](../../../specs/PLAN-SP-004-heuristica-m4.md), [TASKS](../../../specs/TASKS-SP-004-heuristica-m4.md); [investigacion M4 actualizada](../../../spikes/SP-004-investigacion-m4.md).

En el cierre inicial se registraron 11 PASS de Hole Filling y 145 regresiones. La validación realista actual amplió la suite HF a 13 PASS; no se modificaron producción ni fixtures oficiales. El cierre de esta etapa se conserva en commits locales, sin push, PR ni merge.

## Validación final con pedidos realistas — Hole Filling

Se congelaron tres pedidos sintéticos antes de ejecutar las heurísticas. Los bytes de cada JSON están identificados por SHA-256 y por el commit local `fda6d12`; el detalle de la intención, dimensiones y configuración está en [HF-REALISTIC-INTENT.md](../../../../experiments/optimization/hole_filling/cases/HF-REALISTIC-INTENT.md). Son perfiles plausibles de taller, no datos de clientes. Se mantuvieron material 1, vidrio de 6 mm, raster de 1 mm, orientaciones cada 5°, margen 5 mm, separación 3 mm y política retazo → plancha. Cada caso tiene un retazo y una plancha.

### Comparación de métricas oficiales

Cada celda indica colocadas/solicitadas, sin colocar, retazos/planchas usados, utilización, merma en mm², área recuperable en mm² y runtime en ms. Las cifras funcionales son las métricas originales del motor; runtime es una ejecución para FF/BF/WF y la mediana de tres para HF.

| Caso | FF | BF | WF | HF |
|---|---|---|---|---|
| HF-REALISTIC-001 · 15 unidades | 15/15; 0; 1/1; 65.745%; 49,908.91; 18,738; 369 | 15/15; 0; 1/1; 65.745%; 49,908.91; 18,738; 385 | 15/15; 0; 1/1; 65.745%; 49,908.91; 18,738; 356 | 15/15; 0; 1/1; 65.745%; 49,908.91; 18,738; 96,383 |
| HF-REALISTIC-002 · 18 unidades | 18/18; 0; 1/1; 43.490%; 57,164.00; 66,536; 1,741 | 18/18; 0; 1/1; 43.490%; 57,164.00; 66,536; 1,795 | 18/18; 0; 1/1; 43.490%; 57,164.00; 66,536; 1,792 | 18/18; 0; 1/1; 43.490%; 57,164.00; 66,536; 236,795 |
| HF-REALISTIC-003 · 20 unidades | 20/20; 0; 1/1; 74.329%; 60,627.26; 14,948; 574 | 20/20; 0; 1/1; 74.329%; 60,627.26; 14,948; 566 | 20/20; 0; 1/1; 74.329%; 60,627.26; 14,948; 562 | 19/20; 1; 1/1; 71.101%; 77,120.58; 7,958; 238,463 |

Columnas funcionales: colocadas/solicitadas; no colocadas; retazos/planchas; porcentaje de uso; merma; recuperable; runtime. Todos los métodos conservaron el mismo inventario inicial por caso.

### Actividad de pockets y clasificación

Los pockets detectados son componentes interiores del mapa de anclajes legales para una pieza/orientación. Son candidatos de placement, no un conteo de cavidades físicas únicas. El runtime relativo usa la mediana HF frente al baseline más rápido. La categoría E tiene precedencia por el umbral congelado de más de 10×; entre paréntesis se indica la lectura funcional sin esa penalización.

| Caso | Pockets detectados | Pockets usados | Piezas en pocket | Resultado |
|---|---:|---:|---:|---|
| HF-REALISTIC-001 | 0 | 0 | 0 | E (A funcional); patrón y métricas iguales al baseline; 270.88× |
| HF-REALISTIC-002 | 11 | 1 | 1 | E (B funcional); patrón distinto, métricas iguales; 136.02× |
| HF-REALISTIC-003 | 70 | 6 | 6 | E (D funcional); una unidad sin colocar y peores uso, merma y recuperable; 424.65× |

HF-REALISTIC-001 contiene tres círculos de 120–180 mm de diámetro, dos paneles y diez piezas pequeñas. Los círculos no produjeron pockets utilizables; HF recurrió al fallback en sus 15 piezas y reprodujo el baseline. No se generó una figura de pocket.

HF-REALISTIC-002 contiene ocho triángulos, cinco polígonos convexos y cinco piezas pequeñas. HF colocó la pieza 5 en la plancha a 255° y en (283, 41) mm. La firma de placement cambió respecto de FF/BF/WF, aunque las métricas empataron. [La figura](../../../../experiments/optimization/hole_filling/figures/HF-REALISTIC-002-pocket-01.svg) muestra el layout previo, el pocket, la pieza y su placement.

HF-REALISTIC-003 mezcla cuatro rectángulos grandes, cuatro círculos, seis polígonos convexos y seis rectángulos pequeños. HF usó seis pockets: pieza 13 en PLANCHA a 70° (155, 132); pieza 14 en PLANCHA a 170° (242, 153); pieza 10 en PLANCHA a 110° (187, 240); pieza 12 en PLANCHA a 350° (68, 240); pieza 19 en PLANCHA a 15° (123, 332); pieza 15 en RETAZO a 10° (135, 148). Vistas: [01](../../../../experiments/optimization/hole_filling/figures/HF-REALISTIC-003-pocket-01.svg), [02](../../../../experiments/optimization/hole_filling/figures/HF-REALISTIC-003-pocket-02.svg), [03](../../../../experiments/optimization/hole_filling/figures/HF-REALISTIC-003-pocket-03.svg), [04](../../../../experiments/optimization/hole_filling/figures/HF-REALISTIC-003-pocket-04.svg), [05](../../../../experiments/optimization/hole_filling/figures/HF-REALISTIC-003-pocket-05.svg), [06](../../../../experiments/optimization/hole_filling/figures/HF-REALISTIC-003-pocket-06.svg). A pesar de esas decisiones, HF dejó una pieza sin colocar y empeoró las métricas respecto de los tres baselines.

La detección incluye generación del mapa de anclajes y etiquetado de componentes; la traza separa ambas etapas, el placement pocket y la búsqueda fallback. Los tiempos medianos de detección fueron 94,789.53 / 231,987.67 / 236,147.70 ms; la generación de mapa consumió 91,675.95 / 226,456.56 / 231,309.62 ms. El etiquetado tomó 3,113.58 / 5,531.11 / 4,838.08 ms y los placements pocket 1,515.89 / 3,073.25 / 2,131.74 ms. Se revisaron 0/11/70 opciones pocket, se contaron 15/17/14 fallbacks y 3/5/6 cambios de fuente; la traza conserva además 427,386,185 / 588,696,124 / 1,087,324,886 posiciones geométricas evaluadas. El Working Set de Windows observado durante la ejecución se mantuvo alrededor de 460 MB; no se usó un profiler de memoria.

Las tres firmas funcionales HF fueron iguales entre sus respectivas tres repeticiones: **determinismo PASS** para los tres casos. Tiempos individuales, placements, hashes, configuración y contadores están en [traza JSON](hole-filling/sp004_hf_realistic_trace.json); el [CSV](hole-filling/sp004_hf_realistic_results.csv) contiene la comparación y las métricas agregadas. El [notebook](../../../../experiments/optimization/colab/SP004-Hole-Filling.ipynb) incluye los outputs derivados de esa traza y las figuras solo para casos con pockets usados.

**Dictamen final: NO-GO para TA-042.** HF sí mostró decisiones propias en 002 y 003, pero en 002 solo cambió el patrón con un costo de 136×; en 003 colocó seis piezas en pockets pero perdió cobertura y empeoró merma, uso y recuperable a 425×; 001 no usó pockets y costó 271×. El efecto no justifica ese costo local y no conviene integrar esta implementación.

Verificación final: 13 pruebas HF PASS y 145 regresiones focalizadas PASS. Los SVG se validaron como XML. No se modificaron producción, FF/BF/WF, fixtures TA-027 ni los resultados previos de SP-004. No hubo push, PR ni merge.

## Experimento demostrativo de capacidad

> **CASO CONTROLADO DISEÑADO PARA MOSTRAR LA CLASE DE PEDIDO EN LA QUE HOLE FILLING PUEDE SER ÚTIL. NO REPRESENTA RENDIMIENTO GENERAL.**

**Evaluación general:** SMALL/MEDIUM/COMPLEX, diagnósticos y HF-REALISTIC-001/002/003 conservan sus resultados anteriores. La recomendación general para integrar esta implementación en TA-042 sigue siendo **NO-GO**. **Capacidad específica:** HF-CAPABILITY-001 es una configuración dirigida para mostrar cómo un pocket puede reservar espacio exterior; no estima la frecuencia de ese patrón.

El fixture contiene un retazo de 274 × 280 mm, una plancha de igual tamaño, vidrio del mismo material de 6 mm, 16 piezas ya colocadas y verificadas con `SheetLayout` (un círculo y 15 paneles), un inserto pendiente de 32 × 32 mm (P11) y un círculo pendiente de Ø36 mm (P12). Usa raster 1 mm, giros cada 5°, margen 5 mm, separación 3 mm y prioridad retazo → plancha. La preparación ordena P11 antes de P12 por área: 1,024 frente a aproximadamente 1,017.88 mm².

La [intención previa](../../../../experiments/optimization/hole_filling/cases/HF-CAPABILITY-INTENT.md) declara el diseño favorable y los criterios de selección. La [búsqueda separada](../../../../experiments/optimization/hole_filling/cases/HF-CAPABILITY-SEARCH.jsonl) registró 20 configuraciones; el candidato 20 fue el primero válido y la búsqueda se detuvo. El fixture se congeló antes del benchmark definitivo en `f806a27`, SHA-256 `565a7bcd47a8de773f9f7e0c5804a35b618db1e32c0074d8e45eaeacf5d565e5`. El pocket esperado inicialmente cerca de la parte superior del círculo no fue el seleccionado: el componente usado quedó **abajo a la izquierda del marco**, en (51, 191) mm.

### Traza sencilla de la decisión

1. Las 16 piezas previas dejan un marco parcialmente ocupado y una franja libre arriba a la izquierda del retazo.
2. El motor procesa primero P11, el inserto. FF/BF/WF lo colocan fuera del pocket, en (5, 5) mm del retazo.
3. HF detecta 7 componentes candidatos y coloca P11 en un pocket del retazo, a 0° y (51, 191) mm. Su área de anclajes legales tiene 60 celdas.
4. Llega P12, el círculo posterior. En FF/BF/WF la franja exterior quedó ocupada y P12 pasa a la plancha, en (5, 5) mm.
5. HF coloca P12 mediante fallback en (5, 5) mm del retazo: la franja permaneció disponible gracias al placement pocket de P11.

### Métricas definitivas

Los cuatro métodos colocaron 18/18 y no dejaron unidades pendientes. Cada uno usó un retazo; solo HF evitó la plancha. Los tiempos FF/BF/WF corresponden a una ejecución; HF es la mediana de tres ejecuciones.

| Método | Retazos | Planchas | Utilización | Merma mm² | Recuperable mm² | Runtime ms |
|---|---:|---:|---:|---:|---:|---:|
| FF | 1 | 1 | 33.787% | 37,516.56 | 64,080 | 63.05 |
| BF | 1 | 1 | 33.787% | 37,516.56 | 64,080 | 62.32 |
| WF | 1 | 1 | 33.787% | 37,516.56 | 64,080 | 62.81 |
| HF | 1 | 0 | 67.575% | 22,410.56 | 2,466 | 262.99 |

HF usó **una plancha menos** (nivel 1 de demostración), elevó la utilización 33.788 puntos y redujo la merma 15,106 mm². Su área recuperable reportada fue 61,614 mm² menor; esta diferencia se conserva tal como la calculó la métrica oficial. HF tardó 4.22× el baseline más rápido. Detectó 7 componentes candidatos, usó 1 pocket para 1 pieza, revisó 7 opciones y efectuó 1 fallback. Los tres runtimes HF fueron 266.88, 262.99 y 258.75 ms; las firmas funcionales coincidieron: **determinismo PASS**.

[Comparación de layouts finales](../../../../experiments/optimization/hole_filling/figures/HF-CAPABILITY-001-comparison.svg) y [etapa del pocket](../../../../experiments/optimization/hole_filling/figures/HF-CAPABILITY-001-pocket-stage.svg) muestran las mismas máscaras raster de las corridas. El panel HF marca el componente de anclajes y P11; FF/BF/WF muestran la plancha utilizada. Datos completos: [CSV](hole-filling/sp004_hf_capability_results.csv), [traza JSON](hole-filling/sp004_hf_capability_trace.json) y [sección ejecutable del mismo notebook](../../../../experiments/optimization/colab/SP004-Hole-Filling.ipynb).

Para una posible investigación de activación en TA-042, buscar pedidos con círculos o convexos, mezcla de tamaños, ocupación suficiente, piezas pequeñas aún pendientes y un pocket legal detectado a bajo costo. Este caso no implementa esa activación ni demuestra superioridad general; las mediciones realistas y el NO-GO previo permanecen vigentes.
