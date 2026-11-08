# comparison-v2 — Catálogo y contratos de seis motores (TA-043 / B01)

Adición S2 finalización: `GET /api/optimization/comparisons-v2/history` permite
consultar comparaciones v1/v2 propias sin ejecutar motores. Parámetros `limit`
(1–20, por defecto 20) y `before_id` (int32 positivo). Devuelve `items` con
`comparison_id`, `profile`, `started_at`, `status`, `order_ids`, `confirmed`,
`released`, y `next_before_id` nullable para paginación descendente. Requiere
`optimization.view`, respeta propiedad y no entrega snapshots ni claves.
No cambia los contratos históricos ni requiere migración.

Estado: **contratos B01 implementados; revisión de Fabricio pendiente**.
[SPEC TA-043](../../specs/SPEC-TA-043-integracion-seis-motores.md),
[PLAN / puerta B01](../../specs/PLAN-TA-043-integracion-seis-motores.md).
No hay endpoint v2 público, coordinador de seis motores ni migración en B01.
Este documento define el contrato que consumirán B02/B03 y los bloques siguientes.

## Catálogo estable

| Orden de presentación | Código técnico `method` | Nombre / etiqueta visible | Clase productiva | Observación nativa |
|---|---|---|---|---|
| 1 | `FF` | First Fit / FF | `FirstFitOptimizer` | Hechos de colocación |
| 2 | `BF` | Best Fit / BF | `BestFitOptimizer` | Hechos de colocación |
| 3 | `WF` | Worst Fit / WF | `WorstFitOptimizer` | Hechos de colocación |
| 4 | `HF` | Hole Filling / HF | `HoleFillingOptimizer` | Reproducción de solución elegida |
| 5 | `M5` | Best Residual Fit / BRF | `BestResidualFitOptimizer` | Hechos de colocación |
| 6 | `M6-BS` | Beam Search acotada / BS-2 | `BeamSearchOptimizer` | Progreso de búsqueda; requiere adaptación visual en B03 |

El catálogo de aplicación asocia clases de optimizador y resultado reales sin
ejecutarlas ni conectarlas al runner público. Las seis identidades son únicas,
exactas y sensibles a mayúsculas. `BRF` y `BS-2` son etiquetas, no aliases de wire.
M6-BS identifica ancho 2; otros anchos se rechazan en el snapshot de este perfil.
No hay selección automática de ganador ni sustitución de resultados entre
las seis ejecuciones. M6 no completa con FF/BF al agotar recursos. HF conserva
su estrategia híbrida existente de búsqueda local y su protección de cobertura.

Revisión académica 08/11/2026: [SPEC-ACADEMIC-800](../../specs/SPEC-ACADEMIC-800-metodos-independientes.md).
La admisión y `ordering_ready` aceptan hasta 800 unidades; los eventos de
comparación admiten hasta 128 KiB. M6 aplica por defecto búsqueda de ancho 2,
hasta 12 candidatos por padre, primera posición por orientación y puntuación
por cobertura/material/envolvente. Los diagnósticos registran
`bounded_candidates`, `candidate_limit` y `positions_per_orientation`.
El modo exhaustivo histórico es explícito y no completa con otro motor.

`methods` contiene el catálogo en este orden. `executions` admite cualquier orden
pero exige los seis códigos y seis IDs distintos. Consumidores deben unir por
`comparison_id` + `execution_id` + `method`, nunca por posición del arreglo.
El catálogo v1 conserva exclusivamente FF/BF/WF y sus consumidores actuales.

## Versiones independientes

| Capa | Formato | B01 |
|---|---|---|
| HTTP/NDJSON/máscaras v2 | `profile: comparison-v2`, `schema_version: 2` | Schemas y parsers optativos; no rutas |
| Layout HTTP dentro de un resultado v2 | `schema_version: 2`, `metodo` explícito | Geometría/R4 reutilizada, razones de unidades extendidas |
| Entrada geométrica desconectada | `input_version: 1` | Codec existente intacto |
| Entrada congelada del agregado | `comparison_snapshot_version: 2` | DTO y codec puro de entrada; integración UoW pendiente B02/B05 |
| Resultado durable | `snapshot_version: 3` | Codec puro con método, resultado opcional y diagnóstico |
| Concurrencia optimista | `version` / `comparison_version` | Contador independiente de formatos |
| Configuración geométrica | `configuration_id`, `configuration_version` | Identidad congelada, no versión del perfil |

