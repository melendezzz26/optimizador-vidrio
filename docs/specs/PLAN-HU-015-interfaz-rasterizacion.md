# PLAN-HU-015 — Interfaz de rasterización

## Información general

| Campo | Valor |
|---|---|
| Estado del plan | **Approved** |
| SPEC de referencia | [SPEC-HU-015-interfaz-rasterizacion.md](SPEC-HU-015-interfaz-rasterizacion.md), **Reviewed** |
| Autor de la SPEC y del plan | Fabricio Melendez |
| Reviewer de la SPEC | Fabricio Aguilar |
| Revisión humana de la SPEC | 13/10/2026; aprobada para implementación / planificación técnica |
| Reviewer del plan | Fabricio Aguilar |
| Fecha de aprobación del plan | 13/10/2026 |
| Decisión del plan | Aprobado para implementación. |
| Base auditada | `35d1e91` — `docs(HU-015): aprobar especificacion de interfaz raster` |
| Rama | `feature/HU-015-interfaz-rasterizacion` |
| Fecha de planificación | 13/10/2026 |

Documento de planificación aprobado para implementación tras revisión humana de Fabricio Aguilar el 13/10/2026, sin código implementado, pruebas creadas/ejecutadas, benchmark ejecutado ni evidencia funcional nueva. La aprobación del plan queda registrada de forma independiente de la aprobación de la SPEC. La SPEC conserva su estado Reviewed y sus 23 criterios de aceptación; no se modifica en esta entrega.

**Descomposición técnica propuesta para implementación.**

**Descomposición técnica propuesta; no corresponde a la división histórica T1/T2/T3 del backlog, la cual no fue localizada.**

## 1. Verificación inicial y convención documental

Se consultaron `git status`, `git branch --show-current` y `git log --oneline --decorate -5`, también al retomar la tarea: rama esperada, árbol limpio y HEAD `35d1e91`. La SPEC Reviewed está presente con Fabricio Melendez como autor, Fabricio Aguilar como reviewer y fecha 13/10/2026. No se hizo fetch ni merge; el trabajo se basa en ese HEAD local y no afirma sincronización remota nueva.

[CONTRIBUTING.md](../../CONTRIBUTING.md), [docs/README.md](../README.md) y [SPEC-TEMPLATE.md](SPEC-TEMPLATE.md) establecen documentos por identificador en `docs/specs/`, con impacto técnico, pruebas y tareas dentro del documento. TA-036 incluye su descomposición en una sección de la SPEC; HU-013 y HU-014 también concentran su contenido por trabajo. No se encontró una estructura moderna de directorios con `plan.md`/`tasks.md`.

Se sigue ese patrón con **un archivo complementario por identificador**, `docs/specs/PLAN-HU-015-interfaz-rasterizacion.md`, que reúne plan técnico y tareas en §10. No se crean `plan.md`, `tasks.md` ni directorios redundantes, y no se mueve ni reabre la SPEC aprobada. El prefijo PLAN identifica este complemento, sin presentarlo como una convención de nombres preexistente.

No se encontraron otros planes que establezcan un estado documental propio; la plantilla vigente define estados para SPEC. Para este plan se utiliza **Approved**, según el cierre de aprobación solicitado, sin cambiar la convención ni el estado Reviewed de la SPEC.

## 2. Fuentes técnicas auditadas

Las rutas de esta sección describen capacidades existentes en la base auditada; los nombres nuevos de las secciones posteriores son propuestas.

| Fuente | Hallazgo que condiciona el plan |
|---|---|
| [SPEC HU-015](SPEC-HU-015-interfaz-rasterizacion.md), §§5, 8–11, 13 y 16 | Inicio explícito válido `PENDIENTE → EN_OPTIMIZACION`; raster por pieza posterior sin transición repetida; P-01 benchmark, P-02 historia no localizada y P-03 diseño del inicio pendientes. |
| [ADR-001](../adr/ADR-001-seleccion-arquitectura.md), [ADR-002](../adr/ADR-002-operacion-pre-raster.md), CONTRIBUTING | Monolito modular, capas Clean; dominio independiente de HTTP/ORM; FF/BF/WF fuera del alcance. Prevalece la regla vigente de registro sin stock de TA-036/HU-015 frente al texto histórico de ADR-002. |
| [TA-005/006](SPEC-TA-005-TA-006-rasterizacion.md), [TA-007](SPEC-TA-007-validacion-geometrica.md) | Dominio geométrico existente; API y UI no implementadas por esas tareas. Placement y rasterización de material no se invocan en HU-015. |
| [raster_mask.py](../../backend/app/modules/optimization/domain/raster_mask.py), [rasterizer.py](../../backend/app/modules/optimization/domain/rasterizer.py), [placement.py](../../backend/app/modules/optimization/domain/placement.py) | `RasterMask` inmutable; `row_runs(row)` disponible; `rasterize_geometry(geometry, resolution_mm=5.0)` despacha las tres formas. El dominio no valida por sí solo toda la convexidad de datos históricos. Las otras capas de Optimization solo tienen reservas `__init__.py`. |
| [Orders ports](../../backend/app/modules/orders/application/ports.py), [use_cases.py](../../backend/app/modules/orders/application/use_cases.py), [repositories.py](../../backend/app/modules/orders/infrastructure/repositories.py) | `OrderRepositoryPort.get_order` devuelve dict completo o `None`; lectura consistente de cabecera/piezas con un SELECT. No existe start ni actualización genérica de estado. Update/cancel bloquean cabecera con `FOR UPDATE`, revalidan `PENDIENTE`, hacen commit/rollback y no sirven para iniciar. |
| [Orders router](../../backend/app/modules/orders/presentation/router.py), [schemas](../../backend/app/modules/orders/presentation/schemas.py), [dependencies](../../backend/app/modules/orders/presentation/dependencies.py), [geometry](../../backend/app/modules/orders/domain/geometry.py) | GET paginado y detalle existentes; entradas estrictas; conflictos actuales `409`; geometría canónica en `geometria`, polígono con `vertices_mm`; `espesor_mm`/`area_mm2` como Decimal. Se reutilizan reglas geométricas de Orders mediante su frontera de aplicación. |
| [HU-006](SPEC-HU-006-registrar-pedido.md), [HU-013](SPEC-HU-013-gestion-pedidos.md), [TA-036](SPEC-TA-036-saneamiento-funcional.md) | Las fuentes antiguas tienen divergencias sobre material global y códigos de conflicto: se sigue código vigente y HU-015, con material por pieza, `409` y registro sin stock. Edición/cancelación solo para `PENDIENTE`. |
| [models.py](../../backend/app/models.py), [migración R1](../../backend/alembic/versions/e1a2b3c4d5f6_r1_identidad_inventario_pedidos.py) | `pedidos.estado` y su CHECK ya incluyen los cinco estados; `Pieza.geometria` JSONB, cantidad y material por pieza existen. No hay necesidad de tabla ni migración nueva. |
| [HU-001](SPEC-HU-001-inicio-login.md), [auth dependencies](../../backend/app/modules/authentication/presentation/dependencies.py), [permissions.py](../../backend/app/core/permissions.py), [matriz](../seguridad/matriz_permisos.md) | `require_permission` usa rol vigente; sesión ausente/vencida `401`, permiso insuficiente `403`. `EJECUTAR_OPTIMIZACION`: Administrador/Operario. |
| [App.jsx](../../frontend/src/App.jsx), [Sidebar](../../frontend/src/shared/components/Sidebar.jsx), [AppShell](../../frontend/src/shared/components/AppShell.jsx), [NavigationContext](../../frontend/src/shared/components/NavigationContext.js) | Navegación por estado; features Orders/Inventory/Users. No React Router ni vista Optimization integrada. |
| [ordersApi.js](../../frontend/src/features/orders/ordersApi.js), [permissions.js](../../frontend/src/features/authentication/permissions.js), [geometryScaling.js](../../frontend/src/features/orders/geometryScaling.js), [CustomPieceEditor.jsx](../../frontend/src/features/orders/CustomPieceEditor.jsx) | `listOrders`, `getOrder`, `listOrderMaterials` y cancelación/token reutilizables; falta permiso UI específico de ejecución. El editor usa SVG y transformación visual, pero no se reutiliza como rasterizador ni se reconstruye la geometría desde medidas. |
| [feedback compartido](../ui-ux/feedback-compartido.md), [base visual](../ui-ux/inventario-base-visual.md), shared/components y features | PageHeader/PageCard/ActionBar, estados accesibles y tokens existentes. Optimization está reservada con `.gitkeep`. |
| [tests/optimization](../../backend/tests/optimization/), [tests Orders API](../../backend/tests/api/orders/test_orders_api.py), [repositorio Orders tests](../../backend/tests/integration/modules/orders/infrastructure/test_repositories.py) | Raster estándar/polígono/material/placement y `row_runs` ya cubiertos. Orders cubre rollback, conflictos y registro sin stock; el nuevo cierre añadirá carreras reales start/update/cancel. |
| [unit Orders](../../backend/tests/unit/modules/orders/), [auth API](../../backend/tests/api/test_auth_api.py), [permission API](../../backend/tests/api/test_require_permission.py), [sidebar tests](../../frontend/src/shared/__tests__/sidebarNavigation.test.jsx), [staging navigation tests](../../frontend/src/shared/__tests__/stagingNavigation.test.jsx) | Patrones disponibles para dobles de puertos, validación de capas, roles y navegación por estado/subpath. Son fuentes inspeccionadas, no pruebas ejecutadas ahora. |
| [playwright.config.js](../../frontend/playwright.config.js), [E2E servidor](../../backend/tests/e2e_server.py), [HU-012 E2E](../../frontend/tests/e2e/hu012-client-order.spec.js) | Configuración actual ya levanta Vite 5173 y API 8017 con PostgreSQL temporal; hay flujos reales con login. Algunos textos antiguos de testing describen solo el harness HU-007: no reflejan toda la configuración actual. |
| [experiments/raster](../../experiments/raster/README.md), [raster_evidence.py](../../experiments/raster/scripts/raster_evidence.py), [testing](../testing/README.md), [evidence](../evidence/README.md) | Script anterior mide raster/área y produce SVG; no basta como benchmark del DTO HTTP. Experimentos separados de aplicación, resultados generados ignorados y evidencia seleccionada en `docs/evidence/`. |

