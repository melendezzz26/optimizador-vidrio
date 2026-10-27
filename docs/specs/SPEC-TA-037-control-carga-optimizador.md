# SPEC-TA-037 — Control de carga del optimizador

## Información general

| Campo | Valor |
|---|---|
| ID | TA-037 |
| Nombre | Control de carga del optimizador |
| Sprint | Sprint 2 |
| Tipo / épica | Habilitador / Optimización segura |
| Versión | **1.3**: saneamiento del ciclo de vida de plazas de T03; presupuestos y contratos de v1.2 conservados |
| Estado | **Implemented** — T01–T04 validadas técnicamente; pendiente de CI y revisión del PR de saneamiento para Verified. |
| Responsable | Fabricio Aguilar |
| Saneamiento T03 | Fabricio Melendez Quezada con asistencia de Codex; trabajo original T01–T04 de Fabricio Aguilar |
| Revisor del cierre | Pendiente de revisión del PR; no se atribuye una aprobación humana |
| Fecha | 26/10/2026 |
| Rama | `fix/TA-037-admission-lifecycle`, desde `integration/sprint-01` en `445886a` |
| Origen | Auditoría pre-Sprint 2, hallazgo **S1-02** (BLOCKER) y propuesta EN-S2-02 |
| Dependencias | HU-015 como baseline; TA-037 T01 → T02 → T03/T04. TA-021 es un consumidor coordinado, no un prerrequisito para cerrar TA-037. |
| Coordina con | TA-016, TA-018, TA-019, TA-021, HU-017, TA-038 |
| PLAN técnico | [PLAN-TA-037-control-carga-optimizador.md](PLAN-TA-037-control-carga-optimizador.md) |
| Evidencia | [docs/evidence/sprint-02/TA-037](../evidence/sprint-02/TA-037/README.md) |

Este documento nació en **TA-037 T01: definir el presupuesto y el contrato de
errores** y actualmente cubre T01–T04 y el saneamiento de T03. Fija los límites
técnicos, su validación y la respuesta al exceder el presupuesto. Los
valores de §5 fueron aprobados por el equipo el 26/10/2026. T02 implementa los
límites de tamaño (L-01, L-03, L-04, L-05, L-07, L-13); T03 y T04 completan el resto.

**Cambio en v1.1.** La v1.0 se midió con el paso angular de 90° (4 orientaciones por
pieza), que era la configuración vigente al 25/10/2026. El PR #64 fijó el paso
operativo en **5°** (72 orientaciones). Con esa configuración, el costo del cálculo se
multiplica y aparece un fallo nuevo en la caché raster. El diseño no cambia (puntos de
validación, contrato de error, sin mutación); solo se recalibran los valores de §5.

## 1. Objetivo

Impedir que una sola solicitud válida, o varias simultáneas, agoten la CPU o la
memoria del monolito durante la optimización. Para eso, las solicitudes que
exceden el presupuesto se rechazan **antes** de expandir cantidades, candidatos de
stock o estructuras geométricas costosas.

TA-037 no cambia reglas comerciales. Tampoco modifica la lógica de First Fit, Best
Fit ni Worst Fit, ni la confirmación transaccional.

## 2. Alcance

### Incluye

- Límites operativos para pedidos, unidades, geometría, memoria raster, stock
  compatible, memoria interna de layouts, concurrencia y tiempo de cálculo.
- Separación explícita entre validación de negocio y límite operativo (§4).
- Punto de validación de cada límite en el flujo actual (§6).
- Contrato de error HTTP y mensaje para el frontend (§7).
- Criterios de aceptación de T02, T03 y T04 (§9).

### Fuera de alcance

- Cambiar el recorrido, el orden de candidatos o la salida temprana del motor
  (`packing.py`, `first_fit.py`, `best_fit.py`, `worst_fit.py`, `placement.py`,
  `rotation.py`).
- Cambiar el paso angular de 5°, el presupuesto de la caché raster o el de los
  layouts: son decisiones de TA-016 / HU-017 (GAP-05).
- Cambiar la confirmación (`confirmation.py`, `confirmation_adapter.py`).
- Optimizar el rendimiento del motor. Los hallazgos de §11 se derivan a tareas
  posteriores.
- Recuperar pedidos o ejecuciones tras un fallo: corresponde a **TA-038**.
- Límites de creación de pedidos o de inventario. Son del módulo Orders o
  Inventory y se coordinan con sus responsables (GAP-02).
- Parametrizar los límites desde la interfaz o la tabla `configuraciones`, porque
  requeriría una migración y una API nueva.

## 3. Situación inicial auditada (evidencia histórica)

