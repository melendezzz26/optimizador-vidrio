# TASKS-TA-QA-002 — Desglose de Tareas de Rendimiento y Carga

| Tarea | Descripción | Responsable | Estado |
|---|---|---|---|
| **T01** | Redacción de `SPEC-TA-QA-002` y `PLAN-TA-QA-002` bajo metodología SDD | Luis Anthony Ibañez Herrera | [x] Completado |
| **T02** | Implementación del arnés `backend/scripts/benchmark_qa_002.py` con percentiles y memoria | Luis Anthony Ibañez Herrera | [x] Completado |
| **T03** | Ejecución de la matriz base (10, 25, 50, 100, 150 y 200 unidades) con repeticiones controladas | Luis Anthony Ibañez Herrera | [x] Completado |
| **T04** | Ejecución de frontera de capacidad (300 unidades y referencia 800 unidades) y registro de límites | Luis Anthony Ibañez Herrera | [x] Completado |
| **T05** | Construcción de tablas comparativas (QA p50/p95 vs. Melendez) y análisis de telemetría Heroku | Luis Anthony Ibañez Herrera | [x] Completado |
| **T06** | Generación de evidencia formal en `docs/evidence/sprint-02/TA-QA-002/`, compilación en Word y cierre SDD | Luis Anthony Ibañez Herrera | [x] Completado |

---

## Detalle y Checklist de Criterios

### T01 — Especificación Formal SDD
- [x] Crear rama de trabajo `qa/TA-QA-002-rendimiento-carga` desde `integration-02`.
- [x] Definir reglas de negocio (RN-01 a RN-06) con muestreo estadístico y honestidad técnica.
- [x] Definir criterios de aceptación medibles (CA-01 a CA-06).
- [x] Elaborar plan de mitigación de riesgos de medición.

### T02 — Arnés de Medición Estadística (`benchmark_qa_002.py`)
- [x] Adaptar problema geométrico sintético canónico (rectángulos, círculos, pentágonos a 5°).
- [x] Implementar soporte para iteraciones configurables (`--runs N`).
- [x] Integrar cálculo de mediana ($\text{p50}$) y percentil 95 ($\text{p95}$).
- [x] Integrar monitoreo de memoria física residente (RSS pico en MiB) con `psutil`.
- [x] Asegurar compatibilidad en Windows con subprocesos `spawn`.

### T03 — Ejecución del Lote Base (10 a 200 unidades)
- [x] Ejecutar mediciones para 10 unidades ($N \ge 3$).
- [x] Ejecutar mediciones para 25 unidades ($N \ge 3$).
- [x] Ejecutar mediciones para 50 unidades ($N \ge 3$).
- [x] Ejecutar mediciones para 100 unidades ($N \ge 3$).
- [x] Ejecutar mediciones para 150 unidades ($N \ge 3$).
- [x] Ejecutar mediciones para 200 unidades ($N \ge 3$).
- [x] Exportar resultados crudos a `raw_results.json`.

### T04 — Cargas Mayores y Análisis de Límites
- [x] Evaluar 300 unidades y confirmar comportamiento frente al límite de 120 s.
- [x] Contrastar contra el escenario de 800 unidades académicas reducidas.
- [x] Documentar técnicamente por qué la rasterización condiciona el escalamiento.

### T05 — Tablas Comparativas y Análisis de Heroku
- [x] Tabular tiempos p50 y p95 frente a la corrida única de Melendez.
- [x] Tabular consumos de memoria RSS pico por motor y escala.
- [x] Correlacionar tiempos observados con los errores H27 y R12 del dyno web de Heroku.

### T06 — Cierre Documental y Entrega
- [x] Redactar `docs/evidence/sprint-02/TA-QA-002/README.md`.
- [x] Compilar informe final en Word con capturas para Notion (`Evidencia_Notion_TA-QA-002.docx`).
- [x] Actualizar estado de `SPEC-TA-QA-002` a `Verified`.
- [x] Realizar commit documental en la rama de trabajo.
