# Confirmación real First Fit — backend

Base: `f4dd5a5fcd574037e055873d75bafcf15cdbf771`, rama única de escritura
`feature/S1-optimization-core`. SPEC Reviewed / PLAN Approved, sin cambiar estados
documentales. Objetivo: T10 y T11 backend, antes de integración conjunta UI.
Auditoría previa: [confirmation-audit.md](confirmation-audit.md).

## Implementación

- Domain `confirmation.py`: agrupa consumo por fuente/ID contando unidades
  físicas distintas; prueba geometría orientada, ángulos, raster/layout y
  residual mediante funciones existentes. No ejecuta First Fit ni busca alternativas.
- Application `confirmation.py`, `run_ports.py`: ConfirmRun y puertos caller-owned.
  Valida completo/selección/estado, coordina locks, revalidación, consumos,
  movimientos, residuales, recibo durable y TODOS los pedidos CONFIRMADO.
- Infrastructure `confirmation_adapter.py`, `run_uow.py`: una sesión PostgreSQL,
  un commit. No invoca servicios/repositorios Inventory con commit propio.
- Presentation `run_routes.py`, `confirmation_serialization.py`: POST por ID
  sin body, ConfirmResponseV1 existente y guard dinámico optimization.confirm.
  T1 schemas/fixture/mapeo de resultado conservados; HU015 sin cambios de contrato.

## Decisiones técnicas respaldadas por SPEC/PLAN

1. No migración: stock, estado, ledger con FK a run/actor, cantidad y origen de
   retazo ya existen. Única head sigue `s1opt02b4c6d`.
2. La corrida conserva COMPLETADA. Recibo versionado de confirmación en el JSONB
   existente permite GET confirmed=true/confirmable=false. No columna/estado nuevo.
3. Segunda llamada: 409 ALREADY_CONFIRMED según PLAN §12/T1. También se verifica
   ledger por optimización, incluso si un recibo fue alterado externamente.
4. Locks: corrida→FF→asociaciones→pedidos ASC→planchas ASC→retazos ASC;
   propuestas bajo lock de su ejecución. No locks de stock que no se usa.
5. Plancha: cantidad -= número de stock_unit_index distintos usados; estado
   false al llegar a0, como Inventory vigente. Los índices son identidades dentro
   del snapshot de simulación, no números de serie globales que el modelo no posee.
   Se valida cantidad actual suficiente; no se exige que sea idéntica a la pasada.
6. Retazo: estado=false una vez y movimiento cantidad1. Bajo el lock se consulta
   también CONSUMO_OPTIMIZACION histórico, evitando reconsumo por reactivación.
   No se cambia la regla funcional general de edición Inventory.
7. Se compara material/espesor, estado, dimensiones/geometría y área con snapshot;
   cualquier incompatibilidad/insuficiencia produce409, sin sustitución ni FF.
8. Un movimiento por recurso agregado: CONSUMO_OPTIMIZACION, id_optimizacion,
   id_usuario, cantidad_afectada, fecha UTC, motivo y observación con índices.
9. Códigos de residuales estables `FF-{run}-{P|R}{material}-{stock_unit_index}`,
   dentro de VARCHAR40; colisión conocida→409 con rollback, nunca overwrite.
10. Errores PG40001/40P01/55P03→409 seguro; otros DBAPI→500 seguro, tras rollback.

## Residuales: reutilización conservadora, sin inventar política

Se reproduce EXACTAMENTE el algoritmo existente de rectángulo máximo de celdas
interiores libres, con margen/separación y revalidación geométrica. La propuesta
persistida debe coincidir. No es la AABB de un hueco ni aproximación del material
irregular; el rectángulo es una región exacta contenida en el raster libre.
Se comprueba además que placement.geometria coincide con la orientación original:
no se acepta una figura persistida encogida, solapada o fuera de la rejilla.

Se usan ancho/alto mínimos de la configuración EFECTIVA congelada en el run,
no defaults ni una configuración modificada después. Se reutiliza el validador
Inventory: geometría numérica canónica, área HALF_UP a0.01 y rango NUMERIC18,2.
La conversión Decimal→geometría heredada debe conservar dígitos.
Un residual no persistible se omite, se guarda razón técnica en el recibo y se
ajustan recuperable/merma a las regiones realmente materializadas (0 si ninguna).
No se registra área ficticia. Eso no es un mínimo de área configurable nuevo.

**Pendiente explícito:** no existe definición aprobada de mínimo INDEPENDIENTE
DE ÁREA residual. No se agrega campo ni valor inferido; esta sesión usa los mínimos
ancho/alto existentes según autorización expresa. El resto libre queda merma.

## Verificación exacta

