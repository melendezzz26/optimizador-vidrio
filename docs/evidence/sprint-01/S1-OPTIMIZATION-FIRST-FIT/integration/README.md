# Integración Sprint 1 — backend real y Optimization UI

Fecha: **16/10/2026**. SPEC **Reviewed**; PLAN **Approved**.
UI técnicamente lista para revisión y merge normal hacia integration; ese merge
final y la revisión humana siguen pendientes. No se declara Verified.

## Bases, merges y commits

| Concepto | Commit |
|---|---|
| Integration inicial, con RBAC | `c4c5e5cf046a27cc57e9b33a9bd8f8f144b28f8c` |
| Core completo incorporado | `0e9257249e640614c37799bb4bbb38e75f6033a1` |
| UI inicial de Quispe | `4a3c9c1cd244780f8a1d97f1a527cd1fdebcf760` |
| Merge core→integration, publicado | `fe79530ffcd01241fed298a312571a29930c35c8` |
| Merge integration→UI | `dd35bc32b89339a20a196810e2d0c3af446dcbfc` |
| Conexión real, pruebas y preparación reproducible | `5fb7520068f24c8931d1aa61eba6b95f1168bf1f` |
| Caso conjunto CA-28 | `daad72a45b1270b47c2559c4da65f488183fd584` |
| Diferenciación de conflictos de estado/stock | `c5baa8aff7e932ca4c33a0477f4d16f7a04b362d` |

`c5baa8a` identifica el código auditado; el commit documental posterior añade
evidencia y avance del PLAN. El HEAD documental/remoto definitivo se registra
en el informe final de la sesión. Destino de publicación UI:
`origin/feature/S1-optimization-ui`, sin force-push.

Ambos merges usaron `--no-ff` y no tuvieron conflictos. Se preservan los commits
del core, RBAC y el trabajo visual de Quispe. No se hace merge UI→integration,
PR ni modificaciones en main. [Auditoría de ramas y Alembic](branch-audit.md).

Head Alembic antes de incorporar core: **s1rbac01a2b3**.
Head única posterior: **s1opt02b4c6d**, cuyo down_revision es s1rbac01a2b3.
No se crea una migración. `backend/app` y `backend/alembic` en UI son idénticos
a integration después del merge del core.

## Conexión productiva

- `POST /api/optimization/runs`: selección explícita `{order_ids: [...]}`,
  respuesta **201**, NDJSON real sobre `Response.body`. Preparar solo lee los
  detalles de los pedidos; no llama a `/start`, no reserva stock ni inicia un
  subconjunto. El backend acepta el lote en su transacción.
- `GET /api/optimization/runs/{id}`: resultado durable, recuperación por ID y
  consulta disponible con `optimization.view`. La UI conserva el ID de
  `Location` incluso si falla el stream antes del primer envelope válido.
- `POST /api/optimization/runs/{id}/confirm`: **sin body**, permiso dinámico
  `optimization.confirm`. Tras 200 se consulta el resultado canónico, se muestran
  confirmed=true/confirmable=false y se actualizan los pedidos disponibles.
- Un 409 nunca reintenta ni ejecuta FF automáticamente. Se distinguen
  STOCK_CONFLICT, STATE_CONFLICT y ALREADY_CONFIRMED. La confirmación repetida
  queda deshabilitada hasta revisar el resultado o cambiar la selección.
- Estado/progreso proceden de los ocho eventos T1 y del GET. No se usa replay
  temporizado ni fixtures como fuente productiva. Los fixtures permanecen para
  unit/component tests. `stage_changed` no es una dependencia del backend.
- Se preservan Decimal como strings, índices desde 1, fuentes PLANCHA/RETAZO,
  identidad `source:id:stock_unit_index`, métricas en sus unidades y nullabilidad.
  Los contornos orientados se trasladan; no se vuelven a rotar. 2D, 3D, zoom,
  interacción e inspector raster permanecen. Las etiquetas de piezas pequeñas
  ajustan su tamaño sin modificar geometría.
