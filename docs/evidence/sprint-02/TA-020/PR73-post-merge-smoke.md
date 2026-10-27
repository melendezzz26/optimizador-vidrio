# TA-020 — Smoke post-merge del PR #73

| Campo | Valor |
|---|---|
| Fecha | 27/10/2026 |
| Zona horaria del proyecto | America/Lima |
| Ubicación | Trujillo, La Libertad, Perú |
| Responsable técnico | Andro Quispe |
| Scrum Master / revisor | Fabricio Melendez Quezada |
| Periodo | 21/10/2026 – 28/10/2026 |
| PR funcional | [#73](https://github.com/melendezzz26/optimizador-vidrio/pull/73) |
| Resultado | **TA-020 — Lista para Cierre** |

El usuario confirmó review final y merge por Fabricio (`melendezzz26`).
CI backend/frontend/E2E del PR #73 terminó en success según la consulta previa
a GitHub sobre su HEAD `093c13d`. Este smoke valida ahora el código integrado;
no declara el cierre formal, que corresponde al equipo.

## Base y sincronización

- Integration local antes: `2a76141d38ca52045a5f5ee6000fea4eedb00885`.
- Integration después / HEAD verificado: `445886ae7c538ceeae607d59db61f2311050b3b6`.
- Merge commit del PR #73: `445886ae7c538ceeae607d59db61f2311050b3b6`.
- Último commit feature integrado: `093c13dd042889b99d037ea31dfb51e5533cb7c0`.
- Feature inicial limpia con upstream `[gone]`; no se recreó la rama remota.

```powershell
git status -sb
git fetch origin --prune
git switch integration/sprint-01
git pull --ff-only origin integration/sprint-01
git status -sb
git log -10 --oneline
git merge-base --is-ancestor 093c13dd042889b99d037ea31dfb51e5533cb7c0 HEAD
```

Pull fast-forward correcto; ancestry **exit 0**. Integration quedó limpia e
igual a origin. No se creó merge manual ni rebase. La suite
`backend/tests/unit/optimization/test_retazo_priority.py` está presente.

## Pruebas ejecutadas sobre integration

Desde `backend/`, entorno existente `.venv`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/unit/optimization/test_retazo_priority.py -q
..\.venv\Scripts\python.exe -m pytest tests/unit/optimization/test_first_fit.py tests/unit/optimization/test_best_fit.py tests/unit/optimization/test_worst_fit.py tests/unit/optimization/test_stock.py tests/unit/optimization/test_retazo_priority.py tests/integration/optimization/test_best_fit_slice.py tests/integration/optimization/test_worst_fit_slice.py -q
```

| Ejecución | Passed | Failed | Skipped | Tiempo pytest |
|---|---:|---:|---:|---:|
| Suite TA-020 | 26 | 0 | 0 | 0.73 s |
| Regresión focal FF/BF/WF, stock y slices | 113 | 0 | 0 | 1.84 s |

La regresión incluye los 26 casos específicos; no son 139 casos únicos.
Slices BF/WF usan repositorios reales sobre SQLite aislado y el slice WF
reutiliza la regresión FF. No se ejecutó PostgreSQL, suite completa de 498,
E2E ni validación contra producción en este smoke.

## Sanidad del backend

Proceso Python independiente desde backend, cargando `tests.conftest` antes
de importar aplicación: `DATABASE_URL=sqlite://`, dotenv desactivado y clave
efímera. Mismo aislamiento que el smoke anterior del PR #64.

```python
import tests.conftest
from main import app
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.best_fit import BestFitOptimizer
from app.modules.optimization.domain.worst_fit import WorstFitOptimizer
from app.modules.optimization.domain.rotation import RasterCache
from fastapi.testclient import TestClient
with TestClient(app) as client:
    for path in ['/health/live', '/health/ready', '/openapi.json']:
        response = client.get(path)
        assert response.status_code == 200, (path, response.status_code)
        if path == '/openapi.json':
            assert '/health/live' in response.json()['paths']
        print(path, response.status_code)
```

Imports y ciclo de inicio/cierre ASGI: **PASS**. `/health/live`: **200**;
`/health/ready`: **200**; `/openapi.json`: **200** con esquema válido.
Readiness corresponde exclusivamente a SQLite de prueba. Aviso no bloqueante
observado: `StarletteDeprecationWarning` por httpx/TestClient. Sin cambios
productivos ni conexiones a producción.

## Verificación funcional y CA

| CA | Evidencia integrada | Resultado |
|---|---|---|
| CA-01: retazos compatibles primero | `test_feasible_remnant_excludes_sheets_from_evaluation`, orden del adapter en `test_stock.py` | PASS FF/BF/WF |
| CA-02: retazo factible bloquea competencia de plancha | Mismo test parametrizado, planchas tentadoras para BF/WF y pasos 5°/90°; solo se evalúa material retazo | PASS: FF → retazo, BF → retazo, WF → retazo |
| CA-03: fallback a plancha | `test_sheet_fallback`: retazo no factible y ausencia de retazos; prueba de agotamiento por unidad | PASS FF/BF/WF en ambos escenarios |
| CA-04: incompatibles excluidos | `test_adapter_excludes_incompatible_remnant_before_optimization` y rechazo directo del contrato de dominio | PASS para otro tipo de vidrio y otro espesor |
| CA-05: determinismo | `test_priority_is_rechecked_per_unit_and_repeated_runs_are_identical` | PASS: misma entrada produce mismo resultado por heurística |
| CA-06: simulación sin consumo | `test_simulation_leaves_inventory_unchanged` y slices BF/WF/FF | PASS: inventario sin mutación |

Clasificación funcional conservada: **A. SATISFECHA**. No hay regresiones
detectadas ni fallos productivos que requieran correcciones.

## Alcance del PR y entrega documental

`git diff 445886a^1 445886a --stat`: seis archivos, 502 inserciones, únicamente
pruebas/documentación/evidencia TA-020. `git diff 445886a^1 445886a -- backend/app`
sin salida: el PR funcional no cambió producción ni los cuatro motores restringidos.

Tras el smoke satisfactorio y con árbol limpio se creó desde el HEAD verificado
`docs/S2-TA-020-post-merge-smoke`. Solo se agrega este documento y se actualiza
`docs/specs/TASKS-TA-020-retazo-priority.md`. No se escribe ni publica evidencia
directamente en integration.

Validaciones de entrega: búsqueda de zonas/ubicaciones incorrectas sin resultados,
`git diff --check` correcto y diff limitado a documentación. Commit/push y PR
documental hacia integration autorizados; CI de este nuevo PR se consulta aparte.
Pendiente **cierre formal TA-020 por el equipo**, además de review/merge del PR
documental. No merge del PR documental, rebase, force push ni cierre formal.
