# API de confirmación — contrato T1 sin cambios

`POST /api/optimization/runs/{id_optimizacion}/confirm`, sin body.
Guard real `optimization.confirm`; no roles hardcodeados ni exigencia implícita de
view/execute. Se valida la capacidad vigente en DB; revocación403 comprobada.
Respuesta200 ConfirmResponseV1 existente: schema_version1, id_optimizacion,
confirmed=true, orders, materials_consumed (identidades físicas sin duplicados),
remnants_created con source/origen/contorno/área. No recibe placements del cliente.

GET mantiene COMPLETADA y resultado geométrico original. Después del commit:
confirmed=true, confirmable=false. Un recibo versionado en JSONB existente y
movimientos vinculados a corrida mantienen trazabilidad sin columna nueva.
No hay evento NDJSON adicional ni cambio de schemas/fixture T1 o HU015.

| HTTP | Código T1 / caso |
|---|---|
|401|UNAUTHENTICATED, sesión ausente|
|403|FORBIDDEN, confirm no concedido/revocado|
|404|NOT_FOUND, corrida inexistente|
|409|ALREADY_CONFIRMED, segunda llamada/concurrente a misma corrida|
|409|STOCK_CONFLICT, tipo/espesor/estado/geometría/cantidad cambiados o retazo ya consumido|
|409|STATE_CONFLICT, pedidos incompatibles, código residual en conflicto o error PG de serialización/locking|
|422|NOT_CONFIRMABLE, incompleto/SIN_SOLUCION/FALLIDA/no FF seleccionado/patrón manipulado|
|422|INVALID_INPUT, path inválido o body adicional (incluso{})|
|500|INTERNAL_ERROR seguro, rollback ante error inesperado/DB|

24 pruebas API nuevas verdes: éxito+GET+historial Inventory, repetición,
401/403/404, only-confirm permitido, body rechazado, incompleto, stock/retazo409,
500 seguro, dos POST simultáneos reales, SQLSTATE PostgreSQL, validación de flags,
selección, placements, contorno, residual falsificado y material ausente.
95 pruebas de autorización API verdes incluyen el nuevo endpoint.

Captura HTTP/PostgreSQL real:
`confirmation-example-stream.ndjson` (19 eventos), before.json (confirmable),
response.json (200), after.json (confirmed), repeat.json (409), stock.json
(antes/simulación/después, movimientos con actor/opt/fecha y recibo durable).

Reproducir desde backend:

```bash
NEWGLASS_REQUIRE_POSTGRES=1 python -m pytest tests/api/optimization/test_confirmation_api.py tests/api/authorization -q
python ../docs/evidence/sprint-01/S1-OPTIMIZATION-FIRST-FIT/capture_confirmation.py
```

UI4a3c9c1 solo lectura: su parser original acepta esta confirmación,19 eventos
en chunks7bytes y ambos GET sin cambiar T1. Falta conectar adapter/transport en
su rama y probar E2E conjunto. No se modificó ni integró frontend.
