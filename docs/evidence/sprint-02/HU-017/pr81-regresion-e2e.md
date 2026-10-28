# HU-017 — PR #81: regresión de observación E2E

27/10/2026, America/Lima. Rama `feature/HU-017-proceso-visual-optimizacion`.
Base reproducida sin cambios: `a04401c5590381d098bb59009fe57835b9be742f`.
PR: [#81](https://github.com/melendezzz26/optimizador-vidrio/pull/81), destino
`integration/sprint-01`. Ajuste local para revisión; sin commit, push o merge.

## Causa demostrada

Los dos escenarios esperaban una igualdad textual con
`http://127.0.0.1:8017/api/optimization/runs`. HU-017 solicita por decisión
aprobada [DG-01/B](../../../specs/DECISION-HU-017-DG-01-streaming-visual.md)
el mismo endpoint con `?stream_profile=visual-v2`. El predicado descartaba la
respuesta real y agotaba los 30 s originales. No faltaba un POST ni existía
un bloqueo del botón, una petición a otro endpoint o una precondición inválida.

| Escenario original | Desktop | Móvil | Evidencia de la aplicación al fallar el test |
|---|---|---|---|
| S1: editar tres veces | POST real V2, 201 | POST real V2, 201 | `error-context.md`: Resultado completo, Distribución lista y Confirmar corte. |
| TA-037: 151 unidades | POST real V2, 422 | POST real V2, 422 | Aviso del límite 150/151 ya visible y selección conservada. |

Se reprodujeron los cuatro casos por separado con un worker antes de modificar
los tests: cuatro timeouts en los mismos `waitForResponse`. Después se reprodujeron
juntos con dos workers: **0 passed / 4 failed / 0 skipped**, 74.54 s, retries 0.
La misma causa ocurre con y sin concurrencia: no se clasifica como flakiness.

Las trazas de red originales y posteriores al arreglo se resumieron sin headers,
cookies ni tokens en [pr81-network-summary.txt](pr81-network-summary.txt).
Se inspeccionaron las respuestas, snapshots DOM/error-context y consola de los
cuatro casos: cero `pageError`; S1 sin errores de consola; TA-037 solo registra
el error de recurso HTTP 422 esperado. Los ZIP de trazas permanecen en el temporal
local, no se publican como evidencia que pueda contener autenticación de prueba.

### Recorrido inspeccionado

- `OptimizationPage.jsx`: Revisar vidrios y piezas llama a `prepare`; Calcular
  distribución llama a `flow.run`. El requisito raster previo solo corresponde
  al adaptador fixture, no al backend real.
- `useFirstFit.prepare`, `optimizationReducer.prepared`: snapshots de los pedidos
  seleccionados; selección y estado PENDIENTE válidos antes de iniciar.
- `useFirstFit.run`, `createRunTransport`: crean la fuente de eventos y ejecutan
  el POST real. No se sustituyó el clic por una llamada artificial.
- `createBackendRunAdapter`: la pantalla pasa `streamProfile: 'visual-v2'` y `open`
  añade la query aprobada. El body sigue siendo `{order_ids}`.
- `runContract.js` conserva V1 estricto; el lector visual es independiente. Las
  rutas backend permiten V1 predeterminado o V2 explícito en el mismo `/runs`.
- TA-037 rechaza 151 unidades con `LOAD_LIMIT_EXCEEDED` antes de aceptar la corrida.
  El reducer restaura prepared, conserva selección y muestra el aviso con foco.

Los contratos anteriores siguen obligatorios: 201 para aceptación válida, 422
con límite correcto para exceso, cuerpo de pedidos exacto, no consumo durante
simulación y confirmación separada. Lo desactualizado era únicamente asumir una
URL completa sin parámetros para observarlos desde el flujo nuevo.

## Corrección mínima

Solo `s1-post-review.spec.js` y `ta037-load-feedback.spec.js` cambian ejecución:

1. Detectar la respuesta por origen exacto de API, pathname exacto `/runs` y POST.
2. Verificar después, con una aserción explícita, `stream_profile=visual-v2`.
3. Mantener 201/422 y todas las aserciones originales de IDs, PUTs, cantidades,
   geometría 3D, selección, foco, pedido y stock. TA-037 además exige el body exacto.

No hay cambios de producto/backend/heurísticas, máscaras, streaming, timeouts,
workers, fixtures ni configuración. No se agregan skip/fixme/only, mocks o retries.

## Entorno y reproducción

Windows; Node 22.23.2, npm 10.9.8, Python 3.11.9 del venv backend, PostgreSQL 18
local y Chromium gestionado por Playwright. Se utiliza el servidor y fixtures
existentes: clúster temporal, usuario sintético `r1_test`, DB `r1_*`, solo loopback.
`optimization_e2e_data.py` verifica ownership del directorio y conexión antes de
crear datos. Se desactiva dotenv. Sin Supabase ni inventario compartido.

Preparación desde `frontend/`, solo en la sesión de pruebas:

```powershell
$env:PATH = (Resolve-Path '..\backend\venv\Scripts').Path + ';' + $env:PATH
$env:PYTHON_DOTENV_DISABLED = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:NEWGLASS_REQUIRE_POSTGRES = '1'
$env:NEWGLASS_TEST_PG_BIN = 'C:\Program Files\PostgreSQL\18\bin'
$env:PLAYWRIGHT_CHANNEL = 'chromium'
```

Diagnóstico aislado original, para cada proyecto `chromium-desktop` y
`chromium-mobile` y cada escenario:

```powershell
npx playwright test s1-post-review.spec.js --grep 'editar tres veces' --project chromium-desktop --workers=1 --trace=on
npx playwright test ta037-load-feedback.spec.js --grep 'TA037 pedido' --project chromium-desktop --workers=1 --trace=on
```

Se repiten ambos con `--project chromium-mobile`. Las trazas/JSON/logs reales de
esta sesión se conservaron bajo `$env:TEMP\newglass-hu017-pr81-repro`, con salidas
independientes por escenario/proyecto y para `joint-before`/`joint-after`.

## Resultados de validación

Dirigida conjunta antes y después, mismo comando salvo directorio de artefactos:

```powershell
npx playwright test s1-post-review.spec.js ta037-load-feedback.spec.js --grep 'editar tres veces|TA037 pedido' --workers=2 --trace=on --reporter=list,json
```

| Ejecución posterior al arreglo | Passed | Failed | Skipped | Duración |
|---|---:|---:|---:|---:|
| S1 desktop | 1 | 0 | 0 | 6.1 s |
| S1 móvil | 1 | 0 | 0 | 5.8 s |
| TA-037 desktop | 1 | 0 | 0 | 4.3 s |
| TA-037 móvil | 1 | 0 | 0 | 4.8 s |
| Conjunto dirigido, 2 workers | **4** | **0** | **0** | **26.28 s** |
| Regresión HU-017 + S1 Optimization + S1 post-review + TA-037, 2 workers | **38** | **0** | **0** | **119.18 s** |
| Suite completa, 114 casos, 2 workers | **107** | **1** | **6** | **221.46 s** |

Comando de regresión focalizada:

```powershell
npx playwright test hu017-unified-flow.spec.js s1-optimization-ui.spec.js s1-post-review.spec.js ta037-load-feedback.spec.js --workers=2 --trace=retain-on-failure --reporter=list,json
```

Suite completa, sin credenciales HU-015 externas y con retries 0:

```powershell
npm run test:e2e -- --workers=2 --trace=retain-on-failure --reporter=list,json
```

El único fallo restante es otro escenario: Dashboard móvil a 390 px. Los cuatro
casos originales pasan también dentro de esta ejecución completa. No se declara
la suite completa verde ni se oculta su fallo mediante el resultado dirigido.

### Hallazgo independiente: Dashboard / HU-016

`ta-dashboard.spec.js:250` llama a `waitForRealDashboard` después de regresar de
Inventario a Inicio. El contador espera exactamente seis respuestas y recibe
siete; agota su timeout original. `watchDashboardResponses` admite cualquier GET
de Inventory/Orders/Clients y solo vacía el arreglo al cambiar de módulo. No
aisla las peticiones iniciadas en cada visita; una respuesta anterior puede
contaminar el ciclo siguiente. La traza muestra GET de Inventario alrededor de
esa navegación, respuestas 200 y Dashboard renderizado, no fallo de `/runs`.

La referencia local de `origin/feature/HU-016-dashboard-inicial` contiene una
corrección de ese mismo defecto en `a8c3b38`, con seguimiento de identidad de
request por ciclo y evidencia `docs/evidence/sprint-02/HU-016/e2e-response-cycles.md`.
Ese commit no es ancestro de este HEAD. No se copia, reimplementa ni fusiona
desde HU-017: requiere coordinar la entrega HU-016 ya desarrollada.

Comprobación aislada, sin editar Dashboard:

```powershell
npx playwright test ta-dashboard.spec.js --grep 'Dashboard real a 390px' --project chromium-mobile --workers=2 --trace=on --reporter=list,json
```

**1 passed**, 16.1 s total (2.4 s de caso), retries 0. Solo hay un caso y
Playwright utiliza un worker efectivo. El éxito aislado no reemplaza el fallo
completo ni acredita estabilidad; clasifica una carrera del observador E2E,
fuera de los cuatro timeouts originales. No se repite la suite para ocultarlo.

Se conservan los reportes JSON y trazas en el temporal. La salida real de la
regresión dirigida/completa queda en [pr81-e2e-results.txt](pr81-e2e-results.txt),
con rutas de máquina anonimizadas y espacios finales normalizados, sin modificar
resultados. Las comprobaciones
de calidad se registran en [pr81-quality-results.txt](pr81-quality-results.txt).
No se atribuye CI remota a estas ejecuciones locales.

### Calidad y regresión de componentes

| Comando desde frontend | Resultado real |
|---|---|
| `npm run test:unit` | 161 passed / 0 failed / 0 skipped; 199.21 ms. |
| `npm run test:component -- src/features/optimization --maxWorkers=2 --reporter=dot` | 165 passed, 15 archivos, 39.55 s; sin fallos. |
| `npm run lint` | Exit 0. |
| `npm run build` | Exit 0; 1993 módulos, 832 ms. Aviso existente de chunk 502.24 kB (>500 kB), sin cambiar umbral. |

No se modificó backend ni se exige una nueva suite backend para este ajuste
exclusivo de observación E2E. Los escenarios de navegador sí ejecutaron backend
y PostgreSQL reales, incluidos rechazo de carga y confirmación transaccional.
Durante la regresión focalizada Windows registró `WinError 10054` de asyncio al
cerrar conexiones; no produjo fallos en esos 38 casos. No se silencia ni corrige
desde HU-017. Los logs conservan esa observación.

## Seis omisiones históricas y TA-040

Se conservan y reportan los tres escenarios de `hu015-rasterization.spec.js`
en ambos proyectos (3 × 2 = 6):

- Flujo real de pieza cantidad 5, raster, recuperación, resolución y responsive.
- CIRCUNFERENCIA comparada con máscara real del backend.
- POLIGONO_CONVEXO con vértices negativos y columnas sobre 53.

El guard existente usa `HU015_E2E_USERNAME/PASSWORD`. No están configuradas en
CI y se dejaron ausentes en la ejecución completa para reproducir esa condición.
No son PASS ni se suman a la cobertura nueva. TA-040 tiene como alcance corregir
esas precondiciones y hacer efectivo el gate contra omisiones; referencia:
`origin/enabler/TA-040-gate-e2e:docs/specs/SPEC-TA-040-gate-e2e-efectivo.md`.
No se implementa TA-040 desde este arreglo ni se cambian sus guards.

## Trazabilidad y límites

| Contrato / CA | Evidencia de esta corrección |
|---|---|
| HU-017 CA-01/02 | El clic de cálculo real produce un único POST con la selección revisada. |
| HU-017 CA-21/22 | Regresión S1/HU-017: stock intacto durante simulación y confirmación explícita separada. |
| HU-017 CA-23 | V1 sin perfil aprobado en el E2E HU-017; V2 se solicita explícitamente. Los seis HU-015 omitidos no acreditan cobertura actual. |
| HU-017 CA-24/25 | Cuatro casos dirigidos, UI/foco/selección en ambos proyectos y regresión unificada. |
| HU-017 CA-26 | Regresión HU-017 de máscara real y recuperación sin un segundo POST. |
| TA-037 CA-02/04/11 | 422 con límite 150/151, pedido PENDIENTE, aviso con foco y selección/stock conservados. |
| S1 post-review / simulación | Tres PUT con ID/listado conservados; POST 201 con pedido exacto y geometría final 160×200 en 3D. |

Se mantienen los 26 textos CA de HU-017 y 10 SP. La SPEC queda Implemented y el
PLAN Approved con entrega implementada, sin Verified formal: CI verde del PR,
revisión cruzada y merge todavía pendientes. No se modifica TA-021.

**Resultado de entrega:** cuatro fallos originales corregidos; regresión propia
38/38 y calidad correctas. La suite completa permanece **107 passed / 1 failed /
6 skipped** por el fallo independiente de Dashboard; no se presenta como verde.
Coordinar la corrección HU-016 existente y TA-040 fuera de este cambio. Tampoco
se declara CI verde remota: este ajuste no tiene commit ni push.

## Actualización 28/10/2026 — aislamiento de ciclos Dashboard autorizado

El registro anterior de **107/1/6** se conserva como ejecución previa real. El
solicitante autoriza ahora adaptar la corrección Dashboard existente para obtener
cero fallos, sin commit, push, merge, rebase o cambios funcionales.

### Referencia inspeccionada y causa exacta

Se ejecutó `git fetch origin` y se inspeccionó
`a8c3b38957cb745c5ab9099f11533e34ca8c8ce9`. Ese commit modifica únicamente
`frontend/tests/e2e/dashboardResponses.js` y añade evidencia HU-016. El helper
había sido extraído por el commit preparatorio `c941ada`. Ninguno de esos cambios
estaba aplicado de otra forma en este HEAD: el test aún tenía el observador inline
y vaciaba solo `responses.length`/`splice` entre visitas.

Vaciar un arreglo no cancela peticiones pendientes. La respuesta de un GET que
comenzó en Inventario podía llegar después de vaciarlo y contarse junto con las
seis fuentes del nuevo Dashboard. Es una carrera del observador entre ciclos de
navegación, no un error de producto ni una nueva expectativa legítima de siete
fuentes. No se encontraron listeners registrados repetidamente por cada visita:
el observador se crea una vez en la página de cada test. Cambiar el conteo o
deduplicar por URL ocultaría el problema y podría descartar respuestas legítimas.

### Adaptación mínima y prueba negativa

- Se extrae el observador y se adapta exactamente el helper de `a8c3b38`: el blob
  resultante coincide, `f32ec882e236f7273f422d1b0ba53a65d9bc8578`.
- `request` registra identidades en un `WeakSet`; `response` solo incorpora una
  identidad vista en el ciclo actual. `beginCycle()` cambia el conjunto y vacía
  el arreglo antes de volver a Inicio, recargar o reintentar.
- Se conservan filtros de origen/método/recurso y respuestas actuales 403/503;
  las solicitudes repetidas actuales no se ocultan por una deduplicación de URL.
- Se mantienen todas las aserciones E2E: seis/dos fuentes, contenido real,
  permisos, navegación, responsive, refresh/logout y error parcial explícito.
  No se añaden waits artificiales, retries, skips ni cambios de timeout.
- Se adaptan seis unitarias deterministas de la referencia. Con el comportamiento
  original extraído: **3 passed / 3 failed**, incluyendo séptima respuesta tardía,
  mezcla de ciclos y respuesta sin petición observada. Tras el arreglo:
  **6 passed / 0 failed**. Son pruebas unitarias del observador, no evidencia
  simulada presentada como integración backend.

Archivos adicionales a los nueve cambios previos conservados:
`frontend/tests/e2e/dashboardResponses.js`,
`frontend/tests/unit/dashboardResponses.test.js` y
`frontend/tests/e2e/ta-dashboard.spec.js`. No se usa cherry-pick ni se trae la
rama completa HU-016. Los tests previos S1/TA-037 permanecen intactos.

### Regresión posterior al arreglo Dashboard

Mismo entorno aislado descrito arriba: Windows, Node 22.23.2, Python 3.11.9,
PostgreSQL 18 temporal en loopback y Chromium gestionado. Dos workers configurados,
retries 0 y timeouts originales. Artefactos locales de esta ejecución separados
en `$env:TEMP\newglass-hu017-pr81-dashboard`; no se sobrescriben los anteriores.

```powershell
node --test tests/unit/dashboardResponses.test.js
npx playwright test ta-dashboard.spec.js --grep 'Dashboard real a 390px' --project chromium-mobile --workers=2 --trace=on --reporter=list,json
npx playwright test ta-dashboard.spec.js s1-post-review.spec.js ta037-load-feedback.spec.js hu017-unified-flow.spec.js --workers=2 --trace=retain-on-failure --reporter=list,json
```

El caso móvil aislado pasa: **1/0/0**, 38.28 s de ejecución total; un worker efectivo
para ese único caso. La regresión conjunta pasa: **36/0/0**, 138.19 s, incluidos
las 22 ejecuciones Dashboard desktop/móvil, cuatro S1, dos TA-037 y ocho HU-017.

### Resultado definitivo de esta corrección

```powershell
npm run test:e2e -- --workers=2 --trace=retain-on-failure --reporter=list,json
npm run test:unit
npm run test:component -- src/features/dashboard src/features/optimization --maxWorkers=2 --reporter=dot
npm run lint
npm run build
```

| Ejecución real del 28/10 | Passed | Failed | Skipped | Duración |
|---|---:|---:|---:|---:|
| Dashboard móvil 390 px aislado | 1 | 0 | 0 | 38.28 s |
| Dashboard desktop/móvil + S1/TA-037/HU-017 | 36 | 0 | 0 | 138.19 s |
| **Suite E2E completa, 114 casos, dos workers** | **108** | **0** | **6** | **291.93 s** |
| Unitarias frontend, incluidas seis del observador | 167 | 0 | 0 | 347.03 ms |
| Componentes Dashboard + Optimization, 20 archivos | 240 | 0 | 0 | 73.10 s |

Lint y build terminaron con exit 0. Build: 1993 módulos, 1.51 s; mantiene el
aviso existente de chunk 502.24 kB (>500 kB), sin modificar umbral. No se ejecuta
otra suite backend: no cambió backend y los E2E utilizaron API/DB reales.

Los reportes JSON confirman cero fallos, cero resultados flaky y retries 0. En
la suite completa pasan los 22 Dashboard, el caso móvil 390 px y los cuatro
escenarios originales S1/TA-037. Se conservan los tests reales de POST V1 sin
perfil, POST visual-v2, 201, 422, selección, recuperación por GET, máscaras
autoritativas, stock intacto durante simulación y confirmación explícita.
El caso preexistente de error HTTP simulado de Dashboard sigue identificado
como controlado; no se presenta como una avería real del backend.

Las tres pruebas HU-015 omitidas en ambos proyectos siguen siendo los **seis
skips** enumerados arriba. No se declaran aprobadas ni se altera su guard. El
fetch de esta sesión actualizó `origin/integration/sprint-01` a
`332e0c000acd8f98c226d36a2b0783ff16c63efa`, que ya contiene las entregas TA-040 y
TA-041 posteriores. Este arreglo se valida sobre HU-017 `a04401c` más sus cambios
locales; no incorpora esa base nueva por la restricción de no merge/rebase.
Por tanto, el resultado **108/0/6** describe esta rama y no acredita por sí solo
el gate actualizado de TA-040 ni la futura combinación de integración.

Se anexaron las salidas posteriores a `pr81-e2e-results.txt` y
`pr81-quality-results.txt`, preservando sus registros anteriores. La evidencia
de red previa permanece intacta. Se conservan los nueve cambios pendientes
iniciales y los 26 CA, sin editar producto, motor, FF/BF/WF, métricas, persistencia,
streaming o configuración E2E. No se realiza commit, push, cherry-pick ni merge.

**Estado final local:** suite E2E completa con cero fallos; lista para revisión.
La CI remota del PR no se vuelve verde hasta publicar y validar el ajuste con
la base correspondiente. Revisión cruzada, CI del PR y merge siguen pendientes;
SPEC Implemented/PLAN Approved, sin Verified formal ni autorización de despliegue.
