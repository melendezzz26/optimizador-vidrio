# PR #64 — diagnóstico del backend CI

Rama: feature/S2-rotation-best-fit. HEAD original: ef24c49.
Ejecución fallida: https://github.com/melendezzz26/optimizador-vidrio/actions/runs/40284369867
Job backend: 121444479684. Resultado: 2 failed, 2061 passed, 1 warning,
214.67 s; frontend y e2e aprobados.
Se consultó la API de GitHub y el log real; GitHub CLI no estaba instalado.

## Causa exacta

- tests/api/optimization/test_runs_api.py:328,
  test_rotated_placement_geometry_is_durable_and_used_without_second_rotation:
  falla all(Decimal(p['rotation_deg']) == 90 for p in live).
- tests/integration/optimization/test_confirmation.py:215,
  test_residual_created_from_oriented_contours_and_reproducible_free_cells:
  falla all(p.rotation_deg == 90 for p in run.result.placements).

Ambas pruebas usan la fixture prepared de test_runs.py. El commit b87d5f6
de esta feature cambió su paso angular de 90° a 5°, pero las expectativas
geométricas de ambas pruebas seguían suponiendo cuartos de vuelta.
Con pieza 3×1, dos unidades y planchas 2×4, la primera orientación factible
es 70°. Su contorno normalizado es un polígono con vértices
(0.939693,0), (1.965753,2.819078), (1.02606,3.161098), (0,0.34202).
Cada pieza usa una unidad física distinta; no queda rectángulo recuperable.
Aceptar 70° es correcto bajo el contrato de primera orientación factible.

Es una regresión de expectativas introducida por nuestra actualización de la
fixture, no un defecto del motor ni del workflow. Los dos archivos de tests
fallidos estaban sin cambios respecto a integration. Antes del PR, Windows no
tenía PostgreSQL y omitía estas pruebas entre las 605 skipped; nunca pasaron allí.
CI instala PostgreSQL y exige NEWGLASS_REQUIRE_POSTGRES=1, por eso sí las ejecutó.

## Corrección

Sin cambios productivos ni de GitHub Actions. Se parametrizan ambos tests:

- Pieza 3×2, plancha 2×7: fuerza 90°, coloca dos unidades en (0,0)/(0,3)
  sobre una fuente, deja retazo 2×1 en (0,6).
- Pieza 3×1, plancha 2×5: primer ángulo 70°, una pieza por unidad física,
  deja un retazo 2×1 en (0,4) por fuente (dos retazos, 4 mm² en total).

Se mantienen assertions exactas de geometría y métricas; se amplían a ambas
colocaciones persistidas, coordenadas, unidades físicas y todos los retazos
confirmados. No se añaden skips, xfail ni tolerancias para ocultar el fallo.
test_sprint2_angles.py añade el caso original 3×1/2×4 para FF/BF/WF sin PostgreSQL,
verificando ángulos 70°, geometría exacta, coordenadas y dos unidades físicas.

## Reproducción

Ubuntu 24.04 en WSL, Python 3.11.17 y PostgreSQL 16.15; dependencias del mismo
backend/requirements.txt. Clústeres efímeros de tests en loopback, sin BD remota.
Antes de editar: los dos tests originales fallaron con las mismas assertions
(2 failed en 22.55 s). El primer intento compartió cachés de Windows y emitió
dos avisos de permisos; después se separaron las cachés, sin cambiar tests.

Entorno para las siguientes ejecuciones desde backend:

```sh
export NEWGLASS_REQUIRE_POSTGRES=1
export NEWGLASS_TEST_PG_BIN=/usr/lib/postgresql/16/bin
export PYTHON_DOTENV_DISABLED=1
export PYTHONPYCACHEPREFIX=/home/patri/.cache/newglass-pr64-pycache
PYTHON=/home/patri/.cache/newglass-pr64-venv/bin/python
# Añadir a pytest: -o cache_dir=/home/patri/.cache/newglass-pr64-pytest
```

- Tests aislados corregidos: 4 passed, 0 failed, 0 skipped, 1 warning, 20.53 s.
- Archivos relacionados test_runs_api.py y test_confirmation.py:
  52 passed, 0 failed, 0 skipped, 1 warning, 36.90 s.
- Conjunto focal Sprint 2 en Windows (mismos siete archivos de la evidencia):
  117 passed, 0 failed, 0 skipped, 2.13 s.

El warning restante es StarletteDeprecationWarning por httpx/TestClient.

Suite completa, con las variables Linux anteriores:

```sh
$PYTHON -m pytest tests -q -ra \
  -o cache_dir=/home/patri/.cache/newglass-pr64-pytest --tb=short
```

Resultado: **2068 passed, 0 failed, 0 skipped, 1 warning en 658.64 s**.
Incluye las pruebas PostgreSQL anteriormente omitidas. git diff --check aprobado.
No cambios de workflow, skips, xfail ni código productivo. El commit de corrección
se publica únicamente en la rama del PR #64; no se abre otro PR ni se hace merge.
