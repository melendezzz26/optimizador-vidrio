# TA-043 / B05 — Supervisor y coordinador multimétodo

**B05 COMPLETADO en el alcance técnico autorizado; pendiente de revisión de Fabricio.**
SPEC/PLAN permanecen **Draft**, el flujo público v2 está
**PENDIENTE DE INTEGRACIÓN B06** y ST-INT no está ejecutado. No se implementan
API v2, UI, selección o confirmación v2. Fecha: 03/11/2026, America/Lima.

[SPEC](../../../../specs/SPEC-TA-043-integracion-seis-motores.md),
[PLAN](../../../../specs/PLAN-TA-043-integracion-seis-motores.md),
[contrato v2](../../../../contracts/optimization/comparison-v2.md).

## Auditoría, autorización y alcance

Inicio con árbol limpio en `feature/TA-043-integracion-seis-motores`, HEAD
`67010600e8c8c7c6de6528e7e3fc0037b8179381`. Verificados B01–B04 y sus commits:
B04 `8c19b0e`, `e404580`, `6701060`. `git fetch origin --prune` conservó
`origin/integration-02` en `d85a8d3c4fa2ba1b3f70c401ed947adcfbe2470b`, igual
a la base local. No se incorporan avances externos ni HU-018.

Se revisaron RF-01/03/04/14 y RNF-01/02/03, sus CA, B05/T-04/T-05/T-06,
ST-INC-05/E0/D0/P0/L0 y evidencias B01–B04. Se presentó el diseño antes de editar:
captura única consistente, runner B04 único, persistencia por ejecución y dueño
externo que espera al supervisor antes del cierre/admisión.

La auditoría encontró que B02 solo admitía un campo en `runtime`. Se solicitó
revisión y Fabricio respondió **«Autorizar esta ampliación interna de runtime»**:
versión interna, token, PID/start_ticks del dueño y registro de workers por
execution_id; lectura B02 anterior conservada y bloqueo si faltan identidades.
No cambian SQL/Alembic, codecs puros B01, contratos HTTP ni cotas B04.

## Arquitectura y archivos

Las siguientes rutas, salvo indicación, parten de
`backend/app/modules/optimization/`.

| Archivo | Responsabilidad B05 |
|---|---|
| `application/comparison_acceptance_v2.py` | Validación, autorización mediante puerto, captura común, idempotencia y reintento acotado de conflictos de snapshot |
| `application/comparison_calculation_v2.py` | Supervisor de aplicación; seis estados/resultados, eventos posteriores al commit y cierre de pendientes |
| `application/supervision_contracts.py` | Lector estricto de propiedad interna; compatible con B02 anterior |
| `application/comparison_persistence_contracts.py` | Vista inmutable del runtime durable |
| `infrastructure/comparison_v2_uow.py` | REPEATABLE READ, configuración/versiones en la misma captura, claim y propiedad de workers, reconciliación histórica |
| `infrastructure/sequential_runner.py` | Puerto optativo de lifecycle antes de spawn y antes de abrir gate; scheduler/watchdog/cotas B04 conservados |
| `presentation/comparison_supervision_v2.py` | Composición RBAC/UoW/admisión, hilo supervisor y dueño externo, buffers compartidos y recuperación conservadora |
| `presentation/comparison_retention.py` | Un propietario de la ventana comparativa retenida v1/v2; retira máscaras y eventos anteriores después de cierre seguro |
| `application/comparison_calculation.py`, `presentation/comparison_runtime.py` | v1 difiere cierre durable y liberación hasta join externo; llamadas síncronas previas conservan su default |
| `infrastructure/comparison_runner.py` | v1 verifica parada del monitor antes de acreditar cierre |
| `presentation/comparison_routes.py` | Solo composición del mismo propietario de retención; ningún endpoint/schema nuevo |
| `backend/main.py` | Recuperación conservadora al iniciar y shutdown del coordinador al salir del lifespan |
| `backend/tests/integration/optimization/test_comparison_supervision_v2.py` | PostgreSQL y spawn reales, fallos controlados, cierre, lifecycle y regresión v1 |
| `backend/tests/unit/optimization/test_supervision_contracts.py` | Metadatos corruptos/ajenos y propiedad de retención |
| `backend/tests/api/test_health_api.py` | Separa recuperación de startup de la aserción de liveness sin acceso DB |
| `backend/tests/optimization_b01_smoke.py` | Opción B05, mismo smoke real disponible y pendientes públicos explícitos |
| SPEC/PLAN, contrato y este directorio | Autorización, límites y evidencias |

