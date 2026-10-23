# SPEC-HU-015 — Interfaz de rasterización

## Revisión S1-01 — 21/10/2026

Esta revisión autorizada sustituye las reglas históricas de inicio y estados de la vista previa descritas más abajo. Se conserva el cierre Verified y la evidencia del PR #47 como registros históricos: aquella versión sí cambiaba el pedido a EN_OPTIMIZACION. La corrección se verifica por separado en [evidencia S1-01](../evidence/sprint-01/S1-01/README.md).

- `POST /api/optimization/start` se conserva como preparación de consulta: lee el pedido PENDIENTE y valida todas sus piezas, pertenencia, geometría y presupuesto inicial a 5 mm/celda. Devuelve `200 {"id_pedido":10,"estado":"PENDIENTE"}` sin escribir; repetir sobre un pedido todavía válido devuelve 200. Ausencia 404, estado no pendiente 409 y datos/presupuesto inválidos 422.
- `POST /api/optimization/rasterize` acepta PENDIENTE y conserva la lectura de EN_OPTIMIZACION. Relee la pieza persistida y valida pertenencia, geometría, resolución y presupuesto en cada solicitud. OPTIMIZADO, CONFIRMADO y CANCELADO siguen rechazados con 409. No exige un start previo persistido.
- Preparar o rasterizar no modifica pedidos/piezas, no crea optimización/ejecución y no reserva ni consume inventario. Se conservan autenticación, permisos actuales y contratos de error seguros.
- «Vista previa preparada» es una condición local de la UI tras validar y recargar el detalle; no cambia Pedido.estado. Al volver a abrir la vista se puede preparar de nuevo el mismo pendiente. Los pedidos EN_OPTIMIZACION siguen consultables sin normalización ni otro start. La UI cancela/ignora respuestas obsoletas y no deduce una preparación exitosa de un GET pendiente después de un error.
- Previsualizar deja disponible la edición ordinaria del pendiente. Una máscara describe los datos de su cálculo, no constituye una reserva ni el snapshot de First Fit; editar puede reemplazar IDs de piezas y cada nuevo cálculo relee los datos efectivos.
- El inicio real de `/api/optimization/runs` conserva su validación atómica de pendientes y su transición PENDIENTE → EN_OPTIMIZACION junto a la creación de ejecución/snapshot. Confirmación, persistencia y stock conservan sus reglas.

Los criterios históricos que exigían transición, segundo start 409, un único ganador concurrente o rasterización solo en EN_OPTIMIZACION quedan sustituidos para esta revisión por: preparaciones concurrentes válidas sin escrituras; preparación repetible; raster sobre pendiente; edición posterior permitida; recorrido vista previa → raster → First Fit → resultado persistido → confirmación; stock intacto hasta confirmar. No se incorporan migraciones ni reparación automática de históricos.

## Información general

