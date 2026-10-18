# TA-036 — Implementación y validación

Fecha: 12/10/2026 (America/Lima). Rama: `feature/TA-036-saneamiento-funcional`.
Base documental `f6ed987`, integración `b7a0175`. Auditoría paralela previa en [auditoria-ramas.md](auditoria-ramas.md).

## Resultado por bloque

- Inventario (`a565aa3`): baja parcial transaccional, cantidad histórica, saldo y estado automáticos, orden determinista, UI sin Activar/Desactivar e historial conservado. Se mantiene PATCH administrativo. No DELETE físico.
- Pedidos (`d5aa48b`): registro independiente de stock; orden en backend antes de paginar y filtrar. Consulta compatible paralela reservada para Optimization, sin duplicarla.
- Geometría/retazo (commit `feat(TA-036): alinear geometria y editor de retazos`): transformación uniforme de los vértices del contorno, longitudes y ángulos derivados, rechazo de medidas incompatibles con la forma y un único editor reutilizado. Reiniciar/incompletar invalida la geometría candidata de retazo. No se crea formato nuevo ni columnas de ángulos.
- Raster: inspección del código paralelo, sin incorporarlo. Ya recibe `geometria.vertices_mm`; ningún rasterizador nuevo ni algoritmo de optimización en TA-036.

## Migración y compatibilidad

Nueva revisión: `backend/alembic/versions/ta036a1b2c3d_baja_parcial.py`, padre `fa014e1a2b3c`.
`cantidad_afectada` nullable, sin default; historia de planchas y consumo de optimización sin cantidad conocida conserva NULL. Solo bajas manuales históricas de retazo se completan con 1. Restricciones: cantidad positiva si conocida, retazo unitario. Se retira únicamente el índice único manual de plancha.
Upgrade con datos preexistentes, índices/restricciones, conservación histórica, downgrade seguro en vacío, downgrade bloqueado cuando perdería cantidades y reupgrade se verifican en PostgreSQL aislado.
La respuesta de baja de plancha incluye el saldo confirmado y su estado; cantidad es obligatoria y entera estricta. El endpoint de retazo conserva el request sin cantidad y registra 1. Los clientes del POST de plancha deben enviar `cantidad_afectada`.

## Entorno de prueba

Worktree propio dentro del workspace. Python 3.11.9 y dependencias ya instaladas del entorno local; el lanzador de Microsoft Store requiere ejecución fuera del sandbox de procesos. Frontend usa dependencias locales disponibles (la instalación offline no tenía todos los paquetes en cache); no se cambian lockfiles. Se verificaron las 221 dependencias instaladas contra el lockfile, sin diferencias de versión.
`PYTHON_DOTENV_DISABLED=1`, `NEWGLASS_REQUIRE_POSTGRES=1`. Los tests crean clústeres PostgreSQL exclusivos, usuario `r1_test`, host `127.0.0.1`, puerto dinámico y bases sintéticas. Los servidores E2E usan `127.0.0.1:8017` y `127.0.0.1:5173`. Sin Supabase real, Heroku, Pages ni ejecución de Staging. El test denominado `test_staging_bootstrap.py` ensaya únicamente la cadena de migraciones y seed en base sintética local; solo se actualizan sus expectativas del head.

## Comandos y resultados observados

Desde `backend`:

| Comando | Resultado |
|---|---|
| `python -m pytest tests/unit/inventory tests/api/inventory tests/integration/inventory tests/integration/test_ta036_migration.py -q --tb=short` | 478 pasaron antes de la última regresión HTTP; incluye PostgreSQL, carreras y rollback |
| `python -m pytest tests/unit/modules/orders tests/integration/modules/orders tests/api/orders -q --tb=short` | 149 pasaron antes de agregar la regresión geométrica API |
| `python -m pytest -q --tb=short` | 1315 pasaron; 1 advertencia existente; sin errores de teardown (252,42 s), con PGCTLTIMEOUT=85 |
| `python -m alembic heads` | ta036a1b2c3d (head), único head |

Desde `frontend`:

| Comando | Resultado |
|---|---|
| `npm.cmd run test:unit` | 86 pasaron |
| `npm.cmd run test:component` | 198 pasaron en 21 archivos |
| `npm.cmd run lint` | Correcto, sin errores |
| `npm.cmd run build` | Correcto, producción local |
| `npm.cmd run test:e2e -- hu007-custom-piece.spec.js hu007-order-integration.spec.js hu014-inventory-writeoff.spec.js` | 27 pasaron; 1 omisión prevista: la baja total del fixture se ejecuta una sola vez en escritorio |
| `npm.cmd run test:e2e -- hu007-custom-piece.spec.js` | 20 pasaron en escritorio y móvil después del ajuste visual final |

