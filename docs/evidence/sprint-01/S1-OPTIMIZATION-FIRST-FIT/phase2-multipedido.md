# Multipedido y aceptación transaccional

Base/publicación anterior: `2cd5d0eb82b597a0e563849e35107be42510634b`.
Objetivo: T6 histórico (relación) + aceptación T7 del PLAN; no endpoints nuevos aún.

## Implementación / decisiones

- `models.py`, revisión `s1opt02b4c6d_optimization_multipedido.py`: PK compuesta,
  FK sin cascada destructiva, índice inverso, backfill comprobado. Padre exactamente
  `s1rbac01a2b3`; una head. Se preserva el campo legado por autorización explícita:
  compatibilidad escalar, nunca fuente del lote; eliminación posterior documentada.
- `application/run_ports.py`, `runs.py`; `infrastructure/run_uow.py`, `run_snapshot.py`:
  batch caller-owned, locks iniciales por ID ascendente, validador público Orders,
  configuración completa sin defaults, snapshot inmutable/desconectado, un commit.
- Contrato ORM histórico RBAC congelado en `tests/contracts/s1rbac_models.py`;
  sus tests siguen evaluando su propia revisión. Bootstrap/contrato HEAD actualizado.
- Diseño BD y PLAN actualizados; SPEC Reviewed intacta. Sin mutación de inventario.

## Pruebas reproducibles

Desde backend con PostgreSQL local (`NEWGLASS_TEST_PG_BIN` configurado):

```bash
python -m pytest tests/integration/optimization/test_runs.py tests/integration/optimization/test_multipedido_migration.py -q
python -m pytest tests/optimization tests/unit/optimization tests/api/optimization tests/integration/optimization tests/api/authorization tests/integration/test_s1_rbac_migration.py tests/integration/test_staging_bootstrap.py tests/integration/test_clients_migration.py -q
git diff --check
```

**19 passed** focalizadas; **498 passed, 1 warning** regresión. Logs adjuntos.
Cubre N=1/N>1, snapshots multimaterial, pieza inválida, inexistente/no elegible,
configuración NULL/múltiple, lote mixto, rollback inyectado, un commit, FK/PK,
backfill histórico, upgrade desde RBAC, downgrade seguro y rechazo sin pérdida.
HU-015 y RBAC execute regresados por sus rutas existentes; nuevos guards en fase API.
CA avanzados: 02,03,04,05,15,27. HEAD Alembic única comprobada por test.

UI observada `4a3c9c1`; Orders `2a5d835`; ninguna integrada/editada.
Riesgos: campo legado temporal; no recuperación automática de corridas abandonadas;
no endpoint público hasta completar orquestación/resultado. No Supabase.
