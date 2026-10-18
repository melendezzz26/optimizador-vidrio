# Estados multipedido / cierre del bloque backend antes de confirmación

Base publicada: `b5340ff63d11415ae1b91449c6107df8668cf292`.
El commit que contiene esta evidencia cierra la fase 5 de la sesión; en el PLAN
histórico corresponde a terminales T8 y parte de T12, NO a T10 (confirmación).
SPEC permanece Reviewed; PLAN Approved. No PR ni merge a integration.

## Fronteras atómicas

| Frontera | Corrida / ejecución FF | Todos los pedidos del lote |
|---|---|---|
| Inicio aceptado | EN_EJECUCION + asociaciones + snapshot | PENDIENTE → EN_OPTIMIZACION |
| Solución completa | COMPLETADA / COMPLETADA, completo=true, selección FF | EN_OPTIMIZACION → OPTIMIZADO |
| Finalización normal incompleta | SIN_SOLUCION / COMPLETADA, completo=false, sin selección | EN_OPTIMIZACION → PENDIENTE |
| Excepción/cancelación | FALLIDA / FALLIDA, diagnóstico, sin selección | Conserva EN_OPTIMIZACION para reconciliación explícita |

Inicio, resultado completo y SIN_SOLUCION tienen cada uno UN commit de escrituras.
Fallo se registra en transacción independiente tras rollback del cálculo/guardado.
No hay reintento automático, reset por excepción ni endpoint de reconciliación.
Un fallo al registrar FALLIDA deja estado anterior y exige revisión operacional.

## Decisiones / archivos

- `run_uow.py`: rollback explícito incluso ante fallo del propio commit; GET con
  JOIN de padre+ejecución para snapshot coherente; valida estado/completitud,
  selección FF y asociación. No recalcula ni pisa un terminal por disconnect tardío.
- `run_stream.py`, `run_routes.py`: cierre explícito del generador bajo shield en
  StreamingResponse. La prueba ASGI real encontró que cancelar durante send no
  cerraba inmediatamente el generador; queda corregido para ASGI 2.0 y 2.4.
  Cancelación cooperativa entre hitos; nunca se emiten eventos por celda.
- `run_auth.py`: solo wiring con scope=function; reutiliza lectores,
  get_current_user y require_permission reales, sin copiar lógica RBAC.
  Cierra la sesión de auth antes de headers/motor (FastAPI ya fijado en 0.141.1).
  Una prueba observa todas las sesiones de autorización cerradas y sin transacción
  al entrar al cálculo. Endpoints HU-015 y módulo RBAC no modificados.
- `backend/main.py`: CORS expone Location para lectura canónica desde navegador.
- Pruebas de estados/migración/API; expectativas HEAD/tabla actualizadas en
  fixtures Inventory y estructura DB, sin cambiar reglas de esos módulos.
- Inventario: solo lecturas. MaterialUtilizado es propuesta, no consumo. Se
  verifica cantidad/estado de planchas y retazos, cero movimientos/altas de retazo.

## Cobertura focal

Comandos desde backend con PostgreSQL local obligatorio:

```bash
NEWGLASS_REQUIRE_POSTGRES=1 python -m pytest tests/integration/optimization/test_run_states.py tests/integration/optimization/test_multipedido_migration.py tests/api/optimization/test_runs_api.py -q
NEWGLASS_REQUIRE_POSTGRES=1 python -m pytest tests/api/optimization/test_runs_api.py tests/api/authorization -q
```

Resultado observado: **45 passed, 1 warning** (estados/migración/API antes de añadir
la prueba de lifetime auth); **119 passed, 1 warning** (API/autorización, incluida
esa prueba). Se adjuntan logs. La regresión final y suite global incluyen todo.

Cubre N=1/N>1, un commit terminal, completo/SIN_SOLUCION, fallos después del flush
SQL, rollback de patrones/materiales/métricas/N estados, fallo al registrar fallo,
pedido inconsistente sin subset, terminal no recalculable, padres/ejecuciones
inconsistentes rechazados, backfill/downgrade, historia huérfana → rollback de DDL,
rotación90 con contorno ya orientado, Decimal, stock físico y retazo no consumido.

## Ejemplo HTTP/PostgreSQL real y compatibilidad UI

Artefactos generados headless, sin frontend ni capturas inventadas:

- `phase5-example-complete.ndjson`: 13 eventos reales con UTC y secuencia1..13.
- `phase5-example-complete.json`: GET canónico durable.
- `phase5-example-db.json`: head, pedidos, stock antes/después y movimientos.
- `capture_backend_example.py`: reproductor aislado, datos sintéticos, sin Supabase.
- `audit_ui_contract.mjs` / `phase5-ui-parser-audit.json`: parser original leído de
  origin/UI en un directorio temporal; frontend jamás editado.

