# HU-008 — evidencia de implementación

## Alcance y punto de partida

Rama `feature/HU-008-stock-compatible`, basada en `origin/integration/sprint-01`
(`b7a0175522f5506c11a7782c3a4f8433dd61b4a6`). La auditoría inicial reportó
T01, SP-005 T01, T02 y T03 parciales; T04 no implementado (~30 %). La rama
estaba 5 commits por delante de integration y alineada con su remoto.

Se preservaron los cinco commits de Luis Anthony Ibañez Herrera, sin reescritura:

- `24484a4` — SPEC HU-008.
- `8ea8acd` — validador geométrico de dominio.
- `0241365` — puerto de Inventory.
- `ccfa6a6` — consulta de stock compatible.
- `46d801e` — cálculo AABB y rotación ortogonal.

## Decisiones y resultado

- **T01 — implementada:** Inventory consulta por pareja exacta de tipo y espesor; solo incluye planchas activas con cantidad positiva y retazos activos. La lectura no modifica el inventario.
- **SP-005 T01 — formalizada:** candidato individual mediante cajas envolventes alineadas y rotación de 90°. El ID tiene una colisión histórica documentada; la referencia en SPEC-TA-013 no se sobrescribió.
- **T02 — implementada:** servicio de Inventory verifica dimensiones de planchas, ajuste exacto, giro y rechazo por falta de cabida.
- **T03 — implementada:** verifica retazos rectangulares, circulares y poligonales convexos a partir de su geometría persistida. Para siluetas curvas o poligonales, la AABB es una preselección y no prueba contención exacta.
- **T04 — implementada:** el POST de Orders comprueba todas las piezas antes de persistir. Un fallo devuelve 422 con código, índice base 1 y motivo; no persiste pedido ni piezas. El formulario conserva cliente y piezas, marca cada pieza indicada y permite corregir y reintentar. PUT de pedidos históricos queda fuera del chequeo.
- Cada pieza necesita un candidato por separado. No se calcula factibilidad conjunta ni se reserva, consume o descuenta stock. La disponibilidad HU-014 se determina por `estado` y, para planchas, `cantidad > 0`; no se consulta otra vez movimientos porque la baja manual fija `estado = false` en la misma transacción.
- No se añadió migración ni cambio de esquema. SPEC: `Implemented`, pendiente de revisión independiente; no `Verified`.

## Ejecuciones reproducibles

Backend: desde `backend`, configurar el PostgreSQL temporal local indicado por el proyecto:

```powershell
$env:NEWGLASS_TEST_PG_BIN='C:/Users/Andro/.cache/tooling/hu007-postgres/server/pgsql/bin'
$env:NEWGLASS_REQUIRE_POSTGRES='1'
```

| Alcance | Comando | Resultado |
|---|---|---|
| Unitarias focalizadas | `python -m pytest -q tests/unit/modules/inventory/test_stock_compatibility_validator.py tests/unit/modules/inventory/test_stock_compatibility_service.py tests/unit/modules/orders/application/test_use_cases.py tests/unit/modules/orders/test_layer_dependencies.py` | 43 passed |
| Repositorio Inventory con PostgreSQL temporal | `python -m pytest -q tests/integration/inventory/test_repository.py` | 41 passed |
| API Orders y aplicación | `python -m pytest -q tests/api/orders/test_orders_api.py tests/unit/modules/orders/application/test_use_cases.py` | 105 passed, 1 warning |
| Inventory + Orders + HU-014 | `python -m pytest -q tests/unit/inventory tests/unit/modules/inventory tests/unit/modules/orders tests/integration/inventory/test_repository.py tests/api/inventory/test_inventory_api.py tests/api/orders/test_orders_api.py` | 543 passed, 1 warning |
| Backend completo | `python -m pytest` | 1303 passed, 1 warning (333.30 s) |
| Componente HU-008 | `npm.cmd run test:component -- src/features/orders/__tests__/NuevoPedidoT03.test.jsx` | 14 passed |
| Unitarias frontend | `npm.cmd run test:unit` | 101 passed, 0 failed, 0 skipped |
| Componentes frontend | `npm.cmd run test:component` | 207 passed en 20 archivos |
| Lint frontend | `npm.cmd run lint` | Correcto, sin errores |
| Build frontend | `npm.cmd run build` | Correcto; Vite transformó 1941 módulos |
| E2E HU-008 | `npm.cmd run test:e2e -- hu008-stock-compatible.spec.js` | 4 passed en perfiles desktop y mobile |
| E2E completa | `npm.cmd run test:e2e -- --reporter=dot` | 35 passed, 1 skipped (41.4 s); el skip existente reserva la baja única HU-014 para desktop |
| Alembic | `python -m alembic heads` | Un head: `fa014e1a2b3c` |

Las pruebas de API cubren rechazo estructurado y ausencia de persistencia parcial;
la E2E compara inventario antes y después tanto en éxito como en rechazo. La E2E
completa usa un PostgreSQL temporal independiente y un fixture con recursos
separados para que la baja única HU-014 no afecte los pedidos de HU-007/HU-008.

## Criterios de aceptación

- **CA-01:** una plancha compatible permite crear el pedido.
- **CA-02:** un retazo compatible satisface la comprobación individual.
- **CA-03:** se excluyen tipo/espesor incompatibles, inactivos y planchas con cantidad cero.
- **CA-04:** una o más piezas sin candidato bloquean el POST completo y no crean pedido ni piezas.
- **CA-05:** API y UI identifican cada pieza no compatible y muestran el motivo.
- **CA-06:** las lecturas de compatibilidad no alteran cantidades ni estados.

## Riesgos y revisión manual sugerida

La AABB de un retazo circular o poligonal no garantiza que una forma quepa en
su silueta. Se debe revisar esta preselección frente al contrato de la futura
etapa de colocación. También conviene resolver la colisión histórica de
identificadores SP-005 antes de publicar un índice canónico de spikes. La SPEC
queda pendiente de revisión humana independiente y no se marca `Verified`.
