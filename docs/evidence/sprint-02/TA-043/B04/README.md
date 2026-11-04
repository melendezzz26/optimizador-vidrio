# TA-043 / B04 — Política de recursos y concurrencia

**B04 COMPLETADO en el alcance técnico autorizado; decisión de viabilidad:
VIABLE para el caso pequeño medido en WSL2.** Revisar antes de comenzar B05.
No acredita capacidad general, Heroku, admisión compartida v2 ni API pública de
seis motores. SPEC/PLAN siguen Draft; el smoke integral continúa pendiente.

[SPEC](../../../../specs/SPEC-TA-043-integracion-seis-motores.md),
[PLAN B04](../../../../specs/PLAN-TA-043-integracion-seis-motores.md),
[contrato v2](../../../../contracts/optimization/comparison-v2.md).
Fecha: 03/11/2026, America/Lima.

## Auditoría y puerta temprana

Inicio limpio en `feature/TA-043-integracion-seis-motores`, HEAD
`f1fce9feea8ac9260a905a4e1a0c816e27b0e0f9`, con B03 `11f3d3f`, `095ff79`,
`f1fce9f`. Tras `git fetch origin --prune`, `origin/integration-02` permanece en
`d85a8d3c4fa2ba1b3f70c401ed947adcfbe2470b`, sin diferencias con la base local.
No se incorporaron avances de la rama antigua ni HU-018.

Se revisaron RF-03/04, RNF-01/02/03 y sus CA, B04/T-04/T-05/T-11/ST-INC-04,
E0/D0/P0/L0, evidencias B01–B03, presupuesto, admisión, carga, supervisión,
transporte/retención v1 y callbacks/checkpoints B03. Antes de editar se presentó
la política: primitiva optativa, seis procesos secuenciales, plazo global continuo,
watchdog independiente y ninguna integración transaccional/API adelantada.

Antes de crear módulos productivos B04 se ejecutó el ensayo temprano
`python -m tests.optimization_b04_probe`: seis motores reales por adaptadores B03,
con y sin observación, spawn nuevo por motor, RLIMIT_AS vigente, vigilancia de
RSS, startup/cálculo/global y limpieza. Las dos secuencias completaron en unos
5 segundos, con un worker máximo y aproximadamente 61 MiB de RSS agregado
muestreado incluida reserva. No hubo necesidad de modificar ninguna cota.

[early-feasibility.json](early-feasibility.json) conserva fixture, parámetros,
identidades, fases, bytes, métricas y limpieza; [log](early-feasibility.txt).
La instrumentación separa el callback final del cuerpo del motor, pues sucede
después de calcular. El ensayo es diagnóstico preliminar, no el coordinador B05.

## Entrega y límites del bloque

Commits locales de código y pruebas, posteriores a las validaciones:

- `8c19b0e29706f468a33c99073276750ab9f0ade9` — política, worker y primitiva secuencial.
- `e4045800b43cd941269cff7e8e0c81594f2ce0b9` — pruebas, ensayos reproducibles y arnés smoke.

Las corridas se realizaron sobre el árbol antes de esos commits. Los hashes de
`validation.json` y `smoke/cleanup.json` identifican los bytes ensayados y su
correspondencia con el candidato final. El commit documental posterior registra
este informe y los artefactos sin cambiar la política ni las pruebas.

| Archivo | Cambio |
|---|---|
| `application/sequential_policy.py` | Política inmutable, orden estable, rechazo de aumentos, vencimientos y retención global por bytes |
| `infrastructure/sequential_worker.py` | Worker spawn: instancia B03 nueva, controles cooperativos, RLIMIT_AS, observación acotada y resultado v3 |
| `infrastructure/sequential_runner.py` | Ejecución secuencial, watchdog, IPC acotado, propiedad, causas, nunca iniciadas y cierre verificado |
| `backend/scripts/check_comparison_environment.py` | Diagnóstico optativo `--profile comparison-v2`; default v1 conservado |
| `backend/tests/unit/optimization/test_sequential_runner.py` | 26 casos de política/procesos y negativos acotados |
| `backend/tests/optimization_b04_probe.py` | Puerta temprana reproducible con instrumentación solo en hijos desechables |
| `backend/tests/optimization_b04_validation.py` | Medición de la primitiva final, configuración real, paridad B03 y tablas derivadas |
| `backend/tests/optimization_b01_smoke.py` | Opción B04 para regresión real disponible y pendientes explícitos |
| SPEC/PLAN y este directorio | Autorización, delimitación B05, mediciones, resultados y evidencias |

Las primeras tres rutas son relativas a `backend/app/modules/optimization/`.
Catálogo, contratos, DTO, codecs, modelos/migración/UoW B01/B02, adaptadores B03,
los seis algoritmos, runner/runtime/admisión v1 y frontend productivo permanecen
intactos. No se crean rutas ni se ejecutan transacciones v2. No hubo push, merge,
rebase, deploy, cambios en Supabase/Heroku ni migraciones compartidas.