```bash
# backend, runtime PostgreSQL configurado
python ../docs/evidence/sprint-01/S1-OPTIMIZATION-FIRST-FIT/capture_backend_example.py
# raíz repo
node docs/evidence/sprint-01/S1-OPTIMIZATION-FIRST-FIT/audit_ui_contract.mjs
```

Dos pedidos, una pieza cantidad2 de 2×2mm cada uno, plancha ID5 4×2mm cantidad2:

| Pedido | Pieza | unit_index | material_source | material_id | stock_unit_index | x_mm | y_mm |
|---|---|---|---|---|---|---|---|
| 1 | 1 | 1 | PLANCHA | 5 | 1 | 0 | 0 |
| 1 | 1 | 2 | PLANCHA | 5 | 1 | 2 | 0 |
| 2 | 2 | 1 | PLANCHA | 5 | 2 | 0 | 0 |
| 2 | 2 | 2 | PLANCHA | 5 | 2 | 2 | 0 |

Resultado COMPLETADA, 4/4; área usada16mm², piezas16mm², aprovechamiento100%,
merma0, recuperable0, 2 unidades físicas propuestas. Tiempo real en JSON; no se
exige determinismo del reloj. Stock permanece cantidad2/activo; movimientos0,
retazos nuevos0. Ambos pedidos OPTIMIZADO; confirmed=false.

UI observada `4a3c9c1cd244780f8a1d97f1a527cd1fdebcf760`: su parser aceptó los13
mensajes fragmentados en chunks7bytes y GET canónico, Decimal strings intactos.
No divergencia T1 detectada para esta captura. Pendiente conectar open/load a
POST/GET con Bearer en la rama UI; prepare sigue siendo interfaz/local, sin
endpoint adicional. Confirm permanece pendiente y NO debe conectarse todavía.

## CA / alcance / riesgos

Avanzan CA02–05,12–19,26 (view/execute),27; se conservan CA06–11 y HU-015.
CA20–25, confirm de CA26 y E2E conjunto CA28 NO se declaran terminados.
T10/T11 confirmación/concurrencia no iniciados. Sin consumo de stock, movimientos,
remanentes persistidos, reservas o locks de confirmación/inventario.

Pendientes para siguiente bloque: confirmar transaccionalmente sobre snapshot,
revalidación/locks de inventario, consumos/movimientos/retazos exactos, conflictos
409/repetición/carreras. Mínimo de área residual independiente no existe en
configuración; no se inventa y deberá coordinarse antes de creación final.
Caída proceso/DB puede dejar EN_EJECUCION: requiere reconciliación explícita según
PLAN, cuya autoridad/interfaz administrativa aún no se ha expuesto.

Ramas externas observadas: integration c4c5e5c (RBAC incorporado); UI4a3c9c1;
Orders2a5d835; RBAC4189193 ya incorporado. UI/Orders no integradas ni editadas.
Baseline E2E conocido: 20 passed/4 failed Orders HTTP422; no ejecutado/corregido
por esta sesión backend. No atribuir esos fallos a este bloque.

## Verificación final observada

```bash
# backend
NEWGLASS_REQUIRE_POSTGRES=1 python -m pytest tests/optimization tests/unit/optimization tests/api/optimization tests/integration/optimization tests/api/authorization tests/integration/test_s1_rbac_migration.py tests/integration/test_staging_bootstrap.py tests/integration/test_clients_migration.py -q
NEWGLASS_REQUIRE_POSTGRES=1 python -m pytest -q
DATABASE_URL=sqlite:// python -m alembic heads
# raíz
node docs/evidence/sprint-01/S1-OPTIMIZATION-FIRST-FIT/audit_ui_contract.mjs
git diff --cached --check
git diff --check 2cd5d0e
```

- Regresión focal final: **551 passed, 1 warning**, 53.24s.
- Backend completo final: **1900 passed, 1 warning**, 199.17s; sin skips/fallos.
- Única head Alembic: **s1opt02b4c6d**, padre **s1rbac01a2b3**.
- Warning único: deprecación conocida Starlette TestClient/httpx; no se cambian dependencias.
- Primera pasada global encontró 4 failed +57 errores de setup por expectativas
  antiguas de head/tabla en fixtures, no por comportamiento de Inventory/Orders.
  Se actualizaron esas expectativas; la pasada final incluye esas suites verdes.
- Parser UI original acepta los13 eventos reales en chunks7bytes y el GET.
- Git diff-check propio desde merge RBAC limpio. Ancestros ebd1bf8,691cdd5,
  20f9238,bfdeb74,3aca3c8 preservados. Sin cambios propios en frontend,
  Orders, Inventory o Authentication; guards reales reutilizados.

Índice de archivos propios del bloque desde la base RBAC: `phase5-changed-files.txt`.
Los logs y ejemplos son textuales reales; no se producen capturas gráficas.
