# PLAN-TA-019 — Worst Fit

## Información general

| Campo | Valor |
|---|---|
| Estado del PLAN | **Approved** |
| SPEC de referencia | [SPEC-TA-019-worst-fit.md](SPEC-TA-019-worst-fit.md), **Reviewed** |
| Responsable | Fabricio Melendez |
| Revisor de SPEC / PLAN | Pendiente de asignación formal |
| Sprint / épica | Sprint 2 / EP-003 Optimización |
| Rama | `feature/TA-019-worst-fit` |
| Fecha | 25/10/2026 |
| Base del contraste | `b1112a4` más cambios provisionales sin commit |
| Dependencias | SP-002, TA-016, FF y geometría/raster existentes; TA-037 cuando corresponda |

## 1. Objetivo, autoridad y estado

Este PLAN traduce exclusivamente los requisitos funcionales autorizados por el
usuario y formalizados en la SPEC Reviewed. Pasa a Approved por aprobación del
responsable comunicada en esta sesión. T01 y T02 fueron ejecutadas según el plan,
con 22 CA técnicamente satisfechos y evidencia reproducible de Sprint 2.
La revisión cruzada real permanece pendiente. Las decisiones de diseño de §3
derivan de RN-01 a RN-08, no de la existencia del código provisional.

La implementación precedió a esta formalización documental. §8 la contrasta en
modo de solo lectura; sus PASS técnicos no sustituyen la revisión de la SPEC,
el cierre de evidencias ni la Definition of Done. La formalización inicial fue
solo documental. El cierre técnico posterior autorizado añade la regresión
CA-12 y evidencia real, sin cambiar producción ni ejecutar migraciones, commit o PR.

## 2. Secuencia de trabajo y dependencias

1. Revisar SPEC y PLAN, asignar revisor y resolver observaciones de alcance.
2. Vincular la decisión de SP-002 y coordinar el contrato de TA-016; no asumir
   estados de cierre que no estén documentados.
3. Contrastar T01 con RN-01 a RN-08 y corregir solo después de autorización.
4. Completar T02 y evidencia faltante; conservar regresión FF.
5. Ejecutar validación aplicable y revisar diff/alcance.
6. Una vez autorizado, crear commit y PR trazables a TA-019.

No se encontró un documento local identificado como SP-002 o TA-037 al buscar
esos IDs en `docs/`, README y CONTRIBUTING. Son dependencias declaradas, con
referencias formales pendientes; esto no autoriza implementar esas tareas.

## 3. Estrategia técnica derivada de la SPEC

| Decisión propuesta | Requisito que satisface |
|---|---|
| `packing.py` concentra el recorrido compartido, preparación vigente, niveles y aplicación. | RN-01/RN-02/RN-07; CA-02/04/11/13. |
| `FeasibleCandidate` contiene fuente/rangos, layout, orientación y posición canónica. | RN-03/RN-05; CA-05/06/09. |
| Propiedad temporal `layout_after` usa la operación inmutable existente. | RN-04/RN-06; CA-07/10. |
| Score cuenta `usable & ~blocked` del layout posterior. | RN-04; CA-07/08/17/18. |
| Selector WF consume incrementalmente y minimiza la clave aprobada. | RN-05/RN-06; CA-08/09/12. |
| FF usa el primer candidato mediante `next()`, sin evaluación del score. | RN-07; CA-13/22. |
| `worst_fit.py` contiene la política WF y su entrada de dominio. | CA-01; separación de política y geometría. |
| Snapshots y stock se preparan mediante funciones/adaptadores existentes. | RN-01/RN-07; CA-14/19/20. |
| Identidad WF limitada al resultado de dominio; adaptadores actuales siguen FF. | Alcance de salida; sin persistencia/HTTP multimétodo. |

La abstracción debe permitir un futuro selector BF sobre los mismos candidatos,
sin implementarlo aquí. No se crea un framework, registro de métodos ni nuevas
reglas de geometría. Las máscaras/orientaciones pueden conservar sus cachés
existentes; no materializar todos los candidatos con sus layouts posteriores.

## 4. Tareas trazables

### TA-019 T01 — Implementar algoritmo Worst Fit

**Entradas:** SPEC revisada, instancia existente y contratos compartidos.

**Trabajo previsto:**

1. Extraer solo el recorrido y utilidades necesarios para evitar duplicación;
   preservar imports existentes y la semántica de FF.