- SIN_SOLUCION conserva diagnóstico y nunca permite confirmar. FALLIDA conserva
  un mensaje seguro después de consultar el resultado; UI no cambia estados de
  pedidos ni inventa reconciliación.

[OpenAPI capturado del servidor real](openapi-optimization.json) y
[archivos de implementación](implementation-files.txt).

## Pruebas ejecutadas

| Verificación | Resultado exacto | Log |
|---|---|---|
| Core previo al merge: Optimization/HU-015/Inventory/Orders/RBAC | 892 passed, 1 warning | [core-premerge](logs/core-premerge.log) |
| Backend completo post-merge integration | 1976 passed, 1 warning | [backend-postmerge](logs/backend-postmerge.log) |
| Backend completo de cierre | **1976 passed**, 0 failed, 0 skipped, 1 warning; 273.20s | [backend-final](logs/backend-final.log) |
| Frontend unit | **159 passed**, 0 failed/skipped | [unit](logs/frontend-unit.log) |
| Frontend component | **446 passed**, 38 archivos | [component](logs/frontend-component.log) |
| Lint | Exit 0, sin errores/advertencias ESLint | [lint](logs/frontend-lint.log) |
| Build Vite | Exit 0 | [build](logs/frontend-build.log) |
| E2E general, 86 instancias desktop/mobile | **85 passed / 1 skipped / 0 failed** | [E2E completo](logs/e2e-full.log) |
| Revalidación de Optimization + HU-015 | 24 passed | [focalizada](logs/e2e-optimization-hu015.log) |
| Navegación Orders/Inventory y evidencias de stock/conflicto | 6 passed | [stock/navegación](logs/e2e-stock-navigation.log) |
| Tras el último ajuste de feedback: N=1, conflicto y RBAC | 6 passed | [revalidación final](logs/e2e-final-conflict-rbac.log) |

Las revalidaciones se solapan; no se suman como escenarios únicos. La suite
completa E2E corresponde a daad72a; el cambio posterior es únicamente el texto
STATE_CONFLICT y su test. Después pasan unit/component/lint/build y seis E2E
reales pertinentes sobre el árbol c5baa8a. Backend y First Fit no cambian.

La única omisión E2E ya existía: HU-014 no repite la baja destructiva de la misma
plancha en móvil después de agotarla en desktop. Su ejecución desktop pasa;
la consulta sin gestión pasa en ambos viewports. Optimization y HU-015 no omiten
ningún caso. Se conserva la cobertura, no se desactiva un fallo nuevo.

La regresión Dashboard incluye dos instancias del test histórico **CONTROLLED
FAILURE SCENARIO — NOT REAL BACKEND FAILURE**, que inyecta un 500 para verificar
el error parcial. No se presenta como un fallo real. Los E2E nuevos de
Optimization y los HU-015 reales no utilizan `route.fulfill` ni respuestas de
red fixture. Sus datos sintéticos se persisten en PostgreSQL y se consumen
mediante FastAPI y Vite reales.

Subconjuntos del backend completo, **no aditivos**: Optimization 516,
Inventory 497, Orders 150, RBAC API 95, HU-015 API 41 y start/concurrencia
histórico 7. El warning es la deprecación Starlette TestClient/httpx existente.
[Resumen estructurado y conteos por archivo/viewport](test-summary.json).

## Matriz real de Optimization

Cada fila se ejecuta en desktop y móvil. Hay **20 passed** de Optimization.
Las diez pruebas de guardado Orders/Clients pasan: el 422 histórico no se
reproduce. No se modifica Orders ni se atribuye una corrección sin identificarla.

