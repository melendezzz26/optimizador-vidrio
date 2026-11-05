# TA-043 / B03 — Adaptadores de ejecución y diagnósticos

**COMPLETADO en el alcance técnico autorizado de B03; revisión de Fabricio
pendiente.** La integración de los adaptadores desde HTTP permanece **PENDIENTE
DE INTEGRACIÓN B05/B06**. No se acredita el flujo público de seis motores ni el
cierre de TA-043. SPEC/PLAN permanecen Draft. Fecha: 03/11/2026, America/Lima.

[SPEC](../../../../specs/SPEC-TA-043-integracion-seis-motores.md),
[PLAN B03/T-03/T-10/ST-INC-03](../../../../specs/PLAN-TA-043-integracion-seis-motores.md),
[contrato v2](../../../../contracts/optimization/comparison-v2.md).

## Auditoría y diseño previo a cambios

- Rama única `feature/TA-043-integracion-seis-motores`, árbol limpio al iniciar,
  HEAD `abb20d02a0e9740856d1a643eef0bcd59669d16b`; presentes B02 `4ed83fd`,
  `66a54c9` y `abb20d0` y los tres commits B01 anteriores.
- Se ejecutó `git fetch origin --prune`. `origin/integration-02` sigue exactamente
  en `d85a8d3c4fa2ba1b3f70c401ed947adcfbe2470b`, sin diferencias frente a la base
  local. La rama antigua `origin/integration/sprint-01` avanzó a `7556a70` y allí
  incorporó HU-018/PR #96. Ese avance no está en integration-02 ni se incorpora
  aquí; las constataciones iniciales de SPEC/B01/B02 conservan su fecha/base.
- Revisados RF-04/14/15/16/17/18, RNF-05 y sus CA; B03, T-03/T-10/ST-INC-03,
  E0/D0/P0/L0, contratos/codecs B01, repositorio B02 y runner/transporte v1.
- FF/BF/WF/HF/BRF soportan `optimize(on_event, checkpoint, on_visual)`. El runner
  actual invoca exclusivamente FF/BF/WF. HF ya realiza replay de su solución
  elegida y BRF conserva su selector residual. M6 usa `run(on_event, checkpoint)`;
  `optimize()` descarta su outcome y sus milestones pueden describir ramas.
- Antes de editar se presentó el diseño: adaptador optativo en Application,
  catálogo B01 y fábrica nueva por llamada; observación nativa en cinco motores;
  puerto neutral de contadores M6, outcome intacto y layout ganador sin replay de
  búsqueda. No apareció incompatibilidad que exigiera modificar contratos o políticas.

## Archivos del bloque

Commits locales validados:

- `11f3d3fd5f3783e10776c80af64d9cac47aec948` — adaptadores y observación neutral M6.
- `095ff79f44b51426362757764ccd3bf827410e5c` — pruebas, generación de evidencia y arnés smoke.

Las corridas ocurrieron sobre el árbol de trabajo antes de registrar esos commits.
`validation.json` y `smoke/cleanup.json` conservan los hashes de los bytes
ensayados; coinciden con el candidato final. Un commit documental posterior
registra este informe y los reportes, sin cambiar producto ni pruebas.

| Archivo | Responsabilidad |
|---|---|
| `backend/app/modules/optimization/application/engine_execution.py` (nuevo) | Scope, observaciones tipadas, resultado adaptado y ejecución por catálogo |
| `backend/app/modules/optimization/domain/beam_search.py` | Añade únicamente `BeamSearchProgress` y callback opcional `run(on_progress=...)` |
| `backend/tests/unit/optimization/test_engine_execution.py` (nuevo) | 113 casos T-03 con motores productivos |
| `backend/tests/unit/optimization/engine_execution_support.py` (nuevo) | Regenera evidencia JSON de paridad y agotamientos reales, sin servicios |
| `backend/tests/integration/optimization/test_engine_execution_persistence.py` (nuevo) | Seis casos adaptador → B01 → B02 en PostgreSQL propio |
| `backend/tests/optimization_b01_smoke.py` | Añade `--block B03`, reutiliza la regresión real existente y marca integración pendiente |
| SPEC/PLAN TA-043 | Autorización/progreso B03 y alcance del smoke; conserva requisitos, CA, matriz y dependencias |
| Este directorio | Reportes, snapshots, contadores, capturas y limpieza |

No se modificaron catálogo, DTO, schemas, codecs, fixtures, migración ni
repositorio/UoW B01/B02. Tampoco FF/BF/WF/HF/BRF, runner, transporte, coordinador,
admisión, presupuestos, rutas HTTP ni frontend productivo. No hay nuevos endpoints.

## Correspondencia e interfaz final

