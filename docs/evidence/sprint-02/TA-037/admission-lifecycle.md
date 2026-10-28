# TA-037 v1.3 — Saneamiento del ciclo de vida de plazas

Fecha: 27/10/2026, America/Lima. PBI: TA-037, especialmente T03 (CA-08/CA-09).
Rama: `fix/TA-037-admission-lifecycle` → `integration/sprint-01`.
Base: `445886ae7c538ceeae607d59db61f2311050b3b6`.
SPEC/PLAN: `docs/specs/*TA-037-control-carga-optimizador.md`.

Fabricio Aguilar implementó T01–T04 (PR #62, #65, #66, #67 y #68).
Fabricio Melendez Quezada, con Codex, realiza este saneamiento autorizado por el
responsable. No se atribuye a Aguilar esta corrección ni una aprobación humana.

## Problema y corrección

La versión anterior eliminaba plazas al cumplir 300 s, aunque su trabajador
siguiera vivo. La entrega de eventos NDJSON no consume el presupuesto de cálculo
L-12 y puede durar más de 300 s; por tanto, esa caducidad podía permitir superar
L-10/L-11. El cierre del cliente tampoco garantiza que el trabajador haya parado:
la limpieza espera como máximo 2 s y el motor se interrumpe cooperativamente.

`b583870` retira la caducidad por antigüedad. La plaza permanece reservada hasta
que la libera su propietario; se mantiene el lock y la liberación idempotente.
Las fechas de adquisición son solo metadatos diagnósticos, nunca una condición
para recuperar capacidad. La política es conservar el límite: una fuga no
comprobada no autoriza admitir trabajadores adicionales. El reinicio del proceso
elimina sus plazas y trabajadores; una recuperación distribuida pertenece a GAP-03.

No cambia presupuestos, L-12 (120 s sin tiempo de entrega), HTTP/NDJSON, heurísticas,
rotación a 5°, stock, confirmación, frontend, esquemas ni migraciones. La
recuperación de pedidos después de un fallo sigue perteneciendo a TA-038.

## Regresiones añadidas

Commit de pruebas: `24701007a3dae10097d5c708339e64316cfd1dbc`.

- Tres casos con reloj a 300/301/3600 s: dos plazas siguen ocupadas, terceros y
  el mismo usuario se rechazan; solo una liberación real permite otra admisión.
- Dos escenarios con generador NDJSON real, calculador real y PostgreSQL: se
  suspende el consumo en `group_started`, se avanza el reloj a 301 s y se
  verifica que no se admite otra ejecución del mismo usuario ni se crea otra
  optimización. Después se completa o desconecta el stream y se libera su plaza.
- Desconexión con trabajador deliberadamente detenido por un Event: el cierre
  supera la espera de limpieza de 2 s y el trabajador sigue vivo. La plaza se
  conserva hasta reanudarlo y terminar; se comprueba el fallo persistido y que
  inventario y movimientos permanecen intactos.
- Fallo de arranque de Thread: la reserva se libera mediante la limpieza del
  response. Un cliente de prueba estricto observa la excepción de arranque.

Son siete escenarios temporales/de ciclo de vida. Sustituyen la prueba
anterior que esperaba caducidad (incremento neto: seis pruebas). Los escenarios
existentes de 100 ciclos, límite concurrente, rechazo, fallo, desconexión, timeout
y confirmación se conservan.

## Resultados ejecutados

Linux, Python 3.11.9, entorno `.venv` del backend y PostgreSQL 17.11 temporal
exclusivo en loopback. `NEWGLASS_REQUIRE_POSTGRES=1`, dotenv deshabilitado.
No se usa una base compartida ni credenciales de producción.

Antes de corregir, sobre `571ed1b` más la nueva regresión unitaria:

```text
pytest tests/unit/optimization/test_run_admission.py -q -p no:cacheprovider
3 failed, 8 passed in 0.38s
# A 300/301/3600 s active() devolvía 0 en vez de 2 sin liberar ninguna plaza.
```

Después de corregir, sobre `2470100`, sin cambios de producción pendientes:

```text
pytest tests/unit/optimization/test_run_admission.py -q -p no:cacheprovider
11 passed in 0.30s

pytest tests/unit/optimization/test_run_admission.py tests/api/optimization/test_run_concurrency.py tests/api/optimization/test_run_load_limits.py tests/api/optimization/test_run_load_stress.py tests/integration/optimization/test_run_load_limits_pg.py -q -ra --tb=short
39 passed, 1 warning in 10.96s

pytest tests/unit/optimization tests/optimization tests/api/optimization tests/integration/optimization -q -ra --tb=short
717 passed, 1 warning in 68.01s
```

Comandos desde `backend/`, con el venv activado y `NEWGLASS_TEST_PG_BIN` apuntando
a `initdb`/`pg_ctl` locales. La advertencia es la deprecación existente de
Starlette/TestClient/httpx. Cero omisiones en estas ejecuciones.

## Matriz de cierre de T01–T04

| CA | Tarea | Evidencia técnica |
|---|---|---|
| CA-01 | T01 | SPEC v1.3: presupuestos, validaciones y contratos de v1.2 preservados; mediciones históricas en README. |
| CA-02 | T02 | Regresiones `test_load_budget.py`, `test_run_load_limits.py` y límites exactos/+1; 717 PASS. |
| CA-03 | T02 | `test_accept_run_load_limits.py`: rechazo antes de preparación/expansión; 717 PASS. |
| CA-04 | T02 | API y `test_run_load_limits_pg.py`: rechazo sin nuevas ejecuciones, cambios de pedidos o inventario; 39 y 717 PASS. |
| CA-05 | T02 | FF/BF/WF, geometría, corte comercial, confirmación, bloqueos y rollback dentro de las 717 pruebas; motores/confirmación intactos. |
| CA-06 | T02 | Unidades con cantidad máxima de int rechazadas en los tests de carga/estrés; 39 y 717 PASS. |
| CA-07 | T02 | Dos/tres geometrías grandes y cota raster en `test_load_budget.py`/`test_accept_run_load_limits.py`; 717 PASS. |
| CA-08 | T03 | Regresiones 300/301/3600 s y stream lento/PostgreSQL; límites global y por usuario preservados; 39 y 717 PASS. |
| CA-09 | T03 | Finalización, fallo, desconexión, timeout, rechazo, arranque fallido, trabajador vivo tras limpieza y 100 ciclos sin fugas; 39 y 717 PASS. |
| CA-10 | T03 | API conserva 201/422/503, Retry-After y eventos de fallo; confirmación funciona con plazas ocupadas; 39 y 717 PASS. |
| CA-11 | T04 | Frontend intacto: `LoadControlFeedback.test.jsx`, contrato y `ta037-load-feedback.spec.js`; ejecución nueva mediante CI del PR. |
| CA-12 | T04 | `test_run_load_stress.py`, con rechazo temprano de cantidades/stock masivos; 39 y 717 PASS. |

## CI, revisión y cierre formal

El CI del PR debe ejecutar la suite backend completa, frontend unitario y de
componentes, lint/build y E2E de escritorio/móvil. Los resultados locales de
arriba no se presentan como ese CI. Su enlace y resultado se registran en el PR.
La base ya tenía [CI de integración aprobado](https://github.com/melendezzz26/optimizador-vidrio/actions/runs/40529753106):
2172 backend, 161 unitarias frontend, 483 componentes y 100 E2E aprobados, con seis
skips heredados de HU-015. Esos seis casos pertenecen al alcance de TA-040; no se
presentan como ejecutados ni bloquean la prueba focal de TA-037.

El estado documental es Implemented con validación técnica; Verified requiere
CI y revisión del cierre del PR. Integrar el saneamiento y registrar la decisión
formal antes de marcar TA-037 Closed. No se modifica Notion desde esta entrega.

GAP-03 (varios procesos), GAP-04 (fallos tardíos residuales), GAP-05 (capacidad
raster a 5°) y TA-038 siguen explícitamente separados. No se ocultan como
resueltos, ni se amplía TA-037 para implementar otras tareas.


## Verificación independiente y cierre (28/10/2026)

Realizada por Fabricio Aguilar, distinto del autor del saneamiento, sobre
`integration/sprint-01` en `e256bde`, con PostgreSQL efímero obligatorio
(`NEWGLASS_REQUIRE_POSTGRES=1`). Prueba focal:

```text
pytest tests/unit/optimization/test_run_admission.py tests/api/optimization/test_run_concurrency.py tests/api/optimization/test_run_load_limits.py tests/api/optimization/test_run_load_stress.py tests/integration/optimization/test_run_load_limits_pg.py -q
```

| Código de admisión | Resultado |
|---|---|
| Actual (`e256bde`) | **39 passed** |
| Anterior, con vencimiento a 300 s (`445886a`) | **6 failed, 33 passed** |

Las 6 que fallan con el código anterior son exactamente las regresiones de T03:

- `test_unreleased_slots_keep_global_and_user_limits_after_long_delivery[300]`, `[301]` y `[3600]`
- `test_slow_live_stream_keeps_slot_past_300_seconds_until_worker_ends[complete]` y `[disconnect]`
- `test_disconnect_cleanup_does_not_free_a_worker_still_computing`

Esto demuestra que la falla es reproducible y que la corrección evita que se admita
una segunda ejecución incompatible mientras la primera sigue activa (L-10 y L-11).

Desde la integración del PR #74, el CI de integración volvió a ejecutar estas
pruebas en verde en los PR #78, #83 y #85. Desde TA-040 (PR #83), el job E2E corre
106 pruebas sin omisiones, incluidas las 6 de HU-015 que antes se saltaban.

**Estado:** TA-037 pasa a Verified; T03 puede marcarse como Closed. GAP-03, GAP-04,
GAP-05 y TA-038 siguen fuera de este alcance.