| Caso | Comprobación |
|---|---|
| E2E1 — N=1 | Login, selección, POST único, NDJSON, placements, métricas, GET y confirmación; cantidad 1→0, pedido CONFIRMADO; segunda confirmación 409 sin consumo. Las pantallas Orders e Inventory muestran Confirmado, saldo 0, Inactivo e historial CONSUMO_OPTIMIZACION. |
| E2E2 — multipedido | Dos pedidos en una corrida; placements de ambos y confirmación de todos. |
| E2E3 — multimaterial | Dos parejas tipo/espesor, layouts separados y métricas canónicas. |
| E2E4 — unidades físicas | Tres piezas usan dos unidades de una misma fila; layouts independientes en 2D/3D, zoom y control de giro de cámara; cantidad 4→2. |
| E2E5 — retazo primero | Dos piezas en un retazo compatible; se consume una vez; la plancha permanece disponible. |
| E2E6 — SIN_SOLUCION | 1/2 unidades colocadas, diagnóstico visible, pedidos PENDIENTE, stock idéntico, sin confirmación. |
| E2E7 — 409 | PATCH real cambia stock antes de confirmar; revalidación rechaza, movimientos vacíos, pedidos OPTIMIZADO y stock sin otra mutación. |
| E2E8 — RBAC | Sin view no hay acceso; view consulta sin ejecutar; execute no confirma; confirm confirma con su propio usuario. Backend rechaza acciones no autorizadas con 403. |
| E2E9 — orientación | Pieza 70×40 en plancha 40×70 a 90.00°; geometría recibida 40×70, sin segunda rotación; 2D/3D y confirmación real. |
| E2E10 — CA-28 conjunto | Dos pedidos, dos grupos, cantidad 2 por pieza del primer material: seis unidades sobre tres unidades físicas; patrón trazable y confirmación conjunta; saldos finales 0 y 0. |

Los `E2E*-stream.ndjson` son respuestas HTTP capturadas. Se verifican envelope,
sequence continua, progreso y Decimal; además se fragmentan sus bytes cada siete
posiciones para validar el parser. Esta validación secundaria no alimenta la UI.
El adapter productivo procesa los chunks reales al recibirlos. Los
`E2E*-browser-errors.json` quedan vacíos.

## Ejemplo inspeccionable y trazabilidad

En E2E4, para una plancha 100×50 y tres piezas 50×50:

| Unidad de pieza | Unidad física de plancha | x_mm | y_mm |
|---|---|---|---|
| 1 | 1 | 0.000 | 0.000 |
| 2 | 1 | 50.000 | 0.000 |
| 3 | 2 | 0.000 | 0.000 |

La fila tiene cantidad 4 antes y 2 después. Un movimiento registra
cantidad_afectada=2 y `stock_unit_index=1,2`; nunca se descuentan tres placements.
Ver [resultado](chromium-desktop/E2E4-result.json),
[antes](chromium-desktop/E2E4-stock-before.json),
[después](chromium-desktop/E2E4-stock-after.json) y
[movimientos](chromium-desktop/E2E4-movements.json).

Cada caso guarda su GET previo, NDJSON, confirmación, GET confirmado, stock y
estados de pedidos cuando aplican. E2E6 conserva igualdad de stock; E2E7 guarda
stock inmediatamente antes/después del intento 409 y movimientos vacíos.
Las ejecuciones focalizadas crean nuevas bases temporales; los IDs pueden
repetirse entre casos/ejecuciones. Correlación, sequence e IDs se verifican dentro
de cada conjunto de archivos, no entre bases independientes.

## Capturas y HU-015

Se conservan **55 capturas reales representativas**, obtenidas con Chromium.
Los scripts pueden generar otras capturas repetidas de los mismos diálogos;
se retienen las que aportan evidencia.

- [Selección](chromium-desktop/E2E1-selection.png),
  [progreso final](chromium-desktop/E2E1-progress-final.png),
  [placements 2D](chromium-desktop/E2E1-placements.png),
  [métricas](chromium-desktop/E2E1-metrics.png).
- [Unidad física 2 en 3D](chromium-desktop/E2E4-3d-unit2.png),
  [confirmación](chromium-desktop/E2E1-confirmation.png),
  [confirmado](chromium-desktop/E2E1-confirmed.png).
- [Pedido en Orders](chromium-desktop/E2E1-orders-confirmed.png),
  [saldo en Inventory](chromium-desktop/E2E1-inventory-updated.png),
  [movimiento](chromium-desktop/E2E1-inventory-movement.png).
