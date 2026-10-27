# TA-020 — Auditoría de prioridad de retazos

| Campo | Valor |
|---|---|
| Fecha | 27/10/2026 (America/Lima) |
| Sprint / periodo | Sprint 2 / 21/10/2026 – 28/10/2026 |
| Responsable técnico | Andro Quispe |
| Scrum Master / revisor | Fabricio Melendez Quezada |
| Estado de revisión | Revisado / autorizado para continuar — 27/10/2026 |
| Commit base | 2a76141d38ca52045a5f5ee6000fea4eedb00885 |
| Rama | feature/S2-TA-020-retazo-priority |
| Clasificación funcional | **A. SATISFECHA** |

La regla solicitada ya existe para FF/BF/WF. No se modificó código productivo.
Esta clasificación corresponde a los seis criterios provisionales confirmados
por el usuario y los seis escenarios probados. La aclaración del 27/10/2026
resuelve la referencia de trabajo: se usa su regla funcional como aceptación
provisional, sin esperar otra fuente. No declara aprobación formal ni cierre
de TA-020; el review final del PR permanece pendiente.

## Sincronización y alcance

Estado inicial limpio en `feature/S2-rotation-best-fit`. Fetch actualizó
integration de 6f2a159 a 2a76141; PR #64 (b7b9caa) ya integró el trabajo previo.
`git log origin/integration/sprint-01..HEAD --oneline` estaba vacío. Se creó
la rama nueva directamente desde origin/integration/sprint-01, sin rebase/merge.
Se repitió fetch antes de los lotes de escritura; integration permaneció en
2a76141 y `origin/docs/TA-021-comparacion-metodos` en 36d9c234ec6bfce7bf59cca26c8cc9827ac3e89f.

SPEC y PLAN fueron creados antes del archivo nuevo de pruebas. El usuario confirmó
la revisión previa de Fabricio el 27/10/2026 y autorizó continuar hasta crear PR. El trabajo
de auditoría y pruebas está expresamente autorizado por la solicitud.

## Auditoría: diez respuestas

Rutas siguientes relativas a `backend/app/modules/optimization/`.

| Pregunta | Resultado y evidencia de implementación |
|---|---|
| 1. ¿Dónde se establece retazo antes de plancha? | `infrastructure/stock_adapter.py:InventoryStockAdapter.list_compatible` devuelve retazos primero; `domain/packing.py:pack` ordena por fuente y recorre `(REMNANT, SHEET)` por unidad. |
| 2. ¿Adapter, packing o ambos? | Ambos. Adapter ofrece orden reproducible; packing impone elegibilidad separada incluso con entrada que pone planchas primero. |
| 3. ¿FF lo respeta? | `domain/first_fit.py:FirstFitOptimizer.optimize` llama a `pack`; `next(candidates, None)` selecciona el primer candidato factible del nivel. |
| 4. ¿BF lo respeta? | `domain/best_fit.py:BestFitOptimizer.optimize` usa `pack` y `BestFitSelector.select`; minimiza capacidad libre posterior exclusivamente entre candidatos del nivel. |
| 5. ¿WF lo respeta? | `domain/worst_fit.py:WorstFitOptimizer.optimize` usa `pack` y `WorstFitSelector.select`; maximiza capacidad libre posterior del mismo nivel. |
| 6. ¿Se evalúan planchas con retazo factible? | No se generan candidatos geométricos ni se rasterizan/rankean planchas para esa unidad: `break` tras el ganador retazo. Sí se leen planchas en el catálogo y pueden estar en el snapshot; leer stock no equivale a evaluar factibilidad/ranking. |
| 7. ¿Incompatible llega al selector? | No: adapter filtra `(id_tipo_vidrio, espesor_mm)` y disponibilidad; `application/stock.py:CompatibleStockCache.list_compatible` rechaza proveedor incompatible; `domain/problem.py:MaterialGroup.__post_init__` rechaza mezcla incluso sin adapter. `Placement` añade defensa final. |
| 8. ¿Diferencias entre heurísticas? | Solo la elección dentro del nivel: FF primer factible, BF menor residual, WF mayor residual. Orden de orientación/posición y prioridad de fuente compartidos. |
| 9. ¿Lógica duplicada? | Orden retazo primero en adapter y sort de packing, con responsabilidades distintas; no hay tres implementaciones de política. El bucle de niveles y `_feasible_candidates` son comunes. No requiere refactor. |
| 10. ¿Pruebas existentes? | Sí: FF/BF/WF, stock, contratos y slices reales; se reutilizaron sin editarlas, ver abajo. |

