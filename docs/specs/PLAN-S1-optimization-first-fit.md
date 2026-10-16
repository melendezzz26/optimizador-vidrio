# PLAN-S1 — Optimization First Fit

## Información general

| Campo | Valor |
|---|---|
| Estado del plan | **Approved** |
| SPEC de referencia | [SPEC-S1-optimization-first-fit.md](SPEC-S1-optimization-first-fit.md), **Reviewed** |
| Autor de la SPEC y del plan | Fabricio Melendez |
| Reviewer de la SPEC | Fabricio Danniel Aguilar Chávez |
| Revisión humana de la SPEC | 16/10/2026; aprobada para implementación / planificación técnica |
| Reviewer del plan | Fabricio Danniel Aguilar Chávez |
| Fecha de revisión/aprobación del plan | 16/10/2026 |
| Decisión del plan | Aprobado para implementación. |
| Base auditada | `cf84d7314985b33e593dec6505c06d7767e87b99` (HEAD local de `feature/S1-optimization-core`) |
| Rama | `feature/S1-optimization-core` |
| Base de integración | `integration/sprint-01` |
| Fecha de planificación | 16/10/2026 |

Este PLAN convierte la SPEC Reviewed en trabajo ejecutable de backend/core. Fabricio Danniel Aguilar Chávez lo aprobó técnicamente para implementación el 16/10/2026. La aprobación del PLAN es independiente del estado Reviewed de la SPEC y no afirma que se haya implementado código ni ejecutado pruebas de producto.

## 1. Objetivo y convención documental

Entregar una ruta backend única que seleccione pedidos explícitamente, normalice sus piezas, agrupe por material, consulte stock compatible, ejecute First Fit con validación raster, emita progreso durante el cálculo, persista un patrón reconstruible y confirme el lote con una única transacción de inventario.

La auditoría de `docs/specs/` encontró PLANs en archivos planos. `PLAN-HU-015-interfaz-rasterizacion.md` y `PLAN-TA-DASHBOARD-001-dashboard-inicial.md` alojan las tareas dentro del propio PLAN; no se encontró un `TASKS.md` separado para esta convención. Este documento conserva ese formato y concentra sus tareas en §17. No se crea un documento adicional de TASKS.

La salida prioritaria es un vertical slice comprobable con un pedido y un grupo material a través del mismo flujo general de `1..N`. Después se completa la matriz obligatoria multipedido y multimaterial sin crear un segundo motor o una ruta especial para N=1.

## 2. Auditoría técnica de la base actual

Los hallazgos de esta tabla son hechos de la rama auditada; las columnas de diseño posteriores describen trabajo futuro.

| Fuente auditada | Estado comprobado y consecuencia |
|---|---|
| [ADR-001](../adr/ADR-001-seleccion-arquitectura.md), [ADR-002](../adr/ADR-002-operacion-pre-raster.md), [CONTRIBUTING.md](../../CONTRIBUTING.md) | Monolito modular con Clean Architecture. El dominio no importa FastAPI, SQLAlchemy, Supabase o React; Application define puertos y orquesta; Infrastructure adapta persistencia/servicios; Presentation traduce HTTP y permisos. ADR-002 §2.11 mantiene FF/BF/WF como trabajo posterior en Sprint 2. La SPEC adelanta únicamente FF por la corrección posterior de alcance de Sprint 1; ADR-002 queda intacto y su trazabilidad deberá actualizarse después. |
| [PLAN HU-015](PLAN-HU-015-interfaz-rasterizacion.md), [PLAN Dashboard](PLAN-TA-DASHBOARD-001-dashboard-inicial.md), [SPEC HU-015](SPEC-HU-015-interfaz-rasterizacion.md) | Los PLANs guardan TASKS dentro del documento; HU-015 conserva alcance histórico de inicio/rasterización y no contiene First Fit, confirmación ni mutación de inventario. Este PLAN mantiene HU-015 intacta. |
| `backend/app/modules/optimization/` | Existe `StartOptimizationUseCase` para un pedido y rasterización de una pieza; el port Orders es escalar. `RasterMask`, `rasterize_geometry`, `rasterize_material`, `SheetLayout.check/place` y `RasterBudget` ya existen. No hay búsqueda de posiciones, rotaciones, First Fit, grupos, progreso, resultado persistido, stock compatible ni confirmación. Reutilizar los límites de raster existentes y comprobar que cubran el lote/rotación; no fijar presupuestos nuevos por intuición. |
| `backend/app/modules/orders/` y `backend/app/models.py` (`Pedido`, `Pieza`) | Cada `Pieza` guarda `id_pedido`, `id_tipo_vidrio`, `espesor_mm`, `cantidad`, geometría y `area_mm2`; el material efectivo está por pieza y admite pedidos multimaterial. Orders devuelve piezas persistidas, pero el port actual de inicio cambia estado de un pedido por llamada con su propia transacción. No sirve para un lote atómico. La otra rama es responsable del flujo general de Orders/material; este core necesitará un contrato batch transaccional de integración. |
| `backend/app/modules/inventory/` | `Plancha` tiene `cantidad`, dimensiones, tipo, espesor y estado; `Retazo` representa una unidad con geometría, área, tipo, espesor y estado. Los repositorios listan activos e inactivos y ordenan por disponibilidad, fecha e ID. Hay locks y movimientos para operaciones existentes, pero el repositorio/servicio administra su propia sesión y commit; no puede invocarse desde confirmación como una transacción anidada. No hay consulta de stock compatible ni consumo coordinado con Orders. |
| `backend/app/models.py`, R3/R4, [Diseño de BD](../database/convergencia-v1-1.md), [convergencia de Orders multimaterial](../database/convergencia-orders-multimaterial.md) | `Optimizacion` (`optimizaciones`) guarda un único `id_pedido NOT NULL`; `EjecucionOptimizacion` ya admite `FF`, `BF`, `WF` y una fila por método/optimización; `MaterialUtilizado` XOR plancha/retazo modela propuestas por ejecución, no consume stock; `MetricaEjecucion` tiene las cinco métricas R4. `Configuracion` tiene resolución, margen, separación, paso angular nullable y mínimos de ancho/alto para retazo; no contiene mínimo de área. |
| `backend/alembic/versions/` | El grafo auditado es una cadena lineal, con una sola punta local `ta036a1b2c3d` (`TA-036`), descendiente de R4, R3, R2, Orders multimaterial y R1. La revisión nueva debe descender de esa punta y comprobar que el grafo siga teniendo una sola head. No se necesita una merge revision según el grafo local actual. |
| Dominio geométrico y [SPEC-TA-007](SPEC-TA-007-validacion-geometrica.md) | `rasterize_material` crea celdas interiores al material; `SheetLayout` aplica límite, margen, superposición y separación sobre resolución compartida. No rota ni enumera posiciones automáticamente. El raster conservador permite validar material irregular sin tratar AABB como decisión de colocación. |
| Configuración y persistencia | La tabla `configuraciones` existe, pero `backend/app/modules/configuration/` no ofrece actualmente un proveedor de snapshot de corrida. `paso_angular_grados` admite NULL aunque tiene un CHECK positivo cuando no es NULL; hay que rechazar una configuración incompleta antes de iniciar pedidos. |
| API y autorización | Se conservan `POST /api/optimization/start` (un `id_pedido`) y `POST /api/optimization/rasterize` por compatibilidad HU-015. Usan el permiso existente `EJECUTAR_OPTIMIZACION`. No se debe asumir integrada la rama RBAC dinámica ni cambiar estos contratos arbitrariamente. |
| [Estrategia de pruebas](../testing/README.md) y `backend/tests/` | Domain: `backend/tests/optimization/`; use cases y serialización: `backend/tests/unit/optimization/`; API: `backend/tests/api/optimization/`; PostgreSQL: `backend/tests/integration/optimization/` y `backend/tests/integration/`. Hay pruebas HU-015 de inicio concurrente y regresión de Orders/Inventory. No se declara ningún resultado nuevo por esta auditoría. |
| Paquetes geométricos | `backend/requirements.txt` no incluye Shapely ni otra librería de operaciones booleanas poligonales. El plan no requiere una dependencia geométrica nueva: las decisiones de residual se limitan a rectángulos exactos obtenidos de celdas interiores completas del raster. |

## 3. Alcance de esta rama y puntos de integración

### `feature/S1-optimization-core` implementa

- Dominio Optimization: normalización de problema, unidades, agrupación, preparación, rotaciones discretas, raster/caché de corrida, enumeración row-major, First Fit, validación de placement, métricas y cálculo conservador de sobrante recuperable.
- Application Optimization: validación atómica de selección, configuración efectiva, puertos batch/stock/persistencia/transacción, orquestación, progreso, estados, resultado y caso de uso de confirmación.
- Infrastructure Optimization: adaptadores a modelos compartidos y sesión PostgreSQL; migración/modelo ORM multipedido; persistencia FF; stock compatible; locks, movimientos y consumos dentro de la misma unidad de trabajo.
- Presentation Optimization: schemas y rutas nuevos, autenticación/autorización adaptada a permisos vigentes, NDJSON y mapeo seguro de errores.
- Pruebas de Domain, Application, API, integración PostgreSQL, migración, concurrencia y regresión del core.

### Otras ramas y responsabilidades

| Integración | Contrato que este core necesita | Trabajo fuera de esta rama |
|---|---|---|
| `feature/S1-optimization-ui` | En T1 recibe request, eventos NDJSON v1, DTO de resultado, respuesta de confirmación y errores congelados. La ruta nueva transmite progreso real y ofrece lectura durable del resultado. | React, selección visual de pedidos, lectura del stream, patrón y métricas, experiencia de confirmación y E2E de UI. No se modifica frontend aquí. |
| Rama Orders/material flow | Port backend batch que entrega pedido y piezas persistidas y permite bloquear/revalidar/transicionar varios pedidos en la sesión/unidad de trabajo del caso de Optimization. Cada pieza mantiene su material/espesor persistido. | Formulario/API CRUD de Orders y cambios generales del ciclo de pedidos. El core no modifica casos de uso públicos de Orders. Si esa rama entrega una abstracción batch reusable antes de T7, el adaptador de Optimization se conecta a ella; no se duplicará la regla de negocio Orders. |
| Rama RBAC dinámico | Mapeo de permisos conceptuales `optimization.view`, `optimization.execute`, `optimization.confirm` a capacidades backend reales. | No implementar ni duplicar permisos/roles dinámicos. Hasta converger, la dependencia de Presentation debe conservar el mecanismo actual (`EJECUTAR_OPTIMIZACION`) como adaptador transitorio y respetar el usuario autenticado. |
| ADR/documentación de decisión | Registrar que el alcance posterior de ADR-002 se corrigió para adelantar FF a Sprint 1, sin editar su texto histórico. | Actualización/ADR posterior; no cambiar ADR-002 en este PLAN. |

