# SPEC-S1-OPTIMIZATION-FIRST-FIT — Optimización First Fit

## Información general

| Campo | Valor |
|---|---|
| Estado | **Reviewed** |
| PBI relacionado | Cierre de Sprint 1 — Optimization First Fit |
| Autor / Responsable | Fabricio Melendez |
| Reviewer | Fabricio Danniel Aguilar Chávez |
| Fecha | 15/10/2026 |
| Fecha de revisión | 16/10/2026 |
| Rama de trabajo | `feature/S1-optimization-core` |
| Base de integración | `integration/sprint-01` |
| Decisión | Revisada y aprobada para implementación / planificación técnica. |

## 1. Contexto, fuentes y problema

### 1.1 Contexto

HU-015 está cerrada como Verified. Su alcance histórico fue iniciar explícitamente la optimización de un pedido, aceptar la transición `PENDIENTE -> EN_OPTIMIZACION`, rasterizar piezas persistidas, mostrar la geometría y su máscara, y cubrir validaciones y pruebas. HU-015 no implementó heurísticas First Fit, Best Fit o Worst Fit, placement automático, métricas finales, consumo de stock, confirmación de solución ni transiciones a `OPTIMIZADO` o `CONFIRMADO`. Esta SPEC extiende el producto; no reescribe ni amplía retroactivamente HU-015.