Revisión del código de `integration/sprint-01` en `b7b9caa` (después del PR #64):

| # | Hallazgo | Ubicación |
|---|---|---|
| H-01 | `cantidad` acepta hasta 2 147 483 647 por pieza; no hay máximo de piezas por pedido. | `orders/presentation/schemas.py:8,21-36` |
| H-02 | `AcceptRun` expande todas las unidades (`prepare_persisted_problem`) **antes** de cualquier control de tamaño, y luego revisa la geometría una vez por **unidad**, no por pieza. | `optimization/application/runs.py` (bloque `try` posterior a `lock_pending`); `domain/preparation.py:43-49` |
| H-03 | La lista de pedidos de una ejecución no tiene máximo. | `presentation/run_schemas.py:34-41`; `application/runs.py` (validación de ids) |
| H-04 | El stock se expande en una unidad física por cada `cantidad` de plancha, sin tope, y ocurre **después** de aceptar la ejecución: los pedidos ya están en `EN_OPTIMIZACION`. | `infrastructure/stock_adapter.py:41-49`; `application/calculation.py:23` |
| H-05 | Si se supera el presupuesto interno de layouts (128 MiB), la ejecución falla **tarde**, después de empezar el cálculo, como `CALCULATION_FAILED`. | `domain/packing.py:136-141` |
| H-06 | Cada ejecución crea un hilo propio, sin límite de ejecuciones simultáneas. | `presentation/run_stream.py:126-127`; `run_routes.py:66-73` |
| H-07 | La cancelación cooperativa existe solo en los hitos del motor, y no hay presupuesto de tiempo. | `presentation/run_stream.py:69-73,146-149` |
| H-08 | El despliegue corre **un** proceso uvicorn. | `Procfile` |
| H-09 | **Nuevo en v1.1.** El paso angular operativo es fijo en 5°: `AcceptRun` rechaza otra configuración con `CONFIG_CONFLICT`. Cada pieza se rasteriza en hasta 72 orientaciones. | `domain/problem.py` (`SPRINT_2_ANGULAR_STEP_DEG`); `application/runs.py` |
| H-10 | **Nuevo en v1.1.** La caché raster interna (64 MiB) guarda las 72 orientaciones de cada geometría distinta. Con 3 piezas distintas de unos 1300 × 1000 mm ya se supera, y la ejecución falla **tarde**. | `domain/rotation.py` (`RasterCache._raster`, `orientations`) |

Límites que ya existen y se conservan: geometría interna (4000 mm, 4000 celdas por
eje, 16 000 000 celdas), 128 vértices, caché raster de 64 MiB, layouts de 128 MiB y
10 000 orientaciones (`domain/rotation.py`). Estos límites protegen **por objeto**;
ninguno acota el costo acumulado de la solicitud.

### Mediciones

Mediciones con `experiments/raster/scripts/ta037_load_benchmark.py`, solo con el
motor de dominio, a 1 mm (resolución vigente del seed) y planchas de
2440 × 1830 mm. Máquina de referencia: 2 vCPU Intel Xeon a 2,1 GHz, Python 3.11.
Los resultados completos están en la evidencia.

**A 5° (configuración vigente, base de los valores de v1.1):**

| Escenario | Tiempo | Lectura |
|---|---:|---|
| FF de 100 / 150 / 200 rectángulos de 300 × 200 | 1,2 / 3,4 / 7,1 s | 200 unidades: 14 veces más que a 90° |
| FF de 100 / 150 polígonos de 128 vértices | 10,2 / 22,4 s | Las formas no rectangulares son las más caras |
| FF de 200 polígonos de 8 vértices | 50,0 s | El costo depende de la forma, no del número de vértices |
| FF de 200 circunferencias | 4,8 s | Una sola orientación |
| 2 / 3 piezas distintas de ~1300 × 1000 | 1,2 s / falla a los 1,5 s | Caché raster de 64 MiB superada (H-10) |
| Unidad sin encaje × plancha (margen 500 mm) | ~0,62 s por par (5 × 10 = 30,9 s) | 64 veces más que a 90° |

**A 90° (v1.0, histórico):** 500 rectángulos en 3,3 s; ~9,5 ms por par sin encaje;
más de ~49 planchas usadas superan los 128 MiB de layouts; 3 ejecuciones simultáneas
tardan 10,9 s cada una frente a 3,3 s sola (el GIL serializa el cálculo). Estos dos
últimos hallazgos no dependen del paso angular y siguen vigentes.

## 4. Validación de negocio frente a límite operativo

| Tipo | Qué decide | Dónde vive | Ejemplos | ¿Lo cambia TA-037? |
|---|---|---|---|---|
| **Validación de negocio** | Si el dato es correcto para el negocio | Orders, Inventory, Clients | `cantidad > 0`, polígono convexo, material existente, pedido `PENDIENTE`, dimensiones positivas | **No** |
| **Límite operativo** | Si el servidor puede calcular **esta** solicitud con seguridad | `optimization/application` | Unidades por ejecución, stock por material, ejecuciones simultáneas | **Sí, lo define** |

Consecuencias:

1. Un rechazo operativo **no** invalida el pedido: sigue `PENDIENTE`, editable y
   optimizable en un lote más pequeño.
2. El mensaje dice que es un límite del cálculo, no un error del pedido.
3. Ningún límite operativo se valida en un componente React. El frontend solo
   muestra la respuesta del backend.
4. Una pieza que **por sí sola** supera un límite (por ejemplo, cantidad 200 o 140
   vértices) nunca podrá optimizarse en ningún lote. El mensaje lo dice e indica
   que hay que editar el pedido.

## 5. Presupuesto propuesto

Los valores se definen como constantes de la capa Application, igual que
`resource_policy.py`, en un único objeto `RunLoadBudget`. Cambiarlos exige un PR con
la medición que lo justifique. No requieren migración.

**Objetivo de diseño:** que el peor caso **medido** de una solicitud aceptada quede
en unos 30 s en la máquina de referencia, de modo que en un dyno más lento siga por
debajo de L-12.

| ID | Límite | Valor v1.1 | Valor v1.0 | Unidad | Base de la decisión |
|---|---|---:|---:|---|---|
| L-01 | Pedidos por ejecución | **20** | 20 | pedidos | Sin cambio. Acota `IN (...)` y los bloqueos `FOR UPDATE`. |
| L-02 | Líneas de pieza por ejecución | **Retirado** | 200 | — | Cada línea tiene `cantidad ≥ 1`, así que L-03 ya acota las líneas. |
| L-03 | Unidades por ejecución (Σ `cantidad`) | **150** | 500 | unidades | A 5°: 150 rectángulos 3,4 s; 150 polígonos 22,4 s. Con 200 polígonos se llega a 50 s. |
| L-04 | Vértices por pieza | **128** | 128 | vértices | Sin cambio. Es el límite interno de `RasterCache`; se adelanta a antes de expandir. |
| L-05 | Extensión geométrica por pieza | **4000 mm; 4000 celdas por eje; 16 000 000 celdas** | igual | — | Sin cambio. Ya existe en `RasterCache.check_geometry`; se aplica **una vez por pieza**, no por unidad. |
| L-06 | Unidades × orientaciones | **Retirado** | 2000 | — | El paso es fijo en 5° (H-09) y L-03 ya está medido a 5°. El costo no crece en proporción a las orientaciones, así que la fórmula de v1.0 rechazaba de más. |
| L-07 | Stock físico compatible por material (Σ `planchas.cantidad` activas + retazos activos) | **50** | 100 | unidades físicas | Con ~0,62 s por par sin encaje, una unidad que no encaja tarda hasta ~31 s **entre dos hitos** del motor. Es el tiempo máximo en que L-12 no puede actuar. |
| L-08 | Unidades × stock por material | **Retirado** | 5000 | — | A 5°, cualquier tope útil de pares sería demasiado restrictivo. El peor caso total lo acota L-12, y L-07 acota el tramo entre hitos. |
| L-09 | Memoria de layouts por ejecución | **Retirado en v1.2** | 128 MiB | — | No existe una cota inferior segura: cuántas planchas se usan depende de qué piezas encajan, y eso solo se sabe ejecutando el motor. Un rechazo previo podría bloquear pedidos válidos. El presupuesto interno de 128 MiB del motor se mantiene como fallo tardío (GAP-04), acotado por L-03 y L-07. |
| L-10 | Ejecuciones activas por proceso | **2** | 2 | ejecuciones | Sin cambio. A 5° cada ejecución es más larga, así que el límite importa más. |
| L-11 | Ejecuciones activas por usuario | **1** | 1 | ejecuciones | Sin cambio. |
| L-12 | Tiempo máximo de cálculo | **120 s** | 120 s | s | Pasa de respaldo a protección **principal** del peor caso de stock (reemplaza a L-08). Se verifica en los hitos del motor (T03). |
| L-13 | Memoria raster estimada por ejecución | **64 MiB** (existente) | — | bytes estimados | **Nuevo.** Convierte el fallo tardío H-10 en un rechazo temprano, con la misma fórmula que usa el motor (§5.1). |

### 5.1 Reglas de cálculo

- **L-03:** suma de `cantidad` de las filas leídas, **sin crear unidades**.
- **L-07:** se calcula por grupo de material (`id_tipo_vidrio`, `espesor_mm`) con
  las mismas reglas de compatibilidad de `InventoryStockAdapter`: activas, con
  `cantidad > 0` y del mismo material. Se cuentan filas y se suman cantidades sin
  crear `StockCandidate`.
- **L-13:** para cada **geometría distinta** de las piezas seleccionadas (la misma
  huella con la que `RasterCache` comparte máscaras), se recorren los ángulos de
  `discrete_angles(paso)` (solo 0° para circunferencias). Para cada ángulo se calcula
  el ancho y alto de la figura rotada, sin rasterizar, y su rejilla **redondeada hacia
  abajo** (`floor` en vez de `ceil`); los ángulos que podrían exceder la extensión
  interna aportan 0. La estimación por orientación es la misma fórmula de
  `RasterCache._raster`: `filas × (32 + 4 × ceil(columnas / 30) + 8) + 4096 + 512 × vértices`.
  Si la suma supera 64 MiB, se rechaza. Es una **cota inferior**: no incluye el stock
  y redondea hacia abajo, así que solo rechaza lo que el motor seguro rechazaría. Una
  prueba la compara con la caché real del motor (queda entre el 90 % y el 100 %). Se
  usa el cálculo en coma flotante porque el exacto (`oriented_geometry`) tardaría hasta
  ~108 ms por pieza distinta de 128 vértices con los pedidos bloqueados. Se verificó
  con el caso de H-10: 2 piezas distintas (~48,8 MiB) pasan y 3 (~73 MiB) fallan.
- **L-10 y L-11:** cuentan ejecuciones con hilo de cálculo vivo **en este
  proceso**. La plaza se libera cuando termina el hilo, no cuando se cierra la
  conexión del cliente. La regla es válida mientras haya un solo proceso
  (H-08); con más dynos o workers se necesitaría una admisión compartida en base de
  datos, y esa decisión requiere un ADR. La plaza se toma antes de aceptar la ejecución
  y se libera una sola vez: al terminar el hilo de cálculo (éxito, fallo, desconexión o
  L-12), al rechazarse la solicitud antes del stream, o al cerrarse un stream cuyo hilo
  nunca arrancó. **La antigüedad de la plaza no permite liberarla:** la entrega de
  eventos puede durar más de 300 s y está excluida de L-12. Una conexión lenta,
  un abandono o el fin de la espera de limpieza no hacen disponible una plaza
  mientras el trabajador siga vivo. Si se sospecha una fuga, no se recupera
  capacidad por reloj sin demostrar que su propietario terminó; un reinicio del
  proceso elimina también sus trabajadores. Se prueban los límites global y por
  usuario con reloj simulado por encima de 300 s, contrapresión y liberación real.
- **L-12:** se mide desde que arranca el hilo de cálculo, descontando el tiempo de
  entrega de eventos al cliente, para que un cliente lento no consuma el presupuesto. Se
  verifica en cada hito (`group_started`, `piece_started`, `piece_placed`,
  `group_completed`): el primer hito posterior al vencimiento detiene la ejecución.
- Si una solicitud viola varios límites, se informa **solo el primero** en el orden
  de §6. Así el resultado es determinista y fácil de probar.

## 6. Dónde se valida cada límite

Regla general: cada límite se valida en el **último punto donde todavía es barato**,
antes de la primera estructura proporcional a lo que limita.

| Orden | Punto | Archivo y momento | Límites | Qué existe en ese momento | Qué todavía **no** existe |
|---|---|---|---|---|---|
| P1 | Antes de abrir la transacción | `application/runs.py`, `AcceptRun.execute`, después de la validación de ids | L-01 | Solo la lista de ids | Bloqueos, lecturas |
| P2 | Admisión | `presentation/run_routes.py`, `start_run`, **antes** de `AcceptRun`, mediante un puerto de admisión | L-10, L-11 | Usuario autenticado | Transacción, ejecución |
| P3 | Con los pedidos bloqueados | `application/runs.py`, inmediatamente después de `uow.orders.lock_pending(ids)` y **antes** de `prepare_persisted_problem` | L-03, L-04, L-05 (por fila), L-13 | Filas de `piezas` y configuración | Unidades expandidas, máscaras |
| P4 | Stock, durante la aceptación | `application/runs.py`, después de P3 y **antes** de `uow.runs.create`; usa el puerto `count_compatible` del mismo adaptador de stock del cálculo, que cuenta filas sin expandir | L-07 | Conteos por material | `StockCandidate`, layouts |
| P5 | Defensa en el cálculo | `infrastructure/stock_adapter.py`, `list_compatible`, antes del bucle de expansión | L-07 | Filas de inventario | Unidades físicas |
| P6 | Durante el cálculo | `presentation/run_stream.py`, callback `milestone` | L-12 | Ejecución en curso | — |

El paso angular de 5° se sigue validando donde lo dejó el PR #64, antes de P3.
TA-037 no lo cambia.

Notas de diseño:

- **P3 y P4 ocurren dentro de la aceptación** que ya abre `AcceptRun`. P4 lee el
  inventario con una lectura de solo lectura del adaptador de stock. Un rechazo
  lanza `RunError` antes de `runs.create` y de `orders.transition`, así que la
  unidad de trabajo hace rollback: no se crea `optimizaciones`, los pedidos siguen
  `PENDIENTE` y no se lee ni escribe stock para consumo.
- **P4 se adelanta a la aceptación** porque hoy el stock se lee recién en
  `CalculateRun` (H-04), cuando los pedidos ya pasaron a `EN_OPTIMIZACION`. Un
  rechazo en ese punto dejaría una ejecución `FALLIDA` y pedidos atrapados (TA-038).
- **P5 es una red de seguridad.** Cubre el caso de que entre P4 y el cálculo se
  registre más stock. Falla como `CALCULATION_FAILED`, con el motivo en el log del
  servidor, sin cambiar el contrato del stream.
- **P3 no cambia el resultado del motor.** Si la solicitud se acepta, el problema
  preparado es idéntico al actual. P3 solo mueve la verificación de geometría de
  «una vez por unidad» a «una vez por pieza», con la misma función y el mismo error.
  L-13 solo calcula rejillas y no guarda máscaras.

## 7. Contrato de error

### 7.1 Límite de tamaño (L-01, L-03, L-04, L-07, L-13)

`HTTP 422 Unprocessable Content`, sin cuerpo NDJSON. La ejecución no llega a
crearse.

```json
{
  "detail": {
    "code": "LOAD_LIMIT_EXCEEDED",
    "message": "Los pedidos seleccionados suman 180 unidades y el máximo por cálculo es 150. Divide la selección en lotes más pequeños.",
    "limit": {
      "name": "units_per_run",
      "maximum": 150,
      "actual": 180,
      "scope": null
    }
  }
}
```

| Campo | Tipo | Regla |
|---|---|---|
| `code` | string | Siempre `LOAD_LIMIT_EXCEEDED` para los límites de tamaño. |
| `message` | string | En español y apto para mostrar tal cual. No incluye SQL, trazas, nombres de tabla ni rutas. |
| `limit.name` | string | Uno de: `orders_per_run`, `units_per_run`, `vertices_per_piece`, `raster_memory`, `stock_units_per_material`. |
| `limit.maximum` | int | Valor del presupuesto vigente. Para `raster_memory`, en bytes. |
| `limit.actual` | int | Valor medido. Para `raster_memory`, la estimación en bytes. |
| `limit.scope` | object \| null | `{"id_pieza": n}` para L-04; `{"id_tipo_vidrio": n, "espesor_mm": "6.00"}` para L-07; `null` en el resto. |

**L-05 conserva su respuesta actual.** Una pieza que excede la extensión geométrica
interna sigue respondiendo `422 INVALID_INPUT` con el mismo mensaje de siempre («Las
piezas o parámetros exceden las condiciones válidas de cálculo.»), porque T02 usa la
misma función de validación y no debe cambiar respuestas existentes. La diferencia es
que ahora se valida una vez por pieza y antes de expandir.

**Por qué 422:** la solicitud está bien formada, pero no se puede procesar tal como
viene, y reintentarla igual no cambia el resultado. Es coherente con
`INVALID_INPUT`, que ya responde 422. No se usa 413 porque el cuerpo de la
solicitud es pequeño (una lista de ids). No se usa 409 porque no es un conflicto de
estado.

### 7.2 Capacidad ocupada (L-10, L-11)

`HTTP 503 Service Unavailable` con la cabecera `Retry-After: 15`.

```json
{
  "detail": {
    "code": "OPTIMIZER_BUSY",
    "message": "El optimizador está atendiendo otros cálculos. Intenta nuevamente en unos segundos.",
    "limit": { "name": "active_runs", "maximum": 2, "actual": 2, "scope": null }
  }
}
```

Para L-11 se usa `limit.name = "active_runs_per_user"` y el mensaje «Ya tienes un
cálculo en curso. Espera a que termine o revisa su resultado.»

**Por qué 503 y no 429:** el límite protege la capacidad del servidor y no es una
cuota de frecuencia por cliente. `Retry-After` indica que el mismo pedido sí puede
funcionar más tarde, a diferencia de 7.1.

### 7.3 Tiempo de cálculo (L-12)

La ejecución ya fue aceptada y el stream está abierto, así que no puede responder
con otro código HTTP. Termina con el evento `optimization_failed`,
`estado = FALLIDA` y `code = TIME_BUDGET_EXCEEDED`. Agregar este código requiere
actualizar la lista permitida en `frontend/src/features/optimization/runContract.js:117`
y `OptimizationFailedV1`; T03 hace ambos cambios. El mensaje del evento es «El cálculo
superó el tiempo máximo de 120 s y se detuvo. Divide la selección en lotes más
pequeños.». La ejecución queda `FALLIDA`, como en los demás fallos; qué pasa después con
los pedidos lo define TA-038. La presentación específica en pantalla corresponde a T04.

### 7.4 Mensajes por límite

| `limit.name` | Mensaje (las llaves se reemplazan) |
|---|---|
| `orders_per_run` | Seleccionaste {actual} pedidos y el máximo por cálculo es {maximum}. Quita algunos e inténtalo de nuevo. |
| `units_per_run` | Los pedidos seleccionados suman {actual} unidades y el máximo por cálculo es {maximum}. Divide la selección en lotes más pequeños. |
| `vertices_per_piece` | La pieza {id_pieza} tiene {actual} vértices y el máximo admitido es {maximum}. Edita la pieza en su pedido. |
| `raster_memory` | Las piezas seleccionadas tienen demasiadas formas grandes distintas para un solo cálculo. Divide la selección en lotes más pequeños. |
| `stock_units_per_material` | Hay {actual} unidades de stock compatibles para un mismo material y un cálculo admite {maximum}. Solicita al almacenero revisar el inventario activo. |

El backend construye el mensaje y el frontend lo muestra tal cual. T04 agrega la
presentación específica, decidida en `optimizationModel.runErrorFeedback` y no en el
componente:

| Caso | Título | Indicación | Variante |
|---|---|---|---|
| 422 `LOAD_LIMIT_EXCEEDED` | El trabajo es demasiado grande para un solo cálculo | Los pedidos siguen pendientes y no se usó inventario. Ajusta la selección y vuelve a revisar vidrios y piezas. | Error (`role="alert"`) |
| 503 `OPTIMIZER_BUSY` | El optimizador está ocupado | Los pedidos siguen pendientes. Vuelve a presionar «Calcular distribución» en {Retry-After} segundos. | Advertencia (`role="status"`) |
| `TIME_BUDGET_EXCEEDED` | El cálculo superó el tiempo máximo | No se consumió inventario. Consulta el resultado; los pedidos de este trabajo requieren revisión antes de volver a calcularse. | Error |

En los dos primeros casos la ejecución no llegó a crearse: la selección y el resumen se
conservan, no se muestra progreso y «Calcular distribución» sigue disponible. El aviso
recibe el foco. El resto de errores conserva la presentación genérica de siempre.

## 8. Reglas

- **RN-01 — Rechazo temprano.** Ningún límite de §5 se evalúa después de crear la
  estructura proporcional a lo que limita.
- **RN-02 — Sin mutación.** Un rechazo de L-01 a L-11 o de L-13 no crea filas en
  `optimizaciones`, `ejecuciones_optimizacion` ni `optimizacion_pedidos`, no
  cambia el estado de los pedidos y no toca `planchas`, `retazos` ni
  `movimientos_inventario`.
- **RN-03 — Motor intacto.** Las solicitudes dentro del presupuesto producen
  exactamente los mismos placements, eventos, métricas y estados que hoy, con
  First Fit, Best Fit y Worst Fit.
- **RN-04 — Confirmación intacta.** `POST /runs/{id}/confirm` no cambia ni se
  somete a la admisión de L-10 y L-11: confirmar no recalcula.
- **RN-05 — Límites en el backend.** El frontend puede anticipar un aviso, pero la
  decisión es siempre del backend.
- **RN-06 — Sin secretos.** Las respuestas no exponen SQL, trazas, rutas ni datos
  de otros usuarios. El detalle técnico queda en el log del servidor.
- **RN-07 — Determinismo.** Ante la misma solicitud y los mismos datos, se rechaza
  por el mismo límite y con los mismos valores.
- **RN-08 — Fronteras inclusivas.** `actual == maximum` se acepta y
  `actual == maximum + 1` se rechaza.

## 9. Criterios de aceptación

| CA | Tarea | Criterio |
|---|---|---|
| CA-01 | T01 | Esta SPEC documenta los límites vigentes, su punto de validación y su contrato de error, sin cambiar reglas comerciales, con valores medidos en la configuración operativa (5°). |
| CA-02 | T02 | Para L-01, L-03, L-04, L-07 y L-13: con el valor exacto se acepta; con el valor + 1 se responde 422 `LOAD_LIMIT_EXCEEDED` con el `limit.name` correcto. L-05 conserva su `INVALID_INPUT` actual. |
| CA-03 | T02 | Un rechazo de P3 o P4 ocurre sin llamar a `prepare_persisted_problem`, sin rasterizar y sin crear `StockCandidate`. Se prueba con dobles de prueba que fallan si se invocan. |
| CA-04 | T02 | Tras un rechazo, los pedidos siguen `PENDIENTE`, no hay filas nuevas de optimización y el inventario queda igual (PostgreSQL real). |
| CA-05 | T02 | Las suites existentes de First Fit, Best Fit, Worst Fit, el corte comercial (8 de 8 piezas a 1 mm) y la confirmación pasan sin cambios en sus aserciones. |
| CA-06 | T02 | Una pieza con cantidad 2 147 483 647 se rechaza sin asignar memoria proporcional. |
| CA-07 | T02 | El caso de H-10 (3 piezas distintas de ~1300 × 1000) se rechaza con 422 `raster_memory` antes de crear la ejecución; 2 piezas siguen aceptándose. |
| CA-08 | T03 | Con 2 ejecuciones activas, una tercera recibe 503 `OPTIMIZER_BUSY` con `Retry-After`, incluso tras 300 s de entrega lenta; al terminar una, se admite la siguiente. El límite por usuario también se mantiene. |
| CA-09 | T03 | La plaza se libera cuando termina el trabajador tras éxito, desconexión, fallo o L-12; el cierre de la conexión o de su espera de limpieza no la libera antes. Si el trabajador no arranca, se libera la reserva. No quedan plazas tomadas tras 100 ciclos de admisión y rechazo. |
| CA-10 | T03 | El contrato distingue ejecución admitida (201), rechazada (422 o 503) y cancelada (`EXECUTION_INTERRUPTED` o `TIME_BUDGET_EXCEEDED`), y la confirmación sigue igual. |
| CA-11 | T04 | El frontend muestra el mensaje del backend sin perder la selección de pedidos, con el foco en el aviso, y diferencia «divide el lote» de «intenta más tarde». |
| CA-12 | T04 | Las pruebas de stock voluminoso y de límite + 1 terminan en menos de 5 s y sin OOM, porque rechazan antes de expandir. |

## 10. Impacto técnico

| Área | Cambio | Riesgo |
|---|---|---|
| `optimization/application` | Archivo nuevo `load_budget.py`; nuevas verificaciones en `runs.py`; `RunError` admite `details`. | Bajo: no toca el dominio. |
| `optimization/application/ports.py` | Nuevo puerto `count_compatible(group_key)`. | Bajo. |
| `optimization/infrastructure/stock_adapter.py` | `count_compatible` y la defensa P5. | Bajo: misma regla de compatibilidad. |
| `optimization/presentation/run_routes.py` | Mapeo de `LOAD_LIMIT_EXCEEDED` (422) y `OPTIMIZER_BUSY` (503); admisión en T03. | Medio: hoy un código desconocido responde 500. |
| Frontend `features/optimization` | T04: mensaje y estado. T03: nuevo código de fallo. | Bajo. |
| Base de datos | **Sin migración.** | — |
| TA-021 | La comparación ejecuta varios métodos sobre la misma instancia: el presupuesto se aplica **por solicitud** y TA-021 debe sumar su costo. | Coordinar. |
| HU-017 | Los límites de eventos visuales se acuerdan usando este presupuesto. | Coordinar. |

## 11. Gaps y hallazgos derivados

- **GAP-01 — Escaneo de planchas idénticas sin usar.** El motor evalúa una por
  una las unidades físicas vacías de una misma plancha, aunque sean idénticas (a 5°,
  ~0,62 s por unidad cuando la pieza no encaja). Cambiarlo altera el recorrido del
  motor, así que TA-037 no lo hace. Se propone para una tarea de rendimiento.
  Resolverlo permitiría subir L-07.
- **GAP-02 — Límites al crear pedidos e inventario.** Orders no limita `cantidad`,
  piezas por pedido ni vértices. Su validador de autointersección es O(n²) en
  vértices (`orders/domain/geometry.py:101`). Corresponde a Orders e Inventory:
  se avisa a sus responsables y no se modifica desde TA-037.
- **GAP-03 — Escalado horizontal.** L-10 y L-11 valen para un único proceso. Si se
  agregan dynos o workers, se necesita un ADR de admisión compartida.
- **GAP-04 — Fallos tardíos residuales.** El presupuesto de layouts del motor
  (128 MiB, antes L-09) solo se conoce al calcular, y la cota de L-13 no garantiza
  éxito. Ambos casos terminan como `CALCULATION_FAILED` y se recuperan según TA-038.
- **GAP-05 — Capacidad real a 5° (nuevo en v1.1).** Con la caché raster de 64 MiB y
  72 orientaciones, un pedido comercial con 3 formas grandes distintas no se puede
  calcular en un solo lote. L-13 lo convierte en un rechazo claro, pero no lo
  resuelve. La solución (generar orientaciones bajo demanda, revisar el presupuesto
  de la caché o el paso angular) corresponde a TA-016 / HU-017 T02 y se informa a sus
  responsables.

## 12. Pruebas previstas

| Nivel | Qué | Dónde |
|---|---|---|
| Unitarias | `RunLoadBudget`: exacto y + 1 de cada límite; orden de evaluación; mensajes; desbordamiento de la suma; estimación de L-13 igual a la del motor. | `backend/tests/unit/optimization/test_load_budget.py` |
| Aplicación | `AcceptRun` rechaza sin expandir, con UoW en memoria y preparación espía. | `backend/tests/unit/optimization/test_accept_run_load_limits.py` |
| API | Contrato 422 y 503, sin stream y con permisos. | `backend/tests/api/optimization/test_run_load_limits.py` |
| Integración | Sin mutación en PostgreSQL; stock voluminoso por conteo. | `backend/tests/integration/optimization/test_run_load_limits_pg.py` |
| Regresión | FF, BF, WF, el corte comercial y la confirmación, sin cambios. | Suites existentes |
| Frontend | Mensaje, foco y selección conservada. | `frontend/src/features/optimization/__tests__/` |

## 13. Verificación de criterios de aceptación

| CA | Resultado | Evidencia |
|---|---|---|
| CA-01 | PASS | Esta SPEC (v1.0 a v1.2) y `docs/evidence/sprint-02/TA-037/README.md` |
| CA-02 | PASS | `tests/unit/optimization/test_load_budget.py` (exacto y + 1); `tests/api/optimization/test_run_load_limits.py` |
| CA-03 | PASS | `tests/unit/optimization/test_accept_run_load_limits.py` (espía sobre `prepare_persisted_problem`) |
| CA-04 | PASS | `tests/api/optimization/test_run_load_limits.py`, `tests/integration/optimization/test_run_load_limits_pg.py` (PostgreSQL) |
| CA-05 | PASS técnico | Regresión de optimización: 717 PASS, sin cambiar las aserciones de FF/BF/WF, corte comercial o confirmación. La prueba de caducidad de TA-037 sí se sustituye deliberadamente; suite completa y E2E mediante CI del PR. |
| CA-06 | PASS | Cantidad 2 147 483 647 rechazada en menos de 1 s (unitaria) y en ~0,12 s por HTTP (`test_run_load_stress.py`) |
| CA-07 | PASS | Caso H-10 en `test_load_budget.py` y `test_accept_run_load_limits.py` |
| CA-08 | PASS técnico | Reloj a 300/301/3600 s en `test_run_admission.py`; stream real con PostgreSQL por encima de 300 s en `test_run_concurrency.py`; límites global y por usuario preservados. |
| CA-09 | PASS técnico | Éxito, fallo, rechazo, desconexión, L-12, arranque fallido, contrapresión y trabajador vivo después del join de limpieza; 100 ciclos sin fugas. [Evidencia v1.3](../evidence/sprint-02/TA-037/admission-lifecycle.md). |
| CA-10 | PASS | `test_run_concurrency.py`: 201, 422, 503, `TIME_BUDGET_EXCEEDED`; la confirmación funciona con el optimizador lleno |
| CA-11 | PASS | `frontend/src/features/optimization/__tests__/LoadControlFeedback.test.jsx`; E2E `ta037-load-feedback.spec.js` (escritorio y móvil) |
| CA-12 | PASS | `test_run_load_stress.py`: stock y piezas al máximo de la base, rechazados en menos de 5 s y sin OOM |

## Historial de estado

| Fecha | Versión | Estado | Nota |
|---|---|---|---|
| 25/10/2026 | 1.0 | Draft | T01: límites medidos a 90°, puntos de validación y contrato de error propuestos para revisión del equipo. Integrada con el PR #62. |
| 26/10/2026 | 1.1 | Draft | Recalibración al paso operativo de 5° (PR #64): L-03 de 500 a 150, L-07 de 100 a 50, L-02, L-06 y L-08 retirados, L-12 pasa a protección principal, nuevo L-13 (memoria raster) y GAP-05. Integrada con el PR #65. |
| 26/10/2026 | 1.2 | Reviewed | Valores de v1.1 aprobados por el equipo (Scrum Master). Correcciones de implementación de T02: L-09 retirado por no tener cota segura; L-05 conserva `INVALID_INPUT`; L-13 calculado con cota inferior en coma flotante; P4 usa el adaptador de stock del cálculo. |
| 26/10/2026 | 1.2 | Reviewed | T03 implementada según §5.1, §7.2 y §7.3. Detalle de implementación agregado en §5.1: puntos de liberación de la plaza y respaldo de expiración de 300 s. Sin cambios de valores ni de contrato. |
| 26/10/2026 | 1.2 | Implemented | T04: avisos de frontend («divide el lote», «intenta más tarde», tiempo máximo), pruebas de peor caso y E2E real. CA-01 a CA-12 en PASS (§13). Pendiente: CI en verde y revisión para Verified. |
| 27/10/2026 | 1.3 | Implemented | Retirado el respaldo de expiración de 300 s; CA-08/CA-09 precisan que la plaza sigue al trabajador. Presupuestos y contratos conservados. Regresión focalizada 39 PASS; optimización/geometría/API/PostgreSQL/confirmación 717 PASS. Trabajo original de Aguilar preservado; corrección y revisión técnica de Fabricio Melendez con Codex. CI y revisión del PR pendientes para cierre formal. |