## Política efectiva

Orden fijo **FF → BF → WF → HF → M5 → M6-BS**, exactamente un worker de motor
activo por secuencia. Se detiene/join cada proceso y sus lectores/watchdog antes
de lanzar el siguiente. Scope inmutable con comparación, ejecución y método;
seis IDs diferentes y hash común verificados al arrancar. La cola se representa
desde el comienzo y un aborto global identifica las nunca despachadas/iniciadas.

El uso solapado de la misma instancia se rechaza con OPTIMIZER_BUSY. Si el cierre
no puede verificarse, su guard queda cerrado y el reporte no acredita parada.
Este guard **no es una lease de admisión de la aplicación**: B05 debe excluir
comparaciones de otras instancias y FF/v1 mediante la admisión compartida.

| Cota vigente | Valor aplicado, sin multiplicar por seis |
|---|---:|
| RSS agregado muestreado | 1 GiB |
| RSS supervisor | 240 MiB |
| Espacio virtual duro por worker | 256 MiB, limitado también por hard heredado |
| Reserva auxiliar | 16 MiB |
| Arranque por proceso | 30 s |
| Ejecución externa por motor | 120 s |
| Plazo global compartido | 180 s |
| Paquete IPC / observación | 12 MiB / 4 MiB |
| Cola IPC por worker | 1 paquete |
| Retención visual / eventos compartidos | 32 MiB / 8 MiB |

Se conservan las demás cotas de geometría, cachés, ventanas y motores. La política
rechaza presupuestos superiores a los existentes y concurrencia distinta de uno.
Los tests usan cotas menores para activar condiciones específicas; no proponen
nuevos valores productivos. M6 conserva sus límites internos, ancho 2 y cuatro
causas ENGINE; la configuración efectiva está en el JSON de medición final.

El global comienza antes de serializar/despachar y abarca cola, startup y cierre.
El reloj individual se comparte mediante un control spawn independiente del
consumidor y empieza al entrar al adaptador: incluye callbacks/IPC/métricas, no
cola ni startup. La preparación y el cuerpo exclusivo se miden por separado en
el diagnóstico, sin confundirlos con ese reloj de pared externo.

Watchdog separado, muestreo nominal 25 ms, primer vencimiento efectivo de relojes
y causa retenida antes de procesar EOF. Un callback/consumidor bloqueado no pausa
los límites externos. La cancelación se propaga también a checkpoints B03; ante
bloqueo actúa la terminación externa. Los fallos locales conservan los otros cinco;
global/cancelación/RSS agregado abortan la cola con causa explícita, nunca NO_FIT.

`spawn`, PR_SET_PDEATHSIG, PID + start_ticks, join y terminación/kill de respaldo
se aplican a procesos propios. Se siguen descendientes observados por procfs,
su RSS forma parte del agregado y se señalizan solo tras verificar identidad.
El cierre verifica también lectores, monitor y descendientes propios. No se mata
por nombre. `all_workers_stopped` acredita esos componentes internos, **no el
fin del hilo supervisor dueño** ni la liberación de una lease: eso corresponde
a B05. La muerte de supervisor, reconciliación y persistencia transaccional del
cierre siguen pendientes de la integración completa.

El IPC valida scope/hash/resultado, limita recepción y rechaza paquetes inválidos
o sobredimensionados. M6 expone progreso provisional sin placements exploratorios;
el layout final viaja una vez en el resultado. Una falla del observador se informa
en worker_report sin cambiar la solución; si se bloquea, el deadline externo actúa.

Las ventanas de observación son globales para los seis scopes y acotadas por
bytes, con el límite existente de 4096 registros aplicado a las ventanas internas.
No son sesiones HTTP/máscaras proyectadas. B05 deberá usar
`retain_observations=False` cuando entregue la retención al runtime existente,
para no reservar otras ventanas completas de 32/8 MiB. Si necesita coexistencia,
debe compartir contabilización; no duplicar presupuestos. La prueba de handoff
confirma cero bytes en las ventanas de esta primitiva.

## Mediciones y decisión

Caso sintético pequeño B03: rectángulo, círculo y polígono, configuración real 5°,
fuentes compatibles, tres unidades y límites de admisión vigentes respetados.
SHA256 de entrada:
`1fbb532c7bd0d92f7651cecf424ccfed2bbdda515d0e807e4822607ffba1baf2`.
Sin HU-018, sin DB y sin coordinador durante la medición de procesos.

- [Tablas por motor y modalidad](measurements.md): preparación, cuerpo del motor,
  callbacks, métricas, serialización, startup/cola/cierre, RSS y VM.