2. Generar incrementalmente un candidato factible por fuente y nivel, usando
   primera orientación compartida factible y primera posición válida.
3. Calcular el estado posterior temporal inmutable, con margen y separación.
4. Elegir mayor capacidad posterior con los cinco desempates de la SPEC.
5. Aplicar únicamente el ganador y continuar después de piezas no colocables.
6. Reutilizar preparación/stock sin escrituras de inventario ni nueva ruta HTTP.
7. Mantener resultado compatible, identidad WF de dominio y métricas comunes.

**Salida verificable:** algoritmo puro, candidatos descartables, FF perezoso,
resultado completo/parcial y límites de alcance preservados.

**Trazabilidad:** CA-01 a CA-15, CA-20 y CA-21; T02 demuestra CA-16 a CA-19 y CA-22.

**Estado observado:** T01 ejecutada según el plan, con los CA aplicables
técnicamente satisfechos y evidencia de Sprint 2 vinculada en §6. Sin commit;
revisión cruzada y cierre posterior al versionado/PR pendientes.

### TA-019 T02 — Crear pruebas de Worst Fit

| Caso | Ejemplo o comprobación | CA |
|---|---|---|
| WF claro | Pieza 2×2; fuentes 4×4, 6×4 y 3×3: gana 6×4. | 01/05/08 |
| Empate | Fuentes iguales: gana menor `stock_rank`, no ID reconstruido. | 09 |
| Desempates completos | Rangos y posiciones equivalentes salvo el campo que desempata. | 09 |
| Posterior frente a previo | Pieza 1×1, separación 1: 4×4 deja 12 y 1×15 deja 13. | 07/08/17 |
| Varias piezas | Dos fuentes 4×4, tres piezas 2×2: A → B → A sin aplicar descartados. | 10/11 |
| Rotación necesaria | Pieza 3×2 sobre fuente 2×3: usa 90° del componente común. | 03/06/16 |
| Colocación canónica | Una orientación posterior dejaría más espacio, pero se usa la primera factible. | 06 |
| No colocable/parcial | Pieza 5×5 en fuente 4×4; una pieza posterior 2×2 sí se intenta. | 05/20 |
| Retazo primero | Retazo 3×3 y plancha 10×10: pieza 2×2 usa retazo. | 04 |
| Varios retazos | Retazos 3×3 y 4×4: pieza 2×2 elige 4×4. | 04/08 |
| Plancha necesaria | Ningún retazo aloja la pieza; seleccionar WF entre planchas. | 04/05/08 |
| Unidades físicas | Cantidad 2, demanda 3: dos identidades usadas y una unidad faltante. | 20 |
| Margen/separación | Validar posiciones, score posterior y rechazo si no cabe. | 07/17 |
| Material irregular | Triángulo: score interior real y rechazo fuera de su forma. | 18 |
| Multimaterial/multipedido | Sin cruces de tipo/espesor; preservar referencia de cada pedido. | 02/19 |
| Determinismo | Misma instancia repetida y piezas permutadas antes de preparar. | 15 |
| Simulación sin consumo | Comparar inventario y todas las tablas antes/después del slice. | 14 |
| Retención acotada | Comparar objetos vivos con cantidades pequeñas de fuentes; liberar descartados. | 12 |
| FF lazy/early exit | Fallar si consulta el score o evalúa stock después del primer éxito. | 13/22 |
| Errores de recursos | Propagar error técnico; no informar NO_FIT artificial. | 05/20 |

**Ubicaciones previstas:** `backend/tests/unit/optimization/test_worst_fit.py`
y `backend/tests/integration/optimization/test_worst_fit_slice.py`. Reutilizar
las regresiones existentes de FF y geometría, sin duplicarlas.

**Salida verificable:** matriz cubierta, ejecución aplicable correcta y evidencia
reproducible. Estado observado: T02 ejecutada según el plan; validación técnica
completa de los 22 CA, regresión CA-12 y salida real de 381 pruebas archivada
en la evidencia de Sprint 2. Revisión cruzada pendiente, ver §9.

## 5. Coordinación y archivos de alcance

- `domain/packing.py`, `first_fit.py`, `worst_fit.py`: recorrido y política;
  coordinar la extracción con TA-018 para evitar motores o candidatos duplicados.
- `domain/problem.py`: solo la compatibilidad de identidad del resultado de
  dominio que resulte necesaria; no generalizar snapshots o contratos HTTP.
