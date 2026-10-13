# TA-036 — T06: regresión transversal final

Fecha: 13/10/2026, America/Lima. Worktree existente:
`C:\Users\fabri\Documents\TALLER INTEGRADOR I\TA036-saneamiento-worktree`.
Rama `feature/TA-036-saneamiento-funcional`; inicio limpio.
SHA de implementación probado: `0e67631896ac37e7ef043247f1b20656a3b83689`.
Base de comparación: `origin/integration/sprint-01` =
`b7a0175522f5506c11a7782c3a4f8433dd61b4a6`.

Este cierre modifica solamente documentación. La SPEC conserva **Draft** y
**Reviewer pendiente**. La revisión formal decidirá Reviewed/Implemented;
no se marca Verified ni se asigna reviewer automáticamente.

## Ejecución reproducible

Dependencias locales existentes, sin instalaciones ni cambios de lockfile.
Python 3.11.9 del venv backend instalado. Desde `backend`, en PowerShell:

```powershell
$env:PYTHON_DOTENV_DISABLED='1'
$env:NEWGLASS_REQUIRE_POSTGRES='1'
$env:PGCTLTIMEOUT='85'
& '../../optimizador-vidrio/backend/venv/Scripts/python.exe' -m alembic heads
& '../../optimizador-vidrio/backend/venv/Scripts/python.exe' -m pytest -q --tb=short
```

La ruta externa al worktree corresponde únicamente al intérprete instalado;
el código y cwd probados son los de TA036-saneamiento-worktree. Las fixtures
crean clústeres PostgreSQL propios en loopback y bases sintéticas; dotenv está
deshabilitado. No se usa Supabase ni una DATABASE_URL compartida. El test
llamado `test_staging_bootstrap.py` prueba migraciones/seed locales; no ejecuta
Staging ni despliega.

Desde `frontend`, los mismos comandos de validación anteriores:

```powershell
npm.cmd run test:unit
npm.cmd run test:component
npm.cmd run lint
npm.cmd run build
```

E2E completo, sin filtro de archivos, grep ni proyecto:

```powershell
$env:PATH=(Resolve-Path '../../optimizador-vidrio/backend/venv/Scripts').Path + ';' + $env:PATH
$env:PYTHON_DOTENV_DISABLED='1'
$env:NEWGLASS_REQUIRE_POSTGRES='1'
$env:PGCTLTIMEOUT='85'
$env:PLAYWRIGHT_JSON_OUTPUT_NAME='../t06-e2e.json'
python --version
npm.cmd run test:e2e -- --list
npm.cmd run test:e2e -- --reporter=list,json
```

El reporter JSON se utilizó para extraer duración, estados, proyectos y
anotaciones exactos; no modifica el descubrimiento ni los tests. El reporte
transitorio no se versiona. El servidor E2E crea su propia base, usuarios y
JWT sintéticos, en `127.0.0.1:8017`; Vite usa `127.0.0.1:5173`. Teardown terminó
correctamente y el archivo temporal de estado E2E ya no existe.

| Validación | Resultado observado |
| --- | --- |
| Alembic heads | Un único head: `ta036a1b2c3d` |
| Parent | `fa014e1a2b3c`, confirmado en revisión y cadena probada |
| Backend completo | 1330 passed; 0 failed; 0 skipped; 1 warning existente; 322,49 s |
| Frontend unit completo | 103 passed; 0 failed; 0 skipped; 146,0048 ms |
| Frontend component completo | 211 passed en 21 archivos; 21,47 s |
| Lint | OK, exit 0 |
| Build local | OK, exit 0; 947 ms |
| E2E completo | 32 descubiertos; 31 passed; 0 failed; 1 skipped; 0 flaky |

Los conteos frontend coinciden exactamente con el correctivo. No hubo cambios
de configuración, scripts, include/exclude ni omisiones unit/component.
El warning backend es la deprecación existente de httpx con Starlette
TestClient; no hubo fallos de tests ni de teardown. Las migraciones y sus
CHECK se ejecutaron en PostgreSQL aislado dentro de la suite completa.

## E2E y omisión explícita

Inicio: `2026-10-13T05:07:41.419Z` (00:07:41,419 America/Lima).
Duración exacta de `stats.duration`: **43425,486 ms** (**43,425486 s**).
Runner Playwright, motor Chromium, canal **Chrome estable local**. Dos
proyectos sobre ese navegador: escritorio 1440×900 y móvil emulado 390×844
con touch. No equivale a validar Firefox, WebKit o un dispositivo físico.
Dos workers, retries=0; sin errores globales del runner.

| Proyecto | Descubiertos | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: | ---: |
| chromium-desktop | 16 | 16 | 0 | 0 |
| chromium-mobile | 16 | 15 | 0 | 1 |
| Total | 32 | 31 | 0 | 1 |

