# SP-002 ? Auditor?a de reglas comunes

Responsable: Andro Quispe. Revisor: Fabricio Melendez Quezada.
Fecha: 28/10/2026. Verificaci?n t?cnica completada; review y cierre formal pendientes.

## Base y coordinaci?n

Base limpia: `4bcf54db8344d4003f115b38646f6fcfd23984a6`, integration/sprint-01,
tras fetch/prune y pull --ff-only. HEAD previo: `68b4bed` (rama documental anterior).
PR #73 integrado en `445886a`; PR #75 integrado en `2fc228d` (solo smoke/documentaci?n).
?ltimos commits base: `4bcf54d` (#80), `45cbd80`, `a3414df` (#79), `56438b4`, `f1fd38d` (#77).
TA-021 ya est? integrado y fue inspeccionado; no se modifica su comparador.

## Arquitectura auditada

`application/preparation.prepare_persisted_problem` valida geometr?as y construye snapshots;
`domain/preparation.prepare_problem` expande cantidades y agrupa por material.
`with_compatible_stock` valida el proveedor y `InventoryStockAdapter` filtra tipo/espesor,
estado y cantidad; ordena fecha DESC, ID DESC, unidad f?sica ASC.
Los tres optimizadores llaman a `packing.pack`: preparaci?n defensiva ? cach? raster local ?
orientaciones ? nivel retazo/plancha ? candidato can?nico por fuente ? selector ? layout
inmutable del ganador ? Placement ? OptimizationResult.
`calculate_metrics` revalida geometr?a y calcula m?tricas comunes; `compare_methods` (TA-021)
captura una entrada inmutable y crea cada optimizador por ejecuci?n.

Las rutas de componentes siguientes son relativas a
`backend/app/modules/optimization/`; pruebas a `backend/tests/unit/optimization/` salvo indicaci?n.

## Matriz de las 20 reglas

| Regla | FF | BF | WF | Componente com?n | Evidencia | Estado |
|---|---|---|---|---|---|---|
| Preparaci?n de piezas | expansi?n 1..N y orden ?rea/bbox/IDs | Igual | Igual | `preparation.prepare_problem / prepare_group_units` | `test_preparation.py` | COM?N Y GARANTIZADA |
| Agrupaci?n por material | clave (vidrio, espesor) | Igual | Igual | `preparation.prepare_problem` | `test_preparation.py` | COM?N Y GARANTIZADA |
| Compatibilidad vidrio/espesor | igualdad exacta; rechazo de proveedor incompatible | Igual | Igual | `stock.with_compatible_stock; InventoryStockAdapter; MaterialGroup` | `test_stock.py; test_retazo_priority.py` | COM?N Y GARANTIZADA |
| Resoluci?n raster | config.resolution_mm id?ntica | Igual | Igual | `packing.pack; RasterCache` | `test_best_fit.py::test_all_heuristics_use_exact_same_rotation_component` | COM?N Y GARANTIZADA |
| M?scaras | pieza conservadora; material interior | Igual | Igual | `RasterCache._raster; rasterizer` | `test_rotation.py; tests/optimization/` | COM?N Y GARANTIZADA |
| Rotaci?n | RasterCache.orientations | Igual | Igual | `packing.pack` | `test_best_fit.py::test_all_heuristics_use_exact_same_rotation_component` | COM?N Y GARANTIZADA |
| Paso operacional 5? | default y puerta operacional; dominio permite otros pasos expl?citos | Igual | Igual | `OptimizationConfig; AcceptRun` | `test_sprint2_angles.py` | COM?N Y GARANTIZADA |
| Normalizaci?n/deduplicaci?n | bbox local; m?scara completa; primer ?ngulo; c?rculo solo 0? | Igual | Igual | `oriented_geometry; RasterCache.orientations` | `test_rotation.py; test_sprint2_angles.py` | COM?N Y GARANTIZADA |
| Candidato factible | m?scara dentro de usable y fuera de blocked | Igual | Igual | `_feasible_candidates; SheetLayout.first_position` | `test_best_fit.py; test_worst_fit.py; tests/optimization/` | COM?N Y GARANTIZADA |
| Primera orientaci?n por fuente | break tras primera orientaci?n con posici?n | Igual | Igual | `_feasible_candidates` | `test_sprint2_angles.py::test_first_feasible_angle_is_70_not_90_for_pr64_geometry` | COM?N Y GARANTIZADA |
| Primera posici?n por fuente | fila y despu?s columna | Igual | Igual | `SheetLayout.first_position` | `test_common_rules.py::test_nonzero_distances_use_same_conservative_cells_and_first_position` | COM?N Y GARANTIZADA |
| Prioridad RETAZO ? PLANCHA | solo primer nivel factible | Igual | Igual | `packing.pack` | `test_retazo_priority.py` | COM?N Y GARANTIZADA |
| Margen | ceil exacto distancia/resoluci?n; erosi?n | Igual | Igual | `_distance_cells; _empty_layout` | `test_common_rules.py::test_nonzero_distances_use_same_conservative_cells_and_first_position` | COM?N Y GARANTIZADA |
| Separaci?n | ceil exacto; dilataci?n ocupaci?n | Igual | Igual | `_empty_layout; SheetLayout.place` | `test_common_rules.py::test_nonzero_distances_use_same_conservative_cells_and_first_position` | COM?N Y GARANTIZADA |
| Stock f?sico | identidad fuente/id/?ndice; retazo una unidad | Igual | Igual | `StockCandidate; InventoryStockAdapter` | `test_stock.py; test_common_rules.py` | COM?N Y GARANTIZADA |
| Agotamiento de unidades | layouts por identidad; no inventar fuentes | Igual | Igual | `packing.pack` | `test_common_rules.py::test_unplaceable_unit_does_not_skip_smaller_units_or_invent_physical_stock` | COM?N Y GARANTIZADA |
| No colocables | seguir siguientes unidades; unplaced_units expl?cito | Igual | Igual | `packing.pack; OptimizationResult` | `test_common_rules.py::test_unplaceable_unit_does_not_skip_smaller_units_or_invent_physical_stock` | COM?N Y GARANTIZADA |
| Inmutabilidad | snapshots congelados; layout/cache locales; sin consumo | Igual | Igual | `problem.py; packing.pack; comparison.compare_methods` | `test_retazo_priority.py; test_comparison.py` | COM?N Y GARANTIZADA |
| Determinismo | misma entrada y m?todo reproducen placements/eventos | Igual | Igual | `packing.pack; selectores` | `test_sprint2_angles.py; test_comparison.py; test_common_rules.py` | COM?N Y GARANTIZADA |
| Orden estable | grupos/?rdenes ordenados; piezas ?rea/bbox/IDs; stock estable por nivel | Igual | Igual | `prepare_group_units; packing.pack; InventoryStockAdapter` | `test_preparation.py; test_stock.py; test_best_fit.py; test_worst_fit.py` | COM?N Y GARANTIZADA |
| Selecci?n dentro del nivel | Primer factible | M?nimo libre posterior | M?ximo libre posterior | FeasibleCandidate; selectores | test_best_fit.py; test_worst_fit.py; test_comparison.py | DIFERENCIA INTENCIONAL |

## Diferencias y l?mites precisos

BF/WF miden celdas de `usable & ~blocked` despu?s del placement, incluyendo separaci?n;
no ?rea de bbox ni ?rea nominal. Empates: stock_rank, orientation_rank, fila, columna.
FF corta perezosamente al primer candidato y no punt?a los posteriores; BF/WF recorren
el nivel. Es consecuencia de la pol?tica, no otra regla geom?trica. Los patrones finales
pueden diferir. Cada fuente solo ofrece su primera orientaci?n y posici?n factibles.
El orden de stock suministrado forma parte de la entrada: no se promete invariancia ante
su permutaci?n. El adaptador s? lo estabiliza. El dominio permite pasos de investigaci?n;
5? es el default y requisito operacional, no una prohibici?n global de otros pasos.
La duraci?n de TA-021 no es determinista; el contrato reproducible se refiere a entrada,
placements, eventos y m?tricas geom?tricas, excluyendo tiempo.
FF puede no inspeccionar fuentes posteriores inv?lidas que BF/WF s? examinan: la
conclusi?n se acota a entradas v?lidas y presupuestos de recursos admitidos.

## Pruebas y criterios

Desde backend, Python `.venv/Scripts/python.exe`:

```text
python -m pytest tests/unit/optimization tests/optimization tests/integration/optimization/test_first_fit_slice.py tests/integration/optimization/test_best_fit_slice.py tests/integration/optimization/test_worst_fit_slice.py tests/integration/optimization/test_comparison_slice.py -q -ra
534 passed, 0 failed, 1 skipped in 16.91s
```

Skip: test_first_fit_slice.py:14, binarios PostgreSQL locales ausentes; CI exige PostgreSQL.
9 pruebas nuevas SP-002: distancias no nulas a resoluci?n 1/2 mm (6) y
agotamiento/no colocables (3). Resto reutilizado, incluyendo slices SQLite.
CA-01: matriz; CA-02/03: preparation, rotation, sprint2_angles, retazo_priority y common_rules;
CA-04: common_rules y comparison; CA-05: selectores auditados y ninguna modificaci?n productiva.

## GAP y conclusi?n t?cnica

No se encontr? GAP funcional en las 20 reglas para el baseline v?lido auditado.
Hab?a cobertura transversal insuficiente de distancias no nulas y agotamiento/no colocables
combinados; se complet? con 9 pruebas. No se crearon abstracciones ni se modific? producci?n.

FF, BF y WF operan sobre las mismas reglas de preparaci?n, factibilidad y generaci?n
de candidatos; ?nicamente difieren en la pol?tica de selecci?n del candidato dentro
del nivel permitido. Esta conclusi?n tiene los l?mites de entrada y duraci?n indicados arriba.
SP-002 queda t?cnicamente verificado para iniciar TA-027; no cerrado formalmente.
