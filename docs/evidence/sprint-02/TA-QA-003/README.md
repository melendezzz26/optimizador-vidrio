# TA-QA-003 - Auditoria y expectativas previas

Base auditada: dfeaa56f4b7a39dd66f83d28b977f6a771053f13, integration-02. Expectativas registradas antes de ejecutar la bateria de esta tarea. Esto no representa resultados ni certifica cobertura. MF-01, MF-02 y MF-03 siguen pendientes hasta identificar y ejecutar denominadores completos. Sin acceso a Notion se deben validar subtareas oficiales.

## Implementacion auditada

| Metodo | Modulo de dominio | Politica observada |
|---|---|---|
| FF | first_fit.py | Primera fuente factible, orientacion y posicion por orden canonico. |
| BF | best_fit.py | Minimo de celdas libres tras colocar dentro del nivel activo; desempate estable. |
| WF | worst_fit.py | Mayor capacidad libre posterior entre fuentes ya usadas; si ninguna sirve abre primera fuente no usada. |
| HF / M4 | hole_filling.py | Busqueda local acotada de cavidades, orden de fuente FF y fallback. |
| M5 / BRF | best_residual_fit.py | Maximiza mayor rectangulo libre entre fuentes usadas, con desempate por fragmentacion; abre la primera nueva si ninguna usada sirve. |
| M6-BS / BS-2 | beam_search.py | Busqueda beam acotada, ancho predeterminado 2, limites de expansion, memoria y tiempo. |

Catalogo: backend/app/modules/optimization/application/comparison_catalog.py. WF y M5 respetan el nivel de material y priorizan fuentes usadas; no se describen como abrir otra plancha para maximizar residual.

## Pruebas existentes y brechas

Se identificaron pruebas unitarias de los seis motores, rotacion, geometria, separacion, raster y comparison; pruebas de integracion para FF/BF/WF y comparacion. Los fixtures de test_best_fit, test_worst_fit, test_hole_filling y test_beam_search son candidatos a reutilizar, evitando duplicacion. Se debe comprobar que el mismo conjunto comun cubra los seis y que el oraculo geometrico verifique margenes, separacion, fuente y rotacion; un replay basado en el mismo motor no es por si solo un oraculo independiente. Las pruebas ejecutadas y sus limites se registran abajo.

## Expectativas y fixture previstos

| Caso | Metodo | Esperado antes de ejecutar | Justificacion y referencia candidata |
|---|---|---|---|
| AF-01 | seis | Todos completan un caso pequeno comun y producen patron valido | Contrato comun; fixture controlado por definir. |
| AF-02 | FF/BF | FF selecciona primera fuente viable; BF elige la de menor capacidad libre posterior | test_best_fit.py y test_first_fit.py. |
| AF-03 | WF/FF | Con dos fuentes usadas, WF elige mayor residual y FF primera factible | test_worst_fit.py. |
| AF-04 | HF | Buscar pocket reutilizable en fixture existente sin afirmar superioridad general | test_hole_filling.py; seleccionar prueba concreta y registrar coordenadas. |
| AF-05 | M5 | Entre fuentes usadas, elegir mayor rectangulo libre posterior; desempatar segun codigo | test_best_residual_fit.py; seleccionar caso que diferencie puntajes. |
| AF-06 | M6 | Caso determinista dentro de limites donde la secuencia difiera de greedy | Fixture aun por demostrar; no inferirlo de que M6 complete. |
| AF-07 | seis | Separacion cero y positiva respetadas entre piezas | test_ta045_separation.py; ampliar comparacion entre motores si falta. |
| AF-08 | seis | Ninguna pieza invade margen | test_run_geometry.py y pruebas de motor; completar oraculo. |
| AF-09 | seis | Pieza 3x2 en 2x3 solo cabe con rotacion permitida de 90 grados | Pruebas de rotacion existentes; verificar cada metodo. |
| AF-10 | seis | Ninguna interseccion entre piezas del mismo material | Comprobar patrones con oraculo independiente. |
| AF-11 | seis | Pieza imposible se informa incompleta, sin colocacion inventada | Caso 7x7 en fuente 6x4. |
| AF-12 | seis | Rectangulos, circulos y poligonos admitidos generan colocaciones validas | test_hole_filling.py incluye geometria mixta; confirmar soporte y comportamiento por metodo. |

## Resultados y defectos

Defectos de motor: documentar caso, reproduccion, severidad y responsable sugerido Fabricio Melendez Quezada; no corregir heuristicas profundas sin coordinacion.

## Ejecucion parcial

Windows, Python 3.13.17, pytest 9.1.1, dependencias de backend/requirements.txt; base dfeaa56f. La bateria dirigida obtuvo 50 PASS, 0 FAIL, 0 omitidos: ver [JUnit](cases-junit.xml). La regresion seleccionada obtuvo 554 PASS, 0 FAIL, 0 omitidos: ver [JUnit](regression-junit.xml). El nombre del host se ha eliminado de ambos XML; los resultados no se alteraron. El [JUnit inicial](common-junit.xml) corresponde a la primera ejecucion de 24 casos.