### Contrato mínimo de integración con Orders

El contrato de Application requerido es un lote de IDs distintos y ordenados que devuelve snapshots desconectados de todos los pedidos y piezas, y operaciones en una sesión del caller para: bloquear pedidos por ID ascendente, volver a leerlos, validar que todos siguen en el estado esperado y transicionar el lote completo. No puede llamar a `start_pending(id_pedido)` repetidamente porque cada llamada actual hace commit y permitiría estados parciales. La unidad de trabajo de Optimization debe ser el dueño del commit/rollback.

## 4. Arquitectura y archivos probables

Los nombres siguientes son propuestas según el estilo snake_case, dataclasses y puertos presentes; se ajustan si el código final aporta una abstracción reutilizable. No se crean en esta tarea documental.

| Capa | Archivos previstos | Responsabilidad |
|---|---|---|
| Domain | `backend/app/modules/optimization/domain/problem.py`, `preparation.py`, `rotation.py`, `first_fit.py`, `metrics.py`, `residual.py`; reutilizar `raster_mask.py`, `rasterizer.py`, `placement.py` | DTOs inmutables, algoritmos puros, transformaciones de mm, rotaciones, orden, posiciones y métricas sin dependencias de infraestructura. |
| Application | `backend/app/modules/optimization/application/ports.py`, `dto.py` (nuevo si los DTO no encajan en `ports.py`), `use_cases.py`, `errors.py`, `resource_policy.py`, `unit_of_work.py` | Validación del lote/configuración, snapshot, casos de inicio/ejecución/consulta/confirmación y contratos de repositorios/progreso/UoW. |
| Infrastructure | `backend/app/modules/optimization/infrastructure/orders_adapter.py`, `stock_adapter.py`, `persistence_adapter.py`, `unit_of_work.py` | Una sesión SQLAlchemy caller-owned; lectura y transición batch; consulta determinista; bloqueo/consumo y movimientos. No importar otra infraestructura de módulo ni llamar servicios que hagan commit propio. |
| Presentation | `backend/app/modules/optimization/presentation/router.py`, `schemas.py`, `serialization.py`, `dependencies.py` | Compatibilidad HU-015; endpoints `/runs`; schema NDJSON y resultado; status/error/auth. |
| Modelo/migración | `backend/app/models.py`; nueva `backend/alembic/versions/<revision>_optimization_multipedido.py`; actualizar contrato de snapshots ORM existente donde corresponda | Asociación multipedido, constraints/índices y preservación; `CONFIRMADA` no se agrega al estado de optimización. |
| Pruebas | `backend/tests/optimization/`, `backend/tests/unit/optimization/`, `backend/tests/api/optimization/`, `backend/tests/integration/optimization/`, `backend/tests/integration/`, `backend/tests/contracts/` | Unitarias; uso de ports; contratos HTTP; PostgreSQL real temporal; migración/concurrencia y regresión existente. |

Se puede extender `backend/app/models.py` porque ese es el catálogo ORM compartido actual. Ningún import Domain/Application llega a ese archivo. Los adaptadores de Optimization acceden al ORM dentro de Infrastructure a través de la unidad transaccional.

## 5. Modelo multipedido y evolución de BD

### Estado actual y destino

Hoy `OPTIMIZACIONES.id_pedido` es FK no nula a `PEDIDOS.id_pedido`, con índice `(id_pedido, fecha_inicio)`. Una optimización se vincula físicamente a un pedido. Esto es incompatible con el alcance Reviewed de una corrida `1..N`.

El destino mínimo es una entidad asociativa `OPTIMIZACION_PEDIDO` con dos FKs no nulas, sin cascada destructiva, y clave primaria compuesta `(id_optimizacion, id_pedido)`. Esto representa `OPTIMIZACION 1:N OPTIMIZACION_PEDIDO N:1 PEDIDO`; no se crea unicidad global de `id_pedido`, porque un pedido puede aparecer en ejecuciones históricas distintas. Añadir índice para consulta por `(id_pedido, id_optimizacion)`; la PK sirve a la dirección inversa. ORM expone relaciones en `Optimizacion` y `Pedido` mediante una asociación explícita. La Application valida al menos un pedido; una relación padre-hijo vacía no se inserta.

### Migración Alembic

1. Actualizar [el Diseño de Base de Datos](../database/convergencia-v1-1.md) para reflejar la relación multipedido antes de implementar ORM/migración; registrar compatibilidad y preservación histórica.
2. Crear la tabla asociativa e índices con FK hacia optimización y pedido.
3. Copiar cada vínculo vigente desde `optimizaciones.id_pedido` a la asociación, preservando los IDs y sin reordenar ni perder optimizaciones históricas.
4. Verificar dentro del upgrade que cada optimización existente tenga exactamente un vínculo migrado y ningún `id_pedido` huérfano; abortar antes de quitar el campo si falla una comprobación.
5. Quitar la FK/índice antiguos y `optimizaciones.id_pedido` solo tras validar el backfill; conservar el índice funcional por asociación.
6. No cambiar los IDs de corrida/ejecución ni `MATERIAL_UTILIZADO`, métricas o movimientos.
7. Basar la revisión nueva en la punta auditada `ta036a1b2c3d` y probar `ScriptDirectory.get_heads()` con una sola cabeza. No crear merge revision salvo que el grafo cambie antes de implementar.

El downgrade solo puede volver al vínculo directo si cada optimización tiene exactamente un pedido asociado. Si encuentra una corrida multipedido, debe fallar antes de DDL y explicar que el downgrade perdería relaciones; no seleccionar un pedido arbitrario. La prueba usa PostgreSQL aislado e incluye upgrade con datos históricos, múltiples pedidos nuevos, FKs/PK/índice, rollback ante datos inconsistentes y downgrade seguro de estado representable. No implica que toda la historia R3 sea reversible: R3 declara downgrade no soportado.

## 6. Normalización, material y unidades

### DTO de problema

Usar dataclasses inmutables siguiendo el estilo Domain existente, con cantidades/medidas decimales validadas en el límite. Estructuras conceptuales y nombres de trabajo:

- `OptimizationProblem`: IDs explícitos de pedidos, configuración efectiva y grupos ordenados.
- `MaterialGroup`: `(id_tipo_vidrio, espesor_mm)`, unidades ordenadas y stock candidato asociado.
- `PieceUnit`: `id_pedido`, `id_pieza`, `unit_index`, tipo, espesor, geometría persistida de origen, `area_mm2` y geometría/raster reutilizable.
- `StockCandidate`: fuente `RETAZO`/`PLANCHA`, ID persistido, `stock_unit_index`, tipo/espesor, dimensiones/geometría, área de material y metadatos para revalidar.
- `Placement`: IDs de pedido/pieza/unidad, tipo/espesor, fuente/ID/unidad física, fila/columna o coordenadas mm reproducibles, rotación en grados y resolución usada.
- `OptimizationResult`: método FF, estado/completitud, pedidos, grupos, placements, unidades colocadas/total, recursos usados, métricas cuando sean calculables y configuración versionada efectiva.

No duplicar `id_tipo_vidrio` ni `espesor_mm` como campos de persistencia en ejecución si ya son trazables desde `PIEZA` y el patrón serializado puede conservar los valores utilizados. Sí incluir ambos en `PieceUnit`, `StockCandidate`, evento y placement para que el motor/cliente no tenga que consultar el ORM.

### Expansión, grupos y preparación

Application valida el lote completo, toma snapshots de piezas persistidas y llama a una función de Domain para normalizar. Para cada pieza con `cantidad=N` crea `N` unidades lógicas indexadas `1..N`; cada unidad recibe placement propio. Geometry/raster se calcula una vez por firma de geometría, resolución y ángulo; las referencias compartidas son inmutables.

Grupos en orden `(id_tipo_vidrio ASC, espesor_mm ASC)`. Dentro de cada grupo, ordenar unidades por `area_mm2 DESC`, mayor dimensión de bounding box DESC, `id_pedido ASC`, `id_pieza ASC`, `unit_index ASC`. Una función explícita `prepare_group_units` (o equivalente) aplica la política; es preparación previa y no Worst Fit. Tests deben demostrar salida estable ante orden distinto de filas SQL.

## 7. Stock compatible y unidad física

Application define `CompatibleStockPort.list_compatible(group_key)`. El adaptador consulta Inventory en lote una vez por grupo, sin importar su módulo Infrastructure. El filtro exige el mismo tipo y espesor y `estado=True`; para planchas además `cantidad > 0`. El motor recibe snapshots ordenados y el algoritmo nunca conoce SQLAlchemy.

Prioridad aprobada: retazos activos compatibles y después planchas activas compatibles. Dentro de cada tipo: `fecha_registro DESC, id DESC`, que conserva el orden estable observable del repositorio actual después de filtrar activos; para cada plancha, expandir `cantidad` como unidades lógicas `stock_unit_index=1..cantidad` en orden ascendente. La cantidad lógica no crea IDs de plancha nuevos: placement conserva `(material_source=PLANCHA, material_id=id_plancha, stock_unit_index)` y persistencia agrega consumos por ID de plancha. Retazo es unitario y usa `stock_unit_index=1`.

El motor no reserva ni bloquea inventario durante simulación. El stock se vuelve a consultar al confirmar y las filas afectadas se bloquean; si falta una unidad o un retazo fue desactivado, devolver conflicto y no sustituir candidato.

## 8. Raster, rotaciones, posiciones y material irregular

### Raster y caché

