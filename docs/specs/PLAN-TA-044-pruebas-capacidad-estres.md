# PLAN TA-044 — Pruebas de capacidad, estrés, determinismo y concurrencia del optimizador

Autor: Luis Anthony Ibáñez Herrera
Revisor esperado: Andro Joseph Quispe Cesias / Wilder Fabricio Melendez Quezada
Fecha: 04/11/2026

---

## 1. T01 — Diseñar escenarios de capacidad
1. Crear el generador determinista `experiments/optimization/capacity_scenarios.py` que soporte:
   - Tamaños de lote: 10, 25, 50, 75 y 100 piezas.
   - Variedad geométrica equilibrada: rectángulos variados, circunferencias y polígonos convexos.
   - Compatibilidad de materiales: dos grupos (Tipo 1 / 6mm y Tipo 2 / 8mm).
   - Fuentes de material: retazos pequeños/medianos disponibles (`RETAZO`) y planchas estándar (`PLANCHA`).
2. Exportar los escenarios congelados a `experiments/optimization/cases/capacity/CAP-*.json`.
3. Implementar suite de pruebas `backend/tests/unit/optimization/test_capacity_scenarios.py` para asegurar que todos los casos cumplen las reglas geométricas y de dominio.

---

## 2. T02 — Pruebas de capacidad y estrés
1. Diseñar el runner de benchmark `experiments/optimization/benchmark_capacity.py` para medir de forma estricta:
   - Tiempo de ejecución con `time.perf_counter_ns`.
   - Memoria pico mediante `tracemalloc`.
   - Placements realizados, no colocados, utilización porcentual, planchas y retazos consumidos.
2. Ejecutar los métodos de optimización (FF, BF, WF, M4, M5, M6) sobre la escala progresiva.
3. Analizar y documentar el punto de inflexión donde el costo computacional se dispara o se alcanza algún límite técnico.
4. Exportar resultados tabulados en formato CSV y JSON a `docs/evidence/sprint-02/TA-044/`.

---

## 3. T03 — Determinismo y concurrencia
1. Evaluar determinismo repitiendo 5 veces cada escenario y comparando el fingerprint canónico de cada resultado (`placements`, orientaciones y coordenadas).
2. Evaluar concurrencia con `experiments/optimization/probe_concurrency_capacity.py` ejecutando 2, 4 y 8 procesos en paralelo sobre un pool de multiprocessing.
3. Medir interferencia de memoria, estabilidad de procesos y factor de ralentización bajo saturación.
4. Exportar métricas de concurrencia a `docs/evidence/sprint-02/TA-044/concurrency_results.json`.

---

## 4. Consolidación y Documentación para Notion
1. Consolidar el documento Word `Notion/Avance_TA-044_Capacidad_Estres_Concurrencia.docx` incorporando el resumen ejecutivo, subtítulos de cada cambio/prueba, fragmentos de código, tablas comparativas y capturas de ejecución.
2. Generar el reporte formal de auditoría en `docs/evidence/sprint-02/TA-044/README.md`.