## 3. Decisiones de proceso y consistencia

### 3.1 Separación formal de operaciones

**A. `POST /api/optimization/start`:** acepta solo `id_pedido`, autoriza, recupera el pedido bajo control de concurrencia, verifica `PENDIENTE` y piezas válidas y confirma únicamente la transición a `EN_OPTIMIZACION`. No rasteriza, no crea `Optimizacion`/`EjecucionOptimizacion`, FF/BF/WF, métricas, preview ni movimientos de stock. El inicio real en esta HU es la habilitación persistida del proceso operacional del pedido; no se presume un job en background ni una optimización terminada.

**B. `POST /api/optimization/rasterize`:** acepta pedido, pieza y resolución; permite únicamente `EN_OPTIMIZACION`. Recupera los datos vigentes de Orders, valida pertenencia/geometría/presupuesto, llama una vez al dominio por pieza y devuelve la máscara; no realiza escrituras ni transiciones.

Esto coincide con texto explícito de la SPEC Reviewed (§§5, 8, 9 y 11). No hay contradicción respecto de admitir solo `EN_OPTIMIZACION` en rasterize ni se requiere modificar la SPEC. Consultar/seleccionar/cambiar resolución no inicia; `PENDIENTE` es elegible para start, no para rasterize operacional.

### 3.2 Repetición, concurrencia y errores

Se elige **rechazo explícito por conflicto**, sin clave de idempotencia nueva: start sobre `EN_OPTIMIZACION`, `OPTIMIZADO`, `CONFIRMADO` o `CANCELADO` devuelve `409`, sin escrituras. Dos inicios concurrentes producen un único `200` y un `409`; nunca dos transiciones silenciosas. Esto define el comportamiento de repetición permitido por el requisito, sin afirmar que ambos intentos sean éxitos idempotentes.

**Requisito técnico obligatorio de T1:** start debe garantizar que `PENDIENTE → EN_OPTIMIZACION` sea una transición atómica frente a solicitudes concurrentes, sin dos inicios exitosos ni efectos duplicados.

Escenario obligatorio: Pedido #10 está `PENDIENTE` y las solicitudes A y B intentan iniciarlo simultáneamente. Exactamente una realiza y confirma la transición, con `200`; la otra detecta que el pedido ya no está `PENDIENTE` y responde `409 Conflict`. El estado final es `EN_OPTIMIZACION`, con una sola transición confirmada y sin efectos duplicados. No se presupone que A deba ganar: cualquiera puede ser la solicitud exitosa.

**Mecanismo pendiente de elección en T1:** evaluar las siguientes alternativas frente al repositorio SQLAlchemy/Orders existente, sus transacciones y las carreras con edición/cancelación. No se fija una alternativa únicamente por intuición ni se convierte el bloqueo actual de update/cancel en una decisión automática para start.

| Alternativa | Garantía que debe verificarse |
|---|---|
| A. Bloqueo de fila dentro de una transacción, por ejemplo `SELECT ... FOR UPDATE` | Leer y validar el estado/piezas protegidos, efectuar la transición y confirmar dentro de la misma transacción; el segundo intento observa el estado ya cambiado. |
| B. Actualización condicional / compare-and-set | `UPDATE pedidos SET estado = 'EN_OPTIMIZACION' WHERE id_pedido = :id_pedido AND estado = 'PENDIENTE'`; comprobar exactamente una fila actualizada para confirmar éxito. Si no se actualiza ninguna, distinguir pedido inexistente (`404`) de estado no elegible (`409`). Coordinar también la validación de piezas con edición/cancelación, sin validar una lectura obsoleta. |

T1 elegirá y justificará la alternativa que mejor encaje con Orders, con evidencia de consistencia real. El mecanismo SQL queda encapsulado en su persistencia; Domain/Application expresan la transición y sus resultados mediante puertos, sin depender del SQL elegido.

Secuencia funcional/transaccional requerida para T1, independiente de esa elección:

