# Evidencia TA-QA-002 — Rendimiento y Carga

| Campo | Valor |
|---|---|
| Tarea | **TA-QA-002 — Rendimiento y Carga** |
| Sprint | Sprint 2 |
| Fecha de medición | 09/11/2026 – 10/11/2026 |
| Responsable | Luis Anthony Ibañez Herrera |
| Reviewer | Fabricio Melendez Quezada |
| Rama | `qa/TA-QA-002-rendimiento-carga` |
| Base | `integration-02` en commit `b964b2b` |
| Especificación | [SPEC-TA-QA-002](../../../specs/SPEC-TA-QA-002-rendimiento-carga.md) · [PLAN](../../../specs/PLAN-TA-QA-002-rendimiento-carga.md) · [TASKS](../../../specs/TASKS-TA-QA-002-rendimiento-carga.md) |
| Script reproducible | [`backend/scripts/benchmark_qa_002.py`](../../../../backend/scripts/benchmark_qa_002.py) |
| Datos crudos | [`raw_results.json`](raw_results.json) |
| Documento Notion | [`Notion/TA-QA-002/Evidencia_Notion_TA-QA-002.docx`](../../../../../Notion/TA-QA-002/Evidencia_Notion_TA-QA-002.docx) |

---

## 1. Resumen Ejecutivo y Hallazgos Principales

Se ejecutaron pruebas de carga, rendimiento y consumo de memoria sobre los seis motores de optimización del proyecto (`FF`, `BF`, `WF`, `HF`, `M5`, `M6-BS`) bajo la metodología **SDD (Specification-Driven Development)**:

1. **Escenarios de 10 y 25 unidades (Inéditos y Altamente Viables):** Todos los motores completan el 100% de las piezas con consumos de memoria controlados (39 a 65 MiB de RSS). First Fit y Hole Filling responden en menos de 1.6 s. M6-BS completa en 2.03 s (10u) y 8.69 s (25u).
2. **Escenario de 50 unidades:** Todos los motores completan las 50 piezas en 4 planchas con 60.57% de aprovechamiento. Sin embargo, Best Fit (p50: 38.44 s) y Worst Fit (p50: 28.44 s) superan o rozan la ventana de 30 segundos, identificando el punto exacto donde las peticiones síncronas en Heroku comienzan a sufrir timeouts `H27`.
3. **Escenario de 100 unidades:** First Fit (18.58 s) y Hole Filling (18.41 s) son altamente eficientes. M5 completa en 86.44 s gracias a la optimización de tramos de columnas (F4b). Por su parte, M6-BS detiene su búsqueda de forma transparente a las 58 piezas por límite de memoria (`STATE_MEMORY_LIMIT`), sin inventar colocaciones tras la eliminación del fallback sintético.
4. **Escenario de 150 unidades (Primera Frontera de Corte):** M5 supera los 120 s de cálculo (`TIME_BUDGET_EXCEEDED`) y M6-BS agota su plazo nativo (`TIME_LIMIT`). Best Fit roza el corte con 115.92 s. First Fit (52.84 s), Worst Fit (92.91 s) y Hole Filling (53.00 s) logran colocar el 100% en 10 planchas con 71.47% de aprovechamiento.
5. **Escenario de 200 unidades (Límite de Capacidad Comercial):** En esta máquina, la combinatoria de comprobaciones raster a 1 mm y 72 giros a 5° satura el presupuesto de 120 s: los cinco motores heurísticos (`FF`, `BF`, `WF`, `HF`, `M5`) finalizan con `TIME_BUDGET_EXCEEDED`. M6-BS coloca 44 piezas y finaliza con `TIME_LIMIT`.
6. **Honestidad en Cargas Mayores (300 y 800 unidades):** Se ratifica que 300 unidades comerciales grandes colapsan en el 100% de los motores. Se documenta técnicamente que la prueba de 800 unidades realizada por el compañero en `ACADEMIC-800` solo fue viable porque utilizó piezas sintéticas reducidas (120×80 mm, 50 veces más pequeñas que las comerciales), por lo que **no se debe afirmar que el sistema soporta 800 unidades en producción comercial**.

---

## 2. Entorno de Ejecución y Condiciones de Prueba