- Mantener la misma `resolucion_raster_mm` para material y pieza de cada prueba/placement.
- Para cada orientación, transformar geometría original en mm alrededor del centroide, normalizar la caja rotada al origen local y rasterizar la geometría transformada con la regla conservadora vigente. No rotar un bitmap con interpolación.
- Construir ángulos con Decimal: `0, Δθ, 2Δθ, … < 360`; validar `0 < Δθ <= 360`. Normalizar resultados al intervalo `[0,360)`. Esto es búsqueda discreta y no incluye optimización angular continua.
- Círculos reutilizan una máscara sin regenerarla en cada ángulo. Para otras geometrías, eliminar orientación equivalente solo si la máscara raster final y sus dimensiones son idénticas a una ya preparada. No deducir simetría por bounding box.
- Caché local a una corrida por fingerprint estable de geometría, resolución y ángulo normalizado; no compartir entradas entre resoluciones/configuraciones. Tests incluyen ángulos repetidos/simétricos, círculo y bordes de discretización.

### Candidatos row-major

Para cada unidad, candidato de stock y orientación, recorrer los anclajes legales de la grilla con fila exterior y columna interior:

1. `row` desde `0` hasta `material.rows - piece.rows`, inclusive.
2. Para cada fila, `column` desde `0` hasta `material.columns - piece.columns`, inclusive.
3. Llamar `SheetLayout.check(mask, row, column)`, que decide límites del material, margen, ocupación y separación.
4. El primer anclaje válido es el placement de esa orientación/material. Guardar el estado de layout con `place` y detener el recorrido de candidatos, orientaciones y materiales para esa unidad.

El recorrido row-major es reproducible, enumera todas las posiciones del raster que podrían contener la caja de máscara y reutiliza TA-007. La AABB solo descarta candidatos cuyo tamaño ni siquiera cabe; una AABB que cabe obliga a ejecutar todos los checks de geometría/raster. First Fit acepta la primera combinación en el orden congelado de grupo/unidad, stock, rotación y anclaje.

### Fuera del material, libre y ocupado

En `SheetLayout`, la máscara interior del material distingue fuera del material (bit 0) de celdas válidas; una máscara de ocupación independiente distingue celdas ya colocadas de las libres. Se usa la geometría interior de TA-007, no una AABB rellenada. Para retazos circulares y poligonales se usa `rasterize_material`; la máscara interior evita que una pieza se coloque fuera de la forma real. El material irregular pasa además por el mismo margen/separación de `SheetLayout`.

### Geometría residual recuperable

No hay operaciones booleanas poligonales ni Shapely en las dependencias actuales. El primer algoritmo de recuperación del plan será deliberadamente conservador. Para cada unidad física usada, toma la máscara interior del material ya reducida por margen y las celdas ocupadas/expandidas por separación. Recorre las filas y mantiene por columna la altura consecutiva de celdas que están completamente libres; por fila, un stack monótono de alturas enumera los rectángulos máximos que terminan en esa fila. Selecciona el candidato global con este orden: área de celdas descendente, fila superior ascendente, columna izquierda ascendente, ancho descendente y alto descendente. El máximo se calcula por separado para cada unidad de material, sin superponer candidatos.

El rectángulo usa dimensiones exactas `columnas × resolucion` por `filas × resolucion`, se valida de nuevo contra las celdas interiores y placements, y se emite como geometría `RECTANGULO` local a ese nuevo retazo. No representa todo el sobrante ni aproxima una forma irregular: es una región rectangular exacta contenida en el residuo raster conservador; el resto queda como merma.

Persistir solo si cumple `ancho_min_retazo_mm`, `alto_min_retazo_mm`, área positiva y todas las validaciones de geometría/BD. La configuración ORM no contiene hoy un `area_min_retazo_mm2`; no inventar ese valor ni inferir que existe. En T1 resolver con el reviewer si el mínimo de área requerido por SPEC se expresa mediante una regla vigente documentada o si requiere decisión/evolución de `Configuracion`; hasta entonces, la creación respeta mínimos de ancho/alto disponibles y deja explícita la falta de mínimo de área independiente. Registrar ubicación sobre el material fuente en el patrón/evento de confirmación para trazabilidad; la geometría persistida del retazo contiene sus dimensiones locales.

## 9. First Fit, eventos de dominio y progreso

`FirstFitOptimizer` recibe el `OptimizationProblem`, candidatos ya ordenados y parámetros inmutables. No importa FastAPI, ORM, Supabase, Inventory Infrastructure o React. Por grupo ordenado: consulta de stock en Application una vez; itera unidades preparadas; intenta candidato, rotación y anclaje en el orden §8; acepta la primera posición válida; devuelve un resultado completo solo si colocó todas las unidades seleccionadas.

Domain no simula ni publica HTTP. El motor expone hitos tipados (unidad iniciada, placement aceptado, grupo terminado) por callback/iterador in-process; Application los adapta a los eventos semánticos y los pone en el stream. Solo se emiten hitos reales: nunca un evento por celda, rotación o anclaje fallido. Si una unidad no encuentra placement, registrarla sin placement y continuar con las siguientes unidades/grupos; así el patrón parcial aprovecha placements posibles y sigue siendo determinista. Si al final falta una o más unidades, el resultado es `SIN_SOLUCION`; no se persiste material como consumo ni se confirma el lote.

### Transporte seleccionado

Usar `StreamingResponse` con `application/x-ndjson` y `fetch` + `ReadableStream` en frontend. La comunicación es unidireccional, la autenticación Bearer existente funciona con `fetch`, no requiere reconexión bidireccional y cada línea puede representarse incrementalmente. SSE (`EventSource`) complica el encabezado Bearer personalizado; WebSocket añade protocolo/conexión innecesarios para este flujo. La UI externa deberá parsear chunks parciales y límites de línea.

Presentation hace el preflight y confirma la transacción de inicio antes de construir la respuesta stream; por eso errores de lote/configuración se devuelven como HTTP normal. Application carga los candidatos de stock una vez por grupo antes de iniciar el reloj y fuera de una transacción larga. El cálculo se produce al avanzar el iterador de respuesta, sin una transacción DB abierta. Si ya comenzaron los headers NDJSON, el status HTTP no puede cambiar: fallas controladas posteriores se comunican como `optimization_failed` con código seguro y estado durable `FALLIDA`. Cancelación/desconexión se detecta cooperativamente entre unidades y el adaptador intenta registrar `FALLIDA`; un crash puede dejar `EN_EJECUCION` y requiere reconciliación.

Cada línea UTF-8 termina con `\n` y tiene este envelope estable, snake_case y versionado. La forma TypeScript siguiente describe tipos; no fija valores predeterminados de configuración:

```ts
type OptimizationEventNameV1 =
  | "optimization_started" | "group_started" | "piece_started" | "piece_placed"
  | "group_completed" | "metrics_calculated" | "optimization_completed" | "optimization_failed";

type OptimizationEventV1 = {
  schema_version: 1;
  sequence: number;
  event: OptimizationEventNameV1;
  id_optimizacion: number;
  occurred_at: string; // ISO 8601 UTC
  data: Record<string, unknown>;
};

type OptimizationStartedDataV1 = {
  metodo: "FF";
  order_ids: number[];
  total_units: number;
  groups: Array<{ id_tipo_vidrio: number; espesor_mm: string }>;
  configuracion: {
    resolucion_raster_mm: string;
    margen_mm: string;
    separacion_mm: string;
    paso_angular_grados: string;
  };
};
```

`sequence` aumenta una unidad por evento del run. `event` es uno de:

| Evento | Datos obligatorios |
|---|---|
| `optimization_started` | `metodo`, IDs pedidos, total de unidades, grupos y configuración efectiva. |
| `group_started` | `id_tipo_vidrio`, `espesor_mm`, unidades del grupo. |
| `piece_started` | `id_pedido`, `id_pieza`, `unit_index`, clave de grupo, `placed_units`, `total_units`. |
| `piece_placed` | Trazabilidad completa del placement (pedido, pieza, unidad, tipo, espesor, `material_source`, `material_id`, `stock_unit_index`, `x_mm`, `y_mm`, `rotation_deg`), y contadores `placed_units`, `total_units`, `progress_pct`. `progress_pct = placed_units / total_units * 100`, no suma progreso por intentos. |
| `group_completed` | Clave de grupo, colocadas/total y placements del grupo o referencia durable. |
| `metrics_calculated` | Métricas disponibles o `metrics_available=false` si no se usó área material para el denominador. |
| `optimization_completed` | Estado `COMPLETADA` o `SIN_SOLUCION`, `completo`, contadores y URL de resultado persistido. |
| `optimization_failed` | Código y mensaje seguro; nunca excepción, SQL ni stack trace. |

La UI puede pintar los `piece_placed` en vivo. El endpoint GET del resultado persistido es la fuente canónica para reload/reconstrucción; el stream no se presenta como log reanudable. `Cache-Control: no-cache`; deshabilitar buffering de proxy si el entorno lo exige. No incluir configuración/secretos distintos de los cuatro parámetros efectivos.

El reloj `perf_counter_ns` del motor inicia después del preflight y la carga de stock, justo antes de normalizar/rasterizar unidades; termina después de First Fit y métricas de dominio. El adaptador pausa el reloj durante entrega/bloqueo de eventos, serialización y espera de red; no incluye autenticación, consulta/commit DB, HTTP, renderizado React ni animación. Persistir milisegundos enteros en `tiempo_computacional_ms` según precisión de R4.

## 10. Resultado, persistencia y métricas

### Mapeo a tablas existentes

| Tabla/modelo actual | Uso del plan |
|---|---|
| `OPTIMIZACION` / `Optimizacion` | Nueva fila por corrida FF con snapshot `id_configuracion`, actor, hora, estado, versión de política y asociación 1..N. `EN_EJECUCION` al aceptar; `COMPLETADA` si todas las unidades tienen placement; `SIN_SOLUCION` al finalizar el algoritmo controladamente; `FALLIDA` ante error inesperado capturable. Mantener `COMPLETADA` tras confirmación; la elegibilidad se consume una sola vez mediante lock y estados actuales de todos los pedidos. |
| `EJECUCION_OPTIMIZACION` / `EjecucionOptimizacion` | Una única fila `metodo='FF'` por corrida; no crear BF/WF vacíos. `EN_EJECUCION` al inicio, `COMPLETADA` al fin normal incluso si `completo=False` en SIN_SOLUCION, `FALLIDA` ante excepción. `patron_resultado` JSONB versionado conserva grupos, configuración, stock usado/unidad física, placements y residual; `id_ejecucion_seleccionada` apunta a FF solo cuando es completo/confirmable. |
| `MATERIAL_UTILIZADO` / `MaterialUtilizado` | Una fila agregada por fuente física usada en la ejecución; para plancha `cantidad_utilizada` cuenta unidades lógicas consumidas de esa fila; para retazo es 1. Son propuestas persistidas y no mutan stock, igual que exige Diseño de BD. El patrón conserva el `stock_unit_index` usado por placement. |
| `METRICA_EJECUCION` / `MetricaEjecucion` | Una fila si `area_material_total_mm2 > 0`. R4 exige denominador positivo; si no se colocó nada en SIN_SOLUCION, no insertar una fila inválida y devolver métricas no disponibles/null. |
| `CONFIGURACION` / `Configuracion` | Leer una única configuración vigente y copiar sus cuatro parámetros y `id_configuracion` a la corrida. No fijar defaults. Cero, varias vigentes o paso angular NULL/invalidado se rechaza antes de transición; corregir fuente/configuración es externo a la corrida. |
| `MOVIMIENTOS_INVENTARIO` / `MovimientoInventario` | Solo en confirmación, dentro de la misma sesión; registrar `CONSUMO_OPTIMIZACION` con FK al run, recurso, usuario y cantidad realmente descontada. |

