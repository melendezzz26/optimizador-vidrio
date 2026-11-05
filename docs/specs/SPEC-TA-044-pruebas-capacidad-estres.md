# SPEC-TA-044 — Pruebas de capacidad, estrés, determinismo y concurrencia del optimizador

## Información general

| Campo | Valor |
|---|---|
| Estado | En progreso |
| PBI relacionado | TA-044 (T01, T02, T03) |
| Responsable | Luis Anthony Ibáñez Herrera |
| Revisor esperado | Andro Joseph Quispe Cesias |
| Fecha | 04/11/2026 |
| Versión | 1.0 |

---

## 1. Objetivo

Evaluar y documentar cuantitativamente la capacidad máxima de procesamiento, los límites de estrés operativo, el determinismo funcional y el comportamiento concurrente del motor de optimización de NewGlass al incrementar progresivamente la cantidad de piezas y las ejecuciones simultáneas, estableciendo la línea base empírica de degradación y saturación del sistema.

---

## 2. Alcance

### Incluye:
- **T01 — Diseñar escenarios de capacidad:**
  - Matriz progresiva de prueba reproducible: 10, 25, 50, 75, 100, 150 y 200 piezas.
  - Condiciones de dominio realistas: piezas rectangulares, circulares y polígonos convexos; combinación de tamaños; grupos de materiales compatibles (Tipo 1 de 6mm y Tipo 2 de 8mm); stock mixto con retazos iniciales (`RETAZO`) y planchas estándar (`PLANCHA`).
  - Generador determinista versionado (`experiments/optimization/capacity_scenarios.py`) y casos congelados JSON en `experiments/optimization/cases/capacity/`.
  - Pruebas unitarias de integridad de escenarios (`backend/tests/unit/optimization/test_capacity_scenarios.py`).
- **T02 — Pruebas de capacidad y estrés:**
  - Medición con reloj monotónico (`perf_counter_ns`) y pico de asignaciones Python trazadas por `tracemalloc`, no RAM total.
  - Registro de piezas colocadas/no colocadas, planchas nuevas, retazos aprovechados, merma, utilización y fallos/timeouts.
  - Evaluación sobre los métodos disponibles en el motor: First Fit (FF), Best Fit (BF), Worst Fit (WF), Hole Filling (M4), Best Residual Fit (M5) y Beam Search (M6).
  - Identificación del umbral de degradación por método.
  - Exportación de métricas crudas a JSON y CSV en `docs/evidence/sprint-02/TA-044/`.
- **T03 — Determinismo y concurrencia:**
  - Comparación de huellas de colocaciones en cinco repeticiones de CAP-10 para cada uno de los seis métodos.
  - Sonda de paralelismo del motor con 2, 4 y 8 procesos; sus huellas no prueban aislamiento del servicio.
  - Pruebas del servicio con admisión, rechazo, cancelación, persistencia e inventario sobre PostgreSQL aislado.
  - Registro de resultados en `docs/evidence/sprint-02/TA-044/concurrency_results.json`.
- **Evidencia:** resultados JSON/CSV y resumen versionados.

### Fuera de alcance:
- Carga masiva mediante archivos CSV o Excel (HU-018 - Aguilar).
- Previsualización en frontend de archivos subidos ni filas con estado "OBSERVADO" (HU-018).
- Registro o modificación del coordinador público multimétodo (TA-043).

---

## 3. Actor y precondiciones

- **Actor:** Optimizador / Banco de Pruebas de Capacidad.
- **Precondiciones:**
  - Integración confirmada de M5 (PR #95) en `integration/sprint-01`.
  - Heurísticas FF, BF, WF, M4, M5 y M6 disponibles en `app.modules.optimization.domain`.
  - Entorno de ejecución Python 3.11 con dependencias instaladas.

---

## 4. Entradas y datos

| Parámetro | Tipo | Valores / Rango |
|---|---|---|
| Lotes de piezas ($N$) | int | 10, 25, 50, 75, 100, 150, 200 |
| Formas geométricas | str / dict | `RECTANGULO`, `CIRCUNFERENCIA`, `POLIGONO_CONVEXO` |
| Grupos de material | tuple | (1, 6mm), (2, 8mm) |
| Fuentes de stock | MaterialSource | `RETAZO` (prioridad 1), `PLANCHA` (prioridad 2) |
| Configuración de corte | OptimizationConfig | `resolution_mm=1`, `angular_step_deg=5`, `margin_mm=1`, `separation_mm=1` |

---

## 5. Reglas de negocio e invariantes

- **RN-01 (Reproducibilidad Determinista):** Los escenarios se generan con reglas deterministas, sin aleatoriedad en tiempo de ejecución.
- **RN-02 (Validez Geométrica Real):** No se permiten geometrías sintéticas inválidas ni polígonos no convexos; toda pieza debe validar contra `GeometryValidator`.
- **RN-03 (Compatibilidad de Material):** Ninguna colocación puede mezclar materiales incompatibles entre pieza y stock (`piece.material_key == stock.material_key`).
- **RN-04 (Prioridad Estricta de Retazos):** Los retazos factibles deben consumirse antes de aperturar una plancha nueva (`RETAZO` $\to$ `PLANCHA`).
- **RN-05 (Invariante de Determinismo):** Ante idénticas entradas y configuración, el hash funcional del resultado (`placements`) debe ser 100% idéntico entre ejecuciones sucesivas.
- **RN-06 (Aislamiento Concurrente):** Las solicitudes del servicio deben conservar sus identificadores, eventos, resultados e inventario independientes en los casos probados.

---

## 6. Criterios de aceptación

- **CA-01 (T01 - Escenarios):** Existen 7 archivos JSON congelados (`CAP-10.json` a `CAP-200.json`) y suite de pruebas unitarias verde validando su conformidad de dominio.
- **CA-02 (T01 - Variedad):** Los escenarios combinan rectángulos, círculos, polígonos convexos, dos grupos de materiales y stock mixto (retazos + planchas).
- **CA-03 (T02 - Capacidad):** Se registran tiempo, asignaciones Python trazadas, piezas colocadas/no colocadas, planchas y retazos. Clasificar COMPLETE, PARTIAL, TIMEOUT y ERROR; M6 registra el motivo de parada.
- **CA-04 (T02 - Límites):** Se documenta claramente hasta qué número de piezas cada método opera dentro de límites prácticos y dónde ocurre la degradación.
- **CA-05 (T03 - Determinismo):** Comparar las huellas de cinco ejecuciones CAP-10 por método; no inferir ausencia de fugas de memoria.
- **CA-06 (T03 - Concurrencia):** Distinguir paralelismo del motor de concurrencia del servicio y verificar admisión, rechazo, cancelación, persistencia e inventario.
- **CA-07 (Evidencia):** Resultados y conclusiones deben corresponder a la evidencia versionada.

---

## 7. Impacto técnico

- `experiments/optimization/capacity_scenarios.py` (nuevo)
- `experiments/optimization/cases/capacity/CAP-*.json` (nuevos)
- `backend/tests/unit/optimization/test_capacity_scenarios.py` (nuevo)
- `experiments/optimization/benchmark_capacity.py` (nuevo)
- `experiments/optimization/probe_concurrency_capacity.py` (nuevo)
- `docs/evidence/sprint-02/TA-044/` (nueva carpeta de evidencias y resultados crudos)
