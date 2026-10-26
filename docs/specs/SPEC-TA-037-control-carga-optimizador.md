# SPEC-TA-037 — Control de carga del optimizador

## Información general

| Campo | Valor |
|---|---|
| ID | TA-037 |
| Nombre | Control de carga del optimizador |
| Sprint | Sprint 2 |
| Tipo / épica | Habilitador / Optimización segura |
| Estado | **Draft** (T01 lista para revisión) |
| Responsable | Fabricio Aguilar |
| Revisor | Pendiente de asignación |
| Fecha | 25/10/2026 |
| Rama | `docs/TA-037-control-carga` (T01); `enabler/TA-037-guardrails` (T02 en adelante) |
| Origen | Auditoría pre-Sprint 2, hallazgo **S1-02** (BLOCKER) y propuesta EN-S2-02 |
| Dependencias | HU-015, TA-021 (T01); TA-037 T01 (T02); TA-037 T01 y T02 (T03); TA-037 T02 y T03 (T04) |
| Coordina con | TA-019, TA-021, HU-017, TA-038 |
| PLAN técnico | [PLAN-TA-037-control-carga-optimizador.md](PLAN-TA-037-control-carga-optimizador.md) |
| Evidencia | [docs/evidence/sprint-02/TA-037](../evidence/sprint-02/TA-037/README.md) |

Este documento corresponde a **TA-037 T01: definir el presupuesto y el contrato de
errores**. Fija los límites técnicos, el punto exacto donde se valida cada uno y la
respuesta que recibe el cliente cuando una ejecución excede el presupuesto. Los
valores de §5 son una **propuesta medida** y entran en vigor cuando el equipo
apruebe esta SPEC. Hasta entonces, nada de lo descrito está implementado.

## 1. Objetivo

Impedir que una sola solicitud válida, o varias simultáneas, agoten la CPU o la
memoria del monolito durante la optimización. Para eso, las solicitudes que
exceden el presupuesto se rechazan **antes** de expandir cantidades, candidatos de
stock o estructuras geométricas costosas.

TA-037 no cambia reglas comerciales. Tampoco modifica la lógica de First Fit ni la
confirmación transaccional.

## 2. Alcance

### Incluye

- Límites operativos para pedidos, líneas de pieza, unidades, geometría,
  orientaciones, stock compatible, memoria interna de layouts, concurrencia y
  tiempo de cálculo.
- Separación explícita entre validación de negocio y límite operativo (§4).
- Punto de validación de cada límite en el flujo actual (§6).
- Contrato de error HTTP y mensaje para el frontend (§7).
- Criterios de aceptación de T02, T03 y T04 (§9).

### Fuera de alcance

- Cambiar el recorrido, el orden de candidatos o la salida temprana de First
  Fit (`packing.py`, `first_fit.py`, `placement.py`, `rotation.py`).
- Cambiar la confirmación (`confirmation.py`, `confirmation_adapter.py`).
- Optimizar el rendimiento del motor. Los hallazgos de §11 se derivan a tareas
  posteriores.
- Recuperar pedidos o ejecuciones tras un fallo: corresponde a **TA-038**.
- Límites de creación de pedidos o de inventario. Son del módulo Orders o
  Inventory y se coordinan con sus responsables (GAP-02).
- Parametrizar los límites desde la interfaz o la tabla `configuraciones`, porque
  requeriría una migración y una API nueva.

## 3. Situación actual (evidencia)

Revisión del código de `integration/sprint-01` en `d1dcd92`:

| # | Hallazgo | Ubicación |
|---|---|---|
| H-01 | `cantidad` acepta hasta 2 147 483 647 por pieza; no hay máximo de piezas por pedido. | `orders/presentation/schemas.py:8,21-36` |
| H-02 | `AcceptRun` expande todas las unidades (`prepare_persisted_problem`) **antes** de cualquier control de tamaño, y luego revisa la geometría una vez por **unidad**, no por pieza. | `optimization/application/runs.py:24-29`; `domain/preparation.py:43-49` |
| H-03 | La lista de pedidos de una ejecución no tiene máximo. | `presentation/run_schemas.py:34-41`; `application/runs.py:13` |
| H-04 | El stock se expande en una unidad física por cada `cantidad` de plancha, sin tope, y ocurre **después** de aceptar la ejecución: los pedidos ya están en `EN_OPTIMIZACION`. | `infrastructure/stock_adapter.py:41-49`; `application/calculation.py:23` |
| H-05 | Si se supera el presupuesto interno de layouts (128 MiB), la ejecución falla **tarde**, después del cálculo, como `CALCULATION_FAILED`. | `domain/packing.py:136-141` |
| H-06 | Cada ejecución crea un hilo propio, sin límite de ejecuciones simultáneas. | `presentation/run_stream.py:126-127`; `run_routes.py:66-73` |
| H-07 | La cancelación cooperativa existe solo en los hitos del motor, y no hay presupuesto de tiempo. | `presentation/run_stream.py:69-73,146-149` |
| H-08 | El despliegue corre **un** proceso uvicorn. | `Procfile` |

