# API de comparación FF/BF/WF — comparison-v1

Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe; revisión pendiente.
SPEC: [OPT-MULTIMOTOR-VISUAL](../../specs/SPEC-OPT-MULTIMOTOR-VISUAL.md).

El flujo principal acepta un lote, ejecuta los tres motores concurrentemente y
conserva tres resultados. La persona elige uno después de comparar; la API no
elige un ganador. Seleccionar no consume inventario. Confirmar aplica solo la
ejecución elegida, con revalidación transaccional del stock.

## Preparación y compatibilidad

Aplicar mediante el procedimiento habitual la migración aditiva
`s2cmp01a1b2c`, posterior a `s1opt02b4c6d`. Añade metadatos de comparación al
esquema existente; no crea tablas por motor. El downgrade rechaza una base con
historia comparativa antes de ejecutar DDL. No se ejecutaron migraciones sobre
la base remota durante el desarrollo.

Esta versión requiere Linux con procfs y límites de procesos disponibles, un
solo proceso web y al menos 1 GiB disponible al admitir trabajo. No tiene
coordinación distribuida entre réplicas. Rechaza plataformas o recursos
insuficientes; no sustituye el cálculo por tres llamadas secuenciales.

`/api/optimization/runs` mantiene FF V1 y sus eventos `visual-v2`.
`comparison-v1`, `schema_version: 1`, es un recurso separado. El codec durable
de resultado comparativo es V2 e incluye el método; no debe confundirse con la
versión del perfil HTTP. Los resultados históricos FF no se convierten en una
comparación ficticia. La UI puede abrirlos desde su identificador histórico.

## Recursos HTTP

Todas las rutas siguientes parten de `/api/optimization/comparisons` y
requieren autenticación Bearer. Los IDs son enteros positivos.

| Método / ruta relativa | Entrada | Permiso / salida |
|---|---|---|
| `POST /` | `{"order_ids":[1,2]}` y `Idempotency-Key` | `optimization.execute`; 201, resumen y `Location` |
| `GET /requests/{key}` | Clave de aceptación | `optimization.view`; solicitud del actor autenticado |
| `GET /{id}` | — | `optimization.view`; resumen autoritativo |
| `GET /{id}/executions/{execution_id}` | — | `optimization.view`; resultado de ese motor, o `null` si aún no está guardado |
| `GET /{id}/events?after_sequence=0` | Cursor global | `optimization.view`; NDJSON independiente del cálculo |
| `GET /{id}/executions/{execution_id}/visual?offset=0` | Paginación del manifiesto | `optimization.view`; máscaras y últimos hechos retenidos |
| `GET /{id}/executions/{execution_id}/visual/masks/{mask_ref}` | Ventana opcional | `optimization.view`; máscara exacta, aislada por ejecución |
| `PUT /{id}/selection` | `{"execution_id":7,"expected_version":4}` | `optimization.execute`; nueva selección y versión |
| `POST /{id}/confirm` | Mismo cuerpo y `Idempotency-Key` | `optimization.confirm`; recibo del elegido |
| `POST /{id}/release` | `{"expected_version":4}` | `optimization.execute`; liberación segura conservando historia |

Las claves son de 8 a 64 caracteres ASCII, letras, números, guion o guion bajo.
Usar una nueva clave por intención de aceptación o confirmación y conservarla
antes de enviar. Repetir la aceptación con igual actor, clave y lote recupera
la comparación existente. Otro lote con esa clave produce conflicto. La
consulta por clave pertenece al actor; las consultas por ID siguen el permiso
de consulta del sistema, sin introducir una nueva separación por propietario.

Ante una respuesta de aceptación ambigua, consultar `/requests/{key}` y
recuperar su ID. No enviar un POST con otra clave para el mismo intento.
Ante confirmación ambigua, recuperar el resumen/recibo o repetir exactamente
la misma operación y clave. El recibo persiste para evitar consumos duplicados.

## Resumen, selección y confirmación

El resumen contiene `comparison_id`, `version`, `input_sha256`, `order_ids`,
configuración congelada y `requested_pieces`, además de exactamente tres
ejecuciones con `execution_id` y `method` (`FF`, `BF`, `WF`). No inferir el
motor por la posición en un arreglo.

Cada ejecución declara estado, completitud, unidades colocadas/solicitadas,
métricas, tiempo de cálculo y código de fallo público. Las métricas de un
motor fallido son `null`; mostrarlas como cero haría una comparación engañosa.
El tiempo de cálculo excluye esperas de entrega de telemetría y no constituye
una recomendación de ganador.

En el resultado de una ejecución comparativa, cada grupo puede incluir
`stock_compatible`. `false` significa que la captura común no encontró
planchas ni retazos compatibles para ese material y espesor; la interfaz debe
identificar el grupo y no presentar una distribución vacía como solución.
Este diagnóstico no altera el contrato histórico de `/runs`.

`terminal`, `incomplete`, `released`, `confirmed`, `selection_allowed` y
`confirmable` gobiernan las acciones del agregado. Una ejecución completa y
guardada solo se vuelve elegible al terminar los tres trabajadores. Un fallo
parcial se informa; los éxitos completos siguen disponibles para elección
humana. Un resultado incompleto no es confirmable. Inicialmente
`selected_execution_id` es `null`.

Enviar siempre la versión recuperada al seleccionar, confirmar o liberar. Una
versión obsoleta o ejecución ajena responde conflicto y exige recuperar el
estado. No aceptar un layout arbitrario enviado por el navegador. Confirmar
bloquea y revalida comparación, elección, pedidos y stock; cualquier fallo
revierte consumo, movimientos y remanentes. La confirmación queda también
trazada en el snapshot de la ejecución elegida para consultar el origen de
sus retazos mediante inventario.

