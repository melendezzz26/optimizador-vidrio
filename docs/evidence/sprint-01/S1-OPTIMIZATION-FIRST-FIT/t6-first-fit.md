# T6 de sesión — First Fit real

Base: `bfdeb74d90b47fa8810bd483873f6f6eda285f9e`. Rama única core.
Equivale a T4 histórica del PLAN Approved; no es la migración T6 histórica.

## Vertical slice

`application/first_fit.calculate_first_fit` conecta snapshots persistidos de Orders,
preparación T3, provider/cache de stock T4 y `domain/first_fit.FirstFitOptimizer`.
El motor usa rotaciones/cache T5 y SheetLayout público, sin imports de Application,
FastAPI, SQLAlchemy, Supabase o frontend desde Domain. Devuelve el
OptimizationResult/Placement T1 real; no cambia contratos wire ni HU-015.

Orden exacto: grupos tipo ASC/espesor ASC, unidades RN-06, RETAZO antes de PLANCHA;
suborden de stock se conserva del provider (fecha DESC/ID DESC/índice físico ASC).
Para cada candidato: orientaciones válidas ascendentes, row exterior 0..rows-piecerows,
column interior 0..columns-piececolumns, inclusivos. Acepta primera combinación
válida, llama check/place y rompe búsqueda para esa unidad. Jamás compara una
posición válida con alternativas para mejorar el resultado. Bbox negativa evita
posiciones imposibles; la aceptación siempre exige máscara interior real, margen,
separación y no overlap. Retazos circulares/poligonales no se rellenan por AABB.

Cada identidad (fuente, ID, physical_unit_index) tiene SheetLayout independiente.
Se comparten máscaras inmutables, nunca ocupaciones. Márgenes/separación Decimal
se convierten por ceil racional exacto a celdas, incluso valores menores que epsilon
legacy; la fábrica pública TA-007 recibe la distancia ya conservadora. Margen que
vacía toda la caja produce usable vacío sin iteración enorme; separación superior
a todo el material se satura a su diámetro Chebyshev en celdas (misma prohibición).
Posiciones se calculan como índice×resolución Decimal, sin acumulación float.

Si una unidad no cabe, se continúa con las siguientes y se conserva patrón parcial.
complete deriva exclusivamente de contadores T1. OptimizationRun impide COMPLETADA
para parcial y confirmable permanece false; no se implementa transición durable
SIN_SOLUCION/T9 ni confirmación. Métricas/tiempo del resultado siguen None: no se
inventan métricas completas, residuos ni disponibilidad confirmada. Hitos internos
tipados group_started/piece_started/piece_placed/group_completed ocurren durante la
búsqueda y usan contadores reales. No hay streaming ni callbacks HTTP del Domain.

## Pruebas obligatorias cubiertas

En `tests/unit/optimization/test_first_fit.py`:

- 1/18: una pieza cabe y resultado completo, placement/serialización T1.
- 2/10/11: patrón de tres cuadrados, row-major y replay independiente con SheetLayout.
- 3/19/21: no cabe; parcial conservado, unidades sin colocar y no confirmable.
- 4: primer candidato válido, sin siquiera rasterizar el posterior más ajustado.
- 5/6: prioridad retazo y fallback a plancha si no cabe.
- 7: 90° permite encaje; también 45° para rectángulo 6×1 sobre 5×5.
- 8/9: margen, separación, redondeo hacia arriba incluso sub-epsilon y margen enorme.
- 10: límites exactos y dimensiones fraccionarias que exceden el stock.
- 12: triángulo real, desigualdad x+y<=4 en las esquinas; círculo interior, no bbox.
- 13/14: cantidad de piezas y varios índices de una fila plancha, sin compartir layout.
- 15/16/17: dos pedidos, multimaterial/espesor y determinismo con input permutado.
- 20: stock DTO sin mutación; Application hace una consulta lógica del grupo.
- 22: regresión completa tests/optimization (TA-005/006/007), API/start/rasterize HU-015.
- Hitos vivos, propagación de errores de precisión (no NO_FIT falso) y guard de
  arquitectura por AST. Polígonos/círculos como piezas y contorno local serializable.

