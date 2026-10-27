# Smoke post-merge del PR #64

Fecha: **27/10/2026**, America/Lima.
Ubicación del proyecto/equipo: **Trujillo, La Libertad, Perú**.
Periodo: **21/10/2026 – 28/10/2026**.
Revisor / Scrum Master: **Fabricio Melendez Quezada**.
Resultado: **SP-003, TA-016, TA-018 T01 y TA-018 T02 listas para Cierre**.
Pendiente decisión formal del revisor; no se atribuye aprobación en su nombre.

## Base verificada

Rama integration/sprint-01, HEAD `2a76141d38ca52045a5f5ee6000fea4eedb00885`,
igual a origin tras `git fetch origin --prune` y
`git pull --ff-only origin integration/sprint-01`.
La rama local avanzó de 783aac8 a 2a76141 por fast-forward.
`git merge-base --is-ancestor b7b9caa HEAD` terminó con código 0:
contiene el merge del PR #64, `b7b9caa2f40ff2df71ca5e4c28988c6e0f290eae`.

No se creó un merge, rebase, PR, commit ni push. No se incorporaron los commits
de la rama TA-020 inicialmente seleccionada. Sin cambios productivos ni nuevas
funcionalidades; solo evidencia y estados documentales en integration local.

## Smoke de algoritmos

Python 3.11.15, entorno local .venv. Desde backend, ejecutado como un solo comando:

```text
../.venv/Scripts/python.exe -m pytest -q
  tests/unit/optimization/test_rotation.py
  tests/unit/optimization/test_first_fit.py
  tests/unit/optimization/test_best_fit.py
  tests/unit/optimization/test_worst_fit.py
  tests/unit/optimization/test_sprint2_angles.py
  tests/integration/optimization/test_best_fit_slice.py
  tests/integration/optimization/test_worst_fit_slice.py
```

**117 passed, 0 failed, 0 skipped en 2.27 s**.

Se verifican FF/BF/WF, default/seed 5°, secuencia 0,5,...,355, deduplicación,
círculo sin redundancia y uso común de RasterCache.orientations mediante pack.
BF conserva mínimo de capacidad posterior y primera orientación/posición por
fuente; prioridad retazo y fallback a plancha. Pasan normal, rotación necesaria,
no colocable, desempate, repetición, separación y material irregular.
Simulación sin mutación: inputs inmutables y slices con repositorios reales y
snapshots de todas las tablas en SQLite aislado, incluido BF a 5°.

## Imports y arranque

Proceso Python separado: import tests.conftest para SQLite, clave efímera y
dotenv desactivado; import main.app, FirstFitOptimizer, BestFitOptimizer,
WorstFitOptimizer y RasterCache. Inicio/cierre ASGI con `with TestClient(app)`.
Asserts HTTP 200 para `/`, `/health/live`, `/health/ready` y `/openapi.json`:
todos aprobados. Readiness corresponde a SQLite de prueba, no a producción.
Aviso conocido: StarletteDeprecationWarning por httpx/TestClient.

Una sonda inicial consultó `/health` y obtuvo 404 porque esa ruta no existe.
Se corrigió el comando a las rutas reales /health/live y /health/ready;
no fue un fallo del backend ni requirió modificar código.

## Reproducción de SP-003

Desde raíz: cargar experiments/raster/scripts/sp003_angles.py con
`runpy.run_path(..., run_name='smoke')` y ejecutar `measure(step)` por cada paso.
Se compararon con results.json mediante asserts: orientaciones, búsquedas,
candidatos, colocadas, métricas y placements. Coincidencia exacta en los cuatro
pasos; tiempos excluidos de igualdad. measure verifica cinco repeticiones por paso.
No se ejecutó el bloque principal que escribe resultados; JSON e históricos intactos.

| Paso | Orientaciones | Colocadas | Uso % | Merma mm² | Recuperable mm² |
|---|---:|---:|---:|---:|---:|
|90°|6|3|20.652|78|68|
|45°|12|3|20.652|16|130|
|15°|32|3|20.652|16|130|
|5°|68|3|20.652|22|124|

Se conserva la distinción: 45° tuvo mejor calidad/costo en esta instancia;
**5° sigue siendo el contrato operacional** compartido por decisión del equipo.

## Criterios finales

| Trabajo | Criterios comprobados | Estado |
|---|---|---|
| SP-003 | Misma instancia, cuatro pasos, métricas reproducibles, histórico y conclusión alineada a 5° | Lista para Cierre |
| TA-016 | Componente único FF/BF/WF, orden, normalización, deduplicación, 5° y regresiones | Lista para Cierre |
| TA-018 T01 | BF integrado, candidato/capacidad común, mínimo posterior por nivel, desempate y primer placement | Lista para Cierre |
| TA-018 T02 | Normal, rotación, no colocable, desempate, repetibilidad, prioridad, regresión FF e inventario intacto | Lista para Cierre |

Sin fallos reales detectados ni bloqueos técnicos para solicitar Cierre.
Este smoke no sustituye suite completa PostgreSQL, E2E, CI ni validación de
despliegue; no se ejecutaron en esta revisión ni se consultó producción.
`git diff --check` aprobado. Únicos cambios: documentación local, sin publicar.
