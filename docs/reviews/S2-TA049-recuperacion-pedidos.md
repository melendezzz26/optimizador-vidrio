# TA-049 — Recuperación de pedidos

Rama `fix/S2-TA049-recuperacion-pedidos`, base
`5640a58e3c386ea77e5e30e8e21a5a4113b557d1`. Árbol de código y pruebas validado,
sin este informe: `9bc4dd93976bbb9943325e6393e997a60d435b03`.
El SHA del commit local se entrega en el cierre. Sin push, merge, despliegue,
cambios en PR #102 ni acceso a Supabase compartido.

Se leyó `SPEC-TA-049-presupuesto-tiempo.md` en `6798f60` de
`feature/S2-TA049-presupuesto-tiempo` (Draft, base `3f27cd7`), sin fusionarla.
Su D-01 libera First Fit por timeout; excluye las otras fallas y contempla tres
motores. Esta solicitud amplía la recuperación a fallos controlados del motor,
desconexión y persistencia, conservando los contratos actuales de seis motores.

`SqlRunRepository.fail()` cerraba padre/ejecución pero retenía todo el lote.
Además, fallar antes de arrancar el hilo dejaba una aceptación abierta, y faltaba
un checkpoint después del motor/métricas: un vencimiento tardío podía guardarse
como `SIN_SOLUCION`. Nueve regresiones HTTP/PostgreSQL fallaron primero en la base.

La corrección recupera el lote y registra `FALLIDA` en una sola transacción nueva,
después del rollback del resultado. Bloquea padre y pedidos ordenados, refresca
la identidad ORM, verifica ausencia de consumo y exige estados coherentes.
Conserva colocaciones diagnósticas, códigos y excepciones; un aviso tardío no
sobrescribe un resultado terminal. También cubre errores de construcción y
desconexión antes de iniciar el iterador. El checkpoint final precede al SQL.

| Situación | Destino de pedidos / frontera |
|---|---|
| FF completo / confirmado | `OPTIMIZADO` / `CONFIRMADO`; conservar resultado y consumo |
| FF legítimo sin solución | `PENDIENTE`, con resultado `SIN_SOLUCION` |
| FF detenido por fallo o timeout | `PENDIENTE` junto con padre/ejecución `FALLIDA` |
| Comparación v1/v2 con algún resultado elegible | `OPTIMIZADO` al verificar parada de todos los procesos |
| Comparación sin resultado elegible | `PENDIENTE` tras cierre seguro; deadline técnico distinto de `SIN_SOLUCION` |
| Inconsistencia, consumo o commit de recuperación fallido | Sin reset parcial; revisión/reconciliación explícita |

Una caída abrupta no ejecuta `finally`. FF carece de identidad durable de proceso:
no se recupera por GET, reinicio ni TTL. El comando administrativo
`python -m scripts.recover_stopped_run ID --service-stopped` exige que el operador
verifique previamente la parada de **todos** los procesos web/calculadores.
La bandera declara esa comprobación; no demuestra un PID. Reconcilia una corrida
FF abandonada o una `FALLIDA` histórica, con locks y sin consumir stock. Rechaza
perfiles de comparación y protege lotes de ejecuciones posteriores. No se ejecutó
contra ninguna base compartida. Una indisponibilidad de BD requiere resolver la
infraestructura antes de reconciliar; no se promete recuperación durante la caída.

| Validación | Resultado |
|---|---|
| Reproducción inicial | 9 FAIL esperados sobre la base |
| Bloque ampliado HTTP/integración | 53 PASS, incluidas las nuevas regresiones |
| Backend completo y cuatro procesos aislados del CI | 3226 PASS; 0 fallos, 0 skips (3152 + 8 + 26 + 26 + 14) |
| Frontend unidad / componentes (2 workers) | 213 / 589 PASS |
| Frontend lint / build | PASS; aviso existente de chunk >500 kB |
| E2E global de dos fases, gate TA-040 | 146/146 PASS (2 + 144); 73 escritorio y 73 móvil; 0 skips/retries/flaky |

