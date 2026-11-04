# TA-043 / B06 — Persistencia, API y recuperación multimétodo

**B06 COMPLETADO en el alcance técnico autorizado; revisión de Fabricio pendiente.**
SPEC/PLAN siguen **Draft**. UI de seis motores PENDIENTE B07; selección y
confirmación v2 PENDIENTES B08; smoke integral ST-INT PENDIENTE B09–B11.
Fecha: 04/11/2026, America/Lima.

[SPEC](../../../../specs/SPEC-TA-043-integracion-seis-motores.md),
[PLAN](../../../../specs/PLAN-TA-043-integracion-seis-motores.md),
[contrato v2](../../../../contracts/optimization/comparison-v2.md),
[resultados/hashes](validation.json).

## Auditoría y diseño previo

Rama única `feature/TA-043-integracion-seis-motores`, árbol limpio al comenzar,
HEAD `18c36bcc7276dbaa8c1decd2962b4df199a23636`; presentes B05 `70084ce`, `42e98bd`
y `18c36bc` y sus antecedentes B01–B04. `git fetch origin --prune` detectó la
**eliminación externa de `origin/integration-02`** y avances de otras ramas.
La base local `integration-02` conserva `d85a8d3c4fa2ba1b3f70c401ed947adcfbe2470b`.
Se continuó en la misma feature y base local; no se recreó/publicó ninguna
referencia ni se incorporó `integration/sprint-01`, HU-018 u otro trabajo.

Se revisaron RF-04/09/11/12/13/14/19 y sus CA; B06/T-01/T-02/T-06 y
ST-INC-06/E0/D0/P0/L0; contratos, schemas/codecs B01, repositorio B02, adaptadores
B03, política B04 y coordinación/cierre B05. Se presentó antes de implementar:
router v2 separado, guards existentes y propietario, transporte en la misma
retención, recuperación por dueño B05 y liberación solo tras cierre seguro.

No fue necesario modificar contrato estructural B01, esquema/migración B02,
cotas B04 ni protocolo de cierre B05. Se añaden proyecciones y composición HTTP.
El repositorio reutiliza los metadatos operativos de liberación del ciclo v1,
separados del codec puro de entrada y del runtime de propiedad. La revisión AST
comprueba que `_close`, `_reap`, `shutdown` y `recover_pending` de B05 son idénticos
a `18c36bc`; no hay segundo coordinador, scheduler ni watchdog.

## Inventario de archivos

Rutas de producto relativas a `backend/app/modules/optimization/`, salvo indicación.

| Archivo | Cambio B06 |
|---|---|
| `presentation/comparison_v2_routes.py` nuevo | Ocho operaciones públicas, petición estricta, guards/pertenencia, recuperación y errores seguros |
| `presentation/comparison_http_runtime_v2.py` nuevo | Proyección tipada B01, una ventana NDJSON, cursores/observadores, manifiestos y expiración |
| `presentation/comparison_v2_serialization.py` | Resúmenes/ejecuciones; formatter original `result_response_v2` conservado |
| `presentation/comparison_supervision_v2.py` | Puerto de proyección/factory optativo y delegación de reconciliación; cierre B05 intacto |
| `infrastructure/comparison_v2_uow.py` | Lectura por propietario y liberación versionada/durable, sin DDL |
| `presentation/router.py`, `presentation/run_routes.py` | Registro explícito v2 y categorías nuevas de error; v1 mantiene sus códigos existentes |
| `backend/main.py` | Expone por CORS el diagnóstico público `X-Comparison-Recovery` |
| `backend/tests/api/optimization/test_comparisons_v2_api.py` nuevo | 36 casos API/PG/spawn, permisos, resultados, retención y fallos |
| `backend/tests/integration/optimization/test_comparison_v2_http_restart.py` nuevo | TCP/Uvicorn real, desconexión activa, reinicio y ausencia de recálculo |
| `backend/tests/integration/optimization/test_comparison_supervision_v2.py` | Mantiene prueba de lifespan B05; expectativa de ausencia de rutas pasa a ausencia de selection/confirm v2 |
| `backend/tests/optimization_b01_smoke.py` | Modo B06 y captura/limpieza de servicios propios |
| `backend/tests/optimization_b06_validation.py` nuevo | Auditoría reproducible de reportes, hashes, AST, trazabilidad y procesos |
| `frontend/tests/e2e/optimization-comparison.spec.js` | Smoke B06 real y actualización de la antigua aserción de que v2 no existía |
| SPEC/PLAN y contrato v2 | Autorización/progreso y publicación, sin cambiar requisitos, CA, matriz o bloques |
| Este directorio | Reportes, HTTP/NDJSON, recursos, reinicio, capturas y limpieza |

