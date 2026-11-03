# comparison-v2 — Catálogo y contratos de seis motores (TA-043 / B01)

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
No hay fallback a FF ni selección automática de ganador.

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