Los seis algoritmos, adaptadores B03, catálogo/DTO/schemas/codecs B01, modelos,
migraciones y presupuestos permanecen intactos. No hay cambios frontend.

## Captura, admisión y persistencia

Una transacción **REPEATABLE READ** corta, iniciada antes de consultar datos,
autoriza al actor usando los lectores/guard RBAC existentes, serializa la clave
idempotente y bloquea pedidos en orden estable. Captura una configuración vigente
y su versión, mínimos, unidades y fuentes mediante una única consulta común de
stock; arma un DTO desconectado y seis filas. Los conflictos 40001/40P01 o de la
clave concurrente se reintentan hasta tres veces con transacción nueva, sin
alterar presupuestos de cálculo. La historia aceptada no se recaptura.

Orden **FF → BF → WF → HF → M5 → M6-BS**, un worker activo. Cada worker recibe
el mismo hash/DTO y verifica su identidad antes de calcular. La intención de spawn
y su PID/start_ticks quedan persistidos antes de abrir el gate. No viajan sesiones
SQL ni conexiones DB a los hijos. El agregado y sus seis ejecuciones conservan
propiedad, completitud, diagnósticos ENGINE/SUPERVISOR y residuales.

Se usa exactamente la admisión en memoria de FF/v1 (`get_run_admission`), con
reserva exclusiva de comparación. No hay tres semáforos ni soporte distribuido.
Los reintentos recuperan el agregado por actor/clave sin ejecutar otra vez.
Simular cambia únicamente estados/documentos del ciclo existente: no reserva,
consume o genera planchas, retazos ni movimientos.

Cada resultado tiene su propia transacción. `result_persisted` se entrega al salir
del UoW, después del commit; `final_layout` no lo sustituye. Si falla la escritura,
se revierte esa transacción y se intenta guardar `RESULT_SAVE_FAILED` para esa
ejecución. Si falla también el diagnóstico, se aborta conservando resultados
anteriores y la admisión hasta resolver el cierre. Un commit ambiguo se consulta
antes de intentar sobrescribir un terminal ya durable.

## Cierre y recuperación

Secuencia demostrada por `six-real.json`:

1. B04 detiene/join workers, descendientes observados, lectores y watchdog.
2. El hilo supervisor retorna sin liberar admisión ni certificar su propio join.
3. Otro hilo hace `join()` y verifica reporte de procesos e identidades Linux.
4. Resuelve pendientes sin sobrescribir resultados anteriores.
5. Una transacción actualiza pedidos y confirma `supervisor_stopped_at`/estado final.
6. Finaliza sesiones visuales y libera la lease; las llamadas repetidas son inocuas.

v1 usa también dueño externo; un reporte que no acredita cierre no se corrige
solo porque sus PID estén muertos. Una falla del commit de cierre conserva la
lease y permite reintentar la misma finalización sin repetir motores ni consumos.

La recuperación compara PID **y** start_ticks, nunca TTL. No mata procesos por
nombre ni por un PID reutilizado. Sin dueño verificable, con spawn ambiguo o con
DB inaccesible mantiene la reserva operativa. Si el dueño murió sin registrar
ninguna intención de spawn, puede cerrar pendientes sin recalcular. Si hubo
workers registrados, los PID directos muertos **no bastan** para certificar
ausencia de descendientes después de perder el reporte del dueño: conserva el
bloqueo y exige evidencia externa de cierre. No se inventa un mecanismo HTTP
administrativo para resolverlo; B06 debe respetar esta limitación.

## Recursos y observación