| Archivo | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: |
| hu007-custom-piece.spec.js | 20 | 0 | 0 |
| hu007-order-integration.spec.js | 4 | 0 | 0 |
| hu012-client-order.spec.js | 4 | 0 | 0 |
| hu014-inventory-writeoff.spec.js | 3 | 0 | 1 |

Único skip: `HU-014: Almacenero registra una baja y consulta el movimiento
persistido`, `chromium-mobile`, `hu014-inventory-writeoff.spec.js:18`.
Razón exacta: **“La mutación agota un recurso compartido entre viewports.”**
El fixture plancha #701 tiene dos unidades; la prueba de escritorio agota
ambas y registra el movimiento. El segundo viewport omite esa misma mutación.
Es el caso ya documentado en implementación/correctivo, sin cambio en T06.
Se contabiliza como omisión, no como éxito; el flujo móvil de baja completa
no queda validado por E2E. Sí se ejecuta el caso móvil de permisos/consulta.

## Matriz de criterios de aceptación

Rutas de las pruebas abreviadas en la tabla:

- `INV-PG`: `backend/tests/integration/inventory/test_repository.py`.
- `INV-UNIT`: `backend/tests/unit/inventory/test_service.py`.
- `ORD-API`: `backend/tests/api/orders/test_orders_api.py`.
- `ORD-PG`: `backend/tests/integration/modules/orders/infrastructure/test_repositories.py`.
- `GEO-UNIT`: `frontend/tests/unit/geometryScaling.test.js`.
- `EDITOR`: `frontend/src/features/orders/__tests__/CustomPieceEditor.test.jsx`.
- `INV-UI`: `frontend/src/features/inventory/__tests__/InventoryPage.test.jsx`.
- `HU014-UI`: `frontend/src/features/inventory/__tests__/Hu014Inventory.test.jsx`.
- `RETAZO-UI`: `frontend/src/features/inventory/__tests__/RegistrarRetazoGeometry.test.jsx`.

| CA | Resultado | Evidencia | Test | Observación |
| --- | --- | --- | --- | --- |
| CA-01 | PASS | POST/GET conserva vértices de cuadrado y rombo de iguales lados; revisión de rutas de guardado | ORD-API `test_same_edge_lengths_preserve_distinct_canonical_polygons_in_order`; GEO-UNIT `equal lengths cannot determine shape`; RETAZO-UI payload | No existe rasterizador en TA-036. Se audita en lectura el consumidor paralelo de vertices_mm; no se afirma haberlo ejecutado. |
| CA-02 | PASS | Escala uniforme preserva forma/ángulos, cierre, rechazo de concavidad/cruce y degenerados | GEO-UNIT; `convexityValidation.test.js`; EDITOR; E2E hu007-custom-piece (20 passed) | Incluye preview extremo, medidas pequeñas, teclado, sincronización visual y limpieza del estado. |
| CA-03 | PASS | Plancha 10→8 por baja 2 vía HTTP real, movimiento 2; fila disponible conservada | INV-PG `test_real_writeoff_http_routes_never_persist_null_quantity` | También 10→9 y 10→6 en pruebas parametrizadas de servicio y PostgreSQL. |
| CA-04 | PASS | Baja exacta deja 0/false; fallos revierten saldo y movimiento, carreras no exceden saldo | INV-PG `test_partial_writeoff_postgres_balance_history_and_order`, `test_writeoff_failures_roll_back_both_rows`, `test_concurrent_partial_writeoffs_do_not_overspend_balance` | Incluye fallos de persistencia/commit y cantidad inválida. |
| CA-05 | PASS | Retazo registra 1, estado false, fila e historial conservados | INV-PG `test_writeoff_persists_movement_and_deactivates_resource_atomically`, `test_partial_writeoff_postgres_balance_history_and_order`; HU014-UI baja retazo | No DELETE físico. |
| CA-06 | PASS | Solo Historial/Editar/Dar de baja en UI; PATCH administrativo conservado | INV-UI `solo ofrece historial, edición y baja, sin toggles de estado`; INV-PG `test_legacy_inactive_resource_without_writeoff_can_be_reactivated` | APIs internas legítimas de estado no se eliminaron; reactivación tras baja sigue protegida. |
| CA-07 | PASS | Disponibles y saldo positivo primero, fecha/ID DESC; retazo dado de baja al final con historial accesible | INV-PG `test_plancha_order_is_available_then_date_and_id_desc`, `test_partial_writeoff_postgres_balance_history_and_order`; HU014-UI `retazo no solicita cantidad editable y queda detrás del disponible tras baja` | Filtros administrativos conservados, sin nueva paginación. |
| CA-08 | PASS | Dos pedidos creados con tablas Plancha/Retazo vacías; catálogo sigue validado; revisión productiva sin consulta de stock | ORD-API `test_register_order_without_inventory_and_cancel_moves_it_to_end`; orders unit `test_create_order_never_queries_stock_compatibility`, `test_create_order_invalid_catalog` | La prueba API usa persistencia real; la prueba unitaria de llamadas complementa, no reemplaza esa evidencia. |
| CA-09 | PARTIAL | HU-008 conserva puerto/DTO/servicio útil en ref 46d801e; POST TA-036 desacoplado | Auditoría `git show` de puerto, repositorio y StockCompatibilityValidator; CA-08 | Consumo desde Optimization diferido a integración de HU-008. No implementado ni probado en esta rama. Alcance pendiente explícito, sin copiar trabajo ajeno. |
| CA-10 | PASS | RegistrarRetazoForm importa y renderiza CustomPieceEditor, transmite geometria.type/vertices_mm | RETAZO-UI: los tres casos de reutilización/payload, invalidación tras reset y carga de edición | No hay segundo editor poligonal independiente. Validación geométrica compartida. |
| CA-11 | PASS | Orden backend no CANCELADO/CANCELADO, fecha DESC, ID DESC antes de paginar; filtros conservados | ORD-PG `test_list_orders_prioritizes_non_cancelled_with_stable_date_id_order` para cuatro estados; ORD-API cancelar→final | Prueba empates, paginación y filtro de cancelados/no cancelados. |
| CA-12 | PASS | Histórico de plancha desconocido NULL, retazo manual 1; upgrade preserva filas y CHECK; downgrade seguro/bloqueado | `backend/tests/integration/test_ta036_migration.py`: ambos tests; INV-PG historial | No default ficticio, no cambios en revisiones históricas, no stamp. |
| CA-13 | PASS | SHA, comandos, resultados y límites de ejecución consignados en este documento y el índice | Revisión de diff, artefactos, rutas y patrones de credenciales; resultados de suites de T06 | Logs/reportes transitorios fuera del commit; solo documentación en cierre. |