Los seis algoritmos, políticas, catálogo, DTO, schemas/codecs B01, adaptadores
B03, procesos/límites B04, modelos y Alembic permanecen intactos. El head sigue
`s2cmp02d4e6f8`; **B06 no crea migración**. `frontend/src/` no cambia.

## API realmente publicada

Prefijo `/api/optimization/comparisons-v2`. Bearer y permisos vigentes en cada
operación; dueño validado antes de devolver datos. Las ejecuciones y máscaras
se buscan dentro de la comparación, no globalmente por ID/ref.

| Operación | Permiso | Respuesta / comportamiento |
|---|---|---|
| `POST /` | execute | 201, Location y resumen v2; B05 acepta una vez seis métodos |
| `GET /requests/{key}` | view | Recuperación por actor/clave, sin recalcular |
| `GET /{comparison_id}` | view | Resumen durable; reconciliación solo mediante B05 |
| `GET /{comparison_id}/executions/{execution_id}` | view | Resultado completo/parcial/null y diagnóstico; propiedad estricta |
| `GET /{comparison_id}/events` | view | NDJSON tipado, `after_sequence`, dos observadores máximo |
| `GET /{comparison_id}/executions/{execution_id}/visual` | view | Manifiesto paginado y referencias retenidas |
| `GET /{comparison_id}/executions/{execution_id}/visual/masks/{mask_ref}` | view | Ventana de máscara, propietario durable y cache vivo contrastados |
| `POST /{comparison_id}/release` | execute | Versión vigente, dueño y cierre seguro; conserva resultados, no consume stock |

PUT selection y POST confirm no aparecen en OpenAPI ni tienen implementación.
Los flags de elegibilidad conservan el contrato B01; no anuncian esos endpoints.
La liberación B06 solo trata trabajos sin selección/confirmación, conserva los
IDs/snapshots y usa `released_at`, `released_by`, `released_selection_id: null`
junto a la entrada. Esos metadatos no entran al hash geométrico ni al codec B01.
No se cambian marcas de parada para liberar un trabajo incierto.

GET v2 no entrega v1/FF como seis resultados. GET v1 sigue con tres y `/runs`
con FF, sin reinterpretación. Se conserva acceso histórico por permisos v1;
v2 aplica además pertenencia al actor, como requiere la autorización B06.

## Estados, eventos y recuperación

Se exponen exactamente `FF/BF/WF/HF/M5/M6-BS`, con sus nombres del catálogo
FF/BF/WF/HF/BRF/BS-2. QUEUED, STARTING, RUNNING y TERMINATED son independientes
de COMPLETE/PARTIAL/FAILED. Un fallo usa métricas null; un resultado parcial
M6 conserva causa y unidades `RESOURCE_LIMIT`. Nunca iniciado conserva
`runtime_dispatched: 0` y motivo global. El problema/hash y la configuración 5°
se congelan en B05; HTTP no reconstruye ni vuelve a capturar stock por motor.

La misma clave/actor/lote devuelve el mismo agregado; lote o perfil incompatible
produce conflicto. Hay pruebas concurrentes, recuperación tras perder respuesta
y reintento después de reiniciar. Se mantienen seis filas, IDs, versión y
snapshots; no se crean seis ejecuciones nuevas al consultar.

El transporte ocupa **la misma** ventana B05: sustituye su slot de registro por
NDJSON `ComparisonEventV2`, no mantiene otro buffer 8/32 MiB. Se valida scope,
secuencia global/por ejecución, UTC y presentación. `result_persisted` deriva
de la señal B05 posterior al commit; `comparison_finished` se proyecta tras
commit del cierre y join externo del supervisor. M6 solo expone contadores
PROVISIONAL; no concatena placements de ramas ni repite la búsqueda.