Regresiones cubiertas: baja 1 de 10, baja N, exceso/0/fracción/booleano, baja total, historial con cantidad, retazo unitario, rollback y carrera que no excede saldo, prioridad y desempates, UI sin toggles, saldo confirmado incluso si falla refresco, cancelación relegada, POST sin inventario, polígonos de iguales lados y distintas formas/áreas, ángulos por vértice, finitud, degenerados, convexidad, autointersección, teclado, escala responsive y payload del editor compartido de retazo.
Las pruebas geométricas antiguas que exigían reconstrucción desde lados independientes se sustituyen por regresiones del contrato canónico. Se conservan dibujo, cierre, undo/reset y accesibilidad.
Incidencia de entorno observada: una ejecución alcanzó 1315 tests correctos pero `pg_ctl` agotó su plazo de 60 segundos durante el teardown. El log del clúster mostró un checkpoint de cierre de 72,35 segundos; se confirmó `no server running` para los tres clústeres de esa ejecución. Se repite la suite con `PGCTLTIMEOUT=85`, sin modificar fixtures, durabilidad ni servicios compartidos.

Advertencias observadas: deprecación existente de `httpx` en Starlette; avisos de color de Node/Playwright. Ningún fallo pendiente de esos avisos.

## Coordinación pendiente

SPEC permanece Draft; reviewer pendiente. HU-008 debe preservar consulta compatible fuera del POST y leer saldo positivo/estado disponible; Aguilar debe conectar geometría final persistida. No hay decisiones técnicas bloqueantes abiertas en T02–T05. Se elige escala uniforme para conservar la forma; cambiar disposición requiere corregir/redibujar el contorno.
No se realizaron checkout, merge, rebase, cherry-pick ni modificaciones de ramas paralelas. Sus tips e integración se vuelven a comprobar al cierre. Sin push.

## Archivos modificados desde el commit documental

- `backend/alembic/versions/ta036a1b2c3d_baja_parcial.py`
- `backend/app/models.py`
- `backend/app/modules/inventory/application/dto.py`
- `backend/app/modules/inventory/application/ports.py`
- `backend/app/modules/inventory/application/service.py`
- `backend/app/modules/inventory/domain/writeoff.py`
- `backend/app/modules/inventory/infrastructure/repository.py`
- `backend/app/modules/inventory/presentation/router.py`
- `backend/app/modules/inventory/presentation/schemas.py`
- `backend/app/modules/orders/application/use_cases.py`
- `backend/app/modules/orders/infrastructure/repositories.py`
- `backend/tests/api/inventory/test_inventory_api.py`
- `backend/tests/api/inventory/test_movement_history_api.py`
- `backend/tests/api/inventory/test_writeoff_api.py`
- `backend/tests/api/inventory/test_writeoff_schema.py`
- `backend/tests/api/orders/test_orders_api.py`
- `backend/tests/integration/inventory/test_repository.py`
- `backend/tests/integration/modules/orders/infrastructure/test_repositories.py`
- `backend/tests/integration/test_clients_migration.py`
- `backend/tests/integration/test_staging_bootstrap.py`
- `backend/tests/integration/test_ta036_migration.py`
- `backend/tests/unit/inventory/test_movement_history.py`
- `backend/tests/unit/inventory/test_movement_model.py`
- `backend/tests/unit/inventory/test_service.py`
- `backend/tests/unit/modules/orders/application/test_use_cases.py`
- `docs/evidence/sprint-01/TA-036/auditoria-ramas.md`
- `docs/specs/SPEC-TA-036-saneamiento-funcional.md`
- `frontend/src/features/inventory/InventoryPage.jsx`
- `frontend/src/features/inventory/MovementHistoryDialog.jsx`
- `frontend/src/features/inventory/RegistrarRetazoForm.jsx`
- `frontend/src/features/inventory/WriteoffDialog.jsx`
- `frontend/src/features/inventory/__tests__/Hu014Inventory.test.jsx`
- `frontend/src/features/inventory/__tests__/InventoryPage.test.jsx`
- `frontend/src/features/inventory/__tests__/RegistrarRetazoGeometry.test.jsx`
- `frontend/src/features/orders/CustomPieceEditor.css`
- `frontend/src/features/orders/CustomPieceEditor.jsx`
- `frontend/src/features/orders/__tests__/CustomPieceEditor.test.jsx`
- `frontend/src/features/orders/polygonMeasurements.js`
- `frontend/src/features/orders/segmentGeometry.js`
- `frontend/tests/e2e/hu007-custom-piece.spec.js`
- `frontend/tests/e2e/hu014-inventory-writeoff.spec.js`
- `frontend/tests/unit/geometryScaling.test.js`

- `docs/evidence/sprint-01/TA-036/implementacion-validacion.md`

## Controles de cierre

`git diff --check` y `git diff --cached --check`: correctos antes de cada commit. Se comprueban al terminar `git status` y los SHA de integración y ramas paralelas; el resultado final y el SHA del tercer commit se informan en la respuesta de entrega. Sin push.
