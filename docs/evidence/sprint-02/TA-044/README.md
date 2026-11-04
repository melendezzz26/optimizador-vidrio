# Evidencia TA-044 — Pruebas de capacidad, estrés, determinismo y concurrencia del optimizador

**PBI / Tarea:** TA-044 (T01 — Diseñar escenarios / T02 — Pruebas de capacidad y estrés / T03 — Determinismo y concurrencia)
**Autor:** Luis Anthony Ibáñez Herrera
**Revisor esperado:** Andro Joseph Quispe Cesias / Wilder Fabricio Melendez Quezada
**Fecha:** 04/11/2026
**Entorno:** Windows 11 / Python 3.11.1 / 12 CPUs lógicos
**Base:** `integration/sprint-01` tras merge de M5 (PR #95)

---

## 1. Entrada y configuración

- **Independencia funcional:** Tarea desacoplada de HU-018 (importación CSV/Excel de Aguilar). Entradas generadas programáticamente con semilla fija y casos congelados.
- **Artefactos y módulos creados:**
  - `experiments/optimization/capacity_scenarios.py`: Generador determinista de matriz progresiva (10, 25, 50, 75, 100 piezas).
  - `experiments/optimization/cases/capacity/CAP-*.json`: 5 casos congelados con rectángulos, círculos y polígonos convexos en 2 grupos de material (6mm y 8mm) con stock mixto (retazos y planchas).
  - `backend/tests/unit/optimization/test_capacity_scenarios.py`: 11 pruebas unitarias de validación geométrica y contratos inmutables.
  - `experiments/optimization/benchmark_capacity.py`: Runner formal de capacidad, estrés y cálculo de métricas R4.
  - `experiments/optimization/probe_concurrency_capacity.py`: Sonda de determinismo ($N=5$) y concurrencia multi-proceso (2, 4, 8 workers).
  - `docs/evidence/sprint-02/TA-044/capacity_benchmark_results.csv` y `.json`: Datos crudos del benchmark.
  - `docs/evidence/sprint-02/TA-044/concurrency_results.json`: Datos crudos de determinismo y concurrencia.
  - `Notion/Avance_TA-044_Capacidad_Estres_Concurrencia.docx`: Documento Word formal para Notion con capturas y tablas.

---

## 2. Procedimiento de verificación

### 2.1 Validación unitaria de escenarios (T01)
```powershell
cd backend
python -m pytest tests/unit/optimization/test_capacity_scenarios.py -q -ra
```
**Resultado:** `11 passed in 0.19s` (100% verde).

### 2.2 Benchmark de capacidad y estrés (T02)
```powershell
python experiments/optimization/benchmark_capacity.py
```
**Resultado:** 30 ensayos evaluados sobre FF, BF, WF, M4, M5 y M6.

### 2.3 Verificación de determinismo y concurrencia (T03)
```powershell
python experiments/optimization/probe_concurrency_capacity.py
```
**Resultado:** 25 evaluaciones de determinismo (100% PASS, 1 único hash SHA-256 por caso) y 12 pruebas de concurrencia multi-proceso (100% SUCCESS, 0 colisiones).

---

## 3. Resultado esperado vs. resultado obtenido

### 3.1 T01 — Escenarios de capacidad
- **Esperado:** Entradas reproducibles de 10, 25, 50, 75 y 100 piezas con formas no uniformes (rectángulos, círculos, polígonos convexos), grupos compatibles de material (6mm y 8mm) y stock mixto (retazos + planchas).
- **Obtenido:** 5 archivos JSON generados y congelados en `experiments/optimization/cases/capacity/`. Todas las geometrías validaron positivamente contra `GeometryValidator` y los contratos inmutables de `OptimizationProblem`. **PASS**.

### 3.2 T02 — Capacidad y estrés del motor
- **Esperado:** Medición de tiempo monotónico, memoria pico, colocaciones y umbrales de saturación en los 6 métodos.
- **Obtenido:**
  - **Métodos constructivos (FF, BF, WF, M4, M5):** Soportan 100 piezas sin degradación crítica:
    - FF: 100 piezas en 1.86 s | RAM: 1.17 MB | Colocadas: 100/100 (100%)
    - BF: 100 piezas en 2.88 s | RAM: 1.19 MB | Colocadas: 100/100 (100%)
    - WF: 100 piezas en 1.94 s | RAM: 1.24 MB | Colocadas: 100/100 (100%)
    - M4: 100 piezas en 1.92 s | RAM: 1.17 MB | Colocadas: 100/100 (100%)
    - M5: 100 piezas en 2.36 s | RAM: 1.23 MB | Colocadas: 100/100 (100%)
  - **Método de búsqueda en árbol (M6 Beam Search):** Funciona al 100% hasta 25 piezas (26.8 s). En 50, 75 y 100 piezas se detiene por límite de tiempo de búsqueda (30.0 s) produciendo colocaciones parciales (14, 10 y 7 piezas colocadas respectivamente). Este límite queda caracterizado. **PASS**.

### 3.3 T03 — Determinismo y concurrencia
- **Esperado:** Idéntico resultado funcional ante misma entrada (0 drift). En concurrencia, ausencia de saturación bloqueante, sin corrupción de memoria y medición del factor de ralentización.
- **Obtenido:**
  - **Determinismo:** En 5 repeticiones consecutivas para todos los métodos y casos, el fingerprint SHA-256 de los placements fue idéntico en el 100% de las corridas. **PASS**.
  - **Concurrencia:** Con 2, 4 y 8 procesos paralelos sobre 12 núcleos lógicos, todas las ejecuciones completaron con éxito (`all_success = True`), sin corrupción de memoria (`no_interference_hash_match = True`). El throughput escaló hasta 16.32 ops/s con un factor de ralentización de solo 1.32x en FF y 1.77x en M5 bajo 8 workers concurrentes. **PASS**.

---

## 4. Tabla consolidada de capacidad y estrés (Extracto T02)

| Caso | Piezas | Método | Estado | Tiempo (ms) | RAM Pico (MB) | Colocadas | Planchas | Retazos | Utiliz. % |
|---|---|---|---|---|---|---|---|---|---|
| CAP-10 | 10 | FF | SUCCESS | 244.5 | 0.762 | 10/10 | 2 | 3 | 15.6% |
| CAP-10 | 10 | BF | SUCCESS | 262.4 | 0.641 | 10/10 | 2 | 3 | 15.6% |
| CAP-10 | 10 | M5 | SUCCESS | 271.6 | 0.633 | 10/10 | 4 | 3 | 9.2% |
| CAP-10 | 10 | M6 | SUCCESS | 5745.1 | 1.625 | 10/10 | 2 | 3 | 15.6% |
| CAP-25 | 25 | FF | SUCCESS | 386.1 | 0.820 | 25/25 | 4 | 3 | 23.5% |
| CAP-25 | 25 | M5 | SUCCESS | 490.1 | 0.789 | 25/25 | 12 | 3 | 8.9% |
| CAP-25 | 25 | M6 | SUCCESS | 26844.6 | 2.821 | 25/25 | 4 | 3 | 23.5% |
| CAP-50 | 50 | FF | SUCCESS | 763.5 | 1.165 | 50/50 | 6 | 3 | 33.6% |
| CAP-50 | 50 | M5 | SUCCESS | 932.6 | 1.153 | 50/50 | 26 | 3 | 8.4% |
| CAP-50 | 50 | M6 | PARTIAL | 30002.6 | 0.751 | 14/50 | 2 | 2 | 30.1% |
| CAP-100 | 100 | FF | SUCCESS | 1863.4 | 1.169 | 100/100 | 11 | 3 | 38.4% |
| CAP-100 | 100 | BF | SUCCESS | 2877.2 | 1.189 | 100/100 | 11 | 3 | 38.4% |
| CAP-100 | 100 | M4 | SUCCESS | 1918.2 | 1.170 | 100/100 | 11 | 3 | 38.4% |
| CAP-100 | 100 | M5 | SUCCESS | 2364.6 | 1.233 | 100/100 | 53 | 3 | 8.3% |
| CAP-100 | 100 | M6 | PARTIAL | 30001.7 | 0.303 | 7/100 | 1 | 2 | 25.1% |

---

## 5. Tabla consolidada de concurrencia multi-proceso (Extracto T03)

| Caso | Método | Workers | Estado | Wall Time (ms) | Avg Worker (ms) | Slowdown | Throughput (ops/s) |
|---|---|---|---|---|---|---|---|
| CAP-25 | FF | 2 | SUCCESS | 381.7 | 53.9 | 1.05x | 5.24 |
| CAP-25 | FF | 4 | SUCCESS | 347.1 | 55.2 | 1.08x | 11.52 |
| CAP-25 | FF | 8 | SUCCESS | 490.1 | 67.3 | 1.32x | 16.32 |
| CAP-25 | M5 | 2 | SUCCESS | 309.8 | 69.1 | 1.10x | 6.46 |
| CAP-25 | M5 | 4 | SUCCESS | 383.1 | 71.9 | 1.15x | 10.44 |
| CAP-25 | M5 | 8 | SUCCESS | 946.9 | 110.8 | 1.77x | 8.45 |
| CAP-50 | FF | 4 | SUCCESS | 695.3 | 207.9 | 1.39x | 5.75 |
| CAP-50 | FF | 8 | SUCCESS | 856.6 | 237.2 | 1.59x | 9.34 |
| CAP-50 | M5 | 4 | SUCCESS | 908.8 | 214.0 | 1.43x | 4.40 |
| CAP-50 | M5 | 8 | SUCCESS | 1326.6 | 308.2 | 2.06x | 6.03 |

---

## 6. Conclusión técnica

El motor de optimización de NewGlass responde con robustez empírica a la pregunta de capacidad:
1. **Límite de capacidad constructiva:** Los algoritmos FF, BF, WF, M4 y M5 procesan 100 piezas complejas en menos de 3 segundos con 100% de colocación, memoria contenida en ~1.2 MB y respeto estricto de la prioridad `RETAZO` $\to$ `PLANCHA`.
2. **Límite de búsqueda exploratoria (M6):** Demuestra su límite práctico en $\sim 25$ piezas bajo su umbral de 30 segundos. Más allá de ese punto, su uso requiere partición previa de lotes o aumento de presupuestos computacionales.
3. **Determinismo y Concurrencia:** Invariante de hash comprobado (0 drift) y ausencia total de interferencias o fugas de memoria en procesamiento concurrente de hasta 8 workers paralelos.
4. **Evidencia para Notion:** El reporte completo con capturas de visual/terminal, tablas y código queda almacenado en `Notion/Avance_TA-044_Capacidad_Estres_Concurrencia.docx`.