Cursor futuro: 422. Cursor expulsado: 409 `EVENT_CURSOR_EXPIRED`; si se pierde
durante el stream, `snapshot_required`. Runtime/TTL perdido: 410 y recuperación
por GET durable. TTL y relevo retiran máscaras/eventos, no resultados de BD.
Consumidor lento no obliga a retener historia ilimitada. Desconectar HTTP libera
el observador y no cancela motores; falla de proyección no borra resultados ni
se rellena con eventos ficticios. Autenticación no mantiene una conexión DB en
el stream; también se probó el flujo con un pool de una conexión.

Recuperación incierta: 503 `RECOVERY_BLOCKED` en el agregado y reserva conservada.
Los resultados por ejecución ya guardados continúan consultables con
`X-Comparison-Recovery: BLOCKED` y elegibilidad falsa. Se prueba con un FF nativo
completo persistido y dueño/spawn ambiguos; no se oculta la incertidumbre ni se
fuerzan marcas. No hay endpoint administrativo de desbloqueo. Las respuestas
no publican token interno, PID/start_ticks, rutas privadas o trazas.

## Validación ejecutada

| Selección | Casos distintos | Resultado |
|---|---:|---|
| API B06 (FastAPI, RBAC, PostgreSQL, spawn reales) | 36 | PASS |
| TCP/Uvicorn: desconexión y reinicio físico del backend | 1 | PASS |
| Regresiones B01–B05 seleccionadas | 342 | PASS |
| Runner B04 / v1, procesos pytest separados | 26 / 14 | PASS |
| **Backend sin duplicar repeticiones** | **419** | **PASS; cero fallos/skip obligatorios** |
| Contratos frontend v1/v2 existentes | 23 | PASS |
| ST-INC-06 navegador escritorio/móvil | 2 | PASS |

`api-final.xml` contiene 35; `transport-review.xml` repite dos y añade fallo de
proyección/pool único (unión 37 con TCP); `recovery-review.xml` vuelve a comprobar
el caso ambiguo con un resultado completo real, sin sumar otro caso distinto.
Los XML iniciales/preliminares quedan fuera del conteo final. Los warnings son
los existentes de Starlette/httpx y `record_property`/xunit2; no se cambiaron
dependencias para ocultarlos. `npm run lint`, compileall, AST y diff-check pasan.

Entorno: WSL2 Linux, Python 3.11.9, PostgreSQL 18.6, procesos spawn; frontend
Node 22.23.2, navegador Chromium real. Las pruebas API arrancan también su
lifespan con la PostgreSQL propia: no se declara una ejecución SQLite como PASS.

Comandos desde `backend/`, con entorno protegido:

```bash
export PYTHON_DOTENV_DISABLED=1
export NEWGLASS_REQUIRE_POSTGRES=1
export NEWGLASS_TEST_PG_BIN=/usr/lib/postgresql/18/bin
export NEWGLASS_B06_EVIDENCE_DIR=../docs/evidence/sprint-02/TA-043/B06
python -m pytest tests/api/optimization/test_comparisons_v2_api.py tests/integration/optimization/test_comparison_v2_http_restart.py -q -ra --tb=short -o faulthandler_timeout=50 --junitxml=../docs/evidence/sprint-02/TA-043/B06/api-final.xml
python -m pytest tests/api/optimization/test_comparisons_v2_api.py -k 'real_six or cursor or failed_http or one_connection' -q -ra --tb=short -o faulthandler_timeout=50 --junitxml=../docs/evidence/sprint-02/TA-043/B06/transport-review.xml
python -m pytest tests/api/optimization/test_comparisons_v2_api.py -k uncertain -q -ra --tb=short --junitxml=../docs/evidence/sprint-02/TA-043/B06/recovery-review.xml
python -m pytest tests/unit/optimization/test_comparison_v2_contract.py tests/unit/optimization/test_comparison_contract.py tests/unit/optimization/test_comparison_snapshot.py tests/unit/optimization/test_engine_execution.py tests/unit/optimization/test_supervision_contracts.py tests/integration/optimization/test_comparison_v2_migration.py tests/integration/optimization/test_comparison_v2_persistence.py tests/integration/optimization/test_engine_execution_persistence.py tests/integration/optimization/test_comparison_persistence.py tests/integration/optimization/test_comparison_calculation.py tests/integration/optimization/test_comparison_supervision_v2.py tests/api/optimization/test_comparison_connection_lifecycle.py tests/api/optimization/test_comparisons_api.py tests/api/optimization/test_runs_api.py tests/api/test_health_api.py -q -ra --tb=short -o faulthandler_timeout=60 --junitxml=../docs/evidence/sprint-02/TA-043/B06/regression.xml
python -m pytest tests/unit/optimization/test_sequential_runner.py -q -ra --tb=short --junitxml=../docs/evidence/sprint-02/TA-043/B06/b04-processes.xml
python -m pytest tests/unit/optimization/test_comparison_runner.py -q -ra --tb=short --junitxml=../docs/evidence/sprint-02/TA-043/B06/v1-processes.xml
python -m tests.optimization_b01_smoke --block B06 --runtime-root /home/fabri/.cache/newglass-validation.SXhCMM
python -m compileall -q app/modules/optimization main.py tests/optimization_b06_validation.py
python -m tests.optimization_b06_validation
```

