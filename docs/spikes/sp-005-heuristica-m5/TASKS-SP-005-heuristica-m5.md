# TASKS-SP-005 — Investigación y cierre M5

**Autor:** Luis Anthony Ibáñez Herrera
**Revisor asignado:** Andro Joseph Quispe Cesias
**PR:** #93 · **Rama:** `spike/SP-005-heuristica-m5`
**Estado general:** revisión formal pendiente

| ID | Tarea | Estado | Evidencia |
|---|---|---|---|
| SP005-01 | Definir la adaptación M5 y su score de residual | Completada | [SPEC](SPEC-SP-005-heuristica-m5.md), `experimento_m5.py` |
| SP005-02 | Auditar discrepancia notebook vs. CSV/JSON y comparar fixtures con TA-027 | Completada | [REVIEW](REVIEW-SP-005-heuristica-m5.md) |
| SP005-03 | Ejecutar FF/BF/WF/M5 tres veces por caso con el runner y motor oficiales | Completada; 12/12 combinaciones deterministas | [CSV](resultados/resultados_baseline_vs_m5.csv), [JSON](resultados/resumen_comparativo.json) |
| SP005-04 | Añadir pruebas M5 y regresión de geometría, colocación y métricas | Completada; M5 11 passed; regresión dirigida (incluye M5) 367 passed | [test_sp005_m5.py](../../../backend/tests/unit/optimization/test_sp005_m5.py) |
| SP005-05 | Alinear documentación, notebook, resultados y decisión | Completada | [README de evidencia](../../evidence/sprint-02/SP-005/README.md) |
| SP005-06 | Revisión formal independiente de Andro Joseph Quispe Cesias | Pendiente | No hay revisión ni aprobación registrada en PR #93 |

SP005-06 es el único pendiente. No debe marcarse como completado ni usarse esta auditoría técnica como sustituto de la aprobación del revisor asignado.