CA-09 queda PARTIAL por el consumo futuro expresamente reservado a Optimization
y a la rama paralela. No se convierte en PASS por inferencia ni se integra ese
trabajo para cerrar TA-036. La revisión humana debe mantener visible este
alcance pendiente. No hay CA marcado FAIL.

## Verificaciones funcionales e invariantes

**Inventario:** INV-UNIT e INV-PG parametrizan bajas 1/4/10 sobre saldo 10:
9/6/0 y estado true/true/false, con cantidad histórica exacta. El caso HTTP
real comprueba adicionalmente baja 2→saldo 8. Cantidades 0, negativas, superiores
al stock, fraccionarias, booleanas y NULL se rechazan sin nuevas filas ni
alteración del saldo. Movimiento y saldo se confirman/revierten juntos.
Retazo siempre registra 1 y conserva fila/historial. Componentes comprueban
saldo confirmado incluso si falla refresh, ausencia de toggles y acciones
restantes según permisos; backend define orden operacional determinista.

**cantidad_afectada:** histórico desconocido puede ser NULL. Request de plancha
exige entero estricto >0; retazo no admite campo editable. BajaManual valida
cantidades explícitas y permite omisión para retazo; servicio exige cantidad
positiva/saldo suficiente para plancha y asignación unitaria para retazo.
Escritor común del repositorio rechaza NULL, no enteros, <=0 y retazo !=1.
Las rutas API/servicio/repositorio reales se prueban en PostgreSQL aislado.
Los DTO/ORM de lectura mantienen nullable para el historial.

**PostgreSQL permite NULL directo por compatibilidad histórica.** El esquema
no distingue temporalmente inserciones nuevas de antiguas; esto no es defecto
bajo el contrato vigente, que protege nuevas bajas de aplicación. CHECK
`cantidad_afectada IS NULL OR cantidad_afectada > 0` impide cantidades conocidas
no positivas; el CHECK de retazo limita las conocidas a 1. No se agregan
triggers ni se rediseña la migración `ta036a1b2c3d`.

**Pedidos:** inspección de CreateOrderUseCase y dependencias confirma que solo
se validan contratos propios, cliente, catálogo y piezas antes de persistir.
La prueba HTTP con BD vacía no simula stock; el spy unitario confirma ausencia
de consulta compatible. La futura consulta queda en HU-008/Optimization. El
listado comparte contrato backend de estado/fecha/ID y conserva filtros.

