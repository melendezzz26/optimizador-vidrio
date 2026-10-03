# Experimentación de rasterización

Espacio reservado para explorar y validar rasterización durante Sprint 1.
First Fit, Best Fit y Worst Fit están fuera del alcance de ese sprint.
No se implementan algoritmos en esta preparación estructural.

## Organización

- `cases/`: entradas pequeñas y reproducibles; documentar formato, unidades y origen.
- `scripts/`: código de experimentación; cada experimento debe indicar comando,
  dependencias, parámetros y semilla cuando corresponda.
- `results/`: resultados generados al ejecutar los scripts, reconstruibles a
  partir de sus entradas y parámetros.

Las carpetas contienen únicamente `.gitkeep` mientras no haya trabajo incorporado.
Los marcadores no son resultados ni evidencia de ejecución.

## Resultados y evidencia

La regla `experiments/raster/results/*` de `.gitignore` excluye los resultados
generados. `experiments/raster/results/.gitkeep` permanece versionable para
conservar la carpeta. Las entradas de `cases/` y los scripts de `scripts/`
también permanecen versionables.

Los resultados seleccionados que sustenten una conclusión deben copiarse o
documentarse en `docs/evidence/sprint-01/<ID>/`. Para rasterización está reservado
`docs/evidence/sprint-01/SP-001-raster/`. Registrar comando, versión del código,
entradas, parámetros y resultado observado; no declarar métricas sin ejecución.
Las conclusiones de investigación se documentan en `docs/spikes/`.

## Relación con la aplicación

La aplicación nunca importa directamente código de `experiments/`. La integración
posterior en `backend/app/modules/optimization/` corresponde a un trabajo propio,
con pruebas reproducibles en `backend/tests/optimization/` y dependencias explícitas.
