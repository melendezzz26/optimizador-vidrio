# TA-047 — Preflight geométrico de comparación v2

Trabajo local sobre `fix/S2-TA047-preflight-v2`, derivada de
`recovery/sprint-02` en `678ab92f3a32d37509b67779f99359acacedde2f`.
Auditoría del 2026-11-05 (America/Lima). Sin push, actualización del PR #102,
modificación de ramas oficiales, Supabase ni despliegue.

## Causa raíz y contrato existente

`AcceptRun` ya valida selección, configuración vigente única, paso de 5°,
pedidos pendientes, presencia de piezas, cantidades, vértices, dimensiones y
presupuesto raster antes de `runs.create` y de la transición de pedidos.
Usa `check_pieces`, `check_stock` y `prepare_persisted_problem`; esta última
reutiliza el validador público de piezas persistidas de Pedidos. No comprueba
encaje individual ni rechaza la falta de stock. La preparación de geometría
ocurre durante el cálculo, fuera de la transacción de aceptación.

Comparación v1 comparte esas validaciones, captura stock y lo congela antes de
crear su agregado. V2 añade RBAC dentro de la transacción, snapshot repetible,
reintentos de conflictos e idempotencia, pero dejaba sin adelantar la barrera
geométrica del stock. `StockCandidate` verifica formato canónico, números
finitos, material e identidades; no verifica convexidad, degeneración o límites
de raster. Así podían aceptarse fuentes de más de 4000 mm, más de 4000 celdas
por eje, más de 128 vértices y polígonos inválidos.

La primera escritura de negocio de v2 está en
`SqlComparisonV2Repository.create`: `add(Optimizacion)` y `flush`, seguidos de
vínculos de pedidos y seis `EjecucionOptimizacion`. Después se cambia el lote a
`EN_OPTIMIZACION`. Consultas, bloqueos de pedidos y advisory locks anteriores
no escriben registros de negocio. La reserva de admisión en memoria se adquiere
antes de aceptar; el coordinador ya la libera cuando falla la aceptación.

La reproducción sobre el código base, con las regresiones definitivas de
rechazo, dio **6 fallos y 8 aprobadas**: las seis formas de stock inválido
recibían HTTP 201. El test impide ejecutar motores: demuestra aceptación y
persistencia prematuras, sin atribuir a un motor la excepción sintética.

Una segunda deficiencia estaba en `ComparisonV2Coordinator.start`: retiraba
eventos y máscaras del trabajo anterior antes de aceptar el nuevo. Se reprodujo
con una comparación completada real, un pedido pendiente nuevo y stock inválido:
el HTTP 422 dejaba `job.disposed=True` y perdía la ventana visual anterior.
La regresión falló antes de mover la limpieza a después de la aceptación.

## Corrección acotada

- `domain/rotation.py`: extrae `RasterCache.check_base_geometry` de las dos
  comprobaciones ya existentes de preparación: geometría original y base
  normalizada a 0° con RN-04.
- `domain/run_geometry.py`: llama ese método en el mismo punto de su barrera,
  conservando orden, checkpoints y preparación posterior.
- `application/geometric_preflight.py`: valida las bases y límites de piezas y
  fuentes congeladas, reutiliza `raster_number` y `discrete_angles`, y aplica
  `Inventory.calculate_area_mm2` a los retazos. Comprueba límites antes de la
  validación cuadrática de polígonos y una vez por pieza/fuente persistida.
- `application/comparison_acceptance_v2.py`: invoca el preflight después de
  preparar el snapshot y antes de construir/persistir el agregado.
- `presentation/comparison_supervision_v2.py`: retira el trabajo previo solo
  después de aceptar; un rechazo conserva sus eventos y máscaras. La limpieza
  sigue ocurriendo antes de asignar el nuevo trabajo y sus buffers.
- `tests/api/optimization/test_comparison_v2_preflight.py`: regresiones HTTP con
  PostgreSQL temporal obligatorio, observación de SQL y comparación de todas
  las tablas antes/después; casos válidos ejecutan los seis motores nativos.
  Incluye la conservación de la ventana anterior frente a una solicitud inválida.
- `tests/unit/optimization/test_geometric_preflight.py`: precisión, límites,
  RN-04, separación entre contratos de Pedidos/Inventario y ausencia de
  rasterización, búsqueda y mutación.

