# Integración RBAC → Optimization Core

Base core: `3aca3c839ebe7b22a0269826c26d2518157fcb17`.
Integration incorporada por merge normal: `c4c5e5cf046a27cc57e9b33a9bd8f8f144b28f8c`.
Sin conflictos. Se preservan T1/preparación/stock/rotaciones/First Fit y HU-015.

Alembic: una head `s1rbac01a2b3`, padre `ta036a1b2c3d`.
RBAC real disponible: `optimization.view`, `optimization.execute`, `optimization.confirm`.
No se implementó confirmación ni se mutó inventario.

Validación reproducible (backend, runtime PostgreSQL local configurado):

```bash
python -m pytest tests/optimization tests/unit/optimization tests/api/optimization tests/integration/optimization tests/api/authorization tests/integration/test_s1_rbac_migration.py -q
DATABASE_URL=sqlite:// python -m alembic heads
git diff --check
```

Resultado: **473 passed, 1 warning** (deprecación Starlette/httpx); head única; diff-check limpio.
Log: `phase1-rbac-merge.log`. CA relacionados: 15, 26; regresión HU-015/core.

Ramas observadas: UI `4a3c9c1cd244780f8a1d97f1a527cd1fdebcf760`, Orders `2a5d835f0eaff9f0169e67e5b65866e24c532f6e`; ninguna integrada. No cambios propios de frontend/Orders. Pendientes: persistencia, API/NDJSON y estados. SPEC Reviewed / PLAN Approved.