**Revisión S1-01, 21/10/2026:** la [revisión de HU-015](SPEC-HU-015-interfaz-rasterizacion.md#revisión-s1-01--21102026) convierte la preparación histórica en consulta sin transición, manteniendo sus rutas. Vista previa y rasterización conservan PENDIENTE, de modo que el pedido sigue elegible para `/api/optimization/runs`. RN-02/RN-03 no cambian: solo aceptar una ejecución real crea su snapshot y cambia el lote pendiente a EN_OPTIMIZACION. Persistencia, determinismo, métricas, confirmación y permisos no cambian. No se normalizan pedidos históricos EN_OPTIMIZACION ni se amplían los estados de entrada de First Fit. La descripción anterior registra el alcance histórico; la [evidencia S1-01](../evidence/sprint-01/S1-01/README.md) documenta la corrección.

La planificación histórica de ADR-002 §2.11 ubica FF/BF/WF posteriormente, en Sprint 2. Una corrección posterior del alcance de Sprint 1 requiere demostrar al menos una optimización real y visualizable. Para atenderla, esta SPEC adelanta únicamente First Fit al cierre de Sprint 1; Best Fit y Worst Fit permanecen fuera de su alcance. Esta actualización futura de alcance debe reflejarse mediante una actualización/ADR de decisión que conserve la trazabilidad y no reescriba ADR-002. La planificación de ADR-002 es la línea base histórica, no un error.

Una sola selección y una selección de varios pedidos siguen el mismo proceso; seleccionar un pedido es el caso `N=1`.

### 1.2 Fuentes auditadas y hechos actuales

Esta SPEC se elaboró siguiendo el formato de archivo único de `docs/specs/SPEC-TEMPLATE.md`, `CONTRIBUTING.md`, `SPEC-HU-015-interfaz-rasterizacion.md` y `SPEC-TA-DASHBOARD-001-dashboard-inicial.md`. Las fuentes de comportamiento y diseño revisadas incluyen ADR-001, ADR-002 (en particular §§2.3 y 2.11), `docs/database/convergencia-orders-multimaterial.md`, documentación vigente de evolución de BD, `docs/testing/README.md`, y los módulos actuales de Optimization, Orders e Inventory.

Hechos comprobados en el código y esquema vigentes:

- Optimization dispone de `/api/optimization/start` para un `id_pedido` y `/api/optimization/rasterize` para una pieza. El inicio valida piezas persistidas y cambia un pedido `PENDIENTE` a `EN_OPTIMIZACION`; rasterizar requiere ese estado. No existe un flujo First Fit, confirmación o resultado persistido completo.
- Domain contiene rasterización de las geometrías admitidas, rasterización de materiales, `SheetLayout.check/place` y comprobaciones de límites, margen, separación y ocupación. El placement vigente no busca rotaciones ni posiciones automáticamente.
- Orders persiste `id_tipo_vidrio`, `espesor_mm`, `cantidad`, geometría y área en cada PIEZA. El modelo y el repositorio actuales demuestran que un pedido puede ser multimaterial. Sus piezas se recuperan por pedido. La creación/edición actual no proporciona la selección de lote ni la orquestación propuesta aquí.
- Inventory modela planchas con medidas, cantidad y estado booleano; y retazos unitarios con geometría, área y estado booleano. Hay movimientos de inventario y operaciones de bloqueo para algunas actualizaciones/bajas manuales. No existe el adaptador de stock compatible ni el consumo transaccional de Optimization descrito en esta SPEC.
- El ORM y la migración R3 vigentes relacionan `OPTIMIZACIONES` directamente con un único `id_pedido`. `EJECUCIONES_OPTIMIZACION` referencia optimización; no hay una asociación de pedidos a una optimización multipedido.
- La autorización actual del inicio usa `EJECUTAR_OPTIMIZACION`. El RBAC dinámico de otra rama no se considera integrado ni fuente de verdad.
- ADR-002 §2.11 conserva First Fit/Best Fit/Worst Fit fuera del Sprint 1 y los ubica en Sprint 2. Esta SPEC documenta el adelanto posterior de FF solamente, sin modificar ni calificar como errónea la decisión histórica; debe conservarse la trazabilidad mediante actualización/ADR posterior.

### 1.3 Objetivo

Especificar la selección explícita de `1..N` pedidos pendientes, preparación y agrupación deterministas de sus unidades, ejecución First Fit contra stock compatible con rotaciones angulares discretas, emisión de progreso observable, reconstrucción del resultado y confirmación transaccional del lote completo. La simulación debe ser de solo lectura respecto del inventario; únicamente la confirmación explícita puede consumir stock y confirmar pedidos.

## 2. Alcance

### Incluye

- Selección de pedidos pendientes de forma explícita, con acción opcional «Seleccionar todos» que no selecciona pedidos fuera del conjunto visible/definido ni inicia automáticamente el cálculo.
- Validación backend del lote completo y transición de estado aceptada para cada pedido antes de ejecutar el cálculo.
- Recuperación de las piezas persistidas, expansión de cantidades en unidades lógicas y trazabilidad por pedido, pieza y unidad.
- Agrupación por `(id_tipo_vidrio, espesor_mm)`, orden determinista de piezas, búsqueda First Fit, rotación angular discreta y validación geométrica por raster.
- Obtención de candidatos de stock compatibles, priorizando retazos activos antes de planchas activas, con orden determinista dentro de cada categoría y evaluación geométrica real de candidatos.
- Progreso real del cálculo, resultado completo reconstruible, visualización y métricas conceptuales.
- Simulación sin mutaciones de inventario y confirmación explícita atómica para el lote entero.
- Evolución coordinada de contratos, permisos, UI y diseño de datos necesaria para soportar el flujo.

### Fuera de alcance

- Best Fit, Worst Fit, optimización continua, garantía de óptimo global o comparación de heurísticas.
- Selección implícita de todos los pedidos pendientes, ejecución de un subconjunto silencioso o confirmación automática.
- Implementar componentes React, transporte de streaming, endpoints, schemas físicos, modelos, migraciones o detalles de despliegue en esta SPEC; esos elementos se concretarán en PLAN.
- Modificar el alcance, criterios, evidencia o estado histórico de HU-015.
- Usar la rama histórica `feature/HU-008-stock-compatible` como fuente integrada. Solo podrá ser antecedente si existe documentación pertinente; su AABB y rotación 0/90 no definen la regla de esta solución.

## 3. Actores, permisos y precondiciones

**Actores:** usuario autenticado y autorizado para consultar, ejecutar o confirmar optimizaciones; la interfaz de Optimization permite seleccionar pedidos y visualizar el cálculo.

**Capacidades conceptuales propuestas:** `optimization.view`, `optimization.execute` y `optimization.confirm`. El backend continúa siendo la autoridad y debe verificar la capacidad en cada operación. Estos nombres no afirman que el RBAC dinámico en desarrollo en otra rama ya esté integrado. La convergencia de permisos debe coordinarse con esa rama y con los permisos vigentes antes de implementar.

**Precondiciones de ejecución:**

- La solicitud contiene entre uno y N identificadores de pedidos distintos elegidos explícitamente.
- El backend vuelve a leer y validar todos los pedidos, sus estados y sus piezas persistidas antes de aceptar el lote.
- Cada pedido seleccionado está en `PENDIENTE`, tiene piezas válidas, y cada pieza tiene material, espesor, cantidad y geometría válidos.
- Todos los datos de geometría, material y resolución usados por la ejecución son compatibles con los límites seguros acordados.
- Si cualquier pedido del lote no es elegible, no se inicia ningún pedido ni se continúa con un subconjunto.

**Precondiciones de confirmación:** resultado completo y confirmable; permisos vigentes; filas y cantidades actuales de stock disponibles para revalidación; pedidos aún en el estado esperado. La aceptación de la simulación por sí sola no reserva inventario.

## 4. Entradas, fuentes de verdad y resultado

### 4.1 Entradas y fuentes

| Dato | Fuente de verdad | Regla funcional |
|---|---|---|
| Selección | IDs explícitos enviados por la interfaz | `1..N`, sin duplicados. «Seleccionar todos» es una acción explícita del usuario. |
| Estado del pedido | Orders / PEDIDO | Backend relee cada estado antes de aceptar. Solo `PENDIENTE` es elegible al inicio. |
| Piezas | PIEZA persistida en Orders | No confiar en geometrías de cliente; releer IDs, material, espesor, cantidad, geometría y área. |
| Unidad lógica | Expansión de `PIEZA.cantidad` | Cada unidad tiene `id_pedido`, `id_pieza` y `unit_index` independiente, comenzando en 1. |
| Grupo de material | Material persistido por PIEZA | Clave exacta `(id_tipo_vidrio, espesor_mm)`. |
| Stock | Inventory | Solo candidatos activos/disponibles y compatibles por tipo y espesor; geometría real se valida en Domain. |
| Parámetros | Configuración efectiva de la corrida | El resultado identifica `resolucion_raster_mm`, `margen_mm`, `separacion_mm` y `paso_angular_grados`; no se fija valor por defecto en esta SPEC. |

Unidades de dominio: longitudes en mm, áreas en mm², tiempos en ms y ángulos en grados.

Una pieza `id_pieza=27, cantidad=3` produce tres unidades `(27,1)`, `(27,2)` y `(27,3)`. Las máscaras pueden reutilizarse para geometría, resolución y orientación equivalentes; cada unidad conserva placement propio.

### 4.2 Contrato conceptual de placement

Cada placement exitoso conserva, como mínimo: `id_pedido`, `id_pieza`, `unit_index`, `id_tipo_vidrio`, `espesor_mm`, `material_source`, `material_id`, identificación de unidad física cuando aplique, `x_mm`, `y_mm` y `rotation_deg`. La representación conserva escala/resolución suficiente para reproducir y dibujar la colocación sin volver a ejecutar el algoritmo.

### 4.3 Resultado conceptual

El resultado de una corrida incluye método `FF`, IDs de pedidos, grupos de material, placements, materiales/unidades físicas utilizados, unidades colocadas y solicitadas, aprovechamiento, merma, retazo recuperable cuando corresponda, planchas nuevas utilizadas, tiempo computacional y configuración efectiva. Un resultado completo permite reconstruir el patrón sin recalcularlo. Una corrida con unidades sin colocar tiene resultado `SIN_SOLUCION` y no es confirmable.

### 4.4 Métricas mínimas y unidades

| Métrica | Unidad | Regla |
|---|---|---|
| `aprovechamiento_pct` | % | Se informa entre 0 y 100. R4 define `area_material_total_mm2` y `area_piezas_colocadas_mm2`, pero el Diseño de BD no prescribe una fórmula matemática para la relación; el contrato de cálculo debe quedar documentado y ser coherente. |
| `merma_mm2` | mm² | No negativa; corresponde a material no aprovechado según la definición de cálculo vigente que se formalice para FF. |
| `planchas_nuevas_usadas` | unidades físicas | No negativa; cuenta unidades físicas de plancha nuevas efectivamente abiertas/utilizadas, no la cantidad de registros de plancha. |
| `retazo_recuperable_mm2` | mm² | No negativa. Solo contabiliza área residual respaldada por geometría válida y reproducible; si no se obtiene geometría válida, el resultado métrico es 0 y no se crea un retazo. |
| `tiempo_computacional_ms` | ms | No negativo; mide el algoritmo y validaciones locales, excluyendo red, renderizado frontend y animaciones. |

Estos nombres, unidades, nulabilidad obligatoria de las cinco métricas principales y restricciones de rango siguen el contrato R4 de `docs/database/convergencia-v1-1.md` y `METRICA_EJECUCION`. R4 no define todas las fórmulas derivadas ni obliga a una igualdad matemática entre columnas. El tiempo computacional no incluye red, renderizado frontend ni animaciones.

## 5. Reglas de negocio

- **RN-01 — Selección explícita:** el lote es exactamente el conjunto elegido por el usuario. No se agregan todos los pedidos pendientes implícitamente.
- **RN-02 — Validación atómica de inicio:** backend relee el lote completo. Una entrada ausente, duplicada, no pendiente, sin piezas o inválida rechaza la solicitud sin transición parcial ni ejecución de subconjunto.
- **RN-03 — Estados:** el inicio aceptado conduce todos los pedidos seleccionados de `PENDIENTE` a `EN_OPTIMIZACION`. Una solución FF completa conduce todos a `OPTIMIZADO`; confirmar conduce todos a `CONFIRMADO`. Si la corrida finaliza normalmente como `SIN_SOLUCION`, la corrida conserva ese resultado, no consume stock y todos los pedidos participantes que habían pasado a `EN_OPTIMIZACION` vuelven a `PENDIENTE`; ninguno queda parcialmente optimizado. Esta reversión corresponde solo a la finalización controlada `SIN_SOLUCION`.
- **RN-04 — Unidades:** `cantidad=N` significa N placements independientes con `unit_index` entre 1 y N. No se pierde trazabilidad al reutilizar máscaras.
- **RN-05 — Multimaterial:** se forma un grupo por cada pareja exacta `(id_tipo_vidrio, espesor_mm)`, incluso si un mismo pedido tiene varias parejas. Ninguna pieza puede colocarse en un material incompatible.
- **RN-06 — Preparación determinista:** ordenar unidades por `area_mm2` descendente; mayor dimensión de bounding box descendente; `id_pedido` ascendente; `id_pieza` ascendente; `unit_index` ascendente. Es una preparación previa a la heurística; no es Worst Fit.
- **RN-07 — First Fit:** para cada unidad preparada, recorrer en orden determinista los candidatos de material/unidad física, orientaciones permitidas y posiciones; registrar la primera combinación geométricamente válida y continuar con la siguiente unidad. No escoger la mejor entre todas las posiciones válidas.
- **RN-08 — Rotaciones discretas:** para `paso_angular_grados = Δθ`, explorar `0, Δθ, 2Δθ, ... < 360`. Es búsqueda angular discreta, no continua, y no garantiza óptimo global. Orientaciones geométricamente equivalentes pueden evitar recomputación. Una circunferencia no requiere rerasterizarse para cada ángulo.
- **RN-09 — Stock compatible y prioridad:** compatibilidad mínima por mismo `id_tipo_vidrio`, mismo `espesor_mm` y candidato activo/disponible. First Fit recorre primero retazos activos compatibles y después planchas activas compatibles para priorizar la reutilización de material existente antes de abrir planchas nuevas. El orden dentro de cada categoría es determinista y se fija en PLAN conforme a los atributos disponibles; la SPEC no inventa desempates físicos.
- **RN-10 — Prefiltro geométrico:** la AABB solo puede actuar como descarte/precheck negativo si no cabe. Que quepa no demuestra placement válido. Todo placement final, incluidos retazos irregulares y polígonos, requiere validación de geometría real mediante raster/motor geométrico.
- **RN-11 — Validez:** cada placement respeta límites del material, margen, separación, ausencia de superposición, geometría real y resolución/escala consistentes. No se acepta una decisión fundada solo en área o AABB.
- **RN-12 — Progreso observable:** el backend produce durante la ejecución un flujo de progreso real hacia el frontend con los eventos semánticos de §6.1. No se reproduce una animación después de que terminó ni se presenta como ejecución en vivo. No se emite un evento por celda o ángulo fallido. El porcentaje se deriva de `placed_units / total_units` y nunca reporta colocadas unidades no aceptadas por Domain. SSE, WebSocket, NDJSON y librerías concretas se deciden en PLAN.
- **RN-13 — Simulación de solo lectura:** ejecutar o visualizar no decrementa planchas, no consume retazos ni crea movimientos reales de inventario.
- **RN-14 — Completitud:** solo es solución completa si cada unidad lógica de todos los pedidos seleccionados tiene un placement válido. Una parcial no puede confirmarse.
- **RN-15 — Confirmación atómica:** una solicitud de confirmación aplica el lote completo o ninguno. Revalida que el resultado sea confirmable, bloquea filas afectadas, vuelve a comprobar disponibilidad/cantidades/estados, descuenta unidades de plancha, consume retazos, registra movimientos y trazabilidad, registra retazos recuperables válidos según política aprobada y marca todos los pedidos `CONFIRMADO`; luego realiza COMMIT.
- **RN-16 — Conflicto y rollback:** si el stock cambió desde la simulación, responder conflicto conceptualmente equivalente a HTTP 409; no sustituir material silenciosamente. Ante cualquier fallo de confirmación, ROLLBACK completo. Nunca confirmar solo parte del lote, dejar stock consumido sin pedidos confirmados, confirmar pedidos sin consumo correspondiente ni consumir dos veces el mismo retazo.
- **RN-17 — Métricas reproducibles:** cada ejecución FF completa produce como mínimo aprovechamiento (%), merma (mm²), planchas nuevas utilizadas (unidades físicas), retazo recuperable (mm²) cuando exista geometría residual válida y tiempo computacional (ms). Se usan los nombres, unidades y restricciones del modelo vigente R4; las fórmulas no prescritas por el Diseño de BD deben documentarse en el contrato de cálculo y ser coherentes en backend/UI. Los valores corresponden a placements/materiales realmente usados.
- **RN-18 — Sobrantes y retazos recuperables:** un retazo nuevo solo se persiste si existe geometría residual válida y reproducible, derivada del material realmente utilizado y de los placements confirmados. Está prohibido inferirlo solo de una bounding box, aproximar silenciosamente un sobrante irregular a rectángulo o registrar área sin geometría. Los límites de ancho/alto/área mínima reutilizable proceden de la configuración vigente. Si no se puede obtener geometría residual válida, no se crea el retazo y `retazo_recuperable_mm2` refleja 0 para esa ausencia.
- **RN-19 — Dependencias limpias:** Domain contiene geometría, raster, rotación, placement, colisiones, margen, separación, First Fit y métricas puras. Application valida selección, agrupa, obtiene stock a través de ports, orquesta, emite progreso y confirma. Infrastructure adapta SQLAlchemy, Orders/Inventory, PostgreSQL, persistencia y locking. Presentation adapta FastAPI, schemas HTTP, autorización, códigos y transporte. Domain no depende de FastAPI, SQLAlchemy, Supabase ni React.

## 6. Flujo principal y eventos observables

1. La interfaz carga pedidos elegibles y el usuario selecciona explícitamente `1..N` pedidos. La interfaz puede ofrecer «Seleccionar todos» y permite revisar el conjunto antes de iniciar.
2. El backend relee todos los IDs y valida estados, piezas, cantidades, geometrías y permisos. Si cualquiera falla, rechaza el lote completo. Si todos son válidos, acepta el inicio y los pedidos pasan a `EN_OPTIMIZACION` conforme a una única operación de lote.
3. Se recuperan las piezas persistidas y se expanden cantidades en unidades lógicas con trazabilidad.
4. Se agrupan las unidades por `(id_tipo_vidrio, espesor_mm)` y cada grupo prepara su secuencia determinista.
5. Se obtienen primero retazos activos compatibles y luego planchas activas compatibles, con orden determinista dentro de cada fuente. La AABB descarta solo lo que definitivamente no cabe; cada candidato restante se somete a comprobaciones de geometría real.
6. Cada unidad se evalúa con First Fit y rotaciones discretas. Durante el cálculo, el backend envía al frontend progreso real con los eventos semánticos definidos en §6.1. El transporte concreto queda para PLAN.
7. El backend produce resultado completo o `SIN_SOLUCION`, calcula métricas y devuelve/expone datos suficientes para renderizar grupos y reconstruir placements. La simulación no altera inventario. Si el cálculo finaliza normalmente `SIN_SOLUCION`, todos los pedidos del lote vuelven de `EN_OPTIMIZACION` a `PENDIENTE` y ninguno queda optimizado parcialmente.
8. Si el resultado es completo, un usuario con permiso confirma explícitamente. El backend revalida, bloquea y aplica transaccionalmente inventario, movimientos, retazos recuperables permitidos y estado de todos los pedidos.
9. La UI muestra resultado confirmado o conflicto/fallo sin presentar como confirmado un lote que no hizo COMMIT.

### 6.1 Contrato conceptual de eventos

Eventos mínimos: `optimization_started`, `group_started`, `piece_started`, `piece_placed`, `group_completed`, `metrics_calculated`, `optimization_completed` y `optimization_failed`.

`piece_placed` contiene información suficiente para dibujar una unidad sin otra consulta de algoritmo: pedido, pieza, `unit_index`, posición X/Y en mm, rotación en grados, grupo/material y `placed_units`, `total_units` y porcentaje calculado. Cada evento se relaciona con la corrida y grupo correspondientes. Los eventos de grupo y corrida identifican el grupo/material y el estado/progreso agregado necesario para mostrar el proceso. El flujo es backend -> frontend y refleja ejecución efectiva, no animación diferida. Los eventos terminales distinguen completado, `SIN_SOLUCION` y fallo. El transporte técnico (SSE, WebSocket, NDJSON u otro) no queda decidido por esta SPEC.

## 7. Flujos alternativos y errores

- **Selección vacía, IDs repetidos o lote inválido:** error de validación; no se inicia ningún pedido ni subconjunto.
- **Pedido deja de estar `PENDIENTE` entre consulta e inicio:** conflicto; el lote completo no queda parcialmente en `EN_OPTIMIZACION`.
- **Pieza sin geometría/material/cantidad utilizable:** rechazar el lote antes de ejecutar placements y devolver causa identificable sin exponer datos internos.
- **Sin stock compatible o alguna unidad no cabe, con cálculo finalizado normalmente:** registrar corrida `SIN_SOLUCION`, no confirmar ni consumir inventario y devolver todos los pedidos participantes desde `EN_OPTIMIZACION` a `PENDIENTE`; no queda ningún pedido parcialmente optimizado.
- **Crash, timeout, caída de infraestructura o proceso interrumpido inesperadamente:** no aplicar automáticamente la semántica de `SIN_SOLUCION` ni inventar una recuperación/transición. PLAN debe definir reconciliación y recuperación segura de estados y corridas.
- **Error de geometría detectado como finalización controlada:** registrar `optimization_failed` según contrato, sin mutar inventario; el tratamiento de pedidos se define en PLAN. No confundirlo con una finalización limpia `SIN_SOLUCION`.
- **Cálculo o conexión de progreso interrumpidos:** el flujo debe diferenciar pérdida de observación del estado real del cálculo; no simular progreso ni asumir confirmación. Para interrupción inesperada, la política segura se concreta en PLAN.
- **Resultado incompleto o manipulado/no confirmable:** rechazar la confirmación.
- **Stock, cantidad o estado cambió después de simular:** conflicto equivalente a 409, rollback total y nueva simulación explícita si el usuario desea continuar.
- **Fallo al actualizar cualquier fila, crear movimiento, registrar retazo o confirmar pedido:** rollback de todos los cambios del lote.
- **Permiso insuficiente o revocado:** backend rechaza consultar/ejecutar/confirmar según capacidad; ocultar un control en UI nunca sustituye autorización backend.

## 8. Criterios de aceptación

| ID | Criterio comprobable |
|---|---|
| CA-01 | Seleccionar o deseleccionar pedidos, incluida la acción explícita «Seleccionar todos», no cambia estados ni inventario. Solo se envía el conjunto seleccionado por la persona. |
| CA-02 | Un lote con uno o varios pedidos `PENDIENTE` válidos se relee y acepta como una única ejecución lógica; `N=1` usa el mismo flujo que `N>1`. |
| CA-03 | Si un ID no existe, está repetido, el pedido no está pendiente, carece de piezas o falla una validación, no se inicia ningún pedido del lote ni un subconjunto. |
| CA-04 | Una pieza de cantidad N genera exactamente N unidades lógicas con índices `1..N` y placements/trazabilidad independientes. |
| CA-05 | Un pedido con más de una pareja material/espesor genera grupos separados por `(id_tipo_vidrio, espesor_mm)` y no mezcla placements incompatibles. |
| CA-06 | La preparación produce el mismo orden verificable según área descendente, dimensión mayor descendente, pedido ascendente, pieza ascendente y unidad ascendente; el orden no se etiqueta como Worst Fit. |
| CA-07 | Solo se evalúan materiales con mismo tipo y espesor, activos/disponibles; se evalúan primero retazos y luego planchas, con orden determinista dentro de ambas categorías. |
| CA-08 | La AABB solo descarta/precomprueba candidatos que no caben; que quepa no demuestra validez. Todo placement, incluido en retazo irregular, valida la geometría real mediante raster/motor geométrico. |
| CA-09 | Con Δθ configurado, las orientaciones evaluadas siguen exactamente `0, Δθ, ... < 360`; el contrato declara búsqueda discreta, sin promesa de óptimo global. Casos equivalentes pueden reutilizar cálculo y círculos no se rerasterizan por rotación. |
| CA-10 | Para cada unidad, First Fit acepta la primera combinación válida según orden de candidato, orientación y posición; no continúa buscando para sustituirla por una combinación posterior supuestamente mejor. |
| CA-11 | Pruebas geométricas muestran que placements dentro de límites respetan margen, separación, escala y ausencia de superposición con formas rasterizadas reales. |
| CA-12 | Cada placement conserva pedido, pieza, unidad, material, espesor, fuente e ID de material/unidad física aplicables, X/Y y rotación. |
| CA-13 | Los eventos mínimos del contrato ocurren durante el cálculo real y mantienen orden/correlación suficiente para distinguir inicio, unidades, grupos, métricas y terminales; no se emite evento por cada celda o ángulo rechazado. |
| CA-14 | El avance observado coincide con `placed_units / total_units`; cada `piece_placed` contiene los datos necesarios para dibujar esa unidad y no se reproduce una animación posterior. |
| CA-15 | Una corrida de simulación exitosa, `SIN_SOLUCION` o fallida no decrementa planchas, no consume retazos ni registra movimientos reales. |
| CA-16 | El resultado completo permite reconstruir el patrón sin ejecutar otra vez el algoritmo e identifica FF, pedidos, grupos, placements, materiales, unidades, configuración y tiempos. |
| CA-17 | Una ejecución FF completa expone `aprovechamiento_pct` (%), `merma_mm2` (mm²), `planchas_nuevas_usadas` (unidades físicas), `retazo_recuperable_mm2` (mm², respaldado por geometría residual válida y 0 cuando no se genera) y `tiempo_computacional_ms` (ms). Aplica nombres/unidades/rangos R4; la fórmula no definida por BD se documenta para el motor. El tiempo excluye red, renderizado frontend y animaciones. |
| CA-18 | Mismos pedidos, stock, configuración y versión de reglas producen la misma preparación, orden de candidatos, placements y métricas deterministas. |
| CA-19 | Si una o más unidades no se colocan en una finalización normal, la corrida queda `SIN_SOLUCION`, la confirmación se rechaza, no se consume stock y todos los pedidos participantes vuelven a `PENDIENTE`; ninguno queda parcialmente `OPTIMIZADO`. |
| CA-20 | Confirmar vuelve a validar el resultado, revalida stock y estados bajo bloqueo y aplica todas las mutaciones del lote en una transacción única. |
| CA-21 | Confirmar descuenta la cantidad exacta de unidades de plancha y consume una sola vez cada retazo utilizado, registrando movimientos y referencias de trazabilidad. |
| CA-22 | Un retazo recuperable solo se registra con geometría residual válida y reproducible derivada del material usado y placements confirmados; nunca desde AABB sola, aproximación rectangular silenciosa ni área sin geometría. Límites de ancho/alto/área mínima vienen de configuración vigente. Si no se calcula geometría válida, no se registra retazo y su área recuperable es 0. |
| CA-23 | La confirmación cambia todos los pedidos participantes a `CONFIRMADO` únicamente dentro del mismo COMMIT que aplica el stock; fallos en cualquier paso revierten todo el lote. |
| CA-24 | Una modificación concurrente de stock después de simular produce conflicto equivalente a HTTP 409, sin sustitución de material, confirmación parcial ni pérdida de movimientos. |
| CA-25 | Un mismo retazo no puede ser consumido por dos confirmaciones concurrentes; una de ellas falla con conflicto y no duplica consumo. |
| CA-26 | Permisos de vista, ejecución y confirmación se exigen en backend. El comportamiento coincide con capacidades convergidas, sin asumir integrada la rama RBAC dinámica. |
| CA-27 | La asociación de una corrida con cada pedido participante permite consultar y reconstruir trazabilidad multipedido conforme al modelo conceptual `OPTIMIZACION 1:N OPTIMIZACION_PEDIDO N:1 PEDIDO`, preservando referencias históricas tras la migración. |
| CA-28 | El E2E crítico permite seleccionar dos pedidos (incluido un caso multimaterial/cantidad), observar progreso y placements, revisar métricas, confirmar y verificar resultado persistido e inventario actualizado. |

## 9. Impacto técnico y decisiones de convergencia

### Módulos y Clean Architecture

La implementación mantiene el monolito modular y la regla `Presentation -> Application -> Domain`; Infrastructure implementa los ports requeridos. Optimization orquesta el flujo sin importar ORM/routers/repositorios concretos de Orders o Inventory. Orders ofrece lectura/validación de pedidos y estado; Inventory ofrece búsqueda de stock y operaciones transaccionales de confirmación por contratos. No se trasladan responsabilidades al frontend.

### Persistencia y base de datos

**Incompatibilidad vigente:** `OPTIMIZACIONES.id_pedido` es no nulo y representa exactamente un pedido por optimización, tanto en ORM como en la migración R3. Ese modelo no puede representar una única corrida First Fit asociada a varios pedidos sin evolución.

**Decisión conceptual del equipo:** una corrida puede relacionarse con `1..N` pedidos mediante una asociación equivalente a `OPTIMIZACION 1:N OPTIMIZACION_PEDIDO N:1 PEDIDO`. Esto contradice/supera el vínculo actual de una optimización con un único pedido. La decisión exige actualizar el documento de Diseño de Base de Datos, evolucionar ORM y Alembic, incorporar pruebas de migración e integridad y preservar la trazabilidad histórica existente. No se fijan columnas físicas definitivas aparte de la asociación conceptual; los detalles, estrategia histórica y reversibilidad se cierran en PLAN/actualización del Diseño de BD. No se crea migración ni se modifica modelo en esta tarea.

**Material por pieza:** el estado actual sí demuestra multimaterial en `PIEZA`; la convergencia Orders/Multimaterial y el código vigente guardan tipo y espesor por pieza. El objetivo reutiliza esa fuente. Sigue pendiente diseñar su paso por lote/resultado e integración con la nueva asociación multipedido; no se afirma que la persistencia actual de Optimización ya soporte grupos o placements multimaterial.

### API, progreso y autorización

La API vigente solo inicia un pedido y rasteriza una pieza. Se requiere contrato funcional de selección por lote, lectura de resultado, progreso real backend -> frontend con los eventos de §6.1, y confirmación. Los cuerpos, rutas, schemas, transporte (SSE, WebSocket, NDJSON u otro), librerías, reconexión, códigos finales y formato de persistencia quedan para PLAN. El resultado y cada evento deben respetar RN-12 y la trazabilidad descrita en §4 y §6.

La solución de roles/permisos dinámicos está en otra rama. Definir capacidades conceptuales no implica integración; el PLAN debe establecer convergencia con seguridad backend actual y no confiar en controles frontend.

### UI

La futura UI de Optimization debe permitir seleccionar `1..N` pedidos, mostrar grupos por material, progreso verdadero, placements, patrón/métricas y acción explícita de confirmar una solución completa. Estados de carga, falta de solución, fallo y conflicto deben distinguirse. No se implementan componentes React en esta SPEC.

### Retazos recuperables

La regla funcional está definida en RN-18 y CA-22: persistir solo geometría residual válida/reproducible, derivada del material realmente utilizado y de placements confirmados; nunca crearla durante simulación ni aproximarla desde AABB. El algoritmo para obtener la geometría residual, su representación y validaciones numéricas corresponden al PLAN. Los criterios mínimos reutilizables de ancho/alto/área provienen de la configuración vigente. Si la implementación no puede obtener geometría residual válida, no crea ese RETAZO.

## 10. Riesgos y límites

- **Evolución multipedido:** la decisión conceptual supera el vínculo único vigente. Sin actualización coherente del Diseño de BD, ORM, Alembic, integridad y trazabilidad histórica, la corrida no puede atribuirse correctamente a todo el lote.
- **Interrupción inesperada:** crash, timeout, caída de infraestructura o proceso interrumpido pueden dejar estado operativo que no equivale a `SIN_SOLUCION`; PLAN debe diseñar reconciliación segura antes de implementar esa recuperación.
- **Geometría residual:** una máscara raster válida para placement no garantiza por sí sola que un sobrante sea geometría reutilizable persistible. Si no se calcula una geometría residual válida, se omite el retazo.
- **Métricas:** R4 fija nombres, unidades, obligatoriedad y rangos; no prescribe todas las fórmulas ni impone relaciones matemáticas entre ellas. El contrato de cálculo de FF debe documentar las fórmulas que no estén definidas por Diseño de BD y mantener coherencia entre salida y persistencia.
- **Rotación discreta y rendimiento:** el resultado depende del paso angular y resolución efectivos. La búsqueda es discreta y no asegura óptimo global; los valores permitidos y presupuesto computacional deberán acordarse en PLAN/configuración vigente.
- **Orden de candidatos:** la prioridad retazos -> planchas está definida, pero el desempate dentro de cada tipo debe usar atributos disponibles de manera estable y quedar documentado antes de implementar para asegurar reproducibilidad.
- **Progreso distribuido:** perder el flujo no demuestra que el cálculo haya terminado. Transporte y recuperación de observación deben distinguir estado del proceso de estado del cliente.
- **Trazabilidad de alcance:** ADR-002 mantiene la planificación histórica de Sprint 2. El adelanto FF requiere un artefacto de decisión posterior que conserve el historial, sin modificar retroactivamente ese ADR.

## 11. Pruebas previstas

Estas pruebas son trabajo futuro especificado; no se ejecutaron ni se atribuyen resultados a esta SPEC.

- Unitarias de Domain: raster/rotación, equivalencia geométrica, preparación determinista, First Fit, candidatos y posiciones, colisiones, límites, margen, separación, máscaras irregulares y métricas.
- Application/use cases: selección explícita, lectura autoritativa, rechazo completo de lote inválido, expansión, agrupación, ports, resultados parciales, progreso, autorización delegada y confirmabilidad.
- Integración PostgreSQL aislado: Orders/Inventory, persistencia reconstruible, transacciones, locks, movimientos, rollback y consumo unitario de retazos.
- API: selección por lote, validaciones/códigos, autorización, contrato de eventos, `SIN_SOLUCION`, conflicto y confirmación completa.
- Migración Alembic para la asociación multipedido: esquema previo/vigente, datos históricos, integridad referencial, upgrade y downgrade/abortos seguros conforme al Diseño de BD actualizado.
- Frontend component: selección, grupos, eventos/progreso real, patrón, métricas, errores, conflicto y confirmación deshabilitada para resultados incompletos.
- E2E Playwright del flujo crítico desde selección explícita de varios pedidos hasta confirmación e inspección de inventario.
- Concurrencia: dos confirmaciones sobre el mismo stock/retazo; conflicto y ausencia de doble consumo/parcialidad.
- Benchmark y reproducibilidad: escenarios documentados, tamaño de lote/resolución/paso angular, límites de recursos y misma salida ante entradas/configuración/versiones iguales. No atribuir tiempos objetivo hasta acordarlos en PLAN.

## 12. Evidencias previstas

Tras implementación, conservar evidencia reproducible del contrato API, prueba PostgreSQL de commit/rollback/concurrencia, recorrido E2E y resultados de benchmark/reproducibilidad en `docs/evidence/sprint-01/<ID>/`, con comandos, contexto y resultados reales según `docs/evidence/README.md`. Esta SPEC no genera evidencia de implementación.

## 13. Pendientes técnicos y documentales

Las decisiones de implementación de esta sección se precisan en [PLAN-S1-optimization-first-fit.md](PLAN-S1-optimization-first-fit.md). No reabren las decisiones funcionales Reviewed.

- **PT-01 — Decisión de alcance trazable:** reflejar el adelanto de FF al cierre de Sprint 1 mediante actualización/ADR posterior, preservando ADR-002 §2.11 como línea base histórica y sin reescribirlo.
- **PT-02 — Asociación multipedido:** el PLAN define el modelo mínimo, el backfill y downgrade seguro. Sigue pendiente actualizar el documento de Diseño de Base de Datos e implementar ORM/Alembic y pruebas de migración/integridad que preserven trazabilidad.
- **PT-03 — Progreso:** el PLAN selecciona `StreamingResponse` + NDJSON y congela el contrato v1. Sigue pendiente implementarlo y validarlo con la UI consumidora.
- **PT-04 — Geometría residual:** el PLAN selecciona una extracción conservadora y reproducible de un rectángulo raster completamente libre. Sigue pendiente implementarla y comprobarla; el mínimo de área se relaciona con PT-06.
- **PT-05 — Recuperación de fallos inesperados:** el PLAN define reconciliación explícita y sin reintento/reset automático. Sigue pendiente acordar autoridad operativa y permisos antes de exponerla; no se hereda la reversión de `SIN_SOLUCION`.
- **PT-06 — Configuración y métricas:** no fijar defaults para `resolucion_raster_mm`, `margen_mm`, `separacion_mm` ni `paso_angular_grados`; se requiere una configuración vigente completa. El modelo actual no contiene un mínimo independiente de área recuperable, por lo que sigue pendiente decidir si existe una regla documentada o se requiere evolución de configuración. Las fórmulas y redondeos R4 quedan detallados en el PLAN.
- **PT-07 — Orden de stock:** el PLAN fija `fecha_registro DESC, id DESC` dentro de retazos y planchas después del filtro de activos; su implementación y pruebas siguen pendientes.

La SPEC está en estado Reviewed y aprobada para implementación / planificación técnica. El PLAN técnico fue aprobado por separado para implementación el 16/10/2026; su reviewer y decisión constan en el historial propio del PLAN. Ninguno de estos estados declara implementación, pruebas o evidencia.

## Historial de estado

| Fecha | Estado | Cambio |
|---|---|---|
| 15/10/2026 | Draft | Se especificaron selección explícita multipedido, expansión y grupos multimaterial, preparación determinista, First Fit con rotación discreta, stock compatible, progreso observable, resultado reconstruible y confirmación atómica. No se implementó código; no se ejecutaron pruebas atribuibles a esta SPEC; no existe aprobación humana todavía. |
| 15/10/2026 | Draft | Draft refinado con prioridad retazos -> planchas; semántica de finalización controlada `SIN_SOLUCION`; requisito de geometría residual válida para sobrantes; progreso real backend -> frontend con transporte delegado al PLAN; relación multipedido conceptual; y adelanto de First Fit respecto de la planificación histórica, sin reescribir ADR-002. No se implementó código ni se ejecutaron pruebas atribuibles a esta SPEC. La SPEC continúa pendiente de revisión humana y no tiene aprobación. |
| 16/10/2026 | Reviewed | Fabricio Danniel Aguilar Chávez revisó y aprobó para implementación / planificación técnica las decisiones funcionales de selección explícita de 1..N pedidos, First Fit, agrupación por material/espesor, expansión de cantidades, prioridad retazos -> planchas, rotaciones discretas, progreso real, patrón final reconstruible, simulación sin mutación de stock, confirmación transaccional, optimización multipedido, retorno a PENDIENTE ante `SIN_SOLUCION` controlado y geometría válida para nuevos retazos. No se atribuyen implementación, pruebas ni evidencia. La aprobación técnica del PLAN se registra de forma independiente en el historial de ese documento. |