Los errores siguen pasando por el contrato existente `RunRoute`:
`422 INVALID_INPUT` para geometría inválida, `422 LOAD_LIMIT_EXCEEDED` con sus
detalles existentes para límites operativos y `409 CONFIG_CONFLICT` para
configuración vigente incompatible. No se añade formato de error.

El preflight no asigna máscaras, enumera posiciones, evalúa encaje ni ejecuta
heurísticas. Márgenes/separaciones conservan el ceil racional exacto de TA-045
en `packing._empty_layout`; no pasan a float ni se normalizan en el snapshot.
El redondeo RN-04 y la enumeración de rotaciones siguen siendo los existentes.
Las orientaciones diagonales que exceden el raster siguen descartándose por
TA-016, sin invalidar una base de 4000 × 4000 mm que sí puede usarse.

Una entrada válida sin stock, sin encaje, con margen que bloquea el material o
sin capacidad suficiente por separación sigue aceptándose. FF, BF, WF, HF, M5
y M6-BS producen sus resultados y diagnóstico `NO_FIT`/`SIN_SOLUCION` normales.
Los límites dinámicos de M6 y los fallos técnicos conservan su contrato propio.

## Diferencias con TA-047 histórica

Se inspeccionó `recovery-audit/TA-047`, SHA
`a345f33251ea472b5d12cf2e37b2a046f5df652b`, con base
`7556a700496673d00fe41b6036d69d91d0939959`. No se fusionó ni se hizo cherry-pick.

| Aspecto | Histórica | Esta corrección |
|---|---|---|
| Aceptación modificada | `/runs` cuando el proveedor expone `list_compatible` | Solo comparación v2 |
| Pregunta del preflight | Si cada pieza cabe en una fuente vacía | Si la entrada congelada cumple los contratos geométricos |
| Falta de stock / no encaje | `422 INVALID_INPUT` y `preflight_errors` | Entrada válida; resultado posterior `SIN_SOLUCION` |
| Trabajo previo | Rasteriza, prueba posiciones y puede recorrer 72 ángulos | Comprobaciones de base sin máscaras ni búsqueda |
| Stock | Lectura adicional por proveedor | Snapshot v2 ya capturado en su transacción |
| Contratos de contorno | Asume los datos recibidos | Pedidos para piezas; Inventario para retazos |
| Evidencia PostgreSQL/E2E | Registra omisiones dependientes de entorno | Ver resultados de esta ejecución abajo |

Se comparten funciones, no reglas reimplementadas. No se aplica la convexidad
estricta de Inventario a piezas: Pedidos permite ciertos vértices colineales.
La aceptación histórica de `/runs` y v1 permanece intacta. Los seis motores
usan la misma barrera de base extraída, sin cambio de comportamiento.
Lecturas y replays de agregados existentes no ejecutan el nuevo preflight ni
recapturan inventario; las regresiones lo prueban alterando el stock vivo tras
terminar una comparación.

## Validación

Las suites se ejecutan en una copia privada Linux/WSL de esta rama con Python
3.11.9, Node 22.23.2, PostgreSQL 18.6 y dependencias locales del lockfile. Se
deshabilita dotenv, se elimina `DATABASE_URL` heredado y se exige
`NEWGLASS_REQUIRE_POSTGRES=1`, con `NEWGLASS_TEST_PG_BIN` local. Las fixtures
crean y detienen clústeres PostgreSQL exclusivos en loopback; no usan bases
compartidas. Los procesos de pruebas no cambian presupuestos de producción.

| Suite / comando | Resultado final |
|---|---|
| Preflight API + unidad + barrera geométrica existente | 55 PASS |
| Backend completo, con las cuatro exclusiones del workflow | 3126 PASS |
| `test_comparison_calculation.py`, proceso nuevo | 8 PASS |
| `test_comparison_supervision_v2.py`, proceso nuevo | 26 PASS |
| `test_sequential_runner.py`, proceso nuevo | 26 PASS |
| `test_comparison_runner.py`, proceso nuevo | 14 PASS |
| Backend total, sin contar dos veces el bloque focalizado | **3200 PASS; 0 fallos, 0 skips** |
| `npm run test:unit` (incluye gate y protocolo de fases) | 213 PASS |
| `npm run test:component -- --maxWorkers=2` | 589 PASS, 57 archivos |
| `npm run lint` | PASS |
| `npm run build` | PASS |
| E2E B02, fase 1 | 2 PASS |
| E2E restante, fase 2 | 144 PASS |
| E2E global de dos fases / TA-040 | **146/146 PASS; 0 skips, 0 retries, 0 flaky** |