Límites que ya existen y se conservan: geometría interna (4000 mm, 4000 celdas por
eje, 16 000 000 celdas), 128 vértices, caché raster de 64 MiB, layouts de 128 MiB y
10 000 orientaciones (`domain/rotation.py:17-20,62,130-155`). Estos límites protegen
**por objeto**; ninguno acota el costo acumulado de la solicitud.

### Mediciones

Mediciones con `experiments/raster/scripts/ta037_load_benchmark.py`, solo con el
motor de dominio, a 1 mm (resolución vigente del seed), paso de 90° y planchas de
2440 × 1830 mm. Máquina de referencia: 2 vCPU Intel Xeon a 2,1 GHz, Python 3.11.
Los resultados completos están en la evidencia.

| Escenario | Tiempo | Lectura |
|---|---:|---|
| Preparar y serializar 20 000 unidades | 0,24 s + 0,26 s; 3,7 MB de JSON | Lineal; no es el cuello de botella |
| FF de 200 / 500 / 1000 / 2000 unidades de 300 × 200 | 0,5 / 3,3 / 13,4 / 52 s | Crece aproximadamente con el cuadrado de las unidades |
| FF de 500 unidades de 600 × 400 | 14,7 s | Las piezas grandes encarecen cada unidad |
| FF de 50 polígonos de 128 vértices, paso 90° / 15° | 0,44 / 1,26 s | Las orientaciones multiplican el costo |
| Unidad que no encaja × planchas vacías (margen 10 mm) | ~9,5 ms por par; 20 × 100 = 19 s; 20 × 1000 = 196 s | Costo proporcional a unidades × stock físico |
| 150 unidades de 1300 × 1000 con 200 planchas | Falla a los 3,5 s: «layouts exceed 128 MiB» (~49 planchas usadas a 1 mm) | Fallo tardío (H-05) |
| 3 ejecuciones simultáneas de 500 unidades | 10,9 s cada una (frente a 3,3 s sola) | El GIL serializa el cálculo y degrada al resto de la API |

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
4. Una pieza que **por sí sola** supera un límite (por ejemplo, cantidad 600 o 140
   vértices) nunca podrá optimizarse en ningún lote. El mensaje lo dice e indica
   que hay que editar el pedido.

## 5. Presupuesto propuesto

Los valores se definen como constantes de la capa Application, igual que
`resource_policy.py`, en un único objeto `RunLoadBudget`. Cambiarlos exige un PR con
la medición que lo justifique. No requieren migración.

| ID | Límite | Valor | Unidad | Base de la decisión |
|---|---|---:|---|---|
| L-01 | Pedidos por ejecución | **20** | pedidos | La UI selecciona pedidos uno a uno; 20 cubre un turno típico y acota `IN (...)` y los bloqueos `FOR UPDATE`. |
| L-02 | Líneas de pieza por ejecución | **200** | filas de `piezas` | Acota la lectura bloqueada y las validaciones por fila (20 pedidos × 10 líneas). |
| L-03 | Unidades por ejecución (Σ `cantidad`) | **500** | unidades | 500 unidades: de 3,3 s a 14,7 s; 1000: 13,4 s o más, con crecimiento cuadrático. |
| L-04 | Vértices por pieza | **128** | vértices | Ya es el límite interno de `RasterCache`; se adelanta a antes de expandir. |
| L-05 | Extensión geométrica por pieza | **4000 mm; 4000 celdas por eje; 16 000 000 celdas** | — | Ya existe en `RasterCache.check_geometry`; se aplica **una vez por pieza**, no por unidad. |
| L-06 | Unidades × orientaciones por ejecución | **2000** | evaluaciones | Equivale a 500 unidades a 90° (4 ángulos) y a 83 unidades a 15° (24 ángulos). |
| L-07 | Stock físico compatible por material (Σ `planchas.cantidad` activas + retazos activos) | **100** | unidades físicas | Acota la expansión de H-04 y el escaneo de candidatos. |
| L-08 | Unidades × stock físico, por material | **5000** | pares | Peor caso medido de ~9,5 ms por par: unos 48 s. Ejemplos válidos: 100 × 50 o 500 × 10. |
| L-09 | Memoria de layouts por ejecución | **128 MiB** (existente) | bytes estimados | Se rechaza antes de calcular solo cuando la **cota inferior** de planchas necesarias ya supera el presupuesto (§5.1). |
| L-10 | Ejecuciones activas por proceso | **2** | ejecuciones | Con 3 simultáneas, cada una tarda más de 3 veces lo normal; con 2 queda capacidad para el resto de la API. |
| L-11 | Ejecuciones activas por usuario | **1** | ejecuciones | Evita que un usuario ocupe toda la capacidad. |
| L-12 | Tiempo máximo de cálculo | **120 s** | s | Respaldo final, verificado en los hitos del motor (T03). |