- [Medición final JSON](final-process-measurements.json) y
  [log](final-process-measurements.txt): PID/start_ticks, límites, eventos/bytes,
  estados, intervalos de muestreo, máximo simultáneo y paridad de cada resultado.
- Los seis completan ambas modalidades en aproximadamente 5 s frente a 180 s;
  RSS agregado alrededor de 63 MiB con reserva y VM observada de los workers
  alrededor de 39 MiB frente al hard de 256 MiB. Los valores exactos del candidato
  final están en los artefactos enlazados, no se sustituyen por estos redondeos.
- Cada snapshot normalizado solo por tiempo coincide con la ejecución directa
  B03. No se igualan resultados entre heurísticas. Las muestras positivas tienen
  seis completos, cero parciales/fallidos/nunca iniciados; los negativos ejercitan
  parciales M6, fallos y cinco nunca despachados por aborto global.

RSS agregado suma RSS del supervisor/worker/descendientes más reserva, pudiendo
contar páginas compartidas conservadoramente. RSS no es espacio virtual ni la
cota estimada de estados M6. Los picos RSS/VM del monitor son muestreados; el pico
RSS del worker se registra además mediante getrusage. RLIMIT_AS es duro. Una sola
muestra ON/OFF no estima estadísticamente el costo de observación; startup frío,
calentamiento e IO varían. El observador temprano serializa y descarta hechos;
la primitiva final usa IPC real, muestreo de orientaciones y un único resultado
final, por lo que sus volúmenes no son perfiles de transporte idénticos.

**Recomendación:** continuar B05 después de revisión/autorización, con estas
cotas y un worker. No aumentar concurrencia/presupuestos. La viabilidad de entradas
mayores, 150 unidades, retención proyectada y plataforma objetivo sigue pendiente
de medición; la evidencia pequeña no autoriza promesas de capacidad ni deploy.

## Pruebas, smoke e incidencias

| Selección | Resultado real final | Evidencia |
|---|---|---|
| B04 procesos/política, candidato final | 26 PASS, 0 skip | [Log](process-verified.txt), [JUnit](process-verified-junit.xml) |
| Contratos B01, codecs históricos y adaptadores B03 | 186 PASS, 0 skip | [Log](contracts-adapters.txt), [JUnit](contracts-adapters-junit.xml) |
| Runner v1, pytest limpio | 14 PASS, 0 skip | [Log](v1-process.txt), [JUnit](v1-process-junit.xml) |
| Preflight v2 local | disponible / PASS | [preflight.txt](preflight.txt) |
| Puerta temprana y primitiva final | VIABLE en ambas modalidades | JSON/logs de medición anteriores |
| ST-INC-04 del flujo disponible | 2 PASS, escritorio/móvil | [Log](smoke/execution.txt), [Playwright](smoke/playwright-report.json) |

Son **226 pruebas backend distintas**, sin sumar repeticiones. No se ejecutó toda
la suite ni el gate E2E completo. Los 26 casos B04 incluyen: orden/concurrencia uno,
identidad/aislamiento, clocks/startup/cálculo/global y nunca iniciadas, RSS real,
RLIMIT_AS y allocation real rechazada, paquete >12 MiB, retención/evicción/handoff,
observador nativo bloqueado y desconectado, cancelación cooperativa/sin observador,
muerte de worker, descendiente propio, cierre/reuso/no solapamiento, preflight y
las cuatro causas M6 reales conservadas por IPC. No se usaron solo mocks para
demostrar procesos, memoria o capacidad. La simulación de capacidad ausente sirve
solo al rechazo preflight y la cota RSS reducida solo activa el watchdog real.

ST-INC-04 reutiliza el test real existente `TA-043 B01`: PostgreSQL propio,
FastAPI, Vite HTTP y Chromium, login/usuarios/datos sintéticos, 5°, comparación
FF/BF/WF consultable y FF legacy por UI y `/runs`, sin consumo de inventario.
**PASS solo del flujo disponible.** Despacho/espera/admisión v2 y seis motores
públicos: **PENDIENTES DE INTEGRACIÓN B05/B06**, registrados también en
[smoke/cleanup.json](smoke/cleanup.json). Pruebas de recursos y smoke de servicios
son evidencias diferentes. No hubo mocks de red ni endpoints temporales.

Incidencias conservadas:

1. [Inicial: 12 PASS / 5 FAIL](process-initial.txt): carrera EOF/watchdog reemplazaba
   la primera causa. Corregida la prioridad. Los escenarios de startup/cálculo
   individuales se separaron del global con cotas de prueba inferiores a producción.
2. [Intermedia: 16 PASS / 1 FAIL](process-tests.txt): una corrida aún activa coincidió
   con la ampliación de argumentos del worker para el control cooperativo. Un hijo
   tomó una firma distinta. Esta corrida quedó invalidada como candidato uniforme;
   no se acredita como validación final. Se esperó el fin y se ejecutaron de nuevo
   los procesos con una única versión; [22 PASS](process-final.txt).