| Campo | Valor |
|---|---|
| Estado | **Verified** |
| PBI relacionado | HU-015 — Interfaz de rasterización; Sprint 1 |
| Responsable / Autor | Fabricio Melendez |
| Reviewer | Fabricio Danniel Aguilar Chávez |
| Fecha de revisión | 13/10/2026 |
| Decisión | Implementación revisada, aprobada e integrada mediante PR #47. |
| Revisión humana final | Aprobada; confirmada por el equipo para este cierre. |
| Fecha de cierre | 14/10/2026 |
| Rama de implementación | `feature/HU-015-interfaz-rasterizacion` |
| Base de integración | `integration/sprint-01` |
| PR de implementación | [#47 — feat(HU-015): interfaz y rasterización de piezas para optimización](https://github.com/melendezzz26/optimizador-vidrio/pull/47) |
| Último commit de la feature | `a4146551dcec4e5e46a77f803b4f378dbe21a4cd` |
| Merge del PR | `86972fd779bae826909a401874f06d5b7dd2a3ed` |
| Fecha de auditoría | 13/10/2026 |
| Rama auditada | `integration/sprint-01` |
| HEAD local inicial y remoto después de fetch | `728c1dd9020f6c562419620bbcaa1c1ca0545757` |
| Convención | SPEC de archivo único, según `SPEC-TEMPLATE.md` y `CONTRIBUTING.md` |

SPEC cerrada como **Verified** después de la implementación T1/T2/T3, su validación registrada y la revisión humana aprobada por Fabricio Danniel Aguilar Chávez, confirmada por el equipo. El cierre y sus fuentes se documentan en §17. Las secciones 1–16 conservan el alcance y la auditoría originales del 13/10/2026 sobre `728c1dd`; sus referencias a capacidades faltantes, propuestas y pendientes describen esa línea base histórica, no el estado integrado posterior al PR #47. No se reescriben retrospectivamente los criterios de aceptación ni el alcance. Esta actualización documental no vuelve a ejecutar pruebas, experimentos o capturas.

## 1. Contexto, fuente y problema

La fuente explícita recuperada es [ADR-002, §2.11](../adr/ADR-002-operacion-pre-raster.md): selección de pedido; recuperación de piezas; ejecución/configuración permitida; visualización de geometría original frente a máscara raster; estados de error y resultado. El mismo ADR identifica HU-015 por nombre y mantiene FF/BF/WF en Sprint 2.

Se buscaron HU-015/HU015, interfaz/visualización raster, rasterización, Optimization y Results en el repositorio, documentación, historial y referencias remotas disponibles. No se recuperó una SPEC previa de HU-015, plan, tasks ni un backlog versionado que detalle sus criterios. **La división original T1/T2/T3 no fue encontrada en las fuentes auditadas.** No se le atribuirá una división histórica inventada. Un plan/tasks posterior podrá contener una **«Descomposición técnica propuesta»** identificada como tal.

El backend integrado convierte las tres geometrías admitidas en máscaras y valida colocaciones. Sin embargo, no tiene una API de rasterización ni una pantalla que conecte pedidos persistidos con ese dominio. Las imágenes de experimentos no constituyen una interfaz funcional.

Hay documentación histórica divergente: ADR-002 §2.4 exige stock antes de registrar pedidos; [TA-036, §6.2](SPEC-TA-036-saneamiento-funcional.md) y `CreateOrderUseCase` vigente mantienen el POST independiente del stock. HU-015 conserva esta última regla. El apartado inicial de auditoría de TA-036 describe un Optimization aún vacío, pero es anterior a las integraciones #42/#43 y no describe el HEAD actual. No se modifican esos documentos en esta tarea.

## 2. Objetivo

Permitir a los usuarios autorizados seleccionar un pedido persistido `PENDIENTE`, consultar sus piezas e iniciar explícitamente su proceso mediante **«Iniciar optimización»**. Cuando el backend acepta un inicio válido, el pedido pasa a `EN_OPTIMIZACION`; después se rasterizan sus piezas persistidas y se visualiza su geometría original junto con la máscara backend, identificando pieza, pedido, unidades y resolución. El cálculo debe ser reproducible a partir de sus datos efectivos, sin ejecutar heurísticas, completar la optimización ni producir movimientos de inventario.

## 3. Auditoría de la base integrada y ramas paralelas

### 3.1 Git

Se ejecutaron `git status`, `git branch --show-current`, `git fetch origin --prune` y nuevamente `git status`. El primer fetch no pudo conectar por la restricción de red; la repetición autorizada terminó con código 0. Se revisaron también:

```text
git log --oneline --decorate -15
git log --oneline HEAD..origin/integration/sprint-01
git branch -r --sort=-committerdate
git log --all --oneline --decorate --since="2026-10-13 00:00"
git log --first-parent --format="%h %ad %s" --date=iso -10
git log --oneline HEAD..origin/feature/HU-008-stock-compatible
git diff --name-only HEAD...origin/feature/HU-008-stock-compatible
```

- Rama local: `integration/sprint-01`; working tree inicial limpio.
- Local y `origin/integration/sprint-01`: `728c1dd`. El rango `HEAD..origin/integration/sprint-01` está vacío: no hay avance posterior ni PR nuevo en integration frente a la base conocida.
- El fetch completado no informó actualizaciones ni referencias pruneadas. No se atribuyen eliminaciones históricas a este fetch.
- No se hizo merge, checkout, integración de ramas ni modificación de referencias de trabajo.

Integraciones relevantes, en orden real de la primera línea de padres (fechas Git, zona `-0500`):

| Fecha | Commit | PR / contenido |
|---|---|---|
| 12/10/2026 00:06:49 | `9407f26` | #39, HU-012 T03: cliente asociado al pedido |
| 12/10/2026 00:41:59 | `978705f` | #40, HU-014: trazabilidad de inventario |
| 12/10/2026 02:41:21 | `b7a0175` | #41, staging existente |
| 13/10/2026 00:54:59 | `cff3db6` | #42, TA-005/TA-006: rasterización |
| 13/10/2026 12:07:08 | `373dfc2` | #44, TA-036: saneamiento funcional |
| 13/10/2026 13:04:40 | `293a2a9` | #43, TA-007: validación geométrica |
| 13/10/2026 17:25:28 | `728c1dd` | #45, cierre documental TA-035-T1 |

Referencias remotas observadas; su existencia no demuestra trabajo activo en este instante:

| Rama `origin/…` | Punta | Relación con HEAD |
|---|---|---|
| `feature/HU-008-stock-compatible` | `a0a2dd2` | No integrada; contiene 10 commits exclusivos frente a HEAD |
| `feature/TA-036-saneamiento-funcional` | `4e431e5` | Punta antecesora de HEAD |
| `feature/TA-005-TA-006-rasterizacion` | `0ef9819` | Punta antecesora de HEAD |
| `feature/HU-012-T03-asociar-cliente-pedido` | `e1fe3a5` | Punta antecesora de HEAD |
| `feature/TA-DEPLOY-001-staging` | `44b375f` | Punta antecesora de HEAD |
| `feature/HU-014-trazabilidad-inventario` | `f4a6926` | Punta antecesora de HEAD |
| `main` / `HEAD` simbólico | `aae4bcc` | Antecesor de HEAD local |

No aparecen ramas remotas adicionales de Results, Configuration u Optimization. Las antiguas ramas TA-007 y TA-035-T1 no figuran en el inventario actual; no se infiere cuándo se borraron.

### 3.2 Riesgo HU-008

La punta `a0a2dd2` tiene fecha Git `2026-10-12 22:45:23 -0800` (13/10/2026 01:45:23 en Lima). Sus commits exclusivos son `24484a4`, `8ea8acd`, `0241365`, `ccfa6a6`, `46d801e`, `b660021`, `9bf2a50`, `9aaec66`, `edc0809` y `a0a2dd2`. Son trabajo paralelo preexistente, no nuevos merges de integration detectados por el fetch.

- Inventory incorpora `get_compatible_stock(id_tipo_vidrio, espesor_mm)`, que devuelve planchas y retazos candidatos, y `StockCompatibilityService.find_missing_candidate_indexes(pieces)`.
- El servicio filtra por material/espesor y disponibilidad, y verifica candidatos individuales mediante cajas envolventes y giro de 90°. No garantiza que todas las cantidades del pedido quepan simultáneamente ni equivale a la validación raster de TA-007.
- Orders incorpora un `StockCandidateChecker`; `9aaec66` bloquea el registro cuando faltan candidatos y `edc0809` presenta ese rechazo en el formulario.
- Afecta puertos/repositorio/servicio/dominio de Inventory, caso de uso/dependencias/router de Orders, formulario/servicio API frontend y pruebas. Puede interferir directamente con el desacoplamiento pedido-stock y con contratos futuros de HU-015.
- Ese comportamiento contradice TA-036 y la regla vigente del producto. No se integra ni se corrige aquí. Antes de reutilizarlo debe acordarse un contrato de consulta posterior a la creación del pedido; HU-015 no depende de archivos de una rama no integrada.

## 4. Alcance

### Incluye

El núcleo procede de ADR-002 §2.11. Su concreción siguiente es **Propuesta para revisión**:

- Acceso a la vista raster desde la navegación existente para Administrador y Operario.
- Listado paginado/selección de pedidos reales y lectura de su detalle completo mediante los contratos actuales de Orders.
- Presentación de todas las líneas de piezas del pedido: identificador, forma, dimensiones o vértices, cantidad, tipo de vidrio y espesor; selección de una pieza para su vista previa.
- Flujo mínimo **pedido `PENDIENTE` → selección del pedido → consulta de piezas → acción explícita «Iniciar optimización» → validación de precondiciones → `PENDIENTE → EN_OPTIMIZACION` → rasterización de las piezas persistidas → visualización de geometría original vs máscara raster**. La transición pertenece al proceso del pedido. La operación raster sigue calculando una pieza seleccionada por solicitud; no introduce un contrato masivo ni rasteriza todo el pedido automáticamente.
- Rasterización de la geometría persistida recuperada por el backend. Una fila PIEZA puede representar varias unidades mediante `cantidad > 1`: por geometría y resolución efectivas se calcula una sola máscara por tipo de pieza persistida, sin recalcular máscaras idénticas por cantidad. Por ejemplo, Pieza A con `cantidad = 5` produce una `RasterMask A`, reutilizable cinco veces por FF/BF/WF en una etapa posterior fuera de HU-015; aquí no se generan colocaciones.
- Resolución de la vista previa, carga, bloqueo de doble envío, errores recuperables y resultado con geometría/máscara comparables.
- Identificación y metadatos suficientes para interpretar y reproducir el cálculo, sin guardar un historial de ejecuciones.
- Adaptación backend/API mínima necesaria para conectar el dominio existente. No hay endpoint integrado que la sustituya; su responsabilidad y contrato deben revisarse antes de implementar.

### Fuera de alcance

- First Fit, Best Fit, Worst Fit, comparación o elección de heurística, mejor solución y colocación completa del pedido.
- Aprovechamiento final, merma final, planchas utilizadas u otras métricas de una optimización no ejecutada.
- Consumo, reserva o descuento de stock; confirmación de solución/inventario; transiciones posteriores a `EN_OPTIMIZACION`, incluidos los estados `OPTIMIZADO` y `CONFIRMADO`.
- Persistir la vista previa en `optimizaciones`, `ejecuciones_optimizacion`, `metricas_ejecucion` o movimientos de inventario, incluyendo registros ficticios FF/BF/WF.
- Crear/editar piezas o pedidos desde la vista raster, reconstruir polígonos desde lados/ángulos o habilitar concavidad.
- Selección de stock compatible, rasterización de material y validación interactiva de colocaciones en esta propuesta mínima. Requieren un alcance y contrato integrado adicionales; la existencia del dominio TA-007 no implica que ese flujo ya exista.
- CRUD de configuración global, lectura ficticia de una configuración vigente, rotación de piezas y parámetros que no consume la operación ejecutada.
- Reimplementar rasterización en React, cambiar los algoritmos TA-005/006/007, rediseñar globalmente la aplicación o introducir otra arquitectura de navegación.

## 5. Actores, permisos y precondiciones

La matriz efectiva está en [permissions.py](../../backend/app/core/permissions.py):

| Capacidad actual | Administrador | Operario | Almacenero |
|---|---|---|---|
| `GESTIONAR_PEDIDOS` | Sí | Sí | No |
| `EJECUTAR_OPTIMIZACION` | Sí | Sí | No |
| `CONSULTAR_STOCK` / `CONSULTAR_TIPOS_VIDRIO` | Sí | Sí | Sí |
| `CONFIGURAR_OPTIMIZADOR` | Sí | No | No |
| `CONSULTAR_RESULTADOS` | Sí | Sí | Sí |

La matriz vigente confirma que `EJECUTAR_OPTIMIZACION` corresponde a **Administrador y Operario**, y no a Almacenero. **Propuesta para revisión:** aplicar ese permiso al inicio del proceso y a `POST /api/optimization/rasterize`, ocultar la opción al Almacenero y rechazar también su solicitud directa en backend. `CONSULTAR_RESULTADOS` no concede permiso para calcular raster ni habilita una pantalla Results todavía inexistente.

Precondiciones de inicio: sesión válida, autorización, pedido existente en estado `PENDIENTE`, piezas válidas y parámetros compatibles con los límites acordados. Para cada cálculo por pieza se comprueban además existencia, pertenencia, geometría compatible, resolución y tamaño, dentro del proceso ya iniciado del pedido. La autorización se comprueba en cada solicitud. Inventario con stock no es precondición de este flujo.

**Regla de estados de HU-015:** solo un pedido `PENDIENTE` es elegible para **iniciar** optimización. Abrir/consultar la pantalla, seleccionar pedido o pieza y cambiar `resolution_mm` no modifican su estado. Únicamente la acción explícita **«Iniciar optimización»**, con precondiciones válidas y aceptación del backend, produce `PENDIENTE → EN_OPTIMIZACION` para el pedido completo. Un pedido inexistente, no `PENDIENTE`, sin piezas válidas o con un error de validación previo al inicio se rechaza sin transición. El inicio debe ser coherente con el inicio real del proceso; la transacción o caso de uso que lo garantice se resolverá en el plan técnico, sin fijar aquí una implementación.

Los cálculos individuales posteriores pertenecen a ese proceso en `EN_OPTIMIZACION` y no vuelven a iniciarlo ni generan transiciones por máscara. Un pedido ya `EN_OPTIMIZACION` no es elegible para un nuevo inicio; esto no impide rasterizar sus piezas dentro del proceso aceptado. Orders ya persiste `PENDIENTE` al crear y expone los cinco estados en su respuesta; sigue siendo la fuente de verdad y el backend comprueba el estado vigente.

Continuidad conceptual, fuera del alcance inmediato: **`PENDIENTE → EN_OPTIMIZACION → OPTIMIZADO → CONFIRMADO`**. `CANCELADO` continúa como estado alternativo según las reglas existentes. HU-015 cubre únicamente `PENDIENTE → EN_OPTIMIZACION`; no implementa las transiciones posteriores.

## 6. Contratos integrados y dependencias

### 6.1 Orders: entrada suficiente, sin nuevo CRUD

Fuentes: [router](../../backend/app/modules/orders/presentation/router.py), [schemas](../../backend/app/modules/orders/presentation/schemas.py), [casos de uso](../../backend/app/modules/orders/application/use_cases.py), [repositorio](../../backend/app/modules/orders/infrastructure/repositories.py).

| Endpoint existente | Datos y comportamiento relevantes |
|---|---|
| `GET /api/orders` | Filtros `page`, `limit` (1–100), `estado`, `cliente`, `fecha`. Devuelve `items`, `total`, `page`, `limit`, `total_pages`. Cada resumen incluye ID, fecha, estado y cliente visible; no sustituye el detalle de piezas. |
| `GET /api/orders/{id_pedido}` | Devuelve `id_pedido`, `id_cliente` nullable, fecha, estado, usuario de registro y `piezas` completas. Cada pieza contiene `id_pieza`, `id_pedido`, `id_tipo_vidrio`, `espesor_mm`, `tipo_forma`, `cantidad`, `dimensiones`, `geometria`, `area_mm2`. |
| `POST /api/orders` | Crea pedido con cliente, catálogo y geometría válidos; no consulta ni exige stock. No se invoca desde la vista raster. |
| `PUT` / `DELETE /api/orders/{id_pedido}` | Edición/cancelación existentes; fuera de la operación raster. La edición puede reemplazar filas de piezas y cambiar sus IDs. |

Todas estas rutas usan `GESTIONAR_PEDIDOS`. El detalle sí permite recuperar un pedido persistido completo. `dimensiones` puede ser null para polígonos; `geometria` es la fuente del cálculo. Material y espesor pertenecen a cada pieza, no a una cabecera única del pedido.

`espesor_mm` y `area_mm2` son `Decimal` en el esquema de respuesta: no presuponer que cualquier campo numérico HTTP llega como `number`. La adaptación/presentación debe seguir el contrato de serialización real y conservar unidades. El rasterizador recibe números finitos `int`/`float`, no `Decimal`; el límite de adaptación debe normalizar lo necesario sin cambiar el modelo de dominio ni regenerar geometrías.

Frontend ya dispone de `listOrders`, `getOrder`, `listOrderMaterials` y manejo de `OrdersApiError` en [ordersApi.js](../../frontend/src/features/orders/ordersApi.js). No hace falta reconstruir un servicio CRUD paralelo. **Optimization/Application** define el puerto de lectura que necesita el caso de uso por pieza; **Optimization/Infrastructure** implementa ese puerto adaptando el acceso a Orders. Orders sigue siendo la fuente de verdad del pedido, pieza, geometría persistida, material, espesor y cantidad. El adaptador no duplica las reglas de Orders. **Optimization/Domain** no importa esquemas HTTP ni modelos ORM.

### 6.2 Inventory: inventario consultable no equivale a stock compatible

Fuentes: [router](../../backend/app/modules/inventory/presentation/router.py), [schemas](../../backend/app/modules/inventory/presentation/schemas.py), [puertos](../../backend/app/modules/inventory/application/ports.py).

| Endpoint existente | Datos relevantes |
|---|---|
| `GET /api/inventory/tipos-vidrio` | ID, nombre, descripción, estado y espesores del catálogo; permite identificar el material de cada pieza. |
| `GET /api/inventory/planchas` | ID, ancho, alto, espesor, cantidad, estado, fecha e ID de tipo de vidrio. |
| `GET /api/inventory/retazos` | ID, código, espesor, geometría, área, estado, fecha, tipo de vidrio e ID de ejecución de origen nullable. |

Los listados no son una respuesta de compatibilidad. Incluyen estados; una plancha disponible requiere estado activo y cantidad positiva, y un retazo activo es unitario. No hay un endpoint integrado que garantice compatibilidad individual o conjunta con un pedido. Identificar tipo/espesor no basta para afirmar que una pieza cabe.

El alcance mínimo usa el catálogo para rotular piezas, sin obligar a que exista stock. Si no se recupera el nombre, mostrar el ID y un aviso; no inventar un material. La selección de material pertenece a una etapa posterior que necesitará HU-008 desacoplada y el contrato de instancia correspondiente (TA-008), sin integración automática en HU-015.

### 6.3 Configuration y Results

Los módulos backend `configuration/` y `results/` contienen únicamente archivos `__init__.py` de reserva. Sus features frontend contienen `.gitkeep`. [backend/main.py](../../backend/main.py) no registra routers de Configuration, Results ni Optimization.

Sí existen modelos y migraciones de persistencia en [models.py](../../backend/app/models.py): `Configuracion` versionada, con `separacion_mm`, `margen_mm`, `resolucion_raster_mm`, paso angular opcional, mínimos de retazo, vigencia y autor; `Optimizacion`; `EjecucionOptimizacion`; `MaterialUtilizado`; `MetricaEjecucion`. La existencia de esas tablas no equivale a servicios públicos implementados.

`EjecucionOptimizacion.metodo` admite exclusivamente `FF`, `BF`, `WF` mediante `ck_ejecuciones_metodo`. No se debe reutilizar ese registro para una simple máscara. Los valores globales configurados no están disponibles por una API integrada. La línea base de [SP-001](SPEC-TA-005-TA-006-rasterizacion.md) está incorporada como `DEFAULT_RESOLUTION_MM = 5.0` mm/celda en `rasterizer.py`; es el valor inicial de la interfaz propuesto, no una configuración vigente leída de la BD.

## 7. Contrato de dominio TA-005/TA-006/TA-007

Fuentes: [raster_mask.py](../../backend/app/modules/optimization/domain/raster_mask.py), [rasterizer.py](../../backend/app/modules/optimization/domain/rasterizer.py), [placement.py](../../backend/app/modules/optimization/domain/placement.py), [SPEC TA-005/006](SPEC-TA-005-TA-006-rasterizacion.md), [SPEC TA-007](SPEC-TA-007-validacion-geometrica.md).

### 7.1 Piezas y máscaras integradas (#42)

| Entrada pública | Datos | Salida |
|---|---|---|
| `rasterize_geometry(geometry, resolution_mm=5.0)` | Dict con `type`; despacha las tres formas | `RasterMask` |
| `rasterize_rectangle(width_mm, height_mm, resolution_mm=5.0)` | Medidas finitas positivas, mm | Máscara conservadora |
| `rasterize_circle(radius_mm, resolution_mm=5.0)` | Radio finito positivo, mm | Máscara conservadora |
| `rasterize_convex_polygon(vertices_mm, resolution_mm=5.0)` | ≥3 pares finitos; polígono simple convexo validado previamente | Máscara conservadora |

`POLIGONO_CONVEXO` consume directamente `geometry["vertices_mm"]` a través de `_field`; es compatible con la geometría canónica de TA-036. No consume boceto, longitudes ni restricciones angulares del editor.

- Una celda de pieza se ocupa si la figura cubre área positiva de ella; tocar solo una esquina/borde no la ocupa. No es un muestreo por el centro. Una pieza o tramo más delgado que `resolution_mm` no desaparece: ocupa las celdas necesarias según esta regla conservadora.
- Caja trasladada a origen `(0,0)`, fila 0 arriba, Y creciente hacia abajo. Vértices pueden contener coordenadas negativas. El cierre último→primero es implícito.
- Coordenadas normalizadas con redondeo a 6 decimales; tamaños de rejilla por techo de extensión/resolución, con tolerancia interna `1e-9` y mínimo una fila/columna. La extensión de la rejilla puede exceder la geometría.
- `RasterMask` es inmutable: `resolution_mm`, `columns`, `rows` como tupla de enteros de bits. Expone `row_count`, `width_mm`, `height_mm`, `occupied_cells`, `area_mm2`, `row_runs`, `is_occupied` y `to_text`; `from_spans` construye filas por tramos.
- Tipo desconocido, campo ausente, medidas/resolución no finitas o no positivas, vértices mal formados o extensión nula producen `RasterizationError(ValueError)`. Booleanos no se consideran números válidos.
- La biblioteca presupone convexidad/simplicidad ya validada por Orders; no representa una validación completa de polígonos arbitrarios. No se habilita concavidad porque alguna entrada concava no lance excepción.
- No existe tope de filas, columnas, celdas o costo de respuesta en el dominio actual. Debe definirse y aplicarse en la nueva frontera antes de asignar/calcular la máscara.

La RN-07 de SPEC-TA-005/006 recomienda una resolución que no supere la dimensión mínima para reducir el error de área; el código vigente admite figuras más delgadas que una celda y las cubre conservadoramente. **HU-015 reutiliza esta regla sin redefinir la ocupación ni rechazar una pieza por ser delgada.** La UI representa el `RasterMask` producido por backend y no aplica un redondeo visual diferente para calcular celdas.

### 7.2 Material y colocaciones integradas (#43)

`rasterize_material`, `rasterize_material_polygon` y `rasterize_material_circle` aceptan las mismas familias de geometría. La celda material solo es usable si queda completamente dentro de la figura; no se debe mostrar esa máscara como si siguiera la regla conservadora de una pieza.

`SheetLayout.empty(material, margin_mm=0, separation_mm=0)` prepara estado inmutable; `check(piece, row, column)` devuelve `PlacementCheck(is_valid, issue)`; `place` devuelve un nuevo estado o lanza `PlacementError`. Pieza y material requieren la misma resolución. Se comprueban límites de rejilla/material, margen, superposición y separación, en ese orden: `FUERA_DE_LIMITE`, `MARGEN_INSUFICIENTE`, `SUPERPOSICION`, `SEPARACION_INSUFICIENTE`.

Margen y separación son finitos no negativos; se elevan a celdas enteras con tolerancia mediante `distance_in_cells`. Erosión del material y dilatación de ocupación usan vecindad cuadrada, conservadora también en diagonal. No equivalen a distancias euclidianas exactas.

TA-007 se conserva como dependencia de futuras colocaciones. No se muestran controles de margen/separación en una llamada que solo usa `rasterize_geometry`, porque no tendrían efecto.

### 7.3 Cobertura y evidencia existente

Se inspeccionaron, sin ejecutar, `backend/tests/optimization/test_raster_mask.py`, `test_rasterize_standard.py`, `test_rasterize_polygon.py`, `test_rasterize_material.py` y `test_placement.py`: invariantes de máscara, tres formas, entradas inválidas, determinismo/traslación, cobertura conservadora/interior, límites, superposición, margen, separación e inmutabilidad.

`experiments/raster/scripts/raster_evidence.py` y `placement_evidence.py` importan el dominio real y generan evidencia gráfica; no son servicios de aplicación. Hay resultados históricos en `docs/evidence/sprint-01/TA-005-TA-006/` y `TA-007/`. El README de experiments conserva frases de la reserva inicial pese a que ahora existen scripts. No se ejecutaron estos scripts ni se usan sus resultados como pruebas actuales. La aplicación no debe importar `experiments/`.

## 8. Datos de entrada y salida de HU-015

**Propuesta para revisión:** cálculo de una línea de pieza persistida por solicitud, dentro del proceso del pedido ya iniciado y aceptado por backend. La cantidad de esa línea se informa sin duplicar la máscara: Pieza A con `cantidad = 5` produce una sola `RasterMask A`, reutilizable cinco veces en las heurísticas futuras, sin recalcular cinco máscaras idénticas por cantidad. Para ver otra pieza se realiza una nueva selección y solicitud, sin repetir el inicio del pedido. Un cálculo con otra resolución efectiva es una entrada distinta; esta regla no exige persistir máscaras ni un caché entre solicitudes.

| Entrada lógica | Regla |
|---|---|
| `id_pedido`, `id_pieza` | IDs positivos válidos; el servidor comprueba existencia y pertenencia. No confiar solo en el selector UI. |
| Geometría | Leída en backend del pedido persistido, nunca sustituida por coordenadas/dimensiones libres enviadas por el cliente. |
| `resolution_mm` | mm/celda, finito y >0; interfaz iniciada en el `DEFAULT_RESOLUTION_MM` vigente de 5.0. Puede enviarse otra resolución positiva; no se define un conjunto cerrado. Sujeta al límite seguro de recursos. |
| Material, espesor, cantidad | Metadatos de la pieza consultada; no condiciones de stock ni controles de edición. |

El request propuesto contiene **solo** estos campos:

```json
{
  "id_pedido": 41,
  "id_pieza": 7,
  "resolution_mm": 5.0
}
```

Los números son ilustrativos del contrato, no datos observados. El frontend no envía `geometria`, dimensiones ni `vertices_mm` para sustituir los persistidos. El servidor verifica que el pedido y la pieza existan y que la pieza pertenezca al pedido antes de calcular.

La respuesta compacta propuesta debe incluir, como mínimo:

- `id_pedido`, `id_pieza`, `tipo_forma`, `resolution_mm`, `row_count`, `columns` y `occupied_cells`.
- `geometria` efectiva persistida, cantidad y material/espesor como contexto de la pieza; la respuesta permite reproducir el raster con los datos usados, sin depender de un detalle del pedido que pudiera cambiar después.
- `spans_by_row`: una entrada `{ "row": índice, "runs": [...] }` por fila, de arriba abajo. Cada `runs` contiene cero o más pares `[start_col, end_col_exclusive]`, indexados desde cero. Debe haber exactamente `row_count` entradas, con `row` consecutivos desde cero, rangos dentro de `columns` y suma de longitudes igual a `occupied_cells`. Representa la máscara sin pérdida de celdas.
- Convención de origen: caja de la geometría trasladada a `(0,0)` para la máscara, fila 0 arriba, columna 0 a la izquierda e Y creciente hacia abajo. Las dimensiones del contorno original y las de la rejilla se distinguen; la interfaz puede calcular la extensión de la rejilla como `columns × resolution_mm` y `row_count × resolution_mm`.
- Identificación explícita de resultado de **rasterización de pieza**, sin mensajes de factibilidad de material ni optimización completada.

Ejemplo **conceptual** de respuesta; todos sus valores, incluidos filas y celdas, son ilustrativos y no resultados observados. Solo `resolution_mm = 5.0` procede del default vigente:

```json
{
  "id_pedido": 4,
  "id_pieza": 12,
  "tipo_forma": "POLIGONO_CONVEXO",
  "geometria": { "type": "POLIGONO_CONVEXO", "vertices_mm": [[0, 0], [10, 0], [0, 10]] },
  "id_tipo_vidrio": 1,
  "espesor_mm": 4.0,
  "cantidad": 1,
  "resolution_mm": 5.0,
  "row_count": 2,
  "columns": 2,
  "occupied_cells": 3,
  "spans_by_row": [
    { "row": 0, "runs": [[0, 2]] },
    { "row": 1, "runs": [[0, 1]] }
  ]
}
```

`RasterMask.row_runs(row)` devuelve exactamente una `tuple[tuple[int, int], ...]` de tramos `[inicio, fin)` de izquierda a derecha; una fila sin celdas devuelve la tupla vacía. El adaptador solo añade `row` y serializa los pares como listas JSON, sin modificar su semántica. La matriz booleana densa no será el contrato HTTP principal. Los enteros Python de `rows` pueden superar `Number.MAX_SAFE_INTEGER` y las operaciones bit a bit de JavaScript se limitan a 32 bits; los rangos acotados por el límite seguro de rejilla evitan esa pérdida. Las pruebas de contrato deben cubrir más de 53 columnas y una fila vacía cuando corresponda.

## 9. Flujo principal y estados de UI

1. El usuario autorizado abre Optimización/Rasterización desde el sidebar; consultar la pantalla no cambia estados.
2. El sistema carga el listado paginado e identifica los pedidos `PENDIENTE` por ID, cliente, fecha y estado; solo ellos habilitan **«Iniciar optimización»**.
3. Al seleccionar uno, carga su detalle y muestra todas las piezas reales y sus datos; consultar o seleccionar el pedido no cambia su estado.
4. El usuario elige una pieza y una resolución permitida. La geometría original se presenta como referencia; seleccionar pieza o cambiar `resolution_mm` tampoco cambia el estado.
5. El usuario confirma explícitamente **«Iniciar optimización»**. Se indica carga y se bloquea el doble envío. Backend valida autorización, existencia, estado vigente `PENDIENTE`, piezas válidas y parámetros/presupuesto antes de aceptar el inicio.
6. Si falla una precondición, no se inicia el proceso ni se cambia el estado. Si el backend acepta un inicio válido, el pedido pasa **`PENDIENTE → EN_OPTIMIZACION`**, coherentemente con el inicio real del proceso del pedido.
7. Después del inicio aceptado se rasterizan las piezas persistidas mediante solicitudes individuales: backend recupera la pieza, comprueba pertenencia al pedido y al proceso iniciado, valida parámetros/presupuesto y llama al dominio existente. Cada solicitud devuelve una máscara por tipo de pieza persistida, sin duplicarla por cantidad ni generar otra transición.
8. La pantalla identifica el resultado y permite comparar geometría original con máscara, escala/unidades y rejilla. Esto no significa que el pedido esté `OPTIMIZADO` ni `CONFIRMADO`.
9. Al cambiar pieza, pedido o resolución, invalida el resultado anterior como resultado vigente, sin cambiar estados. Otra pieza o resolución del mismo proceso puede calcularse sin repetir el inicio; al seleccionar otro pedido se comprueba su contexto propio. Una respuesta tardía no reemplaza la selección actual.

Este flujo no ejecuta First Fit, Best Fit, Worst Fit ni acomodación automática; tampoco calcula aprovechamiento final, selecciona una solución, consume stock, confirma inventario o alcanza los estados `OPTIMIZADO`/`CONFIRMADO`.

| Estado | Comportamiento visible |
|---|---|
| Cargando pedidos / detalle | Feedback de carga identificable; controles dependientes deshabilitados. |
| Sin pedidos / sin coincidencias | Explicación y posibilidad de recargar o cambiar filtros; no datos de demostración fingidos. |
| Sin pieza seleccionada | Lista real y explicación de qué seleccionar para visualizar su raster; seleccionar no inicia el proceso. |
| Pedido sin piezas / dato inconsistente | Mensaje comprensible e inicio bloqueado, sin transición ni geometría de reemplazo. |
| Parámetro inválido | Error asociado al campo y motivo visible del bloqueo. |
| Iniciando optimización | `loading`, acción «Iniciar optimización» deshabilitada; el estado cambia solo ante aceptación válida del backend. |
| Rasterizando | `loading`, cálculo sin doble envío y contexto de pedido/pieza/resolución en curso; no repite la transición de inicio. |
| Éxito | Contorno y máscara coherentes, identificadores y metadatos efectivos; no métricas heurísticas. |
| Error | Mensaje y acción de recuperación; no máscara inventada ni éxito del resultado anterior. |
| Selección modificada | Resultado anterior retirado o claramente invalidado; nunca rotulado como resultado nuevo. |

## 10. Reglas funcionales y de validación

- **RN-01:** Orders es la fuente de piezas y geometría canónica. Backend obtiene pedido/pieza vigentes por el puerto de Optimization/Application implementado en Optimization/Infrastructure hacia Orders. `POLIGONO_CONVEXO` usa `vertices_mm`; no resolver otra vez lados/ángulos ni aceptar geometría arbitraria del request.
- **RN-02:** Cada cálculo usa una lectura coherente de pieza/pedido. Una pieza retirada o reemplazada desde la selección exige recargar; la respuesta debe identificar la geometría efectiva para evitar presentar un contorno viejo junto a una máscara nueva.
- **RN-03:** Se calcula una máscara de la pieza persistida seleccionada por solicitud y resolución efectiva, dentro del proceso ya iniciado. Una fila PIEZA con `cantidad > 1` representa varias unidades de la misma geometría: se conserva la cantidad como contexto y se reutiliza una única máscara, sin recalcularla por unidad ni rasterizar todo el pedido automáticamente. Su uso repetido por FF/BF/WF pertenece a una etapa posterior.
- **RN-04:** No se consulta disponibilidad de stock para autorizar el registro de un pedido ni este flujo. El inicio válido solo cambia el estado del pedido según RN-12. Rasterizar cada pieza no genera transiciones adicionales, no modifica inventario, no consume ni reserva stock, no crea `Optimizacion` ni ninguna `EjecucionOptimizacion` —incluidas FF/BF/WF— y no persiste el preview raster. No se ejecuta acomodación automática ni se calcula aprovechamiento final o selecciona una solución; HU-015 no marca `OPTIMIZADO` ni `CONFIRMADO`.
- **RN-05:** Backend valida autorización, pertenencia y valores aunque frontend haya validado. Una forma desconocida/inconsistente se rechaza con mensaje comprensible; no se aproxima a rectángulo silenciosamente.
- **RN-06:** La validación de resolución rechaza vacío, cero, negativo, booleano y valor no finito. Antes de construir/serializar una respuesta excesiva, backend estima la rejilla y rechaza solicitudes que superen el máximo seguro de celdas definido mediante benchmark reproducible en el plan técnico. El valor numérico permanece pendiente de esa medición; no se fija arbitrariamente.
- **RN-07:** La interfaz inicia en `DEFAULT_RESOLUTION_MM = 5.0` mm/celda, baseline SP-001, y permite enviar otra resolución positiva. No se limita a un conjunto cerrado, no escribe `Configuracion` ni concede `CONFIGURAR_OPTIMIZADOR`.
- **RN-08:** La UI representa las celdas de `RasterMask` siguiendo la regla conservadora del backend, incluso cuando una pieza o tramo es más delgado que la celda. No aplica redondeo visual distinto. Un cambio de tamaño/zoom de pantalla no altera geometría, resolución ni máscara.
- **RN-09:** No exponer margen, separación, paso angular u otros parámetros que la operación mínima no utiliza.
- **RN-10:** No mostrar un resultado anterior como vigente tras cambiar sus entradas, fallar una solicitud o cerrar sesión. Ignorar/abortar respuestas obsoletas según el patrón existente.
- **RN-11:** El área de una máscara, si se muestra, se identifica como área raster aproximada. No es aprovechamiento, merma ni resultado de una heurística. Su visualización no es obligatoria para este alcance mínimo.
- **RN-12:** Solo un pedido cuyo estado vigente es `PENDIENTE` puede iniciar optimización. Abrir/consultar la pantalla, seleccionar pedido/pieza o cambiar `resolution_mm` no cambia estados. La acción explícita «Iniciar optimización» produce `PENDIENTE → EN_OPTIMIZACION` únicamente si backend valida las precondiciones y acepta el inicio real del proceso del pedido; ninguna máscara individual es dueña de esa transición. Pedido inexistente, no `PENDIENTE`, sin piezas válidas o con error previo de validación se rechaza sin transición. En `EN_OPTIMIZACION` se permiten los cálculos por pieza del proceso aceptado, sin nuevos inicios. No se introducen estados nuevos ni se cubren las transiciones posteriores a `OPTIMIZADO`/`CONFIRMADO`; `CANCELADO` conserva sus reglas existentes.

## 11. API faltante y manejo de errores

No hay endpoint raster en HEAD. **Propuesta para revisión:** `POST /api/optimization/rasterize`, protegido por `EJECUTAR_OPTIMIZACION`, con respuesta `200` para un cálculo exitoso de una pieza. La ruta, request y respuesta de §8 son contratos propuestos, no capacidades existentes.

Se separan conceptualmente dos operaciones:

- **A. Iniciar el proceso de optimización del pedido:** deriva de «Iniciar optimización», valida las precondiciones y, con aceptación válida del backend, realiza `PENDIENTE → EN_OPTIMIZACION` para el pedido. El plan técnico definirá el contrato y la coordinación necesarios para que la transición sea coherente con el inicio real. `POST /api/optimization/start` o un caso de uso equivalente es una **propuesta para el plan técnico**, no un contrato definitivo aprobado; aquí no se prescribe request/response, transacción ni implementación concreta.
- **B. Rasterizar una pieza del pedido:** se mantiene `POST /api/optimization/rasterize` como operación individual del proceso ya iniciado. No inicia implícitamente el pedido ni cambia su estado por cada máscara.

El cuerpo mínimo de B tiene `id_pedido: int`, `id_pieza: int` y `resolution_mm: number`. No admite geometría alternativa ni parámetros de heurísticas. El backend recupera los datos vigentes, comprueba pertenencia y contexto del proceso aceptado en `EN_OPTIMIZACION`, aplica el límite de recursos y llama a `rasterize_geometry`. Responde con los datos efectivos y tramos de §8; no utiliza `201`, no crea `Optimizacion`/`EjecucionOptimizacion`, no persiste preview ni escribe en Orders/Inventory. La transición de A no se delega a estas solicitudes individuales.

Responsabilidades de la implementación propuesta:

| Capa | Responsabilidad |
|---|---|
| `Optimization/Application` | Distingue el inicio del proceso del pedido del cálculo por pieza; define el puerto de lectura de la pieza persistida y comprueba contexto de estado/proceso, pertenencia y parámetros antes de llamar al dominio. La coordinación técnica del inicio y su transición se definirá en el plan técnico. |
| `Optimization/Infrastructure` | Implementa el puerto adaptando el acceso a Orders, sin convertirse en fuente de verdad ni duplicar sus reglas. |
| `Optimization/Domain` | Conserva `RasterMask`, `rasterizer.py` y la validación geométrica existente; no importa FastAPI, SQLAlchemy ni schemas HTTP de Orders. |
| `Optimization/Presentation` | Endpoint, request/response schemas, autorización y traducción de errores de aplicación a HTTP; serializa `row_runs()` según §8. |

Orders conserva pedido, pieza, geometría persistida, material, espesor, cantidad y estado como fuente de verdad. Se conserva su comportamiento de registro; el único cambio de estado cubierto por HU-015 es el inicio válido del proceso del pedido. Los cálculos raster individuales no vuelven a modificar ese estado.

Mapa de errores **propuesto**, siguiendo las convenciones HTTP existentes:

| Situación | Respuesta / recuperación |
|---|---|
| Sin sesión o vencida | `401`; flujo de expiración de sesión actual. |
| Rol sin permiso | `403`; no realizar cálculo. Ocultar la opción no sustituye el control backend. |
| Pedido o pieza inexistente | `404`; recargar listado/detalle. |
| Pieza existente que no pertenece al pedido solicitado | `404` dentro del contexto de ese pedido; no rasterizarla ni revelar datos de otro pedido. |
| Inicio solicitado para pedido existente con estado distinto de `PENDIENTE` | `409` propuesto; recargar el pedido. No iniciar ni cambiar su estado. |
| Inicio solicitado para pedido sin piezas válidas o con validación previa fallida | Rechazo con motivo accionable, sin transición; el contrato de inicio se precisará en el plan técnico. |
| Rasterización individual fuera del contexto de un proceso aceptado en `EN_OPTIMIZACION` | `409` propuesto; recargar el contexto del pedido. No iniciar implícitamente ni cambiar su estado. |
| Resolución no positiva/no finita o geometría persistida no soportada | `422` con motivo seguro y accionable; no sustituir la geometría. |
| Rejilla estimada superior al límite seguro | `422` propuesto, con motivo accionable; rechazar antes de construir/serializar una respuesta excesiva. El número máximo se fijará mediante benchmark. |
| Error inesperado | `500` con mensaje general, sin stack trace ni detalles SQL. |
| Red/timeout o respuesta mal formada | Mensaje de conexión/resultado inválido; permitir reintento explícito, sin presentar éxito. |

Orders no expone actualmente una versión de recurso; su edición reemplaza piezas. El cálculo por pieza relee sus datos al ejecutar y la respuesta incluye la geometría efectiva utilizada. Si el ID seleccionado ya no existe se devuelve `404`; si el pedido dejó de ser `PENDIENTE` antes del inicio, este se rechaza con `409` propuesto. Para cálculos posteriores se valida el contexto del proceso aceptado en `EN_OPTIMIZACION`, sin exigir que el pedido siga `PENDIENTE` ni repetir la transición. No se introduce versionado ni migración en HU-015.

Un fallo previo al inicio no cambia el estado. Un error de rasterización posterior a un inicio aceptado no debe presentarse como optimización completada ni provocar otra transición de inicio. El tratamiento técnico de fallos posteriores, reintentos y coherencia entre aceptación e inicio real se resolverá en el plan técnico; esta SPEC no inventa una reversión automática ni fija mecanismos concretos.

## 12. UI, accesibilidad y arquitectura frontend

Hechos: [App.jsx](../../frontend/src/App.jsx) usa estado y `NavigationContext` para Orders, Inventory y Users. [Sidebar](../../frontend/src/shared/components/Sidebar.jsx) contiene esas tres opciones, sin Optimización para ningún rol. `SessionBar` muestra identidad/rol/sesión. Las carpetas `features/optimization`, `results` y `configuration` solo contienen `.gitkeep`; no hay visor ni servicio raster integrado. El SVG del editor de piezas no es un rasterizador.

Las llamadas actuales usan `fetch`, sesión existente y [shared/apiUrl.js](../../frontend/src/shared/apiUrl.js), con `VITE_API_URL`; en modo staging exige esa variable y en desarrollo puede usar `http://127.0.0.1:8000`. Se conserva ese mecanismo. `ordersApi.js` ya acepta señal de cancelación, token y errores legibles.

Reutilizar `AppShell`, `Sidebar`, `PageHeader`, `PageCard`, `ActionBar`, tokens visuales y componentes `LoadingState`, `EmptyState`, `FeedbackMessage`, `FieldError` cuando correspondan. [Feedback compartido](../ui-ux/feedback-compartido.md) y [base visual](../ui-ux/inventario-base-visual.md) definen el lenguaje existente. El patrón de gestión abre formularios bajo acción; HU-015 mantiene selección/listado inicial, sin forzar un CRUD ni duplicar `useManagementView` para un caso diferente.

- Sidebar como navegación principal; header para identidad/sesión. Mantener navegación por estado, sin introducir React Router.
- Desktop-first y responsive: selección, controles y resultado siguen utilizables en ancho reducido; un viewport desplazable de la rejilla debe estar claramente delimitado y ser operable.
- Labels y unidades explícitos, navegación por teclado, foco visible y estados de controles comprensibles; error de campo con `aria-invalid`/`aria-describedby`, cargas y resultados anunciados, errores con `role="alert"` conforme al patrón compartido.
- No depender solo de color para distinguir contorno/celdas; leyenda, contraste y resumen textual accesible con pieza, forma, resolución y dimensiones. No crear un foco por cada celda.
- La representación debe permitir comparar la geometría original persistida y la máscara en la misma escala o con correspondencia explícita entre ambas vistas, sin deformar la proporción física. Mostrar tipo de forma, dimensiones relevantes, resolución, filas, columnas y celdas ocupadas. No presentar colocación automática, heurísticas, aprovechamiento, merma ni stock consumido.

Evaluación para el plan posterior: Canvas reduce nodos al representar muchas celdas, pero necesita alternativa textual y manejo de escala; SVG facilita contornos/etiquetas, pero requiere controlar el número de elementos; CSS grid/matriz DOM es legible con rejillas pequeñas, pero puede crecer excesivamente. La SPEC no prescribe tecnología; la decisión dependerá de los límites aprobados, accesibilidad y tamaño real de máscara. Renderizar datos del servidor no equivale a calcular el raster en React.

## 13. Criterios de aceptación verificables

Estos criterios describen el comportamiento objetivo de la **Propuesta para revisión**; no son resultados de pruebas ni criterios recuperados literalmente del backlog. Solo el valor numérico del límite seguro requiere medición antes de implementar.

| CA | Dado / Cuando / Entonces |
|---|---|
| CA-01 | Dado un Administrador u Operario autenticado, cuando abre/consulta la opción raster y selecciona pedido, pieza o cambia `resolution_mm`, entonces no cambia ningún estado. Solo un pedido `PENDIENTE` persistido habilita «Iniciar optimización»; los demás estados no permiten un nuevo inicio, también por solicitud directa al backend. El listado conserva identificación y paginación de Orders. |
| CA-02 | Dado un pedido seleccionado, cuando termina la carga de detalle, entonces se muestran todas sus líneas de piezas con ID, forma, datos geométricos, cantidad, material y espesor, sin inventar piezas ni un material único para un pedido multimaterial. |
| CA-03 | Dada una pieza de cualquiera de las tres formas dentro de un proceso de pedido ya iniciado y aceptado, cuando se solicita `POST /api/optimization/rasterize`, entonces backend recupera su `geometria` persistida de Orders mediante el puerto de Optimization/Application; para polígono usa los `vertices_mm` originales y no acepta una geometría sustituta del cliente. Cada llamada individual calcula la pieza sin iniciar implícitamente el pedido ni repetir la transición a `EN_OPTIMIZACION`. |
| CA-04 | Dada una fila PIEZA con cantidad N > 1, cuando se calcula/visualiza su raster para una geometría y resolución efectivas, entonces se rasteriza una sola vez por tipo de pieza persistida y se conserva N como contexto, sin recalcular N máscaras idénticas por cantidad. Pieza A con `cantidad = 5` produce una `RasterMask A`, reutilizable cinco veces por FF/BF/WF en una etapa futura, sin afirmar colocación ni consumo actuales; las demás piezas no se rasterizan en esa solicitud. |
| CA-05 | Dada `resolution_mm` vacía, igual a cero, negativa, no finita o booleana, cuando se intenta ejecutar, entonces UI informa el error y bloquea el envío; backend rechaza también la solicitud directa con valor inválido. |
| CA-06 | Dada una resolución que produciría una rejilla superior al máximo seguro de celdas definido por benchmark, cuando llega al servicio, entonces backend rechaza antes de construir/serializar una respuesta excesiva y explica cómo corregirla. Verificar el límite y el valor inmediatamente superior. |
| CA-07 | Dada una solicitud de inicio o cálculo por pieza en curso, cuando se vuelve a activar su acción, entonces no se emite una segunda solicitud y se mantiene visible el estado de carga. Tras un inicio aceptado, rasterizar otra pieza no repite «Iniciar optimización» ni su transición. |
| CA-08 | Dada respuesta válida, cuando se muestra, entonces aparecen pedido/pieza, tipo de forma, dimensiones relevantes, resolución efectiva, filas, columnas, celdas ocupadas y geometría original comparable con la máscara backend, con unidades y escala identificables. |
| CA-09 | Dada una pieza rectangular persistida de 800×600 mm a la resolución inicial de 5 mm/celda, cuando se rasteriza, entonces se muestran 160 columnas, 120 filas y 19 200 celdas ocupadas. Dada una pieza de 1×10 mm a la misma resolución, entonces conserva 1 columna y 2 filas ocupadas; la UI no aplica otro redondeo a la máscara. |
| CA-10 | Dado un polígono con coordenadas negativas y una máscara de más de 53 columnas, cuando se serializa en `spans_by_row` con pares `[start_col, end_col_exclusive]` y se visualiza, entonces reconstruir sus celdas coincide con `RasterMask`, sin perder celdas ni modificar la geometría persistida. |
| CA-11 | Dado un cambio de pedido, pieza o resolución durante/después de una solicitud, cuando llega una respuesta anterior, entonces no se presenta como resultado de la selección vigente. |
| CA-12 | Dado fallo HTTP, de red o respuesta mal formada, cuando finaliza la solicitud, entonces se muestra un mensaje accionable sin stack trace, se permite recuperación y no se fabrica un raster exitoso. |
| CA-13 | Dado un listado sin pedidos `PENDIENTE` o un pedido elegible sin piezas válidas, cuando se carga, entonces se distingue el estado vacío/inconsistente y no se habilita iniciar sin piezas válidas; backend rechaza también el inicio directo de un pedido sin piezas válidas sin cambiar su estado. |
| CA-14 | Dado un pedido válido con inventario sin stock compatible, cuando se crea mediante el flujo existente, se inicia explícitamente su proceso y luego se rasteriza una pieza, entonces la ausencia de stock no bloquea ninguna de esas operaciones. |
| CA-15 | Dado un pedido `PENDIENTE`, cuando el usuario confirma explícitamente «Iniciar optimización» y backend valida y acepta el inicio real del proceso, entonces el pedido pasa a `EN_OPTIMIZACION` antes de rasterizar sus piezas. Si falla una precondición previa —pedido inexistente, no `PENDIENTE`, sin piezas válidas o error de validación—, entonces no se inicia ni se cambia el estado. La transición corresponde al pedido completo; los cálculos individuales no la repiten. En el flujo, exitoso o fallido, no cambian cantidad/estado de planchas o retazos ni movimientos de inventario, ni se consume stock. |
| CA-16 | Dado un Almacenero o una sesión ausente/vencida, cuando intenta iniciar el proceso o calcular una pieza por solicitud directa, entonces backend rechaza con 403/401 respectivamente; la UI no concede la operación por ocultamiento visual solamente y un inicio no autorizado no cambia el estado. |
| CA-17 | Dada una pieza reemplazada o una selección desactualizada, cuando se solicita, entonces se rechaza/recarga según el contrato y no se combina una máscara nueva con un contorno antiguo. |
| CA-18 | Dado uso por teclado o viewport reducido, cuando se recorre el flujo, entonces se accede a selección, parámetros y acción con foco visible, labels/unidades y feedback anunciado; se conserva un resumen textual del resultado. |
| CA-19 | Dada una ejecución repetida con la misma geometría persistida y resolución efectiva, cuando se consulta el resultado, entonces coinciden `row_count`, `columns`, `occupied_cells` y cada rango de `spans_by_row`; la respuesta identifica la geometría utilizada y no exige historial persistido. |
| CA-20 | Dado el inicio del proceso y una rasterización exitosa o fallida, cuando se consultan los datos antes/después, entonces no se crea `Optimizacion`, ninguna `EjecucionOptimizacion` —incluidas FF/BF/WF—, métrica ni preview raster persistido; no se ejecutan heurísticas/acomodación automática, no se calcula aprovechamiento final, no se selecciona solución ni se confirma inventario y no se marca el pedido `OPTIMIZADO` ni `CONFIRMADO`. |
| CA-21 | Dado un `id_pieza` inexistente, cuando se solicita rasterizarlo, entonces backend responde `404` y no calcula una máscara. |
| CA-22 | Dada una pieza existente que pertenece a otro `id_pedido`, cuando se solicita con el pedido seleccionado, entonces backend responde `404`, no calcula la máscara y no devuelve la geometría ajena. |
| CA-23 | Dada una geometría persistida con `type` no soportado o datos incompatibles, cuando se solicita, entonces backend responde `422` con mensaje comprensible sin stack trace, no sustituye la forma ni muestra un raster como éxito. |

## 14. Estrategia de pruebas prevista

No se ejecutan ni crean pruebas en esta tarea documental. Los resultados históricos del repositorio no se presentan como validación de HU-015.

| Nivel | Cobertura futura y propósito |
|---|---|
| Unitarias frontend | Solo lógica nueva aislable: adaptación de DTO, unidades/etiquetas, validación de parámetros y representación sin pérdida. No replicar rasterización ni tests del editor geométrico. |
| Componentes | Selector paginado y detalle real representado por fixtures de contrato; estados vacío/loading/error/success, parámetros, bloqueo de doble envío, cambio de selección y respuesta tardía, máscara/leyenda/resumen accesible, roles y ancho reducido. Los mocks no demuestran integración backend. |
| API / integración | Inicio explícito: solo `PENDIENTE`, transición válida a `EN_OPTIMIZACION` y ninguna transición ante errores previos. `POST /api/optimization/rasterize` propuesto dentro del proceso aceptado: autorización, pieza ausente/ajena, lectura de pedido persistido mediante puerto de Optimization/Application, geometría efectiva, tres formas, geometría no soportada, rangos por fila y >53 columnas, resolución inválida, presupuesto antes del cálculo, cantidad > 1 sin máscaras duplicadas y ausencia de transiciones repetidas/escrituras raster o de inventario. Recursos de prueba locales/controlados. |
| Unitarias backend | Solo nueva orquestación, validación de presupuesto y serialización; reutilizar la cobertura existente de TA-005/006/007 como regresión, sin duplicar todos sus casos. |
| Regresión | Preservar creación de pedido sin stock, contratos de detalle/material y navegación/roles existentes; evaluar pruebas focalizadas y lint/build según los archivos que realmente cambien. |
| E2E posterior | Flujo crítico estabilizado: pedido persistido local `PENDIENTE` → selección/consulta sin cambio de estado → «Iniciar optimización» → validación/aceptación → `EN_OPTIMIZACION` → rasterización backend por pieza → resultado visible. No declarar E2E completo con solo construcción de UI o respuestas simuladas. |

Comandos existentes de referencia, no ejecutados aquí: desde `frontend/`, `npm run test:unit`, `npm run test:component`, `npm run lint`, `npm run build`; `npm run test:e2e` solo con flujo y entorno preparados. Desde `backend/`, `python -m pytest -q tests/optimization` y selección de pruebas API/unidad correspondientes a la futura implementación. La selección exacta se hará cuando existan cambios; no se define un comando para un archivo HU-015 todavía inexistente.

## 15. Evidencias futuras requeridas

- Código real de la conexión pedido→dominio y de la presentación del resultado, con archivo/fragmento/commit identificables.
- Terminal con comandos y resultados reales de pruebas, duración y contexto; separar resultados actuales de antecedentes.
- API local si se implementa el adaptador: solicitud/respuesta raster, identificadores, resolución, rejilla, autorización y rechazo de entrada inválida, sin credenciales.
- Frontend ejecutado **localmente**: selección de pedido real, piezas, estados, comparación original/máscara y resultado reproducible para las tres formas.
- Error real, diagnóstico, corrección y verificación si aparece durante implementación; no fabricar un fallo para completar una narrativa.
- Verificación del inicio explícito y la transición válida `PENDIENTE → EN_OPTIMIZACION`, sin cambio por consulta ni errores previos, sin transiciones por máscara, sin ejecuciones FF/BF/WF ni descuento de inventario y sin alcanzar `OPTIMIZADO`/`CONFIRMADO`.

No se generan capturas ahora. `NewGlass-Notion` queda intacta y se reserva exclusivamente para futuras capturas reales; no se guardarán allí Markdown, logs, scripts, resultados ni índices. La documentación/evidencia técnica futura seguirá las convenciones de `docs/evidence/` del repositorio. En capturas y outputs no mostrar contraseñas, JWT, Authorization, cookies, cadenas de conexión ni tokens.

## 16. Decisiones cerradas y pendientes materiales

La definición funcional queda aprobada tras revisión humana: solo un pedido `PENDIENTE` puede iniciar optimización mediante acción explícita y aceptación válida del backend, pasando a `EN_OPTIMIZACION` para el pedido completo. Abrir/consultar, seleccionar o cambiar resolución no cambia estados; un error previo al inicio tampoco. Después se rasteriza una pieza persistida por solicitud mediante `POST /api/optimization/rasterize`, sin repetir la transición ni duplicar máscaras por `cantidad > 1`. Se conservan geometría obtenida de Orders mediante el puerto de Optimization/Application y su adaptador de Infrastructure; respuesta sin pérdida por `spans_by_row`, derivada de `RasterMask.row_runs()`; resolución inicial 5.0 mm/celda y cualquier otro valor positivo dentro del presupuesto; ocupación conservadora incluso para tramos más delgados que una celda; autorización de Administrador/Operario. No hay consumo de stock, persistencia de optimización/ejecución/preview, FF/BF/WF ni avance a `OPTIMIZADO`/`CONFIRMADO`. La capa Presentation define el contrato HTTP y Domain conserva la semántica geométrica.

Permanecen **tres pendientes materiales**:

| ID | Pendiente | Cierre requerido |
|---|---|---|
| P-01 | Valor numérico del máximo seguro de celdas raster. | El plan técnico incluirá un benchmark reproducible con tamaños de entrada, resolución, costo de cálculo y tamaño de respuesta; a partir de él se fijará el límite antes de implementar el endpoint. No se asigna un número arbitrario. |
| P-02 | La división original T1/T2/T3 no fue encontrada en las fuentes auditadas. | Recuperarla si existe. Esto no bloquea la definición funcional; un plan/tasks posterior podrá introducir una **«Descomposición técnica propuesta»**, sin presentarla como backlog histórico. |
| P-03 | Diseño técnico del inicio del proceso y su transición, separado del cálculo por pieza. | El plan técnico resolverá el contrato de inicio (`POST /api/optimization/start` o caso de uso equivalente, aún no aprobado), la coherencia entre inicio real y transición, y el tratamiento de fallos posteriores/reintentos. Si requiere transacción o caso de uso específico, se definirá allí; no se fija implementación concreta en esta SPEC. |

Riesgos conocidos que no abren otra decisión funcional de HU-015: HU-008 sigue fuera de la línea integrada y contradice el registro sin stock; ADR-002 §2.4 conserva esa regla histórica; los datos persistidos incompatibles se rechazan con `422`; la UI deberá preservar escala y accesibilidad al representar rejillas grandes. La elección de Canvas/SVG u otra técnica de dibujo pertenece al plan de implementación, conservando el contrato de resultado y el presupuesto fijado por P-01.

Estado histórico de la entrega de definición del 13/10/2026: **Reviewed** tras la revisión humana de Fabricio Aguilar, aprobado para implementación / planificación técnica. En esa entrega no se agregaron migraciones, dependencias, rutas ejecutables, código frontend/backend, plan ni tareas. El cierre posterior consta en §17.

## 17. Cierre verificado de HU-015 — 14/10/2026

**Resultado:** implementación revisada, aprobada e integrada mediante [PR #47](https://github.com/melendezzz26/optimizador-vidrio/pull/47), desde `feature/HU-015-interfaz-rasterizacion` hacia `integration/sprint-01`. Reviewer: **Fabricio Danniel Aguilar Chávez**. La aprobación humana se registra conforme a la confirmación expresa del equipo para este cierre.

Git y los metadatos públicos de GitHub confirman el merge `86972fd779bae826909a401874f06d5b7dd2a3ed`, realizado el **14/10/2026 a las 06:30:23 de Lima** (timestamp `merged_at` de GitHub). Su segundo padre es la punta publicada `a4146551dcec4e5e46a77f803b4f378dbe21a4cd`; el commit está incorporado en `origin/integration/sprint-01`. La implementación corresponde a T1 `0650450`, T2 `72bd2d7`, T3 `2f70ee1` y fix de colección CI `a414655`. La comparación del código frontend/backend entre esa punta y el merge no presenta diferencias.

### 17.1 Validación y trazabilidad

- [T1 — backend](../evidence/sprint-01/HU-015/t1-backend.md): focalizada final **100 passed, 1 warning, 0 skipped**; concurrencia PostgreSQL, CAS/rollback, permisos, contratos y ausencia de escrituras excluidas. Regresión completa histórica **1564 passed, 1 warning**, con posterior validación focalizada de los cambios finales; no se presenta como una nueva corrida completa.
- [Benchmark y política técnica](../evidence/sprint-01/HU-015/benchmark-limite.md): mediciones reproducibles y presupuesto aplicado antes del cálculo/serialización. P-01 queda concretado en políticas técnicas de protección, sin convertirlas en restricciones funcionales nuevas del negocio.
- [T2 — interfaz](../evidence/sprint-01/HU-015/t2-frontend.md): selección, permisos, Orders, start 200/409, reconciliación incierta, recuperación, errores y cantidad como atributo; regresión Orders **101 passed**.
- [T3 — visualización/E2E](../evidence/sprint-01/HU-015/t3-visualizacion-e2e.md): **70 focalizadas, 124 unitarias, 296 componentes**, lint/build PASS; **6 E2E reales post-fix, 0 failed, 0 skipped, 0 flaky**, Playwright 1.63.0 / Chromium 153.0.8010.12 contra Supabase de pruebas, con fixtures limpiados. La corrección de escala `resolution_mm × pixels_per_mm` tiene regresión de componente y validación real posterior. Los seis E2E no incluyen 409, cubierto por T1/T2.
- [CI del PR #47](https://github.com/melendezzz26/optimizador-vidrio/actions/runs/38556535398): checks **backend, frontend y e2e completados con success**, consultados para este cierre. HU-015 real E2E se omite expresamente si faltan sus credenciales externas; un skip de CI no se cuenta como PASS del flujo HU-015. Su corrida real está respaldada por la evidencia T3 separada.
- Evidencia visual local complementaria: **16 PNG T1, 8 PNG T2 y 9 PNG T3** bajo la estructura NewGlass-Notion; no forma parte del commit documental ni sustituye las pruebas.

La matriz siguiente contrasta los criterios originales de §13 con el código y pruebas integrados. No atribuye todos los criterios a los seis E2E.

| CA | Resultado | Evidencia principal |
|---|---|---|
| CA-01 | Cumple | Filtros/paginación y selección sin transición en T2; estados rechazados en API T1. |
| CA-02 | Cumple | Detalle persistido y filas por pieza/material en componentes T2 y E2E T3. |
| CA-03 | Cumple | Casos de uso/puerto Orders y API de tres formas T1; rechazo de geometría enviada por cliente. |
| CA-04 | Cumple | Unit T1 comprueba una llamada para cantidad 5; componentes/E2E muestran una máscara y cantidad. |
| CA-05 | Cumple | Schemas/API T1 y validación finita positiva de UI T2. |
| CA-06 | Cumple | Benchmark, preflight y pruebas de límite/inmediatamente superior T1; 422/retry real T3. |
| CA-07 | Cumple | Doble envío/loading en componentes T2; E2E recupera y rasteriza sin otro start. |
| CA-08 | Cumple | Resumen y previews SVG/Canvas; regresión matemática de escala y E2E/PNG post-fix T3. |
| CA-09 | Cumple | E2E T3 verifica 800×600 a 5: 160×120/19 200; pieza 1×10: 1×2. |
| CA-10 | Cumple | Serialización lossless >53 bits y filas vacías T1; spans end-exclusive T3 y polígono negativo E2E. |
| CA-11 | Cumple | Pruebas de respuestas tardías y cambios de pedido/pieza/resolución T2. |
| CA-12 | Cumple | Errores seguros API/transporte T1/T2 y 422/retry real T3. |
| CA-13 | Cumple | Empty/inconsistencia en componentes T2; inicio inválido con rollback T1. |
| CA-14 | Cumple | API crea/inicia/rasteriza sin stock en T1; fixtures E2E T3 sin stock. |
| CA-15 | Cumple | CAS/transacción y carreras PostgreSQL T1; start explícito, validación y ausencia de escrituras de inventario. |
| CA-16 | Cumple | API 401/403 y rol vigente T1; navegación/permiso T2. |
| CA-17 | Cumple | Relectura de piezas/contexto T2 y uso de geometría efectiva de la respuesta T3; 404 API T1. |
| CA-18 | Cumple | Labels/resumen textual en componentes T3; teclado/foco y viewports 1440/1024/800 en E2E real. |
| CA-19 | Cumple | Determinismo del dominio (`test_same_input_gives_same_mask`) y serialización fiel T1; geometría efectiva identificada. No se atribuye un test repetido de endpoint a T3. |
| CA-20 | Cumple | API/integración T1 verifica ausencia de optimizaciones/ejecuciones/métricas/inventario; cleanup E2E. |
| CA-21 | Cumple | API T1 devuelve 404 para pieza inexistente sin rasterizar. |
| CA-22 | Cumple | API T1 devuelve 404 para pieza ajena sin revelar geometría. |
| CA-23 | Cumple | Geometría corrupta/no soportada produce 422 seguro en API T1. |

### 17.2 Cierre de pendientes y límites conservados

P-02 no se transforma retrospectivamente en un backlog histórico recuperado: la división T1/T2/T3 se concretó en el PLAN aprobado y su implementación. P-03 queda resuelto mediante start explícito, CAS/validación/commit o rollback en Orders y cálculos individuales sin transición, con pruebas de concurrencia y reconciliación. PLAN permanece **Approved**, sin modificaciones en este cierre; no se crea ni modifica TASKS.

Se conservan las limitaciones declaradas: presupuestos técnicos conservadores de recursos, medición local sin garantía de SLA/RSS y defecto de redondeo preexistente del dominio para ciertos radios fraccionarios, tratado con 422 seguro y registrado en T1 para seguimiento separado. No se amplía el alcance a FF/BF/WF, stock compatible, placement, aprovechamiento, merma ni confirmación de solución. No se afirma certificación WCAG. No hay pruebas obligatorias fallidas registradas en la validación final ni bloqueantes de HU-015 pendientes para este cierre aprobado.

## Historial de estado

- 13/10/2026 — **Draft**: auditoría de `728c1dd` y referencias remotas después de fetch; alcance recuperado de ADR-002 y propuesta delimitada. Sin pruebas ejecutadas de HU-015, implementación ni validación funcional nueva.
- 13/10/2026 — **Draft**: revisión de decisiones propuestas sobre unidad por pieza, fuente persistida, `POST /api/optimization/rasterize`, respuesta por rangos, resolución, roles y criterios de aceptación. Pendiente de revisión humana.
- 13/10/2026 — **Draft**: precisión final de ocupación conservadora, estado `PENDIENTE`, propiedad de capas y esquema por filas; quedan P-01 y P-02 para el equipo.
- 13/10/2026 — **Draft**: ajuste final de estados: inicio explícito válido `PENDIENTE → EN_OPTIMIZACION`, separado de rasterización por pieza y sin transición por consulta o error previo; una máscara por tipo de pieza persistida sin duplicar por cantidad. Se conservan 23 criterios de aceptación y se añade P-03 para el plan técnico. Esta regla sustituye la decisión anterior de mantener el pedido `PENDIENTE` al iniciar el proceso. Sin implementación ni pruebas ejecutadas.
- 13/10/2026 — **Reviewed**: revisión humana completada por **Fabricio Aguilar**; decisiones funcionales aprobadas para implementación / planificación técnica. Autor: Fabricio Melendez. Se aprueba el flujo `PENDIENTE → Iniciar optimización → EN_OPTIMIZACION → rasterización por pieza`, con validación y aceptación del backend antes de la transición; una máscara por geometría persistida, reutilizable según cantidad. HU-015 no ejecuta todavía FF/BF/WF, no consume stock ni alcanza los estados `OPTIMIZADO`/`CONFIRMADO`. Se conservan los 23 criterios de aceptación y los pendientes materiales. Sin implementación ni verificación funcional de HU-015 en este cierre.
- 14/10/2026 — **Verified**: cierre formal **Reviewed → Verified** autorizado tras revisión humana aprobada por **Fabricio Danniel Aguilar Chávez**, confirmada por el equipo, e integración del [PR #47](https://github.com/melendezzz26/optimizador-vidrio/pull/47) en `86972fd779bae826909a401874f06d5b7dd2a3ed`, desde la feature `a4146551dcec4e5e46a77f803b4f378dbe21a4cd`. Los 23 CA tienen evidencia de implementación/pruebas conforme a §17; checks del PR backend/frontend/e2e exitosos y E2E real HU-015 respaldado separadamente. Únicamente documentación: sin nueva ejecución de pruebas, cambios de código, PLAN/TASKS ni deploy.
