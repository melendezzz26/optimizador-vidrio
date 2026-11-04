# SPEC-TA-044 — Pruebas de capacidad, estrés, determinismo y concurrencia del optimizador

## Información general

| Campo | Valor |
|---|---|
| Estado | Verified |
| PBI relacionado | TA-044 (T01, T02, T03) |
| Responsable | Luis Anthony Ibáñez Herrera |
| Reviewer | Andro Joseph Quispe Cesias / Wilder Fabricio Melendez Quezada |
| Fecha | 04/11/2026 |
| Versión | 1.0 |

---

## 1. Objetivo

Evaluar y documentar cuantitativamente la capacidad máxima de procesamiento, los límites de estrés operativo, el determinismo funcional y el comportamiento concurrente del motor de optimización de NewGlass al incrementar progresivamente la cantidad de piezas y las ejecuciones simultáneas, estableciendo la línea base empírica de degradación y saturación del sistema.

---

## 2. Alcance

### Incluye:
- **T01 — Diseñar escenarios de capacidad:**
  - Matriz progresiva de prueba reproducible: 10, 25, 50, 75 y 100 piezas.
  - Condiciones de dominio realistas: piezas rectangulares, circulares y polígonos convexos; combinación de tamaños; grupos de materiales compatibles (Tipo 1 de 6mm y Tipo 2 de 8mm); stock mixto con retazos iniciales (`RETAZO`) y planchas estándar (`PLANCHA`).
  - Generador determinista versionado (`experiments/optimization/capacity_scenarios.py`) y casos congelados JSON en `experiments/optimization/cases/capacity/`.
  - Pruebas unitarias de integridad de escenarios (`backend/tests/unit/optimization/test_capacity_scenarios.py`).
- **T02 — Pruebas de capacidad y estrés:**
  - Medición cuantitativa con reloj monotónico (`perf_counter_ns`) y memoria pico (`tracemalloc`).
  - Registro de piezas colocadas/no colocadas, planchas nuevas, retazos aprovechados, merma, utilización y fallos/timeouts.
  - Evaluación sobre los métodos disponibles en el motor: First Fit (FF), Best Fit (BF), Worst Fit (WF), Hole Filling (M4), Best Residual Fit (M5) y Beam Search (M6).
  - Identificación del umbral de degradación por método.
  - Exportación de métricas crudas a JSON y CSV en `docs/evidence/sprint-02/TA-044/`.
- **T03 — Determinismo y concurrencia:**
  - Verificación de determinismo funcional ($N=5$ repeticiones): comprobación de huella hash exacta (placement fingerprint) en todas las corridas.
  - Pruebas de concurrencia multi-proceso (2, 4 y 8 procesos simultáneos): medición de tasa de completitud, degradación de latencia, contención de CPU y verificación de no interferencia.
  - Registro de resultados en `docs/evidence/sprint-02/TA-044/concurrency_results.json`.
- **Documentación de Avances para Notion:**
  - Generación del documento Word estructurado en `Notion/Avance_TA-044_Capacidad_Estres_Concurrencia.docx` con subtítulos descriptivos, código fuente, tablas y capturas de terminal.

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
| Lotes de piezas ($N$) | int | 10, 25, 50, 75, 100 |
| Formas geométricas | str / dict | `RECTANGULO`, `CIRCUNFERENCIA`, `POLIGONO_CONVEXO` |
| Grupos de material | tuple | (1, 6mm), (2, 8mm) |
| Fuentes de stock | MaterialSource | `RETAZO` (prioridad 1), `PLANCHA` (prioridad 2) |
| Configuración de corte | OptimizationConfig | `resolution_mm=1`, `angular_step_deg=5`, `margin_mm=0`, `separation_mm=0` |

---

## 5. Reglas de negocio e invariantes

- **RN-01 (Reproducibilidad Determinista):** Todo escenario generado debe derivar de una semilla fija (`seed`) y reglas algorítmicas canónicas, sin aleatoriedad flotante en tiempo de ejecución.
- **RN-02 (Validez Geométrica Real):** No se permiten geometrías sintéticas inválidas ni polígonos no convexos; toda pieza debe validar contra `GeometryValidator`.
- **RN-03 (Compatibilidad de Material):** Ninguna colocación puede mezclar materiales incompatibles entre pieza y stock (`piece.material_key == stock.material_key`).
- **RN-04 (Prioridad Estricta de Retazos):** Los retazos factibles deben consumirse antes de aperturar una plancha nueva (`RETAZO` $\to$ `PLANCHA`).
- **RN-05 (Invariante de Determinismo):** Ante idénticas entradas y configuración, el hash funcional del resultado (`placements`) debe ser 100% idéntico entre ejecuciones sucesivas.
- **RN-06 (Aislamiento Concurrente):** Las optimizaciones paralelas no comparten memoria mutable de layouts ni caches de rasterizado; no hay efectos colaterales entre workers.

---

## 6. Criterios de aceptación

- **CA-01 (T01 - Escenarios):** Existen 5 archivos JSON congelados (`CAP-10.json` a `CAP-100.json`) y suite de pruebas unitarias verde validando su conformidad de dominio.
- **CA-02 (T01 - Variedad):** Los escenarios combinan rectángulos, círculos, polígonos convexos, dos grupos de materiales y stock mixto (retazos + planchas).
- **CA-03 (T02 - Capacidad):** Se registran tiempo (ms), memoria pico (MB), piezas colocadas/no colocadas, planchas y retazos para cada lote y método analizado.
- **CA-04 (T02 - Límites):** Se documenta claramente hasta qué número de piezas cada método opera dentro de límites prácticos y dónde ocurre la degradación.
- **CA-05 (T03 - Determinismo):** 5 ejecuciones consecutivas del mismo caso y método generan idéntico fingerprint funcional (0 drift).
- **CA-06 (T03 - Concurrencia):** Pruebas con 2, 4 y 8 procesos concurrentes demuestran 100% de finalizaciones exitosas y documentan el factor de degradación por concurrencia.
- **CA-07 (Evidencia Notion):** Documento Word en `Notion/Avance_TA-044_Capacidad_Estres_Concurrencia.docx` generado con evidencia visual, código y tablas.

---

## 7. Impacto técnico

- `experiments/optimization/capacity_scenarios.py` (nuevo)
- `experiments/optimization/cases/capacity/CAP-*.json` (nuevos)
- `backend/tests/unit/optimization/test_capacity_scenarios.py` (nuevo)
- `experiments/optimization/benchmark_capacity.py` (nuevo)
- `experiments/optimization/probe_concurrency_capacity.py` (nuevo)
- `docs/evidence/sprint-02/TA-044/` (nueva carpeta de evidencias y resultados crudos)
- `Notion/Avance_TA-044_Capacidad_Estres_Concurrencia.docx` (nuevo reporte Word para Notion)
