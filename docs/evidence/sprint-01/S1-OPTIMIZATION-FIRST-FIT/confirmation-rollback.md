# Rollback total — errores PostgreSQL y conflictos

Base f4dd5a5. `test_confirmation_rollback.py`:9 casos verdes.
Pruebas de SQL real con triggers temporales instalados SOLO en la BD PostgreSQL
sintética aislada. No son migraciones ni se instalan en el producto.

| Inyección/conflicto | Qué se comprueba |
|---|---|
| AFTER UPDATE planchas | rollback incluso después de que la sentencia de decremento se ejecutó |
| AFTER INSERT movimientos | revierte stock que ya fue flusheado y ledger |
| AFTER INSERT residual | revierte consumo, movimientos y toda alta de retazo |
| BEFORE completar lote (AFTER UPDATE pedido CONFIRMADO que lanza error) | revierte resultado/recibo y TODOS los pedidos, incluidos anteriores en la transacción |
| AFTER UPDATE JSONB recibo | no queda confirmed durable ni inventario consumido |
| Conflicto retazo en lote mixto | plancha válida no se consume parcialmente |
| Cantidad insuficiente en lote mixto | retazo válido no se consume parcialmente |
| AFTER UPDATE retazo a inactivo | revierte también la plancha y lote asociados |
| Colisión código residual persistido |409, conserva recurso ajeno y revierte consumo previamente flusheado |

Un snapshot completo antes/después compara pedidos, piezas, planchas, retazos,
movimientos, optimizaciones, asociaciones, ejecución/patrón, materiales propuestos
y métricas. Las secuencias PostgreSQL pueden asignar IDs sin conservar filas tras
rollback; no se exige reutilizar esos IDs. Después de quitar cada trigger se
confirma la MISMA solución original para demostrar que no quedó reserva/mutación.

API añade inyección PostgreSQL P0001→500 seguro y40001→409 seguro, ambas con
snapshot íntegro. Un error sintético después de grabar movimientos prueba también
la ruta de excepciones Application. Mensajes HTTP nunca incluyen SQL/stack.

```bash
# backend, PostgreSQL local obligatorio
NEWGLASS_REQUIRE_POSTGRES=1 python -m pytest tests/integration/optimization/test_confirmation_rollback.py tests/api/optimization/test_confirmation_api.py -q
```

Resultados incluidos en focal169 y backend1976, sin fallos/skips. Invariantes:
cantidad>=0; consumo retazo<=1; ledger nuevo con actor/run/cantidad positiva;
ningún subconjunto de un lote pasa a CONFIRMADO; simulación no muta inventario.
CA20,21,23,24,25. Min área independiente no inventado; residual solo con geometría
reproducible, límites efectivos y regla de persistibilidad Inventory vigente.
