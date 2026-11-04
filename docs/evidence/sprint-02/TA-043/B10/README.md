# TA-043 / B10 — Recursos y preparación operativa

Estado: **PARCIAL**. Las dos cargas ejecutadas respetaron los límites y
terminaron con los seis motores completos. La capacidad para 150 unidades y
una carga representativa de muchas unidades no queda acreditada: el escenario
medido fue el fixture B09 (3 unidades), con una segunda variante geométrica
escalada, también de 3 unidades.

## Alcance y fuentes

- Código evaluado: `a6ff120` (HEAD de B09).
- Medición: [measurements.json](./measurements.json), generada en WSL2 con
  Python 3.11.9 del runtime aislado de B09.
- Harness: `backend/tests/optimization_b10_measurement.py`, que reutiliza el
  worker real de `optimization_b04_probe.py`; no usa mocks ni bases
  compartidas.
- Fixture base: `docs/evidence/sprint-02/TA-043/B03/adapter-validation.json`.

## Comandos reproducibles

```powershell
wsl.exe -e bash -lc 'cd /mnt/c/Users/fabri/Documents/TALLER\ INTEGRADOR\ I/optimizador-vidrio/backend && PATH=/home/fabri/.cache/newglass-validation.SXhCMM/backend/.venv/wsl/bin:$PATH PYTHONPATH=/mnt/c/Users/fabri/Documents/TALLER\ INTEGRADOR\ I/optimizador-vidrio/backend /home/fabri/.cache/newglass-validation.SXhCMM/backend/.venv/wsl/bin/python -m tests.optimization_b10_measurement'
```

La medición ejecutó FF, BF, WF, HF, M5 y M6-BS en orden, con un único worker
activo, observación real y limpieza por proceso. `inventory_consumed` quedó en
`false`; el harness no crea ni modifica inventario.

## Resultados observados

| Escenario | Unidades | Resultado | Tiempo global | RSS agregado máximo | VM worker máximo |
|---|---:|---|---:|---:|---:|
| `small-b09-reference` | 3 | 6/6 completos | 2.685 s | 61.3 MiB | 38.3 MiB |
| `representative-scaled-3-units` | 3 | 6/6 completos | 2.786 s | 61.5 MiB | 38.3 MiB |

En la variante escalada, las geometrías y planchas fueron ampliadas 10x
manteniendo materiales, espesor, rotación de 5° y el mismo número de unidades.
Los tiempos externos por motor fueron, respectivamente:

| Escenario | FF | BF | WF | HF | M5 | M6-BS |
|---|---:|---:|---:|---:|---:|---:|
| Pequeño | 2.90 ms | 2.91 ms | 3.00 ms | 4.40 ms | 2.83 ms | 21.52 ms |
| Escalado | 4.76 ms | 4.28 ms | 4.55 ms | 20.54 ms | 6.73 ms | 207.60 ms |

Los arranques estuvieron por debajo de 0.51 s, el máximo de paquetes
observado fue 1,216 bytes, y no hubo resultados parciales, fallidos ni
workers remanentes. La retención y los límites efectivos permanecieron en la
política existente: RSS agregado 1 GiB, supervisor 240 MiB, VM por worker
256 MiB, reserva 16 MiB, startup 30 s, cálculo 120 s, global 180 s, IPC
12 MiB, visual 4 MiB, retención visual 32 MiB y eventos 8 MiB.

## Matriz B10

| Criterio | Evidencia | Brecha |
|---|---|---|
| CA-03/04/05/17 | `measurements.json`, B04/B05/B06 y B09 | No se acreditó una carga de muchas unidades |
| N02/N03/N05/N06 | B04/B05/B06 y medición nueva | Heroku no fue ejecutado ni desplegado |
| Un worker y cierre seguro | `maximum_active_workers=1`, `all_workers_stopped=true` | No hay nueva carga de 150 unidades |
| Límites de memoria, IPC y tiempos | Valores observados y política serializada | La capacidad superior al caso medido queda pendiente |
| Compatibilidad Linux | Ejecución real en WSL2, spawn y procfs | WSL2 no sustituye la validación de una plataforma objetivo |
| v1 y `/runs` | Evidencias B06/B09 | Sin cambios en esta fase |

## Operación y riesgos

Se reutilizan las evidencias B06/B09 para health/readiness, autenticación,
CORS, recuperación, reinicio sin recálculo, confirmación y limpieza. B10 no
modificó backend, frontend, heurísticas, límites ni migraciones. No se
ejecutó PostgreSQL compartido ni se expusieron secretos.

Heroku no queda validado por extrapolación desde WSL2. Debe confirmarse en
B11 si la plataforma objetivo ofrece `procfs`, `prctl`, `RLIMIT_AS`, spawn y
el cierre de descendientes requeridos por el supervisor. La capacidad de
150 unidades, el comportamiento bajo saturación y una medición de plataforma
objetivo quedan pendientes para B11.