R4 y [Diseño de Base de Datos](../database/convergencia-v1-1.md) definen nombres, unidades, rangos y redondeo de columnas; el diseño no prescribe las fórmulas completas. Para esta ejecución:

- `area_piezas_colocadas_mm2` = suma de `PieceUnit.area_mm2` colocadas.
- `area_material_total_mm2` = área de cada unidad física usada: `ancho_mm × alto_mm` por plancha/unidad; `Retazo.area_mm2` por retazo consumido. Excluir stock inspeccionado pero no usado.
- `aprovechamiento_pct` = `area_piezas_colocadas_mm2 / area_material_total_mm2 × 100`, redondeado a precisión de columna R4 y validado en `[0,100]`.
- `retazo_recuperable_mm2` = suma de áreas de geometrías residuales exactas que superan las dimensiones mínimas vigentes y se persistirían al confirmar; cero cuando no hay ninguna.
- `merma_mm2` = `area_material_total_mm2 − area_piezas_colocadas_mm2 − retazo_recuperable_mm2`, no negativa. Si la suma excede el total, fallar validación de métricas en vez de ocultar el error saturando en cero.
- `planchas_nuevas_usadas` = cantidad de unidades físicas de plancha utilizadas (no registros de plancha). `tiempo_computacional_ms` usa el reloj descrito en §9.

El resultado final persiste todas las unidades solicitadas, colocadas o sin placement, con estado/razón de no colocación y placements por grupo. Una corrida parcial es reconstruible pero no confirmable. Reconsultar resultado nunca invoca el motor.

## 11. Estados, unidades de trabajo y fallos

No mantener locks DB durante el cálculo ni hacer commits dentro de puertos separados.

| Frontera | Operación atómica |
|---|---|
| Inicio del lote | Validar IDs distintos; bloquear todos los `Pedido` por ID ascendente; releer elegibilidad y piezas; validar configuración; crear `Optimizacion`, asociación para cada pedido y única `EjecucionOptimizacion(FF)`; cambiar todos los pedidos `PENDIENTE → EN_OPTIMIZACION`; commit único. Cualquier pedido inválido revierte todo y no crea ejecución/subconjunto. |
| Cálculo | Sin transacción larga. Consultar snapshots de stock por grupo; ejecutar Domain; no consumir, desactivar o mover stock. Al terminar se elige una de las dos transacciones finales siguientes. |
| Resultado completo | En una sesión: guardar patrón, materiales propuestos, métricas, `EjecucionOptimizacion.COMPLETADA/completo=True`, `Optimizacion.COMPLETADA`, referencia seleccionada y cambiar todos los pedidos `EN_OPTIMIZACION → OPTIMIZADO`; commit único. |
| `SIN_SOLUCION` controlado | En una sesión: persistir patrón parcial, `EjecucionOptimizacion.COMPLETADA/completo=False`, `Optimizacion.SIN_SOLUCION`, métricas solo si hay área material positiva, limpiar selección confirmable y cambiar todos los participantes `EN_OPTIMIZACION → PENDIENTE`; commit único. Sin movimientos ni cambios en stock. |
| Fallo inesperado/cancelación | Capturar excepción conocida para marcar padre/ejecución `FALLIDA` y cerrar fecha en transacción independiente; no clasificar como SIN_SOLUCION, no confirmar y no devolver pedidos automáticamente a PENDIENTE. Si el proceso cae antes de registrar FALLIDA, deja `EN_EJECUCION` para reconciliación. No reintentar cálculo automáticamente. |
| Confirmación | Caso de uso separado; una sola sesión transaccional para run, pedidos, recursos, movimientos, nuevos retazos y confirmación de todos los pedidos; ver §12. |

Para recuperación de una corrida inesperadamente abandonada: no hacer reset automático ni volver a ejecutar. Una reconciliación explícita inspecciona estado durable con locks; solo si padre/ejecución no están completos, todos los pedidos siguen `EN_OPTIMIZACION` y no existe movimiento `CONSUMO_OPTIMIZACION` del run, puede marcar corrida/ejecución `FALLIDA` y devolver el lote entero a `PENDIENTE` en la misma transacción. Si cualquier comprobación no concuerda, detenerse para investigación humana. La operación inicial será de administración/reconciliación operacional, no endpoint abierto de usuario; el alcance/interfaz y autoridad operativa se aprueban antes de exponerla. No utilizar esta ruta para `SIN_SOLUCION`.

Los locks de lote y confirmación se toman en orden estable: corrida, pedidos ascendentes, planchas ascendentes y retazos ascendentes. La transacción de inicio usa los pedidos; la de finalización primero lockea corrida y luego pedidos; la de confirmación empieza por corrida y sigue el mismo orden. Esta regla reduce deadlocks y la captura PostgreSQL traduce conflicto a 409.

## 12. Confirmación transaccional

`ConfirmOptimizationUseCase` recupera el patrón y propuestas desde DB, no desde un placement enviado por el cliente. Una solución solo se confirma si `Optimizacion.COMPLETADA`, selección apunta a ejecución FF completa, todos los pedidos asociados siguen `OPTIMIZADO`, y cada recurso del patrón continúa activo/compatible con cantidad suficiente.

Dentro de una transacción PostgreSQL:

1. Bloquear corrida y pedidos asociados ordenados; comprobar que el patrón completo y cada pedido siguen confirmables.
2. Agrupar el consumo por plancha; bloquear fila, verificar activo, tipo/espesor y `cantidad >= cantidad_utilizada`; descontar unidades físicas. Bloquear cada retazo, verificar exactamente una unidad activa y material compatible; marcarlo consumido/inactivo.
3. Insertar movimiento `CONSUMO_OPTIMIZACION` por recurso con cantidad, usuario y `id_optimizacion`; guardar sin commit intermedio.
4. Validar y crear geometrías residuales rectangulares exactas calculadas según §8, aplicando umbrales configurados; asignar `id_ejecucion_origen`. Ningún retazo se crea desde AABB o solo un área.
5. Cambiar todos los pedidos `OPTIMIZADO → CONFIRMADO`; commit único.

Si cualquier recurso cambió, la operación completa hace rollback y Presentation responde 409; no se busca reemplazo de material. Cualquier excepción/constraint hace rollback, preservando stock/pedidos/movimientos en conjunto. La segunda confirmación del mismo run bloquea y encuentra pedidos que ya no están `OPTIMIZADO`; devuelve 409 sin duplicar consumo. Para un lote de planchas que usa varias unidades de una misma fila, verificar/decrementar el total agregado una sola vez.

El adaptador actual de Inventory (`InventoryRepository.transaction()` y `InventoryService`) crea y confirma su propia sesión; no usarlo desde esta ruta. Implementar métodos transaction-aware que reciben la sesión del UoW de Optimization, sin importar módulos Infrastructure entre sí. Orders debe ofrecer la misma propiedad de transacción al lockear y cambiar todos los pedidos.

## 13. Contratos API y autorización

### Compatibilidad

Conservar `/api/optimization/start` y `/api/optimization/rasterize` sin cambiar sus request/response ni permiso mientras HU-015 tenga consumidores. La ruta nueva no delega al caso escalar varias veces; una selección `N=1` entra por el mismo `OptimizationProblem` que `N>1`.

### Rutas nuevas

| Método/ruta | Contrato propuesto | HTTP |
|---|---|---|
| `POST /api/optimization/runs` | JSON con `order_ids: int[]` explícitos, sin duplicados ni configuración de geometría del cliente. Preflight transaccional; responde como stream NDJSON v1 con `id_optimizacion`, método FF, configuración snapshot y eventos §9. | `201` (run aceptado, `Location` a resultado); `401`, `403`, `404` lote con ID ausente, `409` estado/configuración vigente conflictiva, `422` cuerpo/duplicados/datos persistidos inválidos, `500` mensaje seguro antes de iniciar headers. |
| `GET /api/optimization/runs/{id_optimizacion}` | Estado, pedidos relacionados, grupos, patrón, colocadas/total, configuración, métricas disponibles y confirmable. Respuesta canonical/versionada para reconstrucción. | `200`; `401`, `403`, `404`, `500`. |
| `POST /api/optimization/runs/{id_optimizacion}/confirm` | No recibe placements ni materiales alternativos; el backend carga el resultado persistido. Responde estado de todos los pedidos, materiales consumidos y nuevos retazos válidos. | `200`; `401`, `403`, `404`, `409` run/stock/estado conflictivo, `422` ejecución no completa/no confirmable, `500` seguro con rollback. |

Una lista mezclada con un pedido ausente no inicia los demás. Body inválido se mapea a 422. Después de que comience streaming, los status HTTP no cambian; los errores terminales se exponen como evento seguro y estado consultable. No incluir SQL, stack, credenciales o geometría inválida en mensajes de error.

### Integración de permisos

Application no decide roles. Presentation depende de adaptadores para `optimization.view`, `.execute`, `.confirm`. Hoy solo está comprobado el guard `EJECUTAR_OPTIMIZACION` para las rutas HU-015. Hasta integrar RBAC, conservar ese guard exactamente para los endpoints existentes; para las tres rutas nuevas acordar con la rama RBAC la traducción temporal a permisos/roles backend actuales. Si el modelo vigente no distingue una capacidad, mantenerla cerrada hasta resolver la traducción; no inferirla por el ocultamiento en UI ni añadir permisos dinámicos paralelos permanentes aquí.