| Nombre | Código | Clase / invocación productiva | Resultado nativo | Observación adaptada |
|---|---|---|---|---|
| FF | FF | FirstFitOptimizer.optimize | OptimizationResult | Milestones/VisualEvent OBSERVED |
| BF | BF | BestFitOptimizer.optimize | BestFitResult | Milestones/VisualEvent OBSERVED |
| WF | WF | WorstFitOptimizer.optimize | WorstFitResult | Milestones/VisualEvent OBSERVED |
| HF | HF | HoleFillingOptimizer.optimize | HoleFillingResult | Replay elegido FINAL_REPLAY |
| BRF | M5 | BestResidualFitOptimizer.optimize | BestResidualFitResult | Milestones/VisualEvent OBSERVED |
| BS-2 | M6-BS | BeamSearchOptimizer.run | BeamSearchOutcome + BeamSearchResult | Contadores PROVISIONAL; layout ganador FINAL_REPLAY |

`EngineExecutionAdapter(method).execute(scope, problem, minimum_width_mm=...,
minimum_height_mm=..., checkpoint=..., on_observation=...)` devuelve
`AdaptedExecution`: scope, payload B01, residuales, outcome M6 original y tipos de
error técnico/observador separados. Cada llamada crea su propio motor; los
callbacks y contadores son locales. No se importa código experimental desde app.

El scope inmutable identifica comparación/ejecución/método desde el origen.
Identidad desconocida, alias o scope contradictorio se rechazan. La entrada debe
ser canónica e inmutable: el adaptador no reordena ni modifica fuentes/piezas.
Se verifica tipo, método y problema del resultado antes de calcular métricas con
la función común existente, usando los mínimos recibidos. Ambos mínimos son
argumentos obligatorios: no se introduce un default operativo que pueda sustituir
la configuración capturada. El tiempo medido incluye
cálculo/métricas y excluye el tiempo dentro del observador; no es tiempo de cola.

Los hechos internos no son envelopes HTTP ni referencias persistidas de máscaras:
no crean secuencias, retención o alias visuales globales. `final_layout` identifica
la solución calculada y validada lista para persistir; **no significa commit** ni
`result_persisted`. B05 debe guardar primero y anunciar después del commit. La
propiedad durable se verifica al escribir/leer mediante B02.

### HF, BRF y M6

HF conserva búsqueda acotada, filtro, fallback y protecciones de cobertura/planchas.
Solo se conectan los callbacks del replay nativo elegido, nunca las búsquedas
internas. Sus estadísticas se copian al diagnóstico B01; flags bool se representan
como 0/1 para respetar los contadores enteros del contrato, sin tocar el estado
nativo. BRF usa el constructor y selector actuales: residual, fragmentación y
desempates originales, conservando `M5` y nombre visible BRF.

M6 se invoca una sola vez con `run()`. Conserva ancho 2, límites por defecto,
score, poda, generación, prioridades y desempates. El puerto neutral nuevo toma
contadores reales al crear la frontera inicial y después de completar un nivel;
no entrega placements ni introduce otra búsqueda. Los milestones nativos M6
exploratorios no se reenvían al observador común. No se dibujan ramas provisionales.
Los campos de progreso se validan contra `SearchProgressV2` sin cambiar ese schema.

El resultado final procede exclusivamente de `outcome.result`; se conserva además
el outcome original completo, estadísticas, traza y motivo. No se reconstruye ni
se vuelve a ejecutar M6 para animar. El AST del cálculo M6 se compara con B02
eliminando solo el puerto/hook de observación añadido: es idéntico
([validation.json](validation.json)). La configuración default se registra en
[adapter-validation.json](adapter-validation.json).

`EXPANSION_LIMIT`, `GEOMETRY_PROBE_LIMIT`, `STATE_MEMORY_LIMIT` y `TIME_LIMIT`
permanecen causas ENGINE. Un retorno nativo parcial, incluso vacío, conserva su
resultado y causa; no se convierte en NO_FIT. NO_FIT requiere resultado geométrico
incompleto sin agotamiento; COMPLETED requiere completitud real.

Las excepciones de cálculo/checkpoint no fabrican parciales: el payload tiene
resultado null y diagnóstico externo compatible B01 (CANCELLED, TIME_BUDGET_EXCEEDED,
MEMORY_BUDGET_EXCEEDED o EXECUTION_FAILED). `SUPERVISOR` es el canal externo ya
definido por B01; no implica que B03 implemente un supervisor de procesos. No se
publican mensajes internos de excepciones. BaseException de control no se captura.

Un observador que lanza Exception se desconecta y se informa mediante
`observer_error_type`; el resultado no cambia por esa excepción. Ese estado
separado debe ser atendido por el consumidor futuro, no confundirse con fallo de
heurística. Los checkpoints funcionan aun sin observador o tras desconectarlo.
Los callbacks son síncronos: su costo puede alcanzar una cota temporal real, y un
callback bloqueado requiere supervisión externa B04/B05. No se alteró el reloj
interno M6 ni se promete paridad ante cortes temporales distintos.