Cotas B04 intactas: RSS agregado 1 GiB, supervisor 240 MiB, espacio virtual duro
256 MiB/worker, reserva 16 MiB, startup 30 s, cálculo 120 s/motor y global 180 s;
IPC 12 MiB, visual 4 MiB, cola uno, retención comparativa 32/8 MiB.
Los ensayos negativos reducen límites exclusivamente en sus instancias de prueba.

El runner usa `retain_observations=False`. El runtime conserva una sola ventana
comparativa, máscaras con dueño por ejecución y eventos sin duplicar bitmaps.
El relevo v1/v2 retira ambas ventanas del trabajo anterior tras su cierre seguro.
Errores de observación desconectan el observador; no cambian las decisiones ni
convierten un fallo en NO_FIT. Si el consumidor bloquea, la admisión sigue ocupada
hasta que el supervisor termine; los límites externos B04 siguen actuando.
M6 conserva sus cuatro causas y solo progreso provisional, sin placements de ramas.

## Validación reproducible

Todos los comandos parten de `backend/`, Linux/WSL2, Python 3.11.9 y PostgreSQL
18.6 local. Entorno obligatorio:

```bash
export PYTHON_DOTENV_DISABLED=1
export NEWGLASS_REQUIRE_POSTGRES=1
export NEWGLASS_TEST_PG_BIN=/usr/lib/postgresql/18/bin
export NEWGLASS_B05_EVIDENCE_DIR=../docs/evidence/sprint-02/TA-043/B05
python -m pytest tests/unit/optimization/test_supervision_contracts.py tests/integration/optimization/test_comparison_supervision_v2.py -q -ra --tb=short --junitxml=../docs/evidence/sprint-02/TA-043/B05/b05-focused.xml
```

El fixture `test_runs.prepared` crea dos pedidos sintéticos de dos rectángulos
2×2 mm cada uno, dos planchas 4×2 mm de material de prueba, paso 5°, mínimos 1×1,
sin margen/separación. `six-real.json` contiene el problema congelado, hash,
versiones, estados, PID/inicio, recursos y timeline; los demás JSON conservan los
escenarios negativos. No se exige diferencia de layouts entre motores.

Las pruebas crean un clúster loopback propio mediante `postgres_support.py`,
migran solo ese clúster y lo detienen en `finally`. Los directorios de pytest
retienen únicamente datos sintéticos y logs; no queda PostgreSQL ejecutándose.
No se usa `.env`, Supabase, Heroku ni una base compartida.

Los reportes XML conservan cantidades y resultados reales. Las ejecuciones
preliminares se conservan por separado y **no se suman** como casos distintos.
Los comandos finales figuran debajo; resultados y hashes del candidato se
registran en `validation.json`. No se atribuyen resultados de B04 a esta entrega.

| Nivel / selección | Casos distintos | Resultado |
|---|---:|---|
| B05: metadatos/retención unitarios | 12 | PASS |
| B05: coordinación PostgreSQL/spawn, v1 y lifespan | 26 | PASS |
| Regresión seleccionada B01–B03, persistencia, API/legacy/health | 304 | PASS |
| Runner secuencial B04, pytest independiente | 26 | PASS |
| Runner v1, pytest independiente | 14 | PASS |
| Total backend sin duplicar repeticiones | **382** | **PASS; cero fallos/skip** |

`b05-focused.xml` contiene 36; `closure-review.xml` repite el caso principal y
añade asignación fallida del dueño; `recovery-review.xml` repite los casos
afectados y añade plataforma no admitida: unión de 38, no suma de 47.
`regression.xml` conserva seis warnings: deprecación existente Starlette/httpx
y cinco avisos `record_property`/xunit2. No son errores ni se cambian dependencias
para ocultarlos. Los fallos inducidos están en los JSON y en las aserciones de
prueba; su aislamiento esperado es lo que recibe PASS.

Selecciones adicionales exactas (mismo entorno del comando anterior):