La entrada v2 conserva `profile`, `methods`, `input`, `input_sha256`, configuración,
solicitud original, mínimos métricos y `engine_parameters: {"M6-BS":{"width":2}}`.
El hash se comprueba al leer e incluye geometría, cantidades, stock/ranking y
configuración del problema. Los mínimos métricos se capturan aparte. Los campos
de ejecución/presupuestos/parada se incorporarán mediante contratos de runtime
en B02/B04/B05; este codec B01 valida únicamente la entrada congelada, sin escribir BD.

El sobre de resultado 3 tiene exactamente `snapshot_version`, `profile`, `method`,
`result` y `diagnostic`. `result` conserva el JSON geométrico interno existente;
`diagnostic` contiene `origin`, `termination_reason` y contadores `statistics`.
El lector reconstruye el tipo de resultado correcto sin ejecutar heurísticas.
El dueño persistente deberá contrastar `expected_method` y la identidad de su fila.

El lector compatible despacha snapshots 1/2 al lector histórico y 3 al lector
nuevo. Snapshot 1 solo significa FF; snapshot 2 solo FF/BF/WF. No se inventan
diagnósticos históricos: el DTO leído mantiene `diagnostic: null` cuando nunca
se capturó. Un escritor v3 exige diagnóstico explícito. Los lectores y fixtures
v1 permanecen intactos; no se reinterpretan registros ni se crean ejecuciones ficticias.

## Estados de ejecución y resultados

Los IDs son enteros positivos; identidades HTTP nuevas se limitan al rango de las
rutas vigentes (int32 positivo). Contadores son enteros no negativos; booleanos
no se aceptan como contadores/identidades. Medidas decimales mantienen strings.

| `dispatch_state` | `status` | `outcome` | Resultado / elegibilidad |
|---|---|---|---|
| QUEUED / STARTING / RUNNING | EN_EJECUCION | null | Sin resultado persistido, diagnóstico terminal ni elegibilidad |
| TERMINATED | COMPLETADA | COMPLETE | Resultado persistido completo, diagnóstico ENGINE/COMPLETED |
| TERMINATED | COMPLETADA | PARTIAL | Resultado válido incompleto; diagnóstico NO_FIT o límite M6; no elegible |
| TERMINATED | FALLIDA | FAILED | Sin resultado inventado; métricas null, cobertura persistida cero; causa explícita |

`COMPLETADA` en el ciclo de una ejecución significa que terminó y entregó un
resultado; `complete`/`outcome` distingue cobertura total de parcial. El layout
usa `estado: COMPLETADA` o `SIN_SOLUCION` según cobertura y mantiene la causa
independiente: `SIN_SOLUCION` por sí solo no certifica imposibilidad geométrica.
Una unidad faltante tiene `NO_FIT` solo con terminación geométrica NO_FIT; si M6
se interrumpió por recursos conserva `RESOURCE_LIMIT`. No se fabrican placements
de una frontera incompleta ni se promete recuperar un parcial de un kill duro.

Razones ENGINE: `COMPLETED`, `NO_FIT`, `EXPANSION_LIMIT`, `GEOMETRY_PROBE_LIMIT`,
`STATE_MEMORY_LIMIT`, `TIME_LIMIT`. Las cuatro últimas pertenecen a M6-BS.
Razones SUPERVISOR: `GLOBAL_TIME_LIMIT`, `TIME_BUDGET_EXCEEDED`,
`MEMORY_BUDGET_EXCEEDED`, `EXECUTION_FAILED`, `RESULT_SAVE_FAILED`,
`WORKER_STOPPED`, `PROCESS_START_FAILED`, `CANCELLED`. No publicar stack traces.
Contadores diagnósticos no son métricas comerciales ni nuevos límites operativos.