Los comandos backend son los del workflow, con las suites sensibles a recursos
en procesos separados. Cubren API, integración PostgreSQL, geometría/raster,
TA-045, contratos/snapshots, los seis motores, supervisión, persistencia,
confirmación y compatibilidad histórica. Las 35 regresiones nuevas están
incluidas en el total backend. El bloque focalizado no se suma otra vez.
Las salidas finales se conservan en `test-results/`.

Los rechazos comprueban que no hay `INSERT`, `UPDATE` ni `DELETE` y que todas
las tablas conservan sus filas: comparaciones, ejecuciones, asociaciones,
estados, reservas y movimientos de inventario. También prueban que no arranca
ningún motor, que la admisión vuelve a cero y que puede adquirirse de nuevo
el token exclusivo. Otra regresión conserva los eventos y las máscaras de la
comparación anterior completada.

El protocolo E2E original se ejecutó con UUID
`78da438b-f3ad-43d0-ab66-592872589ea8`, del 2026-11-05 20:31:55 al 20:44:57
(America/Lima). Descubrió 146 casos, ejecutó primero B02 y después los 144
restantes: 73 en Chromium escritorio y 73 en Chromium móvil. Se comprobaron
identificadores exactos contra el plan, sin duplicados, omisiones, fallos ni
reintentos. El gate conjunto TA-040 terminó con `ok=true`, sin excepciones
aprobadas ni problemas. Los dos clústeres PostgreSQL temporales de las fases
quedaron detenidos (`pg_ctl status=3`, sin `postmaster.pid`), ambos en loopback.
Los mensajes de fallo FF de persistencia del log corresponden a escenarios
que inyectan ese fallo deliberadamente y cuyas aserciones aprobaron.

Un primer intento E2E falló al lanzar Chromium: la ruta temporal larga
excedía el límite del socket `SingletonSocket`, antes de ejecutar escenarios.
Se conserva por separado con UUID `213cd8e4-1d35-4c42-aa6c-afa2688c91e4`,
en `attempts/` y `test-results/e2e-initial.txt`. La corrida final usó una ruta
`TMPDIR` corta en `/tmp`; no cambió tests, gate, navegador, retries ni timeouts.

La primera ejecución de componentes con concurrencia predeterminada dio 575
aprobadas y 14 fallos, incluidos timeouts de 5000 ms. WSL anunciaba 22 CPU.
La misma suite completa pasó con dos workers locales; no se modificó ningún
archivo frontend, configuración, timeout, retry, aserción ni presupuesto de
los motores. Se conservan ambas salidas de componentes. El build conserva
únicamente su aviso existente de chunk superior a 500 kB y backend su aviso
existente de deprecación Starlette/httpx.

Una primera corrida backend aprobó sus 3125 casos de entonces, pero el ejecutor
temporal terminó con error de shell al haber sido editado durante la ejecución.
La repetición se interrumpió al descubrir la pérdida de retención anterior.
La tabla refleja la corrida completa posterior del código final: 3126 aprobadas
y salida 0, más las cuatro suites aisladas finales. No se computan intentos
incompletos como certificación.

Para respetar la condición de crear un commit solo tras completar las pruebas,
se fijó primero el índice candidato con árbol Git
`a4dbcae3aef780f347e2b74d3b5aadf60534a0df`. La copia privada usa ese índice y
verifica que no existan diferencias de contenido contra su working tree.
Los reportes E2E originales conservan el HEAD base `678ab92`, anterior al commit;
la identidad del contenido candidato está en el árbol y el manifiesto de fuentes
de `global-e2e/provenance.json`. No se altera el SHA de los reportes para atribuir
la corrida a un commit todavía inexistente.