```bash
python -m pytest tests/integration/optimization/test_comparison_supervision_v2.py -k 'owner_allocation or common_capture' -q -ra --tb=short --junitxml=../docs/evidence/sprint-02/TA-043/B05/closure-review.xml
python -m pytest tests/integration/optimization/test_comparison_supervision_v2.py -k 'recovery or owner_allocation or lifespan' -q -ra --tb=short --junitxml=../docs/evidence/sprint-02/TA-043/B05/recovery-review.xml
python -m pytest tests/unit/optimization/test_comparison_v2_contract.py tests/unit/optimization/test_comparison_contract.py tests/unit/optimization/test_comparison_snapshot.py tests/unit/optimization/test_engine_execution.py tests/integration/optimization/test_comparison_v2_migration.py tests/integration/optimization/test_comparison_v2_persistence.py tests/integration/optimization/test_engine_execution_persistence.py tests/integration/optimization/test_comparison_persistence.py tests/integration/optimization/test_comparison_calculation.py tests/api/optimization/test_comparison_connection_lifecycle.py tests/api/optimization/test_comparisons_api.py tests/api/optimization/test_runs_api.py tests/api/test_health_api.py -q -ra --tb=short --junitxml=../docs/evidence/sprint-02/TA-043/B05/regression.xml
python -m pytest tests/unit/optimization/test_sequential_runner.py -q -ra --tb=short --junitxml=../docs/evidence/sprint-02/TA-043/B05/b04-process-regression.xml
python -m pytest tests/unit/optimization/test_comparison_runner.py -q -ra --tb=short --junitxml=../docs/evidence/sprint-02/TA-043/B05/v1-process-regression.xml
python -m compileall -q app/modules/optimization main.py
python -m tests.optimization_b05_validation
```

El último comando comprueba reportes, hashes del smoke, AST, ausencia de workers
con las identidades ensayadas, conservación exacta de 36 requisitos/CA/matriz y
once bloques/dependencias respecto a `6701060`. Genera
[validation.json](validation.json) y [measurements.md](measurements.md), sin DB.
El archivo `backend/tests/optimization_b05_validation.py` forma parte del bloque.

## Smoke ST-INC-05

```bash
python -m tests.optimization_b01_smoke --block B05 --runtime-root /home/fabri/.cache/newglass-validation.SXhCMM
```

FastAPI, frontend HTTP, Chromium y PostgreSQL reales en copia temporal propia.
La selección reutilizada `TA-043 B01` comprueba v1 de tres motores y `/runs`
en escritorio/móvil. `smoke/` conserva informe, HTTP, capturas y limpieza.
El inicio/consulta pública de seis motores queda **PENDIENTE B06**; la coordinación
v2 real se acredita en las pruebas aplicación/BD/spawn, no por ese smoke.
No hay endpoints temporales ni mocks de red para fabricar PASS público v2.

**Resultado: PASS del flujo disponible, 2/2 escenarios reales en 17,9 s**,
escritorio y móvil. `runner_exit: 0`, `processes_after: []` y
`temporary_copy_removed: true`. El backend/frontend/navegador y el clúster
temporal propio terminaron; no se eliminó ni señaló ningún proceso ajeno.

## Commits y verificaciones finales

- `70084ceac358d5e62107b52f2c973f42480c46af` — implementación y protocolo de cierre.
- `42e98bde09a744feb7f06b9de1d5847c545ee796` — pruebas, smoke y validador de artefactos.

Las pruebas precedieron a esos commits; `validation.json` y el manifiesto del
smoke identifican los bytes ejecutados. El commit documental posterior registra
este informe, contrato interno autorizado y artefactos, sin cambiar producto.
`compileall`, AST, invariantes documentales y `git diff --check` satisfactorios.
No se repite un build/lint frontend porque su código permanece intacto; Vite y
la integración HTTP se ejecutaron realmente en el smoke.

## Revisión y pendientes

Mantener una sola instancia/proceso web; la admisión no está distribuida. La
capacidad observada vale para el caso pequeño y WSL2, no acredita carga general
ni Heroku. B06 debe exponer consulta/recuperación sobre estos resultados sin
recalcular, respetar propiedad y límites de retención y conservar el bloqueo
operativo ante incertidumbre. B07/B08 y ST-INT siguen pendientes.

No hubo push, merge, rebase, deploy, nuevas ramas, cambios algorítmicos ni
migraciones compartidas. La entrega se detiene para revisión de Fabricio antes
de B06; no declara TA-043 cerrada.