El agregado incluye los campos de v1 más `methods` y `supervisor_stopped`, con seis
resúmenes que declaran despacho/outcome/diagnóstico/result_available. `terminal`
solo es verdadero con supervisor detenido y las seis ejecuciones terminadas.
`incomplete` identifica parciales o fallos. Solo completos persistidos son elegibles
tras cierre seguro, mientras el trabajo no esté liberado/confirmado. Selección
inicial null; selección/confirmación manuales y versionadas. B01 solo valida esos
invariantes, no implementa las acciones ni certifica parada de procesos v2.

Cada resultado HTTP contrasta método, comparación, cobertura, métricas, tiempo y
causa contra su ejecución. Conserva pedidos/piezas/unidades, grupos materiales,
geometría orientada, planchas/retazos físicos y residuales mediante validadores
geométricos existentes. Las métricas ausentes son null; nunca ceros ficticios.

## Eventos, máscaras y M6

NDJSON usa secuencia global y secuencia por ejecución, UTC, perfil/versión,
comparación y scope explícito de ejecución/método. Globales: `comparison_accepted`,
`comparison_finished`, `heartbeat`, `snapshot_required`; sus identidades de motor
y `presentation` son null. Los demás identifican la ejecución y presentación.

Se conservan los hechos tipados de preparación, orden y colocación de v1; se
añaden `execution_state` y `search_progress`. `result_persisted` exige resultado
disponible y `execution_failed` exige outcome FAILED. Ninguna notificación de
persistencia debe emitirse antes del commit: ese comportamiento pertenece a B05.
Una máscara declara también perfil/versión, comparación y ejecución/método;
las referencias cruzadas se rechazan. Tamaños/ventanas y políticas visuales
reutilizadas no se amplían en B01.

`presentation` es OBSERVED, PROVISIONAL o FINAL_REPLAY. En esta primera versión
`search_progress` de M6 solo ofrece contadores (niveles completos, procesadas,
expansiones, sondeos y tamaño de frontera): **no** ofrece ramas/layouts provisionales.
Su presentación es PROVISIONAL. Los hechos de colocación de M6 solo se admiten
como FINAL_REPLAY de la solución elegida; no se concatenan ramas exploradas como
placements definitivos. El adaptador real y la presentación se implementarán en
B03/B07. HF conserva su observación de solución elegida sin alterar políticas.

## API futura: contrato, no endpoint funcional B01

Prefijo previsto `/api/optimization/comparisons-v2`. No aparece en OpenAPI/rutas
productivas de B01; no se instala un placeholder que acepte trabajo incompleto.

| Operación / subrecurso | Contrato previsto | Bloque consumidor |
|---|---|---|
| POST / | `{order_ids}`, Bearer, Idempotency-Key; resumen v2 y Location | B05/B06 |
| GET /requests/{key}, GET /{id} | Recuperación por actor/clave o ID y resumen | B06 |
| GET /{id}/executions/{execution_id} | ExecutionResponseV2, resultado opcional | B06 |
| GET /{id}/events | ComparisonEventV2 NDJSON, cursor global | B05/B06 |
| GET /{id}/executions/{execution_id}/visual y /visual/masks/{mask_ref} | Manifiesto/descriptores/payload de máscaras del dueño | B06/B07 |
| PUT /{id}/selection | `{execution_id, expected_version}` | B08 |
| POST /{id}/confirm | Mismo cuerpo + Idempotency-Key; recibo v2 | B08 |
| POST /{id}/release | `{expected_version}` | B06/B08 |

Permisos, claves de 8–64 caracteres y categorías de error conservan el contrato
actual. El perfil se valida contra el persistido. Se prevé 409
`COMPARISON_PROFILE_MISMATCH` ante recurso de otro perfil; misma clave con otro
perfil/lote produce conflicto. B06 implementará esa política; B01 no cambia errores
de endpoints v1. `/comparisons` continúa con tres motores y `/runs` con FF/visual-v2.
No se consume inventario al simular ni seleccionar; la confirmación transaccional
del elegido sigue perteneciendo a B08.

