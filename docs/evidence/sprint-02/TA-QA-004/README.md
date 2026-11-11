# Evidencia TA-QA-004 — Fiabilidad y recuperación

| Campo | Valor |
|---|---|
| Tarea | TA-QA-004 · T01 — Medir escenarios de fallo |
| SPEC | [SPEC-TA-QA-004-fiabilidad-recuperacion.md](../../../specs/SPEC-TA-QA-004-fiabilidad-recuperacion.md) |
| Responsable | Fabricio Danniel Aguilar Chavez (`fabrilar1`) |
| Rama de la evidencia | `docs/S2-TA-QA-004-fiabilidad` (repo `optimizador-vidrio`) |
| Código medido | `newglass-backend` `main` en `7a99663`. La suite local y `collect-only` se corrieron en `test/TA-QA-006-port-security-tests`, que es `main` más 3 archivos de prueba de seguridad, sin cambios en `app/` (SPEC D-17). |
| Fecha | 11/11/2026 |
| Estado | CA-01, CA-02 y CA-03 con resultados de Windows y del entorno de verificación Linux; **pendiente el enlace al CI** (MR-02, MR-03 y MR-04 completas, y CA-04). |

## Qué se entregó

- Tabla de fallos simulados por etapa crítica, con mecanismo, prueba, entorno y resultado (CA-01).
- Resultados de no duplicación de stock y de pedidos coherentes (CA-02).
- Métricas MR-01 a MR-05 con su denominador, valor y fuente (CA-03).
- Trazabilidad: commit medido, salidas de comandos en texto y archivos de medición (CA-04).
- Entregables complementarios: SPEC-TA-049 histórica, riesgos residuales y procedimiento
  de reconciliación en Staging, **no ejecutado**.

No se modificó código, base de datos, Heroku ni Supabase (SPEC D-01).

**Fuentes de resultados:**

| Abreviatura | Fuente | Qué cubre |
|---|---|---|
| **Win** | Suite local en Windows: 2725 passed, 944 skipped, 0 failed (ver "Salidas de comandos") | Pruebas unitarias. Las de PostgreSQL se omiten. |
| **Lnx** | Entorno de verificación Linux con PostgreSQL 16.15 y Python 3.13.18: 28 passed, 0 failed ([medicion-MR05.txt](medicion-MR05.txt)) | Los 26 casos de MR-01, `http_restart` y `lifespan`. No es el CI. |
| **CI** | `Backend CI` de `newglass-backend` (pendiente) | Todas las pruebas, incluidas PostgreSQL y solo Linux, con Python 3.11. |

## CA-01 — Fallos simulados en etapas críticas

