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