* **Sistema Operativo:** Windows 11 (plataforma `win32`, arquitectura AMD64).
* **Intérprete:** Python 3.11.9 (64-bit), coincidente con el estándar del proyecto.
* **Librerías principales:** `numpy 2.x`, `pydantic 2.x`, `psutil 7.x`.
* **Aislamiento:** Subprocesos independientes con `multiprocessing.get_context('spawn')`.
* **Muestreo de memoria:** Sondeo continuo cada 40 ms sobre `psutil.Process(pid).memory_info().rss`.
* **Geometría sintética canónica:**
  - Rectángulos $600 \times 800\text{ mm}$ ($480\,000\text{ mm}^2$).
  - Círculos de radio $260\text{ mm}$ ($212\,371.66\text{ mm}^2$).
  - Pentágonos convexos $(0,0),(500,0),(620,400),(250,700),(0,400)$ ($317\,000\text{ mm}^2$).
  - 2 grupos de vidrio independientes de 6 mm de espesor ($N/2$ piezas cada uno).
  - Planchas de $2140 \times 3300\text{ mm}$ ($7\,062\,000\text{ mm}^2$), asignadas con $S(n) = \max(4, \min(50, n))$.
  - Resolución $1\text{ mm}$, margen $3\text{ mm}$, separación $3\text{ mm}$, paso angular $5^\circ$ (72 giros).
* **Límites operativos:** Checkpoint estricto de 120 s por motor, timeout de supervisor a los 150 s.
* **Repeticiones:** $N = 3$ iteraciones independientes por cada motor y tamaño para cálculo de p50 y p95.

---

## 3. Matriz Consolidada de Resultados