### 5.1 Reglas de cálculo

- **L-03:** suma de `cantidad` de las filas leídas, **sin crear unidades**.
- **L-06:** `L-03 × orientaciones`, donde las orientaciones son
  `len(discrete_angles(paso_angular))`, y 1 para circunferencias.
- **L-07 y L-08:** se calculan por grupo de material (`id_tipo_vidrio`, `espesor_mm`)
  con las mismas reglas de compatibilidad de `InventoryStockAdapter`: activas, con
  `cantidad > 0` y del mismo material. Se cuentan filas y se suman cantidades sin
  crear `StockCandidate`.
- **L-09:** `cota = ceil(Σ área de unidades del grupo / área de la plancha compatible
  más grande)`. Se rechaza si Σ por grupo de `cota × estimación de bytes por layout`
  supera 128 MiB. La estimación de bytes por layout es la misma fórmula de
  `packing.py:138`. Solo se rechaza lo que **seguro** fallaría; si la cota cabe y el
  motor falla igual, sigue el fallo tardío actual (TA-038).
- **L-10 y L-11:** cuentan ejecuciones con hilo de cálculo vivo **en este
  proceso**. La plaza se libera cuando termina el hilo, no cuando se cierra la
  conexión del cliente. La regla es válida mientras haya un solo proceso
  (H-08); con más dynos o workers se necesitaría una admisión compartida en base de
  datos, y esa decisión requiere un ADR.
- Si una solicitud viola varios límites, se informa **solo el primero** en el orden
  de §6. Así el resultado es determinista y fácil de probar.

## 6. Dónde se valida cada límite

Regla general: cada límite se valida en el **último punto donde todavía es barato**,
antes de la primera estructura proporcional a lo que limita.

| Orden | Punto | Archivo y momento | Límites | Qué existe en ese momento | Qué todavía **no** existe |
|---|---|---|---|---|---|
| P1 | Antes de abrir la transacción | `application/runs.py`, `AcceptRun.execute`, después de la validación de ids (línea 13) | L-01 | Solo la lista de ids | Bloqueos, lecturas |
| P2 | Admisión | `presentation/run_routes.py`, `start_run`, **antes** de `AcceptRun` (línea 70), mediante un puerto de admisión | L-10, L-11 | Usuario autenticado | Transacción, ejecución |
| P3 | Con los pedidos bloqueados | `application/runs.py`, inmediatamente después de `uow.orders.lock_pending(ids)` (línea 18) y **antes** de `prepare_persisted_problem` (línea 24) | L-02, L-03, L-04, L-05 (por fila), L-06 | Filas de `piezas` (≤ L-02) y configuración | Unidades expandidas, máscaras |
| P4 | Stock, en la misma transacción | `application/runs.py`, después de P3 y **antes** de `uow.runs.create` (línea 32); usa un puerto nuevo `count_compatible` que no expande | L-07, L-08, L-09 | Conteos por material | `StockCandidate`, layouts |
| P5 | Defensa en el cálculo | `infrastructure/stock_adapter.py`, `list_compatible`, antes del bucle de expansión (línea 41) | L-07 | Filas de inventario | Unidades físicas |
| P6 | Durante el cálculo | `presentation/run_stream.py`, callback `milestone` (líneas 69-73) | L-12 | Ejecución en curso | — |

Notas de diseño:

- **P3 y P4 están dentro de la transacción** que ya abre `AcceptRun`. Un rechazo
  lanza `RunError` antes de `runs.create` y de `orders.transition`, así que la
  unidad de trabajo hace rollback: no se crea `optimizaciones`, los pedidos siguen
  `PENDIENTE` y no se lee ni escribe stock para consumo.