- Preparación, stock, `SheetLayout`, raster, métricas y orientación: reutilizar;
  no modificar sus reglas para adaptar el algoritmo.
- `rotation.py` queda intacto. TA-016 debe conservar orden determinista de
  `RasterCache.orientations(unit, resolution, step)` y `rotation_deg`, contorno
  local y máscara coherentes. Coordinar sus consumidores de métricas y
  confirmación, que revalidan sin volver a buscar colocaciones.
- Fuera del diff de implementación: frontend, SQLAlchemy/Alembic, RBAC,
  confirmación transaccional y contratos HTTP/NDJSON multimétodo.

## 6. Validación y evidencia reproducible

Desde `backend/`, con el entorno existente; no requiere instalar dependencias
ni ejecutar migraciones:

```powershell
.\venv\Scripts\python.exe -m pytest tests/unit/optimization/test_worst_fit.py -q
.\venv\Scripts\python.exe -m pytest tests/unit/optimization tests/optimization tests/api/optimization/test_run_contract.py tests/integration/optimization/test_worst_fit_slice.py -q
```

Desde la raíz:

```text
git diff --check
git status
git diff --stat
git diff --name-status
```

Guardar salida real, versión de Python, revisión/estado del árbol y alcance de
las suites. Los archivos nuevos no aparecen en `git diff --stat` ni
`--name-status` hasta ser añadidos al índice: informar también `git status` y
sus tamaños sin hacer staging implícito.

El slice SQLite utiliza repositorios reales y metadata de pruebas adaptado en
memoria; no valida restricciones, locks o concurrencia PostgreSQL. La regresión
existente de FF también se reutiliza en ese slice sin Alembic. No ejecutar las
fixtures PostgreSQL que migran una base mientras esa acción no esté autorizada.

**Validación final del cierre técnico:** el comando combinado produjo
`381 passed in 1.59s`, código de salida 0. Incluye 28 pruebas unitarias de WF/
regresión FF y dos slices. La prueba CA-12 aislada produjo
`1 passed, 27 deselected in 0.30s`.

La salida real completa está en
[backend-tests.txt](../evidence/sprint-02/TA-019/backend-tests.txt); el contexto y
los comandos están en el [README de evidencia](../evidence/sprint-02/TA-019/README.md).
El antecedente anterior de 380 pruebas queda superado por esta ejecución.
No constituye verificación de integración HTTP WF ni de PostgreSQL.

## 7. Riesgos y mitigaciones

| Riesgo | Tratamiento |
|---|---|
| Mayor costo que FF | WF evalúa todas las fuentes del nivel; conservar generadores y cachés acotadas. |
| Fragmentación no representada completamente | Score libre total no garantiza continuidad; validar factibilidad real y no prometer óptimo. |
| Conflictos con TA-016 | Consumir el contrato actual, no editar rotación; coordinar cambios con sus consumidores. |
| Conflictos con TA-018 | Compartir candidato/recorrido y acordar ownership de `packing.py`/`first_fit.py`. |
| Identidad futura de método | Resultado WF solo de dominio. Los adaptadores FF actuales pueden rechazarlo o perder su identidad al reconstruirlo; no conectarlos aquí. |
| Presupuestos globales / TA-037 | Mantener guardrails existentes y vincular definición global pendiente; número acotado de objetos no equivale a límite global de bytes. |
| Regresión de FF por extracción | Preservar `next()`, imports y orden; ejecutar regresiones geométricas, métricas y contrato actual. |
| Pérdida de trazabilidad SDD | Registrar aprobación del responsable y revisión cruzada pendiente; no usar el código como justificación de requisitos. |

## 8. Contraste READ-ONLY con la implementación provisional

**Fuentes:** [packing.py](../../backend/app/modules/optimization/domain/packing.py),
[worst_fit.py](../../backend/app/modules/optimization/domain/worst_fit.py),
[first_fit.py](../../backend/app/modules/optimization/domain/first_fit.py),
[pruebas WF](../../backend/tests/unit/optimization/test_worst_fit.py) y
[slice](../../backend/tests/integration/optimization/test_worst_fit_slice.py).
Las funciones de prueba citadas debajo pertenecen a esos dos archivos salvo
indicación expresa. Las utilidades comunes existentes se inspeccionan, no se modifican.

**Clasificación:** PASS = conformidad respaldada por código/prueba inspeccionados
y, cuando aplica, la ejecución final archivada; PARTIAL = mecanismo presente
con verificación específica incompleta; FAIL = contradicción concreta con la SPEC.
Los PASS técnicos no sustituyen la revisión cruzada. La aprobación del
responsable y la evidencia del cierre técnico se registran separadamente.