PostgreSQL local aislado (`r1_test@127.0.0.1`, NEWGLASS_REQUIRE_POSTGRES=1).
No Supabase, datos reales de negocio ni frontend.

```bash
# backend; runtime PostgreSQL de Cloud configurado
NEWGLASS_REQUIRE_POSTGRES=1 python -m pytest tests/unit/optimization/test_confirmation.py tests/integration/optimization/test_confirmation.py tests/integration/optimization/test_confirmation_concurrency.py tests/integration/optimization/test_confirmation_rollback.py tests/api/optimization/test_confirmation_api.py tests/api/authorization -q --basetemp=/workspace/.setup/confirmation-final-proof-verified
NEWGLASS_REQUIRE_POSTGRES=1 python -m pytest -q --junitxml=/workspace/.setup/confirmation-backend-full.xml
DATABASE_URL=sqlite:// python -m alembic heads
```

Focal final: **169 passed, 1 warning**, 14.02s.
Backend completo: **1976 passed, 1 warning**, 208.58s, sin fallos/errors/skips.
Warning conocido Starlette TestClient/httpx; sin cambios de dependencias.

Conteos derivados del JUnit de esa ejecución, subconjuntos de los1976 (no sumar
otra vez): Optimization516; Inventory497; Orders150; autorización API95;
HU015 API41 + concurrencia histórica de inicio7. Nuevas suites: unit13,
PostgreSQL funcional24, carreras4, rollback9, API24; mapa RBAC agrega2 casos.
[Resumen](confirmation-test-summary.json), [log focal](confirmation-focused.log),
[log completo](confirmation-backend-full.log).

- [Locking / carreras reales](confirmation-concurrency.md).
- [Rollback / triggers PostgreSQL](confirmation-rollback.md).
- [Contrato API / ejemplo HTTP real](confirmation-api.md).

## Ejemplo real y compatibilidad UI observada

[Captura reproducible](capture_confirmation.py) crea dos pedidos, seis unidades,
dos materiales; produce19 eventos NDJSON reales, GET previo, POST confirm,
GET posterior y repetición409. Stock:

| Recurso | Antes/simulación | Después de confirmar |
|---|---|---|
| PLANCHA5, 6×2mm | cantidad4, activa | cantidad2, activa; dos unidades físicas consumidas |
| RETAZO9, 4×2mm | activo | inactivo; consumido una sola vez para dos placements |
| Nuevo RETAZO1 | inexistente | activo, 4×2mm,8mm², origen ejecuciónFF1 |
| Pedidos1,2 | PENDIENTE→OPTIMIZADO | ambos CONFIRMADO |
| Movimientos | 0 | dos: plancha cantidad2, retazo cantidad1, actor/run/fecha |

Nuevo residual proviene de PLANCHA5 unidad2, x2/y0. Configuración margin0,
separation0, resolution1, step90, mínimos ancho/alto1. Área material32mm²,
piezas24mm², recuperable8mm², merma0, aprovechamiento75%.
La simulación conserva el inventario intacto. Repetición409 no cambia una fila.
Datos exactos: `confirmation-example-{before,response,after,repeat,stock}.json`
y `confirmation-example-stream.ndjson`, sin tokens/credenciales.

```bash
# backend
python ../docs/evidence/sprint-01/S1-OPTIMIZATION-FIRST-FIT/capture_confirmation.py
# raíz
node docs/evidence/sprint-01/S1-OPTIMIZATION-FIRST-FIT/audit_confirmation_ui.mjs
```

UI observada `4a3c9c1cd244780f8a1d97f1a527cd1fdebcf760`, solo lectura.
Su parser ORIGINAL acepta19 eventos fragmentados en chunks7bytes, confirmación con
3 identidades físicas y1 residual, y GET posterior confirmed=true/confirmable=false.
[Resultado real](confirmation-ui-parser-audit.json). No merge ni cambios frontend.
Queda conectar sus operaciones open/load/confirm y hacer integración/E2E conjunta.

## CA y pendientes

Avanzan CA20–25 y confirmación de CA26; CA15/simulación, HU015 y RBAC preservados.
CA22 respaldado por geometría real/creación validada, con pendiente área independiente
explícito. CA28 tiene recorrido HTTP backend real; E2E visual conjunto pendiente.
No SPEC Verified ni cierre global T13.

T10/T11 backend terminados. Reconciliación administrativa de corridas abandonadas
(T12), política independiente de área mínima y revisión/integración UI siguen
pendientes; no se expone ni se hace auto-reset de corridas FALLIDA.
Sin bloqueo de atomicidad/locking en este bloque. No PR, no merge a integration,
no push a ramas ajenas. Archivos propios: `confirmation-changed-files.txt`.