## Artefactos y verificación B01

[Fixture compartido](comparison-v2.json): seis resultados de motores productivos
directos sobre una entrada común pequeña. Estados/eventos son ejemplos construidos
para contratos; no demuestran integración pública ni concurrencia. El parcial
procede de M6 con max_expansions=1; el fallo es un ejemplo tipado, no una muerte
de proceso ejecutada para generar el fixture. Tiempos son los de esa captura.

Desde backend, `python -m tests.unit.optimization.comparison_v2_support` regenera
el archivo y valida schemas; tiempos pueden variar, layouts/identidades se conservan
sin corte temporal. El fixture v1 nunca se sobrescribe. T-01/T-07 verifican ambos
lenguajes, identidades, rechazos, round-trip y regresión histórica.

Evidencia, inventario de condiciones de tres y alcance de CA-02/11/12/14 en
[TA-043/B01](../../evidence/sprint-02/TA-043/B01/README.md). ST-INC-01 acredita
servicios reales v1 y legacy; los seis públicos, migración, adapters/supervisión
v2 y smoke integral permanecen pendientes de sus bloques. Se requiere revisión
de Fabricio antes de avanzar a consumidores B02/B03.

## Persistencia B02: composición durable interna

La autorización posterior de B02 incorpora una migración aditiva y un repositorio
optativo; no cambia estos schemas HTTP, los codecs/fixtures B01, `/comparisons`
ni `/runs`, ni publica todavía rutas v2.

`comparison_snapshot` guarda íntegro el sobre de entrada B01 versión 2, con
perfil y seis métodos congelados, más un objeto hermano `runtime` cuyo único
campo inicial es `supervisor_stopped_at` (UTC o null). El codec puro recibe solo
la entrada; `comparison_version` continúa siendo el contador SQL optimista,
independiente de las versiones de perfil, entrada y resultado.

Cada `patron_resultado` v2 contiene `profile`, `comparison_id`, `execution_id`,
`method`, `dispatch_state`, `snapshot`, `residual_rectangles` y `visual_references`.
`snapshot` es null mientras está activo y es el sobre B01 de resultado versión 3
al terminar, con resultado/completitud y diagnóstico; permite fallos sin layout.
El despacho QUEUED/STARTING/RUNNING/TERMINATED no cambia los estados SQL históricos.
Las referencias de máscara guardan perfil/versión y propietario completo;
persistir una referencia no garantiza disponibilidad del bitmap ni replay visual.

Se reutilizan tablas, FK y unicidad actuales. Solo `ck_ejecuciones_metodo` se
amplía a `FF/BF/WF/HF/M5/M6-BS`. Los lectores históricos de resultado 1/2 y agregado
1 se conservan sin backfill; el lector compatible devuelve sus DTO originales.
El downgrade comprueba incompatibilidades bajo bloqueo antes de cualquier DDL.
Registrar una parada observada es una operación interna de persistencia: la
prueba real de procesos y la liberación de admisión pertenecen a B05, y no se
deducen de esa marca por sí sola. Selección/confirmación v2 pertenecen a B08.

Validación y límites de lo demostrado: [evidencia B02](../../evidence/sprint-02/TA-043/B02/README.md).

## Propiedad interna del runtime B05 (ampliación autorizada)

Fabricio autorizó ampliar exclusivamente el hermano `runtime`, sin cambiar el
esquema SQL/Alembic ni los contratos HTTP, codecs puros de entrada/resultado o
presupuestos B04. El lector conserva el formato B02 anterior de un solo campo.
Las nuevas aceptaciones coordinadas escriben `runtime_version: 1`,
`supervisor_stopped_at`, `supervisor` y `workers`.

