# SPEC-EN-UX-004 — Cancelación real y segura de comparaciones

## Información general

| Campo | Valor |
|---|---|
| Estado | **Draft — contrato propuesto, sin endpoint ni implementación aprobada** |
| Incremento | EN-UX-004 / P1 |
| Dependencias | EN-UX-001, EN-UX-002, supervisor B04/B05, comparison-v2 |
| Revisión | Humana y de seguridad obligatoria antes de merge |
| Repositorios | Contrato en este repositorio; backend `newglass-backend`; frontend `newglass-frontend` |
| Base documental | `integration-02` |
| Referencias | SPEC-TA-043, SPEC-TA-040, contrato comparison-v2 |

## 1. Objetivo

Permitir a un usuario autorizado interrumpir una comparación de seis motores **sin generar confirmaciones ni descuentos de inventario, sin liberar prematuramente una reserva ni anunciar un cierre antes de verificar la terminación del supervisor y todos los procesos descendientes**.

La acción NO equivale a «Pausar vista» ni a «Liberar pedidos sin confirmar». No se altera la implementación matemática FF, BF, WF, HF, M5 o M6-BS.

## 2. Situación verificada sobre backend/main

- `presentation/comparison_v2_routes.py` expone creación, consulta, historial, selección, confirmación y liberación, pero **no POST /cancel**.
- `ComparisonV2Coordinator` posee un `job.cancel` (threading.Event), un único trabajo activo, supervisión con identidad de proceso y `_close` con comprobación de workers y lease.
- `SequentialProcessRunner` recibe una señal `cancel` e interrumpe workers a través de sus mecanismos de terminación y join. El estado de fallos actual usa también `WORKER_STOPPED`, que no distingue una cancelación aceptada por el operario.
- El snapshot JSON durable de comparación guarda `runtime.supervisor`, `workers` y `supervisor_stopped_at`, pero no intención persistente de cancelación.
- `parseComparisonV2` y el modelo Pydantic son estrictos; **ampliar estados de respuesta exige versionar y probar el contrato simultáneamente en backend y frontend**.
- El reinicio con supervisor no verificable conserva admisión bloqueada. No se debe resolver esa situación matando un PID no identificado.

## 3. Contrato de operación propuesto (pendiente de implementación)

### API

`POST /api/optimization/comparisons-v2/{comparison_id}/cancel`

Requiere permiso `optimization.execute`, propietario del trabajo y encabezado `Idempotency-Key` válido. Cuerpo JSON `{ "expected_version": <int> }`. La clave se vincula al actor y comparación; reutilizarla con otro recurso/actor debe fallar sin actuar.

- **202 Accepted** cuando se registró durablemente la solicitud y la detención aún no se acreditó. Respuesta incluye `comparison_id`, `cancel_state: "REQUESTED" | "STOPPING"`, y `version`; no declara `terminal=true` por el simple envío.
- **200 OK** solo si se verificó cierre, terminalidad y consistencia; la respuesta distingue `cancel_state: "CANCELLED"` del término natural `"COMPLETED"`.
- **409 Conflict** cuando la comparación se confirmó/liberó o el mismo identificador tiene otra clave incompatible. La llegada durante cierre natural no debe reescribir una comparación completada.
- **404/403** según política vigente para recursos inexistentes o no autorizados; no filtrar identidades entre usuarios.
- **503 RECOVERY_BLOCKED** si la supervivencia de workers es incierta; sin fingir cancelación.
- Repetir una solicitud con igual clave y actor devuelve el estado durable actual sin generar una segunda señal, movimiento de stock ni incremento indebido de versión.

Un GET posterior de la comparación debe exponer un estado de cancelación durable; se requiere evolución **versionada** de los DTOs, validadores React, esquemas Pydantic y documentación de contrato. No reutilizar el indicador `released` para significar cancelación.

### Modelo durable

El snapshot de comparación podrá incorporar un bloque `cancellation` con `requested_at`, `requested_by`, `request_key`, `status` y `verified_at`; solo se persisten metadatos y nunca PIDs no verificados como prueba. Se definen transiciones atómicas con `comparison_version` y bloqueo SQL, aprovechando el JSON versionado actual o una migración Alembic reproducible **solo si las invariantes lo requieren**. No modificar Supabase manualmente.

Estados permitidos:
`NONE -> REQUESTED -> STOPPING -> CANCELLED`; en carrera con fin natural,
`REQUESTED/STOPPING -> COMPLETED_BEFORE_CANCEL` si el resultado terminal se cerró antes de acreditar la cancelación. `RECOVERY_BLOCKED` representa imposibilidad de acreditar cierre, no finalización. Nunca `CANCELLED` mientras el supervisor o un descendiente siga vivo.

### Ciclo del supervisor