| CA | Estado | Evidencia en código/prueba | Gap |
|---|---|---|---|
| CA-01 | PASS | `WorstFitSelector.select`, `WorstFitOptimizer.optimize`; `test_clearly_worst_source_and_domain_method_identity`. | Ninguno funcional identificado. |
| CA-02 | PASS | `pack` compartido; preparación existente; `SheetLayout.first_position/place` y `RasterCache`; slice real. | Ninguno funcional identificado. |
| CA-03 | PASS | `_feasible_candidates` consume `RasterCache.orientations`; `test_rotation_uses_common_component_and_first_feasible_angle`; `rotation.py` sin diff. | Coordinación formal TA-016 pendiente. |
| CA-04 | PASS | Bucle RETAZO → PLANCHA de `pack`; `test_remnant_priority_prevents_even_evaluating_sheets`, `test_worst_fit_between_remnants`, `test_sheet_fallback_only_when_no_remnant_is_feasible`. | Ninguno funcional identificado. |
| CA-05 | PASS | `first_position` y `place`; `test_unplaceable_piece_has_no_fake_placement_and_is_not_confirmable`. | Ninguno funcional identificado. |
| CA-06 | PASS | `yield` y `break` por fuente; `test_does_not_search_for_a_better_angle_or_position_within_source`. | Ninguno funcional identificado. |
| CA-07 | PASS | `FeasibleCandidate.layout_after` y `remaining_free_cells_after_placement`; `test_score_uses_real_post_placement_separation_and_does_not_mutate_layout`. | Ninguno funcional identificado. |
| CA-08 | PASS | Clave negativa posterior en `WorstFitSelector.select`; pruebas de fuente clara, posterior y varios retazos. | Ninguno funcional identificado. |
| CA-09 | PASS | Tupla completa de selección; `test_tie_preserves_upstream_stock_rank_not_id_order`, `test_selector_uses_all_approved_tiebreaks`. | Ninguno funcional identificado. |
| CA-10 | PASS | `SheetLayout` inmutable y `place` devuelve otro estado; prueba de score/no mutación. | Ninguno funcional identificado. |
| CA-11 | PASS | Única asignación del ganador a `layouts`; `test_multiple_pieces_change_source_and_losing_trials_are_not_applied`. | Ninguno funcional identificado. |
| CA-12 | PASS | `test_candidate_selection_is_incremental_and_releases_discarded_layouts`: 8 y 80 fuentes factibles, dos piezas, referencias débiles, intercalado generación/score y comparación de picos sin fijar un conteo exacto. | Cerrado técnicamente; salida real archivada. |
| CA-13 | PASS | `pack` usa `next` sin selector para FF; `test_first_fit_does_not_score_or_evaluate_later_sources`. | Ninguno funcional identificado. |
| CA-14 | PASS | `test_preparation_stock_slice_does_not_consume_or_mutate_inventory`; slice compara todas las tablas. | Evidencia limitada al cálculo; no afirma confirmación WF. |
| CA-15 | PASS | `test_repeated_same_problem_has_fresh_layouts_and_identical_events`, `test_multimaterial_multiorder_and_existing_piece_order_are_deterministic`. | Ninguno funcional identificado. |
| CA-16 | PASS | `test_rotation_uses_common_component_and_first_feasible_angle`: 3×2 en 2×3 a 90°. | Ninguno funcional identificado. |
| CA-17 | PASS | `test_margin_changes_score_and_is_respected_at_canonical_position`, `test_separation_blocks_the_required_empty_cell`. | Ninguno funcional identificado. |
| CA-18 | PASS | `test_irregular_material_score_counts_interior_not_bbox`; raster interior común. | Ninguno funcional identificado. |
| CA-19 | PASS | Prueba multimaterial/multipedido y `test_real_multiorder_multimaterial_stock_to_wf_without_any_database_writes`. | Ninguno funcional identificado. |
| CA-20 | PASS | Pruebas no colocable, `test_failed_large_piece_does_not_suppress_smaller_units` y unidades físicas; DTO `RunStatus.NO_SOLUTION` existente. | Sin nueva ruta HTTP WF, conforme al alcance. |
| CA-21 | PASS | Diff limitado a dominio/pruebas/documentación; modelos y Alembic sin cambios. | Ninguno de esquema identificado. |
| CA-22 | PASS | Suite final de 381 pruebas; regresiones FF y `test_existing_first_fit_slice_still_passes_without_migrations`; salida en `backend-tests.txt`. | Ninguno técnico identificado. |