`supervisor` es null antes del claim o `{token, identity: {pid, start_ticks}}`;
el token identifica al dueño del hilo y la identidad a su proceso Linux.
`workers` relaciona IDs de ejecución pertenecientes al agregado con identidades
PID/start_ticks. Un valor null registra intención de spawn antes de crear el
proceso y conserva la ambigüedad si el dueño muere sin registrar su identidad.
La identidad se persiste antes de permitir que el worker atraviese el gate.

El cierre local exige join externo del supervisor y prueba de parada de procesos,
lectores y monitor; luego confirma la marca durable y libera admisión compartida
FF/v1/v2. Una marca lógica, un TTL o recibir el último resultado no prueba parada.
Recuperación no recalcula ni mata procesos ajenos: dueño vivo/desconocido,
intención sin identidad o falta de acceso a los metadatos mantienen el bloqueo
operativo. Se compara PID **y** start_ticks para no confundir reutilización de PID.
El formato antiguo legible no recibe identidades inventadas.

Tras perder el proceso dueño, solo se cierra automáticamente una aceptación sin
intenciones de spawn registradas y con dueño demostrado muerto. Si hubo workers,
sus PID directos muertos no acreditan por sí solos ausencia de descendientes;
sin el reporte de join previo se conserva el bloqueo hasta obtener evidencia
externa. La recuperación exige plataforma/preflight admitidos para interpretar
identidades de procesos. No se añade una ruta administrativa en B05.

Los estados de ejecución y snapshots siguen siendo los de B01/B02.
`runtime_dispatched` y `runtime_engine_started` son estadísticas enteras internas
del diagnóstico existente para distinguir las ejecuciones nunca iniciadas; no
sustituyen sus causas ENGINE/SUPERVISOR. `result_persisted` se entrega solo tras
commit. Este puerto interno no publica eventos HTTP v2: su exposición es B06.

## Publicación B06 — 04/11/2026

Los contratos anteriores de B01 quedan publicados en el prefijo explícito
`/api/optimization/comparisons-v2`. Se implementan POST colección, GET por ID/clave,
GET ejecución, GET eventos, GET manifiesto/máscara y POST release, con los
subrecursos de la tabla. PUT selection y POST confirm **no están registrados**:
continúan pendientes de B08. Las capacidades de elegibilidad del resumen conservan
la semántica contractual B01; no certifican disponibilidad de esos endpoints.

V2 requiere permiso vigente y pertenencia al actor de la comparación. Solicitud
ajena o ejecución/máscara fuera de scope devuelve 404 sin revelar sus datos.
Por clave se consulta exclusivamente al actor autenticado. Recurso propio de otro
perfil devuelve 409 `COMPARISON_PROFILE_MISMATCH`. V1 conserva su acceso por
permiso, sus tres métodos y el error 409 `STATE_CONFLICT` existente al recibir un
recurso v2; `/runs` sigue siendo el lector FF histórico. No se detectan perfiles
mediante intentos de selección/confirmación ni se convierten registros.

POST responde 201 y Location con un resumen autoritativo, que puede haber avanzado
desde la aceptación. La misma clave/actor/lote recupera el mismo agregado y seis
IDs; otro lote/perfil da conflicto. Los IDs JSON v2 son enteros estrictos; no se
coercionan booleanos o strings. Se conservan los guards RBAC y el formato seguro
`{"detail":{"code":"...","message":"..."}}` de categorías vigentes. No cambian
schemas ni errores históricos v1.

La consulta de un agregado sin dueño local con cierre incierto devuelve 503
`RECOVERY_BLOCKED`, con `comparison_id` público y mensaje controlado; mantiene la
reserva operativa. Sus ejecuciones durables siguen consultables y declaran
`eligible: false`; el header `X-Comparison-Recovery: BLOCKED`, expuesto por CORS,
hace explícita la incertidumbre. No se publican token interno, PID, start_ticks,
trazas, rutas privadas o metadatos crudos de runtime. La recuperación delega en el
dueño B05 y nunca fuerza marcas de cierre ni vuelve a optimizar.