3. [Candidato: 24 PASS / 1 FAIL](process-candidate.txt): la prueba esperaba el nombre
   base ValueError en vez del subtipo real ComparisonSnapshotError que B03 informa.
   Se corrigió la aserción; [caso repetido PASS](process-observer-fix.txt), y luego
   el candidato final completo obtuvo 26 PASS, incluido guard de no solapamiento.
4. Se corrigió la codificación de la tabla derivada por el canal PowerShell→WSL,
   sin alterar números. El generador final escribe UTF-8 directamente.

No hay fallo obligatorio abierto. Los reportes negativos se conservan y no se
cuentan como PASS. No se elevó cota productiva ni se modificó heurística para pasar.

## Reproducción, trazabilidad y limpieza

WSL Ubuntu, Python 3.11.9, PostgreSQL 18.6, Node 22.23.2 y Chromium Playwright
instalados previamente. Desde `backend/`, con `.venv/wsl/bin` en PATH:

```sh
export PYTHON_DOTENV_DISABLED=1 NEWGLASS_REQUIRE_POSTGRES=1
export NEWGLASS_TEST_PG_BIN=/usr/lib/postgresql/18/bin
python -m tests.optimization_b04_probe
python -m pytest tests/unit/optimization/test_sequential_runner.py -q -ra --tb=short --junitxml=../docs/evidence/sprint-02/TA-043/B04/process-verified-junit.xml
python -m tests.optimization_b04_validation
python -m pytest tests/unit/optimization/test_engine_execution.py tests/unit/optimization/test_comparison_v2_contract.py tests/unit/optimization/test_comparison_snapshot.py -q -ra --tb=short --junitxml=../docs/evidence/sprint-02/TA-043/B04/contracts-adapters-junit.xml
python -m pytest tests/unit/optimization/test_comparison_runner.py -q -ra --tb=short --junitxml=../docs/evidence/sprint-02/TA-043/B04/v1-process-junit.xml
python -m scripts.check_comparison_environment --profile comparison-v2
python -m tests.optimization_b01_smoke --block B04 --runtime-root /home/fabri/.cache/newglass-validation.SXhCMM
```

El runtime-root del smoke apunta a dependencias Linux locales existentes; en otra
máquina indicar la instalación equivalente. La primitiva y el diagnóstico no usan
DB. Solo el smoke crea/migra PostgreSQL temporal propio. No se apunta al `.env`.
No hay código frontend modificado: lint/build frontend no son checks de este
cambio Python. Se verifican sintaxis Python, enlaces, hashes, presupuesto intacto,
36 requisitos/CA/filas y once bloques conservados, y git diff --check.

| Requisito / CA | Acreditado en B04 / pendiente |
|---|---|
| RF-03 / CA-03 | Seis scopes contabilizados, orden y nunca iniciadas con causa; persistencia de esas transiciones B05 |
| RF-04 / CA-04 | Completo/parcial/fallo y causas M6/externas preservadas; no se rescata un parcial sin paquete válido tras kill |
| RNF-01 / CA-N01 | Spawn, instancias aisladas, hash/scope y propiedad de retención; transporte a máscara HTTP B05/B06 |
| RNF-02 / CA-N02 | Cotas compartidas, preflight, RSS/VM, IPC, retención, reloj y pruebas reales; capacidad proyectada completa pendiente |
| RNF-03 / CA-N03 | Cierre de hijos/lectores/watchdog/descendientes y guard conservador; muerte del supervisor dueño antes de admisión B05 |
| ST-INC-04 | Servicios actuales PASS; nuevas capacidades públicas pendientes sin PASS anticipado |

La limpieza del smoke registra procesos propios antes/después vacíos, runner exit
0 y copia temporal/TMPDIR/clúster eliminados. Los procesos de los ensayos se unen
antes de cada despacho y quedan con identidad posterior null; lectores/monitores
se unen al cerrar. La prueba de descendiente verifica cierre de su propio árbol.
[validation.json](validation.json) registra además puertos libres, temporales,
fuentes ensayadas, correspondencia con el smoke y validaciones documentales.
Un cierre incierto produce WorkersNotStopped/guard cerrado, nunca una autorización
para liberar la admisión de B05.

Riesgos para B05: integración única de admisión FF/v1/v2; evitar ejecutar dos
instancias v2 a la vez; dueño externo que espera fin del supervisor real; persistir
antes de anunciar; no duplicar retención; continuar drenando IPC aunque no haya
visores; reconciliación conservadora y prueba de identidad al recuperar procesos.
Mantener las mediciones grandes/Heroku pendientes y HU-018 separado de esta base.

Detenerse al presentar estos resultados. No iniciar B05 sin revisión/autorización.
