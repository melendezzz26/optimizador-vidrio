# TA-043 / B10 — Recursos y preparación operativa

Estado: **COMPLETADO para las cargas medidas**. Se conservaron las mediciones
de 3 unidades y se añadió una carga representativa válida de 12 unidades.
La capacidad para 150 unidades y para cargas superiores a 12 unidades no queda
acreditada.

## Alcance y fuentes

- Código evaluado: `a6ff120` (HEAD de B09; no se modificó producción).
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
`false`; el harness no crea ni modifica inventario. Ambos casos usan el mismo
hash de entrada para sus seis motores. El caso de 12 unidades contiene
rectángulos, circunferencias y polígonos convexos, cuatro pedidos, cuatro
unidades físicas de plancha, material/espesor compatibles y configuración de
rotación de 5°.

## Resultados observados

| Escenario | Unidades | Resultado | Tiempo global | RSS agregado máximo | VM worker máximo |
|---|---:|---|---:|---:|---:|
| `small-b09-reference` | 3 | 6/6 completos | 2.685 s | 61.3 MiB | 38.3 MiB |
| `representative-12-units` | 12 | 6/6 completos | 2.978 s | 61.9 MiB | 38.3 MiB |

Los tiempos externos por motor fueron:

| Escenario | FF | BF | WF | HF | M5 | M6-BS |
|---|---:|---:|---:|---:|---:|---:|
| Pequeño | 3.05 ms | 2.75 ms | 2.65 ms | 4.28 ms | 2.65 ms | 20.14 ms |
| 12 unidades | 7.51 ms | 11.04 ms | 10.19 ms | 9.99 ms | 10.49 ms | 154.75 ms |

Los arranques estuvieron por debajo de 0.55 s, el máximo de paquete observado
fue 1,207 bytes, y no hubo resultados parciales, fallidos ni workers
remanentes. La retención y los límites efectivos permanecieron en la
política existente: RSS agregado 1 GiB, supervisor 240 MiB, VM por worker
256 MiB, reserva 16 MiB, startup 30 s, cálculo 120 s, global 180 s, IPC
12 MiB, visual 4 MiB, retención visual 32 MiB y eventos 8 MiB.

## Matriz B10

| Criterio | Evidencia | Brecha |
|---|---|---|
| CA-03/04/05/17 | `measurements.json`, B04/B05/B06 y B09 | Capacidad superior a 12 unidades no medida |
| N02/N03/N05/N06 | B04/B05/B06 y medición nueva | Heroku no fue ejecutado ni desplegado |
| Un worker y cierre seguro | `maximum_active_workers=1`, `all_workers_stopped=true` | No hay medición de 150 unidades |
| Límites de memoria, IPC y tiempos | Valores observados y política serializada | Capacidad superior al caso medido queda pendiente |
| Compatibilidad Linux | Ejecución real en WSL2, spawn y procfs | WSL2 no sustituye la validación de una plataforma objetivo |
| v1 y `/runs` | Evidencias B06/B09 | Sin cambios en esta fase |

## Operación y riesgos

Se reutilizan las evidencias B06/B09 para health/readiness, autenticación,
CORS, recuperación, reinicio sin recálculo, confirmación y limpieza. B10 no
modificó backend, frontend, heurísticas, límites ni migraciones. No se
ejecutó PostgreSQL compartido ni se expusieron secretos.

La operación web mantiene la política de una única instancia/proceso web;
la medición no levanta un segundo supervisor. Linux/WSL2 permitió verificar
`procfs`, `prctl`, `RLIMIT_AS`, spawn y cierre de descendientes. Heroku no
queda validado por extrapolación desde WSL2: debe confirmarse que ofrece esos
mecanismos y el cierre requerido por el supervisor. La capacidad de 150
unidades y el comportamiento bajo saturación quedan pendientes.