La solicitud original sigue disponible después del cálculo, selección,
confirmación y recarga. Usa mm, mm² y grados. Conserva formas, cantidades,
materiales y medidas persistidas. Si un dato histórico no existe, la interfaz
lo informa o etiqueta la medida como calculada; no reconstruye una medida
ingresada desde el placement girado. El cambio del formulario a cm es un
trabajo posterior acordado.

## Eventos y presentación

Cada línea NDJSON incluye perfil, versión, comparación, `sequence`, instante
UTC, tipo de evento y `data`. Los eventos de motor incluyen además
`execution_id`, `method` y `execution_sequence`. Los globales llevan esos tres
campos en `null`. Validar ambas identidades también en las referencias a máscaras.

Hechos principales: `comparison_accepted`, `engine_ready`, `engine_started`,
`preparation_started`, `piece_rasterizing`, `piece_ready`,
`preparation_completed`, `ordering_ready`, `orientation_testing`,
`source_selected`, `piece_started`, `piece_placed`, `piece_unplaced`,
`group_started`, `group_completed`, `result_persisted`, `execution_failed` y
`comparison_finished`. El resultado se anuncia después de su commit.
Las orientaciones se muestrean; colocaciones y resultados no se muestrean.

La UI presenta máscaras → orden disponible → giros/colocaciones → resultado.
El orden corresponde al algoritmo real; no vuelve a ordenar para animarlo.
Las transiciones de presentación entre fases observadas no retrasan el cálculo.
Si este terminó antes, se indica que se muestran pasos observados. Pausar la
vista, cambiar de pestaña o desconectar el stream no pausa ni cancela motores.
Movimiento reducido elimina transiciones conservando ángulos y datos.

El cursor es global y creciente. Los heartbeats cada 10 s no avanzan la
secuencia. Un cursor fuera del historial produce `EVENT_CURSOR_EXPIRED` (409)
con el cursor reciente, o `snapshot_required` si caduca durante la transmisión.
Recuperar resumen, resultados y manifiestos y reconectar desde la secuencia
recuperada. No fabricar un replay íntegro a partir de muestras.

## Máscaras, límites y recuperación

Los manifiestos paginados exponen preparación, orden disponible, hecho actual,
última orientación, secuencia por ejecución y descriptores retenidos. Respetar
`next_offset`; una referencia solo se consulta en su comparación y ejecución.
Las ventanas admiten `row_start`, `column_start`, `row_count` hasta 256 y
`column_count` hasta 1024, con respuesta máxima de 256 KiB.

| Recurso | Límite aplicado |
|---|---|
| Comparaciones activas | Una por proceso web, admisión exclusiva compartida con FF histórico |
| Trabajadores | Tres procesos `spawn`, entrada JSON común validada por SHA256, barrera de arranque |
| Memoria | 1 GiB RSS agregado muestreado; 240 MiB supervisor; 256 MiB de espacio virtual duro por worker; reserva auxiliar de 16 MiB |
| Tiempo | Arranque 30 s; cálculo por motor 120 s; global 900 s (antes 180 s; ver SPEC-TA-037 v1.4 y SPEC-TA-043) |
| IPC | Cola de un paquete por worker; paquete máximo 12 MiB, visual 4 MiB |
| Observación | Dos observadores; lotes de hasta 16 eventos, de hasta 128 KiB cada uno (ACADEMIC-800) |
| Retención | 32 MiB visuales compartidos entre los tres; 8 MiB y hasta 4096 eventos |
| Vigencia visual | Hasta 300 s tras terminar, o hasta que una nueva comparación sustituya la retenida |

Los máximos de entrada son 20 pedidos, 800 unidades (ver SPEC-ACADEMIC-800), 128 vértices y
50 unidades físicas de stock por grupo/material. No garantizan que cualquier
combinación de sus máximos quepa en memoria/tiempo. Superar el presupuesto
produce un fallo explícito; no es «sin solución». RSS es muestreado y cuenta
páginas compartidas varias veces; no equivale a memoria física única.

La retención es efímera en el proceso web. Si expira, se agota o reinicia,
`VISUAL_DATA_UNAVAILABLE` informa la ausencia; resultados y solicitud siguen
en BD y no se recalculan para dibujarlos. La recuperación comprueba identidad
del supervisor/trabajadores con PID y tiempo de inicio. Solo reconcilia y
devuelve pedidos cuando se demuestra su terminación. Un TTL de observación no
prueba que un trabajador murió. Sin prueba de parada se conserva la admisión.

Los errores mantienen el envoltorio público de Optimization. Capacidad ocupada
y recurso/plataforma insuficientes responden 503; identidad inexistente 404;
estado/versión/stock conflictivos 409; autenticación/permisos 401/403. Consultar
los códigos específicos del cuerpo antes de decidir una recuperación.

## Fixture y evidencia

[comparison-v1.json](comparison-v1.json) contiene hechos, máscaras y resultados
reales de los tres motores sobre un caso sintético. Se genera con
`experiments/optimization/export_comparison_contract.py`; su captura secuencial
valida serialización, no demuestra concurrencia. Las pruebas backend y frontend
consumen el mismo archivo. La concurrencia se acredita por separado con barrera
y procesos reales, junto con la [evidencia de integración](../../evidence/sprint-02/OPT-MULTIMOTOR-VISUAL/README.md).