Desde `frontend/`: `npm run test:component -- src/features/optimization/__tests__/ComparisonV2Contract.test.jsx src/features/optimization/__tests__/ComparisonContract.test.jsx --reporter=default --reporter=json --outputFile=../docs/evidence/sprint-02/TA-043/B06/frontend-contracts.json`
y `npm run lint` (Windows: `npm.cmd`). No cambia código de producto frontend;
Vite se levanta y sirve realmente en el smoke, sin atribuir un build inexistente.

## Smoke ST-INC-06 y limpieza

**PASS: 2/2 escenarios, 27,0 s**. Cada proyecto arranca sesión real en la UI,
usa fetch real desde Chromium hacia FastAPI y procesa respuestas con parsers
B01. PostgreSQL aislado y un proceso web. Pedido sintético mixto: rectángulo
10×10, círculo radio 2 y triángulo convexo; tres unidades, stock 100×50 compatible,
paso 5° real. No se emplea HU-018 ni importación. Se comprueba readiness, POST,
GET ID/clave, seis completos/métricas/diagnósticos, eventos, idempotencia,
recarga, conflicto de perfil, historia v1 en la UI y `/runs`, cero consumo.
Se comparan también todas las planchas, retazos y sus movimientos por HTTP,
sin limitar la comprobación a las fuentes originales del pedido.

Las pestañas siguen siendo las cuatro de v1; no se simulan seis distribuciones
en pantalla ni se acredita B07 o ST-INT. Se conserva evidencia sanitizada en
`smoke/chromium-desktop/` y `smoke/chromium-mobile/`.

`smoke/cleanup.json`: `runner_exit: 0`, `processes_after: []` y
`temporary_copy_removed: true`. La copia, clúster y servicios propios se
detienen/eliminan tras verificar su ruta. No se mata por nombre ni se toca
Supabase, Heroku o servicios compartidos. En pytest los clústeres propios se
detienen en finally; sus datos sintéticos/logs temporales siguen la retención
habitual de pytest. Los PID/inicios de workers/servidores ensayados ya no viven.

`http-restart.json` conserva el caso TCP: stream desconectado al primer
engine_started, seis resultados posteriores, dos identidades de Uvicorn,
reinicio con DB común, snapshot inmutable, cero hijos nuevos al servir historia
y limpieza completada. No se basa solo en mocks ni en cambiar un objeto Python.

En el caso API pequeño de cuatro rectángulos, el runner integrado tardó
**5,978 s**, con máximo **un worker**, RSS agregado muestreado **146,91 MiB**
incluida reserva, supervisor **107,61 MiB** y espacio virtual máximo de worker
**38,36 MiB**. Es el contexto de prueba FastAPI/pytest en WSL2; no se presenta
como medida de Heroku ni del proceso Uvicorn del otro ensayo. Los valores crudos
y el muestreo están en `api-real.json`; no garantizan haber capturado cada pico.

## Trazabilidad del alcance B06