Pruebas nuevas: `test_run_recovery.py` en API e integración y
`test_comparison_recovery.py`; cubren rollback tras SQL, fallo de la recuperación,
salida abrupta real, concurrencia, idempotencia, confirmación y deadlines v1/v2.
Se actualizaron expectativas antiguas y el aviso frontend sin modificar selección.
Motores, presupuestos, esquema/migraciones y correcciones TA-045, B08 y TA-047
permanecen intactos.

Archivos de producción: `application/{calculation,run_ports,run_recovery}.py`,
`infrastructure/run_uow.py`, `presentation/{run_routes,run_stream}.py` dentro de
Optimization, y `scripts/recover_stopped_run.py`. Pruebas actualizadas:
`api/optimization/{test_runs_api,test_run_geometry_api}.py`,
`integration/optimization/test_run_states.py` y
`frontend/src/features/optimization/{optimizationModel.js,__tests__/LoadControlFeedback.test.jsx}`.
Las 26 regresiones nuevas están incluidas en el total backend; no se suman
otra vez los bloques focalizados.

Entornos reutilizados: Python 3.11.9, Node 22.23.2 y PostgreSQL 18.6 temporal exclusivo
en loopback, con dotenv deshabilitado y PostgreSQL obligatorio. La primera suite
completa sobre la carpeta montada agotó dos esperas del harness v2 de 25 s y se
interrumpió; no cuenta como PASS. Se reutilizó la copia Linux temporal existente,
verificando hashes de 2088 archivos; los 28 casos de comparación/preflight pasaron
sin cambiar límites, retries o código. Artefactos fuera de Git; ningún clon ni
worktree nuevo. Dependencias coincidentes con requirements/lockfile. Salidas y
manifiestos temporales en `/home/fabri/.cache/ta049` (WSL); datos PostgreSQL
detenidos y eliminados, sin versionar artefactos.

El protocolo `node scripts/run-e2e-phases.js`, UUID
`a4ab0b1e-c5b7-47c9-85c4-c6a762318807`, validó IDs exactos contra su plan,
sin duplicados ni excepciones aprobadas. Sus reportes conservan el HEAD base
anterior al commit; el contenido probado corresponde al árbol indicado arriba.
Backend usó los comandos del CI con las cuatro suites en procesos separados
y `-x -q -ra --tb=short`. Las comprobaciones de hashes antes/después no detectaron
cambios de fuentes. `recovery/sprint-02` está limpio en la base y permite
fast-forward local al commit de esta rama; no se ejecutó esa integración.

## Seguimiento en staging, PR #109

En la versión v26 (`41a92008`), el dyno web Basic respondió y el historial de
NewGlass mostró doce pedidos en optimización. La comparación #84 abrió sus seis
resultados. La #85 figuró finalizada sin vínculos de pedido y su GET devolvió
500 de trazabilidad. Ese estado terminal no participa en la recuperación de
trabajos en ejecución. La actividad del dyno por sí sola no identifica al
supervisor ni a sus procesos hijos.

Una solicitud nueva vuelve a intentar el cierre local o la recuperación
pendiente antes de reservar admisión. Un rechazo verificado antes de aceptar
el pedido permite cambiar de selección en el navegador. Una respuesta ambigua
conserva la clave de idempotencia y el lote original.

La recuperación al iniciar consulta comparaciones. Las corridas FF autónomas
siguen su procedimiento administrativo. Para v2, el resultado terminal
persistido por el runner después de verificar la parada del proceso y sus
descendientes acredita el cierre de ese worker. La recuperación exige además
que el supervisor previo y los workers identificados ya no estén activos.
Una intención de lanzamiento sin identidad o una ejecución sin prueba de
parada conserva la reserva.

Para diagnosticar pedidos históricos, ejecutar primero `python -m
scripts.reconcile_stuck_orders --report -` desde `backend` con acceso autorizado.
Revisar cada vínculo y el consumo antes de aplicar el plan. Para #85, contrastar
el lote congelado y las filas de `optimizacion_pedidos` con el registro original.
El API registra el ID y la validación fallida para facilitar ese diagnóstico.