| Caso | Metodo | Esperado | Obtenido | Evidencia |
|---|---|---|---|---|
| AF-01, 07, 08, 10 | seis | Dos rectangulos validos en 8x8 con margen 1 y separacion 0 o 1 | 12 casos aceptados por oraculo rectangular independiente | PASS, test_common_geometry_with_margin |
| AF-02 | FF/BF | FF primera fuente 6x4; BF fuente 3x3 de menor residual | IDs 1 y 2 respectivamente sobre mismo fixture | PASS, test_first_fit_and_best_fit_differ_on_same_sources |
| AF-03 | WF/FF | WF elige fuente usada con mayor residual; FF primera factible | IDs [1,2,2] y [1,2,1] | PASS, test_among_sources_in_use_wf_picks_most_post_placement_free_cells |
| AF-04 | HF/FF | Pocket valido, disposicion diferente y cobertura conservada | Ambos completos; HF coloca pieza 4 en (47,24) | PASS, test_hf03_real_optimizer_uses_pocket_and_differs_from_ff; replay del proyecto, no oraculo independiente |
| AF-05 | M5/FF | M5 deja rectangulo mayor; FF sigue primera fuente | IDs [1,2,2] y [1,2,1] | PASS, test_among_sources_in_use_m5_picks_largest_residual_rectangle |
| AF-06 | M6/FF | Explorar si hay diferencia determinista dentro de limites | Semilla exploratoria 13: piezas 3x2, 2x4, 2x1, 1x3 en 6x6; ambos completos, patrones distintos y validos | PASS de reproducibilidad, test_beam_finds_a_different_valid_deterministic_layout_than_first_fit. El fixture se descubrio antes de fijar coordenadas; no prueba optimalidad ni toda la politica M6. |
| AF-09 | seis | Pieza 3x2 en fuente 2x3 necesita giro permitido | 6 colocaciones completas con giro de 90 o 270 grados | PASS, test_required_quarter_turn |
| AF-11 | seis | 7x7 en 6x4 no cabe; sin colocaciones | 6 rechazos controlados | PASS, test_impossible_piece_is_not_placed |
| AF-12 | seis | Formas mixtas validas | 6 patrones completos con rectangulo, circulo y poligono, acotados por cajas disjuntas independientes | PASS, test_mixed_shapes_have_disjoint_bounding_boxes |

MF-01 para la bateria dirigida: 50/50 = 100% de los casos pytest ejecutados, no del universo de requisitos. MF-02 para el subconjunto rectangular con oraculo independiente: 26/26 = 100% patrones (12 comunes, 6 de rotacion, 2 de AF-06 y 6 de AF-12 con oraculo conservador de cajas); no extrapolar a otros datasets. MF-03: 6/6 politicas con al menos un caso controlado correcto; para M6 se verifica frontera acotada, cierre por niveles e independencia entre motores mediante test_bounded_policy_closes_every_level_and_revalidates_geometry y test_resource_exhaustion_never_calls_another_engine. No prueba exhaustivamente toda la funcion de puntuacion. Ningun defecto observado en estas ejecuciones no demuestra ausencia de defectos.

Comandos ejecutados desde backend, usando el entorno aislado creado para esta tarea:

```text
..\.qa003-venv\Scripts\python.exe -m pytest tests/unit/optimization/test_ta_qa_003_common.py tests/unit/optimization/test_best_fit.py::test_normal_chooses_smallest_remaining_source_and_keeps_method_with_metrics tests/unit/optimization/test_first_fit.py::test_first_candidate_wins_without_trying_later_better_sheet tests/unit/optimization/test_worst_fit.py::test_among_sources_in_use_wf_picks_most_post_placement_free_cells tests/unit/optimization/test_hole_filling.py::test_hf03_real_optimizer_uses_pocket_and_differs_from_ff tests/unit/optimization/test_best_residual_fit.py::test_among_sources_in_use_m5_picks_largest_residual_rectangle tests/unit/optimization/test_beam_search_independent.py -q -ra --junitxml=../docs/evidence/sprint-02/TA-QA-003/cases-junit.xml
..\.qa003-venv\Scripts\python.exe -m pytest tests/unit/optimization/test_first_fit.py tests/unit/optimization/test_best_fit.py tests/unit/optimization/test_worst_fit.py tests/unit/optimization/test_hole_filling.py tests/unit/optimization/test_best_residual_fit.py tests/unit/optimization/test_beam_search.py tests/unit/optimization/test_beam_search_independent.py tests/unit/optimization/test_rotation.py tests/unit/optimization/test_run_geometry.py tests/unit/optimization/test_ta045_separation.py tests/unit/optimization/test_comparison.py tests/optimization -q -ra --junitxml=../docs/evidence/sprint-02/TA-QA-003/regression-junit.xml
```

Limitaciones: el fixture mixto usa cajas disjuntas, un criterio conservador suficiente para este caso, no un oraculo general para poligonos solapados en caja. El caso M6 fue descubierto exploratoriamente y sus pruebas controladas no agotan todas las combinaciones de la funcion de puntuacion. Pendiente cotejar subtareas con Notion. No se ha solicitado correccion de motor ni se han modificado motores.
