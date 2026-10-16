# T3 de sesión — expansión, agrupación y preparación

Base: `ebd1bf80f70e1a091380a88ae0207376cd47f5e5`; rama exclusiva
`feature/S1-optimization-core`. Fecha: 16/10/2026 (Lima).
Equivalencia documental: T2 del PLAN Approved; no es la migración multipedido.

Objetivo: transformar snapshots persistidos de Orders en unidades inmutables,
grupos exactos tipo/espesor y secuencias RN-06 deterministas (CA-04/05/06/18).
Archivos: `domain/preparation.py`, `application/preparation.py`,
`tests/unit/optimization/test_preparation.py`, PLAN y esta evidencia/logs.

## Decisiones y límites

Application reutiliza la validación pública de piezas persistidas de Orders y
convierte NUMERIC/JSON mediante Decimal(str(valor)), sin Decimal(float).
Domain expande índices 1..N, rechaza piezas duplicadas y usa las invariantes T1
para cobertura exacta de pedidos. El cálculo de bbox usa Decimal sin rasterizar.
IDs de pieza son globales persistidos según T1; cada unidad conserva también pedido.
No se inventa un port batch ni persistencia multipedido; caller proporciona snapshots.
No hay mutaciones, acceso SQL, estados, métricas o endpoints nuevos.

## Vigilancia del equipo

Refs y archivos observados: [log](logs/t3-team.txt). Orders `2a5d835` incluye
`dd10ec0`: `FormularioPedido.buildPayload` ya construye tipo/espesor dentro de
cada pieza y devuelve `{piezas}`; es una evolución relacionada con el 422 histórico.
No prueba por sí sola que todo E2E pase; no se integra ni se corrige Orders aquí.
RBAC `4189193` incluye catálogo dinámico optimization.view/execute/confirm y guards;
no se duplica. UI `e42829d` sigue con fixtures y adapter futuro: usa fuentes
`plancha/retazo` en minúsculas, eventos `group_id`/run_id y medidas numéricas;
T1 usa RETAZO/PLANCHA, esquema v1, strings Decimal y stock_unit_index. Necesitará
adaptación coordinada; no altera el contrato backend congelado ni bloquea el motor puro.
HU-008 `a0a2dd2` es antecedente, no política geométrica. Integración `cf84d73`.

## Pruebas reproducibles y resultado

Desde backend, `source /workspace/.setup/runtime.sh` (Python 3.11.9 y PostgreSQL
17 local) y ejecutar:

```bash
python -m pytest -q tests/unit/optimization/test_preparation.py
python -m pytest -q tests/unit/optimization/test_preparation.py tests/optimization tests/unit/optimization tests/api/optimization
python -m alembic heads
```

22 focalizadas aprobadas; regresión combinada **308 passed, 1 warning** (TestClient/httpx),
0 fallos/skips. [Log](logs/t3-tests.txt). Alembic: única head `ta036a1b2c3d`.
HU-015 conserva raster/placement, API y contratos, todos verdes.
`git diff --check` correcto antes del commit. SPEC permanece Reviewed; PLAN Approved.

Baseline Cloud previo (otra base: main aae4bcc): backend 961 passed; frontend
128 passed, lint/build correctos; E2E 20 passed / 4 failed Orders HTTP 422.
No se atribuye ese resultado a esta rama ni se reejecuta frontend en estas tareas.
Riesgos pendientes: batch caller-owned Orders, puente RBAC y convergencia UI;
ninguno se requiere para lógica pura de preparación. No hay bloqueo material.
