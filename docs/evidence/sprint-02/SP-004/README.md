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