1. Tras autenticación/autorización, abrir/adoptar la unidad de trabajo de la petición. Acceder al pedido mediante el contrato de Orders, con la protección de concurrencia seleccionada en T1.
2. Si no existe: `404`. Si no está `PENDIENTE`: `409`. Leer sus piezas de forma coherente con la validación y la transición dentro de la operación atómica, también frente a update/cancel.
3. Exigir al menos una fila y validar **todas las piezas del pedido**: cantidad positiva, pertenencia, forma canónica soportada, números finitos y geometría válida usando las reglas de Orders. Un pedido parcialmente corrupto se rechaza entero con `422`; no se ignoran filas inválidas ni se fabrica geometría. No reconsultar disponibilidad de stock ni exigir que material histórico siga activo para rasterizar.
4. Validar que las piezas sean rasterizables y estimar el presupuesto a la resolución inicial 5.0, sin construir máscaras. La SPEC exige validación de parámetros/presupuesto previa al inicio: como start recibe solo ID, se evalúa ese baseline. Las resoluciones elegidas posteriormente se validan en cada rasterize; un cambio de resolución no repite start. Una pieza que no supera el presupuesto inicial impide iniciar, con motivo visible.
5. Solicitar `PENDIENTE → EN_OPTIMIZACION` mediante la operación específica de Orders y comprobar que este intento obtuvo el único inicio válido. Si se elige compare-and-set, exigir exactamente una fila actualizada; un segundo intento no es un éxito silencioso. Commit de la unidad de trabajo y solo después devolver éxito. Capturar los datos mínimos de respuesta antes del commit, sin una lectura ORM posterior que convierta un commit exitoso en un falso fallo.
6. Cualquier validación o fallo anterior al commit provoca rollback y no deja la transición aplicada. No ejecutar raster dentro de esta transacción; si se usa bloqueo, no mantenerlo durante el cálculo raster.

La alternativa elegida debe coordinar start con edición/cancelación: si editar gana, start relee las piezas finales; si cancelar gana, start falla; si start gana, update/cancel rechazan el estado avanzado sin reemplazar piezas. No se reutilizan `update_order` ni `cancel_order` para cambiar estado: sus commits internos y sus efectos no corresponden a start. Las nuevas primitivas transaccionales no harán commits independientes.

Un timeout después del commit puede ocultar un inicio exitoso. La UI conserva el ID y consulta `GET /api/orders/{id_pedido}`: si está `EN_OPTIMIZACION`, continúa sin otro start; si sigue `PENDIENTE`, permite reintento explícito; en otro estado, bloquea y explica. No reintentar POST automáticamente. Un error raster posterior deja el pedido `EN_OPTIMIZACION`, permite corregir resolución/reintentar el cálculo y no revierte el inicio ni marca `OPTIMIZADO`/`CONFIRMADO`. La continuidad conceptual posterior sigue siendo `PENDIENTE → EN_OPTIMIZACION → OPTIMIZADO → CONFIRMADO`; HU-015 no implementa sus dos últimos pasos y `CANCELADO` conserva sus reglas.

## 4. Arquitectura backend propuesta

Se mantiene `Presentation → Application → Domain`, con Infrastructure implementando puertos. Los nombres de clases, métodos y archivos que siguen aún no existen.

| Capa | Diseño propuesto |
|---|---|
| Optimization/Domain | Reutilizar `RasterMask`, `RasterizationError`, `rasterize_geometry` y conservar placement. Sin FastAPI, SQLAlchemy, Pydantic ni imports de Orders. No modificar RasterMask: `row_runs` ya satisface el contrato. |
| Optimization/Application | `StartOptimizationUseCase`, `RasterizeOrderPieceUseCase`; puertos estrechos para lectura de pedido/pieza, validación persistida de Orders y unidad de trabajo con transición controlada. Errores de aplicación para ausencia/conflicto/validación/presupuesto; no usar HTTPException aquí. Política de recursos y DTO internos sin ORM. |
| Optimization/Infrastructure | Adaptador por composición hacia los contratos de aplicación de Orders y unidad de trabajo SQLAlchemy. Traduce datos planos y Decimal cuando corresponda, sin declarar otras entidades Pedido/Pieza ni consultas paralelas a esas tablas. |
| Orders/Application | Publicar la frontera mínima que falta para lectura coherente y transición atómica específica, además del puerto de lectura existente; exponer validación de piezas persistidas reutilizando GeometryValidator. Ninguna dependencia de Optimization, FastAPI, ORM ni del mecanismo SQL elegido. |
| Orders/Infrastructure | Extensión localizada de `SQLAlchemyOrderRepository` para garantizar la transición atómica con el mecanismo elegido y justificado en T1, dentro de la transacción de start. Conserva las entidades y reglas de persistencia existentes. |
| Optimization/Presentation | `router.py`, `schemas.py`, `dependencies.py`, serializador de rangos y mapeo seguro de errores. Ambos POST usan `require_permission("EJECUTAR_OPTIMIZACION")`. Registrar router en `backend/main.py` solo al implementar T1. |

### 4.1 Puertos y adaptación elegida

Contratos propuestos, expresados como responsabilidades y nombres orientativos:

- `OptimizationOrderReader.get_order(id_pedido)`: lectura coherente de cabecera y piezas, reutilizando por composición `OrderRepositoryPort.get_order`; búsqueda de la pieza dentro del pedido leído, sin endpoint/CRUD paralelo.
- `PersistedOrderPiecesValidator.validate(piezas)`: frontera de aplicación de Orders que aplica sus validadores geométricos existentes y verifica coherencia con `tipo_forma`; devuelve datos canónicos o error, nunca ORM ni geometría reconstruida.
- `OptimizationStartUnitOfWork`: contexto con lectura coherente del pedido, `transition_pending_to_optimization(id_pedido)`, commit y rollback. StartOptimizationUseCase valida entre la lectura y la actualización; la salida del contexto sin commit revierte. El adaptador delega la transición atómica a una nueva interfaz estrecha de Orders, por ejemplo `OrderOptimizationStatePort`, y emplea la misma sesión para todas sus operaciones. El puerto expresa éxito/ausencia/conflicto y las garantías de consistencia, sin exponer bloqueo SQL ni compare-and-set a Domain/Application.

Se elige **composición del repositorio/puertos de Orders con un adaptador dedicado de Optimization**, ampliando solo la capacidad de estado ausente. Usar directamente el amplio repositorio de Orders desde ambos casos de uso los acoplaría a catálogo/CRUD; un repositorio ORM independiente en Optimization duplicaría lectura de piezas y disciplina de concurrencia. Las implementaciones concretas se conectan en dependencies; los adaptadores reciben interfaces, sin importar otro repositorio concreto entre módulos. Los snapshots dict/DTO son datos de intercambio, no copias de entidades de negocio.

Responsabilidad explícita: **Optimization/Application → puerto requerido → Optimization/Infrastructure → adaptador → contrato de Orders**, que conserva la fuente de verdad de Pedido/Pieza y la persistencia de su estado. Optimization no ejecutará escrituras directas sobre tablas de Orders saltándose ese contrato para facilitar start. Si falta capacidad para la transición, T1 ampliará el puerto/repositorio de Orders de forma mínima y explícita; no duplicará repositorios completos ni modelos ORM.

