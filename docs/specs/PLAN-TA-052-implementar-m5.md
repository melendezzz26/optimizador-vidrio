# PLAN TA-052 — Implementar heurística M5 en el sistema

Autor: Luis Anthony Ibáñez Herrera

Revisor esperado: Andro Joseph Quispe Cesias (aprobación formal pendiente)

1. **T01 — Dominio y Aplicación:**
   - Crear `domain/best_residual_fit.py` con `BestResidualFitSelector`, `BestResidualFitResult` y `BestResidualFitOptimizer`.
   - Crear `application/best_residual_fit.py` con `calculate_best_residual_fit`.
   - Extender `domain/problem.py` para incluir `"M5"` en `Literal["FF", "BF", "WF", "M5"]`.
   - Exponer M5 en la lista opcional `EXTENDED_METHODS` de `application/comparison.py`; `DEFAULT_METHODS` conserva FF/BF/WF. La conexión pública queda para TA-043.

2. **T02 — Pruebas unitarias y evidencia:**
   - Crear `backend/tests/unit/optimization/test_best_residual_fit.py` con 18 pruebas productivas nuevas de TA-052.
   - Ejecutar `test_best_residual_fit.py` junto con `test_sp005_m5.py`: 29 pruebas en la selección conjunta. Las 11 heredadas de SP-005 aún ejercitan su optimizador experimental, no el motor productivo de TA-052.
   - Registrar evidencia en `docs/evidence/sprint-02/TA-052/README.md`.
   - Comprobar ausencia de regresiones con `pytest` y limpieza de diff con `git diff --check`.