Traza: catálogo filtrado → `CompatibleStockCache` → `MaterialGroup` validado →
`pack` prepara unidades y orden estable → `_feasible_candidates` filtra fuente,
comprueba máscara/posición real con layout actual → FF/BF/WF eligen dentro del
nivel → solo ganador modifica layout local → siguiente unidad reinicia niveles.

Determinismo: adapter ordena fecha DESC, ID DESC, unidad física ASC; packing
conserva el orden relativo por nivel, prepara unidades y ordena grupos/pedidos.
BF/WF desempatan por stock_rank, orientation_rank, row, column. No se promete
igual solución entre heurísticas; se verifica repetibilidad de cada una.

## Pruebas existentes reutilizadas

Rutas relativas a `backend/tests/`:

- `unit/optimization/test_first_fit.py`: `test_remnant_has_priority_even_if_input_includes_sheet_first`,
  `test_fallback_from_too_small_remnant_to_sheet`,
  `test_vertical_slice_persisted_snapshots_inventory_dtos_no_mutation_or_repeated_queries`.
- `unit/optimization/test_best_fit.py`: `test_remnants_compete_only_with_remnants_and_sheets_are_not_evaluated`,
  `test_sheet_fallback_and_physical_unit_exhaustion`,
  `test_reproducibility_events_and_immutable_input`, `test_application_simulation_does_not_mutate_inventory`.
- `unit/optimization/test_worst_fit.py`: `test_remnant_priority_prevents_even_evaluating_sheets`,
  `test_sheet_fallback_only_when_no_remnant_is_feasible`,
  `test_repeated_same_problem_has_fresh_layouts_and_identical_events`.
- `unit/optimization/test_stock.py`: `test_filter_material_and_inactive`,
  `test_priority_dates_ids_and_physical_units_no_collisions_or_mutation`,
  `test_provider_contract_cannot_inject_wrong_material`.
- `integration/optimization/test_worst_fit_slice.py`: snapshot completo de tablas
  para WF y `test_existing_first_fit_slice_still_passes_without_migrations`
  (reutiliza slice FF: cantidad de planchas, pedidos pendientes y tablas sin registros).
- `integration/optimization/test_best_fit_slice.py`: snapshot completo de tablas
  antes/después de simulación BF, para pasos 5° y 90°.

## Pruebas agregadas y matriz CA → evidencia

Archivo nuevo: `backend/tests/unit/optimization/test_retazo_priority.py`.
26 casos parametrizados; reutiliza helpers y adapter reales existentes.
No se usa el filtro del helper `problem` como prueba de exclusión de incompatibles.

Los CA-01 a CA-06 corresponden ahora a los seis puntos confirmados por el
usuario el 27/10/2026, transcritos en SPEC §8 como criterios provisionales.
Sustituyen la numeración operativa inicial; los escenarios y pruebas no cambian.
Evidencia de ejecución: [backend-tests.txt](backend-tests.txt).

| CA | Evidencia | Prueba nueva | Resultado |
|---|---|---|---|
| CA-01: Evaluar primero retazos compatibles. | Plancha primero en entrada; adapter ordena fuentes y packing impone niveles FF/BF/WF | `test_feasible_remnant_excludes_sheets_from_evaluation`; existente `test_priority_dates_ids_and_physical_units_no_collisions_or_mutation` | PASS |
| CA-02: Si existe al menos un retazo factible, FF/BF/WF deben resolver únicamente dentro del nivel retazo. | Planchas tentadoras para BF/WF; solo material retazo evaluado; pasos 5°/90° | `test_feasible_remnant_excludes_sheets_from_evaluation` | PASS, 6 casos |
| CA-03: Las planchas nuevas solo se evalúan si no existe ningún retazo factible. | Exclusión con retazo factible; fallback por retazo pequeño, ausencia o agotamiento por unidad | `test_feasible_remnant_excludes_sheets_from_evaluation`, `test_sheet_fallback`, `test_priority_is_rechecked_per_unit_and_repeated_runs_are_identical` | PASS en FF/BF/WF |
| CA-04: incompatibles excluidos | Otro vidrio/espesor descartado por adapter antes del motor; contrato de dominio rechaza inyección directa | `test_adapter_excludes_incompatible_remnant_before_optimization`, `test_domain_rejects_incompatible_candidate_without_filtering_helper` | PASS, 6 + 2 casos |
| CA-05: reproducibilidad, FF/BF/WF | Tres ejecuciones iguales, eventos/placements/fuentes iguales, entrada inmutable; retazo agotado conduce a plancha por unidad | `test_priority_is_rechecked_per_unit_and_repeated_runs_are_identical` | PASS, 3 casos |
| CA-06: simulación sin consumo, FF/BF/WF | Snapshot DTO antes/después y nueva lectura idéntica; además slices existentes con repositorios/SQLite | `test_simulation_leaves_inventory_unchanged` | PASS, 3 casos + slices reutilizados |

