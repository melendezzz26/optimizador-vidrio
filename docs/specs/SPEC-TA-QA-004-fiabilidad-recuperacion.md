# SPEC-TA-QA-004 — Fiabilidad y recuperación

## Información general

| Campo | Valor |
|---|---|
| ID | TA-QA-004 |
| Nombre | Fiabilidad y recuperación: escenarios de fallo, pruebas por entorno y métricas de fiabilidad |
| Tareas | T01 — Medir escenarios de fallo |
| Tipo | Tarea de calidad (auditoría, documentación y medición; sin cambios de código, de BD ni de despliegue) |
| Sprint | Sprint 2 |
| Versión | 1.4 |
| Estado | **Draft** |
| Responsable | Fabricio Danniel Aguilar Chavez (`fabrilar1`) |
| Reviewer | Andro Joseph Quispe Cesias (distinto del autor) |
| Rama | `docs/S2-TA-QA-004-fiabilidad` (repo `optimizador-vidrio`) |
| Base | `integration-02` en `e49a521` (después del PR #117) |
| Código auditado | `newglass-backend`, rama `main` en `7a99663` (repo independiente desde EN-REPO-001; su raíz es el antiguo `backend/`) |
| Fecha | 10/11/2026 |
| Característica ISO/IEC 25010 | Fiabilidad (§4.5 del modelo de calidad); cubre en parte el vacío **V-02** y la parte de TA-049 del vacío **V-18** |
| Evidencia | [docs/evidence/sprint-02/TA-QA-004](../evidence/sprint-02/TA-QA-004/README.md) |
| Referencias | [Modelo de calidad ISO 25010](../quality/ISO-25010-modelo-calidad.md) · [Matriz TA-QA-001](../quality/TA-QA-001-matriz-metricas-iso25023.md) · [SPEC-TA-049 (histórica)](SPEC-TA-049-presupuesto-tiempo.md) · [S2-TA049-recuperacion-pedidos.md](../reviews/S2-TA049-recuperacion-pedidos.md) · [TA-037 admission-lifecycle.md](../evidence/sprint-02/TA-037/admission-lifecycle.md) · [SPEC-TA-QA-006](SPEC-TA-QA-006-seguridad-permisos.md) |

## 1. Objetivo

Medir con las pruebas existentes **cómo se comporta el backend ante fallos simulados en
sus etapas críticas** (admisión, cálculo, desconexión, guardado del resultado, reinicio del
proceso y confirmación), demostrar que **no hay descuento duplicado de stock ni pedidos en
estados inconsistentes**, y medir la **tasa de éxito y el tiempo de recuperación** con las
métricas MR-01 a MR-05, que la matriz de TA-QA-001 no tiene (vacío V-02 del modelo de
calidad), sin editar esa matriz. Todo con evidencia trazable a pruebas, commits y
ejecuciones del CI.

Como entregables complementarios, recuperar la SPEC-TA-049 como documento histórico
(vacío V-18), registrar los riesgos residuales y dejar documentado, **sin ejecutarlo**, el
procedimiento recomendado para reconciliar pedidos atascados en Staging.

## 2. Alcance

### Incluye

- Auditoría de los mecanismos M1 a M6 (§4.1) sobre `newglass-backend` `main`.
- Matriz etapa crítica → fallo simulado → mecanismo → prueba → entorno (§4.2 y §8).
- Ejecución de la suite local del backend en Windows y enlace a una ejecución verde del
  CI de `newglass-backend` para las pruebas con PostgreSQL y las de solo Linux.
- Métricas MR-01 a MR-05 (§5.2), medidas en la evidencia.
- Entregables complementarios (§9): SPEC-TA-049 histórica, riesgos residuales,
  procedimiento de reconciliación no ejecutado y actualización de V-02 y V-18.

### Fuera de alcance

- **Cualquier cambio de código** en `newglass-backend` o `newglass-frontend`, incluidos el
  script `reconcile_stuck_orders.py` de Fabricio Melendez (D-08) y el workflow del CI.
- **Ejecutar `reconcile_stuck_orders`** (dry-run o apply) en Staging o en cualquier BD
  compartida, y cualquier acceso a Heroku o Supabase (D-09).
- **Disponibilidad**: medición del endpoint de salud en una ventana (D-06).
- Instalar PostgreSQL en Windows para correr localmente las pruebas de integración (D-07).
- Editar la matriz de TA-QA-001 (entregable de Andro) y MP-05, que sigue en TA-QA-002 (D-04, D-05).
- Cerrar la parte de V-18 sobre el respaldo de M6 (S2-WF-CARGA y SPEC-TA-053), que
  corresponde a TA-QA-002 / TA-QA-003 (D-11).
- Crear pruebas nuevas: se miden las existentes.

## 3. Actores y precondiciones

**Actores:** responsable de la tarea (auditoría y medición); equipo NewGlass (revisión y,
fuera de esta tarea, decisión sobre la reconciliación en Staging).

**Precondiciones:**

- `newglass-backend` `main` en `7a99663` o posterior, con su workflow `Backend CI`.
- Suite local con el comando del CI para Windows desde la raíz de `newglass-backend`
  (`python -m pytest tests -q` con los tres `--ignore` de las pruebas de solo Linux).
- Las pruebas de API e integración necesitan un clúster PostgreSQL aislado
  (`tests/integration/postgres_support.py`): en Windows, sin binarios locales, se omiten;
  en el CI (`NEWGLASS_REQUIRE_POSTGRES=1`) son obligatorias.

## 4. Situación actual (auditoría F0)

Auditoría de solo lectura sobre `newglass-backend` `main` en `7a99663` y
`optimizador-vidrio` `integration-02` en `e49a521`. Las rutas de código son relativas
a la raíz de `newglass-backend`.

### 4.1 Mecanismos de recuperación

| ID | Mecanismo | Evidencia | Comportamiento | Límite |
|---|---|---|---|---|
| M1 | Admisión acotada (`OPTIMIZER_BUSY`, 503 con `Retry-After: 15`) | `app/modules/optimization/application/admission.py`; `infrastructure/in_process_admission.py`; `presentation/run_routes.py` | 2 corridas por proceso (L-10) y 1 por usuario (L-11). Una comparación reserva todo el proceso y nunca coexiste con corridas. Liberar dos veces no libera otra plaza. | En memoria: válida con un solo proceso (`Procfile`: `--workers 1`). Varios procesos requieren un ADR. |
| M2 | Supervisor de comparaciones v2 (`RECOVERY_BLOCKED`, 503) | `presentation/comparison_supervision_v2.py`; `presentation/comparison_v2_routes.py`; `infrastructure/process_lifecycle.py` | Si no puede probar que el supervisor y los trabajadores pararon (PID y tiempo de inicio en `/proc`), mantiene la admisión reservada y responde `RECOVERY_BLOCKED`. No mata procesos ni recalcula. | La prueba de parada depende de `/proc` (Linux). En una plataforma sin `/proc` la comparación queda bloqueada a propósito. |
| M3 | Recuperación al reiniciar el proceso | `main.py` (`lifespan`: `recover_pending()` al arrancar, `shutdown()` al cerrar) | Al arrancar revisa las comparaciones sin terminar y las cierra solo con prueba de parada; los pedidos pasan a `OPTIMIZADO` (si hay un resultado elegible) o a `PENDIENTE`. | Solo cubre comparaciones. Una corrida First Fit no tiene identidad de proceso durable. |
| M4 | Fallo controlado de First Fit (TA-049) | `infrastructure/run_uow.py` (`fail`, `recover_stopped`); `application/run_recovery.py`; `scripts/recover_stopped_run.py` (commit `ec46a7a`) | Ante timeout, error del motor, desconexión o fallo al guardar: la corrida queda `FALLIDA` y los pedidos vuelven a `PENDIENTE` en una sola transacción, después del rollback y verificando que no hay consumo. Un aviso tardío no sobrescribe un resultado terminal. | Una caída brusca no ejecuta `finally`: se recupera con `recover_stopped_run ID --service-stopped`, que exige detener el servicio. La bandera es una declaración del operador, no una verificación de PID. |
| M5 | Confirmación transaccional | `application/confirmation.py`; `infrastructure/confirmation_adapter.py` | Bloquea la corrida, exige pedidos en `OPTIMIZADO`, descuenta stock y crea retazos en una sola transacción. `ALREADY_CONFIRMED` impide un segundo consumo. | — |
| M6 | Reconciliación de pedidos atascados | `scripts/reconcile_stuck_orders.py` → `application/order_reconciliation.py` → `infrastructure/order_reconciliation_repository.py` | Dry-run por defecto. Clasifica cada pedido en `EN_OPTIMIZACION`: A (sin optimización), B (todas terminales, sin consumo ni confirmación), C (alguna `EN_EJECUCION`), D (`COMPLETADA` sin liberar), E (consumo o confirmación). Con `--apply` solo A y B vuelven a `PENDIENTE`: una transacción por pedido, `SELECT … FOR UPDATE` y nueva clasificación dentro de ella. `--order` limita a pedidos concretos; `--report -` imprime un JSON. | C, D y E solo se informan. Ninguna herramienta corrige D. Sin "deshacer". |

### 4.2 Pruebas por mecanismo y entorno

✅ corre en Windows · ⏭️ PostgreSQL: en Windows se omite, en el CI es obligatoria · 🐧 solo Linux (proceso de pytest aparte en el CI o comando local con `--ignore`).

| Mecanismo | ✅ Windows | ⏭️ PostgreSQL (CI) | 🐧 Solo Linux |
|---|---|---|---|
| M1 | `tests/unit/optimization/test_run_admission.py` | `tests/api/optimization/test_run_concurrency.py`; `tests/integration/optimization/test_start_concurrency.py` | `tests/unit/optimization/test_sequential_runner.py` |
| M2 | `tests/unit/optimization/test_supervision_contracts.py`; `test_run_admission.py::test_new_request_retries_safe_recovery_before_reserving_capacity` | `tests/api/optimization/test_comparisons_v2_api.py`; `tests/api/optimization/test_comparison_recovery.py`; `tests/api/optimization/test_comparison_connection_lifecycle.py` | `tests/integration/optimization/test_comparison_supervision_v2.py`; `tests/unit/optimization/test_comparison_runner.py` |
| M3 | — | — | `tests/integration/optimization/test_comparison_v2_http_restart.py` (reinicio real de Uvicorn); `test_comparison_supervision_v2.py::test_fastapi_lifespan_recovers_and_shuts_down_real_v2_without_routes` |
| M4 | — | `tests/api/optimization/test_run_recovery.py`; `tests/integration/optimization/test_run_recovery.py`; `tests/integration/optimization/test_run_states.py`; `test_run_concurrency.py::test_time_budget_stops_the_run_as_failed_and_frees_the_slot` | — |
| M5 | `tests/unit/optimization/test_confirmation.py` | `tests/integration/optimization/test_confirmation_rollback.py`; `tests/integration/optimization/test_confirmation_concurrency.py`; `tests/integration/optimization/test_confirmation.py`; `tests/api/optimization/test_confirmation_api.py` | — |
| M6 | `tests/unit/optimization/test_stuck_order_reconciliation_unit.py` | `tests/integration/optimization/test_stuck_order_reconciliation_pg.py` | — |
| Salud (contexto) | — | `tests/api/test_health_api.py`; `tests/integration/test_health_database.py` | — |

Conclusión: en Windows solo se ejercitan cuatro archivos unitarios de este grupo. Las
transacciones, el reinicio y la reconciliación real se verifican en el CI. Por eso la
evidencia combina la suite local con una ejecución verde del CI (CA-04).

El comando local de Windows ignora `test_resource_profile.py`, que el CI de
`newglass-backend` sí corre en su suite general. No es un defecto: es una diferencia
conocida entre entornos.

### 4.3 Qué publica el CI de `newglass-backend`

| Hecho | Evidencia |
|---|---|
| El job ejecuta una suite general y cuatro procesos aislados (`test_comparison_calculation.py`, `test_comparison_supervision_v2.py`, `test_sequential_runner.py`, `test_comparison_runner.py`), cada uno con `-q -ra --junitxml`. | `.github/workflows/ci.yml`, paso "Run tests" |
| Los JUnit se escriben en `$RUNNER_TEMP` y **no se suben** como artefacto. Solo se sube y se muestra en el resumen del job un informe con, por fase, aprobadas, fallidas, errores y omitidas, y los nombres de los casos fallidos. | Pasos "Summarize backend failures safely" y "Preserve sanitized backend summary"; `.github/scripts/backend_failure_summary.py` |
| Con `-q` el log no muestra los nombres de los casos ni sus tiempos. | `.github/workflows/ci.yml` |

Consecuencia para la medición: las tasas MR-01 a MR-04 se pueden medir con el resumen por
fase (§5.2); los tiempos por caso de MR-05 no están disponibles en el CI, así que MR-05 se
mide con `pytest --durations` en un entorno Linux con PostgreSQL (D-15, §5.3).

## 5. Reglas verificadas y métricas

### 5.1 Reglas verificadas

Comportamiento existente que esta tarea comprueba con las pruebas de §4.2; no se cambia.

- RN-01: La admisión nunca supera 2 corridas por proceso ni 1 por usuario; una comparación
  no coexiste con corridas; una solicitud rechazada responde `OPTIMIZER_BUSY` sin efectos y
  sin perder plazas (M1).
- RN-02: Sin prueba de parada de los procesos de una comparación, la admisión queda
  reservada y la API responde `RECOVERY_BLOCKED`; nunca se recalcula (M2, M3).
- RN-03: Una corrida o comparación que falla de forma controlada queda en un estado final
  y sus pedidos vuelven a `PENDIENTE` sin consumo. Si hay inconsistencia o consumo, no hay
  reinicio parcial (M2, M4).
- RN-04: Un error durante la confirmación deshace todas sus escrituras; dos
  confirmaciones concurrentes producen como máximo un consumo (M5).
- RN-05: La reconciliación no escribe sin `--apply` y, con `--apply`, solo cambia los
  casos A y B (M6).

### 5.2 Métricas de fiabilidad

Métricas del proyecto, inspiradas en las medidas de recuperabilidad, tolerancia a fallos y
ausencia de fallos de ISO/IEC 25023; las metas son del proyecto, no de la norma. Cubren el
vacío V-02 salvo disponibilidad (D-06), sin editar la matriz de TA-QA-001.

**Cómo se cuentan los casos (MR-01 a MR-04).** Los casos parametrizados cuentan por
separado. El denominador de cada métrica se obtiene con `pytest --collect-only -q` sobre sus
pruebas (funciona en Windows aunque luego se omitan). El numerador sale del resumen del CI:
si la fase que contiene esas pruebas termina con 0 fallidas, 0 errores y 0 omitidas, todos
sus casos se aprobaron.

| ID | Métrica | Subcaracterística | Fórmula | Meta | Pruebas | Fuente |
|---|---|---|---|---|---|---|
| MR-01 | Recuperación de pedidos tras un fallo controlado | Recuperabilidad | casos aprobados ÷ casos ejecutados × 100. Cada caso verifica RN-03: estado final y pedidos en `PENDIENTE` sin consumo, o bloqueo sin reinicio parcial ante inconsistencia | 100 % | `tests/api/optimization/test_run_recovery.py`; `tests/integration/optimization/test_run_recovery.py`; `tests/api/optimization/test_comparison_recovery.py` | CI, suite general (PostgreSQL) |
| MR-02 | Atomicidad de la confirmación ante errores | Tolerancia a fallos | casos en que el error deja stock, movimientos, retazos y pedidos sin cambios ÷ casos ejecutados × 100 | 100 % | `tests/integration/optimization/test_confirmation_rollback.py` | CI, suite general (PostgreSQL) |
| MR-03 | Consumo único ante confirmaciones concurrentes | Ausencia de fallos | casos que terminan con exactamente un consumo o un rechazo controlado ÷ casos ejecutados × 100 | 100 % | `tests/integration/optimization/test_confirmation_concurrency.py` | CI, suite general (PostgreSQL) |
| MR-04 | Recuperación coherente tras reinicio o pérdida del supervisor | Recuperabilidad | casos aprobados ÷ casos ejecutados × 100. Cada caso verifica RN-02: cierre sin recalcular solo con prueba de parada, o bloqueo con admisión reservada | 100 % | `tests/integration/optimization/test_comparison_v2_http_restart.py`; de `test_comparison_supervision_v2.py`: `test_startup_recovery_ignores_standalone_ff_and_keeps_invalid_comparison_reserved`, `test_recovery_requires_process_identity_proof_without_recalculation`, `test_fastapi_lifespan_recovers_and_shuts_down_real_v2_without_routes`, `test_failed_closure_commit_keeps_lease_until_successful_retry`, `test_recovery_on_unsupported_platform_keeps_block_without_pid_inference` | CI: suite general (`http_restart`) y proceso aislado de supervisión (solo Linux) |
| MR-05 | Tiempo de recuperación | Recuperabilidad | tiempo desde el fallo inyectado hasta que los pedidos vuelven a `PENDIENTE` (o la comparación queda cerrada tras el reinicio), medido como **cota superior** con el tiempo de la fase `call` de cada caso según `pytest --durations=0 --durations-min=0` (excluye `setup` y `teardown`). Se informa el máximo de cada grupo y el máximo global, en ms | máximo < 15 000 ms (`Retry-After` de la admisión) | Ver lista de MR-05 abajo | `pytest --durations`, fase `call`, en un entorno Linux con PostgreSQL (D-15, §5.3) |

**Pruebas de MR-05** (17 casos, todos medidos en la ejecución de §5.3):

| Grupo | Prueba | Caso | Fin de la recuperación que verifica | Tiempo `call` |
|---|---|---|---|---|
| Corrida First Fit | `tests/api/optimization/test_run_recovery.py::test_stopped_engine_releases_entire_batch_and_can_retry` | `[False-TimeBudgetExceeded-TIME_BUDGET_EXCEEDED]` | `assert_released`: corrida `FALLIDA` y pedidos en `PENDIENTE` | 190 ms |
| | | `[True-ExecutionInterrupted-EXECUTION_INTERRUPTED]` | Ídem | 170 ms |
| | | `[True-RuntimeError-CALCULATION_FAILED]` | Ídem | 160 ms |
| | | `[True-TimeBudgetExceeded-TIME_BUDGET_EXCEEDED]` | Ídem | 140 ms |
| | | `[False-RuntimeError-CALCULATION_FAILED]` | Ídem | 130 ms |
| | | `[False-ExecutionInterrupted-EXECUTION_INTERRUPTED]` | Ídem | 110 ms |
| | `…::test_failed_result_flush_rolls_back_then_releases_in_separate_transaction` | — | Ídem (`RESULT_SAVE_FAILED`) | 90 ms |
| | `…::test_deadline_after_last_engine_checkpoint_cannot_commit_no_solution` | — | Ídem (`TIME_BUDGET_EXCEEDED`) | 60 ms |
| | `…::test_worker_start_failure_recovers_accepted_orders` | — | Ídem (`EXECUTION_INTERRUPTED`) | 40 ms |
| | `…::test_error_constructing_stream_after_acceptance_is_propagated_and_recovers` | — | Ídem (`EXECUTION_INTERRUPTED`) | 40 ms |
| | `…::test_disconnect_before_body_iterator_starts_recovers_accepted_batch` | — | Ídem (`EXECUTION_INTERRUPTED`) | 30 ms |
| Comparación por plazo | `tests/api/optimization/test_comparison_recovery.py::test_comparison_deadline_releases_only_after_stop_and_allows_new_work` | `[v2-calculation]` | Pedidos en `PENDIENTE` después de la parada | 3 310 ms |
| | | `[v2-global]` | Ídem | 2 010 ms |
| | | `[v1-calculation]` | Ídem | 830 ms |
| | | `[v1-global]` | Ídem | 660 ms |
| Reinicio del proceso | `tests/integration/optimization/test_comparison_v2_http_restart.py::test_real_http_disconnect_then_backend_restart_never_recalculates` | — | Comparación cerrada tras reiniciar Uvicorn | **5 480 ms** |
| | `tests/integration/optimization/test_comparison_supervision_v2.py::test_fastapi_lifespan_recovers_and_shuts_down_real_v2_without_routes` | — | Comparación cerrada (`terminal`) por el `lifespan` | 700 ms |

Los tiempos se toman de las filas `call` de
[medicion-MR05.txt](../evidence/sprint-02/TA-QA-004/medicion-MR05.txt), que `pytest`
informa con resolución de 10 ms.

No se incluye `test_failure_of_recovery_commit_is_visible_and_requires_reconciliation`: sus
pedidos solo vuelven a `PENDIENTE` después de una reconciliación explícita, que no es una
recuperación automática.

**Por qué sigue siendo una cota superior.** La fase `call` excluye la preparación de la BD
(`setup`) y la limpieza (`teardown`), pero incluye lo que la prueba hace antes del fallo
(crear la solicitud, arrancar el cálculo o el servidor) y sus verificaciones posteriores.
Por eso sobrestima el tiempo de recuperación real: si la cota cumple la meta, la
recuperación también la cumple.

MP-05 (ejecuciones completas sobre iniciadas) sigue siendo la métrica de continuidad de
TA-QA-002 y no se mide aquí (D-05).

### 5.3 Medición de MR-05

| Campo | Valor |
|---|---|
| Código medido | `newglass-backend`, `main` en `7a99663` |
| Entorno | Entorno de verificación Linux (Ubuntu 24.04) con PostgreSQL 16.15 y Python 3.13.18. **No es el CI**, que usa Python 3.11 (ubuntu-24.04). |
| Directorio | Raíz de `newglass-backend` |
| Comando | `NEWGLASS_REQUIRE_POSTGRES=1 python -m pytest tests/api/optimization/test_run_recovery.py tests/integration/optimization/test_run_recovery.py tests/api/optimization/test_comparison_recovery.py tests/integration/optimization/test_comparison_v2_http_restart.py "tests/integration/optimization/test_comparison_supervision_v2.py::test_fastapi_lifespan_recovers_and_shuts_down_real_v2_without_routes" -q --durations=0 --durations-min=0` |
| Resultado | **28 passed, 0 failed**, 1 warning, en 27,14 s: los 27 casos de los cuatro archivos (12 + 10 + 4 + 1) más el caso `lifespan`. Coincide con el conteo de los casos en el código. |
| Fase usada | `call` de la tabla de `--durations` (se descartan las filas `setup` y `teardown`) |
| Salida completa | [docs/evidence/sprint-02/TA-QA-004/medicion-MR05.txt](../evidence/sprint-02/TA-QA-004/medicion-MR05.txt) |

Esta ejecución única reemplaza la medición anterior, que sumaba dos corridas superpuestas
(31 casos).

| Grupo | Casos | Máximo `call` |
|---|---|---|
| Corrida First Fit | 11 | 190 ms |
| Comparación por plazo | 4 | 3 310 ms (`v2-calculation`) |
| Reinicio del proceso | 2 | 5 480 ms (`http_restart`) |
| **Máximo global de MR-05** | **17** | **5 480 ms < 15 000 ms → cumple** |

Tiempos medidos fuera de MR-05, solo informativos:
`tests/integration/optimization/test_run_recovery.py`, 20–80 ms por caso, salvo
`test_abrupt_process_exit_requires_explicit_offline_reconciliation`, 550 ms (su recuperación
requiere `recover_stopped_run`, no es automática);
`test_failure_of_recovery_commit_is_visible_and_requires_reconciliation`, 80 ms.

El resumen de advertencias de la salida no detalla la advertencia (1 warning). No afecta al
resultado: ningún caso falló.

## 6. Decisiones y preguntas abiertas

### Decisiones

| ID | Decisión | Motivo |
|---|---|---|
| D-01 | La tarea no toca Heroku, la BD ni el código: auditoría, documentación y medición. | Decisión del responsable (recorte de alcance después de F0, 10/11/2026). |
| D-02 | La SPEC-TA-049 se trae desde `6798f60` como histórica: queda en Draft, con una nota al inicio que indica que la reemplazan `ec46a7a` y `docs/reviews/S2-TA049-recuperacion-pedidos.md`. Su contenido no se modifica. | Decisión del responsable (P-06 de F0). El código integrado amplió el alcance de esa SPEC; actualizarla reescribiría una decisión ajena. |
| D-03 | La SPEC y la evidencia van en `optimizador-vidrio`, rama `docs/S2-TA-QA-004-fiabilidad` desde `integration-02`. | Decisión del responsable (P-07 de F0). Ahí están las SPEC y el modelo de calidad existentes. |
| D-04 | Las métricas usan el prefijo MR-xx en esta SPEC; no se edita la matriz de TA-QA-001. | Decisión del responsable (P-08 de F0). La matriz es entregable de Andro. |
| D-05 | MP-05 sigue asignada a TA-QA-002. | Asignación del modelo de calidad (V-02). |
| D-06 | Disponibilidad (endpoint de salud en una ventana fijada) queda fuera de alcance; V-02 queda cubierto en parte. | Decisión del responsable (P-09 de F0). Requiere acceso a Heroku y una herramienta de sondeo. |
| D-07 | No se instala PostgreSQL en Windows: las pruebas con PostgreSQL y las de solo Linux se evidencian con el CI. | Decisión del responsable (P-10 de F0). |
| D-08 | No se modifica `scripts/reconcile_stuck_orders.py`; su docstring desactualizado se registra como H-01. | Decisión del responsable (P-11 de F0). Es código de Fabricio Melendez. |
| D-09 | La reconciliación en Staging solo se documenta (§9.3); no se ejecuta. | Decisión del responsable (P-01 a P-05 de F0). |
| D-10 | Las salidas de los comandos se registran como texto en "Salidas de comandos" de la evidencia; no se adjuntan capturas. | Decisión del responsable, igual que en TA-QA-006. |
| D-11 | En el modelo de calidad solo se actualizan V-02 (cobertura parcial con MR-01 a MR-05) y la parte de TA-049 de V-18. La parte de V-18 sobre el respaldo de M6 (S2-WF-CARGA y SPEC-TA-053) no se cierra. | Decisión del responsable (F1). Esa parte corresponde a TA-QA-002 / TA-QA-003. |
| D-12 | Los criterios de aceptación son exactamente los cuatro de Notion para TA-QA-004 (T01 — Medir escenarios de fallo), con sus mecanismos, pruebas y métricas (§8). Lo que no es criterio de Notion (SPEC-TA-049 histórica, riesgos residuales, procedimiento de reconciliación y actualización de V-02 y V-18) pasa a "Entregables complementarios" (§9). Reemplaza los CA-01 a CA-06 de la versión 1.0, derivados de F0. | Decisión del responsable (cierre de P-01 de F1, 10/11/2026). |
| D-13 | Se agrega MR-05 "Tiempo de recuperación (ms)", medido como cota superior, con meta menor que el `Retry-After` de 15 s. La fuente inicial (JUnit del CI) se reemplazó por la de D-15. | Decisión del responsable (F1, 10/11/2026), para cubrir "tiempo de recuperación" de CA-03. |
| D-14 | MR-01 mide corridas y comparaciones (incluye `test_comparison_recovery.py`) y deja fuera `test_run_concurrency.py::test_time_budget_stops_the_run_as_failed_and_frees_the_slot`. | Corrección de F1: esa prueba verifica `FALLIDA`, que no hubo consumo y que se liberó la plaza, pero no el estado de los pedidos que exige RN-03. Sigue en la matriz §4.2 (M4) y en CA-01. |
| D-15 | MR-05 se mide con `pytest --durations=0 --durations-min=0`, tomando solo la fase `call`, en un entorno Linux con PostgreSQL; el entorno y el comando quedan registrados en §5.3. Agregar `--durations` al CI de `newglass-backend` queda como **mejora recomendada** a Fabricio Melendez, no como requisito de esta tarea. | Decisión del responsable (cierre de P-02 con la opción c, 10/11/2026). El CI no publica tiempos por caso (§4.3), y la fase `call` excluye la preparación de la BD, que distorsionaba la cota. |
| D-16 | El caso `test_comparison_supervision_v2.py::test_fastapi_lifespan_recovers_and_shuts_down_real_v2_without_routes` se mantiene en MR-05 y se mide en la misma ejecución de §5.3, seleccionado por su id de nodo. Esa ejecución única reemplaza la medición anterior. | Decisión del responsable (cierre de P-03 con la opción a, 11/11/2026). Así los 17 casos de MR-05 tienen tiempo medido en una sola corrida reproducible. |
| D-17 | La suite local de Windows y el `collect-only` se ejecutan en `newglass-backend`, rama `test/TA-QA-006-port-security-tests` (`main` en `7a99663` más 3 archivos de prueba de seguridad, sin cambios en `app/`). La ejecución de CI que se enlaza es la del PR de traslado de esas pruebas a `main`. | Decisión del responsable (F2, 11/11/2026). El código de la aplicación y las pruebas de fiabilidad son idénticos a `main`; solo se suman 3 archivos de prueba que no tocan los mecanismos M1 a M6. |

### Preguntas abiertas

Ninguna. P-01 (criterios de Notion) se cerró con D-12, P-02 (fuente de MR-05) con D-15 y
P-03 (caso `lifespan`) con D-16.

## 7. Diseño técnico

| Archivo | Repo / capa | Cambio | Fase |
|---|---|---|---|
| `docs/specs/SPEC-TA-QA-004-fiabilidad-recuperacion.md` | `optimizador-vidrio` / Documentación | Nuevo: esta SPEC. | F1 |
| `docs/specs/SPEC-TA-049-presupuesto-tiempo.md` | `optimizador-vidrio` / Documentación | Recuperada desde `6798f60` sin cambiar su contenido; nota histórica al inicio y una línea de historial (D-02). | F1 |
| `docs/evidence/sprint-02/TA-QA-004/README.md` | `optimizador-vidrio` / Evidencia | Nuevo: resultados por criterio (§8), MR-01 a MR-05, riesgos residuales, enlace al CI de `newglass-backend` y "Salidas de comandos". | F2 |
| `docs/quality/ISO-25010-modelo-calidad.md` | `optimizador-vidrio` / Documentación | §4.5 y V-02 (cobertura parcial), nota de TA-049 en V-18 sin cerrar la parte de M6, y línea de historial (D-11). | F3 |

Sin cambios en `newglass-backend`, `newglass-frontend`, migraciones, contrato de la API,
workflows, Heroku ni Supabase.

## 8. Criterios de aceptación

Criterios de Notion para TA-QA-004, T01 — Medir escenarios de fallo (D-12).

| ID | Criterio (Notion) | Mecanismos | Pruebas | Métricas | Cómo se verifica |
|---|---|---|---|---|---|
| CA-01 | Fallos simulados en etapas críticas. | M1 a M5 | Admisión y arranque: `test_run_admission.py`, `test_run_concurrency.py` (rechazo, fallo del cálculo, desconexión, plazo, fallo al iniciar el hilo). Cálculo, desconexión y guardado: `api/test_run_recovery.py`, `integration/test_run_recovery.py` (incluye salida abrupta real), `test_comparison_recovery.py`. Procesos de la comparación: `test_comparison_supervision_v2.py` (caída de un motor, fallo de escritura, fallo de arranque de un proceso). Reinicio: `test_comparison_v2_http_restart.py`. Confirmación: `test_confirmation_rollback.py`. | MR-01, MR-02, MR-04 | Tabla en la evidencia: etapa → fallo simulado → mecanismo → prueba → entorno (Windows, PostgreSQL en el CI, solo Linux) → resultado. |
| CA-02 | Sin descuento duplicado ni pedidos inconsistentes. | M4, M5, M6 | `test_confirmation_concurrency.py` (misma optimización dos veces, carrera por el último retazo o plancha); `test_confirmation_rollback.py`; `integration/test_run_recovery.py` (lote inconsistente sin reinicio parcial, dos fallos que nunca liberan a otro dueño, aviso tardío); `test_stuck_order_reconciliation_unit.py` y `test_stuck_order_reconciliation_pg.py` (solo A y B cambian). | MR-02, MR-03 | MR-02 = 100 % y MR-03 = 100 % en el CI; casos de lote inconsistente y de reconciliación en verde. |
| CA-03 | Tiempo de recuperación y tasa de éxito. | M1 a M4 | Las de MR-01, MR-04 y MR-05 (§5.2). | MR-01, MR-04 (tasa de éxito); MR-05 (tiempo) | MR-01 y MR-04 medidas con su denominador y el resumen del CI. MR-05 medida con `pytest --durations`, fase `call`, en sus 17 casos (D-15, D-16, §5.3): máximo 5 480 ms < 15 000 ms. |
| CA-04 | Evidencia trazable. | — | Suite local de Windows y `Backend CI` de `newglass-backend` | Todas | `docs/evidence/sprint-02/TA-QA-004/README.md` con: commit de `newglass-backend` medido, enlace a la ejecución del CI del PR de traslado a `main` (id y fecha; D-17), suite local con `0 failed` y omisiones explicadas, denominadores de `--collect-only` (`collect-only.txt`), cada resultado ligado a `archivo::prueba`, y las salidas de los comandos en texto (D-10). |

## 9. Entregables complementarios

No son criterios de aceptación de Notion, pero forman parte del PR (D-12).

### 9.1 SPEC-TA-049 histórica

`docs/specs/SPEC-TA-049-presupuesto-tiempo.md` en Draft, con contenido igual a `6798f60`
salvo la nota inicial, la línea de historial y la limpieza de `<>` (D-02).

| Hecho | Evidencia |
|---|---|
| La SPEC solo existe en el commit `6798f60` (04/11/2026, `docs(TA-049): define optimization deadline contract`), en `feature/S2-TA049-presupuesto-tiempo`, local y en `origin`. | `git log --all -- docs/specs/SPEC-TA-049-presupuesto-tiempo.md`; `git branch -a --contains 6798f60` |
| No está en `integration-02`. | `git merge-base --is-ancestor 6798f60 origin/integration-02` → no es ancestro |
| El arreglo integrado es `ec46a7a` (06/11/2026), con el informe `docs/reviews/S2-TA049-recuperacion-pedidos.md`, que leyó la SPEC en `6798f60` sin fusionarla y amplió su alcance. | `git show --stat ec46a7a` |
| El stash local "TA-049 T02 en progreso" también la toca; no se aplica ni se usa. | `git log --all` (`refs/stash`) |

### 9.2 Riesgos residuales y hallazgos

| ID | Riesgo | Mitigación actual | Tratamiento |
|---|---|---|---|
| R-01 | Una caída brusca durante una corrida First Fit deja sus pedidos en `EN_OPTIMIZACION`: no hay identidad de proceso durable ni recuperación automática. | `recover_stopped_run --service-stopped` con el servicio detenido; `reconcile_stuck_orders` informa el caso C. | Se documenta; fuera de alcance. |
| R-02 | La admisión en memoria solo es válida con un proceso. | `Procfile` con `--workers 1`. | Se documenta; escalar requiere ADR. |
| R-03 | No hay detección ni alerta de pedidos atascados: depende de un dry-run manual. | `reconcile_stuck_orders` en dry-run. | Se documenta; fuera de alcance. |
| R-04 | El caso D (`COMPLETADA` sin liberar) no tiene herramienta de corrección. | Se informa en el dry-run. | Revisión manual del equipo (§9.3). |
| R-05 | El despliegue es manual en un solo dyno: tras un merge la demo puede mostrar una versión anterior, y sin medición de disponibilidad no hay dato de caídas. | Redespliegue manual. | Disponibilidad fuera de alcance (D-06); V-02 queda abierto en esa parte. |
| R-06 | En Windows casi todas las pruebas de fiabilidad se omiten. | El CI las corre como obligatorias. | Evidencia de CI (D-07). |
| R-07 | El CI no publica los JUnit ni los tiempos por caso (§4.3): MR-05 no se puede medir en cada PR. | Resumen por fase en el job; MR-05 medida fuera del CI (D-15). | Mejora recomendada a Fabricio Melendez: agregar `--durations` al CI. |

| ID | Hallazgo | Tratamiento |
|---|---|---|
| H-01 | El docstring de `scripts/reconcile_stuck_orders.py` todavía indica ejecutar desde `backend\` y, en Heroku, `cd backend`, que son rutas del monorepo. En `newglass-backend` el comando corre desde la raíz. | No se toca el script (D-08). El procedimiento §9.3 usa la ruta correcta. Se avisa a Fabricio Melendez en el PR. |
| — | No se encontró ningún defecto de recuperación en el código auditado. | — |

### 9.3 Procedimiento recomendado de reconciliación en Staging (no ejecutado)

Procedimiento documentado para que el equipo lo use cuando lo decida. **En esta tarea no se
ejecuta ningún paso** (D-09).

1. **Precondiciones (decisión del equipo).** Acordar qué app de Heroku y qué base de datos
   son Staging, confirmar que despliegan `newglass-backend` y quién tiene acceso a
   `heroku run`. Hacerlo fuera de una demo.
2. **Dry-run.** Sobre la app acordada, desde la raíz de `newglass-backend`:
   `python -m scripts.reconcile_stuck_orders --report -`. La salida (tabla y JSON) se guarda
   en la máquina de quien ejecuta: el sistema de archivos del dyno es efímero. El informe
   solo contiene IDs, estados y casos; no contiene secretos.
3. **Revisión del equipo.** Revisar el informe: lista de pedidos A y B que se devolverán a
   `PENDIENTE` y qué se hace con C, D y E. Registrar quién aprueba y cuándo.
4. **Registro previo.** Conservar el JSON del dry-run como registro de los estados
   anteriores: el script no tiene "deshacer".
5. **Apply con lista cerrada.** Solo con el OK registrado:
   `python -m scripts.reconcile_stuck_orders --apply --report -` con un `--order` por cada
   pedido aprobado. Una lista cerrada evita tocar pedidos que se atascaron después del
   dry-run.
6. **Verificación.** Repetir el dry-run: ninguno de los pedidos aprobados debe seguir en
   A o B. Los cambios quedan además en el log (`Pedido … reconciliado`).
7. **Casos fuera del procedimiento.** C requiere `recover_stopped_run` con el servicio
   detenido (ventana de mantenimiento); D y E requieren revisión manual. Ninguno se toca
   con este procedimiento.

### 9.4 Modelo de calidad

En F3: V-02 con la cobertura parcial de MR-01 a MR-05 y disponibilidad pendiente; nota de
TA-049 en V-18 sin cerrar la parte de M6; línea de historial que cita TA-QA-004 (D-11).

## 10. Pruebas previstas

No se crean pruebas: se ejecutan y miden las existentes.

| Ejecución | Dónde | Resultado esperado |
|---|---|---|
| Suite completa con el comando del CI para Windows (§3) | Windows, raíz de `newglass-backend` | `0 failed`; pruebas de PostgreSQL omitidas por falta de binarios locales |
| Archivos de §4.2 que corren en Windows, con `-ra` | Windows | Unitarios en verde; los de PostgreSQL omitidos con su motivo |
| `pytest --collect-only -q` sobre las pruebas de MR-01 a MR-05 | Windows | Denominadores de cada métrica |
| `Backend CI` (suite general con PostgreSQL y los cuatro procesos aislados) | GitHub Actions de `newglass-backend`, PR de traslado a `main` (D-17) | Ejecución verde con 0 fallidas, 0 errores y 0 omitidas por fase; base para MR-01 a MR-04 |
| Comando de §5.3 con `--durations=0 --durations-min=0` | Entorno Linux con PostgreSQL | 0 failed; tiempos `call` para MR-05 (D-15) |

## 11. Evidencia requerida

- `docs/evidence/sprint-02/TA-QA-004/README.md` con:
  - la tabla de fallos simulados por etapa (CA-01);
  - los resultados de no duplicación e inconsistencia, MR-02 y MR-03 (CA-02);
  - MR-01, MR-04 y MR-05 con su denominador, valor y fuente (CA-03), con enlace a
    `medicion-MR05.txt` (salida completa del comando de §5.3 con la tabla de `--durations`);
  - la trazabilidad: commit medido, ejecución del CI, suite local y salidas de los
    comandos en texto, sin capturas (CA-04, D-10);
  - los entregables complementarios de §9.2 y §9.3, este último marcado como no ejecutado.

## Historial de estado

| Fecha | Versión | Estado | Cambio |
|---|---|---|---|
| 10/11/2026 | 1.0 | Draft | Creación con la auditoría F0 (M1 a M6 y pruebas por entorno), recorte de alcance, métricas MR-01 a MR-04, riesgos R-01 a R-06, hallazgo H-01, procedimiento de reconciliación no ejecutado, decisiones D-01 a D-12 y criterios CA-01 a CA-06. |
| 10/11/2026 | 1.1 | Draft | Criterios reemplazados por los cuatro de Notion (T01), con mecanismos, pruebas y métricas (D-12). Nueva sección "Entregables complementarios" (SPEC-TA-049 histórica, riesgos, procedimiento, modelo de calidad). Nueva MR-05 "Tiempo de recuperación (ms)" con sus 11 casos (D-13). MR-01 corregida (D-14). Auditoría de lo que publica el CI (§4.3), riesgo R-07 y pregunta abierta P-02. P-01 cerrada. |
| 10/11/2026 | 1.2 | Draft | P-02 cerrada con D-15: MR-05 se mide con `pytest --durations`, fase `call`, en un entorno Linux con PostgreSQL; `--durations` en el CI queda como mejora recomendada. Nueva §5.3 con entorno, comando y resultado (máximo 5 070 ms < 15 000 ms, cumple). Tabla de MR-05 con el tiempo de cada caso y conteos corregidos (6 y 4 casos parametrizados; 17 casos, 16 medidos). Conteo 27/31 por conciliar en F2. Nueva pregunta abierta P-03 (caso `lifespan` sin tiempo). |
| 11/11/2026 | 1.3 | Draft | Nueva medición única de MR-05 que reemplaza la anterior (28 passed, 0 failed; PostgreSQL 16.15, Python 3.13.18), con el caso `lifespan` incluido: P-03 cerrada con D-16. Tabla de MR-05 con el tiempo `call` de cada uno de los 17 casos; máximo 5 480 ms < 15 000 ms. Conteo conciliado (27 + 1 = 28; el 31 anterior sumaba dos corridas). Salida guardada en `docs/evidence/sprint-02/TA-QA-004/medicion-MR05.txt`. |
| 11/11/2026 | 1.4 | Draft | Evidencia F2 creada (README, `collect-only.txt`). D-17: suite local y `collect-only` en `test/TA-QA-006-port-security-tests` (sin cambios en `app/`) y CI del PR de traslado a `main`. Denominadores confirmados: MR-01 = 26, MR-02 = 9, MR-03 = 4, MR-04 = 12, MR-05 = 17. Corrección de formato: D-16 vuelve a la tabla de decisiones (una línea en blanco la separaba). Pendiente: enlace y resumen del CI. |
