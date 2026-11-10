# SPEC-TA-QA-002 — Rendimiento y Carga

## Información general

| Campo | Valor |
|---|---|
| ID | TA-QA-002 |
| Tarea | Rendimiento y Carga de Motores de Optimización |
| Sprint | Sprint 2 |
| Prioridad / Tipo | Alta / QA & Rendimiento |
| Estado | **Verified** (Mediciones completadas, tabuladas y verificadas contra CA-01 a CA-06) |
| Responsable | Luis Anthony Ibañez Herrera |
| Reviewer | Fabricio Melendez Quezada |
| Rama | `qa/TA-QA-002-rendimiento-carga` |
| Base | `integration-02` en commit `b964b2b` |
| Fecha de inicio | 09/11/2026 |
| Dependencias | `backend/scripts/benchmark_load_engines.py`, SPEC-TA-019 v2, SPEC-TA-037 v1.4, SPEC-TA-043 |
| Evidencia | [`docs/evidence/sprint-02/TA-QA-002/README.md`](../evidence/sprint-02/TA-QA-002/README.md) y [`Notion/TA-QA-002/Evidencia_Notion_TA-QA-002.docx`](../../../../Notion/TA-QA-002/Evidencia_Notion_TA-QA-002.docx) |

---

## 1. Objetivo

Evaluar y cuantificar de manera controlada, reproducible y estadísticamente representativa el tiempo de respuesta, consumo de memoria física residente (RSS) y estabilidad/causas de error de los seis motores de optimización vigentes (`FF`, `BF`, `WF`, `HF`, `M5`, `M6-BS`):

1. Medir el comportamiento bajo cargas escalonadas de **10, 25, 50, 100, 150 y 200 unidades físicas**.
2. Obtener métricas estadísticas formales de **mediana (p50)** y **percentil 95 (p95)** mediante múltiples iteraciones ($N \ge 3$), superando las mediciones de corrida única históricas.
3. Evaluar de forma transparente los límites de frontera en cargas mayores (**300 unidades comerciales** y referencia de **800 unidades académicas reducidas**), documentando causas de fallo sin atribuir capacidades no demostradas.
4. Contrastar los resultados en tablas comparativas frente a las mediciones previas de Melendez (`S2-WF-CARGA`).
5. Correlacionar los hallazgos técnicos del cuello de botella en **rasterización** con la telemetría en vivo del dyno web de Heroku (`newglass-api-staging`), explicando las causas de los eventos de corte `H27` y `R12`.

---

## 2. Alcance

### Incluye
* Escenarios controlados de **10, 25, 50, 100, 150 y 200 unidades** con piezas geométricas mixtas (rectángulos, círculos, pentágonos convexos) con resolución de 1 mm, separación y margen de 3 mm, y paso angular de 5°.
* Ejecución aislada por motor y proceso (`spawn`) para evitar contaminación de memoria o bloqueos por GIL.
* Medición de tiempos de reloj (`wall-clock`), memoria RSS pico (MiB) mediante muestreo con `psutil`, y diagnóstico de terminación.
* Cálculo de percentiles **p50** y **p95** por motor y escenario.
* Registro exhaustivo del ambiente de pruebas (Windows 11, hardware, Python 3.11.9, commit `b964b2b`).
* Construcción de tablas comparativas contra la corrida única previa de Melendez.
* Registro de evidencias continuas para Notion y compilación en documento Word (`.docx`).

### Fuera de alcance
* Modificar los algoritmos de optimización o heurísticas internas de los motores.
* Alterar los límites de tiempo de producción (120 s de cálculo por motor, 900 s global).
* Alterar inventario real en base de datos PostgreSQL de producción o staging.

---

## 3. Actor y Precondiciones

* **Actor:** Ingeniero de QA / Automatización de Pruebas.
* **Precondiciones:**
  1. Repositorio en rama aislada `qa/TA-QA-002-rendimiento-carga`.
  2. Intérprete Python 3.11.9 con librerías del proyecto instaladas (`numpy`, `pydantic`, `psutil`).
  3. Máquina sin cargas pesadas concurrentes para evitar ruido en la medición de tiempos.

---

## 4. Entradas y Configuración Geométrica

El lote de prueba utiliza la definición canónica del proyecto (`scripts/benchmark_comparison.py`):
* **Piezas geométricas (rotación a 5°):**
  - Rectángulos: $600 \times 800\text{ mm}$ ($480\,000\text{ mm}^2$).
  - Círculos: radio $260\text{ mm}$ ($\approx 212\,371.66\text{ mm}^2$).
  - Pentágonos convexos: $(0,0), (500,0), (620,400), (250,700), (0,400)$ ($317\,000\text{ mm}^2$).