## 14. Contrato para integración con `S1-optimization-ui`

Entregar en T1 y congelar en schemas/examples backend versionados:

1. Request `POST /runs`: `order_ids`; selección explícita, IDs únicos.
2. Transporte `application/x-ndjson`, envelope `{schema_version, sequence, event, id_optimizacion, occurred_at, data}`, tratamiento de fragmentos de línea/chunks y errores pre/post headers.
3. Ocho tipos semánticos de evento §9 y payload de `piece_placed` incluyendo material/unidad, coordenadas mm, ángulo, trazabilidad y progreso real.
4. DTO del GET canónico: `id_optimizacion`, estado, `metodo=FF`, `order_ids`, grupos y key material, placements, recursos, `placed_units`, `total_units`, `completo`, métricas nullable, config efectiva, `confirmable`.
5. Confirmación `POST /runs/{id}/confirm` y response de pedidos/materiales creados/consumidos; 409 concurrente/stock desactualizado.
6. Códigos y formato de errores 401/403/404/409/422/500; error de stream es evento terminal seguro y el GET conserva status.

Se acuerda el schema en T1 para que Quispe pueda empezar el consumer React sin esperar migración, persistencia o confirmación. El stream incremental alimenta preview; reload usa GET y no vuelve a ejecutar FF. El equipo UI realiza el render gráfico; el core no depende de la UI ni envía eventos por intentos fallidos.

## 15. Pruebas y evidencia previstas

No ejecutar la suite durante la creación documental. Para la implementación:

| Capa | Pruebas mínimas planeadas |
|---|---|
| Domain unit | Expansión/cantidad, grouping multimaterial, sort estable, grupos sin piezas inválidas, rotaciones/normalización/deduplicación/círculos, caché, row-major primero válido, geometría real de retazo irregular, límites/margen/separación/no overlap, resultado incompleto, determinismo y métricas. |
| Application unit | Un pedido por flujo N=1; N pedidos; multimaterial; missing/duplicate/no elegible invalida lote completo; stock vacío/incompatible; progreso/hitos; SIN_SOLUCION vs excepción; estados y resultados; permisos delegados; timer excluye I/O y stream. |
| API | Conservación HU-015; request/event/result/confirm schemas; stream NDJSON con fragmentación; 200/201 y error map 401/403/404/409/422/500; autorización backend; sanitización; disconnect/cancel; GET después de completado/fallido. |
| PostgreSQL integration | Upgrade/backfill/downgrade condicionado; grafo Alembic con una head; asociación multipedido y FK; transacciones de inicio/completo/SIN_SOLUCION; JSONB/métricas; locking/consumo/movimientos/residuos; rollback total; doble confirmación simultánea sobre mismo run/stock. |
| Regression | Suites de `tests/optimization`, API/start HU-015, pruebas de Orders y Inventory afectadas por modelos compartidos; migraciones R3/R4 y multimaterial según fixture de PostgreSQL aislado. |
| E2E | Core provee API/status/stream para que la rama UI cubra seleccionar → progreso real → patrón/métricas → confirmar. El backend prueba una corrida HTTP completa sin mocks de Domain; E2E visual conjunto se coordina entre ramas y no cambia propiedad de frontend. |
| Frontend component / Playwright | Corresponde a `feature/S1-optimization-ui`: pruebas de componentes para selección, parseo NDJSON, placements/métricas y estados de confirmación; Playwright conjunto para seleccionar → progreso vivo → patrón → confirmar. El core entrega contratos T1 y servidor/API integrable; no cambia ni ejecuta suites del frontend como parte de su implementación. |
| Benchmark/reproducibilidad | Fixture estable pequeño y uno representativo; repetir iguales pedidos, stock y config debe producir mismo orden de eventos/placements/patrón. Medir tiempo solo Domain/motor, registrar tamaño de grilla/unidades; no establecer umbral hasta revisar tiempos reales. |

Las pruebas de migración y concurrencia usan PostgreSQL temporal aislado conforme a `docs/testing/README.md`; no ejecutar contra Supabase compartido. Evidencia futura se organiza en `docs/evidence/sprint-01/S1-OPTIMIZATION-FIRST-FIT/` con comandos, configuración no secreta y resultados reales. No afirmar resultados hasta ejecutarlos.

## 16. Camino crítico, paralelización y riesgo

### Ruta crítica

`T1` → (`T2 → T3 → T4` en paralelo con `T5` y `T6`) → `T7 → T8` → (`T9` en paralelo con `T10 → T11`) → `T12 → T13`.

T5 y T6 pueden avanzar en paralelo con T2/T3/T4 después de congelar T1; T3 precede T4. T7 depende del contrato de transacción batch de Orders y de stock/config; debe acordarse con la otra rama antes de terminar T1/T5. Confirmación y streaming comparten los DTO de T1/T8, pero pueden implementarse en paralelo después de persistencia. T11 depende de la implementación de confirmación.

### No posponer dentro del cierre Sprint 1

First Fit real; placements reconstruibles; lote explícito `1..N` por un solo flujo; expansión de cantidades; grupos multimaterial; stock compatible y unidades físicas; geometría real; eventos/progreso producido durante cálculo; resultado final/métricas; estados completos/SIN_SOLUCION; confirmación explícita; transacción atómica, locking, rollback y conflicto concurrente; pruebas PostgreSQL críticas.

### Posponible solo si no pone en riesgo esos criterios

Optimización de rendimiento avanzada después de benchmark, cache compartida entre corridas, geometría residual no rectangular (se registra merma hasta algoritmo válido), reanudación de stream tras desconexión, visualizaciones adicionales, telemetría externa y cualquier heurística BF/WF. El vertical slice sirve para validar pronto el camino, no habilita cerrar Sprint dejando pendiente `1..N`, multimaterial, confirmación o rollback.

### Riesgos/bloqueos detectados

- **Asociación 1-pedido actual:** incompatible con SPEC; requiere migración, snapshots de modelo y revisión de diseño BD antes de desplegar. El downgrade de lotes multipedido no es representable.
- **Transactions cross-module:** repositorios Orders/Inventory actuales hacen commits propios o scalar CAS; sin un contrato caller-owned de sesión no se puede garantizar lote y confirmación atómicos. Dependencia inmediata con rama Orders/material flow.
- **Mínimo de área para retazo:** SPEC refiere ancho/alto/área vigentes; ORM solo almacena ancho/alto. Falta corroborar documentación/regla de mínimo de área o aprobar cambio de configuración; no inventar un default.
- **Configuración vigente no asegurada:** campo `vigente` no tiene constraint de unicidad global y `paso_angular_grados` es nullable. El snapshot debe fallar cerrado si no hay exactamente una configuración completa.
- **NDJSON y buffering:** proxy/deploy puede agrupar fragmentos; verificar entorno con fetch real. Después de headers no hay códigos HTTP nuevos; cliente debe leer `optimization_failed` y consultar GET.
- **Carga geométrica:** discretización conserva límites de manera conservadora y puede rechazar placements físicamente posibles; benchmark informa tiempo/memoria, no se debe presentar como óptimo global.
- **Configuración/criterio reproducible:** guardar versión y snapshot efectivos; cada cambio de policy/serialización requiere versión del patrón para reconstrucción.
- **Transición Orders externa:** hasta que el contrato batch de Orders esté disponible, no asumir que el endpoint existente de inicio puede satisfacer el caso multipedido.

## 17. TASKS — descomposición de `feature/S1-optimization-core`

Estimación de curso: `1 SP = 6 horas`. Los SP son propuesta, no registro de horas realizadas. Cada tarea cierra con cambios limitados, pruebas indicadas y evidencia de rama; los commits correspondientes se crearán durante implementación, no en este PLAN.

### T1 — Congelar contratos compartidos (1 SP)

- **Objetivo:** publicar contrato para UI antes de completar persistencia: request, NDJSON v1, evento placement, GET result, confirmación, errores y permisos puente.
- **Archivos/capas probables:** `application/dto.py`, `presentation/schemas.py`, `presentation/serialization.py`, examples/contratos en `backend/tests/api/optimization/`; esta sección del PLAN.
- **Dependencias:** SPEC Reviewed; inspección de endpoints/auth existentes.
- **Criterios verificables:** nombres/campos snake_case, unidades mm/mm²/ms/grados; progress_pct derivado; parseo NDJSON por líneas; API sin defaults cliente; estados normal y stream failure documentados; UI puede comenzar sin migración.
- **Pruebas mínimas:** pruebas de schema/serialización de fixtures contractuales; no mocks de motor se requieren para fijar envelope.
- **Evidencia esperada:** ejemplo versionado request, 8 eventos, result, confirm y matriz de errores; mensaje de integración a rama `S1-optimization-ui`.

#### T1 — Contrato v1 concretado (16/10/2026)

Fuentes de implementación del contrato:

- [Modelo puro e inmutable](../../backend/app/modules/optimization/domain/problem.py).
- [DTO de observación de corrida y progreso](../../backend/app/modules/optimization/application/dto.py).
- [Schemas v1](../../backend/app/modules/optimization/presentation/run_schemas.py) y
  [adaptación modelo → wire](../../backend/app/modules/optimization/presentation/run_serialization.py).
- [Ejemplos JSON versionados para UI](../../backend/tests/api/optimization/fixtures/s1_contract_v1.json).
  Son fixtures ilustrativas, no resultados observados de un motor ni evidencia de streaming.

Esta concreción implementa solamente estructuras, invariantes y serialización de T1.
No registra rutas `/runs`, no codifica ni transmite NDJSON, no prepara/expande/ordena
unidades, no rota ni ejecuta FF y no cambia persistencia. T2 y posteriores permanecen
pendientes. La aprobación general de este PLAN se conserva; no equivale a una nueva
aprobación humana de la implementación T1.

**Auditoría y reutilización.** No existe una clase `Rasterizer`: los puntos públicos
son las funciones de `rasterizer.py`. Se conservan `RasterMask`, esas funciones,
`SheetLayout`, `PlacementCheck`, `RasterizedPiece`, `OptimizationOrders`, los casos
de uso escalares, adaptador Orders, schemas, serialización, guards y rutas HU-015.
El `placement.py` actual valida geometría y devuelve un layout; no representa una
asignación con identidad. Por eso `problem.Placement` compone `PieceUnit` y
`StockCandidate` más posición/orientación, sin añadir trazabilidad a `SheetLayout`.
Los schemas geométricos de HU-015 se reutilizan en los nuevos schemas.

