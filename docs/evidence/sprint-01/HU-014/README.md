# HU-014 — Baja y trazabilidad de inventario

## Identificación

| Campo | Valor |
|---|---|
| PBI | HU-014 — Baja y trazabilidad de inventario |
| SPEC | [SPEC-HU-014-trazabilidad-inventario.md](../../../specs/SPEC-HU-014-trazabilidad-inventario.md) |
| Rama | `feature/HU-014-trazabilidad-inventario` |
| HEAD funcional documentado | `83cedbe` |
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

La matriz completa CA-01 a CA-19 está en la [SPEC, sección 13](../../../specs/SPEC-HU-014-trazabilidad-inventario.md). CA-01 a CA-06 y CA-08 a CA-15, CA-17 a CA-19 constan como cumplidos. CA-07 y CA-16 constan como parciales porque la exclusión general de materiales en consumidores de stock no está demostrada por un contrato o consumidor activo de stock disponible.

## Entorno y resultados informados

- Backend: Windows, Python 3.11.9, pytest y PostgreSQL aislado para pruebas de integración.
- Inventory unit: **350 passed**.
- Inventory integration: **59 passed**.
- Inventory API: **46 passed**.
- Backend completo: **1181 passed**.
- Frontend unit: **84/84 PASS**.
- Frontend component: **166/166 PASS**.
- Frontend lint: **PASS**.
- Frontend build: **PASS**.
- E2E específico HU-014: **3 passed, 1 skipped, 0 failed**.
- `git diff --check`: **PASS**.
- Advertencia no bloqueante reportada en backend: `StarletteDeprecationWarning` / `httpx`.

El caso que registra una baja real se ejecuta en desktop: el fixture tiene una única plancha y la baja manual es única. El escenario de permisos se ejecuta en desktop y mobile. El skip no es un fallo.

La suite E2E global se ejecutó y tiene fallos pertenecientes a HU-007. No se reporta como verde y esos fallos no se atribuyen a HU-014; se revisarán separadamente.

Los comandos reproducibles y el desglose se encuentran en [test-results/README.md](test-results/README.md). No se fabricaron ni adjuntaron logs JUnit, salidas de pytest o capturas inexistentes.

## Cierre

La SPEC queda en **Implemented**, no en Verified. Antes de Verified y del cierre formal del PR queda la revisión final por otro integrante. La cobertura parcial de elegibilidad general de stock también queda visible en CA-07 y CA-16.