* **Distribución de materiales:** 2 grupos de vidrio independientes de $6\text{ mm}$ ($N/2$ piezas cada uno).
* **Planchas de stock:** Dimensiones $2140 \times 3300\text{ mm}$ ($7\,062\,000\text{ mm}^2$), asignadas con la regla $S(n) = \max(4, \min(50, n))$.
* **Parámetros operativos:** Resolución $1\text{ mm}$, margen $3\text{ mm}$, separación $3\text{ mm}$, paso angular $5^\circ$ ($72$ orientaciones).

---

## 5. Reglas de Negocio y Técnicas (RN)

* **RN-01 (Muestreo e Inferencia Estadística):** Para cada escenario $U \in \{10, 25, 50, 100, 150, 200\}$ se ejecutan $N \ge 3$ repeticiones idénticas. El percentil 50 ($\text{p50}$) corresponde a la mediana exacta y el percentil 95 ($\text{p95}$) se calcula con interpolación lineal estándar.
* **RN-02 (Aislamiento de Procesos y Límite de Tiempo):** Cada ejecución de motor se lanza en un subproceso exclusivo (`spawn`). Cada motor dispone de un límite estricto de **120 s de cálculo** (`DEFAULT_COMPARISON_BUDGET.calculation_seconds`). Si no concluye en 120 s, emite `TimeBudgetExceeded` y termina con `TIME_BUDGET_EXCEEDED`. El supervisor detiene el proceso a los $30\text{ s} + 120\text{ s} = 150\text{ s}$.
* **RN-03 (Muestreo de Memoria RSS):** Se monitorea periódicamente la memoria física residente (`rss`) del proceso hijo mediante `psutil.Process.memory_info()`, registrando el valor pico en MiB.
* **RN-04 (Honestidad Técnica en Cargas Mayores):** Si una carga $\ge 200$ o $300$ unidades supera los 120 s de cálculo o el espacio de memoria, se registra con su causa explícita de terminación. Está estrictamente prohibido declarar soporte comercial de cargas que no completaron exitosamente.
* **RN-05 (Cuello de Botella en Rasterización):** La búsqueda de orígenes libres en la matriz raster de $1\text{ mm}$ con 72 orientaciones por pieza representa el mayor costo de CPU (`SheetLayout.first_position`). Se debe documentar cómo este factor escala con la cantidad de piezas y planchas.
* **RN-06 (Correlación con Heroku):** El análisis de resultados debe contrastarse con los registros del dyno web de Heroku (`newglass-api-staging`, cuota 512 MB), evidenciando que cálculos síncronos superiores a 30 s disparan el corte del enrutador HTTP (`H27` / `R12`).

---

## 6. Criterios de Aceptación (CA)

* **CA-01 (Cobertura de Escenarios Requeridos):** Se ejecutan y documentan de forma completa los 6 escenarios base: **10, 25, 50, 100, 150 y 200 unidades**, para los 6 motores (`FF`, `BF`, `WF`, `HF`, `M5`, `M6-BS`).
* **CA-02 (Métricas Estadísticas p50 y p95):** Se obtienen y tabulan formalmente los percentiles p50 y p95 de tiempo de respuesta mediante repeticiones controladas.
* **CA-03 (Consumo de Memoria):** Se registra y tabula el consumo de memoria RSS pico (MiB) para cada motor y escenario.
* **CA-04 (Registro de Ambiente y Condiciones):** Se especifica el entorno completo (Windows 11, hardware, Python 3.11.9, commit `b964b2b`, parámetros de resolución y rotación).
* **CA-05 (Tabla Comparativa vs. Melendez):** Se elabora una tabla comparativa que contraste las mediciones estadísticas de QA frente a la medición previa de una sola corrida de Melendez (`S2-WF-CARGA`).
* **CA-06 (Análisis de Cargas Mayores y Heroku):** Se documentan las limitaciones en 300 unidades y se explica la correlación con la saturación por rasterización y los errores `H27` de Heroku.

---

## 7. Evidencias Requeridas

1. Script reproducible de benchmark estadístico: `backend/scripts/benchmark_qa_002.py`.
2. Archivo de resultados brutos en JSON: `docs/evidence/sprint-02/TA-QA-002/raw_results.json`.
3. Reporte formal de evidencia en Markdown: `docs/evidence/sprint-02/TA-QA-002/README.md`.
4. Documentación visual y capturas para Notion: `Notion/TA-QA-002/Evidencia_Notion_TA-QA-002.docx` e imágenes en `Notion/TA-QA-002/img/`.

---

## Historial de Estado

* **2026-11-09:** *Draft* — Creado bajo metodología SDD.
* **2026-11-09:** *In-Progress* — Aprobado para ejecución de mediciones.
* **2026-11-10:** *Verified* — Batería ejecutada (10 a 200 u), p50/p95 calculados, tablas comparativas elaboradas y CA-01 a CA-06 verificados.
