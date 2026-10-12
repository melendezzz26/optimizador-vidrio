# HU-014 — Baja y trazabilidad de inventario

## Identificación

| Campo | Valor |
|---|---|
| PBI | HU-014 — Baja y trazabilidad de inventario |
| SPEC | [SPEC-HU-014-trazabilidad-inventario.md](../../../specs/SPEC-HU-014-trazabilidad-inventario.md) |
| Rama | `feature/HU-014-trazabilidad-inventario` |
| HEAD funcional HU-014 antes del merge | `83cedbe` |
| Merge post-integración | `01d84f9` |
| HEAD actual | `6489120` |
| Estado de SPEC | Implemented; pendiente revisión final para Verified |

## Trazabilidad de implementación

HU-014 → [SPEC](../../../specs/SPEC-HU-014-trazabilidad-inventario.md) → migración → backend → OpenAPI → frontend → pruebas → E2E → commits → futuro PR.

Commits funcionales de HU-014:

- `90ed2c2` — persistencia de movimientos.
- `3673735` — bajas transaccionales.
- `2724ae9` — historial y reglas finales.
- `579feea` — contrato OpenAPI.
- `83cedbe` — frontend + E2E HU-014.

La migración `fa014e1a2b3c` tiene como parent `ef6564220e70`. La revisión específica de migración se realizó con PostgreSQL aislado; no se ejecutó contra Supabase.

## Sincronización post-integración

`integration/sprint-01` llegó a `9407f26` y fue incorporada a esta rama mediante el merge `01d84f9`. Antes del PR quedaron incluidos los cambios integrados de HU-003 y HU-012.

## Backend y API

Rutas implementadas:

- `POST /api/inventory/planchas/{id_plancha}/baja`
- `POST /api/inventory/retazos/{id_retazo}/baja`
- `GET /api/inventory/planchas/{id_plancha}/movimientos`
- `GET /api/inventory/retazos/{id_retazo}/movimientos`

Las bajas manuales admiten `BAJA_ROTURA`, `BAJA_MERMA`, `BAJA_ERROR_REGISTRO` y `BAJA_RETIRO`. `CONSUMO_OPTIMIZACION` está reservado y no se acepta en el comando manual. La identidad del actor procede de la sesión autenticada, el motivo es obligatorio, la observación es opcional y la fecha la asigna el servidor.

El repositorio bloquea el recurso con `SELECT ... FOR UPDATE`; insertar movimiento y establecer `estado=false` forman una transacción atómica. Una baja manual previa produce 409. Un `estado=false` sin historial puede recibir una primera baja trazable. La reactivación después de una baja se rechaza con conflicto. El recurso y sus movimientos se conservan; no se ejecuta DELETE físico.

OpenAPI documenta para POST `201`, `401`, `403`, `404`, `409`, `422`; para GET de movimientos `200`, `401`, `403`, `404`, `422`.

## Frontend

La interfaz HU-014 está incluida para planchas y retazos: acción “Dar de baja”, selector de los cuatro eventos, motivo y observación, paso de revisión/confirmación, prevención de doble envío, feedback de éxito/error, fila conservada como inactiva y acción “Ver historial”. El historial presenta evento, motivo, observación, actor, fecha y optimización cuando existe; `observacion=null` se presenta como “Sin observación”. La interfaz no infiere una baja histórica solo desde `estado=false`.

Los diálogos implementan nombre accesible, foco inicial, ciclo de foco, Escape, retorno de foco y controles deshabilitados durante envío; los casos tienen cobertura de componentes.

## Criterios de aceptación

La matriz completa CA-01 a CA-19, incluido el texto de cada criterio, está en la [SPEC, sección 13](../../../specs/SPEC-HU-014-trazabilidad-inventario.md). CA-01 a CA-06, CA-08 a CA-15 y CA-17 a CA-19 constan como cumplidos. CA-07 y CA-16 permanecen parciales porque actualmente no existe un consumidor first-party real de stock elegible en el que verificar la exclusión. La auditoría no detectó un flujo first-party que permita utilizar material dado de baja; no se implementó funcionalidad especulativa para cerrar artificialmente esos criterios. La futura HU/PBI que implemente selección o consumo para optimización deberá verificar RN-09 con PostgreSQL controlado.

## Entorno y resultados previos al merge

- Backend: Windows, Python 3.11.9, pytest y PostgreSQL aislado para pruebas de integración.
- Inventory unit: **350 passed** (resultado previo al merge).
- Inventory integration: **59 passed** (resultado previo al merge).
- Inventory API: **46 passed** (resultado previo al merge).
- Backend completo: **1181 passed** (resultado previo al merge).
- Frontend unit: **84/84 PASS** (resultado previo al merge).
- Frontend component: **166/166 PASS** (resultado previo al merge).
- Frontend lint: **PASS** (resultado previo al merge).
- Frontend build: **PASS** (resultado previo al merge).
- Advertencia no bloqueante reportada en backend: `StarletteDeprecationWarning` / `httpx`.

## Resultados post-merge informados

- Backend completo: **1207 passed, 1 warning**, duración **258.92 s**. Comando: `.\venv\Scripts\python.exe -m pytest tests -q`. El único warning es `StarletteDeprecationWarning` de FastAPI/Starlette `TestClient`; no bloqueante.
- Alembic: `fa014e1a2b3c (head)`, único head. Comando: `.\venv\Scripts\python.exe -m alembic heads`.
- Frontend unit: **84 passed, 0 failed** (`npm run test:unit`).
- Frontend component: **19 test files passed; 205 tests passed, 0 failed** (`npm run test:component`).
- Lint: **PASS** (`npm run lint`).
- Build: **PASS** (`npm run build`), Vite **8.3.1**, **1941 modules transformed**.
- E2E específico HU-014: **3 passed, 1 skipped, 0 failed**. Comando: `npx playwright test tests/e2e/hu014-inventory-writeoff.spec.js`.
- Suite E2E completa: **31 passed, 1 skipped, 0 failed**. Comando: `npm run test:e2e`.
- El único skip corresponde al escenario de baja HU-014 en `chromium-mobile`: el fixture tiene una única plancha y esa baja solo puede ejecutarse una vez. El escenario de permisos sí se ejecuta en desktop y mobile. El skip es intencional, no un fallo.
- `git diff --check`: PASS para este cambio documental, verificado después de editar.

La suite E2E completa post-merge está verde en los resultados informados; ya no se registra una deuda vigente de HU-007 para esta rama.

Los comandos reproducibles y el desglose se encuentran en [test-results/README.md](test-results/README.md). No se fabricaron ni adjuntaron logs JUnit, salidas de pytest o capturas inexistentes.

## Cierre

La rama puede someterse a revisión mediante PR. La SPEC permanece en **Implemented**, no en Verified, y HU-014 no se declara Done. Verified requiere resolver formalmente CA-07/CA-16 mediante una selección real de stock y sus pruebas, o una decisión de alcance aprobada por el equipo/PO que difiera esos criterios. También queda pendiente la revisión final por otro integrante y el cierre formal del PR.
