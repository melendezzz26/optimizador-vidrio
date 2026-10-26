# Evidencia — granularidad operacional de 5°

2026-10-26, misma feature/S2-rotation-best-fit. Integration 6f2a159 incorporada
por merge normal. Sin PR, rebase ni merge a integration.

Auditoría de todas las fuentes: docs/reviews/S2-angular-configuration.md.
Default antes: ninguno en OptimizationConfig; seed/demo 90°; HTTP valor vigente
de BD. Ahora default y nuevo seed 5°, aceptación operativa exige 5° sin mutar
versiones anteriores. No se modificó ninguna BD real.

SP-003 histórico conservado en results-historical-90-45-15.json; results.json
contiene nueva medición 90/45/15/5 con misma instance() y cinco tiempos por paso.
5°: 68 orientaciones preparadas, 24 búsquedas, 3 candidatos, 3 colocaciones,
uso 20.652%, merma 22 mm², recuperable 124 mm², mediana 34.008 ms.
15°: 32 orientaciones, 18 búsquedas, merma 16, recuperable 130, mediana 11.514 ms.
El giro canónico del polígono pasa de 135° a 130°. No se cambia la regla de
primera orientación para intentar mejorar este resultado. 5° es el contrato
del equipo, aunque 45° tenga mejor relación calidad/costo en esta instancia.
Memoria no medida: no existe instrumentación en el experimento.

## Pruebas ejecutadas

Python 3.11.15, mismo entorno de dependencias del checkpoint TA-018.
Desde backend, ../.venv/Scripts/python.exe:

- Antes: -m pytest -q tests/unit/optimization/test_rotation.py
  tests/unit/optimization/test_first_fit.py tests/unit/optimization/test_best_fit.py
  tests/unit/optimization/test_worst_fit.py
  tests/integration/optimization/test_best_fit_slice.py
  tests/integration/optimization/test_worst_fit_slice.py
  → 101 passed in 1.85s.
- Después: mismo comando más tests/unit/optimization/test_sprint2_angles.py
  → 114 passed in 2.07s.
- Suite completa: -m pytest -q → 1458 passed, 605 skipped, 1 warning in 54.55s.
  Omisiones por falta de binarios PostgreSQL locales; aviso de deprecación
  Starlette/httpx. No se ejecutaron E2E de navegador.
- SP-003: .venv/Scripts/python experiments/raster/scripts/sp003_angles.py
  desde raíz; cada paso comprueba igualdad en cinco cálculos independientes.

Cobertura: 72 ángulos 0..355, orden, ausencia de máscaras duplicadas, círculo a 0°,
FF/BF/WF llaman al mismo RasterCache.orientations con 5°, prioridad de retazo,
repetición de resultados/eventos, inputs inmutables, snapshot de todas las tablas
intacto tras BF a 5°. Pruebas de packing cubiertas por FF/BF/WF existentes.
Guard de aceptación rechaza 90/45/15 antes de bloquear pedidos o crear ejecuciones.
Las regresiones históricas con paso explícito 90° se mantienen.

SPEC/PLAN/TASKS TA-016 y TA-018 actualizados. Criterio BF, selección WF y
pipeline de máscaras/orientaciones no se modifican. git diff --check aprobado.