- **P4 se adelanta a la aceptación** porque hoy el stock se lee recién en
  `CalculateRun` (H-04), cuando los pedidos ya pasaron a `EN_OPTIMIZACION`. Un
  rechazo en ese punto dejaría una ejecución `FALLIDA` y pedidos atrapados (TA-038).
- **P5 es una red de seguridad.** Cubre el caso de que entre P4 y el cálculo se
  registre más stock. Falla como `CALCULATION_FAILED`, con el motivo en el log del
  servidor, sin cambiar el contrato del stream.
- **P3 no cambia el resultado de First Fit.** Si la solicitud se acepta, el problema
  preparado es idéntico al actual. P3 solo mueve la verificación de geometría de
  «una vez por unidad» a «una vez por pieza», con la misma función y el mismo error.

## 7. Contrato de error

### 7.1 Límite de tamaño (L-01 a L-09)

`HTTP 422 Unprocessable Content`, sin cuerpo NDJSON. La ejecución no llega a
crearse.

```json
{
  "detail": {
    "code": "LOAD_LIMIT_EXCEEDED",
    "message": "Los pedidos seleccionados suman 740 unidades y el máximo por cálculo es 500. Divide la selección en lotes más pequeños.",
    "limit": {
      "name": "units_per_run",
      "maximum": 500,
      "actual": 740,
      "scope": null
    }
  }
}
```

| Campo | Tipo | Regla |
|---|---|---|
| `code` | string | Siempre `LOAD_LIMIT_EXCEEDED` para L-01 a L-09. |
| `message` | string | En español y apto para mostrar tal cual. No incluye SQL, trazas, nombres de tabla ni rutas. |
| `limit.name` | string | Uno de: `orders_per_run`, `piece_rows_per_run`, `units_per_run`, `vertices_per_piece`, `geometry_extent`, `orientations_per_run`, `stock_units_per_material`, `unit_stock_pairs_per_material`, `layout_memory`. |
| `limit.maximum` | int | Valor del presupuesto vigente. |
| `limit.actual` | int | Valor medido. Para `geometry_extent` es el eje mayor en celdas. |
| `limit.scope` | object \| null | `{"id_pieza": n}` para L-04 y L-05; `{"id_tipo_vidrio": n, "espesor_mm": "6.00"}` para L-07 a L-09; `null` en el resto. |

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
y `OptimizationFailedV1`. Ese cambio corresponde a T03 y T04. Qué pasa después con
los pedidos lo define TA-038.

### 7.4 Mensajes por límite

| `limit.name` | Mensaje (las llaves se reemplazan) |
|---|---|
| `orders_per_run` | Seleccionaste {actual} pedidos y el máximo por cálculo es {maximum}. Quita algunos e inténtalo de nuevo. |
| `piece_rows_per_run` | Los pedidos seleccionados tienen {actual} líneas de piezas y el máximo por cálculo es {maximum}. Divide la selección. |
| `units_per_run` | Los pedidos seleccionados suman {actual} unidades y el máximo por cálculo es {maximum}. Divide la selección en lotes más pequeños. |
| `vertices_per_piece` | La pieza {id_pieza} tiene {actual} vértices y el máximo admitido es {maximum}. Edita la pieza en su pedido. |
| `geometry_extent` | La pieza {id_pieza} es demasiado grande para la resolución de cálculo configurada. Edita la pieza o solicita revisar la configuración. |
| `orientations_per_run` | El cálculo requeriría {actual} combinaciones de piezas y orientaciones, y el máximo es {maximum}. Selecciona menos unidades o solicita revisar el paso angular. |
| `stock_units_per_material` | Hay {actual} unidades de stock compatibles para un mismo material y un cálculo admite {maximum}. Solicita al almacenero revisar el inventario activo. |
| `unit_stock_pairs_per_material` | La combinación de piezas y stock de un mismo material es demasiado grande para un solo cálculo. Selecciona menos pedidos de ese material. |
| `layout_memory` | Las piezas de un mismo material necesitarían más planchas de las que un cálculo puede manejar. Divide la selección en lotes más pequeños. |

El backend construye el mensaje. En el primer paso, el frontend lo muestra tal
cual, porque `runApi.js:51` ya usa `detail.message`. T04 agrega la presentación
específica: aviso no destructivo y selección conservada.

## 8. Reglas

- **RN-01 — Rechazo temprano.** Ningún límite de §5 se evalúa después de crear la
  estructura proporcional a lo que limita.
- **RN-02 — Sin mutación.** Un rechazo de L-01 a L-11 no crea filas en
  `optimizaciones`, `ejecuciones_optimizacion` ni `optimizacion_pedidos`, no
  cambia el estado de los pedidos y no toca `planchas`, `retazos` ni
  `movimientos_inventario`.
