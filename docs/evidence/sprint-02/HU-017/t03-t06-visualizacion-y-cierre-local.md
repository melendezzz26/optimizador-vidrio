# HU-017 T03–T06 — Visualización y verificación local

## Alcance de esta entrega

28/10/2026 UTC. Rama `feature/HU-017-proceso-visual-optimizacion`, derivada de
`4bcf54d` de `integration/sprint-01`. Continuación de
[T01](t01-flujo-unificado.md) y [T02](t02-bases-y-rotaciones-lazy.md), conforme a
la [SPEC](../../../specs/SPEC-HU-017-proceso-visual-optimizacion.md), el
[PLAN](../../../specs/PLAN-HU-017-proceso-visual-optimizacion.md) y
[DG-01/B](../../../specs/DECISION-HU-017-DG-01-streaming-visual.md).

El solicitante autorizó completar HU-017 con pruebas temporales, como excepción
para esta historia. Se usó PostgreSQL 17 aislado, administrado por los fixtures,
y cuentas sintéticas. No se conectó a Supabase ni se utilizó staging. Las
validaciones posteriores deberán usar la BD de desarrollo/pruebas indicada por
el solicitante, mediante configuración explícita y fixtures apropiados para ese
entorno; esta excepción no autoriza reutilizar limpieza destructiva de fixtures
temporales sobre una BD compartida. No se creó un archivo de credenciales.

Este checkpoint se registró antes de publicar HU-017 o abrir PR; sus resultados
son locales y no acreditan CI remota/despliegue ni revisión cruzada humana.
Actualmente la rama está publicada y propuesta en PR #81. El diagnóstico y la
corrección local de sus cuatro fallos E2E se registran en
[pr81-regresion-e2e.md](pr81-regresion-e2e.md), sin alterar los resultados
históricos de este archivo ni publicar el ajuste antes de revisión.

| Commit | Incremento |
|---|---|
| `aca12c2` | Pruebas previas de contrato optativo, máscaras reales y compatibilidad. |
| `1ec14f7` | Eventos V2 acotados, retención y recuperación autoritativa. |
| `da40a11` | Pruebas de inspección, recuperación, aislamiento visual y consumidor lento. |
| `3574609` | Panel visual, integración de resultado y endurecimiento de recuperación. |
| `f13d4c7` | Medición reproducible de proyección visual frente a cálculo sin observación. |

## Implementación comprobable

`POST /api/optimization/runs?stream_profile=visual-v2` conserva el body
`{order_ids}` y el mismo motor/ciclo de corrida. Sin perfil o con `v1` conserva
los ocho eventos V1. Un perfil desconocido, vacío o duplicado se rechaza antes
de aceptar pedidos o reservar recursos. GET y confirmación conservan V1.

Los siete hechos nuevos describen preparación, bases listas, orientación
realmente evaluada, fuente elegida y unidad NO_FIT. Los hechos salen del
recorrido compartido del dominio; no hay otro rasterizador ni heurística visual.
Se distinguen procesadas y colocadas. Error técnico, agotamiento de recursos y
desconexión no se convierten en NO_FIT. Al desconectar después de elegir una
fuente se conserva la colocación diagnóstica real, sin duplicarla al recibir el
hito de colocación.

Se reutilizan transporte NDJSON, cola de uno, acknowledgement, checkpoints y
consulta por ID/Location. Observación, referencias, serialización y espera de
entrega se excluyen de los relojes de cálculo y presupuesto. Ocultar/pausar solo
congela el detalle local; continúa la recepción y el contador real. No hay sleeps
para animación, eventos por celda/posición ni historial ilimitado.

La UI integra preparación y cálculo en Optimization. Presenta etapa, orden de
unidades observado, pieza actual, muestra angular, fuente física y máscara. El
detalle identifica resolución, dimensiones y ordinal; FF no recibe un score
inventado. Las vistas 2D/3D conservan placements canónicos y el raster de resultado
consulta las máscaras de esa misma corrida. El resultado enumera faltantes y
motivos, método/configuración efectivos, métricas y residuales disponibles. La
confirmación solo se habilita después de GET autoritativo y conserva permisos,
diálogo y transacción existentes.