**Geometría y retazo:** vertices_mm conserva la disposición ordenada; lados y
ángulos son derivados. Cambiar una medida reescala uniformemente la figura,
no resuelve una forma desde lados independientes. Los tests comprueban extremos
200:5000 y 5000:200, tamaños de preview/padding inválidos, escala positiva
menor que 0.01, valores no finitos, degenerados, cierre/convexidad/cruce,
selección línea/etiqueta de ambos SVG, teclado y reset/undo. Los pequeños valores
válidos se prueban en la UI y funciones puras dentro de sus tolerancias; no
se afirma que todos los valores arbitrariamente pequeños sean persistibles.
RegistrarRetazoForm reutiliza el editor y envía el formato existente
`geometria = {type: POLIGONO_CONVEXO, vertices_mm}`; backend deriva el área.

## Ramas paralelas y riesgos residuales

| Rama | Archivos solapados | Contrato afectado | Riesgo de conflicto | Acción posterior |
| --- | --- | --- | --- | --- |
| origin/feature/HU-008-stock-compatible | backend/app/modules/inventory/application/ports.py; backend/app/modules/inventory/infrastructure/repository.py | Baja parcial, cantidad positiva y consulta compatible desacoplada de POST | Medio textual/funcional por puerto y repositorio compartidos | Conservar consulta y validación de cantidades; probar saldo positivo después de baja; preparar consumo desde Optimization. |
| origin/feature/TA-005-TA-006-rasterizacion | Ninguno | Geometría final vertices_mm de pedidos/retazos | Bajo textual; medio funcional al conectar consumidores | Conservar algoritmo estándar/personalizado de Aguilar y pasar geometría persistida; no inferir forma desde lados. |

[Auditoría e instrucciones posteriores para ambos equipos](auditoria-ramas.md)
incluyen los comandos checkout/fetch/merge solicitados, para después del merge
de TA-036. Ninguno se ejecutó durante T06. Se inspeccionaron refs locales
46d801e y 5c58321; no se afirma que sean los últimos tips del servidor remoto.

Riesgos/límites abiertos: revisión humana pendiente; CA-09 PARTIAL; una baja
móvil E2E omitida; compatibilidad futura con ramas paralelas pendiente de sus
integraciones; downgrade con historia cuantificada intencionalmente bloqueado
para evitar pérdida de información. No se validaron servicios desplegados.

## Revisión Git y commits

Se revisó `git diff --name-status origin/integration/sprint-01...HEAD` y el diff
de implementación. No hay .env, secretos/credenciales reales detectados,
temporales ni artefactos locales en los cambios versionados. Los valores de
prueba son sintéticos. No hay cambios en infraestructura desplegada, workflows,
Supabase, Heroku o Pages. Los archivos bajo `modules/*/infrastructure` son
repositorios de aplicación, no configuración de despliegue. Las modificaciones
de tests de bootstrap/clientes solo actualizan expectativas del head Alembic.

Commits de implementación/evidencia previos al cierre:

- `f6ed987 docs(TA-036): definir saneamiento funcional`
- `a565aa3 feat(TA-036): implementar baja parcial de inventario`
- `d5aa48b fix(TA-036): alinear pedidos y validacion de stock`
- `58911a6 feat(TA-036): alinear geometria y editor de retazos`
- `0e67631 fix(TA-036): restaurar invariantes y cobertura funcional`

El commit de cierre tiene título `docs(TA-036): cerrar evidencia de saneamiento
funcional` y contiene únicamente README de evidencia, este resultado final,
actualización de auditoría e historial de SPEC. Su SHA se identifica con
`git log -1` tras crearlo; no se intenta insertar el hash del commit dentro de
su propio contenido. El SHA probado de producción permanece 0e67631.

`git diff --check`, revisión del estado y `git diff --cached --check` se
ejecutan antes del commit documental. No se incluyen logs, JSON transitorio,
artefactos de build o reportes Playwright. Ningún archivo de producción cambió
durante T06. El estado final se verifica limpio tras el commit.

Conclusión técnica: **READY FOR HUMAN REVIEW**. T06 ejecutado con cero fallos;
CA-09 PARTIAL y el skip móvil quedan explícitos para revisión. No se hizo
push, PR, merge, rebase ni deploy. La SPEC continúa Draft.

## Inventario de archivos de TA-036 contra integraci?n

47 archivos, incluidos los documentos de este cierre. El commit final solo modifica cuatro documentos.

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
- `backend/tests/unit/inventory/test_writeoff.py`
- `backend/tests/unit/modules/orders/application/test_use_cases.py`
- `docs/evidence/sprint-01/TA-036/README.md`
- `docs/evidence/sprint-01/TA-036/auditoria-ramas.md`
- `docs/evidence/sprint-01/TA-036/correctivo-regresion.md`
- `docs/evidence/sprint-01/TA-036/implementacion-validacion.md`
- `docs/evidence/sprint-01/TA-036/t06-regresion-final.md`
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