Después del PASS global se creó el commit de implementación
`232a85839cf0107e0dedfe8de0070878d1a1f9b0`. Su árbol completo es exactamente
`a4dbcae3aef780f347e2b74d3b5aadf60534a0df`, el candidato probado; su padre es
la base `678ab92f3a32d37509b67779f99359acacedde2f`. La comprobación queda en
[`global-e2e/commit-proof.json`](global-e2e/commit-proof.json). El commit
posterior añade únicamente esta evidencia, sin cambios de código.

### Evidencia y reproducción

- [`global-e2e/validation.json`](global-e2e/validation.json): resultado original
  del gate; [`plan.json`](global-e2e/plan.json), [`b02.json`](global-e2e/b02.json)
  y [`remaining.json`](global-e2e/remaining.json): descubrimiento y resultados.
- [`global-e2e/provenance.json`](global-e2e/provenance.json): versiones, entorno,
  árbol candidato, SHA-256 de las fuentes antes/después y cierre de PostgreSQL.
- [`test-results/backend.txt`](test-results/backend.txt), las cuatro salidas
  aisladas y [`focused.txt`](test-results/focused.txt): backend final.
- [`test-results/red.txt`](test-results/red.txt): reproducción del defecto
  geométrico en la base. Los logs frontend y E2E incluyen sus intentos iniciales.
- [`SHA256SUMS`](SHA256SUMS): integridad de los archivos de este directorio,
  salvo el propio manifiesto. Los JSON originales se copian sin modificación;
  los logs eliminan únicamente escapes ANSI, espacios de fin de línea y líneas
  vacías finales.

En Linux con las dependencias del lockfile y binarios PostgreSQL locales,
sin variables de conexión heredadas ni dotenv, desde `backend/`:

```sh
export NEWGLASS_REQUIRE_POSTGRES=1 PYTHON_DOTENV_DISABLED=1
export NEWGLASS_TEST_PG_BIN=/usr/lib/postgresql/18/bin
unset DATABASE_URL SECRET_KEY
python -m pytest tests --ignore=tests/unit/optimization/test_comparison_runner.py --ignore=tests/integration/optimization/test_comparison_calculation.py --ignore=tests/integration/optimization/test_comparison_supervision_v2.py --ignore=tests/unit/optimization/test_sequential_runner.py -q -ra --tb=short
python -m pytest tests/integration/optimization/test_comparison_calculation.py -q -ra --tb=short
python -m pytest tests/integration/optimization/test_comparison_supervision_v2.py -q -ra --tb=short
python -m pytest tests/unit/optimization/test_sequential_runner.py -q -ra --tb=short
python -m pytest tests/unit/optimization/test_comparison_runner.py -q -ra --tb=short
```

Desde `frontend/`, con Node y Python disponibles en `PATH` y el mismo entorno
PostgreSQL local:

```sh
npm run test:unit
npm run test:component -- --maxWorkers=2
npm run lint
npm run build
export TMPDIR="$(mktemp -d /tmp/t47.XXXXXX)"
export CI=true PLAYWRIGHT_CHANNEL=chromium
node scripts/run-e2e-phases.js
```

### Integración local

La rama local puede integrarse por fast-forward desde `recovery/sprint-02`
en `678ab92f3a32d37509b67779f99359acacedde2f`: es ancestro directo y no hubo
merge, rebase ni cherry-pick. La referencia remota local conocida sigue en
esa misma base; no se hace fetch ni se presume el estado remoto actual.
Con las suites y el gate anteriores aprobados, la corrección queda lista para
revisión e integración local. No se ejecutó CI remoto ni se modificó el PR #102.

## Riesgos y límites

Stock activo heredado que incumpla el contrato de Inventario o los límites
existentes ahora bloquea una solicitud nueva v2 con 422, aunque hubiese otra
fuente utilizable. Es coherente con la preparación actual, que procesa todas
las fuentes congeladas; no se filtran ni corrigen datos silenciosamente.
No se revalida historia ni se migra información.

La validación de contornos añade trabajo acotado a la transacción de aceptación
(máximo de vértices y fuentes existente). No garantiza solución, no adelanta
límites dinámicos de búsqueda ni sustituye las comprobaciones durante cálculo
y confirmación. No se modifican heurísticas, límites, presupuestos, workflows,
frontend ni contratos JSON publicados.