La inspección carga una ventana exacta de la máscara inmutable del backend,
mediante canvas reutilizado. Explica qué ventana se muestra y que el resto queda
fuera de la vista; el contorno completo y el original se distinguen. Puede seguir
la pieza actual o seleccionar una referencia retenida. Se valida corrida,
pieza/fuente, resolución, orientación, dimensiones y ventana; se abortan o ignoran
respuestas anteriores. Una orientación sin detalle por presupuesto no se
sustituye silenciosamente por la máscara base. Expiración/error visual no borra
el resultado ni inicia otro cálculo.

## Cotas y recuperación

| Recurso | Límite probado / comportamiento |
|---|---|
| Frames V2 | Hasta 64 KiB UTF-8 por línea, sin máscaras embebidas. |
| Muestreo | Primera evaluación real por unidad, hasta 150; hasta 128 adicionales, máximo 10 adicionales/s con reloj monotónico. Los hechos críticos se conservan. |
| Cola | Una entrega pendiente con ack; no avanza la preparación mientras el consumidor está suspendido en su evento inicial. |
| Máscaras | Objetos reales compartidos, hasta 64 MiB contabilizados y 1024 referencias por contexto. Presupuesto visual agotado: indisponibilidad explícita, mismo resultado. |
| Contextos | Hasta dos; no se desalojan activos. Uno terminado puede desalojarse para aceptar otro. |
| TTL | Consultables hasta 300 s tras finalizar el worker, o menos si hay desalojo/reinicio. Limpieza perezosa al reservar/consultar: no existe borrado mediante temporizador en reposo. La memoria retenida sigue acotada a dos contextos. |
| Manifiesto | Hasta 64 descriptores por página, revisión monotónica y contadores recuperables; la UI limita el total a 1024 y rechaza páginas incoherentes. |
| Ventana | Hasta 256 filas × 1024 columnas; JSON hasta 256 KiB. Rangos de bits y offsets absolutos, sin cambiar resolución del motor. |
| Frontend | Lectura incremental acotada de NDJSON/JSON, fetch por frame, abortos y un resultado de ventana cacheado por inspector; sin DOM por celda. |
| Acceso | `optimization.view`, además de la consulta canónica; 401/403, 404 para referencia ajena y 410 para detalle no disponible. Iniciar/confirmar mantienen sus permisos independientes. |

La retención es local al proceso. No promete persistencia de máscaras en BD,
replay, cancelación distribuida ni disponibilidad mínima de cinco minutos. Al
recuperar se consulta primero el resultado guardado y luego el manifiesto; si
el detalle expiró, el resultado sigue siendo consultable/confirmable según sus
propias reglas. Los límites anteriores no son una garantía global de RSS del
servidor, DB o todas las solicitudes concurrentes.

## Verificación reproducible

Desde `backend/`, usando el entorno virtual existente y PostgreSQL temporal:

```bash
NEWGLASS_TEST_PG_BIN=/tmp/hu016-tools/root/usr/lib/postgresql/17/bin NEWGLASS_REQUIRE_POSTGRES=1 .venv/bin/python -m pytest -q
NEWGLASS_TEST_PG_BIN=/tmp/hu016-tools/root/usr/lib/postgresql/17/bin NEWGLASS_REQUIRE_POSTGRES=1 .venv/bin/python -m pytest tests/api/optimization/test_visual_runs_api.py -q
```

Resultado final de suite completa: **2312 passed**, 398.34 s, una advertencia
previa TestClient/httpx y ningún skip.
La ampliación API final, incluido consumidor visual lento: **12 passed**,
10.30 s; una advertencia previa de deprecación TestClient/httpx. Esta prueba
adicional se incorporó después de comenzar la suite completa y se ejecutó por
separado; los recuentos no se suman como pruebas distintas.

`test_visual_facts.py` compara los ocho casos representativos de TA-021 con y
sin observación para FF/BF/WF: 24 combinaciones con resultados y hitos iguales,
problema sin mutación, barrera previa y ordinales reales. Además verifica el
cupo 150+128 y que no se generen ángulos posteriores al primer factible FF.
`test_visual_store.py` cubre compartición de bits, límites exactos/+1, referencias
cruzadas, ventanas, activos, TTL y desalojo. La API contrasta bits/contorno,
configuración aceptada, permisos, NO_FIT, V1, reservas, presupuesto visual,
relojes y desconexión. Las suites existentes completan determinismo, retazos,
desempates, margen/separación y confirmación transaccional.

