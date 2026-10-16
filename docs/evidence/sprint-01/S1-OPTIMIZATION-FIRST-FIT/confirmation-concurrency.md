# Locking y concurrencia — PostgreSQL real local

Base f4dd5a5; prueba `test_confirmation_concurrency.py` (4 casos) y
`test_confirmation_api.py::test_two_real_http_confirmations_have_one_200_and_one_409`.
Todos verdes en focal169 y backend1976. No locks simulados ni SQLite.

Dos conexiones, ThreadPoolExecutor y barrera de inicio. El listener SQLAlchemy
solo detiene temporalmente al ganador DESPUÉS de que PostgreSQL haya adquirido
FOR UPDATE. La segunda conexión ejecuta su sentencia real y queda esperando.
Una tercera conexión observa pg_stat_activity.wait_event_type='Lock' y
pg_blocking_pids. Se comprueba que el PID bloqueador es el ganador, luego se libera
para commit. Finalmente se relee stock, ledger y TODOS los pedidos de cada corrida.
No se reemplazan consultas ni commits por mocks.
A HTTP ejecuta dos POST reales; los demás casos ejecutan ConfirmRun directamente
y registran códigos de resultado de aplicación equivalentes a200/409. La traducción
HTTP de esos conflictos está cubierta por las24 pruebas API.

| Caso | Fila que genera espera real | Resultado observado |
|---|---|---|
| A: misma optimización | optimizaciones | uno confirma, otro ALREADY_CONFIRMED409; una sola cantidad2 descontada, un movimiento |
| A HTTP | optimizaciones | dos POST reales:200/409; T1 y error seguros; consumo único |
| B: dos optimizaciones / mismo retazo | retazos | uno confirma, otro STOCK_CONFLICT409; retazo inactivo, ledger cantidad1 una vez; perdedor OPTIMIZADO |
| C: dos optimizaciones / última plancha | planchas | uno confirma, otro STOCK_CONFLICT409; cantidad final0, nunca negativa; un movimiento |
| D: actualización stock concurrente | planchas | confirmación espera commit de actualización a cantidad1; relee y rechaza409; cero movimientos y todos OPTIMIZADO |

Los archivos `confirmation-lock-*.json` contienen los PIDs, espera y query
FOR UPDATE reales y resultados de cada caso. Son datos locales sintéticos,
no credenciales. La observación es histórica, no afirma que esos procesos sigan vivos.

Reproducción desde backend:

```bash
NEWGLASS_REQUIRE_POSTGRES=1 python -m pytest tests/integration/optimization/test_confirmation_concurrency.py tests/api/optimization/test_confirmation_api.py::test_two_real_http_confirmations_have_one_200_and_one_409 -q --basetemp=/tmp/newglass-confirmation-locks
```

Los JSON nuevos quedan en /tmp/newglass-confirmation-locks/test_*/postgres-lock-proof.json.
Orden global del producto: corrida, FF, asociaciones, pedidos ASC, planchas ASC,
retazos ASC; propuestas de esa ejecución. La suficiencia de plancha se verifica
tras adquirir el lock, contando unidades físicas distintas del patrón, no piezas.
El retazo se revalida por estado y por ausencia de consumo previo incluso si fue
reactivado. No se agregan versiones, tablas, campos consumed o reservas ficticias.
CA20,21,23,24,25; confirma bajo permiso dinámico CA26.