La unidad de trabajo controla un solo commit. La autenticación actual ya puede haber iniciado una transacción por autobegin en la sesión de petición: el adaptador debe adoptar esa transacción de lectura o usar una sesión de proceso con propiedad explícita, sin anidar ciegamente `Session.begin()` ni confirmar a través de dos repositorios. **Alternativa elegida para T1:** adoptar la sesión de petición tras autorización y hacer commit/rollback únicamente en el contexto de start; autenticación solo realizó lecturas. Registrar una prueba de esta integración. Mantener import lazy de la base como hacen las dependencias vigentes.

## 5. Contratos HTTP propuestos para T1

No son endpoints existentes. Se mantienen URL bajo `/api`, `200` para operación exitosa, `detail` legible para errores de negocio y `422` para validación, siguiendo router/schema actuales. No se usa `201`: no se crea un recurso Optimization.

IDs: enteros JSON estrictos, positivos y hasta `2147483647`, sin booleanos/coerción de texto. Request con `extra="forbid"`; cliente no envía estado, geometría ni usuario. Resolución requerida: número JSON finito >0, sin booleanos, vacío ni cadena; UI inicia en 5.0 mm/celda. Backend conserva validación aunque UI bloquee entradas.

### 5.1 Start

`POST /api/optimization/start`

```json
{ "id_pedido": 10 }
```

Respuesta mínima `200`:

```json
{ "id_pedido": 10, "estado": "EN_OPTIMIZACION" }
```

| Situación | HTTP / efecto |
|---|---|
| Inicio válido confirmado | `200`; única transición del pedido |
| Pedido inexistente | `404`; ninguna escritura |
| Estado distinto de PENDIENTE, incluido inicio repetido/concurrente | `409`; ninguna transición adicional |
| Sin piezas o alguna pieza persistida inválida; presupuesto inicial excedido | `422`; motivo seguro y sin transición |
| ID/cuerpo inválido | `422`; no ejecutar caso de uso |
| Sin sesión, token vencido o cuenta no válida | `401`, convención Bearer vigente; ninguna escritura |
| Rol sin permiso, incluido Almacenero | `403`; ninguna escritura |
| Fallo inesperado/commit fallido | `500` general; rollback si no se confirmó; no SQL/stack trace en respuesta |

### 5.2 Rasterize

`POST /api/optimization/rasterize`

```json
{ "id_pedido": 10, "id_pieza": 25, "resolution_mm": 5.0 }
```

| Campo de respuesta | Tipo / semántica |
|---|---|
| `id_pedido`, `id_pieza` | Enteros positivos del origen efectivo |
| `tipo_forma` | RECTANGULO, CIRCUNFERENCIA o POLIGONO_CONVEXO |
| `geometria` | Objeto canónico efectivo con `type` y width_mm/height_mm, radius_mm o `vertices_mm` según forma; solo la geometría persistida, sin boceto ni restricciones |
| `id_tipo_vidrio`, `espesor_mm` | Material por pieza; ID y Decimal serializado según convención de Orders (cadena decimal en JSON), sin pérdida silenciosa de precisión |
| `cantidad` | Entero positivo N de la fila PIEZA; contexto, sin N máscaras |
| `resolution_mm` | Número finito positivo efectivo en mm/celda |
| `row_count`, `columns` | Enteros positivos; altura/ancho de la rejilla en celdas |
| `occupied_cells` | Entero entre cero y `row_count * columns` |
| `spans_by_row` | Lista de exactamente `row_count` objetos `{row: int, runs: [[int, int], ...]}` |

Firma existente verificada directamente: **`RasterMask.row_runs(self, row: int) -> tuple[tuple[int, int], ...]`**. Devuelve tramos ocupados de izquierda a derecha, con semántica **`[start_col, end_col_exclusive)`**; fila vacía devuelve `()`, fila fuera de rango lanza `IndexError`. El test existente usa `((1, 3), (5, 8))`, fila vacía y `((0, 8),)`. Presentation convierte tuplas a listas JSON y añade el índice de fila, sin cambiar dominio.

Invariantes: filas consecutivas `0..row_count-1`; `0 <= start < end <= columns`; rangos ordenados sin solapamiento; fila vacía con `runs: []`; suma de `end-start` igual a `occupied_cells`. Índices y contadores deben caber exactamente en enteros seguros JavaScript, además de respetar el presupuesto operativo. No exponer filas como enteros de bits ni matriz booleana densa. Se conserva la representación lossless con más de 53 columnas.

Ejemplo completo conceptual, con IDs ilustrativos y geometría pequeña; no es evidencia de una ejecución:

```json
{
  "id_pedido": 10,
  "id_pieza": 25,
  "tipo_forma": "POLIGONO_CONVEXO",
  "geometria": { "type": "POLIGONO_CONVEXO", "vertices_mm": [[0, 0], [10, 0], [0, 10]] },
  "id_tipo_vidrio": 7,
  "espesor_mm": "6.00",
  "cantidad": 5,
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

| Situación | HTTP / recuperación |
|---|---|
| Pieza válida de pedido EN_OPTIMIZACION | `200`; máscara y geometría efectivas; ninguna escritura |
| Pedido inexistente o pieza inexistente/ajena | `404`; no revelar geometría ajena ni calcular |
| Pedido en cualquier estado distinto de EN_OPTIMIZACION | `409`; recargar contexto, sin start implícito |
| Resolución/geometría no válida o presupuesto excedido | `422`; explicar corrección; no sustituir forma ni generar payload excesivo |
| Sin sesión / sin permiso | `401` / `403` como start |
| Error inesperado | `500` general, sin preview fabricado |

Validación JSON no finita: seguir el manejo seguro de `OrderRoute` para no devolver `input` infinito/NaN en el detalle de `422`; no importar schemas de Orders/Presentation desde Application. Un fallo de red no equivale a una respuesta HTTP y se representa como tal en UI.

### 5.3 Cantidad y fuente de verdad

Una fila PIEZA persistida con `cantidad = N` produce **una llamada a rasterize_geometry y una sola máscara**, para esa geometría/resolución. N no multiplica spans, filas ni geometría del DTO. Las heurísticas futuras reutilizarán esa máscara N veces, sin afirmar colocación/consumo aquí. Cambiar resolución sí es otra entrada; no se exige caché global ni persistencia de preview. Dos filas distintas no se fusionan automáticamente por parecer iguales.

La respuesta incluye geometría efectiva para que el visor no mezcle la máscara nueva con un detalle previo. Orders sigue siendo la única fuente del pedido, piezas y estado. Un ID sustituido por edición antes del inicio requiere recargar; las llamadas raster no escriben en Orders, Inventory ni tablas Optimization.

## 6. Benchmark y límite de recursos — diseño, sin ejecución

P-01 se resolverá en T1 **antes de fijar `MAX_RASTER_CELLS` y habilitar el endpoint**. No se asigna ahora ningún valor numérico. El script previo de evidencia se toma como referencia de entradas, no como medición suficiente del nuevo HTTP ni como resultado actual.

### 6.1 Matriz reproducible

| Caso propuesto | Geometría en mm | Resoluciones mm/celda |
|---|---|---|
| Rectángulo pequeño | 100 × 50 | 20, 10, 5, 2, 1 |
| Rectángulo de referencia CA-09 | 800 × 600 | 20, 10, 5, 2, 1 |
| Rectángulo comercial grande | 2440 × 1830, dimensión usada por TA-007 | 20, 10, 5, 2, 1, sujeto al precontrol del runner |
| Círculo | radio 500 | 20, 10, 5, 2, 1 |
| Polígono convexo | hexágono existente: [[250,0],[750,0],[1000,433],[750,866],[250,866],[0,433]] | 20, 10, 5, 2, 1 |
| Casos de forma/presupuesto adversos | 1 × 10; rectángulos muy largos/delgados y altos/estrechos; convexo con coordenadas negativas; variantes convexas con más vértices | Selección progresiva de las mismas resoluciones |

Los casos adversos importan porque `row_runs` recorre bits hasta la última columna ocupada, un payload siempre incluye todas las filas y el costo del polígono depende también de vértices. La cantidad N no debe influir en costo de máscara; comparar una entrada idéntica con cantidad 1 y 5.

Procedimiento futuro:

1. Crear entradas versionadas bajo `experiments/raster/cases/hu015-resources.json` y runner `experiments/raster/scripts/hu015_resource_benchmark.py`. Reutilizar código productivo, incluido serializador propuesto, nunca importarlo desde experiments hacia aplicación.
2. Comando previsto desde raíz, con entorno backend preparado: `python experiments/raster/scripts/hu015_resource_benchmark.py`. El runner añadirá `backend/` al path como `raster_evidence.py`. Este archivo/comando aún no existe y no se ejecuta en la planificación.
3. Registrar commit, dirty status, Python/dependencias, SO, CPU/RAM, fecha y hash de casos; semilla fija si se generan variantes. Ejecutar un calentamiento y cinco repeticiones por caso en procesos aislados; ordenar desde rejillas pequeñas hacia grandes. Reportar muestras, mediana y máximo; no extrapolar del mejor tiempo.
4. Medir con `perf_counter` por separado rasterización, extracción de `row_runs`/DTO y codificación JSON usando la misma ruta de serialización elegida para API. Registrar costo total y bytes UTF-8 reales del payload completo (incluye geometría y metadatos), no longitud de una captura truncada ni tamaño comprimido.
5. Medir memoria con `tracemalloc` en una pasada separada para no contaminar tiempos; registrar pico de asignaciones Python y su limitación frente a RSS. Si se mide RSS del proceso, identificar herramienta y plataforma; si no es razonablemente medible, registrar N/D y motivo, sin inventarlo.
6. El runner tendrá timeout y presupuesto de memoria explícitos fijados por quien lo ejecute según su entorno. Preestimar dimensiones antes de crear datos, detener/escalar progresivamente y marcar casos omitidos/fallidos con motivo. No intentar combinaciones peligrosas para completar la tabla.

Registro por muestra: caso/forma, número de vértices, cantidad, resolución, dimensiones y bbox, filas, columnas, `total_cells = rows * columns`, `occupied_cells`, tiempos de raster/DTO/JSON, bytes y memoria pico. Conservar resultados brutos en `experiments/raster/results/hu015/` y resumen seleccionado en `docs/evidence/sprint-01/HU-015/benchmark-limite.md`, solo cuando existan resultados reales.

### 6.2 Selección y aplicación de presupuesto

Con las mediciones, acordar capacidad de servidor, tamaño/tiempo de respuesta y margen para concurrencia; elegir el máximo que cumpla todos los casos admitidos. Si celdas totales no acotan suficientemente vértices, dimensiones extremas o bytes de geometría, añadir presupuestos complementarios sustentados en esa evidencia. No fijar umbrales arbitrarios ahora ni afirmar que el número de celdas por sí solo mide memoria real. Documentar valores, justificación y entorno antes de cerrar T1.

Application hará **preflight antes de llamar al rasterizador**: validar forma/números y estimar bbox/rejilla alineada con el dominio actual. Rectángulo y polígono normalizan a 6 decimales; círculo usa `round(2 * radius, 6)`; conteo actual `max(1, ceil(length / resolution - 1e-9))`. No importar helpers privados de rasterizer ni cambiar su semántica; la política implementará la estimación y las pruebas focalizadas verificarán coincidencia en bordes de redondeo. Rechazar también cocientes/extensiones no finitos o fuera de presupuesto antes de generar enteros/bits enormes. Contar celdas de bbox, no multiplicar por cantidad ni usar únicamente occupied_cells posterior.

El preflight de start evalúa baseline 5.0 y el de rasterize su resolución efectiva. Presentation verificará tamaño previsto del DTO/JSON y consistencia antes de materializar una respuesta excesiva; si se necesita un límite de bytes/rangos, usar estimación superior conservadora o construcción acotada incremental, sin generar primero un JSON gigante para después rechazarlo. Pruebas en el umbral y superior, rejillas estrechas/altas y payloads con muchos vértices. Sin estos datos y guardas, no dar por cerrado el contrato operativo de T1.

## 7. Frontend e integración propuestos

Feature `frontend/src/features/optimization/`: `OptimizationPage.jsx`, `optimizationApi.js`, hook de flujo cuando sea útil y componentes de selección/resultado. Exponer API pública con `index.js` siguiendo authentication/users. Añadir `canExecuteOptimization` a permisos frontend y exportarlo; usar los mismos roles de backend. Integrar view `optimization` en `App.jsx` y Sidebar/AppShell/NavigationContext; conservar SessionBar, fallback de vistas y subpath staging. Sin React Router, gestión de stock ni nueva navegación global.

Reutilizar `listOrders({page, limit, estado: 'PENDIENTE'})`, `getOrder` y catálogo para rotular material; no duplicar CRUD. `optimizationApi` implementará start/rasterize con `API_URL`, token/AbortSignal, error propio con status y detalle seguro. Se valida estructura de respuesta y spans antes de mostrar resultado. Si catálogo falla, mostrar ID/aviso sin bloquear el cálculo por ausencia de nombre. No reducir un pedido multimaterial a una cabecera de material.

Flujo visible:

1. Cargar listado paginado PENDIENTE; seleccionar pedido y consultar datos básicos/piezas, sin transición.
2. Pulsar **«Iniciar optimización»**; impedir doble envío y esperar aceptación backend.
3. Con `200`, mantener seleccionado el pedido y mostrar **EN_OPTIMIZACION**, aunque desaparezca del listado filtrado PENDIENTE. Releer su detalle para tener IDs/piezas vigentes; si esta lectura falla, reintentar GET, nunca repetir start.
4. Habilitar selección de pieza y resolución inicial 5.0 mm/celda; ejecutar **«Rasterizar pieza»**. Se puede seleccionar/consultar pieza antes de start como permite la SPEC, pero su cálculo sigue bloqueado hasta EN_OPTIMIZACION. Cambios de resolución posteriores se validan por solicitud.
5. Mostrar geometría efectiva y máscara con metadatos; otra pieza o resolución usa el mismo proceso sin nuevo inicio. Cantidad se muestra como unidades previstas, no máscaras/colocaciones.

Cada selección/resolución tendrá identidad de solicitud; abortar lecturas/cálculos obsoletos cuando sea posible e ignorar respuestas tardías. Cancelar fetch de start no prueba rollback servidor: resolver el resultado incierto con GET del ID original, incluso si la selección cambió. Al cerrar sesión limpiar resultado/contexto local. Para volver a un proceso tras recargar/perder contexto, ofrecer recuperación explícita mediante listado Orders filtrado `EN_OPTIMIZACION` y lectura del pedido; es continuidad de un proceso existente, con start deshabilitado, no otro inicio ni historial raster. La vista inicial continúa siendo PENDIENTE.

### 7.1 Estados y accesibilidad

| Estado UI | Comportamiento / recuperación |
|---|---|
| Carga de pedidos | LoadingState, controles dependientes bloqueados |
| Vacío sin pendientes | EmptyState y recarga; ninguna pieza de demostración |
| Pedido seleccionado / carga de piezas | Contexto visible y detalle real; no cambia estado |
| Sin piezas válidas / error de datos | Mensaje textual, start bloqueado; backend vuelve a validar |
| Iniciando optimización | Acción disabled/aria-busy y guardia de doble envío; mostrar PENDIENTE hasta aceptación |
| Resultado incierto de start | Consultar estado por GET; no POST automático |
| EN_OPTIMIZACION | Estado textual, start inhabilitado y controles de raster habilitados al completar detalle |
| Rasterizando | Contexto de pieza/resolución, acción bloqueada; no ocultar qué está en curso |
| Resultado | Dos paneles y resumen accesible de los datos efectivos |
| Error recuperable | Feedback accionable; no éxito ni máscara anterior como resultado vigente |
| Error de autorización | 401 usa onSessionExpired; 403 informa y bloquea operación sin conceder permisos |
| Límite excedido | Motivo de 422 y ajuste de resolución/reintento explícito; sin afirmar éxito |

Reutilizar labels/unidades, foco visible, teclado, `role="status"` en cargas/resultados, `role="alert"` en errores y FieldError con `aria-invalid`/`aria-describedby`. No depender solo del color, no crear un tab stop por celda. Mantener lectura textual incluso cuando Canvas no sea accesible. Dos columnas en escritorio y apilado responsive; viewport del dibujo delimitado, con controles de zoom/desplazamiento accesibles si se necesitan.

## 8. Visualización propuesta

**Elección: SVG para geometría original y Canvas 2D para raster.** SVG encaja con el editor actual y basta un rect/polygon/circle para el contorno; reutilizar conceptos de escalado/bbox sin importar lógica de edición o reconstruir coordenadas. Canvas evita miles de nodos SVG/DOM y permite dibujar un rectángulo por tramo, no por celda. CSS grid con elemento por celda se descarta por costo DOM. No se añade librería de gráficos.

- Panel A dibuja `geometria` efectiva: rectángulo por width/height, círculo por radius, polígono desde pares `vertices_mm`, con cierre implícito y coordenadas negativas permitidas. No recalcular lados/ángulos ni modificar el origen persistido de la respuesta.
- Panel B interpreta directamente spans; por tramo dibuja ancho `(end-start) * resolution_mm`, alto `resolution_mm` y posición `(start * resolution_mm, row * resolution_mm)`. No convertir primero a matriz booleana ni usar bitwise JavaScript sobre filas Python.
- Ambos usan transformación con un único factor uniforme de mm a px y ejes X/Y iguales. Para comparar, usar la extensión común de geometría y rejilla (`columns * resolution_mm`, `row_count * resolution_mm`); trasladar el contorno por minX/minY solo al dibujar. Evitar dos autoescalados que oculten diferencias físicas. Mostrar regla conservadora y exceso de rejilla como conceptos distintos.
- Canvas se dimensiona al viewport visible y a devicePixelRatio, no a rows × columns en píxeles físicos ilimitados; redibujar al cambiar tamaño/zoom y evitar blur por escalado CSS desproporcionado. Grilla individual solo cuando las celdas son legibles; omitir líneas de grilla no elimina spans del resultado. Mostrar siempre resolución, filas, columnas, occupied_cells, pedido/pieza, forma, dimensiones, material, espesor y cantidad.
- No transformar el render en otra rasterización por muestreo. Con zoom bajo algunas celdas se perciben pequeñas, pero los datos y tramos recibidos se conservan; permitir ampliar/inspeccionar sin prometer una imagen lossless a cualquier escala. Texto alternativo/resumen, leyenda de contorno/celdas y estados accesibles sin depender de color.

Canvas es una propuesta sustentada por costo DOM y por el riesgo de rejillas grandes; T3 deberá verificar tiempos de dibujo con máscaras en el límite aprobado en T1. El benchmark backend no demuestra rendimiento del visor. Ningún dato de prueba o métrica final de aprovechamiento se muestra como resultado productivo.

## 9. Persistencia y pruebas previstas

### 9.1 Sin migración

La auditoría de modelos y migraciones confirma **NO migración para HU-015**: ya existen estado/check del pedido, geometría JSONB, cantidad y material por pieza. No se guarda preview ni se crea Optimization, ejecución FF/BF/WF, configuración, métrica, selección/consumo de stock o estado nuevo. La escritura requerida es un valor permitido en una columna existente. No se crearán tablas, columnas o versión de recurso por conveniencia; si aparece una necesidad real de esquema en implementación, detener ese cambio y justificarlo antes de ampliar el alcance. No se ejecutaron Alembic ni consultas contra BD en esta planificación.

### 9.2 Cobertura nueva, sin duplicar dominio existente

| Nivel / momento | Cobertura futura |
|---|---|
| Backend unit — T1 | StartOptimizationUseCase: éxito, estado incorrecto, ausencia, vacío/corrupción, presupuesto inicial, validación previa sin commit y fallo de commit. RasterizeOrderPieceUseCase: lectura correcta, pieza ajena/ausente, EN_OPTIMIZACION requerido, resolución/budget, una sola llamada al rasterizador con cantidad >1 y cero escrituras. Validación de dependencias de capas. |
| API start — T1 | `200`, `401`, `403`, `404`, todos los estados no PENDIENTE `409`, repetición `409`, sin piezas/geométrica inválida `422`, schema estricto y `500` seguro. Verificar que GET/listado no cambia estado y que solo se escribe Pedido.estado, sin registros Optimization/Inventory. |
| API rasterize — T1 | Rectángulo, círculo y polígono con vertices_mm; cantidad N, resolución inválida (incluye booleano/no finito), pieza ausente/ajena `404`, pedido ausente `404`, todos los estados no EN_OPTIMIZACION `409`, límite `422`, geometría incompatible `422`, contrato completo de spans, >53 columnas y fila vacía mediante fixture de serializador. |
| Integración PostgreSQL — T1 | Commit/rollback reales; carreras start/update y start/cancel con el mecanismo seleccionado; fallo de commit sin estado parcial. Adoptar sesión usada por auth. Leer desde otra sesión para comprobar persistencia; no presentar un mock como prueba de semántica transaccional real. |
| Concurrencia start A/B — T1 | Preparar Pedido #10 PENDIENTE y coordinar dos intentos simultáneos en sesiones/conexiones independientes. Verificar exactamente un inicio exitoso (`200`), el otro rechazado (`409`), una única transición confirmada, estado final EN_OPTIMIZACION leído desde una tercera sesión y ausencia de efectos duplicados/escrituras excluidas. Ejecutar como integración con PostgreSQL aislado cuando se compruebe el mecanismo SQL/transaccional elegido; los mocks unitarios no demuestran concurrencia de BD y dos llamadas meramente secuenciales no cubren este escenario. |
| Presupuesto / serializador — T1 | Estimación previa congruente con redondeo/epsilon del dominio; límite y valor superior, alta/estrecha, muy ancha, coordenadas negativas, overflow, vértices/payload, rechazo antes de llamar rasterizador/crear respuesta excesiva. Reconstruir celdas desde rangos y comparar con máscara; reutilizar tests RasterMask existentes. |
| Frontend componentes — T2 | Listado paginado/selección/detalle, start y actualización a EN_OPTIMIZACION, acción bloqueada antes de inicio, timeout y recuperación GET, loading/errores 401/403/404/409/422, pieza/resolución, cancelación/respuesta tardía, cantidad N y límite excedido. Adaptación de DTO sin replicar rasterización. Sidebar/roles/subpath y mocks de authentication actualizados. |
| Frontend visor — T3 | Tres formas reales, coordenadas negativas, spans con huecos, >53 columnas, misma escala, proporción, fila vacía, metadatos/cantidad, teclado/foco/leyenda/resumen y responsive. Un spy de Canvas comprueba la interpretación de tramos, pero no demuestra calidad visual: complementar con navegador local. |
| E2E final — T3 | Login → Optimization → seleccionar PENDIENTE → iniciar → EN_OPTIMIZACION → seleccionar pieza/resolución → rasterizar → geometría/máscara visibles. Usar API/backend reales y PostgreSQL temporal del harness existente, IDs propios por caso, escritorio/móvil; comprobar cantidad y ausencia de efectos excluidos. No interceptar el éxito raster para declarar integración. |
| Regresión — T1/T3 según cambio | T1: dominio TA-005/006/007 y Orders (registro sin stock, detalle, edición/cancelación/concurrencia), auth/permisos. T2/T3: navegación, sesión, Orders UI y pruebas unitarias/componentes aplicables, lint/build y E2E al estabilizar el flujo. No exigir E2E HU-015 durante T1 sin frontend. |

Ubicaciones propuestas: `backend/tests/unit/optimization/`, `backend/tests/api/optimization/`, `backend/tests/integration/optimization/` y extensiones focalizadas de pruebas Orders; frontend `src/features/optimization/__tests__/`, `tests/unit/` para transformaciones puras si procede y `tests/e2e/hu015-rasterization.spec.js`. No se crean pruebas en este paso. Reutilizar los helpers locales de `tests/orders_support.py`, auth y PostgreSQL temporal; no usar por defecto la base remota compartida.

Comandos **futuros**, solo cuando existan esos archivos y el entorno esté preparado:

- Desde backend: `python -m pytest -q tests/unit/optimization tests/api/optimization tests/integration/optimization`, más selección Orders/auth afectada y `python -m pytest -q tests/optimization` como regresión geométrica.
- Desde frontend T2/T3: `npm run test:component -- src/features/optimization/__tests__` y pruebas de navegación afectadas; `npm run test:unit`, `npm run lint`, `npm run build` cuando corresponda.
- Solo T3 con flujo estable: `npm run test:e2e -- tests/e2e/hu015-rasterization.spec.js`; usar configuración existente con API 8017/Vite 5173 y Chrome local o canal configurado. La documentación antigua de harness sin login no sustituye esta configuración actual.

## 10. Descomposición técnica propuesta para implementación

**Descomposición técnica propuesta; no corresponde a la división histórica T1/T2/T3 del backlog, la cual no fue localizada.** Son exactamente tres tareas técnicas. Todos sus checks están pendientes; el orden es T1 → T2 → T3. No se asignan responsables históricos ni se presentan estas tareas como backlog recuperado.

### HU-015-T1 — Backend y contrato raster

**Objetivo:** dejar un contrato HTTP estable y probado, con transición segura y presupuesto sustentado.

- [ ] Revisar este plan/contratos y la extensión mínima de la frontera Orders; mantener SPEC Reviewed como referencia.
- [ ] Crear casos de uso StartOptimizationUseCase/RasterizeOrderPieceUseCase y puertos/adaptador por composición; ampliar mínimamente y de forma explícita el contrato de Orders para validación/transición atómica, sin escrituras directas desde Optimization ni duplicar entidades/repositorios o mover CRUD.
- [ ] Evaluar bloqueo de fila transaccional frente a actualización condicional/compare-and-set; elegir y justificar en T1 el mecanismo que encaje con SQLAlchemy/Orders y coordine start con update/cancel. Mantener Domain/Application independientes del mecanismo SQL.
- [ ] Implementar unidad de trabajo, validación completa previa y transición atómica única PENDIENTE → EN_OPTIMIZACION; ante A/B simultáneos, exactamente un 200 y un 409, estado final EN_OPTIMIZACION y ningún efecto duplicado. Mantener rechazo repetido 409 y rollback.
- [ ] Implementar endpoints start/rasterize, dependencies/autorización, schemas estrictos, serializador spans, lectura efectiva y errores seguros. Registrar router en main.py sin importar base al cargar módulos.
- [ ] Crear/ejecutar en T1 el benchmark reproducible de §6; decidir un límite defendible `MAX_RASTER_CELLS` o equivalente, documentarlo, probarlo y aplicarlo antes de rasterización/serialización excesiva, con guardas complementarias si la evidencia lo exige. Aplicar preflight al inicio en 5.0 y a cada cálculo. No ejecutar el benchmark en esta revisión documental.
- [ ] Incorporar pruebas unitarias y API de start/rasterize, y prueba específica de integración/concurrencia A/B de §9 cuando aplique al mecanismo seleccionado, usando PostgreSQL aislado para verificar semántica real. Comprobar un solo éxito, rechazo/conflicto, estado final y ausencia de efectos duplicados; conservar cantidad N sin N llamadas/máscaras y regresión geométrica/Orders/auth aplicable. No crear ni ejecutar pruebas en esta revisión.
- [ ] Documentar request/response efectivos, resultados y presupuesto en evidencia técnica cuando existan. No crear FF/BF/WF, preview persistido, stock ni migración.

**Archivos previstos, no creados ahora:** `optimization/application/{ports,use_cases,errors,resource_policy}.py`; `optimization/infrastructure/orders_adapter.py`; `optimization/presentation/{router,schemas,dependencies,serialization}.py`; extensión localizada de Orders application/ports, fachada de validación y repository; `backend/main.py`; pruebas/backend y runner/casos de benchmark descritos arriba. Los nombres exactos pueden ajustarse manteniendo las responsabilidades.

**Cierre verificable:** contratos start/rasterize y errores estables; mecanismo concurrente elegido y justificado; caso A/B con un único inicio confirmado, segundo intento 409, estado final EN_OPTIMIZACION y sin efectos duplicados; ninguna transición en rasterize; umbral sustentado, documentado, probado y aplicado previamente; rollback probado; ninguna escritura excluida; evidencia nueva identificable. Sin frontend ni E2E frontend en T1. P-01 solo se cierra con medición real y P-03 con revisión del diseño y validación de consistencia, no por existir este plan.

### HU-015-T2 — Interfaz e integración

**Objetivo:** flujo funcional React → API desde pedido persistido hasta recepción de máscara backend.

- [ ] Crear feature optimization y cliente API; reutilizar listado/detalle/catálogo de Orders con token, señal de cancelación y mensajes accionables.
- [ ] Integrar view, Sidebar/AppShell y permiso canExecuteOptimization (Administrador/Operario); conservar navegación por estado y SessionBar/subpath.
- [ ] Implementar listado inicial PENDIENTE, selección/detalle, acción Iniciar optimización y conservación del pedido seleccionado al pasar a EN_OPTIMIZACION.
- [ ] Habilitar pieza/resolución/rasterize solo en proceso iniciado; tratar cantidad como contexto; mostrar respuesta/metadatos textuales para preparar el visor de T3, sin inventar éxito visual final.
- [ ] Resolver doble envío, loading/disabled, error de autorización, dato desactualizado, límite, timeout start con GET y recuperación explícita de procesos EN_OPTIMIZACION; ignorar respuestas obsoletas.
- [ ] Incorporar pruebas de componentes/cliente API y navegación correspondientes; verificar integración local con backend T1, diferenciándola de fixtures/mock. Conservar labels, teclado y feedback accesible desde esta tarea.

**Archivos previstos:** `frontend/src/features/optimization/{OptimizationPage,optimizationApi,index,...}` con extensiones apropiadas; `App.jsx`, Sidebar, permisos/index de authentication y tests focalizados. No tocar CRUD/configuración/stock por conveniencia.

**Dependencia y cierre:** T1 cerrado con límite y contrato; UI realiza start una vez y raster por pieza real, muestra estado efectivo, gestiona recuperación y pasa componentes/controles aplicables. La comparación gráfica y E2E completo no se declaran cerrados en T2.

### HU-015-T3 — Visualización y cierre

**Objetivo:** cerrar el flujo visible y verificable de HU-015.

- [ ] Implementar panel SVG de geometría original y Canvas raster desde spans, con escala física común, normalización solo visual y sin matriz DOM por celda.
- [ ] Integrar comparación, resolución, dimensiones, filas/columnas/celdas, material/espesor, cantidad y resumen textual; mantener una máscara por pieza, sin afirmar N colocaciones.
- [ ] Completar accesibilidad, teclado/foco/contraste/leyenda y responsive; verificar en navegador que máscaras en el límite T1 se dibujan de forma usable sin canvas gigante.
- [ ] Incorporar pruebas de visualización y ejecutar E2E final con login/API/PostgreSQL reales cuando el flujo esté estabilizado; regresión frontend/backend afectada, lint/build y evidencia reproducible.
- [ ] Preparar capturas manuales locales, resultados de pruebas/benchmark y Git/PR cuando proceda; registrar error real, diagnóstico y corrección solo si ocurrió.
- [ ] Revisar los 23 CA originales sin renumerarlos; actualizar SPEC a Implemented únicamente al completar implementación y a Verified únicamente con evidencia y revisión final que correspondan. No anticipar esos estados ni cerrar P-02 con una división inventada.

**Archivos previstos:** componentes de visualización y estilos dentro de feature optimization, sus pruebas, E2E HU-015 y documentación/evidencia asociadas. Compartir helpers solo si aparece reutilización real, sin ampliar editor/arquitectura global.

**Dependencia y cierre:** T1/T2 completos; las tres formas comparables con raster backend real; todos los CA evaluados con evidencia, efectos excluidos ausentes, visor accesible/responsive y revisión final registrada. No avanzar el pedido a OPTIMIZADO/CONFIRMADO para demostrar HU-015.

### 10.1 Trazabilidad de los 23 CA, sin criterios nuevos

| CA existentes | Tarea / verificación principal |
|---|---|
| CA-01, 02, 07, 11, 12, 13, 16, 17 | T2 para flujo/UI; T1 para estados, autenticación y rechazos efectivos |
| CA-03, 04, 05, 06, 14, 15, 19, 20, 21, 22, 23 | T1 para casos de uso/contrato/presupuesto/ausencia de efectos; T2 presenta contexto/errores y T3 confirma el flujo completo |
| CA-08, 09, 10, 18 | T3 para representación y acceso; T1 prueba DTO/rangos y resultados canónicos de backend |

## 11. Evidencias futuras y límites de esta entrega

No se toca **NewGlass-Notion**. Se reserva exclusivamente para capturas de pantalla generadas manualmente durante implementación; no md, txt, logs, json, scripts ni índices. Este plan solo prevé las capturas siguientes:

- Código backend por capas, transición y rasterizador existente conectado.
- Endpoint/API: start y estado efectivo, rasterize y spans, autorización y errores.
- Benchmark/límite: entradas, mediciones reales, selección de umbral y rechazo previo.
- Tests: unit/API/integración y componente con comandos/resultados reales.
- Interfaz local: selección, inicio EN_OPTIMIZACION, piezas/resolución y estados.
- Geometría original vs raster para las tres formas y cantidad >1.
- Error real + corrección si ocurre, sin fabricar un fallo.
- E2E real del flujo estabilizado y Git/PR cuando esas etapas estén autorizadas.

Documentación y evidencia seleccionada seguirán `docs/evidence/sprint-01/HU-015/`; salidas reconstruibles del benchmark, experiments/raster/results. Capturas sin JWT, cookies, Authorization, contraseñas, cadenas de conexión ni datos sensibles. No crear archivos vacíos ni capturas ficticias para simular cierre.

La revisión humana del plan técnico está completada y aprobada. Permanecen pendientes la ejecución del benchmark/valor del presupuesto (P-01), historia T1/T2/T3 aún no localizada (P-02) y materialización/validación del diseño de inicio (P-03). La descomposición de este documento no resuelve el antecedente histórico. HU-008 no integrada no se copia ni se convierte en dependencia del inicio/raster; no se selecciona stock compatible en HU-015.

Este cierre incorpora únicamente el PLAN mediante un commit documental. No se modifica backend, frontend ni SPEC Reviewed; no se crean tests, benchmark ejecutable, migraciones ni endpoints. No se ejecutan pruebas/benchmark, no se hace push, PR o merge y no se toca NewGlass-Notion.

## Historial del plan

- 13/10/2026 — **Draft**: plan técnico y tres tareas propuestas a partir de SPEC Reviewed en `35d1e91`, con auditoría de fuentes locales. Separación start/rasterize, transacción de inicio, estado permitido, contratos, benchmark diseñado y visor SVG/Canvas propuestos para revisión. Sin implementación ni validación funcional ejecutada.
- 13/10/2026 — **Approved**: revisión humana completada por **Fabricio Aguilar**; autor **Fabricio Melendez**. **Aprobado para implementación**. Se aprueban la separación entre start y rasterize; `PENDIENTE → EN_OPTIMIZACION` mediante start; rasterize únicamente sobre `EN_OPTIMIZACION`, sin cambiar estado; protección frente a starts concurrentes con un solo éxito y otro `409`, sin efectos duplicados; Orders como fuente de verdad y adaptación por composición; una máscara por PIEZA persistida, reutilizable según `cantidad > 1`; respuesta `spans_by_row`; benchmark previo a fijar `MAX_RASTER_CELLS` o equivalente; SVG para geometría original y Canvas para raster; ausencia de migración; y T1/T2/T3 como descomposición técnica propuesta, sin atribuirla al backlog histórico no localizado. La elección justificada del mecanismo de concurrencia y la ejecución/validación previstas permanecen en T1. Sin implementación, pruebas ni benchmark ejecutados en este cierre; SPEC Reviewed intacta.