Desde `frontend/`:

```bash
npm run test:unit
npm run test:component -- --reporter=dot
npm run lint
npm run build
PATH="/workspace/optimizador-vidrio/backend/.venv/bin:$PATH" NEWGLASS_TEST_PG_BIN=/tmp/hu016-tools/root/usr/lib/postgresql/17/bin NEWGLASS_REQUIRE_POSTGRES=1 PYTHON_DOTENV_DISABLED=1 PLAYWRIGHT_CHANNEL=chromium PLAYWRIGHT_BROWSERS_PATH=/tmp/hu016-tools/browsers HU015_E2E_USERNAME=O70000001 HU015_E2E_PASSWORD=Orders-test-2026! npm run test:e2e -- hu017-unified-flow.spec.js s1-optimization-ui.spec.js hu015-rasterization.spec.js --workers=1
```

Resultados finales: **161 unitarias Node**, **506 componentes (47 archivos,
142.91 s)** y **38 E2E (5.7 min)**, todos correctos y sin skips. ESLint y build
de producción correctos. El build mantiene el aviso de tamaño de chunk superior
a 500 kB; no es un fallo de compilación ni se cambió su umbral.
Las credenciales del comando pertenecen a la cuenta sintética publicada en
`backend/tests/e2e_server.py`. Chromium local 154; desktop y mobile, sin retries.
Se usa un worker para recoger evidencia sin desalojar referencias terminadas de
otro escenario concurrente; no se aumentan presupuestos ni se relajan asserts.
El límite real de dos contextos sigue cubierto por pruebas específicas.

Los nuevos componentes prueban loading/éxito/error/410/reintento explícito,
obsolescencia, pausa local, foco y ausencia de máscara. El estado V2 comprueba
secuencias intercaladas, configuración/resolución/ángulo incorrectos, descarte de
hechos tardíos, fallo técnico y confirmación solo después de GET. Se mantienen
las comprobaciones de permisos y regresión V1. La suite E2E conserva HU-015 e
incluye flujo unificado, rotación, parcial, recuperación sin segundo POST,
retazos, multimaterial, stock antes/después y confirmación separada.

Se comprobó ausencia de desbordamiento horizontal en 360/768/1440 px, controles
mediante teclado/foco y preferencia de movimiento reducido. Se inspeccionaron
las capturas reales del contorno y máscara a 90°; no se declara una certificación
completa de lector de pantalla o WCAG.

Capturas seleccionadas del E2E de rotación y recuperación:
[360 px](t04-mascara-real-360.png) y [1440 px](t04-mascara-real-1440.png).

## Medición de recursos

Desde la raíz, sobre `f13d4c7` y sus fuentes, sin BD ni cambios de inventario:

```bash
backend/.venv/bin/python experiments/raster/scripts/hu017_preparation_benchmark.py /workspace/optimizador-vidrio/backend
backend/.venv/bin/python experiments/raster/scripts/hu017_preparation_benchmark.py /workspace/optimizador-vidrio/backend --visual
```

Instancias sintéticas a 1 mm/celda y paso 5°. `tracemalloc` mide asignaciones
Python durante el cálculo, no RSS. Las cotas de cache/referencias son bytes
contabilizados; las máscaras compartidas no constituyen una segunda copia.
La medida visual incluye la proyección real, validación/serialización de los
siete hechos nuevos y retención; no incluye HTTP, los ocho hitos heredados,
latencia de red ni CPU/GPU del navegador. Las ventanas se serializan después de
medir el cálculo. Una corrida por caso, con otras suites ejecutándose: los
tiempos son observaciones locales, sin umbral de aceptación ni promesa de SLO.

