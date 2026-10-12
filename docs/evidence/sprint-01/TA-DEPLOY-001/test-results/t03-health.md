# T03 — Health checks

Fecha: 12/10/2026. Rama: `feature/TA-DEPLOY-001-staging`.
Base de tarea: `f2248e2` (T02 cerrada).

## Contrato implementado

- `/health/live`: 200 `{"status":"ok"}`, sin importar persistencia ni consultar BD.
- `/health/ready`: SELECT 1; 200 `{"status":"ready"}` o 503 `{"status":"not_ready"}`.
- `/db-test`: retirado; 404 y ausente de OpenAPI.
- Plazo HTTP de readiness: tres segundos para checkout/conexión/consulta.
  PostgreSQL además usa `statement_timeout=3000` local a la transacción;
  el rollback al devolver la conexión evita contaminar el pool.
- Se usa el engine existente y un único trabajador de diagnóstico. Si el
  driver sigue bloqueado tras vencer el plazo HTTP, conserva el permiso:
  probes posteriores devuelven 503 inmediatamente, sin acumular una cola.
  El timeout HTTP no pretende cancelar un hilo Python ni demostrar recuperación
  del driver; los timeouts de conexión/pool de T02 deben configurarse en destino.
- No se devuelve ni registra la excepción de BD, incluso si llega después
  del timeout. Las respuestas no incluyen SQL, host, usuario, URL o versión.

## Validaciones de esta sesión

Desde `backend/`, usando `venv/Scripts/python.exe` fuera del sandbox Windows:

```text
python -m pytest tests/api/test_health_api.py tests/api/inventory/test_lazy_db_import.py -q
7 passed, 1 warning in 1.88s

python -m pytest tests/api/test_health_api.py tests/api/inventory/test_lazy_db_import.py tests/integration/test_health_database.py -q
8 passed, 1 warning in 8.09s
```

La segunda ejecución incorpora la prueba real PostgreSQL local de SELECT 1,
timeout transaccional y restitución del timeout previo al devolver la conexión.
No hubo skips. Warning: deprecación Starlette/httpx de TestClient; no se alteran
dependencias para ocultarlo.

Suite completa `python -m pytest tests -q`:
**1278 passed, 1 warning in 247.00s (0:04:06)**, código 0, sin skips.
La advertencia es la misma deprecación Starlette/httpx.
`git diff --check`: código 0. Comprobación staged requerida antes del commit.

CA-05/06/07: verificación local; no smoke remoto. No se conectó a Supabase ni
se hicieron despliegues. No se crearon migraciones ni se alteraron modelos.