| Piezas | Motor | Mín (s) | p50 / Mediana (s) | p95 (s) | Máx (s) | RSS Pico (MiB) | Colocadas | Planchas | Aprov. % | Motivo de Terminación |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **10** | **FF** | 0.44 | **0.45** | **0.45** | 0.45 | 39.58 | 10/10 | 2 | 24.10% | COMPLETED |
| **10** | **BF** | 0.85 | **0.86** | **0.87** | 0.87 | 40.09 | 10/10 | 2 | 24.10% | COMPLETED |
| **10** | **WF** | 0.76 | **0.77** | **0.79** | 0.79 | 42.46 | 10/10 | 2 | 24.10% | COMPLETED |
| **10** | **HF** | 0.60 | **0.61** | **0.61** | 0.61 | 40.07 | 10/10 | 2 | 24.10% | COMPLETED |
| **10** | **M5** | 1.21 | **1.22** | **1.22** | 1.23 | 42.58 | 10/10 | 2 | 24.10% | COMPLETED |
| **10** | **M6-BS** | 1.95 | **2.03** | **2.10** | 2.11 | 59.43 | 10/10 | 2 | 24.10% | COMPLETED |
| **25** | **FF** | 1.57 | **1.58** | **1.59** | 1.59 | 40.82 | 25/25 | 2 | 60.57% | COMPLETED |
| **25** | **BF** | 8.64 | **8.73** | **8.82** | 8.83 | 43.05 | 25/25 | 2 | 60.57% | COMPLETED |
| **25** | **WF** | 5.30 | **5.48** | **5.68** | 5.70 | 46.24 | 25/25 | 2 | 60.57% | COMPLETED |
| **25** | **HF** | 1.69 | **1.72** | **1.75** | 1.75 | 41.72 | 25/25 | 2 | 60.57% | COMPLETED |
| **25** | **M5** | 23.78 | **23.89** | **23.99** | 24.00 | 46.89 | 25/25 | 2 | 60.57% | COMPLETED |
| **25** | **M6-BS** | 8.40 | **8.69** | **20.47** | 21.78 | 64.54 | 25/25 | 2 | 60.57% | COMPLETED |
| **50** | **FF** | 9.44 | **9.53** | **9.62** | 9.63 | 51.88 | 50/50 | 4 | 60.57% | COMPLETED |
| **50** | **BF** | 34.07 | **38.44** | **42.81** | 43.30 | 54.39 | 50/50 | 4 | 60.57% | COMPLETED |
| **50** | **WF** | 27.34 | **28.44** | **29.54** | 29.66 | 57.39 | 50/50 | 4 | 60.57% | COMPLETED |
| **50** | **HF** | 4.07 | **4.09** | **4.11** | 4.11 | 51.88 | 50/50 | 4 | 60.57% | COMPLETED |
| **50** | **M5** | 19.86 | **19.89** | **19.92** | 19.92 | 57.71 | 50/50 | 4 | 60.57% | COMPLETED |
| **50** | **M6-BS** | 19.08 | **19.16** | **19.24** | 19.25 | 71.56 | 50/50 | 4 | 60.57% | COMPLETED |
| **100** | **FF** | 18.13 | **18.58** | **19.03** | 19.08 | 70.99 | 100/100 | 8 | 59.62% | COMPLETED |
| **100** | **BF** | 60.51 | **61.11** | **61.71** | 61.78 | 73.02 | 100/100 | 8 | 59.62% | COMPLETED |
| **100** | **WF** | 45.51 | **45.70** | **45.89** | 45.91 | 75.16 | 100/100 | 8 | 59.62% | COMPLETED |
| **100** | **HF** | 18.25 | **18.41** | **18.57** | 18.59 | 70.71 | 100/100 | 8 | 59.62% | COMPLETED |
| **100** | **M5** | 85.91 | **86.44** | **86.97** | 87.03 | 76.07 | 100/100 | 8 | 59.62% | COMPLETED |
| **100** | **M6-BS** | 37.90 | **37.91** | **37.92** | 37.92 | 73.59 | 58/100 | 5 | 58.57% | **STATE_MEMORY_LIMIT** |
| **150** | **FF** | 52.40 | **52.84** | **53.28** | 53.33 | 79.21 | 150/150 | 10 | 71.47% | COMPLETED |
| **150** | **BF** | 115.88 | **115.92** | **115.96** | 115.97 | 82.59 | 150/150 | 10 | 71.47% | COMPLETED |
| **150** | **WF** | 85.87 | **92.91** | **99.95** | 100.73 | 84.45 | 150/150 | 10 | 71.47% | COMPLETED |
| **150** | **HF** | 52.70 | **53.00** | **53.30** | 53.33 | 79.83 | 150/150 | 10 | 71.47% | COMPLETED |
| **150** | **M5** | 120.53 | **120.62** | **120.71** | 120.72 | 82.05 | — | — | — | **TIME_BUDGET_EXCEEDED** |
| **150** | **M6-BS** | 111.45 | **111.45** | **256.76** | 272.91 | 73.70 | — | — | — | **TIME_LIMIT** |
| **200** | **FF** | 119.92 | **120.00** | **120.08** | 120.09 | 84.47 | — | — | — | **TIME_BUDGET_EXCEEDED** |
| **200** | **BF** | 120.00 | **120.00** | **120.00** | 120.00 | 67.90 | — | — | — | **TIME_BUDGET_EXCEEDED** |
| **200** | **WF** | 120.01 | **120.02** | **120.03** | 120.03 | 73.04 | — | — | — | **TIME_BUDGET_EXCEEDED** |
| **200** | **HF** | 120.05 | **120.05** | **120.05** | 120.05 | 80.61 | — | — | — | **TIME_BUDGET_EXCEEDED** |
| **200** | **M5** | 119.99 | **120.00** | **120.01** | 120.01 | 69.32 | — | — | — | **TIME_BUDGET_EXCEEDED** |
| **200** | **M6-BS** | 112.65 | **112.75** | **112.85** | 112.86 | 72.80 | 44/200 | 4 | 69.00% | **TIME_LIMIT** |

---

## 4. Tabla Comparativa: Melendez (Corrida Única) vs. QA (p50 / p95)