| Caso | Pico Python sin/con visual (bytes) | Máscaras pieza sin/con | Referencias | Bytes visuales contabilizados | Nuevos frames / bytes totales / máximo |
|---|---:|---:|---:|---:|---:|
| 8 piezas idénticas 400×300; plancha 2140×3300 | 2 495 324 / 2 513 390 | 1 / 1 | 2 | 1 119 392 | 20 / 14 355 / 979 |
| Pieza 1200×600; plancha 800×1800; requiere giro | 3 758 032 / 3 775 397 | 17 / 17 | 10 | 2 305 284 | 14 / 8 168 / 977 |
| 3 geometrías × 3 unidades; plancha 2140×3300 | 2 690 804 / 2 710 710 | 3 / 3 | 4 | 1 213 584 | 26 / 17 739 / 1002 |

Tiempos transcurridos sin/con visual: 197.75/322.21, 1170.77/1256.74 y
339.10/537.66 ms. Tiempo dentro del callback visual: 23.80, 14.98 y 108.80 ms.
Ventana JSON máxima por caso: 8132, 8416 y 8132 bytes. La cantidad de muestras
puede variar con el reloj; no se usa como resultado algorítmico. Sobre los 30
streams V2 guardados por la ejecución final E2E, incluyendo los hitos heredados:
frame máximo **1014 bytes**, máximo por corrida **24 457 bytes / 42 eventos** y
máximo observado de ocho muestras angulares. No son cotas para todo lote posible;
las cotas contractuales se comprueban aparte mediante API/lectores/sampler.

Los tres hashes funcionales coinciden exactamente sin/con visual:

- 8 idénticas: `9179a653757dc7c66fb2849f85bfb8bcc2c4baabb3e4ebf29ea367f3fc0be965`.
- Requiere giro: `0f446223733ea90b21c5a1d9ff69ea98a853769e1a646ba64e771d973a85579b`.
- 3 geometrías: `e86e84949d81000f30715ccfa70ca6ae136c8731efb4131238be492080f5d8fd`.

La prueba de consumidor lento adelanta 301 s el reloj con el stream suspendido
en `preparation_started`: no hay máscaras adelantadas ni expulsión del contexto
activo; se completa con presupuesto de cálculo de 1 s. Otra prueba añade 60 s
sintéticos por registro y verifica tiempo computacional cero con ambos relojes
controlados. Son comprobaciones deterministas de exclusión temporal, no pruebas
de latencia de producción. La evidencia visual E2E comprueba render completo y
ventanas, sin afirmar una medición aislada de CPU/GPU o FPS del navegador.

## Matriz de los 26 CA

Los archivos backend citados pertenecen a `backend/tests/`; los componentes a
`frontend/src/features/optimization/__tests__/`; los E2E a `frontend/tests/e2e/`.
El estado se refiere al alcance local de la SPEC, con HTTP FF y condiciones
multimétodo expresamente conservadas.