| Etapa | Fallo simulado | Mecanismo | Prueba | Entorno | Resultado |
|---|---|---|---|---|---|
| Admisión | Capacidad o usuario ocupados; liberaciones repetidas; 100 ciclos sin fugas | M1 | `tests/unit/optimization/test_run_admission.py` | Windows | ✅ Win |
| Admisión | Tercera corrida concurrente → 503 sin efectos | M1 | `tests/api/optimization/test_run_concurrency.py::test_third_concurrent_run_gets_503_without_side_effects_and_is_admitted_later` | PostgreSQL | CI: pendiente |
| Arranque del cálculo | El hilo de cálculo no arranca | M1, M4 | `tests/api/optimization/test_run_recovery.py::test_worker_start_failure_recovers_accepted_orders`; `test_run_concurrency.py::test_worker_start_failure_releases_reserved_slot` | PostgreSQL | ✅ Lnx (1.ª); CI: pendiente (2.ª) |
| Cálculo | Error del motor, interrupción o plazo vencido (6 combinaciones) | M4 | `tests/api/optimization/test_run_recovery.py::test_stopped_engine_releases_entire_batch_and_can_retry` | PostgreSQL | ✅ Lnx (6/6) |
| Cálculo | Plazo vencido después del último hito del motor | M4 | `…::test_deadline_after_last_engine_checkpoint_cannot_commit_no_solution` | PostgreSQL | ✅ Lnx |
| Cálculo | Plazo de la corrida (`TIME_BUDGET_EXCEEDED`) | M1, M4 | `test_run_concurrency.py::test_time_budget_stops_the_run_as_failed_and_frees_the_slot` | PostgreSQL | CI: pendiente |
| Cálculo | Plazo de cálculo o global de una comparación v1/v2 | M2 | `tests/api/optimization/test_comparison_recovery.py` (4 casos) | PostgreSQL | ✅ Lnx (4/4) |
| Cálculo | Caída de un motor o mensaje IPC sobredimensionado en la comparación | M2 | `tests/integration/optimization/test_comparison_supervision_v2.py::test_local_process_and_ipc_failure_preserve_other_five` (2 casos) | Solo Linux | CI: pendiente |
| Desconexión | El cliente se desconecta antes de iniciar el cuerpo de la respuesta | M4 | `…/test_run_recovery.py::test_disconnect_before_body_iterator_starts_recovers_accepted_batch` | PostgreSQL | ✅ Lnx |
| Desconexión | Desconexión con el motor todavía calculando | M1 | `test_run_concurrency.py::test_client_disconnect_frees_the_slot_when_the_worker_stops` | PostgreSQL | CI: pendiente |
| Guardado del resultado | Falla el guardado del resultado | M4 | `…/test_run_recovery.py::test_failed_result_flush_rolls_back_then_releases_in_separate_transaction` | PostgreSQL | ✅ Lnx |
| Guardado del resultado | Falla el commit de la propia recuperación | M4 | `…/test_run_recovery.py::test_failure_of_recovery_commit_is_visible_and_requires_reconciliation` | PostgreSQL | ✅ Lnx |
| Guardado del resultado | Falla la escritura en la BD durante una comparación | M2 | `test_comparison_supervision_v2.py::test_database_write_failure_does_not_emit_false_persistence` | Solo Linux | CI: pendiente |
| Caída del proceso | Salida abrupta real del proceso durante una corrida | M4 | `tests/integration/optimization/test_run_recovery.py::test_abrupt_process_exit_requires_explicit_offline_reconciliation` | PostgreSQL | ✅ Lnx |
| Caída del proceso | Falla el lanzamiento de un proceso de la comparación | M2 | `test_comparison_supervision_v2.py::test_spawn_failure_keeps_other_engines_and_closes_spawn_intent` | Solo Linux | CI: pendiente |
| Reinicio | Desconexión HTTP real y reinicio de Uvicorn | M3 | `tests/integration/optimization/test_comparison_v2_http_restart.py` | PostgreSQL + `/proc` | ✅ Lnx |
| Reinicio | `lifespan` de FastAPI recupera y apaga v2 | M3 | `test_comparison_supervision_v2.py::test_fastapi_lifespan_recovers_and_shuts_down_real_v2_without_routes` | Solo Linux | ✅ Lnx |
| Reinicio | Identidad del dueño muerta, viva, PID reutilizado, desconocida o con lanzamiento a medias (7 casos) | M2, M3 | `test_comparison_supervision_v2.py::test_recovery_requires_process_identity_proof_without_recalculation` | Solo Linux | CI: pendiente |
| Confirmación | Error SQL real en cada escritura de la confirmación (9 casos) | M5 | `tests/integration/optimization/test_confirmation_rollback.py` | PostgreSQL | CI: pendiente |
| Confirmación | Reglas de confirmabilidad | M5 | `tests/unit/optimization/test_confirmation.py` | Windows | ✅ Win |

## CA-02 — Sin descuento duplicado ni pedidos inconsistentes

| Riesgo | Prueba | Casos | Resultado |
|---|---|---|---|
| Doble consumo por confirmaciones concurrentes | `tests/integration/optimization/test_confirmation_concurrency.py` (misma optimización dos veces, carrera por el mismo retazo, por la última plancha, bloqueo de inventario) | 4 | CI: pendiente (MR-03) |
| Escrituras parciales de la confirmación | `tests/integration/optimization/test_confirmation_rollback.py` | 9 | CI: pendiente (MR-02) |
| Reinicio parcial de un lote inconsistente (pedidos mezclados o con consumo) | `tests/integration/optimization/test_run_recovery.py::test_inconsistent_batch_blocks_failure_without_partial_reset` | 2 | ✅ Lnx |
| Liberar pedidos que ya pertenecen a otra ejecución | `…::test_two_failures_and_new_acceptance_never_release_another_owner` | 1 | ✅ Lnx |
| Un aviso tardío sobrescribe un resultado terminal | `…::test_late_failure_refreshes_previously_loaded_terminal_state`; `…::test_reconciliation_and_late_failure_preserve_terminal_outcomes` | 1 + 3 | ✅ Lnx |
| Fallo y liberación de pedidos en commits separados | `…::test_failure_and_order_release_have_one_commit_or_total_rollback` | 1 | ✅ Lnx |
| La reconciliación toca casos C, D o E | `tests/unit/optimization/test_stuck_order_reconciliation_unit.py` | 5 | ✅ Win |
| Ídem, contra PostgreSQL real | `tests/integration/optimization/test_stuck_order_reconciliation_pg.py` | 2 | CI: pendiente |

## CA-03 — Tiempo de recuperación y tasa de éxito

Denominadores tomados de [collect-only.txt](collect-only.txt) (68 casos recogidos; los
parametrizados cuentan por separado).