**Conteo final:** 22 PASS / 0 PARTIAL / 0 FAIL. SPEC Reviewed y PLAN Approved
por aprobación del responsable; revisor y revisión cruzada real pendientes.

### Precisión sobre memoria observada

La auditoría previa de solo lectura instrumentó `SheetLayout` con referencias
débiles y casos pequeños: dos layouts posteriores de prueba simultáneos;
hasta dos estados base temporales; y un estado anterior adicional retenido por
variables locales de `pack` de la pieza previa. Para K layouts reales usados,
la cota observada/razonada es K + 5 objetos durante selección, hasta cuatro en
la primera pieza. Un caso con K=1 alcanzó seis objetos vivos y cero al retornar.

No se retienen todos los candidatos; algunos estados comparten máscaras. La
auditoría histórica no es un presupuesto global aprobado de bytes. La nueva
regresión CA-12 protege la propiedad de escalamiento: multiplica las fuentes
factibles por diez y exige que los picos de candidatos/layouts posteriores no
superen dos veces la referencia pequeña, sin depender de la cota histórica K+5.
También detecta materialización adelantada y comprueba liberación durante la
selección y al retornar. Usa grids 4×4, sin cargas masivas ni OOM.

## 9. Gaps y comportamiento fuera de alcance

| Gap | Estado | Evidencia o acción pendiente |
|---|---|---|
| G-01 — CA-12 | Cerrado técnicamente | Regresión automatizada de retención incremental y liberación; ejecución aislada y suite final correctas. |
| G-02 — Evidencia | Cerrado técnicamente | `README.md`, `backend-tests.txt` y `diff-check.txt` en `docs/evidence/sprint-02/TA-019/`. |
| G-03 — Dependencias | Coordinación pendiente | Vincular referencias de SP-002 y TA-037; coordinar TA-016/TA-018 sin asumir su aprobación. No altera el conteo de conformidad funcional actual. |
| G-04 — Proceso | Revisión cruzada y versionado pendientes | Aprobación del responsable registrada: SPEC Reviewed y PLAN Approved. Asignar revisor para revisión cruzada real; commit y PR siguen sin autorización. |

No se detectó comportamiento funcional implementado fuera del alcance de esta
SPEC: la extracción compartida, eventos existentes y especialización de
`OptimizationResult` con identidad WF permanecen en dominio. La ampliación de
la anotación `method` no generaliza HTTP/persistencia; el valor base sigue FF.
No hay BF, UI multimétodo, TA-025/TA-026, migraciones o nueva confirmación.

## 10. Definition of Done

TA-019 se considera terminada únicamente cuando:

- [ ] Revisión cruzada de la SPEC por revisor formalmente asignado.
- [x] PLAN aprobado por el responsable y coherente con la SPEC Reviewed.
- [x] Implementación cumple todos los CA, incluido cierre verificable de CA-12.
- [x] Pruebas aplicables pasan y FF no presenta regresiones.
- [x] `git diff --check` pasa y el diff mantiene el alcance autorizado.
- [x] Existe evidencia reproducible y trazabilidad de cada CA.
- [ ] Dependencias/contratos pertinentes están vinculados y coordinados.
- [ ] Commit y PR autorizados mantienen trazabilidad explícita con TA-019.

El cierre técnico se respalda por la ejecución final y evidencia registrada.
La aprobación del responsable establece SPEC Reviewed y PLAN Approved, con
T01/T02 ejecutadas según el plan. La revisión cruzada, coordinación pendiente
y entrega continúan abiertas; no se declara Verified ni cierre posterior al PR.

## Historial de estado

| Fecha | Estado | Nota |
|---|---|---|
| 25/10/2026 | Draft | PLAN derivado de la SPEC; contraste provisional de solo lectura, sin aprobación formal. |
| 25/10/2026 | Draft | Cierre técnico/evidencial: CA-12 automatizado, 381 pruebas correctas, 22 CA PASS; revisor y aprobación formal pendientes. |
| 25/10/2026 | Approved | Aprobación del responsable comunicada en esta sesión; SPEC Reviewed, T01/T02 ejecutadas y evidencia de Sprint 2 vinculada. Revisión cruzada y versionado pendientes. |