`tests/integration/optimization/test_first_fit_slice.py` usa PostgreSQL temporal,
OrdersRepository y InventoryRepository reales: dos pedidos persistidos con quantity=2,
plancha #5 cantidad=2, cuatro placements en índices físicos 1/2. Después: cantidad=2,
pedidos siguen PENDIENTE y cero Optimizacion/Ejecucion/Movimiento creados. No hay
batch transaccional inventado ni writes de producción: el test crea solo su fixture.

## Ejemplo inspeccionable y benchmark observado

Script real [first_fit_example.py](first_fit_example.py); salida [log](logs/t6-example.txt).
Tres cuadrados 2×2 en plancha 4×4, resolución 1, paso 90, margen/separación 0:
placements (0,0,0°), (2,0,0°), (0,2,0°), unidades 1/2/3 de pieza 101, pedido 21,
plancha 5/índice físico 1. Patrón derivado de máscaras reales:

```text
AABB
AABB
CC..
CC..
```

También 12 rectángulos 100×50 sobre 600×300, resolución 10 (60×30 celdas), paso 5°:
12/12 colocadas. Medición solo Domain en esta máquina: 0.676 ms pequeño y 18.982 ms
representativo; medición única ilustrativa, no SLA ni promesa de escala. El resultado
geométrico es repetible, el tiempo de pared no se presenta como métrica determinista.

## Comandos reproducibles

Desde backend, `source /workspace/.setup/runtime.sh`:

```bash
python -m pytest -q tests/unit/optimization/test_first_fit.py tests/integration/optimization/test_first_fit_slice.py
python -m pytest -q tests/optimization tests/unit/optimization tests/api/optimization tests/integration/optimization
python -m pytest -q
python ../docs/evidence/sprint-01/S1-OPTIMIZATION-FIRST-FIT/first_fit_example.py
python -m alembic heads
```

Focalizadas **26 passed** ([log](logs/t6-focused.txt)); regresión Optimization/HU-015
**374 passed, 1 warning**, sin skips/fallos ([log](logs/t6-regression.txt)).
Suite completa **1709 passed, 1 warning in 156.10s**, sin skips/fallos
([log](logs/t6-backend-full.txt)); incluye Orders, Inventory, migraciones
R1/R2/R3/R4/multimaterial y regresiones de HU-015. Warning conocido TestClient/httpx.
`python -m alembic heads`: única head `ta036a1b2c3d`.
`git diff --check` y revisión whitespace de archivos nuevos correctos antes del commit.

## Criterios, ramas externas y riesgos

Avanzados CA-04/05/06/07/08/09/10/11/12/15/18; parte Domain de CA-13/14/16/19.
No se afirma cierre de los CA que exigen transporte, durabilidad, estados,
métricas/confirmación o concurrencia. SPEC Reviewed y PLAN Approved conservados.

[Refs por tarea](logs/t6-team.txt) sin cambios desde T5. Orders dd10ec0 construye
payload por pieza relacionado con 422; RBAC 4189193 aporta permisos dinámicos;
UI e42829d es fixture y necesita mapeo al v1 (fuentes mayúsculas, Decimal string,
IDs de grupo/stock_unit_index y contorno ya orientado). Ninguna integración aquí.
HU-008 a0a2dd2 histórico, sin reutilizar sus aprobaciones AABB/solo 0–90/bloqueos.
Futuras tareas deben acordar batch caller-owned y guards antes de rutas nuevas.
Baseline Cloud previo (otra base) conserva backend 961, frontend 128/lint/build
correctos, E2E 20/4 Orders HTTP 422; no se ejecuta ni corrige frontend aquí.

Limitaciones: FF discreto no garantiza óptimo ni solución continua; precisión/rangos
son TA-005/006 con rechazo seguro de los casos que no puede rasterizar; cache por
corrida y presupuesto por máscara, no una garantía de tiempo/memoria global para
lotes arbitrarios. Consultar catálogos completos por grupo mantiene el contrato
actual de Inventory, requiere port filtrado coordinado si el volumen lo exige.
Ningún stock queda reservado. No endpoint/persistencia/streaming/estado nuevo,
ninguna migración, sin PR ni merges. No bloqueos materiales del slice.