| ID | Métrica | Denominador | Valor medido | Meta | Estado |
|---|---|---|---|---|---|
| MR-01 | Recuperación de pedidos tras un fallo controlado | 26 (12 + 10 + 4) | **CI: pendiente.** Dato complementario Lnx: 26/26 = 100 % | 100 % | Pendiente del CI; sin fallos en Lnx |
| MR-02 | Atomicidad de la confirmación ante errores | 9 | CI: pendiente | 100 % | Pendiente |
| MR-03 | Consumo único ante confirmaciones concurrentes | 4 | CI: pendiente | 100 % | Pendiente |
| MR-04 | Recuperación coherente tras reinicio o pérdida del supervisor | 12 (1 + 11) | **CI: pendiente.** Dato complementario Lnx: 2/2 casos medidos (`http_restart`, `lifespan`) | 100 % | Pendiente del CI |
| MR-05 | Tiempo de recuperación (fase `call`, cota superior) | 17 | 17/17 medidos; **máximo 5 480 ms** (`http_restart`); comparación 3 310 ms; First Fit 190 ms | < 15 000 ms | ✅ Cumple (SPEC §5.3) |

Regla de medición del CI (SPEC §5.2): si la fase que contiene las pruebas termina con 0
fallidas, 0 errores y 0 omitidas, el numerador es igual al denominador. MR-01, MR-02,
MR-03 y `http_restart` están en la suite general; las 11 de supervisión de MR-04 están en el
proceso aislado `comparison-supervision`.

## CA-04 — Evidencia trazable

| Elemento | Dónde |
|---|---|
| Commit medido | `newglass-backend` `main` en `7a99663` (primera línea de [medicion-MR05.txt](medicion-MR05.txt)) |
| Suite local en Windows | "Salidas de comandos" → Suite completa |
| Denominadores | [collect-only.txt](collect-only.txt) |
| Tiempos de MR-05 | [medicion-MR05.txt](medicion-MR05.txt) (tabla de `--durations`, filas `call`) |
| Ejecución del CI | "Salidas de comandos" → CI (**pendiente**) |
| Resultado por prueba | Tablas CA-01 a CA-03, con `archivo::prueba` |
| Decisiones y alcance | SPEC §6 (D-01 a D-17) |

## Resultados por mecanismo y entorno

Resumen de la matriz de la SPEC §4.2 con lo medido hasta ahora.

| Mecanismo | Windows | PostgreSQL | Solo Linux |
|---|---|---|---|
| M1 Admisión | ✅ Win | CI: pendiente | CI: pendiente |
| M2 Supervisor | ✅ Win (`test_supervision_contracts.py`) | ✅ Lnx (`test_comparison_recovery.py`); resto CI: pendiente | CI: pendiente |
| M3 Reinicio | — | — | ✅ Lnx (`http_restart`, `lifespan`); resto CI: pendiente |
| M4 Fallo First Fit | — | ✅ Lnx (22 casos de `test_run_recovery.py`); resto CI: pendiente | — |
| M5 Confirmación | ✅ Win | CI: pendiente | — |
| M6 Reconciliación | ✅ Win | CI: pendiente | — |

## Entregables complementarios

| Entregable | Dónde | Estado |
|---|---|---|
| SPEC-TA-049 histórica | [SPEC-TA-049-presupuesto-tiempo.md](../../../specs/SPEC-TA-049-presupuesto-tiempo.md) | Recuperada desde `6798f60`, en Draft, con nota de que la reemplazan `ec46a7a` y [S2-TA049-recuperacion-pedidos.md](../../../reviews/S2-TA049-recuperacion-pedidos.md) |
| Riesgos residuales R-01 a R-07 y hallazgo H-01 | SPEC §9.2 | Documentados |
| Procedimiento de reconciliación en Staging | SPEC §9.3 | **Documentado, no ejecutado** (SPEC D-09) |
| Modelo de calidad (V-02 y V-18) | `docs/quality/ISO-25010-modelo-calidad.md` | Pendiente (F3) |

## Salidas de comandos

Comandos ejecutados por el responsable. Se registra el resumen de cada salida, y la salida
completa cuando se guardó en un archivo; no se adjuntan capturas (SPEC D-10).

### Suite completa del backend (Windows)

```powershell
# Desde la raíz de newglass-backend, rama test/TA-QA-006-port-security-tests, con el venv activo
python -m pytest tests -q --ignore=tests/unit/optimization/test_comparison_runner.py --ignore=tests/unit/optimization/test_sequential_runner.py --ignore=tests/unit/optimization/test_resource_profile.py
```