- [SIN_SOLUCION](chromium-desktop/E2E6-sin-solucion.png),
  [conflicto 409](chromium-desktop/E2E7-409.png),
  [consulta con view solamente](chromium-desktop/E2E8-view-only.png),
  [caso conjunto](chromium-desktop/E2E10-confirmed.png).
- [Raster HU-015](chromium-desktop/HU-015-raster-rectangle.png),
  [círculo](chromium-desktop/HU-015-raster-circle.png),
  [polígono](chromium-desktop/HU-015-raster-polygon.png) y
  [raster móvil](chromium-mobile/HU-015-raster-rectangle.png).

La captura de progreso corresponde al estado final; no se fabrica una imagen de
un estado intermedio que no se haya capturado. El NDJSON conserva los eventos
intermedios reales. HU-015 mantiene su secuencia PENDIENTE→start→EN_OPTIMIZACION→
rasterize, geometría/máscara, errores de recursos, recuperación y los tres tipos
geométricos: **6 E2E passed**, además de API/component. No requiere First Fit.

## Reproducción

Entorno observado: Python 3.11, PostgreSQL **17.11** local, FastAPI real en 8017,
Vite real en 5173 y Chromium. `E2E*-runtime.json` registra versión y head reales.
No se usa Supabase, ni DATABASE_URL compartida. `tests.e2e_server` crea un clúster
loopback propio, migra, carga cuentas sintéticas y detiene PostgreSQL al terminar.

Activar el virtualenv backend e indicar los binarios PostgreSQL instalados. En
este Cloud se utilizó `source /workspace/.setup/runtime.sh`; su equivalente es
activar `backend/.venv`, definir NEWGLASS_TEST_PG_BIN y, cuando corresponda, las
bibliotecas PostgreSQL mediante LD_LIBRARY_PATH.

Desde backend:

```bash
NEWGLASS_REQUIRE_POSTGRES=1 pytest -q --junitxml=/tmp/newglass-backend.xml
alembic heads
```

Desde frontend:

```bash
npm run test:unit
npm run test:component
npm run lint
npm run build
```

Desde la raíz, con el mismo Python activo:

```bash
NEWGLASS_E2E_CHROMIUM_EXECUTABLE=/usr/bin/chromium bash docs/evidence/sprint-01/S1-OPTIMIZATION-FIRST-FIT/integration/run-e2e.sh --workers=2
```

El script exporta únicamente credenciales sintéticas del servidor temporal.
En un equipo con Chrome instalado puede omitirse la variable del ejecutable.
También admite filtros de Playwright, por ejemplo `s1-optimization-ui.spec.js`
o `hu015-rasterization.spec.js`. Se probó el script/config versionado con la
regresión completa y las revalidaciones focalizadas.

## Criterios, límites y próximo paso

La matriz avanza CA-01–05, CA-12–17, CA-19–24 y CA-26–28 en integración real.
CA-06–11/18 y la concurrencia/rollback de CA-20/23/25 conservan la regresión
backend completa. Esto aporta evidencia; no cambia el estado de la SPEC.

No quedan discrepancias funcionales de nombres, Decimal, índices, eventos,
estados o confirmación entre UI y T1. Dos límites permanecen explícitos:

1. T1 FF expone contornos/resolución, no máscaras RLE; no se inventa una fuente
   para el inspector. Raster real continúa en HU-015 con sus precondiciones.
2. La reconciliación administrativa y la política independiente de área mínima
   residual siguen fuera de este bloque. El backend solo usa geometría residual
   válida y mínimos de ancho/alto vigentes; no se modifica esa política.

Recomendación: revisar los commits UI y estas capturas; hacer fetch y comprobar
que integration sigue en fe79530 o auditar cualquier avance. Con una única head
Alembic y regresión compatible, integrar **origin/feature/S1-optimization-ui →
integration/sprint-01 mediante merge normal --no-ff**, preservando ambos padres.
No se realiza ese merge en esta sesión. Mantener SPEC Reviewed/PLAN Approved
hasta integración final y revisión humana.