**Modelo interno (nombres ingleses).**

| Tipo | Contenido e invariantes de T1 |
|---|---|
| `OptimizationConfig` | Cuatro parámetros efectivos `Decimal`, obligatorios, sin defaults. Resolución positiva, margen/separación no negativos y paso en `(0,360]`. |
| `PieceUnit` | `order_id`, `piece_id`, `unit_index>=1`, `glass_type_id`, `thickness_mm`, `geometry`, `area_mm2`. Identidad `(piece_id, unit_index)`; `shape_type` deriva de la geometría y `material_key` de tipo/espesor. No se expande cantidad. |
| `StockCandidate` | Enum `MaterialSource.REMNANT=RETAZO` / `SHEET=PLANCHA`, `material_id`, `physical_unit_index>=1`, tipo/espesor, geometría y área. Identidad `(source, material_id, physical_unit_index)`. Retazo siempre índice 1. Plancha rectangular; dos índices pueden representar una misma fila sin generar nuevos IDs. |
| `MaterialGroup` | Tipo/espesor, unidades y candidatos como tuplas; verifica compatibilidad y rechaza identidades repetidas. No agrupa ni ordena entradas por sí mismo. |
| `OptimizationProblem` | IDs explícitos, config y grupos. Rechaza selección/grupos/unidades duplicados, pedidos no cubiertos y snapshots contradictorios de una misma pieza. Conserva el orden recibido: la preparación corresponde a T2. |
| `Placement` | Referencias inmutables `piece`/`stock`, `x_mm`, `y_mm`, `rotation_deg` y `geometry` orientada/local. No duplica los IDs contenidos en sus referencias; la serialización los expone. Compatibilidad y ángulo `[0,360)` validados. La aceptación geométrica sigue siendo responsabilidad de `SheetLayout`. |
| `OptimizationResult` | Problema, placements únicos, métricas y tiempo opcionales; `method=FF`, contadores, `complete`, unidades sin colocar y materiales usados se derivan. No puede lograr completitud contando dos veces una unidad. |
| `OptimizationMetrics` | Contenedor validado de los valores posteriores R4, sin ejecutar fórmulas ni extraer residuos. No permite porcentaje fuera de `[0,100]`, áreas negativas ni denominador cero. |
| `OptimizationRun` / `Progress` | Estado de observación `EN_EJECUCION/COMPLETADA/SIN_SOLUCION/FALLIDA`, confirmación y elegibilidad; progreso derivado de colocadas/total. No son entidades ORM ni casos de uso de transición. |

Geometría: snapshot copiado y congelado recursivamente (`MappingProxyType` y tuplas),
manteniendo números `int/float` canónicos compatibles con el raster vigente. No
rerasteriza ni renormaliza coordenadas. No reemplaza la validación de geometría
persistida de Orders/Inventory. Espesor, áreas, parámetros, posiciones y ángulos
nuevos usan `Decimal`; no aceptan conversión implícita desde float. El puente de
T3 al raster existente convertirá explícitamente lo imprescindible después de su
preflight, sin cambiar TA-005/006/007 ni reducir precisión de snapshots originales.

**Precisión y nombres wire.** Se mantienen los nombres snake_case de §§9/14:
`id_optimizacion`, `id_pedido`, `id_pieza`, `id_tipo_vidrio`, `espesor_mm`,
`metodo`, `estado`, `completo`, `configuracion`. Las medidas Decimal se transmiten
como **strings decimales JSON**, coherente con `espesor_mm` de HU-015; la UI no debe
presuponer `number`. Los cuatro parámetros del ejemplo TypeScript de §9 se han
precisado como strings. Coordenadas del contorno canónico conservan el contrato
geométrico numérico existente. IDs, índices, contadores y milisegundos son enteros;
`schema_version` es 1. No se cuantizan medidas ni se calculan métricas en T1.

Se usa **`physical_unit_index` en Domain** y **`stock_unit_index` en wire**, conservando
el nombre ya acordado con UI en el PLAN; el adaptador realiza un mapeo explícito
uno a uno. No hay dos índices distintos ni se confunde ninguno con `material_id`.

**Inicio y configuración.** `RunRequestV1={order_ids: int[]}` exige IDs positivos,
distintos y al menos uno; rechaza extras. No recibe geometría, método ni parámetros
cliente. Los cuatro parámetros provienen del snapshot backend vigente y se
publican en `optimization_started` y GET. Esto fija la fuente de configuración,
sin implementar todavía su proveedor o validación transaccional.

**Eventos.** `OptimizationEventV1` es una unión discriminada por `event`; todos
requieren `{schema_version:1, sequence>=1, event, id_optimizacion, occurred_at, data}`.
`occurred_at` es ISO 8601 UTC con zona explícita. `sequence` comienza en 1 y aumenta
por cada evento de la corrida; la secuencia completa será validada por T9.

| Evento | Payload v1 concretado |
|---|---|
| `optimization_started` | `metodo=FF`, `order_ids`, `total_units` global, claves `groups`, `configuracion`. |
| `group_started` | `id_tipo_vidrio`, `espesor_mm`, `total_units` del grupo. |
| `piece_started` | Pedido/pieza/unidad, clave material y contadores globales con `progress_pct`. |
| `piece_placed` | Campos de `PlacementV1`: trazabilidad completa, `stock_unit_index`, X/Y/ángulo, `resolution_mm`, `geometria` orientada/local; contadores globales y `material:StockV1` con geometría/área del material para pintar sin otra consulta. |
| `group_completed` | Clave material, contadores/progreso **del grupo**, `result_url` de GET como referencia durable de sus placements. GET durante cálculo es un snapshot, no promete persistir cada evento. |
| `metrics_calculated` | `metrics_available` y `metrics:MetricsV1\|null`. Sin material usado, false/null. |
| `optimization_completed` | `estado=COMPLETADA\|SIN_SOLUCION`, `completo`, contadores/progreso globales y `result_url`. Se emite también para fin normal sin solución; nunca implica confirmación. |
| `optimization_failed` | `estado=FALLIDA`, `code`, `message` seguro y `result_url`. Códigos: `CALCULATION_FAILED`, `EXECUTION_INTERRUPTED`, `RESULT_SAVE_FAILED`. |

`progress_pct` se deriva como Decimal de `placed_units / total_units * 100` y se
serializa como string, sin acumular intentos ni redondear a un porcentaje falso.
Los schemas rechazan discrepancias con los contadores. El adapter HTTP futuro
deberá construir mensajes seguros: nunca serializar directamente una excepción.
El fixture separa siete eventos del camino exitoso de un octavo tipo de evento
alternativo de fallo; no se emiten ambos terminales para una misma corrida.

El transporte futuro usa `application/x-ndjson`: un JSON UTF-8 por línea terminada
en `\n`. Un chunk de red puede contener media línea, varias líneas o dividir un
carácter UTF-8. UI debe usar decodificación incremental, acumular texto, separar
por salto de línea y parsear solo líneas completas; al terminar, un fragmento
incompleto o ausencia de terminal requiere consultar GET y no fabricar éxito.
La implementación/parsing de transporte pertenece a T9/UI, no a T1. No hay
reanudación ni reejecución automática por reconexión. Se conservan `201`/`Location`
para aceptación futura; tras headers, fallo por evento y consulta durable, sin
cambiar HTTP ni aplicar reset de `SIN_SOLUCION` a un crash.

**GET reconstruible (`RunResponseV1`).** Incluye ID, estado, método, pedidos,
configuración, `groups` con **todas las unidades solicitadas** y geometría original,
`placements`, `materials_used` (cada unidad física usada una sola vez),
`unplaced_units`, contadores/progreso, `completo`, `metrics_available`, métricas
nullable, `tiempo_computacional_ms` nullable, `confirmed` y `confirmable`.
Cada placement conserva contorno ya orientado, local a su bounding box, más X/Y
y resolución; se dibuja trasladando ese contorno sin recalcular FF ni rotarlo de
nuevo. Material conserva geometría útil y área: no se sustituye un retazo irregular
por AABB. Origen en esquina superior izquierda del material normalizado, Y hacia
abajo, mm y grados. T3 producirá el contorno orientado/local; T1 solo lo representa.
La geometría original puede contener coordenadas negativas, como en HU-015.

Unidades sin placement se identifican por pedido/pieza/índice y clave material;
`reason=PENDING` en ejecución, `NO_FIT` en SIN_SOLUCION, `INTERRUPTED` en FALLIDA.
`completo` expresa cobertura geométrica, mientras `estado` expresa estado durable;
ni siquiera 100% observado habilita confirmar hasta estado COMPLETADA. `confirmed`
es observación derivada de la confirmación posterior, no una columna nueva;
`confirmable` es elegibilidad de snapshot y no sustituye revalidación bajo locks.
Después de confirmar, el estado de corrida conserva COMPLETADA y confirmable=false.

`MetricsV1`: `aprovechamiento_pct`, `merma_mm2`, `planchas_nuevas_usadas`,
`retazo_recuperable_mm2`, `area_material_total_mm2`, `area_piezas_colocadas_mm2`,
`tiempo_computacional_ms`. El tiempo también se expone en GET cuando se midió una
corrida sin métricas disponibles. Métricas disponibles requieren los siete campos;
sin cálculo aún, el modelo permite null y no inventa ceros. Los cálculos y
restricciones finales de persistencia siguen en T8.

**Confirmación.** `POST /runs/{id_optimizacion}/confirm` no recibe body. El
identificador proviene del path y no acepta patrón/materiales del cliente.
`ConfirmResponseV1` incluye `{schema_version:1,id_optimizacion,confirmed:true,orders,
materials_consumed,remnants_created}`. Cada pedido lleva estado CONFIRMADO; consumo
enumera identidades físicas `(material_source,material_id,stock_unit_index)` sin
duplicados; el backend futuro agregará por fila para descontar cantidades. Cada
retazo creado incluye su ID, identidad del material fuente, posición local X/Y,
geometría rectangular exacta y área. Lista vacía si no se genera geometría válida.
Este schema no confirma ni consume inventario.

