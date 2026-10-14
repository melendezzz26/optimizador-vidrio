# HU-015-T2 — Interfaz e integración de rasterización

**Estado de la tarea:** implementada, lista para revisión; sin commit.
**Rama:** `feature/HU-015-interfaz-rasterizacion`.
**Base:** T1 `0650450` (`feat(HU-015): implementar backend de rasterizacion`); `origin/integration/sprint-01` permanece en `728c1dd`, sin commits pendientes de incorporar al HEAD `0650450`.
**Documentos:** SPEC permanece **Reviewed** y PLAN **Approved**.

## Implementación

Se añadió Optimization siguiendo el patrón de features planas, `AppShell`, componentes compartidos y navegación por estado. El Sidebar es el único punto de navegación del módulo. `Administrador` y `Operario` tienen acceso de interfaz; `Almacenero` no. El backend conserva la decisión definitiva de autorización.

La lista consume `listOrders` con `estado=PENDIENTE`, paginación y actualización explícita. La vista de recuperación filtra `EN_OPTIMIZACION`. La selección carga `getOrder`, conserva el contexto tras iniciar y permite consultar de nuevo el detalle. Si tanto start como la consulta de reconciliación fallan, la UI oculta el estado/piezas anteriores, mantiene las acciones bloqueadas y muestra que el resultado sigue incierto con una consulta explícita disponible. El catálogo de Orders aporta nombres de material y, si falla, se muestran los IDs sin bloquear el flujo.

El transporte común `createApiRequest` conserva `API_URL`/`VITE_API_URL`, el token de sesión, la señal de cancelación, los mensajes por status y el fallback seguro de validación. Orders delega en el mismo transporte; sus firmas y contratos existentes se mantienen.

`POST /api/optimization/start` envía únicamente `id_pedido`. Con `200 EN_OPTIMIZACION` conserva el pedido seleccionado, actualiza el estado local, vuelve a consultar las piezas y no rasteriza automáticamente. Ante `409`, informa el conflicto, actualiza la lista PENDIENTE y mantiene el estado local previamente consultado sin habilitar acciones sobre información obsoleta. Si timeout, fallo de red/servidor o respuesta 2xx inesperada deja incierto el resultado, consulta el ID original con Orders; nunca repite start automáticamente. La respuesta reconciliada permite continuar si el backend confirma `EN_OPTIMIZACION`, volver a iniciar expresamente si sigue `PENDIENTE` o bloquea el flujo para otros estados. Tras cambiar de módulo o recargar, la recuperación explícita vuelve a consultar pedidos EN_OPTIMIZACION y detalle.

La pieza se identifica como un único registro persistido; cantidad es un atributo. La resolución empieza en **5 mm/celda**, acepta cualquier número finito positivo y bloquea vacío, cero, negativos y entradas no numéricas. `POST /api/optimization/rasterize` envía únicamente `id_pedido`, `id_pieza` y `resolution_mm`; conserva el objeto recibido y `spans_by_row` sin mutarlos ni expandirlos a matriz. La comprobación estructural exige filas consecutivas y admite filas válidas con `runs=[]`.

El resumen presenta forma, cantidad, resolución, filas, columnas, celdas ocupadas, material y espesor. Cambiar pedido, pieza o resolución invalida el raster anterior. Un `422` seguro se muestra como error recuperable y permite cambiar resolución y reintentar. Esta entrega no incorpora Canvas, SVG geométrico, heurísticas, placement ni funciones de stock.

## Cobertura y verificación

- Pruebas focalizadas de Optimization, API y navegación: **68 pasaron** en 4 archivos.
- Regresión de componentes Orders: `npm run test:component -- src/features/orders/__tests__` — **101 pasaron** en 8 archivos. La prueba de navegador local también consumió el listado, detalle y catálogo Orders reales.
- Unit frontend: `npm run test:unit` — **124 pasaron**, 0 fallos.
- Componentes frontend: `npm run test:component` — **288 pasaron**, 0 fallos, 25 archivos.
- `npm run lint`: pasó.
- `npm run build`: pasó (Vite 8.3.1).
- `git diff --check`: sin errores de espacios/conflictos.

La prueba manual usó un PostgreSQL temporal aislado, API en loopback y pedidos/materiales/usuarios sintéticos; no usó staging ni bases compartidas. Operario completó `start 200` y `rasterize 200`. La pieza rectangular con cantidad 5 aparece una sola vez y devuelve 20 filas, 40 columnas y 800 celdas ocupadas. Circunferencia y polígono convexo también rasterizaron con `200` (16×16/224 y 13×14/150 respectivamente). Al competir otro start, el segundo request de UI obtuvo `409`, presentó el conflicto y no actualizó falsamente el estado del detalle. Una resolución `0.001` produjo `422` por el límite de recursos; cambiarla a 5 permitió retry `200`. Se interceptó una respuesta perdida después de que el servidor aceptara start: la UI reconcilió `EN_OPTIMIZACION` mediante GET y habilitó la pieza sin repetir POST. Después de recargar, Administrador recuperó explícitamente un pedido EN_OPTIMIZACION y rasterizó sin start. Almacenero no recibió Optimization en navegación y el backend respondió `403`. Sin errores de JavaScript del navegador ni desbordamiento horizontal a 800 px.

Accesibilidad básica revisada: campos con labels asociados, acciones con texto y `disabled` real, cargas/resultados/errores con roles textuales compartidos, foco visible heredado y navegación del Sidebar por teclado. La auditoría final repitió la focalizada Optimization/navegación (**68**), suite unitaria (**124**), suite de componentes (**288**), lint y build tras corregir la presentación del estado incierto. No se ejecutó Lighthouse/auditoría T3.

## Límites y archivos

El backend productivo no fue modificado; `git diff -- backend/` está vacío. SPEC/PLAN permanecen intactos. T3 conserva el render geométrico y de spans; HU-015 no se marca como completa/Verified.

Archivos frontend incorporados/modificados:

- App, permisos, Sidebar y pruebas de navegación.
- Transporte compartido y adaptación del cliente Orders.
- `features/optimization/`: página, estilos, API, hook y pruebas de componente/API con fixtures.

No se generaron capturas ni se hizo commit, stage, push, PR o merge.