Los eventos respetan `ComparisonEventV2`, secuencia global y por ejecución,
presentación y UTC. Se entrega solo historia realmente retenida, con máximo dos
observadores y ventanas B04/B05 compartidas. Cursor futuro da 422; cursor ya
expulsado da 409 `EVENT_CURSOR_EXPIRED` y `latest_sequence`, o `snapshot_required`
si la expulsión ocurre durante un stream. Recuperar por GET el resumen/resultados
persistidos. Runtime expirado/reiniciado da 410 `VISUAL_DATA_UNAVAILABLE`, nunca
replay fabricado. La desconexión HTTP libera al observador, no cancela los motores.
El stream no conserva conexiones DB abiertas.

La proyección usa exactamente la retención B05: reemplaza el registro interno por
NDJSON, sin segunda ventana. TTL o relevo de trabajo retiran máscaras/eventos;
sus referencias durables no garantizan disponibilidad del bitmap. M6 solo publica
contadores PROVISIONAL; su resultado final procede del snapshot ganador y no se
recalcula para animarlo. La UI de seis motores y visores integrados siguen en B07.

POST release exige dueño, permiso execute, versión vigente y cierre seguro ya
demostrado; no cancela ni desbloquea un supervisor incierto. Reutiliza el ciclo de
pedidos sin consumo y conserva resultados/IDs. El repositorio compone los mismos
metadatos operativos de liberación del ciclo v1 (`released_at`, `released_by`,
`released_selection_id: null`) junto a la entrada, separados del codec puro B01
y de `runtime`. Son opcionales para lectores históricos; no se ejecuta backfill,
no cambia SQL/Alembic y no se implementa selección/confirmación. Un reintento
inmediato de la misma liberación recupera su versión sin duplicar efectos.

Pruebas, endpoints, datos sintéticos y límites: [evidencia B06](../../evidence/sprint-02/TA-043/B06/README.md).

## Activación B08 — selección y confirmación manual

El estado de publicación descrito en B06 es histórico. B08 activa exactamente
`PUT /{id}/selection` y `POST /{id}/confirm` de la tabla contractual, sin alterar
sus schemas B01 ni las rutas v1. Selección exige `optimization.execute` y
confirmación `optimization.confirm`; ambas exigen dueño, perfil v2, pertenencia,
resultado completo durable y cierre seguro B05. `RECOVERY_BLOCKED` no se fuerza.

La selección inicial sigue siendo null. Se permite cambiarla antes de confirmar
con `expected_version` vigente, incrementando `comparison_version`; no consume
inventario. Tras confirmar, selección y recibo son inmutables. Liberar antes de
confirmar borra la selección y conserva su ID en `released_selection_id`, usando
el mismo ciclo v1 y sin consumir stock.

La confirmación reutiliza la transacción v1 y su revalidación de inventario:
comparación, ejecución elegida, asociaciones, pedidos y fuentes en orden estable;
consumo, movimientos, retazos, pedidos y recibo en un solo commit. El recibo
operativo `confirmation` ocupa los sobres JSON existentes del agregado y de la
ejecución elegida, separado de la entrada B01 y del resultado snapshot 3. No hay
nuevas columnas, constraints, migraciones ni cambios del codec puro. Las lecturas
validan concordancia de método, ejecución, actor, versión y fuentes; los cinco
resultados no elegidos permanecen intactos. Los diagnósticos de motor sobreviven
a la actualización de métricas efectivamente recuperables; un retazo descartado
por Inventario no se presenta como creado.

La clave, ejecución y versión originales recuperan el mismo recibo después de un
commit, incluso si la respuesta se perdió. Otra operación sobre una comparación
confirmada produce `ALREADY_CONFIRMED`; versión obsoleta produce `STATE_CONFLICT`,
stock incompatible `STOCK_CONFLICT` y resultado no elegible `NOT_CONFIRMABLE`, con
los códigos HTTP existentes (incluido 422 para este último). La UI conserva el
ID histórico y la clave durante reintentos, y consulta antes de repetir efectos.

Alcance, pruebas y smoke reales: [evidencia B08](../../evidence/sprint-02/TA-043/B08/README.md).