```text
2725 passed, 944 skipped, 1 warning
- 0 failed
- 944 skipped: pruebas de API e integración que necesitan PostgreSQL (las corre el CI)
- 1 warning: StarletteDeprecationWarning de fastapi/testclient (preexistente)
```

### Denominadores de MR-01 a MR-04 (Windows)

```powershell
# Desde la raíz de newglass-backend, rama test/TA-QA-006-port-security-tests, con el venv activo
python -m pytest tests/api/optimization/test_run_recovery.py tests/integration/optimization/test_run_recovery.py tests/integration/optimization/test_confirmation_rollback.py tests/integration/optimization/test_confirmation_concurrency.py tests/api/optimization/test_comparison_recovery.py tests/integration/optimization/test_comparison_v2_http_restart.py tests/integration/optimization/test_comparison_supervision_v2.py --collect-only -q
```

```text
68 tests collected in 0.97s
- 12 tests/api/optimization/test_run_recovery.py
- 10 tests/integration/optimization/test_run_recovery.py
-  9 tests/integration/optimization/test_confirmation_rollback.py
-  4 tests/integration/optimization/test_confirmation_concurrency.py
-  4 tests/api/optimization/test_comparison_recovery.py
-  1 tests/integration/optimization/test_comparison_v2_http_restart.py
- 28 tests/integration/optimization/test_comparison_supervision_v2.py (11 de ellos en MR-04)
Salida completa: collect-only.txt
```

### Medición de MR-05 (entorno de verificación Linux)

```bash
# Desde la raíz de newglass-backend, main en 7a99663; Linux, PostgreSQL 16.15, Python 3.13.18
NEWGLASS_REQUIRE_POSTGRES=1 python -m pytest tests/api/optimization/test_run_recovery.py tests/integration/optimization/test_run_recovery.py tests/api/optimization/test_comparison_recovery.py tests/integration/optimization/test_comparison_v2_http_restart.py "tests/integration/optimization/test_comparison_supervision_v2.py::test_fastapi_lifespan_recovers_and_shuts_down_real_v2_without_routes" -q --durations=0 --durations-min=0
```

```text
28 passed, 1 warning in 27.14s
- 0 failed
- 1 warning: StarletteDeprecationWarning de fastapi/testclient (preexistente; se filtró del archivo guardado)
Salida completa: medicion-MR05.txt
```

### CI de `newglass-backend`

En el CI, `NEWGLASS_REQUIRE_POSTGRES=1` hace que una prueba de PostgreSQL **falle en lugar
de omitirse** si falta el clúster (`tests/integration/postgres_support.py`). Por eso, un job
`backend` en verde con 0 omitidas por fase demuestra que las pruebas de MR-01 a MR-04 se
ejecutaron y pasaron.

```text
Run de GitHub Actions: (pendiente: enlace al run del PR de traslado de TA-QA-006 a main)
Job backend:           (pendiente: resultado)
Resumen por fase:      (pendiente: "Diagnóstico seguro de backend" del resumen del job)
```

## Hallazgos

| ID | Hallazgo | Tratamiento |
|---|---|---|
| — | **No se encontró ningún defecto de recuperación** en el código auditado ni falló ninguna prueba medida. | — |
| H-01 | El docstring de `scripts/reconcile_stuck_orders.py` indica ejecutar desde `backend\` (rutas del monorepo). | No se toca el script (SPEC D-08). Se avisa a Fabricio Melendez en el PR. |

## Limitaciones

- **MR-05 se midió fuera del CI**, en un entorno Linux con Python 3.13.18; el CI usa
  Python 3.11. El CI no publica tiempos por caso (SPEC §4.3, R-07); agregar `--durations`
  al CI queda como mejora recomendada (SPEC D-15).
- **En Windows se omiten 944 pruebas** de PostgreSQL. Las pruebas de solo Linux se ignoran
  con `--ignore` o se omiten. Su resultado depende del CI (SPEC R-06, D-07).
- **Disponibilidad** no se mide (SPEC D-06): V-02 queda cubierto en parte.
- **Riesgos de diseño documentados, no corregidos**: caída brusca de First Fit sin
  recuperación automática (R-01), admisión válida con un solo proceso (R-02), sin alerta de
  pedidos atascados (R-03) y caso D sin herramienta (R-04).
- La reconciliación en Staging **no se ejecutó** (SPEC D-09).

## Cómo reproducir

1. En `newglass-backend`, en `main` (o en una rama con `app/` igual a `main`), con el venv
   activo, correr la suite y el `collect-only` de "Salidas de comandos" desde la raíz.
2. En un entorno Linux con PostgreSQL, correr el comando de MR-05 y leer las filas `call`
   de `--durations`.
3. Revisar el resumen "Diagnóstico seguro de backend" del job `Backend CI` y aplicar la
   regla de medición de CA-03.