Los seis escenarios originales siguen cubiertos por 26 pruebas nuevas:
6 de prioridad, 6 de fallback (retazo no factible/sin retazo), 8 de
incompatibilidad, 3 de determinismo/agotamiento y 3 de simulación.
No hay GAP funcional identificado en los CA provisionales; el review final del PR
continúa pendiente y esta confirmación no implica cierre de TA-020.

## Ejecución reproducible

Entorno local `.venv/Scripts/python.exe`; desde `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/unit/optimization/test_retazo_priority.py -q
# 26 passed in 0.44s

..\.venv\Scripts\python.exe -m pytest tests/unit/optimization tests/optimization tests/api/optimization/test_run_contract.py tests/integration/optimization/test_worst_fit_slice.py tests/integration/optimization/test_best_fit_slice.py -q
# 498 passed in 5.39s
```

Segunda salida completa archivada. Incluye las 26 nuevas y 472 existentes.
Sin migraciones ni base remota; slices con SQLite local no equivalen a probar
concurrencia PostgreSQL ni CI remota. No hay cambios frontend que validar.

## Verificación y entrega

Comprobar desde raíz:

```powershell
git diff --check
git diff --cached --check
git diff 2a76141d38ca52045a5f5ee6000fea4eedb00885 -- backend/app
```

Los cuatro archivos restringidos (`domain/packing.py`, `first_fit.py`,
`best_fit.py`, `worst_fit.py`) permanecen idénticos a la base, al igual que
todo `backend/app`. Solo se agregan SPEC, PLAN, TASKS, esta evidencia, log y
el archivo de pruebas. No se crea comparador multimétodo.

## Entrega final preparada

- Base inicial: `2a76141d38ca52045a5f5ee6000fea4eedb00885`.
- Base final validada: `9cf6dc8739b9b6d1be19d0bb8d2411d762b74a80`.
- Sincronización normal de integration en la feature: merge `78224ce`, sin conflictos.
  No se realizó merge de ningún PR ni cambios directos en integration.
- Ubicación del proyecto: Trujillo, La Libertad, Perú; zona horaria America/Lima.
- SPEC/PLAN: revisados / autorizados para continuar por Fabricio Melendez Quezada,
  el 27/10/2026, según confirmación expresa del usuario.
- Clasificación: **A. SATISFECHA**; CA-01 a CA-06 verificados.
- Validación final tras sincronización: TA-020 **26 passed / 0 failed / 0 skipped**;
  regresión **498 passed / 0 failed / 0 skipped** (incluye los 26 de TA-020).
- PostgreSQL: no se encontraron binarios locales en PATH ni en la ruta de la
  fixture; no se ejecutaron regresiones PostgreSQL. Sin E2E en esta entrega.
- Diff contra integration: solo los seis archivos TA-020 descritos arriba;
  producción intacta, sin TA-021, secretos, temporales ni artefactos de entorno.
- Commits existentes: `b8d0417`, `f02efd3`; sincronización `78224ce`.
- Estado previo al PR: **Revisada y lista para entrega mediante PR**.
- Entrega autorizada: commit/push a `feature/S2-TA-020-retazo-priority`, crear PR
  hacia `integration/sprint-01`, consultar CI y solicitar review de Fabricio.
- Pendientes: PR/CI, review final del PR, merge por Fabricio, smoke y cierre.
  No habilitar auto-merge, rebase, squash ni cerrar TA-020.