| Escenario | Motor | Melendez (`S2-WF-CARGA`) | QA p50 (Mediana) | QA p95 | Motivo Melendez | Motivo QA | Diagnóstico Técnico |
|---|---|---:|---:|---:|---|---|---|
| **10 u** | FF | *No medido* | **0.45 s** | **0.45 s** | — | COMPLETED | Escenario inédito; óptima respuesta |
| **10 u** | BF | *No medido* | **0.86 s** | **0.87 s** | — | COMPLETED | Escenario inédito; óptima respuesta |
| **10 u** | WF | *No medido* | **0.77 s** | **0.79 s** | — | COMPLETED | Escenario inédito; óptima respuesta |
| **10 u** | HF | *No medido* | **0.61 s** | **0.61 s** | — | COMPLETED | Escenario inédito; óptima respuesta |
| **10 u** | M5 | *No medido* | **1.22 s** | **1.22 s** | — | COMPLETED | Escenario inédito; óptima respuesta |
| **10 u** | M6-BS | *No medido* | **2.03 s** | **2.10 s** | — | COMPLETED | Escenario inédito; búsqueda completa |
| **25 u** | FF | *No medido* | **1.58 s** | **1.59 s** | — | COMPLETED | Escenario inédito; sub-2s |
| **25 u** | BF | *No medido* | **8.73 s** | **8.82 s** | — | COMPLETED | Escenario inédito; escala normal |
| **25 u** | WF | *No medido* | **5.48 s** | **5.68 s** | — | COMPLETED | Escenario inédito; escala normal |
| **25 u** | HF | *No medido* | **1.72 s** | **1.75 s** | — | COMPLETED | Escenario inédito; sub-2s |
| **25 u** | M5 | *No medido* | **23.89 s** | **23.99 s** | — | COMPLETED | Mayor latencia por holgura exhaustiva |
| **25 u** | M6-BS | *No medido* | **8.69 s** | **20.47 s** | — | COMPLETED | Varianza en p95 por poda de ramas |
| **50 u** | FF | ~4.64 s (en 46u) | **9.53 s** | **9.62 s** | COMPLETED | COMPLETED | Consistente con 46u |
| **50 u** | BF | ~12.12 s (en 46u) | **38.44 s** | **42.81 s** | COMPLETED | COMPLETED | **Peligro Heroku:** supera 30 s |
| **50 u** | WF | ~9.53 s (en 46u) | **28.44 s** | **29.54 s** | COMPLETED | COMPLETED | Roza límite de 30 s |
| **50 u** | HF | ~4.77 s (en 46u) | **4.09 s** | **4.11 s** | COMPLETED | COMPLETED | Más veloz que First Fit |
| **50 u** | M5 | ~93.75 s (en 46u) | **19.89 s** | **19.92 s** | COMPLETED | COMPLETED | **Mejora drástica:** F4b (tramos de columna) |
| **50 u** | M6-BS | 0.00 s (fallo en 46u) | **19.16 s** | **19.24 s** | `STATE_MEMORY_LIMIT` | COMPLETED | **Éxito:** gracias a grafo compartido (F2) |
| **100 u** | FF | 16.61 s | **18.58 s** | **19.03 s** | COMPLETED | COMPLETED | Altamente estable |
| **100 u** | BF | 54.64 s | **61.11 s** | **61.71 s** | COMPLETED | COMPLETED | Supera doblemente timeout HTTP |
| **100 u** | WF | 40.50 s | **45.70 s** | **45.89 s** | COMPLETED | COMPLETED | Supera timeout HTTP |
| **100 u** | HF | 16.47 s | **18.41 s** | **18.57 s** | COMPLETED | COMPLETED | Altamente estable |
| **100 u** | M5 | 120.12 s (Fallo) | **86.44 s** | **86.97 s** | `TIME_BUDGET_EXCEEDED` | COMPLETED | **Mejora:** completa dentro de los 120 s |
| **100 u** | M6-BS | 0.00 s (Fallo) | **37.91 s** | **37.92 s** | `STATE_MEMORY_LIMIT` | `STATE_MEMORY_LIMIT` | Coloca 58/100 y para limpiamente |
| **150 u** | FF | 47.12 s | **52.84 s** | **53.28 s** | COMPLETED | COMPLETED | Completa las 150 piezas |
| **150 u** | BF | 103.81 s | **115.92 s** | **115.96 s** | COMPLETED | COMPLETED | Roza límite de 120 s |
| **150 u** | WF | 81.41 s | **92.91 s** | **99.95 s** | COMPLETED | COMPLETED | Completa las 150 piezas |
| **150 u** | HF | 47.98 s | **53.00 s** | **53.30 s** | COMPLETED | COMPLETED | Completa las 150 piezas |
| **150 u** | M5 | 120.09 s (Fallo) | **120.62 s** | **120.71 s** | `TIME_BUDGET_EXCEEDED` | `TIME_BUDGET_EXCEEDED` | **Frontera de corte:** excede 120 s |
| **150 u** | M6-BS | 0.00 s (Fallo) | **111.45 s** | **256.76 s** | `STATE_MEMORY_LIMIT` | `TIME_LIMIT` | Agota presupuesto de tiempo |
| **200 u** | FF | 67.81 s | **120.00 s** | **120.08 s** | COMPLETED | `TIME_BUDGET_EXCEEDED` | Excede 120 s en esta máquina |
| **200 u** | BF | 120.00 s (Fallo) | **120.00 s** | **120.00 s** | `TIME_BUDGET_EXCEEDED` | `TIME_BUDGET_EXCEEDED` | Excede 120 s |
| **200 u** | WF | 118.66 s | **120.02 s** | **120.03 s** | COMPLETED | `TIME_BUDGET_EXCEEDED` | Excede 120 s |
| **200 u** | HF | 69.03 s | **120.05 s** | **120.05 s** | COMPLETED | `TIME_BUDGET_EXCEEDED` | Excede 120 s |
| **200 u** | M5 | 120.05 s (Fallo) | **120.00 s** | **120.01 s** | `TIME_BUDGET_EXCEEDED` | `TIME_BUDGET_EXCEEDED` | Excede 120 s |
| **200 u** | M6-BS | 0.00 s (Fallo) | **112.75 s** | **112.85 s** | `STATE_MEMORY_LIMIT` | `TIME_LIMIT` | Coloca 44 piezas y agota tiempo |
| **300 u** | Todos | 120.00 s (Fallo) | **>120.00 s** | **>120.00 s** | `TIME_BUDGET_EXCEEDED` | `TIME_BUDGET_EXCEEDED` | **Inviable comercialmente** |