| CA | Evidencia / resultado local |
|---|---|
| 01 | Un solo flujo Optimization; `hu017-unified-flow.spec.js`, ausencia de selector de modos. |
| 02 | Selección/revisión no ejecutan `/start` ni `/rasterize`; un único POST `/runs`, E2E unificado. |
| 03 | `unit/optimization/test_run_geometry.py`, `test_visual_facts.py`: bases previas, validación, snapshot y búsqueda lazy compartida FF/BF/WF. |
| 04 | Configuración inmutable y resolución única; `test_run_geometry.py`, `api/optimization/test_run_geometry_api.py`, API V2 y `VisualState.test.jsx`. |
| 05 | Presupuestos exactos/+1 y error técnico; suites de geometría/carga existentes y `test_visual_store.py`; no ajuste silencioso de resolución. |
| 06 | `piece_ready` conserva base real; API de ventana y loading/éxito de `RunVisualization.test.jsx`. |
| 07 | Identidad pedido/pieza/unidad en eventos y panel; `test_visual_facts.py`, `VisualState.test.jsx`, E2E multipedido. |
| 08 | Solo evaluaciones reales, ordinal y leyenda de muestreo; pruebas de sampler/laziness y E2E giro a 90°. |
| 09 | Ganador antes de colocación, identidad física/ángulo coherentes; API V2 y rechazo de discrepancias en `VisualState.test.jsx`. |
| 10 | `piece_unplaced` por NO_FIT, lista canónica; API parcial, E2E SIN_SOLUCION y prueba V2 de fallo técnico separado. |
| 11 | 24 casos FF/BF/WF con/sin observador iguales; pausa/ocultar no reinician cálculo, `RunVisualization.test.jsx`. |
| 12 | Desconexión persiste FALLIDA/diagnóstico sin stock; API V2 y suites de streaming; E2E recuperación sin POST. |
| 13 | Sampler 150+128/10 adicionales por segundo, referencias sin bits por evento, lector 64 KiB y JSON acotado; store/API/contrato/consumidor lento. |
| 14 | Igualdad observada/no observada más regresiones deterministas FF/BF/WF y TA-021; tres hashes medidos idénticos. |
| 15 | `test_first_fit.py`, `test_rotation.py`, `test_run_geometry.py`, `test_visual_facts.py`: salida temprana y ángulos no utilizados no generados. |
| 16 | `test_worst_fit.py`, `integration/optimization/test_worst_fit_slice.py` y observación sobre los ocho casos: retazos, score y desempates conservados. |
| 17 | Componentes/estado visual reutilizables, rótulo del método recibido e instrumentación común BF. Se conserva la condición de la SPEC: HTTP/persistencia BF no existen aún y no se habilitan aquí; V1/V2 públicos siguen FF. |
| 18 | Suites de rotación, FF/BF/WF, métricas y confirmación; igualdad de resultados completos con margen/separación de los casos TA-021. |
| 19 | Material/espesor e identidad física en snapshots, eventos y resultado; API real, E2E multimaterial/multiunidad/retazo. |
| 20 | Resultado canónico, 2D/3D/raster, método, faltantes y métricas/residuales; `OptimizationVisualizations.test.jsx` y E2E completos/parciales. |
| 21 | API V2/stream lento y E2E comparan cantidades y movimientos antes/después de simular; cero consumo/reserva de inventario. |
| 22 | V2 no habilita confirmar hasta GET; `VisualState.test.jsx`, API/transacciones de confirmación y E2E con diálogo/RBAC/conflicto. |
| 23 | V1 predeterminado y contratos estrictos conservados, HU-015 técnico fuera del build principal; API y E2E HU-015/V1/S1-01. |
| 24 | Loading/vacío/error/410/reintento, abortos obsoletos y pausa local en componentes; E2E 360/768/1440, teclado/foco y movimiento reducido. |
| 25 | E2E reales unificados, parcial, recuperación sin recalcular y stock intacto; regresión de confirmación explícita. |
| 26 | Ventanas de bits reales del cache, contorno original/orientado y resolución aceptada; validación de referencias/contexto, rechazo tardío y E2E máscara ganadora a 90° después de recuperar. |

## Estado y límites del cierre

T01–T06 tienen implementación y evidencia local; el cierre técnico se registra
solo después de las comprobaciones finales indicadas arriba. Los 26 textos CA
y la estimación aprobada 10 SP / 60 h se conservan. No se presenta BF/WF HTTP,
selección de ganador, replay o persistencia permanente de máscaras como trabajo
realizado. La comprobación raster es conservadora; el GAP vectorial independiente
sigue separado y no se introduce una garantía geométrica nueva.

La entrega queda preparada para la revisión humana e integración que el
solicitante habilite después. Este registro no cambia el estado remoto del
backlog, no acredita merge/CI remoto/staging y no sustituye esa revisión cruzada.

Seguimiento PR #81: la matriz anterior conserva la evidencia histórica local.
La regresión posterior de CA-21/22/23/24/25/26 y de TA-037/S1 se detalla en
[la evidencia del ajuste E2E](pr81-regresion-e2e.md). Los seis skips históricos
HU-015 de la ejecución equivalente a CI se reportan como omitidos, no como PASS.
SPEC Implemented/PLAN Approved: CI verde, revisión cruzada y merge pendientes.

Actualización 28/10: el arreglo autorizado del observador Dashboard deja la
suite completa local en **108 passed / 0 failed / 6 skipped** con dos workers.
Se conserva la ejecución previa 107/1/6 y se documentan referencia `a8c3b38`,
prueba negativa/positiva, calidad y límites de la base en
[el seguimiento definitivo del PR #81](pr81-regresion-e2e.md#resultado-definitivo-de-esta-corrección).
Los seis HU-015 no cuentan como PASS; sin Verified formal ni merge/CI atribuidos.