**Errores futuros (`ErrorResponseV1`).** Forma estable
`{"detail":{"code":"STOCK_CONFLICT","message":"…"}}`; mensajes seguros y sin SQL,
stack ni datos sensibles. Los errores de validación de rutas nuevas se adaptarán
a esta forma en T9. No cambia el `detail` histórico de HU-015.

| HTTP | Códigos | Operación/semántica |
|---|---|---|
| 401 | `UNAUTHENTICATED` | Sesión ausente/vencida. |
| 403 | `FORBIDDEN` | Capacidad no concedida. |
| 404 | `NOT_FOUND` | Pedido del lote o corrida ausente; nunca inicio parcial. |
| 409 | `STATE_CONFLICT`, `CONFIG_CONFLICT` | Inicio con estados/configuración conflictivos. |
| 409 | `STOCK_CONFLICT`, `ALREADY_CONFIRMED`, `STATE_CONFLICT` | Confirmación con stock/estados cambiados o repetida; rollback total. |
| 422 | `INVALID_INPUT`, `NOT_CONFIRMABLE` | Cuerpo/datos inválidos o resultado incompleto/no confirmable. |
| 500 | `INTERNAL_ERROR` | Fallo antes de headers o confirmación revertida; mensaje general. |
| Tras headers | Evento `optimization_failed` | Estado HTTP sin cambios; GET permite observar FALLIDA o estado pendiente de reconciliación si falla infraestructura. |

**Permisos puente y pendientes de integración.** `/start` y `/rasterize` conservan
`EJECUTAR_OPTIMIZACION`. Las capacidades futuras `.view/.execute/.confirm` y su
traducción temporal siguen pendientes con RBAC (§13): no se activan rutas nuevas
ni se conceden permisos por inferencia. UI puede desarrollar el consumer sobre
estos fixtures; los controles reales deberán esperar el guard backend acordado.
El contrato batch caller-owned de Orders descrito en §3 sigue pendiente de acuerdo
cross-branch; T1 no simula ese acuerdo ni introduce un port transaccional sin dueño.

Antes de T3/revisión siguiente: revisar el mapeo `physical_unit_index` →
`stock_unit_index`, strings Decimal, composición de placement y contorno orientado
local; cerrar el contrato batch de Orders y el puente RBAC antes de sus adaptadores.
El mínimo independiente de área recuperable no existe en Configuracion: permanece
pendiente de decisión humana, sin default inventado ni proveedor nuevo en T1.

Mensaje de integración preparado para `S1-optimization-ui`: «Contrato S1 v1 en
`run_schemas.py`, ejemplos en `fixtures/s1_contract_v1.json`. Inicio solo order_ids;
medidas Decimal como strings; siete eventos de éxito y terminal alternativo de
fallo; placements con contorno orientado/local y stock_unit_index; GET canónico;
confirm sin body y conflicto 409. Endpoints, transporte y guards nuevos aún no
implementados». Este texto queda disponible para el equipo; no se envía mediante
herramientas de mensajería en esta tarea.

### T2 — Problem normalization, expansión y grupos deterministas (1.5 SP)

- **Objetivo:** convertir snapshots de `1..N` pedidos en `OptimizationProblem`, `MaterialGroup` y `PieceUnit` sin perder trazabilidad.
- **Archivos/capas probables:** `domain/problem.py`, `domain/preparation.py`, pruebas en `tests/unit/optimization/`.
- **Dependencias:** T1.
- **Criterios verificables:** cantidad N crea N índices desde 1; no comparte placement; agrupa tipo/espesor exactos; ordena grupos y unidades con RN-06; material se toma de cada PIEZA; IDs invalidos fallan antes del motor.
- **Pruebas mínimas:** quantity 1/varias, 2 pedidos, multimaterial, misma pieza en distintos IDs, entradas permutadas producen mismo problema.
- **Evidencia esperada:** salida determinista de fixture y resultados de tests focalizados.

### T3 — Rotación discreta, máscaras y caché por corrida (1.5 SP)

- **Objetivo:** preparar orientaciones mediante geometría mm transformada y reutilizar raster sin interpolación.
- **Archivos/capas probables:** `domain/rotation.py`, extensión localizada de `domain/rasterizer.py` o módulo de máscaras preparado, `tests/optimization/`.
- **Dependencias:** T2; conservar TA-005/006/007.
- **Criterios verificables:** secuencia Decimal `0.. <360`; normalización; ángulos duplicados omitidos solo al ser la misma máscara; círculo no rerasterizado; key de caché incluye geometría, resolución y ángulo; raster material/pieza comparte resolución.
- **Pruebas mínimas:** 0/5/355, paso 360, círculo, simetrías de rectángulo/cuadrado, polígono irregular, cambios de resolución y origen normalizado.
- **Evidencia esperada:** fixtures de máscaras/orientaciones; tests existentes de raster continúan pasando.

### T4 — Motor First Fit y recorrido de posiciones (2 SP)

- **Objetivo:** implementar el motor puro First Fit con enumeración row-major y primer placement aceptado.
- **Archivos/capas probables:** `domain/first_fit.py`, reutilizar `placement.py`, `domain/problem.py`; tests `tests/optimization/` y/o `tests/unit/optimization/`.
- **Dependencias:** T2 y T3.
- **Criterios verificables:** orden de stock/orientación/row/column estable; AABB solo descarte; invoca `SheetLayout.check/place`; detiene intento en primera combinación válida; reporte de completa solo con todas las unidades; sin dependencia externa.
- **Pruebas mínimas:** varias posiciones (acepta primero row-major), ninguna válida, dos materiales candidatos, bounds/margin/separation/overlap, retazo circular/poligonal y determinismo.
- **Evidencia esperada:** tests de unit placement y patrón reproducible pequeño.

### T5 — Puerto y adaptador de stock compatible (1.5 SP)

- **Objetivo:** consultar stock activo compatible una vez por grupo y expandir cantidad de plancha como unidades físicas lógicas.
- **Archivos/capas probables:** `application/ports.py`, DTO, `infrastructure/stock_adapter.py`, composición en `presentation/dependencies.py`, pruebas unitarias/integration.
- **Dependencias:** T1; DTO de grupo T2 puede acordarse en paralelo.
- **Criterios verificables:** filtro tipo+espesor+estado y plancha cantidad >0; retazos antes de planchas; suborden fecha DESC/ID DESC; plancha `stock_unit_index=1..cantidad`; retazo unitario; query por grupo; sin locks/reservas durante simulación.
- **Pruebas mínimas:** incompatibles/inactivos/cantidad cero excluidos; categoría y desempate; varias unidades de una fila distinguibles; consulta por grupo.
- **Evidencia esperada:** snapshot de candidatos SQL ordenado y tests de adapter; no hay decremento/movimientos.

### T6 — Asociación multipedido ORM y migración Alembic (2 SP)

- **Objetivo:** evolucionar el vínculo directo de `Optimizacion` sin perder el historial actual.
- **Archivos/capas probables:** `docs/database/convergencia-v1-1.md`, `backend/app/models.py`, nueva revisión desde `ta036a1b2c3d`, `backend/tests/contracts/`, `backend/tests/unit/` y `backend/tests/integration/`.
- **Dependencias:** diseño §5; puede avanzar en paralelo con T2–T5.
- **Criterios verificables:** asociación con PK compuesta/FKs/índices; backfill 1:1 histórico; no uniqueness global por pedido; downgrade falla antes de DDL si detecta run multipedido; una sola Alembic head; contrato ORM coherente.
- **Pruebas mínimas:** PostgreSQL temporal vacía e histórica; varias relaciones nuevas; FK/PK/backfill; rollback de upgrade inválido; downgrade uno-a-uno y downgrade multipedido rechazado.
- **Evidencia esperada:** grafo de revisiones y reporte de migración aislada; no ejecutar sobre base compartida.

### T7 — Config snapshot, UoW y aceptación atómica del lote (1.5 SP)

- **Objetivo:** crear preflight y transacción de inicio compartida con Orders, con un único dueño de commit.
- **Archivos/capas probables:** `application/ports.py`, `application/unit_of_work.py`, `application/use_cases.py`, `infrastructure/orders_adapter.py`, `infrastructure/unit_of_work.py`, `dependencies.py`.
- **Dependencias:** T1, T6 y contrato batch de rama Orders; T5 para interoperabilidad de la sesión.
- **Criterios verificables:** 1..N IDs explícitos; locks en orden; se valida todo antes de cambio; configuración única completa snapshot; creación de run+FF+asociaciones+estados en commit único; rollback sin subset; no se mantiene transacción durante motor.
- **Pruebas mínimas:** una lista válida N=1 y N>1; pedido ausente/no pendiente/sin piezas; config cero/múltiple/paso null; fallo de persistencia => rollback de todos.
- **Evidencia esperada:** prueba PostgreSQL del inicio y especificación de integración Orders cerrada.

### T8 — Persistencia de patrón, métricas y terminales de cálculo (2 SP)

- **Objetivo:** conectar el motor con result DTO y persistir completo/SIN_SOLUCION sin tocar stock.
- **Archivos/capas probables:** `domain/metrics.py`, `domain/residual.py`, `application/use_cases.py`, `infrastructure/persistence_adapter.py`, schemas y tests.
- **Dependencias:** T4–T7.
- **Criterios verificables:** únicamente FF; JSONB versionado reconstruible; materiales propuestos agregados sin consumo; métricas R4 coherentes; `COMPLETADA`/`OPTIMIZADO` atómicos; `SIN_SOLUCION`/reset completo a `PENDIENTE`; caso sin material no viola `area_material_total_mm2 > 0`; residuos solo exactos/validables.
- **Pruebas mínimas:** patrón round-trip sin motor; solución completa; parcial/no stock; métricas con retazo/plancha; rectángulo residual máximo/tie-breaks y revalidación; falta de material para denominador; error final transaction rollback.
- **Evidencia esperada:** result JSON de fixture con áreas verificadas manualmente en unit test; comparación de estado antes/después, inventario idéntico.

### T9 — Streaming NDJSON y endpoints nuevos (1.5 SP)

- **Objetivo:** transportar eventos vivos y exponer estado/result durable sin cambiar HU-015.
- **Archivos/capas probables:** `presentation/router.py`, `schemas.py`, `serialization.py`, dependencies, `backend/tests/api/optimization/`.
- **Dependencias:** T1, T7 y T8; contratos de stream ya disponibles para UI.
- **Criterios verificables:** POST crea/acepta y stream produce eventos durante cálculo; sequence estable y progreso correcto; GET reconstruye patrón; desconexión/fallo no reporta éxito falso; compatibilidad de `/start` y `/rasterize`; error stream sanitized.
- **Pruebas mínimas:** integración API stream con chunks parciales, event order, auth y 401/403/404/409/422/500 pre/post headers.
- **Evidencia esperada:** captura de líneas NDJSON con timestamps y `piece_placed` reales; schema response GET después del run.