---

## 5. Correlación Técnica con la Telemetría de Heroku

De acuerdo con las capturas de métricas de `newglass-api-staging` en Heroku (Dyno web `1 dyno`, cuota 512 MB):

1. **Eventos `H27` (Client Closed Request):**
   * El enrutador HTTP de Heroku corta forzosamente cualquier conexión abierta que supere los **30 segundos** sin emitir respuesta.
   * Nuestros datos de laboratorio demuestran que a partir de **50 unidades**, Best Fit ya toma **38.44 s**, y a partir de **100 unidades**, Best Fit toma **61.11 s**, Worst Fit toma **45.70 s** y M5 toma **86.44 s**.
   * **Conclusión:** Si un usuario solicita una comparación de más de 50 unidades de forma síncrona contra la API web, Heroku registrará indefectiblemente un error `H27`. La optimización multi-motor debe ejecutarse siempre de forma desacoplada en segundo plano con polling o WebSockets.
2. **Consumo de Memoria y Eventos `R12`:**
   * En Heroku la memoria alcanzó picos de **279 MB (54.5%)**.
   * En nuestras pruebas locales, el RSS máximo por motor individual se situó entre **70 y 84 MiB**.
   * Al ejecutarse los motores de forma secuencial, el consumo de memoria es seguro y no satura la cuota de 512 MB. Los eventos `R12` (Exit timeout) en Heroku se deben al agotamiento de tiempo de los workers al procesar pedidos en cola y no a fallos por memoria fuera de cuota (`OOM`).

---

## 6. Verificación de Criterios de Aceptación (SDD)

| Criterio | Descripción | Estado | Evidencia |
|---|---|:---:|---|
| **CA-01** | Cobertura de escenarios base (10, 25, 50, 100, 150 y 200 unidades) | **PASS** | §3 Matriz Consolidada de Resultados |
| **CA-02** | Obtención de métricas estadísticas p50 (mediana) y p95 con $N \ge 3$ | **PASS** | §3 Matriz Consolidada con 3 repeticiones por punto |
| **CA-03** | Registro del consumo de memoria física residente (RSS pico en MiB) | **PASS** | §3 Muestreo de RSS continuo con `psutil` |
| **CA-04** | Registro exhaustivo del ambiente de ejecución y condiciones de prueba | **PASS** | §2 Especificación de hardware, SO y Python 3.11.9 |
| **CA-05** | Elaboración de tabla comparativa cruzada contra datos de Melendez | **PASS** | §4 Tabla Comparativa de tiempos y motivos |
| **CA-06** | Análisis honesto de cargas mayores (300 y 800) y correlación con Heroku | **PASS** | §1 y §5 Correlación técnica y justificación de límites |

---

## 7. Instrucciones de Reproducción

Para reproducir cualquier medición en Windows, desde la carpeta `backend\` con el entorno activo:

```powershell
# Ejecución completa de la matriz con 3 repeticiones y exportación JSON:
python -m scripts.benchmark_qa_002 --sizes 10 25 50 100 150 200 --runs 3 --output-json ../docs/evidence/sprint-02/TA-QA-002/raw_results.json

# Ejecución de un único escenario (por ejemplo, 50 unidades):
python -m scripts.benchmark_qa_002 --sizes 50 --runs 3
```
