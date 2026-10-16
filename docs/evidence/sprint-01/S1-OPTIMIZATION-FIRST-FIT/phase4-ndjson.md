# API / progreso NDJSON real

Base publicada `c40c29ae6cf542f8bba37287f5976a323ffe5972`.
T9 histórico del PLAN. Archivos: `presentation/run_routes.py`, `run_stream.py`,
registro en router existente; clasificación de fallo Application, método fail
Infrastructure y pruebas API/actualización del mapa RBAC de endpoints.

- POST `/api/optimization/runs`, body `{ "order_ids": [...] }`, RBAC execute.
  Preflight/transacción completa antes de headers. 201 + Location canónico.
- GET `/api/optimization/runs/{id}`, RBAC view; reconstrucción durable T1.
- StreamingResponse application/x-ndjson UTF8, newline por evento, no-cache,
  X-Accel-Buffering:no. Ocho eventos T1, sequence1..N por corrida, UTC.
- Productor consume First Fit real con callback; buffer de un evento y acuse al
  reanudar consumidor. No se calcula todo para reproducirlo después. Prueba abre
  GET/UoW al recibir piece_placed: DB aún EN_EJECUCION, antes del resultado final.
- piece_placed contiene material completo, identidad física, geometría orientada,
  Decimal string y progreso real. Grupo usa total local; pieza/terminal global.
- Fallo: CALCULATION_FAILED / RESULT_SAVE_FAILED / EXECUTION_INTERRUPTED, mensaje
  seguro sin SQL. Intento transacción independiente FALLIDA, placements diagnósticos,
  pedidos permanecen EN_OPTIMIZACION. Un disconnect tardío no pisa terminal durable.
- HU-015 start/rasterize y errores históricos conservados. No endpoint confirmación,
  ningún cambio en schemas/fixture T1, frontend, Orders o inventario.

## Pruebas

```bash
# backend con PostgreSQL local, no Supabase
python -m pytest tests/api/optimization/test_runs_api.py tests/integration/optimization/test_runs.py -q
python -m pytest tests/optimization tests/unit/optimization tests/api/optimization tests/integration/optimization tests/api/authorization tests/integration/test_s1_rbac_migration.py tests/integration/test_staging_bootstrap.py tests/integration/test_clients_migration.py -q
git diff --cached --check
```

Primera focal: **34 passed, 1 warning**. Después se agregaron 4 pruebas de
capacidades independientes, fallo de guardado y 500 seguro; todas incluidas en
regresión final **533 passed, 1 warning**. Logs adjuntos. Cubre 401/403, execute/view
independientes/revocación DB, body/IDs inválidos, conflicto config, 404, NDJSON parseable
con TypeAdapter T1, sequence, completitud, SIN_SOLUCION, métricas nullable,
multimaterial/retazo+plancha, failure parcial, guardado fallido y cancelación.

CA avanzados: 02,03,12,13,14,15,16,17,19,26 (confirmación aún pendiente).
Alembic única s1opt02b4c6d. UI observada 4a3c9c1: runTransport sigue inyectando
open/load; será necesario conectarlos a POST/GET cuando se integre conjuntamente.
No endpoint inventado de prepare/replay; GET y result_url son la recuperación.
Confirmación permanece pendiente. Inventario no mutado en los tests.
Riesgo explícito: caída DB/proceso puede dejar EN_EJECUCION; reconciliación manual
según PLAN, sin retry/reset automático. No se implementa esa operación administrativa.
