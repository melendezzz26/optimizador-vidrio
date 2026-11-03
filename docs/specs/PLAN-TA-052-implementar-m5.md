# PLAN TA-052 — Implementar heurística M5 en el sistema

1. **T01 — Dominio y Aplicación:**
   - Crear `domain/best_residual_fit.py` con `BestResidualFitSelector`, `BestResidualFitResult` y `BestResidualFitOptimizer`.
   - Crear `application/best_residual_fit.py` con `calculate_best_residual_fit`.
   - Extender `domain/problem.py` para incluir `"M5"` en `Literal["FF", "BF", "WF", "M5"]`.
   - Registrar `BestResidualFitOptimizer` en `application/comparison.py`.

2. **T02 — Pruebas unitarias y evidencia:**
   - Crear `backend/tests/unit/optimization/test_best_residual_fit.py` con batería completa de 16 pruebas.
   - Ejecutar la suite conjunta de M5 (`test_best_residual_fit.py` y `test_sp005_m5.py`), totalizando 27 pruebas.
   - Registrar evidencia en `docs/evidence/sprint-02/TA-052/README.md`.
   - Comprobar ausencia de regresiones con `pytest` y limpieza de diff con `git diff --check`.
