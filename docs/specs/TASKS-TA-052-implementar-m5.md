# TASKS TA-052 — Implementar heurística M5

Autor: Luis Anthony Ibáñez Herrera

Revisor esperado: Andro Joseph Quispe Cesias (aprobación formal pendiente)

- [x] T01: Crear módulo de dominio `domain/best_residual_fit.py`.
- [x] T01: Crear módulo de aplicación `application/best_residual_fit.py`.
- [x] T01: Extender tipo `method` en `domain/problem.py` para incluir `"M5"`.
- [x] T01: Exponer M5 en `EXTENDED_METHODS` de `application/comparison.py`; `DEFAULT_METHODS` sigue con FF/BF/WF y el registro público queda para TA-043.
- [x] T02: Crear `tests/unit/optimization/test_best_residual_fit.py` (18 pruebas productivas nuevas de TA-052 pasando).
- [x] T02: Verificar `tests/unit/optimization/test_sp005_m5.py` (11 pruebas heredadas pasando; aún ejercitan el optimizador experimental de SP-005). Selección conjunta: 29 pruebas, no 29 pruebas productivas directas.
- [x] T02: Comprobar las regresiones portables relacionadas y registrar por separado la limitación de `test_comparison_runner.py` en Windows; CI backend en Linux PASS.
- [x] T02: Registrar evidencia reproducible en `docs/evidence/sprint-02/TA-052/README.md`.