### T10 — Caso de uso de confirmación y UoW de Inventory (2 SP)

- **Objetivo:** revalidar resultado/stock y confirmar todo el lote con una transacción única.
- **Archivos/capas probables:** `application/use_cases.py`, ports, `infrastructure/unit_of_work.py`, stock/persistence adapter, `presentation/router.py`, Inventory integration tests.
- **Dependencias:** T5–T8; port caller-owned de Orders e Inventory.
- **Criterios verificables:** patrón solo desde DB; lock pedidos/recursos en orden; agrupa cantidad plancha; consumo retazo unitario; movimientos reales y nuevos retazos exactos; pedidos CONFIRMADO; un solo commit; cualquier discrepancia rollback y 409; segundo submit no duplica.
- **Pruebas mínimas:** complete; incompleta/no confirmable; candidato desactivado/cantidad insuficiente; rollback después de cada tipo de escritura; prueba de repetición.
- **Evidencia esperada:** estado/deltas/movimientos antes-después en PostgreSQL temporal y ausencia de stock mutado en simulación.

### T11 — Concurrencia y garantías PostgreSQL (1.5 SP)

- **Objetivo:** comprobar las garantías bajo operaciones simultáneas sobre lote, plancha, retazo y mismo run.
- **Archivos/capas probables:** `backend/tests/integration/optimization/`, fixture PostgreSQL; utilidades existentes de concurrencia.
- **Dependencias:** T6, T7 y T10.
- **Criterios verificables:** dos confirmaciones del mismo run, dos runs compitiendo por última plancha/retazo, e inicio con pedido compartido no dejan doble consumo ni estado parcial; lock order no deadlock reproducible.
- **Pruebas mínimas:** PostgreSQL real con sesiones separadas; aserciones después del commit/rollback para todos pedidos, stock, movimientos y sobrantes.
- **Evidencia esperada:** resultado de escenarios concurrentes aislados, registro de bloqueo/conflicto y DB íntegra.

### T12 — Recuperación controlada, errores, permisos y regresión backend (1 SP)

- **Objetivo:** cerrar fallos terminales y verificar regresión del contrato existente antes de integrar UI.
- **Archivos/capas probables:** `application/use_cases.py` (reconcile explicit), error mapper/router, `backend/tests/api/optimization/`, tests Orders/Inventory/Optimization existentes.
- **Dependencias:** T7–T11; confirmar alcance operativo de reconciliación con reviewer antes de exponer acción.
- **Criterios verificables:** SIN_SOLUCION queda distinto de FALLIDA; crash no reinicia solo; reconciliación requiere estado durable no completo, pedidos EN_OPTIMIZACION y cero movimiento consumo; condiciones no coincidentes paran sin mutación; endpoints HU-015/regresiones conservados; permisos backend mapeados.
- **Pruebas mínimas:** excepción durante motor, cancelación, stale run, reconciliación segura/denegada, API HU-015 y tests de Orders/Inventory afectados.
- **Evidencia esperada:** matriz de terminales y regresiones con comandos/resultados reales. Si una transición operativa no se aprueba, dejar API/acción fuera y documentar el bloqueo sin auto-reset.

### T13 — Integración de rama, reproducibilidad y evidencia (1.5 SP)

- **Objetivo:** demostrar el vertical slice y los CA de backend con contratos listos para la rama UI.
- **Archivos/capas probables:** tests unit/api/integration; documentación en `docs/evidence/sprint-01/S1-OPTIMIZATION-FIRST-FIT/`; actualización posterior de SPEC/PLAN solo a partir de resultados observados.
- **Dependencias:** T1–T12; disponibilidad de cambios compatibles de Orders/RBAC/UI para pruebas conjuntas.
- **Criterios verificables:** un pedido/una agrupación atraviesa el flujo general y se visualiza por contrato; después se verifica N y multimaterial; progreso proviene durante ejecución; confirmación/rollback/concurrencia pasan; patrón repetido es determinista; HU-015 continúa regresión verde.
- **Pruebas mínimas:** benchmark de fixtures, API end-to-end backend y Playwright conjunto cuando UI esté integrada; no usar datos compartidos sin autorización de sus responsables.
- **Evidencia esperada:** comandos, resultados sin inventar y ejemplos sanitizados del patrón/eventos. E2E UI puede quedar coordinado cross-branch, pero no puede quedar sin contrato ni bloquear pruebas backend.

**Estimación total propuesta: 20.5 SP (123 horas de curso).** Camino de desbloqueo más temprano para UI: T1 (1 SP). Vertical slice de backend: T1 → T2 → T3 → T4 → T5/T6 → T7 → T8 → T9. Confirmación segura continúa por T10 → T11 → T12; la entrega no se considera completa antes de cerrar esa ruta crítica.

## Historial del plan

| Fecha | Estado | Cambio |
|---|---|---|
| 16/10/2026 | Draft | PLAN técnico y TASKS derivados de SPEC Reviewed. Auditoría de rama, capas, Orders/Inventory, modelos, configuración, endpoints, raster y Alembic; definición de asociación multipedido, DTO normalizado, stock, First Fit row-major, NDJSON v1, persistencia, métricas, límites transaccionales, confirmación y ruta crítica. No se implementó código ni se ejecutaron pruebas para este PLAN. Revisión humana del PLAN pendiente. |
| 16/10/2026 | Approved | Fabricio Danniel Aguilar Chávez revisó y aprobó técnicamente este PLAN para implementación. Se aprueban la descomposición técnica, sus contratos, decisiones de arquitectura/persistencia/transacciones, estrategia de pruebas y TASKS. No se atribuyen implementación, pruebas ejecutadas ni evidencia de producto. |

## Avance autónomo T3–T6 (numeración de sesión, 16/10/2026)

Se conserva el PLAN **Approved**, la SPEC **Reviewed** y la numeración histórica.
La instrucción de sesión redefine los identificadores operativos: T3 sesión = T2
histórica (preparación), T4 sesión = T5 histórica (stock), T5 sesión = T3 histórica
(rotación), T6 sesión = T4 histórica (motor). La migración T6 histórica y los
bloques de persistencia/streaming/estados/confirmación siguen excluidos; no se
confunden con el vertical slice puro de esta sesión.

| Tarea de sesión | Estado | Evidencia |
|---|---|---|
| T3 preparación (T2 histórica) | Ejecutada; 22 focalizadas, 308 regresión aprobadas | [T3](../evidence/sprint-01/S1-OPTIMIZATION-FIRST-FIT/t3-preparation.md) |
| T4 stock (T5 histórica) | Ejecutada; 8 focalizadas y 743 regresión aprobadas | [T4](../evidence/sprint-01/S1-OPTIMIZATION-FIRST-FIT/t4-stock.md) |
| T5 rotación (T3 histórica) | Ejecutada; 25 focalizadas y 348 regresión aprobadas | [T5](../evidence/sprint-01/S1-OPTIMIZATION-FIRST-FIT/t5-rotation.md) |
| T6 motor (T4 histórica) | Ejecutada; 26 focalizadas, 374 Optimization y 1709 backend aprobadas | [T6](../evidence/sprint-01/S1-OPTIMIZATION-FIRST-FIT/t6-first-fit.md) |

No se afirma aceptación integral, cierre ni verificación de la SPEC. El baseline
E2E histórico es 20 passed / 4 failed Orders (HTTP 422), fuera de esta rama.
La rama Orders dd10ec0 ya envía material/espesor por pieza; integrar y verificar
corresponde a su dueño. UI fixture diverge de T1 en casing, nombres y Decimal:
convergencia futura, sin alterar unilateralmente el contrato v1. RBAC incorpora
permisos dinámicos; no se duplica. Refs observados por tarea se guardan en evidencia.

Decisión técnica T4: adapter sobre DTO/lecturas públicas InventoryRepository; dos lecturas de catálogo dentro de una read_transaction por consulta lógica de grupo, cache exclusivo por corrida. No se importa Inventory Infrastructure ni se inventa consulta SQL cross-module. Filtrado exacto y orden fecha DESC/ID DESC conservan §7. Ver evidencia T4 para coste y evolución futura del port.

Decisiones técnicas T5: precisión RN-04 de TA-005/006 explícita en contorno devuelto; bridge Decimal/config con round-trip exacto y coordenadas aritméticas con error máximo de conversión 1e-12 mm antes de redondeo a 6 decimales. Excesos de rango/presupuesto producen error, nunca placement supuesto. Presupuestos por máscara iguales a HU-015 y máximo técnico de 10000 orientaciones. Cache por corrida y deduplicación solo por máscara completa, no AABB. Ver evidencia T5 para límites conocidos del raster histórico.

Decisiones técnicas T6: motor puro con candidato → orientación → fila → columna;
conserva el suborden del provider y acepta primera combinación válida. Layout
independiente por identidad física, máscaras compartidas inmutables. Distancias
Decimal usan ceil racional exacto antes del puente TA-007 (incluido sub-epsilon).
Hitos internos tipados, sin HTTP. Resultado parcial conserva placements diagnósticos
y no habilita confirmación en T1. No se calcula métrica ni se cambia estado durable.
El puente Application recibe snapshots persistidos existentes, sin inventar batch
transaccional. El test de integración demuestra dos pedidos persistidos y cuatro
placements sobre dos unidades de plancha sin consumo ni cambios de estado.
Ejemplos ejecutados y logs completos están en evidencia T6. Regresión final:
1709 passed, 1 warning; una sola Alembic head ta036a1b2c3d. No se integran otras
ramas, no se implementa frontend y no se modifica el estado Reviewed de SPEC.

Próxima revisión de Fabricio: revisar los cuatro commits/evidencias del vertical
slice y coordinar con Orders/RBAC/UI las APIs batch, guards y mapeo al contrato v1
antes de habilitar endpoints. La migración, persistencia/métricas, streaming,
estados, confirmación y concurrencia permanecen pendientes según sus tareas
históricas; este avance no equivale al cierre de Sprint ni SPEC Verified.