- **RN-03 — First Fit intacto.** Las solicitudes dentro del presupuesto producen
  exactamente los mismos placements, eventos, métricas y estados que hoy.
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
| CA-01 | T01 | Esta SPEC documenta L-01 a L-12, su punto de validación y su contrato de error, sin cambiar reglas comerciales. |
| CA-02 | T02 | Para L-01 a L-09: con el valor exacto se acepta; con el valor + 1 se responde 422 `LOAD_LIMIT_EXCEEDED` con el `limit.name` correcto. |
| CA-03 | T02 | Un rechazo de P3 o P4 ocurre sin llamar a `prepare_persisted_problem` ni crear `StockCandidate`. Se prueba con dobles de prueba que fallan si se invocan. |
| CA-04 | T02 | Tras un rechazo, los pedidos siguen `PENDIENTE`, no hay filas nuevas de optimización y el inventario queda igual (PostgreSQL real). |
| CA-05 | T02 | Las suites existentes de First Fit, Worst Fit, el corte comercial (8 de 8 piezas a 1 mm) y la confirmación pasan sin cambios en sus aserciones. |
| CA-06 | T02 | Una pieza con cantidad 2 147 483 647 se rechaza sin asignar memoria proporcional. |
| CA-07 | T03 | Con 2 ejecuciones activas, una tercera recibe 503 `OPTIMIZER_BUSY` con `Retry-After`; al terminar una, se admite la siguiente. |
| CA-08 | T03 | La plaza se libera si el cliente se desconecta, si el cálculo falla o si se supera L-12. No quedan plazas tomadas tras 100 ciclos de admisión y rechazo. |
| CA-09 | T03 | El contrato distingue ejecución admitida (201), rechazada (422 o 503) y cancelada (`EXECUTION_INTERRUPTED` o `TIME_BUDGET_EXCEEDED`), y la confirmación sigue igual. |
| CA-10 | T04 | El frontend muestra el mensaje del backend sin perder la selección de pedidos, con el foco en el aviso, y diferencia «divide el lote» de «intenta más tarde». |
| CA-11 | T04 | Las pruebas de stock voluminoso y de límite + 1 terminan en menos de 5 s y sin OOM, porque rechazan antes de expandir. |

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

- **GAP-01 — Escaneo de planchas idénticas sin usar.** First Fit evalúa una por
  una las unidades físicas vacías de una misma plancha, aunque sean idénticas
  (~9,5 ms por unidad cuando la pieza no encaja). Cambiarlo altera el recorrido de
  First Fit, así que TA-037 no lo hace. Se propone para una tarea de rendimiento.
  Resolverlo permitiría subir L-07 y L-08.
- **GAP-02 — Límites al crear pedidos e inventario.** Orders no limita `cantidad`,
  piezas por pedido ni vértices. Su validador de autointersección es O(n²) en
  vértices (`orders/domain/geometry.py:101`). Corresponde a Orders e Inventory:
  se avisa a sus responsables y no se modifica desde TA-037.
- **GAP-03 — Escalado horizontal.** L-10 y L-11 valen para un único proceso. Si se
  agregan dynos o workers, se necesita un ADR de admisión compartida.
- **GAP-04 — Fallo tardío residual de L-09.** La cota inferior no garantiza éxito.
  El fallo tardío se recupera según TA-038.

## 12. Pruebas previstas

| Nivel | Qué | Dónde |
|---|---|---|
| Unitarias | `RunLoadBudget`: exacto y + 1 de cada límite; orden de evaluación; mensajes; desbordamiento de la suma. | `backend/tests/unit/optimization/test_load_budget.py` |
| Aplicación | `AcceptRun` rechaza sin expandir, con UoW en memoria y preparación espía. | `backend/tests/unit/optimization/test_accept_run_load_limits.py` |
| API | Contrato 422 y 503, sin stream y con permisos. | `backend/tests/api/optimization/test_run_load_limits.py` |
| Integración | Sin mutación en PostgreSQL; stock voluminoso por conteo. | `backend/tests/integration/optimization/test_run_load_limits_pg.py` |
| Regresión | FF, WF, el corte comercial y la confirmación, sin cambios. | Suites existentes |
| Frontend | Mensaje, foco y selección conservada. | `frontend/src/features/optimization/__tests__/` |

## Historial de estado

| Fecha | Estado | Nota |
|---|---|---|
| 25/10/2026 | Draft | T01: límites medidos, puntos de validación y contrato de error propuestos para revisión del equipo. |