1. Autorización de usuario, ownership, idempotencia y estado bajo transacción; **persistir solicitud antes de activar el Event**.
2. Comprobar coincidencia entre comparación almacenada, token del propietario y proceso supervisor. No actuar sobre otra comparación o un job sustituido.
3. Señalar `job.cancel.set()`. La cola no inicia nuevos motores después de la señal.
4. Conservar resultados previamente guardados. Las ejecuciones aún activas o no iniciadas reciben causa `CANCELLED` (no reemplazar resultados completos), después del cierre de stream.
5. Reutilizar `runner` + `_close` para comprobar todos los descendants, identidad y join; mientras no exista prueba de cierre, conservar lease/admisión y estado no terminal.
6. En una única transición durable coherente, marcar `CANCELLED`, registrar hora de parada y estado final de pedidos, sin confirmación de materiales.
7. Si el servicio reinicia, la intención durable se lee al recuperar. Si el owner anterior sigue vivo o su identidad es ambigua, mantener `RECOVERY_BLOCKED`; **jamás inferir muerte por timeout ni por PID reutilizado**.
8. Si la comparación ya había terminado cuando llegó la solicitud, devolver su estado real e impedir reescribir diagnósticos.

## 4. Pedido, inventario y trazabilidad

- Solicitar o repetir cancelación no ejecuta `/confirm`, no genera `movimientos`, no descuenta planchas, no crea retazos.
- El estado de pedidos solo se transiciona al cierre seguro. Los resultados parciales/terminados persisten con su fuente y unidad física.
- La política de liberación posterior de pedidos no puede ser implícita ni ambigua: debe documentar qué ocurre con órdenes parcialmente optimizadas, conservando posibilidad de consulta histórica sin confirmar cortes.
- Eventos auditables: solicitud, identidad de dueño, parada confirmada, rechazo por versión, y recuperación tras reinicio; sin registrar credenciales.

## 5. UI / usabilidad

En la barra de contexto de una comparación **v2 cancelable**, botón visible `Cancelar optimización`; confirmación con número de trabajo y explicación de consecuencias. Evitar dobles envíos; no implementar cancelación en memoria local como sustituto. Estados: `Solicitando cancelación`, `Cancelando`, `Cancelación confirmada` o `No se pudo verificar el cierre`. Tras recarga, reflejar el snapshot durable, no un indicador temporal. Lecturas históricas no dependen de máscaras visuales retenidas.

## 6. Pruebas bloqueantes (fixture sintético, PostgreSQL efímero)

| ID | Escenario / propiedad |
|---|---|
| CA-01 | Cancelar durante FF; comprobar señal, cierre de todos los hijos, cero movimientos y terminal durable |
| CA-02 | Cancelar durante HF/M5/BS-2; no iniciar motores pendientes |
| CA-03 | Cancelar entre motores, conservar los resultados completos y motivos de cancelación exactos |
| CA-04 | Carrera cancelación/finalización: un único estado terminal coherente sin sobrescribir resultados |
| CA-05 | Dos POST iguales o concurrentes: idempotencia, misma intención, sin efectos extra |
| CA-06 | Actor sin permiso, usuario distinto, trabajo equivocado: sin señal ni filtración de datos |
| CA-07 | Reinicio con solicitud persistida y workers identificados: recuperación controlada |
| CA-08 | Owner/descentientes desconocidos o vivos tras reinicio: bloquear admisión, nunca confirmar cierre |
| CA-09 | Histórico 2D/3D e inspector consultables sin datos de progreso temporal |
| CA-10 | Pruebas Playwright desktop/móvil, sin saltear escenarios ni ocultar carreras |
| CA-11 | No se genera `/confirm`, movimiento de inventario, baja de stock ni registro de retazo |
| CA-12 | Backend y frontend aceptan únicamente DTOs versionados y válidos |

## 7. Plan de implementación por PR

1. **Backend PR A**: persistencia de intención, pruebas transaccionales e idempotencia, contrato HTTP y schemas, sin exponer falsa terminalidad.
2. **Backend PR B**: integración con supervisor y cierre seguro, causal `CANCELLED`, recuperación tras reinicio y pruebas de concurrencia/descendientes.
3. **Frontend PR C** (dependiente de backend aprobado): transporte, UI de confirmación y estados, tests RTL/E2E con backend fijado a SHA probado.
4. **QA y documentación**: actualizaciones de contrato, capturas, evidencias de CI, Definition of Done y aprobación humana separada del merge.

## 8. Estado y bloqueos

**Solo SPEC de diseño. No hay endpoint implementado ni validación funcional de cancelación.** Cualquier cambio posterior debe comenzar por ejecutar pruebas con PostgreSQL de loopback y workers controlados, revisar permisos y asegurar el protocolo de persistencia. No se ha intervenido producción ni se han modificado heurísticas.

## Historial de estado

- Draft: propuesta de contrato tras inspección del supervisor real, sin aprobación de integración.