## Pruebas y evidencia real

| Selección | Resultado | Evidencia |
|---|---|---|
| T-03 inicial | 98 PASS / 8 FAIL; condiciones de fixtures, abajo | [Log](t03-initial.txt), [JUnit](t03-initial-junit.xml) |
| T-03 corregida antes del caso mixto adicional | 106 PASS; repetición, no se suma | [Log](t03-tests.txt), [JUnit](t03-junit.xml) |
| T-03 final + seis motores + visuales/contratos | 370 PASS, 0 skip; incluye 113 casos T-03 y 49 B01 | [Log](unit-regression.txt), [JUnit](unit-regression-junit.xml) |
| Persistencia directa adaptadores + regresión B02/v1 | 53 PASS, 0 skip; seis nuevos, 28 B02 y 19 v1 | [Log](persistence-regression.txt), [JUnit](persistence-regression-junit.xml) |
| Repetición de la integración con mínimos obligatorios | 6 PASS, repetidos; no se suman | [Log](adapter-persistence-final.txt), [JUnit](adapter-persistence-final-junit.xml) |
| Contratos frontend B01/v1/visual | 27 PASS en tres archivos | [Log](frontend-contracts.txt) |
| Registro directo de seis motores y cuatro agotamientos M6 | PASS, sin HTTP | [Log](adapter-evidence.txt), [datos](adapter-validation.json) |
| ST-INC-03 del flujo disponible | 2 PASS escritorio/móvil; adaptadores HTTP pendientes | [Log](smoke/execution.txt), [Playwright](smoke/playwright-report.json), [limpieza](smoke/cleanup.json) |

Son **423 casos backend distintos**, más repeticiones explícitas. No se ejecutó
la suite completa del repositorio ni el gate E2E completo; se ejecutaron las
regresiones focalizadas aplicables. No hubo skip contabilizado como PASS.

T-03 compara nueve entradas canónicas × seis motores (54 casos): fuentes
alternativas, unidades físicas/retazos, giro real, margen/separación, polígono,
materiales/espesores múltiples, parcial/no-fit y las tres formas juntas a 5°.
La igualdad incluye placements, geometrías, fuentes, métricas y residuales;
solo se excluye duración de reloj. Callbacks nativos y adaptados coinciden en los
cinco motores, y progreso/outcome/traza coinciden en M6. Se verifica una sola
invocación M6 para un parcial no vacío y ausencia de placements provisionales.

Otros casos: fábrica nueva por ejecución; desconocidos/aliases/scope/resultado
inconsistente; observador desactivado o roto; checkpoints/cancelación sin visor;
cuatro agotamientos reales M6 con/sin observador; parcial vacío/no vacío frente a
fallo sin resultado; HF pocket/fallback y ambas protecciones; BRF residual y sus
desempates; llamadas concurrentes aisladas al adaptador, sin cambiar workers.

La integración PostgreSQL persiste los seis resultados productivos a través del
repositorio B02 sin coordinador, confirma las cuatro causas M6 reales y un fallo
cancelado. Round-trip de resultado/completitud/diagnóstico/residuales, stock y
movimientos intactos. No se certifica parada ni se habilita selección al guardar.

| Requisito / CA | Cobertura B03 y límite |
|---|---|
| RF-04 / CA-04 | Completo, parcial/no-fit, cuatro causas y fallo tipados; round-trip real B02; UI v2 pendiente |
| RF-14 / CA-14 | Factory/catálogo/identidad y codecs B01/B02 preservados; conexión runner/API/UI pendiente |
| RF-15 / CA-15 | Casos HF vigentes, replay elegido, protección/fallback y estadísticas |
| RF-16 / CA-16 | Paridad BRF, fuentes/score/desempates mediante suite productiva existente |
| RF-17 / CA-17 | Paridad BS-2 con trazas/estadísticas y evidencia SP-006 de la suite vigente |
| RF-18 / CA-18 | on_progress neutral sin TypeError, contadores provisionales sin placements y único layout ganador; visualización v2 pendiente |
| RNF-05 / CA-N05 | Regresión de los seis motores y paridad bajo entrada/límites equivalentes, sin igualar motores |
| ST-INC-03 / T-13 | Regresión real disponible PASS; nuevos adaptadores desde servicios PENDIENTES DE INTEGRACIÓN |

## Reproducción y limpieza

Entorno: Ubuntu/WSL2, Python 3.11.9, PostgreSQL 18.6, Node 22.23.2 y Chromium real
administrado por Playwright. Dependencias existentes, sin instalaciones ni cambios
de versiones/presupuestos. Desde `backend/`, con `.venv/wsl/bin` en PATH:

```sh
export PYTHON_DOTENV_DISABLED=1 NEWGLASS_REQUIRE_POSTGRES=1
export NEWGLASS_TEST_PG_BIN=/usr/lib/postgresql/18/bin
python -m pytest tests/unit/optimization/test_engine_execution.py tests/unit/optimization/test_first_fit.py tests/unit/optimization/test_best_fit.py tests/unit/optimization/test_worst_fit.py tests/unit/optimization/test_hole_filling.py tests/unit/optimization/test_best_residual_fit.py tests/unit/optimization/test_beam_search.py tests/unit/optimization/test_beam_search_t02.py tests/unit/optimization/test_visual_facts.py tests/unit/optimization/test_comparison_contract.py tests/unit/optimization/test_comparison_snapshot.py tests/unit/optimization/test_comparison_v2_contract.py -q -ra --tb=short --junitxml=../docs/evidence/sprint-02/TA-043/B03/unit-regression-junit.xml
python -m pytest tests/integration/optimization/test_engine_execution_persistence.py tests/integration/optimization/test_comparison_v2_persistence.py tests/integration/optimization/test_comparison_v2_migration.py tests/integration/optimization/test_comparison_persistence.py -q -ra --tb=short --junitxml=../docs/evidence/sprint-02/TA-043/B03/persistence-regression-junit.xml
python -m tests.unit.optimization.engine_execution_support
python -m tests.optimization_b01_smoke --block B03 --runtime-root /home/fabri/.cache/newglass-validation.SXhCMM
```

Desde `frontend/`: `npm run test:component -- src/features/optimization/__tests__/ComparisonV2Contract.test.jsx src/features/optimization/__tests__/ComparisonContract.test.jsx src/features/optimization/__tests__/VisualContract.test.jsx`.
En PowerShell se usó `npm.cmd`. El runtime-root del smoke debe señalar una
instalación Linux equivalente en otra máquina; no es una dependencia productiva.

El arnés B03 reutiliza el test `TA-043 B01` del spec crítico existente, sin mocks
de red: clúster PostgreSQL propio, FastAPI, frontend HTTP y Chromium, login real,
configuración 5°, pedidos/fuentes sintéticos controlados y stock testigo. Abre
comparación real FF/BF/WF, consulta sus tres resultados completos y la UI, verifica
inventario intacto, libera pedidos y calcula/consulta FF por `/runs` con la UI legacy.
No utiliza ese PASS para acreditar nuevos adaptadores no conectados al servicio.

El teardown detiene los servicios/navegador/PG propios y elimina exclusivamente la
copia Linux/TMPDIR/clúster creados por el arnés, con ruta resuelta verificada.
Para remanentes comprueba PID y tiempo de inicio; nunca mata por nombre. El reporte
final contiene procesos antes/después vacíos, runner exit 0 y copia eliminada.
Las fixtures PostgreSQL de integración detienen su clúster en finally; el estado
de temporales/puertos al cierre se registra en validation.json. No se tocaron
Supabase, Heroku ni otros destinos compartidos.

## Incidencias, límites y siguiente revisión

El intento inicial tuvo seis fallos de paridad por una entrada antigua con planchas
antes de retazos: los motores la canonizan internamente, pero no era la entrada
congelada canónica exigida por B01/B02. El test normaliza esa fixture una vez antes
de ambas invocaciones, preservando ranking relativo. El adaptador no cambia orden
ni relaja su comprobación del problema.

Los otros dos fallos eran expectativas de fixture HF: el caso diferenciador antiguo
no activa pocket con los límites actuales y la protección de planchas necesita el
contraejemplo ya documentado con `max_regions=24`. Se usa `product_problem()` con
defaults para pocket y las condiciones equivalentes del test existente
`test_equal_coverage_more_sheets_restores_ff_and_callbacks` para esa protección.
No se amplían límites productivos para pasar pruebas; se conservan defaults y
se verifican además sus regresiones. Los logs FAIL no se borraron.

Los parámetros opcionales de prueba reutilizan objetos nativos existentes; el
perfil productivo conserva BS-2 y todos sus defaults. No se ensayó capacidad de
Heroku, seis workers simultáneos ni cargas de estrés. B04 debe medir temprano
tiempos, memoria, callbacks/serialización y viabilidad de un worker con 180 s
globales; ninguna medición de capacidad se deduce de estas pruebas pequeñas.
B05/B06 deben conectar adaptadores, persistir antes de anunciar, probar parada
real y conservar admisión; B07/B08 permanecen fuera del bloque. HU-018 sigue
condicionado a su integración independiente en la base oficial.

Sin fallos obligatorios pendientes de B03. Se detiene para revisión de Fabricio
antes de B04; el smoke integral sigue obligatorio y pendiente. No se hizo push,
merge, rebase, deploy ni cambios en entornos compartidos.
