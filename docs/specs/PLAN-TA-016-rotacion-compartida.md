# PLAN TA-016

1. Auditar diff PR58 y reutilizar pack / rotation (completado).
2. Capturar línea base: 80 passed in 2.52s en Python 3.11.15.
3. Formalizar contrato existente sin modificar generación de ángulos/máscaras.
4. Verificar FF/BF/WF con prueba común y repetir línea base.
5. Publicar evidencia y mantener historial mediante merges normales.

Comando baseline desde backend:
`../.venv/Scripts/python -m pytest -q tests/unit/optimization/test_first_fit.py tests/unit/optimization/test_rotation.py tests/unit/optimization/test_worst_fit.py tests/integration/optimization/test_worst_fit_slice.py`.
