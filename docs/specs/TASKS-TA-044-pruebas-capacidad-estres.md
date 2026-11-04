# TASKS TA-044 — Pruebas de capacidad, estrés, determinismo y concurrencia

Autor: Luis Anthony Ibáñez Herrera
Revisor esperado: Andro Joseph Quispe Cesias / Wilder Fabricio Melendez Quezada

- [x] **T01 — Diseñar escenarios de capacidad**
  - [x] Implementar generador reproducible en `experiments/optimization/capacity_scenarios.py`.
  - [x] Generar y congelar casos `CAP-10.json`, `CAP-25.json`, `CAP-50.json`, `CAP-75.json`, `CAP-100.json`.
  - [x] Crear suite de pruebas unitarias `backend/tests/unit/optimization/test_capacity_scenarios.py`.
  - [x] Validar 100% verde en pytest (11 passed in 0.19s).
  - [x] Registrar avance y capturas en el documento Word de Notion.
- [x] **T02 — Pruebas de capacidad y estrés**
  - [x] Implementar runner de benchmark `experiments/optimization/benchmark_capacity.py`.
  - [x] Medir métricas de tiempo, memoria, colocaciones y stock para 10, 25, 50, 75 y 100 piezas en métodos disponibles (FF, BF, WF, M4, M5, M6).
  - [x] Exportar resultados a `docs/evidence/sprint-02/TA-044/capacity_benchmark_results.json` y `.csv`.
  - [x] Identificar umbrales de saturación y degradación (M6 se degrada en 50+ piezas por límite de tiempo; FF/BF/WF/M4/M5 escalan a 100 piezas en <3s).
  - [x] Registrar avance, tablas y capturas en el documento Word de Notion.
- [x] **T03 — Determinismo y concurrencia**
  - [x] Verificar invariante de determinismo ($N=5$) con cálculo de fingerprint SHA-256 de placements (100% coincidencia, 0 drift).
  - [x] Implementar sonda de concurrencia `experiments/optimization/probe_concurrency_capacity.py` (2, 4 y 8 procesos).
  - [x] Medir degradación de rendimiento y verificar ausencia de interferencia (100% éxito, throughput hasta 16.32 ops/s).
  - [x] Exportar datos a `docs/evidence/sprint-02/TA-044/concurrency_results.json`.
  - [x] Registrar avance, análisis y capturas en el documento Word de Notion.
- [x] **Cierre y Consolidación**
  - [x] Generar reporte final en `docs/evidence/sprint-02/TA-044/README.md`.
  - [x] Actualizar estado de `SPEC-TA-044` a `Verified`.
  - [x] Completar documento Word en `Notion/Avance_TA-044_Capacidad_Estres_Concurrencia.docx`.
