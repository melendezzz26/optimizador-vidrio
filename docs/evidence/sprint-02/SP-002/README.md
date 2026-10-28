# SP-002 — Auditoría de reglas comunes

Responsable: Andro Quispe. Revisor: Fabricio Melendez Quezada.
Fecha: 28/10/2026. Verificación técnica completada; review y cierre formal pendientes.

## Base y coordinación

Base limpia: `4bcf54db8344d4003f115b38646f6fcfd23984a6`, integration/sprint-01,
tras fetch/prune y pull --ff-only. HEAD previo: `68b4bed` (rama documental anterior).
PR #73 integrado en `445886a`; PR #75 integrado en `2fc228d` (solo smoke/documentación).
últimos commits base: `4bcf54d` (#80), `45cbd80`, `a3414df` (#79), `56438b4`, `f1fd38d` (#77).
TA-021 ya está integrado y fue inspeccionado; no se modifica su comparador.

## Arquitectura auditada

`application/preparation.prepare_persisted_problem` valida geometrías y construye snapshots;
`domain/preparation.prepare_problem` expande cantidades y agrupa por material.
`with_compatible_stock` valida el proveedor y `InventoryStockAdapter` filtra tipo/espesor,
estado y cantidad; ordena fecha DESC, ID DESC, unidad física ASC.
Los tres optimizadores llaman a `packing.pack`: preparación defensiva → caché raster local →
orientaciones → nivel retazo/plancha → candidato canónico por fuente → selector → layout
inmutable del ganador → Placement → OptimizationResult.
`calculate_metrics` revalida geometría y calcula métricas comunes; `compare_methods` (TA-021)
captura una entrada inmutable y crea cada optimizador por ejecución.

Las rutas de componentes siguientes son relativas a
`backend/app/modules/optimization/`; pruebas a `backend/tests/unit/optimization/` salvo indicación.

## Matriz de las 20 reglas

| Regla | FF | BF | WF | Componente común | Evidencia | Estado |
|---|---|---|---|---|---|---|
| Preparación de piezas | expansión 1..N y orden área/bbox/IDs | Igual | Igual | `preparation.prepare_problem / prepare_group_units` | `test_preparation.py` | COMÚN Y GARANTIZADA |
| Agrupación por material | clave (vidrio, espesor) | Igual | Igual | `preparation.prepare_problem` | `test_preparation.py` | COMÚN Y GARANTIZADA |
| Compatibilidad vidrio/espesor | igualdad exacta; rechazo de proveedor incompatible | Igual | Igual | `stock.with_compatible_stock; InventoryStockAdapter; MaterialGroup` | `test_stock.py; test_retazo_priority.py` | COMÚN Y GARANTIZADA |
| Resolución raster | config.resolution_mm idéntica | Igual | Igual | `packing.pack; RasterCache` | `test_best_fit.py::test_all_heuristics_use_exact_same_rotation_component` | COMÚN Y GARANTIZADA |
| Máscaras | pieza conservadora; material interior | Igual | Igual | `RasterCache._raster; rasterizer` | `test_rotation.py; tests/optimization/` | COMÚN Y GARANTIZADA |
| Rotación | RasterCache.orientations | Igual | Igual | `packing.pack` | `test_best_fit.py::test_all_heuristics_use_exact_same_rotation_component` | COMÚN Y GARANTIZADA |
| Paso operacional 5° | default y puerta operacional; dominio permite otros pasos explícitos | Igual | Igual | `OptimizationConfig; AcceptRun` | `test_sprint2_angles.py` | COMÚN Y GARANTIZADA |
| Normalización/deduplicación | bbox local; máscara completa; primer ángulo; círculo solo 0° | Igual | Igual | `oriented_geometry; RasterCache.orientations` | `test_rotation.py; test_sprint2_angles.py` | COMÚN Y GARANTIZADA |
| Candidato factible | máscara dentro de usable y fuera de blocked | Igual | Igual | `_feasible_candidates; SheetLayout.first_position` | `test_best_fit.py; test_worst_fit.py; tests/optimization/` | COMÚN Y GARANTIZADA |
| Primera orientación por fuente | break tras primera orientación con posición | Igual | Igual | `_feasible_candidates` | `test_sprint2_angles.py::test_first_feasible_angle_is_70_not_90_for_pr64_geometry` | COMÚN Y GARANTIZADA |
| Primera posición por fuente | fila y después columna | Igual | Igual | `SheetLayout.first_position` | `test_common_rules.py::test_nonzero_distances_use_same_conservative_cells_and_first_position` | COMÚN Y GARANTIZADA |
| Prioridad RETAZO → PLANCHA | solo primer nivel factible | Igual | Igual | `packing.pack` | `test_retazo_priority.py` | COMÚN Y GARANTIZADA |
| Margen | ceil exacto distancia/resolución; erosión | Igual | Igual | `_distance_cells; _empty_layout` | `test_common_rules.py::test_nonzero_distances_use_same_conservative_cells_and_first_position` | COMÚN Y GARANTIZADA |
| Separación | ceil exacto; dilatación ocupación | Igual | Igual | `_empty_layout; SheetLayout.place` | `test_common_rules.py::test_nonzero_distances_use_same_conservative_cells_and_first_position` | COMÚN Y GARANTIZADA |
| Stock físico | identidad fuente/id/índice; retazo una unidad | Igual | Igual | `StockCandidate; InventoryStockAdapter` | `test_stock.py; test_common_rules.py` | COMÚN Y GARANTIZADA |
| Agotamiento de unidades | layouts por identidad; no inventar fuentes | Igual | Igual | `packing.pack` | `test_common_rules.py::test_unplaceable_unit_does_not_skip_smaller_units_or_invent_physical_stock` | COMÚN Y GARANTIZADA |
| No colocables | seguir siguientes unidades; unplaced_units explícito | Igual | Igual | `packing.pack; OptimizationResult` | `test_common_rules.py::test_unplaceable_unit_does_not_skip_smaller_units_or_invent_physical_stock` | COMÚN Y GARANTIZADA |
| Inmutabilidad | snapshots congelados; layout/cache locales; sin consumo | Igual | Igual | `problem.py; packing.pack; comparison.compare_methods` | `test_retazo_priority.py; test_comparison.py` | COMÚN Y GARANTIZADA |
| Determinismo | misma entrada y método reproducen placements/eventos | Igual | Igual | `packing.pack; selectores` | `test_sprint2_angles.py; test_comparison.py; test_common_rules.py` | COMÚN Y GARANTIZADA |
| Orden estable | grupos/órdenes ordenados; piezas área/bbox/IDs; stock estable por nivel | Igual | Igual | `prepare_group_units; packing.pack; InventoryStockAdapter` | `test_preparation.py; test_stock.py; test_best_fit.py; test_worst_fit.py` | COMÚN Y GARANTIZADA |
| Selección dentro del nivel | Primer factible | Mínimo libre posterior | Máximo libre posterior | FeasibleCandidate; selectores | test_best_fit.py; test_worst_fit.py; test_comparison.py | DIFERENCIA INTENCIONAL |

## Diferencias y límites precisos

BF/WF miden celdas de `usable & ~blocked` después del placement, incluyendo separación;
no área de bbox ni área nominal. Empates: stock_rank, orientation_rank, fila, columna.
FF corta perezosamente al primer candidato y no puntúa los posteriores; BF/WF recorren
el nivel. Es consecuencia de la política, no otra regla geométrica. Los patrones finales
pueden diferir. Cada fuente solo ofrece su primera orientación y posición factibles.
El orden de stock suministrado forma parte de la entrada: no se promete invariancia ante
su permutación. El adaptador sí lo estabiliza. El dominio permite pasos de investigación;
5° es el default y requisito operacional, no una prohibición global de otros pasos.
La duración de TA-021 no es determinista; el contrato reproducible se refiere a entrada,
placements, eventos y métricas geométricas, excluyendo tiempo.
FF puede no inspeccionar fuentes posteriores inválidas que BF/WF sí examinan: la
conclusión se acota a entradas válidas y presupuestos de recursos admitidos.

## Pruebas y criterios

Desde backend, Python `.venv/Scripts/python.exe`:

```text
python -m pytest tests/unit/optimization tests/optimization tests/integration/optimization/test_first_fit_slice.py tests/integration/optimization/test_best_fit_slice.py tests/integration/optimization/test_worst_fit_slice.py tests/integration/optimization/test_comparison_slice.py -q -ra
534 passed, 0 failed, 1 skipped in 16.91s
```

Skip: test_first_fit_slice.py:14, binarios PostgreSQL locales ausentes; CI exige PostgreSQL.
9 pruebas nuevas SP-002: distancias no nulas a resolución 1/2 mm (6) y
agotamiento/no colocables (3). Resto reutilizado, incluyendo slices SQLite.
CA-01: matriz; CA-02/03: preparation, rotation, sprint2_angles, retazo_priority y common_rules;
CA-04: common_rules y comparison; CA-05: selectores auditados y ninguna modificación productiva.

## GAP y conclusión técnica

No se encontró GAP funcional en las 20 reglas para el baseline válido auditado.
Había cobertura transversal insuficiente de distancias no nulas y agotamiento/no colocables
combinados; se completó con 9 pruebas. No se crearon abstracciones ni se modificó producción.

FF, BF y WF operan sobre las mismas reglas de preparación, factibilidad y generación
de candidatos; únicamente difieren en la política de selección del candidato dentro
del nivel permitido. Esta conclusión tiene los límites de entrada y duración indicados arriba.
SP-002 queda técnicamente verificado para iniciar TA-027; no cerrado formalmente.