| Requisito / CA | Actividad / prueba real | Evidencia / límite |
|---|---|---|
| RF-04 / CA-04 | B06 API: completo, cuatro parciales M6, HF fallido y deadline | `api-real.json`, JSON de cuatro causas, `failed-engine.json`, `global-deadline.json`; UI v2 pendiente B07 |
| RF-09 / CA-09 | POST concurrente, reintento por clave/ID, pérdida de stream y reinicio | XML API/TCP y `http-restart.json`; confirmación idempotente v2 queda B08 |
| RF-11 / CA-11 | Regresión histórica PG/v1/legacy y smoke UI existente | `regression.xml`, `smoke/*/TA-043-b06-history-legacy.json`; sin conversión ni recálculo |
| RF-12 / CA-12 | Rutas/perfil explícitos, conflicto cruzado, propietario y schemas B01 | API/contratos frontend y smoke; selection/confirm no publicados |
| RF-13 / CA-13 | Persistencia B02 y upgrade/downgrade en regresión; release operativo | Migración B02 inalterada, `regression.xml`; ningún DDL compartido |
| RF-14 / CA-14 | Seis identidades en DB/HTTP/eventos/máscaras, mismos codecs | API/contratos y `validation.json`; no segunda factory algorítmica |
| RF-19 / CA-19 | GET ID/clave/ejecución, cursor/TTL, TCP/reinicio y bloqueo ambiguo | `api-real.json`, `http-restart.json`, `ambiguous-recovery.json`; elección/recibo v2 pendiente B08 |
| SM-01/02/03/07/08/10 | ST-INC-06 real + cierre/procesos B05 | Evidencia de capacidades disponibles, sin anticipar PASS de selección/confirmación ni UI de seis motores |

Los 36 requisitos, 36 CA, matriz y once bloques/dependencias se conservan
literalmente; el validador lo compara con `18c36bc`. No se declara completado
un CA cuyo alcance incluye bloques futuros ni se cierra TA-043.

## Incidencias y límites

- Primer intento API: 500 del manifiesto por Decimal en unidades ordenadas.
  Se aplicó la proyección decimal existente (`plain`) y se repitió el caso y la
  suite afectada. `preliminary-api.xml` conserva FAIL; no integra el conteo PASS.
  La configuración de esa primera fixture intentaba leer startup en SQLite;
  la fixture definitiva conecta RBAC/lifespan/UoW a la misma PostgreSQL aislada.
- Las aserciones de ausencia de API v2 de B01/B05 se actualizaron al hito B06;
  siguen comprobando v1/legacy y ausencia de selection/confirm v2.
- El bloqueo conservador de B05 sigue vigente ante dueño/spawn/descendientes
  inciertos. No se añadió reparación administrativa ni heurísticas de TTL/PID.
- Los recursos observados corresponden al caso pequeño; no garantizan capacidad
  general, formas/cantidades máximas ni Heroku. Conservadas cotas 1 GiB agregado,
  240 MiB supervisor, 256 MiB virtual/worker, reserva 16 MiB, 30/120/180 s y
  12/4/32/8 MiB IPC/visual/retención. Concurrencia uno, sin ampliaciones.
- B07 debe manejar expiración/recuperación y errores nuevos del perfil v2, sin
  reutilizar un parser v1 estricto para seis motores. B08 debe completar elección,
  confirmación y liberación después de selección, preservando transacciones.
- La referencia remota de integración ausente requiere coordinación del equipo;
  esta entrega conserva la base local y no la publica por iniciativa propia.

## Commits locales y revisión final

- `ffd7193558d9e6303a1ae773f6ba346dade28041` — API, proyección, propiedad y recuperación.
- `7eed2a4405ceb8240c8530699597f546b6cb1a47` — pruebas API/TCP, smoke y auditor de evidencia.

Las pruebas se ejecutaron sobre el árbol antes de esos commits. Los hashes de
`validation.json` y `smoke/cleanup.json` identifican los bytes ensayados; el commit
documental posterior registra este informe y los artefactos, sin cambiar producto.
Se comprobaron enlaces locales, ausencia de JWT en artefactos y `git diff --check`.

No hubo push, merge, rebase, nuevas ramas, despliegues, cambios de algoritmos,
migraciones compartidas o modificaciones de Supabase/Heroku. Se detiene B06
para revisión y autorización antes de B07.
